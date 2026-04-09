"""Postprocess node: confidence merging, validation, explanations."""

import logging
import time
import uuid
from datetime import datetime, timezone

from docmind.core.config import get_settings

from .types import AuditEntry

logger = logging.getLogger(__name__)


def _lookup_cv_quality(bounding_box: dict, quality_map: dict, grid_size: int = 4) -> float:
    """Map bounding box center to nearest grid cell in quality map."""
    if not quality_map or not bounding_box:
        return 0.5
    center_y = bounding_box.get("y", 0.5) + bounding_box.get("height", 0) / 2
    center_x = bounding_box.get("x", 0.5) + bounding_box.get("width", 0) / 2
    grid_row = min(int(center_y * grid_size), grid_size - 1)
    grid_col = min(int(center_x * grid_size), grid_size - 1)
    region = quality_map.get(f"{grid_row},{grid_col}")
    return region.get("overall_score", 0.5) if region else 0.5


def _merge_confidence(vlm_confidence: float, cv_quality: float) -> float:
    """Merge VLM confidence with CV quality score."""
    settings = get_settings()
    merged = (vlm_confidence * settings.CONFIDENCE_VLM_WEIGHT) + (cv_quality * settings.CONFIDENCE_CV_WEIGHT)
    return round(max(0.0, min(1.0, merged)), 4)


def _generate_low_confidence_explanation(field: dict, cv_quality: float) -> str | None:
    """Generate human-readable explanation for low-confidence fields."""
    confidence = field.get("confidence", 0.0)
    if confidence >= get_settings().CONFIDENCE_LOW_THRESHOLD:
        return None
    reasons = []
    if field.get("vlm_confidence", 0.0) < 0.5:
        reasons.append("VLM had low confidence in reading this field")
    if cv_quality < 0.4:
        reasons.append("image quality in this region is poor (possible blur or noise)")
    if field.get("is_missing"):
        reasons.append("field was expected but not found in the document")
    if not reasons:
        reasons.append("combined confidence from VLM and image quality is below threshold")
    return "; ".join(reasons)


def _validate_template_fields(fields: list[dict], template_type: str | None) -> list[dict]:
    """Validate fields against template requirements, add missing placeholders."""
    if not template_type:
        return list(fields)

    from docmind.library.templates.loader import get_template_fields
    config = get_template_fields(template_type)
    required_fields = config["required_fields"] if config else []
    found_keys = {f.get("field_key") for f in fields if f.get("field_key")}

    validated = []
    for field in fields:
        updated = {**field}
        if updated.get("field_key") in required_fields:
            updated["is_required"] = True
        validated.append(updated)

    for req_key in required_fields:
        if req_key not in found_keys:
            validated.append({
                "id": str(uuid.uuid4()), "field_type": "key_value",
                "field_key": req_key, "field_value": "", "page_number": 1,
                "bounding_box": {}, "confidence": 0.0, "vlm_confidence": 0.0,
                "cv_quality_score": 0.0, "is_required": True, "is_missing": True,
            })
    return validated


CAPTION_PROMPT = """Describe this image in detail. Include:
- People (appearance, clothing, pose, expression)
- Objects (logos, text, items, accessories)
- Setting (indoor/outdoor, background, lighting)
- Text visible in the image
- Overall context and purpose of the image

Be thorough and specific. Return only the description, no JSON."""


def _generate_image_caption(image) -> str | None:
    """Generate a detailed caption for an image using VLM.

    Args:
        image: OpenCV image array.

    Returns:
        Caption string, or None if generation fails.
    """
    import asyncio
    from docmind.library.providers import get_vlm_provider

    provider = get_vlm_provider()

    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(
            provider.extract(images=[image], prompt=CAPTION_PROMPT)
        )
        return response.get("content", "").strip() or None
    finally:
        loop.close()


