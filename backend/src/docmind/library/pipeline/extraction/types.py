"""Shared types for the extraction pipeline."""

from typing import Any, Callable, TypedDict


class AuditEntry(TypedDict):
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int
    timestamp: str


class ExtractionState(TypedDict):
    document_id: str
    user_id: str
    file_bytes: bytes
    file_type: str
    template_type: str | None
    page_images: list[Any]
    page_count: int
    quality_map: dict
    skew_angles: list[float]
    raw_fields: list[dict]
    vlm_response: dict
    document_type: str | None
    enhanced_fields: list[dict]
    comparison_data: dict
    extraction_id: str
    status: str
    error_message: str | None
    audit_entries: list[AuditEntry]
    progress_callback: Callable | None
