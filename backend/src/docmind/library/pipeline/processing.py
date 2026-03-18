"""
docmind/library/pipeline/processing.py

LangGraph StateGraph for the document processing pipeline.

Nodes: preprocess -> extract -> postprocess -> store.
Each node is a pure function: takes state dict, returns state update dict.
"""

import asyncio
import dataclasses
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict

from docmind.library.cv.deskew import detect_and_correct
from docmind.library.cv.preprocessing import convert_to_page_images
from docmind.library.cv.quality import assess_regions
from docmind.library.providers import get_vlm_provider

logger = logging.getLogger(__name__)


class AuditEntry(TypedDict):
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int
    timestamp: str


class ProcessingState(TypedDict):
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


def _serialize_quality_map(raw_map: dict) -> dict[str, dict]:
    """Serialize quality map from tuple keys to string keys.

    Converts (row, col) tuple keys to "row,col" strings and
    RegionQuality dataclass values to plain dicts.

    Args:
        raw_map: Dict mapping (row, col) tuples to RegionQuality objects.

    Returns:
        Dict with string keys and dict values.
    """
    serialized: dict[str, dict] = {}
    for (row, col), quality in raw_map.items():
        key = f"{row},{col}"
        if dataclasses.is_dataclass(quality):
            serialized[key] = dataclasses.asdict(quality)
        else:
            serialized[key] = {
                "blur_score": quality.blur_score,
                "noise_score": quality.noise_score,
                "contrast_score": quality.contrast_score,
                "overall_score": quality.overall_score,
            }
    return serialized


def preprocess_node(state: dict) -> dict:
    """Preprocess document: convert to images, deskew, assess quality.

    Takes raw file bytes from state, converts to page images,
    runs deskew correction on each page, and assesses quality
    on the first page.

    Args:
        state: ProcessingState dict with file_bytes and file_type.

    Returns:
        State update dict with page_images, page_count, quality_map,
        skew_angles, and audit_entries. On error, returns status='error'
        with error_message.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")

    def _notify(progress: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback("preprocess", progress, message)

    try:
        file_bytes = state["file_bytes"]
        file_type = state["file_type"]

        # Step 1: Convert to page images
        _notify(0.1, "Converting document to page images")
        raw_images = convert_to_page_images(file_bytes, file_type)

        # Step 2: Deskew each page
        _notify(0.4, "Correcting page skew")
        corrected_images = []
        skew_angles = []
        for page_img in raw_images:
            corrected, angle = detect_and_correct(page_img)
            corrected_images.append(corrected)
            skew_angles.append(angle)

        # Step 3: Assess quality on first page
        _notify(0.7, "Assessing image quality")
        quality_map_raw: dict = {}
        if corrected_images:
            quality_map_raw = assess_regions(corrected_images[0])

        quality_map = _serialize_quality_map(quality_map_raw)

        # Compute mean quality for audit
        mean_quality = 0.0
        if quality_map_raw:
            mean_quality = sum(
                q.overall_score for q in quality_map_raw.values()
            ) / len(quality_map_raw)

        # Build audit entry
        duration_ms = int((time.time() - start_time) * 1000)
        audit_entry: AuditEntry = {
            "step_name": "preprocess",
            "step_order": 1,
            "input_summary": {
                "file_type": file_type,
                "file_size_bytes": len(file_bytes),
            },
            "output_summary": {
                "page_count": len(corrected_images),
                "mean_quality": round(mean_quality, 4),
                "skew_angles": skew_angles,
            },
            "parameters": {
                "deskew_threshold": 2.0,
                "quality_grid": "4x4",
            },
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_entries = list(state.get("audit_entries", []))
        existing_entries.append(audit_entry)

        _notify(1.0, "Preprocessing complete")

        return {
            "page_images": corrected_images,
            "page_count": len(corrected_images),
            "quality_map": quality_map,
            "skew_angles": skew_angles,
            "audit_entries": existing_entries,
        }

    except Exception as e:
        logger.error("Preprocessing failed: %s", e)
        return {
            "status": "error",
            "error_message": f"Preprocessing failed: {e}",
        }


GENERAL_EXTRACTION_PROMPT = """Analyze this document and extract all structured information.

