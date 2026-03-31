from pydantic import BaseModel
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    chunk_count: int
    status: str
    message: str


class DocumentListItem(BaseModel):
    id: int
    filename: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDeleteResponse(BaseModel):
    message: str
    filename: str
    deleted_chunks: int
