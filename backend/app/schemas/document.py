from datetime import datetime
from typing import Literal

from pydantic import BaseModel


AccessScope = Literal[
    "private",
    "role",
    "company",
]


class DocumentUploadResponse(BaseModel):

    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str

    uploaded_by: int

    access_scope: AccessScope
    access_role: str | None

    created_at: datetime

    class Config:
        from_attributes = True


class DocumentAccessUpdateRequest(BaseModel):

    access_scope: AccessScope

    access_role: str | None = None