"""
docmind/modules/settings/schemas.py

Pydantic models for provider configuration request/response serialization.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class ProviderType(str, Enum):
    VLM = "vlm"
    EMBEDDING = "embedding"


class ProviderName(str, Enum):
    DASHSCOPE = "dashscope"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GOOGLE = "google"
    OLLAMA = "ollama"


# ── Requests ─────────────────────────────────────────────


class SetProviderRequest(BaseModel):
    provider_name: ProviderName
    api_key: str = Field(..., min_length=1, max_length=500)
    model_name: str = Field(..., min_length=1, max_length=100)
    base_url: str | None = Field(default=None, max_length=500)


class ValidateProviderRequest(BaseModel):
    provider_name: ProviderName
    api_key: str = Field(..., min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)


# ── Responses ────────────────────────────────────────────


class ValidateProviderResponse(BaseModel):
    success: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None


class ProviderConfigResponse(BaseModel):
    provider_type: ProviderType
    provider_name: ProviderName
    model_name: str
    base_url: str | None
    is_validated: bool
    api_key_prefix: str
    created_at: datetime
    updated_at: datetime


class ProvidersResponse(BaseModel):
    vlm: ProviderConfigResponse | None = None
    embedding: ProviderConfigResponse | None = None
