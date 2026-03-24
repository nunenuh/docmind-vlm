"""
docmind/modules/extractions/usecase.py

Extraction use case — orchestrates repository calls and maps to response schemas.
"""

from docmind.core.logging import get_logger

from .repositories import ExtractionRepository
from .services import ExtractionService
from .schemas import (
    AuditEntryResponse,
    ComparisonResponse,
    ExtractedFieldResponse,
    ExtractionResponse,
    OverlayRegion,
)

logger = get_logger(__name__)

# Confidence color thresholds
_HIGH_CONFIDENCE = 0.8
_MEDIUM_CONFIDENCE = 0.5
_COLOR_HIGH = "#22c55e"      # green
_COLOR_MEDIUM = "#f59e0b"    # amber
_COLOR_LOW = "#ef4444"       # red




class ExtractionUseCase:
    """Orchestrates extraction operations."""

    def __init__(
        self,
        repo: ExtractionRepository | None = None,
        service: ExtractionService | None = None,
    ) -> None:
        self.repo = repo or ExtractionRepository()
        self.service = service or ExtractionService()

    async def get_extraction(self, document_id: str) -> ExtractionResponse | None:
        """Get the latest extraction with fields for a document.

        Args:
            document_id: The document ID.

        Returns:
            ExtractionResponse with nested fields, or None.
        """
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            return None

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

    async def get_audit_trail(self, document_id: str) -> list[AuditEntryResponse]:
        """Get audit trail for the latest extraction of a document.

        Args:
            document_id: The document ID.

        Returns:
            List of AuditEntryResponse, or empty list.
        """
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

    async def get_overlay_data(self, document_id: str) -> list[OverlayRegion]:
        """Get confidence overlay regions for the latest extraction.

        Maps each extracted field's bounding box to an OverlayRegion
        with color coding based on confidence level.

        Args:
            document_id: The document ID.

        Returns:
            List of OverlayRegion, or empty list.
        """
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            return []

        fields = await self.repo.get_fields(str(extraction.id))

        regions = []
        for f in fields:
            bbox = f.bounding_box or {}
            regions.append(OverlayRegion(
                x=bbox.get("x", 0.0),
                y=bbox.get("y", 0.0),
                width=bbox.get("width", 0.0),
                height=bbox.get("height", 0.0),
                confidence=f.confidence,
                color=self.service.confidence_color(f.confidence),
                tooltip=f"{f.field_key}: {f.field_value}" if f.field_key else None,
            ))
        return regions

    async def get_comparison(self, document_id: str) -> ComparisonResponse | None:
        """Get comparison data for the latest extraction.

        Args:
            document_id: The document ID.

        Returns:
            ComparisonResponse or None if no extraction exists.
        """
        extraction = await self.repo.get_latest_extraction(document_id)
        if extraction is None:
            return None

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
