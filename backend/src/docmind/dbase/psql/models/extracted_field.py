"""ExtractedField Model.

Stores individual extracted fields with confidence scores and bounding boxes.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base

if TYPE_CHECKING:
    from .extraction import Extraction


def _uuid() -> str:
    return str(uuid.uuid4())


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    extraction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("extractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)
    field_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vlm_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cv_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    extraction: Mapped["Extraction"] = relationship(back_populates="fields")
