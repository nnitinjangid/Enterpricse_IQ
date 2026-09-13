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


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def get_file_extension(
    filename: str,
) -> str:

    return Path(
        filename
    ).suffix.lower()


# =========================================================
# INTERNAL DOCUMENT PROCESSING
# =========================================================

def process_document(
    document: Document,
    current_user: User,
    db: Session,
) -> dict:
    """
    Run the complete document ingestion pipeline.

    Pipeline:

        Extract
            ↓
        Chunk
            ↓
        Save chunks in MySQL
            ↓
        Generate embeddings
            ↓
        Store vectors in Qdrant
            ↓
        Mark document as embedded
    """

    # =====================================================
    # STEP 1 - EXTRACT TEXT
    # =====================================================

    try:

        text = extract_text(
            document.file_path,
            document.file_type,
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = (
            f"Document extraction failed: {str(e)}"
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                f"Document extraction failed: {str(e)}"
            ),
        )

    if not text or not text.strip():

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

    # =====================================================
    # STEP 2 - CREATE CHUNKS
    # =====================================================

    try:

        chunks = create_document_chunks(
            text=text,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

    except Exception as e:

        document.status = "failed"

        document.error_message = (
            f"Chunking failed: {str(e)}"
        )

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

    # =====================================================
    # STEP 3 - REMOVE OLD MYSQL CHUNKS
    # =====================================================

    db.query(
        DocumentChunk
    ).filter(
        DocumentChunk.document_id
        == document.id
    ).delete(
        synchronize_session=False
    )

    # =====================================================
    # STEP 4 - SAVE NEW CHUNKS IN MYSQL
    # =====================================================

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

        document.error_message = (
            f"Failed to save document chunks: {str(e)}"
        )

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

    # =====================================================
    # STEP 5 - GENERATE EMBEDDINGS + STORE IN QDRANT
    # =====================================================

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

    # =====================================================
    # STEP 6 - VERIFY VECTOR COUNT
    # =====================================================

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

    # =====================================================
    # STEP 7 - MARK DOCUMENT AS EMBEDDED
    # =====================================================

    document.status = "embedded"

    document.error_message = None

    db.commit()

    db.refresh(
        document
    )

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "status": document.status,
        "text_length": len(text),
        "total_chunks": len(chunks),
        "vectors_stored": vector_count,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "access_scope": document.access_scope,
        "access_role": document.access_role,
    }


# =========================================================
# GET ALL DOCUMENTS
# =========================================================

@router.get(
    "",
)
def get_documents(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """
    Return documents visible to the current user.

    Admin:
        Can see all documents.

    Normal user:
        Can see:
        - Their own documents
        - Company documents
        - Documents assigned to their role
    """

    query = db.query(
        Document
    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if current_user.role == "admin":

        documents = (
            query
            .order_by(
                Document.id.desc()
            )
            .all()
        )

    # -----------------------------------------------------
    # NORMAL USER
    # -----------------------------------------------------

    else:

        from sqlalchemy import or_

        documents = (
            query
            .filter(
                or_(
                    Document.uploaded_by
                    == current_user.id,

                    Document.access_scope
                    == "company",

                    (
                        Document.access_scope
                        == "role"
                    )
                    & (
                        Document.access_role
                        == current_user.role
                    ),
                )
            )
            .order_by(
                Document.id.desc()
            )
            .all()
        )

    # -----------------------------------------------------
    # BUILD RESPONSE
    # -----------------------------------------------------

    result = []

    for document in documents:

        chunk_count = (
            db.query(
                DocumentChunk
            )
            .filter(
                DocumentChunk.document_id
                == document.id
            )
            .count()
        )

        result.append(
            {
                "id": document.id,
                "filename": document.filename,
                "original_filename": (
                    document.original_filename
                ),
                "file_type": document.file_type,
                "file_size": document.file_size,
                "status": document.status,
                "uploaded_by": document.uploaded_by,
                "access_scope": (
                    document.access_scope
                ),
                "access_role": (
                    document.access_role
                ),
                "chunk_count": chunk_count,
                "error_message": (
                    document.error_message
                ),
            }
        )

    return {
        "total": len(result),
        "documents": result,
    }


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

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

    # =====================================================
    # VALIDATE FILENAME
    # =====================================================

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

    # =====================================================
    # VALIDATE FILE TYPE
    # =====================================================

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. "
                "Allowed types: PDF, DOCX, CSV, XLSX."
            ),
        )

    # =====================================================
    # READ FILE
    # =====================================================

    file_content = await file.read()

    file_size = len(
        file_content
    )

    # =====================================================
    # VALIDATE EMPTY FILE
    # =====================================================

    if file_size == 0:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # =====================================================
    # VALIDATE FILE SIZE
    # =====================================================

    if file_size > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "File size cannot exceed 20 MB."
            ),
        )

    # =====================================================
    # CREATE UPLOAD DIRECTORY
    # =====================================================

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =====================================================
    # CREATE UNIQUE STORED FILENAME
    # =====================================================

    stored_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    file_path = (
        UPLOAD_DIR
        / stored_filename
    )

    # =====================================================
    # SAVE FILE
    # =====================================================

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

    # =====================================================
    # CREATE DOCUMENT RECORD
    # =====================================================

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

    # =====================================================
    # SAVE DOCUMENT IN MYSQL
    # =====================================================

    try:

        db.add(
            document
        )

        db.commit()

        db.refresh(
            document
        )

    except Exception:

        if file_path.exists():

            os.remove(
                file_path
            )

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Failed to create document record."
            ),
        )

    # =====================================================
    # RUN COMPLETE INGESTION PIPELINE
    # =====================================================

    try:

        process_document(
            document=document,
            current_user=current_user,
            db=db,
        )

    except HTTPException:

        # process_document already updates
        # document status and error_message.

        raise

    except Exception as e:

        document.status = "failed"

        document.error_message = (
            f"Document processing failed: {str(e)}"
        )

        db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                f"Document processing failed: {str(e)}"
            ),
        )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    db.refresh(
        document
    )

    return document


