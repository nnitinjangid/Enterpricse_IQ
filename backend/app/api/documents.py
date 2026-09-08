import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentUploadResponse
from app.services.document_parser import extract_text
from app.services.qdrant_service import (
    store_document_chunks,
)
from app.services.text_chunker import (
    create_document_chunks,
)


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)


# =========================================================
# Configuration
# =========================================================

UPLOAD_DIR = Path("uploads")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".csv",
    ".xlsx",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# =========================================================
# Helper Functions
# =========================================================

def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase.
    """

    return Path(filename).suffix.lower()


# =========================================================
# Upload Document
# =========================================================

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload an enterprise document.

    Supported formats:
    - PDF
    - DOCX
    - CSV
    - XLSX

    Maximum file size:
    - 20 MB
    """

    # -----------------------------------------------------
    # Validate filename
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    original_filename = Path(
        file.filename
    ).name

    # -----------------------------------------------------
    # Validate extension
    # -----------------------------------------------------

    extension = get_file_extension(
        original_filename
    )

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. "
                "Allowed types: PDF, DOCX, CSV, XLSX."
            ),
        )

    # -----------------------------------------------------
    # Read file
    # -----------------------------------------------------

    file_content = await file.read()

    file_size = len(file_content)

    # -----------------------------------------------------
    # Validate empty file
    # -----------------------------------------------------

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # -----------------------------------------------------
    # Validate file size
    # -----------------------------------------------------

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size cannot exceed 20 MB.",
        )

    # -----------------------------------------------------
    # Create upload directory
    # -----------------------------------------------------

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Generate unique filename
    # -----------------------------------------------------

    stored_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    file_path = UPLOAD_DIR / stored_filename

    # -----------------------------------------------------
    # Save file
    # -----------------------------------------------------

    try:

        file_path.write_bytes(
            file_content
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # -----------------------------------------------------
    # Create database record
    # -----------------------------------------------------

    document = Document(
        filename=stored_filename,
        original_filename=original_filename,
        file_type=extension.lstrip("."),
        file_path=str(file_path),
        file_size=file_size,
        status="uploaded",
        uploaded_by=current_user.id,
    )

    try:

        db.add(document)

        db.commit()

        db.refresh(document)

    except Exception:

        if file_path.exists():
            os.remove(file_path)

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document record.",
        )

    return document


# =========================================================
# Extract Document Text
# =========================================================

@router.post(
    "/{document_id}/extract",
)
def extract_document_text(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract text from an uploaded document.

    Supported:
    - PDF
    - DOCX
    - CSV
    - XLSX

    Users can only access documents
    uploaded by themselves.
    """

    # -----------------------------------------------------
    # Find document
    # -----------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.uploaded_by == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # -----------------------------------------------------
    # Extract text
    # -----------------------------------------------------

    try:

        text = extract_text(
            document.file_path,
            document.file_type,
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = str(e)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Document extraction failed: {str(e)}"
            ),
        )

    # -----------------------------------------------------
    # Validate extracted text
    # -----------------------------------------------------

    if not text.strip():

        document.status = "failed"

        document.error_message = (
            "No readable text found in document."
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text found in document.",
        )

    # -----------------------------------------------------
    # Update document status
    # -----------------------------------------------------

    document.status = "extracted"

    document.error_message = None

    db.commit()

    # -----------------------------------------------------
    # Return extracted text
    # -----------------------------------------------------

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "file_type": document.file_type,
        "status": document.status,
        "text_length": len(text),
        "text": text,
    }


# =========================================================
# Create Document Chunks + Store Embeddings
# =========================================================

@router.post(
    "/{document_id}/chunk",
)
def chunk_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract, clean and split a document into chunks.

    Then:

    1. Store chunks in MySQL.
    2. Generate embeddings.
    3. Store embeddings in Qdrant.

    Page numbers are preserved for PDF documents.
    """

    # -----------------------------------------------------
    # Find document
    # -----------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.uploaded_by == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # -----------------------------------------------------
    # Extract text
    # -----------------------------------------------------

    try:

        text = extract_text(
            document.file_path,
            document.file_type,
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = str(e)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Document extraction failed: {str(e)}"
            ),
        )

    # -----------------------------------------------------
    # Validate text
    # -----------------------------------------------------

    if not text.strip():

        document.status = "failed"

        document.error_message = (
            "No readable text found in document."
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text found in document.",
        )

    # -----------------------------------------------------
    # Create chunks
    # -----------------------------------------------------

    try:

        chunks = create_document_chunks(
            text=text,
            chunk_size=1000,
            chunk_overlap=200,
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = str(e)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chunking failed: {str(e)}",
        )

    # -----------------------------------------------------
    # Validate chunks
    # -----------------------------------------------------

    if not chunks:

        document.status = "failed"

        document.error_message = (
            "No chunks could be created from document."
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No chunks could be created.",
        )

    # -----------------------------------------------------
    # Remove existing MySQL chunks
    # -----------------------------------------------------

    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id
    ).delete(
        synchronize_session=False
    )

    # -----------------------------------------------------
    # Save chunks to MySQL
    # -----------------------------------------------------

    try:

        for chunk in chunks:

            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk["chunk_index"],
                page_number=chunk["page_number"],
                content=chunk["content"],
            )

            db.add(document_chunk)

        db.commit()

    except Exception as e:

        db.rollback()

        document.status = "failed"
        document.error_message = str(e)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to save document chunks: {str(e)}"
            ),
        )

    # -----------------------------------------------------
    # Store embeddings in Qdrant
    # -----------------------------------------------------

    try:

        vector_count = store_document_chunks(
            chunks=chunks,
            document_id=document.id,
            filename=document.original_filename,
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = (
            f"Qdrant storage failed: {str(e)}"
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to store embeddings in Qdrant: {str(e)}"
            ),
        )

    # -----------------------------------------------------
    # Validate Qdrant storage
    # -----------------------------------------------------

    if vector_count != len(chunks):

        document.status = "failed"

        document.error_message = (
            "Some document embeddings were not "
            "stored in Qdrant."
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Some document embeddings were not "
                "stored in Qdrant."
            ),
        )

    # -----------------------------------------------------
    # Update document status
    # -----------------------------------------------------

    document.status = "embedded"

    document.error_message = None

    db.commit()

    # -----------------------------------------------------
    # Return result
    # -----------------------------------------------------

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "status": document.status,
        "total_chunks": len(chunks),
        "vectors_stored": vector_count,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "chunks": chunks,
    }