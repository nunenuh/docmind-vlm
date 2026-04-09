"""
docmind/modules/auth/schemas.py

Pydantic models for auth request/response serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ── Requests ──────────────────────────────────────────


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Responses ─────────────────────────────────────────


class AuthUserResponse(BaseModel):
    id: str
    email: str
    created_at: str | None = None


class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: AuthUserResponse


class SessionResponse(BaseModel):
    user: AuthUserResponse


class MessageResponse(BaseModel):
    message: str


# ── API Token Scopes ─────────────────────────────────


class TokenScope(str, Enum):
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"
    EXTRACTIONS_READ = "extractions:read"
    EXTRACTIONS_WRITE = "extractions:write"
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    PROJECTS_CHAT = "projects:chat"
    RAG_READ = "rag:read"
    TEMPLATES_READ = "templates:read"
    TEMPLATES_WRITE = "templates:write"
    PERSONAS_READ = "personas:read"
    PERSONAS_WRITE = "personas:write"
    ADMIN_ALL = "admin:*"


# ── API Token Requests ───────────────────────────────


class CreateTokenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[TokenScope]
    token_type: Literal["live", "test"] = "live"
    expires_in_days: int | None = Field(
        default=90,
        ge=1,
        le=365,
        description="Days until token expires. Null for no expiry.",
    )


class UpdateTokenRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    scopes: list[TokenScope] | None = None


# ── API Token Responses ──────────────────────────────


class TokenResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    token_type: str
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    revoked_at: datetime | None


class TokenCreatedResponse(TokenResponse):
    plain_token: str


class TokenListResponse(BaseModel):
    tokens: list[TokenResponse]
    total: int
