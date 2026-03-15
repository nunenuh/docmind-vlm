"""docmind/modules/extractions/usecase.py — Stub."""

from docmind.core.logging import get_logger

from .schemas import (
    AuditEntryResponse,
    ComparisonResponse,
    ExtractionResponse,
    OverlayRegion,
)

logger = get_logger(__name__)


class ExtractionUseCase:
    def get_extraction(self, document_id: str) -> ExtractionResponse | None:
        return None

    def get_audit_trail(self, document_id: str) -> list[AuditEntryResponse]:
        return []

    def get_overlay_data(self, document_id: str) -> list[OverlayRegion]:
        return []

    def get_comparison(self, document_id: str) -> ComparisonResponse | None:
        return None