def postprocess_node(state: dict) -> dict:
    """Postprocess: merge confidence, validate template, generate explanations.

    Args:
        state: ExtractionState with raw_fields, quality_map, template_type.

    Returns:
        State update with enhanced_fields, comparison_data, audit_entries.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")
    settings = get_settings()

    def _notify(progress: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback("postprocess", progress, message)

    try:
        raw_fields = state.get("raw_fields", [])
        quality_map = state.get("quality_map", {})
        template_type = state.get("template_type")

        _notify(0.65, "Merging confidence scores")

        enhanced_fields = []
        corrected_ids = []

        for field in raw_fields:
            field_id = field.get("id", str(uuid.uuid4()))
            bbox = field.get("bounding_box", {})
            cv_quality = _lookup_cv_quality(bbox, quality_map)
            vlm_conf = field.get("vlm_confidence", field.get("confidence", 0.5))
            merged_conf = _merge_confidence(vlm_conf, cv_quality)

            enhanced = {
                **field, "id": field_id, "confidence": merged_conf,
                "vlm_confidence": vlm_conf, "cv_quality_score": cv_quality,
                "is_required": field.get("is_required", False),
                "is_missing": field.get("is_missing", False),
            }

            if abs(merged_conf - field.get("confidence", 0.0)) > 0.05:
                corrected_ids.append(field_id)
            enhanced_fields.append(enhanced)

        _notify(0.75, "Validating template fields")
        enhanced_fields = _validate_template_fields(enhanced_fields, template_type)

        added_ids = []
        raw_field_ids = {f.get("id") for f in raw_fields}
        for field in enhanced_fields:
            if field.get("is_missing") and field.get("id") not in raw_field_ids:
                added_ids.append(field["id"])

        _notify(0.80, "Generating explanations")
        final_fields = []
        for field in enhanced_fields:
            cv_quality = _lookup_cv_quality(field.get("bounding_box", {}), quality_map)
            explanation = _generate_low_confidence_explanation(field, cv_quality)
            if explanation:
                field = {**field, "low_confidence_reason": explanation}
            final_fields.append(field)

        # Generate image caption for image documents (single page, non-PDF)
        file_type = state.get("file_type", "")
        page_images = state.get("page_images", [])
        if file_type in ("png", "jpg", "jpeg", "webp", "tiff") and page_images:
            _notify(0.90, "Generating image caption")
            try:
                caption = _generate_image_caption(page_images[0])
                if caption:
                    final_fields.append({
                        "id": str(uuid.uuid4()),
                        "field_type": "image_caption",
                        "field_key": "image_description",
                        "field_value": caption,
                        "page_number": 1,
                        "bounding_box": {},
                        "confidence": 0.95,
                        "vlm_confidence": 0.95,
                        "cv_quality_score": 0.0,
                        "is_required": False,
                        "is_missing": False,
                    })
            except Exception as e:
                logger.warning("Caption generation failed: %s", e)

        duration_ms = int((time.time() - start_time) * 1000)
        audit_entry: AuditEntry = {
            "step_name": "postprocess", "step_order": 3,
            "input_summary": {"raw_field_count": len(raw_fields), "quality_regions": len(quality_map)},
            "output_summary": {
                "enhanced_field_count": len(final_fields),
                "corrected_count": len(corrected_ids),
                "added_count": len(added_ids),
                "low_confidence_count": sum(1 for f in final_fields if f.get("confidence", 1.0) < settings.CONFIDENCE_LOW_THRESHOLD),
            },
            "parameters": {
                "vlm_weight": settings.CONFIDENCE_VLM_WEIGHT,
                "cv_weight": settings.CONFIDENCE_CV_WEIGHT,
                "low_confidence_threshold": settings.CONFIDENCE_LOW_THRESHOLD,
            },
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_entries = list(state.get("audit_entries", []))
        existing_entries.append(audit_entry)

        _notify(1.0, "Postprocessing complete")
        return {"enhanced_fields": final_fields, "comparison_data": {"corrected": corrected_ids, "added": added_ids}, "audit_entries": existing_entries}

    except Exception as e:
        logger.error("Postprocessing failed: %s", e, exc_info=True)
        return {"status": "error", "error_message": "Postprocessing failed. See server logs for details."}