For each piece of information found, return a JSON object with:
- "field_type": one of "key_value", "table_cell", "entity", "text_block"
- "field_key": the label/key (null for text blocks)
- "field_value": the extracted text value
- "page_number": which page (1-indexed)
- "bounding_box": {"x": float, "y": float, "width": float, "height": float} as ratios of page dimensions (0.0-1.0)
- "confidence": your confidence in this extraction (0.0-1.0)

Return a JSON object: {"fields": [...], "document_type": "<detected type>"}
"""

DOCUMENT_CATEGORIES = [
    "invoice", "receipt", "medical_report", "contract",
    "id_document", "letter", "form", "other",
]


def extract_node(state: dict) -> dict:
    """Extract structured data from document images using VLM.

    In general mode (no template), uses GENERAL_EXTRACTION_PROMPT.
    Parses fields from VLM response, attaches confidence scores,
    and optionally classifies document type.

    Args:
        state: ProcessingState dict with page_images and template_type.

    Returns:
        State update dict with raw_fields, vlm_response, document_type,
        and audit_entries. On error, returns status='error' with error_message.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")

    def _notify(progress: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback("extract", progress, message)

    try:
        page_images = state["page_images"]
        template_type = state.get("template_type")

        # Get VLM provider
        _notify(0.1, "Initializing VLM provider")
        provider = get_vlm_provider()

        # Build prompt based on mode
        prompt = GENERAL_EXTRACTION_PROMPT

        _notify(0.3, "Running VLM extraction")

        # Call VLM provider
        loop = asyncio.new_event_loop()
        try:
            vlm_response = loop.run_until_complete(
                provider.extract(images=page_images, prompt=prompt)
            )
        finally:
            loop.close()

        _notify(0.6, "Parsing extraction results")

        # Parse fields from VLM response
        structured = vlm_response["structured_data"]
        raw_fields = structured.get("fields", [])
        document_type = structured.get("document_type", template_type)

        # Attach VLM confidence to each field (immutable — new dicts)
        response_confidence = vlm_response["confidence"]
        raw_fields = [
            {**field, "vlm_confidence": field.get("confidence", response_confidence)}
            for field in raw_fields
        ]

        # Classify document type if general mode and not detected
        if not template_type and not document_type and page_images:
            _notify(0.8, "Classifying document type")
            classify_loop = asyncio.new_event_loop()
            try:
                classify_response = classify_loop.run_until_complete(
                    provider.classify(image=page_images[0], categories=DOCUMENT_CATEGORIES)
                )
            finally:
                classify_loop.close()

            document_type = classify_response["structured_data"].get(
                "document_type", "other"
            )

        # Serialize VLM response (exclude raw_response for state)
        serialized_vlm = {
            "content": vlm_response.get("content", ""),
            "confidence": vlm_response.get("confidence", 0.0),
            "model": vlm_response.get("model", ""),
            "usage": vlm_response.get("usage", {}),
        }

        # Build audit entry
        duration_ms = int((time.time() - start_time) * 1000)
        audit_entry: AuditEntry = {
            "step_name": "extract",
            "step_order": 2,
            "input_summary": {
                "mode": "template" if template_type else "general",
                "page_count": len(page_images),
                "template_type": template_type,
            },
            "output_summary": {
                "field_count": len(raw_fields),
                "document_type": document_type,
                "vlm_model": vlm_response.get("model", ""),
            },
            "parameters": {
                "provider": provider.provider_name,
                "model": provider.model_name,
            },
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_entries = list(state.get("audit_entries", []))
        existing_entries.append(audit_entry)

        _notify(1.0, "Extraction complete")

        return {
            "raw_fields": raw_fields,
            "vlm_response": serialized_vlm,
            "document_type": document_type,
            "audit_entries": existing_entries,
        }

    except Exception as e:
        logger.error("Extraction failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_message": "Extraction failed. See server logs for details.",
        }


def run_processing_pipeline(initial_state: dict) -> dict:
    """Run the full processing pipeline.

    Stub implementation — raises NotImplementedError.
    """
    raise NotImplementedError("Processing pipeline not yet implemented")
