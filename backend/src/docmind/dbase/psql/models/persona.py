"""Persona Model.

Stores AI persona configurations for project-level RAG chat.
Presets (is_preset=True) are shared; custom personas are user-scoped.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    boundaries: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
