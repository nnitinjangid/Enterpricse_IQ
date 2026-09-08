from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True