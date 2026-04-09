"""Preprocess node: convert to images, deskew, assess quality."""

import dataclasses
import logging
import time
from datetime import datetime, timezone

from docmind.core.config import get_settings
from docmind.library.cv.deskew import detect_and_correct
from docmind.library.cv.preprocessing import convert_to_page_images
from docmind.library.cv.quality import assess_regions

from .types import AuditEntry

logger = logging.getLogger(__name__)


def _serialize_quality_map(raw_map: dict) -> dict[str, dict]:
    """Serialize quality map from tuple keys to string keys."""
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

    Args:
        state: ExtractionState dict with file_bytes and file_type.

    Returns:
        State update with page_images, page_count, quality_map, skew_angles, audit_entries.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")
    settings = get_settings()

    def _notify(progress: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback("preprocess", progress, message)

    try:
        file_bytes = state["file_bytes"]
        file_type = state["file_type"]

        _notify(0.1, "Converting document to page images")
        raw_images = convert_to_page_images(file_bytes, file_type)

        _notify(0.4, "Correcting page skew")
        corrected_images = []
        skew_angles = []
        for page_img in raw_images:
            corrected, angle = detect_and_correct(page_img, threshold=settings.CV_DESKEW_THRESHOLD)
            corrected_images.append(corrected)
            skew_angles.append(angle)

        _notify(0.7, "Assessing image quality")
        quality_map_raw: dict = {}
        if corrected_images:
            quality_map_raw = assess_regions(corrected_images[0])

        quality_map = _serialize_quality_map(quality_map_raw)

        mean_quality = 0.0
        if quality_map_raw:
            mean_quality = sum(q.overall_score for q in quality_map_raw.values()) / len(quality_map_raw)

        duration_ms = int((time.time() - start_time) * 1000)
        audit_entry: AuditEntry = {
            "step_name": "preprocess",
            "step_order": 1,
            "input_summary": {"file_type": file_type, "file_size_bytes": len(file_bytes)},
            "output_summary": {
                "page_count": len(corrected_images),
                "mean_quality": round(mean_quality, 4),
                "skew_angles": skew_angles,
            },
            "parameters": {
                "deskew_threshold": settings.CV_DESKEW_THRESHOLD,
                "quality_grid": f"{settings.CV_QUALITY_GRID_SIZE}x{settings.CV_QUALITY_GRID_SIZE}",
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
        return {"status": "error", "error_message": f"Preprocessing failed: {e}"}
