"""Citation Model.

Stores document citations referenced in chat messages.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base

if TYPE_CHECKING:
    from .chat_message import ChatMessage


def _uuid() -> str:
    return str(uuid.uuid4())


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    text_span: Mapped[str] = mapped_column(Text, nullable=False, default="")

    message: Mapped["ChatMessage"] = relationship(back_populates="citations")
