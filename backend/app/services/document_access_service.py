from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User


ALLOWED_ACCESS_SCOPES = {
    "private",
    "role",
    "company",
}

ALLOWED_ROLES = {
    "admin",
    "manager",
    "user",
}


def validate_access_configuration(
    access_scope: str,
    access_role: str | None = None,
) -> None:

    if access_scope not in ALLOWED_ACCESS_SCOPES:

        raise ValueError(
            "Invalid document access scope. "
            "Allowed values: private, role, company."
        )

    if access_scope == "role":

        if not access_role:

            raise ValueError(
                "access_role is required when "
                "access_scope is 'role'."
            )

        if access_role not in ALLOWED_ROLES:

            raise ValueError(
                "Invalid access role. "
                "Allowed roles: admin, manager, user."
            )

    else:

        if access_role is not None:

            raise ValueError(
                "access_role must be null when "
                "access_scope is not 'role'."
            )


def can_access_document(
    document: Document,
    user: User,
) -> bool:

    # -----------------------------------------
    # ADMIN
    # -----------------------------------------

    if user.role == "admin":
        return True

    # -----------------------------------------
    # DOCUMENT OWNER
    # -----------------------------------------

    if document.uploaded_by == user.id:
        return True

    # -----------------------------------------
    # COMPANY ACCESS
    # -----------------------------------------

    if document.access_scope == "company":
        return True

    # -----------------------------------------
    # ROLE ACCESS
    # -----------------------------------------

    if document.access_scope == "role":

        return (
            document.access_role
            == user.role
        )

    # -----------------------------------------
    # PRIVATE ACCESS
    # -----------------------------------------

    return False


def can_manage_document_access(
    document: Document,
    user: User,
) -> bool:

    # Admin can manage every document.

    if user.role == "admin":
        return True

    # Document owner can manage their own document.

    if document.uploaded_by == user.id:
        return True

    return False


def get_authorized_documents(
    db: Session,
    user: User,
) -> list[Document]:

    documents = (
        db.query(Document)
        .all()
    )

    return [
        document
        for document in documents
        if can_access_document(
            document=document,
            user=user,
        )
    ]


def get_authorized_document_ids(
    db: Session,
    user: User,
) -> list[int]:

    documents = get_authorized_documents(
        db=db,
        user=user,
    )

    return [
        document.id
        for document in documents
    ]


def get_document_if_authorized(
    document_id: int,
    db: Session,
    user: User,
) -> Document | None:

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        return None

    if not can_access_document(
        document=document,
        user=user,
    ):
        return None

    return document