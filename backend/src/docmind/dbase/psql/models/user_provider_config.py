"""User Provider Config Model.

Stores user-configured AI provider settings with encrypted API keys.
One config per (user_id, provider_type) pair.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserProviderConfig(Base):
    __tablename__ = "user_provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "vlm" | "embedding"
    provider_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "dashscope" | "openai" | "google" | "ollama"
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint("user_id", "provider_type", name="uq_user_provider_type"),
    )
