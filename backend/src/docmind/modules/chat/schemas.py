"""docmind/modules/chat/schemas.py"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class Citation(BaseModel):
    page: int
    bounding_box: dict
    text_span: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation]
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    items: list[ChatMessageResponse]
    total: int
    page: int
    limit: int
