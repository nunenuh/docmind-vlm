"""docmind/modules/documents/schemas.py"""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., pattern="^(pdf|png|jpg|jpeg|tiff|webp)$")
    file_size: int = Field(..., gt=0, le=20_971_520)
    storage_path: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    document_type: str | None
    page_count: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    limit: int


class ProcessRequest(BaseModel):
    """Deprecated — use POST /api/v1/extractions/{document_id}/process instead."""

    template_type: str | None = None


class DocumentSearchParams(BaseModel):
    """Query parameters for document search."""

    q: str | None = None
    file_type: str | None = None
    status: str | None = None
    standalone: bool = True
