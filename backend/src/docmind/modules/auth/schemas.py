"""
docmind/modules/auth/schemas.py

Pydantic models for auth request/response serialization.
"""

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
