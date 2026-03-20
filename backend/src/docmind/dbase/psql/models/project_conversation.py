"""ProjectConversation Model.

Stores conversation sessions within a project for RAG chat.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base

if TYPE_CHECKING:
    from .project import Project
    from .project_message import ProjectMessage


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectConversation(Base):
    __tablename__ = "project_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    project: Mapped["Project"] = relationship(back_populates="conversations")
    messages: Mapped[list["ProjectMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="ProjectMessage.created_at",
    )
