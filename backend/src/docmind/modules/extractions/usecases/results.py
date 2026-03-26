"""Extraction results usecase — read extractions, audit trails, overlays."""

from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException

from ..protocols import ConfidenceServiceProtocol, ExtractionRepositoryProtocol
from ..repositories import ExtractionRepository
from ..schemas import (
    AuditEntryResponse,
    ComparisonResponse,
    ExtractedFieldResponse,
    ExtractionResponse,
    OverlayRegion,
)
from ..services import ConfidenceService

logger = get_logger(__name__)


class ExtractionResultsUseCase:
    """Orchestrates reading extraction results."""

    def __init__(
        self,
        repo: ExtractionRepositoryProtocol | None = None,
        confidence_service: ConfidenceServiceProtocol | None = None,
    ) -> None:
        self.repo = repo or ExtractionRepository()
        self.confidence_service = confidence_service or ConfidenceService()

    async def get_extraction(self, document_id: str) -> ExtractionResponse:
        """Get the latest extraction with fields for a document."""
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            raise NotFoundException("Extraction not found")

        fields = await self.repo.get_fields(str(extraction.id))

        field_responses = [
            ExtractedFieldResponse(
                id=str(f.id),
                field_type=f.field_type,
                field_key=f.field_key,
                field_value=f.field_value,
                page_number=f.page_number,
                bounding_box=f.bounding_box or {},
                confidence=f.confidence,
                vlm_confidence=f.vlm_confidence,
                cv_quality_score=f.cv_quality_score,
                is_required=f.is_required,
                is_missing=f.is_missing,
            )
            for f in fields
        ]

        return ExtractionResponse(
            id=str(extraction.id),
            document_id=str(extraction.document_id),
            mode=extraction.mode,
            template_type=extraction.template_type,
            fields=field_responses,
            processing_time_ms=extraction.processing_time_ms,
            created_at=extraction.created_at,
        )

    async def get_audit_trail(
        self, document_id: str
    ) -> list[AuditEntryResponse]:
        """Get audit trail for the latest extraction."""
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            return []

        entries = await self.repo.get_audit_trail(str(extraction.id))
        return [
            AuditEntryResponse(
                step_name=e.step_name,
                step_order=e.step_order,
                input_summary=e.input_summary or {},
                output_summary=e.output_summary or {},
                parameters=e.parameters or {},
                duration_ms=e.duration_ms,
            )
            for e in entries
        ]

    async def get_overlay_data(
        self, document_id: str
    ) -> list[OverlayRegion]:
        """Get confidence overlay regions for the latest extraction."""
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            return []

        fields = await self.repo.get_fields(str(extraction.id))
        return [
            OverlayRegion(
                x=bbox.get("x", 0.0),
                y=bbox.get("y", 0.0),
                width=bbox.get("width", 0.0),
                height=bbox.get("height", 0.0),
                confidence=f.confidence,
                color=self.confidence_service.confidence_color(f.confidence),
                tooltip=(
                    f"{f.field_key}: {f.field_value}" if f.field_key else None
                ),
            )
            for f in fields
            for bbox in [f.bounding_box or {}]
        ]

    async def get_comparison(
        self, document_id: str
    ) -> ComparisonResponse:
        """Get comparison data for the latest extraction."""
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            raise NotFoundException("Comparison not available")

        fields = await self.repo.get_fields(str(extraction.id))
        field_responses = [
            ExtractedFieldResponse(
                id=str(f.id),
                field_type=f.field_type,
                field_key=f.field_key,
                field_value=f.field_value,
                page_number=f.page_number,
                bounding_box=f.bounding_box or {},
                confidence=f.confidence,
                vlm_confidence=f.vlm_confidence,
                cv_quality_score=f.cv_quality_score,
                is_required=f.is_required,
                is_missing=f.is_missing,
            )
            for f in fields
        ]

        return ComparisonResponse(
            enhanced_fields=field_responses,
            raw_fields=[],
            corrected=[],
            added=[],
        )
