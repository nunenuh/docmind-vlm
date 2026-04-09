"""docmind/modules/extractions/schemas.py"""

from datetime import datetime

from pydantic import BaseModel, Field


class ExtractedFieldResponse(BaseModel):
    id: str
    field_type: str
    field_key: str | None
    field_value: str
    page_number: int
    bounding_box: dict
    confidence: float = Field(..., ge=0.0, le=1.0)
    vlm_confidence: float
    cv_quality_score: float
    is_required: bool
    is_missing: bool


class ExtractionResponse(BaseModel):
    id: str
    document_id: str
    mode: str
    template_type: str | None
    fields: list[ExtractedFieldResponse]
    processing_time_ms: int
    created_at: datetime


class AuditEntryResponse(BaseModel):
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int


class OverlayRegion(BaseModel):
    x: float
    y: float
    width: float
    height: float
    confidence: float
    color: str
    tooltip: str | None


class ComparisonResponse(BaseModel):
    enhanced_fields: list[ExtractedFieldResponse]
    raw_fields: list[dict]
    corrected: list[str]
    added: list[str]


# ── API Request Schemas ───────────────────────────────────


class ProcessRequest(BaseModel):
    """Request body for triggering extraction pipeline."""

    template_type: str | None = None


class ClassifyRequest(BaseModel):
    """Request body for auto-detecting document type."""

    document_id: str = Field(..., min_length=1)


class ClassifyResponse(BaseModel):
    """Response from document type classification."""

    document_type: str | None
    confidence: float = 0.0
