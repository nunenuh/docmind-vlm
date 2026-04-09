"""Extraction Model.

Stores extraction job metadata linked to a document.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base

if TYPE_CHECKING:
    from .audit_entry import AuditEntry
    from .document import Document
    from .extracted_field import ExtractedField


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="general")
    template_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    document: Mapped["Document"] = relationship(back_populates="extractions")
    fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list["AuditEntry"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )
