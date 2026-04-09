"""docmind/modules/personas/schemas.py"""

from datetime import datetime

from pydantic import BaseModel, Field


class PersonaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str = Field(..., min_length=1)
    tone: str = Field(default="professional", max_length=50)
    rules: str | None = None
    boundaries: str | None = None


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str | None = Field(default=None, min_length=1)
    tone: str | None = Field(default=None, max_length=50)
    rules: str | None = None
    boundaries: str | None = None


class PersonaResponse(BaseModel):
    id: str
    name: str
    description: str | None
    system_prompt: str
    tone: str
    rules: str | None
    boundaries: str | None
    is_preset: bool
    created_at: datetime
