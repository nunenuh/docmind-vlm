"""
docmind/library/pipeline/processing.py

LangGraph StateGraph for the document processing pipeline.

Nodes: preprocess -> extract -> postprocess -> store.
Each node is a pure function: takes state dict, returns state update dict.
"""

import dataclasses
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict

from docmind.library.cv.deskew import detect_and_correct
from docmind.library.cv.preprocessing import convert_to_page_images
from docmind.library.cv.quality import assess_regions

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


def run_processing_pipeline(initial_state: dict) -> dict:
    """Run the full processing pipeline.

    Stub implementation — raises NotImplementedError.
    """
    raise NotImplementedError("Processing pipeline not yet implemented")
