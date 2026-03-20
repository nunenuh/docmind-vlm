"""docmind/modules/projects/schemas.py"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    persona_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    persona_id: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    persona_id: str | None
    document_count: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    limit: int


class ProjectDocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: str | None
    message_count: int
    created_at: datetime


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: str | None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: str
    title: str | None
    messages: list[MessageResponse]
    created_at: datetime
