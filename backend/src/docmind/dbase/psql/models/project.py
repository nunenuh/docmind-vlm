"""Project Model.

Stores project metadata for Knowledge Base mode.
All queries MUST filter by user_id.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base

if TYPE_CHECKING:
    from .document import Document
    from .persona import Persona
    from .project_conversation import ProjectConversation


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("personas.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    persona: Mapped["Persona | None"] = relationship(lazy="selectin")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        foreign_keys="Document.project_id",
    )
    conversations: Mapped[list["ProjectConversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
