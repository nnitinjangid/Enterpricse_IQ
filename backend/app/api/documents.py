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

from app.core.dependencies import (
    get_current_user,
)

from app.models.document import Document

from app.models.document_chunk import (
    DocumentChunk,
)

from app.models.user import User

from app.schemas.document import (
    DocumentAccessUpdateRequest,
    DocumentUploadResponse,
)

from app.services.document_access_service import (
    can_manage_document_access,
    validate_access_configuration,
)

from app.services.document_parser import (
    extract_text,
)

from app.services.qdrant_service import (
    store_document_chunks,
    update_document_access_metadata,
)

from app.services.text_chunker import (
    create_document_chunks,
)


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)


UPLOAD_DIR = Path("uploads")


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".csv",
    ".xlsx",
}


MAX_FILE_SIZE = 20 * 1024 * 1024


def get_file_extension(
    filename: str,
) -> str:

    return Path(
        filename
    ).suffix.lower()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    if not file.filename:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    original_filename = Path(
        file.filename
    ).name

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

    file_content = await file.read()

    file_size = len(
        file_content
    )

    if file_size == 0:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "File size cannot exceed 20 MB."
            ),
        )

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    file_path = (
        UPLOAD_DIR
        / stored_filename
    )

    try:

        file_path.write_bytes(
            file_content
        )

    except Exception as e:

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                f"Failed to save file: {str(e)}"
            ),
        )

    document = Document(
        filename=stored_filename,
        original_filename=original_filename,
        file_type=extension.lstrip("."),
        file_path=str(file_path),
        file_size=file_size,
        status="uploaded",
        uploaded_by=current_user.id,

        # ---------------------------------
        # DEFAULT ACCESS
        # ---------------------------------
        access_scope="private",
        access_role=None,
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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Failed to create document record."
            ),
        )

    return document


@router.patch(
    "/{document_id}/access",
    response_model=DocumentUploadResponse,
)
def update_document_access(
    document_id: int,
    access_data: DocumentAccessUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    # -----------------------------------------
    # FIND DOCUMENT
    # -----------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # -----------------------------------------
    # CHECK MANAGEMENT PERMISSION
    # -----------------------------------------

    if not can_manage_document_access(
        document=document,
        user=current_user,
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission "
                "to change access for this document."
            ),
        )

    # -----------------------------------------
    # VALIDATE ACCESS CONFIGURATION
    # -----------------------------------------

    try:

        validate_access_configuration(
            access_scope=(
                access_data.access_scope
            ),
            access_role=(
                access_data.access_role
            ),
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # -----------------------------------------
    # UPDATE MYSQL
    # -----------------------------------------

    document.access_scope = (
        access_data.access_scope
    )

    document.access_role = (
        access_data.access_role
    )

    try:

        db.commit()

        db.refresh(document)

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                f"Failed to update document access: "
                f"{str(e)}"
            ),
        )

    # -----------------------------------------
    # UPDATE QDRANT PAYLOAD
    # -----------------------------------------

    try:

        update_document_access_metadata(
            document_id=document.id,
            access_scope=(
                document.access_scope
            ),
            access_role=(
                document.access_role
            ),
        )

    except Exception as e:

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Document access was updated in MySQL "
                "but Qdrant metadata could not be updated. "
                f"Please retry the access update. Error: {str(e)}"
            ),
        )

    return document


@router.post(
    "/{document_id}/extract",
)
def extract_document_text(
    document_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                f"Document extraction failed: {str(e)}"
            ),
        )

    if not text.strip():

        document.status = "failed"

        document.error_message = (
            "No readable text found in document."
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "No readable text found in document."
            ),
        )

    document.status = "extracted"

    document.error_message = None

    db.commit()

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "file_type": document.file_type,
        "status": document.status,
        "text_length": len(text),
        "text": text,
    }


@router.post(
    "/{document_id}/chunk",
)
def chunk_document(
    document_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                f"Document extraction failed: {str(e)}"
            ),
        )

    if not text.strip():

        document.status = "failed"

        document.error_message = (
            "No readable text found in document."
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "No readable text found in document."
            ),
        )

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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=f"Chunking failed: {str(e)}",
        )

    if not chunks:

        document.status = "failed"

        document.error_message = (
            "No chunks could be created from document."
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "No chunks could be created."
            ),
        )

    db.query(
        DocumentChunk
    ).filter(
        DocumentChunk.document_id
        == document.id
    ).delete(
        synchronize_session=False
    )

    try:

        for chunk in chunks:

            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=(
                    chunk["chunk_index"]
                ),
                page_number=(
                    chunk["page_number"]
                ),
                content=(
                    chunk["content"]
                ),
            )

            db.add(
                document_chunk
            )

        db.commit()

    except Exception as e:

        db.rollback()

        document.status = "failed"

        document.error_message = str(e)

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Failed to save document chunks: "
                f"{str(e)}"
            ),
        )

    try:

        vector_count = store_document_chunks(
            chunks=chunks,
            document_id=document.id,
            filename=(
                document.original_filename
            ),
            uploaded_by=current_user.id,

            access_scope=(
                document.access_scope
            ),

            access_role=(
                document.access_role
            ),
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = (
            f"Qdrant storage failed: {str(e)}"
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Failed to store embeddings in Qdrant: "
                f"{str(e)}"
            ),
        )

    if vector_count != len(chunks):

        document.status = "failed"

        document.error_message = (
            "Some document embeddings were not "
            "stored in Qdrant."
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Some document embeddings were not "
                "stored in Qdrant."
            ),
        )

    document.status = "embedded"

    document.error_message = None

    db.commit()

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "status": document.status,
        "total_chunks": len(chunks),
        "vectors_stored": vector_count,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "access_scope": (
            document.access_scope
        ),
        "access_role": (
            document.access_role
        ),
        "chunks": chunks,
    }