# =========================================================
# UPDATE DOCUMENT ACCESS
# =========================================================

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

    # =====================================================
    # FIND DOCUMENT
    # =====================================================

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

    # =====================================================
    # CHECK MANAGEMENT PERMISSION
    # =====================================================

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

    # =====================================================
    # VALIDATE ACCESS CONFIGURATION
    # =====================================================

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

    # =====================================================
    # UPDATE MYSQL
    # =====================================================

    document.access_scope = (
        access_data.access_scope
    )

    document.access_role = (
        access_data.access_role
    )

    try:

        db.commit()

        db.refresh(
            document
        )

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Failed to update document access: "
                f"{str(e)}"
            ),
        )

    # =====================================================
    # UPDATE QDRANT METADATA
    # =====================================================

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
                "Please retry the access update. "
                f"Error: {str(e)}"
            ),
        )

    return document


# =========================================================
# EXTRACT DOCUMENT TEXT
# =========================================================

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

    # =====================================================
    # FIND DOCUMENT
    # =====================================================

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.uploaded_by
            == current_user.id,
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # =====================================================
    # EXTRACT
    # =====================================================

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
                f"Document extraction failed: "
                f"{str(e)}"
            ),
        )

    # =====================================================
    # VALIDATE TEXT
    # =====================================================

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

    # =====================================================
    # UPDATE STATUS
    # =====================================================

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


# =========================================================
# CHUNK DOCUMENT
# =========================================================

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

    # =====================================================
    # FIND DOCUMENT
    # =====================================================

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.uploaded_by
            == current_user.id,
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # =====================================================
    # EXTRACT
    # =====================================================

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
                f"Document extraction failed: "
                f"{str(e)}"
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

    # =====================================================
    # CREATE CHUNKS
    # =====================================================

    try:

        chunks = create_document_chunks(
            text=text,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
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

    # =====================================================
    # DELETE OLD CHUNKS
    # =====================================================

    db.query(
        DocumentChunk
    ).filter(
        DocumentChunk.document_id
        == document.id
    ).delete(
        synchronize_session=False
    )

    # =====================================================
    # SAVE CHUNKS
    # =====================================================

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

    # =====================================================
    # STORE VECTORS
    # =====================================================

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

    # =====================================================
    # VERIFY VECTOR COUNT
    # =====================================================

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

    # =====================================================
    # SUCCESS
    # =====================================================

    document.status = "embedded"

    document.error_message = None

    db.commit()

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "status": document.status,
        "total_chunks": len(chunks),
        "vectors_stored": vector_count,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "access_scope": (
            document.access_scope
        ),
        "access_role": (
            document.access_role
        ),
        "chunks": chunks,
    }