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
import uuid
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

TEMPLATE_EXTRACTION_PROMPT = """Analyze this document as a {template_type}.

Extract the following required fields: {required_fields}
Also extract if present: {optional_fields}

For each field, return a JSON object with:
- "field_type": one of "key_value", "table_cell", "entity", "text_block"
- "field_key": the field name from the template
- "field_value": the extracted text value (null if not found)
- "page_number": which page (1-indexed)
- "bounding_box": {{"x": float, "y": float, "width": float, "height": float}} as ratios of page dimensions (0.0-1.0)
- "confidence": your confidence in this extraction (0.0-1.0)
- "is_required": true if this is a required field
- "is_missing": true if the field was not found in the document

Return a JSON object: {{"fields": [...], "document_type": "{template_type}"}}
"""

DOCUMENT_CATEGORIES = [
    "invoice", "receipt", "medical_report", "contract",
    "id_document", "letter", "form", "other",
]


def _get_template_config(template_type: str) -> dict | None:
    """Get template configuration for a given template type.

    Args:
        template_type: Template name (e.g. "invoice", "receipt").

    Returns:
        Dict with required_fields and optional_fields lists,
        or None if template_type is unknown.
    """
    templates = {
        "invoice": {
            "required_fields": ["invoice_number", "date", "total_amount", "vendor_name"],
            "optional_fields": ["due_date", "tax_amount", "line_items", "purchase_order"],
        },
        "receipt": {
            "required_fields": ["date", "total_amount", "merchant_name"],
            "optional_fields": ["tax_amount", "payment_method", "line_items"],
        },
        "medical_report": {
            "required_fields": ["patient_name", "report_date", "report_type"],
            "optional_fields": ["doctor_name", "diagnosis", "test_results", "facility"],
        },
        "contract": {
            "required_fields": ["parties", "effective_date", "contract_type"],
            "optional_fields": ["expiry_date", "terms", "signatures", "governing_law"],
        },
        "id_document": {
            "required_fields": ["full_name", "document_number", "date_of_birth"],
            "optional_fields": ["expiry_date", "nationality", "address", "issuing_authority"],
        },
    }
    return templates.get(template_type)


def extract_node(state: dict) -> dict:
    """Extract structured data from document images using VLM.

    In general mode (no template), uses GENERAL_EXTRACTION_PROMPT.
    In template mode, uses TEMPLATE_EXTRACTION_PROMPT with required/optional fields.
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
        if template_type:
            config = _get_template_config(template_type)
            if config is None:
                logger.warning("Unknown template type requested: %s", template_type)
                return {
                    "status": "error",
                    "error_message": "Unknown template type. See server logs for details.",
                }
            prompt = TEMPLATE_EXTRACTION_PROMPT.format(
                template_type=template_type,
                required_fields=", ".join(config["required_fields"]),
                optional_fields=", ".join(config["optional_fields"]),
            )
        else:
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


CONFIDENCE_VLM_WEIGHT = 0.7
CONFIDENCE_CV_WEIGHT = 0.3
LOW_CONFIDENCE_THRESHOLD = 0.5


def _lookup_cv_quality(
    bounding_box: dict,
    quality_map: dict,
    page_height: int = 4,
    page_width: int = 4,
) -> float:
    """Map bounding box center to nearest grid cell in quality map.

    Args:
        bounding_box: Dict with x, y, width, height as ratios (0.0-1.0).
        quality_map: Dict mapping "row,col" strings to quality dicts.
        page_height: Number of grid rows.
        page_width: Number of grid columns.

    Returns:
        Overall quality score for the grid cell, or 0.5 as fallback.
    """
    if not quality_map or not bounding_box:
        return 0.5
    center_y = bounding_box.get("y", 0.5) + bounding_box.get("height", 0) / 2
    center_x = bounding_box.get("x", 0.5) + bounding_box.get("width", 0) / 2
    grid_row = min(int(center_y * page_height), page_height - 1)
    grid_col = min(int(center_x * page_width), page_width - 1)
    key = f"{grid_row},{grid_col}"
    region = quality_map.get(key)
    if region is None:
        return 0.5
    return region.get("overall_score", 0.5)


def _merge_confidence(vlm_confidence: float, cv_quality: float) -> float:
    """Merge VLM confidence with CV quality score.

    Formula: final = vlm * 0.7 + cv * 0.3, clamped to [0.0, 1.0].

    Args:
        vlm_confidence: VLM extraction confidence (0.0-1.0).
        cv_quality: CV region quality score (0.0-1.0).

    Returns:
        Merged confidence rounded to 4 decimal places.
    """
    merged = (vlm_confidence * CONFIDENCE_VLM_WEIGHT) + (cv_quality * CONFIDENCE_CV_WEIGHT)
    return round(max(0.0, min(1.0, merged)), 4)


def _generate_low_confidence_explanation(
    field: dict, cv_quality: float
) -> str | None:
    """Generate human-readable explanation for low-confidence fields.

    Args:
        field: Enhanced field dict with confidence, vlm_confidence, is_missing.
        cv_quality: CV quality score for this field's region.

    Returns:
        Explanation string if confidence < threshold, None otherwise.
    """
    confidence = field.get("confidence", 0.0)
    if confidence >= LOW_CONFIDENCE_THRESHOLD:
        return None
    reasons = []
    vlm_conf = field.get("vlm_confidence", 0.0)
    if vlm_conf < 0.5:
        reasons.append("VLM had low confidence in reading this field")
    if cv_quality < 0.4:
        reasons.append(
            "image quality in this region is poor (possible blur or noise)"
        )
    if field.get("is_missing"):
        reasons.append("field was expected but not found in the document")
    if not reasons:
        reasons.append(
            "combined confidence from VLM and image quality is below threshold"
        )
    return "; ".join(reasons)


def _validate_template_fields(
    fields: list[dict], template_type: str | None
) -> list[dict]:
    """Validate extracted fields against template requirements.

    Adds missing required fields as placeholder entries with
    confidence=0.0, is_missing=True, is_required=True.

    Args:
        fields: List of enhanced field dicts.
        template_type: Template name, or None for general mode.

    Returns:
        Validated list of field dicts (new list, no mutation).
    """
    if not template_type:
        return list(fields)

    required_map = {
        "invoice": ["invoice_number", "date", "total_amount", "vendor_name"],
        "receipt": ["date", "total_amount", "merchant_name"],
        "medical_report": ["patient_name", "report_date", "report_type"],
        "contract": ["parties", "effective_date", "contract_type"],
        "id_document": ["full_name", "document_number", "date_of_birth"],
    }
    required_fields = required_map.get(template_type, [])
    found_keys = {f.get("field_key") for f in fields if f.get("field_key")}

    validated_fields = []
    for field in fields:
        updated = {**field}
        if updated.get("field_key") in required_fields:
            updated["is_required"] = True
        validated_fields.append(updated)

    for req_key in required_fields:
        if req_key not in found_keys:


            validated_fields.append({
                "id": str(uuid.uuid4()),
                "field_type": "key_value",
                "field_key": req_key,
                "field_value": "",
                "page_number": 1,
                "bounding_box": {},
                "confidence": 0.0,
                "vlm_confidence": 0.0,
                "cv_quality_score": 0.0,
                "is_required": True,
                "is_missing": True,
            })
    return validated_fields


def postprocess_node(state: dict) -> dict:
    """Postprocess extraction results: merge confidence, validate, explain.

    Steps:
    1. Merge VLM confidence with CV quality score per field
    2. Validate against template (if template mode)
    3. Generate explanations for low-confidence fields
    4. Build comparison data (enhanced vs raw)
    5. Record audit entry

    Args:
        state: ProcessingState dict with raw_fields, quality_map, template_type.

    Returns:
        State update dict with enhanced_fields, comparison_data, audit_entries.
        On error, returns status='error' with error_message.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")

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
            vlm_conf = field.get(
                "vlm_confidence", field.get("confidence", 0.5)
            )
            merged_conf = _merge_confidence(vlm_conf, cv_quality)

            enhanced = {
                **field,
                "id": field_id,
                "confidence": merged_conf,
                "vlm_confidence": vlm_conf,
                "cv_quality_score": cv_quality,
                "is_required": field.get("is_required", False),
                "is_missing": field.get("is_missing", False),
            }

            original_conf = field.get("confidence", 0.0)
            if abs(merged_conf - original_conf) > 0.05:
                corrected_ids.append(field_id)

            enhanced_fields.append(enhanced)

        _notify(0.75, "Validating template fields")

        enhanced_fields = _validate_template_fields(enhanced_fields, template_type)

        # Track added fields (from template validation)
        added_ids = []
        raw_field_ids = {f.get("id") for f in raw_fields}
        for field in enhanced_fields:
            if field.get("is_missing") and field.get("id") not in raw_field_ids:
                added_ids.append(field["id"])

        _notify(0.80, "Generating explanations")

        # Generate explanations for low-confidence fields (immutable)
        final_fields = []
        for field in enhanced_fields:
            bbox = field.get("bounding_box", {})
            cv_quality = _lookup_cv_quality(bbox, quality_map)
            explanation = _generate_low_confidence_explanation(field, cv_quality)
            if explanation:
                field = {**field, "low_confidence_reason": explanation}
            final_fields.append(field)

        comparison_data = {
            "corrected": corrected_ids,
            "added": added_ids,
        }

        duration_ms = int((time.time() - start_time) * 1000)

        audit_entry: AuditEntry = {
            "step_name": "postprocess",
            "step_order": 3,
            "input_summary": {
                "raw_field_count": len(raw_fields),
                "quality_regions": len(quality_map),
            },
            "output_summary": {
                "enhanced_field_count": len(final_fields),
                "corrected_count": len(corrected_ids),
                "added_count": len(added_ids),
                "low_confidence_count": sum(
                    1 for f in final_fields
                    if f.get("confidence", 1.0) < LOW_CONFIDENCE_THRESHOLD
                ),
            },
            "parameters": {
                "vlm_weight": CONFIDENCE_VLM_WEIGHT,
                "cv_weight": CONFIDENCE_CV_WEIGHT,
                "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
            },
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_entries = list(state.get("audit_entries", []))
        existing_entries.append(audit_entry)

        _notify(1.0, "Postprocessing complete")

        return {
            "enhanced_fields": final_fields,
            "comparison_data": comparison_data,
            "audit_entries": existing_entries,
        }

    except Exception as e:
        logger.error("Postprocessing failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_message": "Postprocessing failed. See server logs for details.",
        }


async def _persist_results(state: dict, extraction_id: str) -> None:
    """Persist extraction results to the database.

    Stub — will be implemented when DB layer is wired up.
    Currently a no-op placeholder that tests can mock.

    Args:
        state: ProcessingState dict with enhanced_fields, audit_entries, etc.
        extraction_id: UUID string for the new extraction record.
    """
    logger.info(
        "Persisting extraction %s for document %s (stub)",
        extraction_id,
        state.get("document_id"),
    )


def store_node(state: dict) -> dict:
    """Store extraction results to the database.

    Generates a new extraction_id, persists results via _persist_results,
    and sets pipeline status to 'ready'.

    Args:
        state: ProcessingState dict with enhanced_fields, audit_entries, etc.

    Returns:
        State update dict with extraction_id, status, audit_entries.
        On error, returns status='error' with error_message.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")

    def _notify(progress: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback("store", progress, message)

    try:


        extraction_id = str(uuid.uuid4())

        _notify(0.9, "Persisting extraction results")

        asyncio.run(_persist_results(state, extraction_id))

        duration_ms = int((time.time() - start_time) * 1000)

        audit_entry: AuditEntry = {
            "step_name": "store",
            "step_order": 4,
            "input_summary": {
                "document_id": state.get("document_id", ""),
                "field_count": len(state.get("enhanced_fields", [])),
            },
            "output_summary": {
                "extraction_id": extraction_id,
            },
            "parameters": {},
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_entries = list(state.get("audit_entries", []))
        existing_entries.append(audit_entry)

        _notify(1.0, "Storage complete")

        return {
            "extraction_id": extraction_id,
            "status": "ready",
            "audit_entries": existing_entries,
        }

    except Exception as e:
        logger.error("Storage failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "error_message": "Storage failed. See server logs for details.",
        }


def should_continue(state: dict) -> str:
    """Conditional edge function for the processing graph.

    Returns "end" if the pipeline has errored, "continue" otherwise.
    """
    if state.get("status") == "error":
        return "end"
    return "continue"


def build_processing_graph():
    """Build and compile the LangGraph processing pipeline.

    Graph: preprocess -> extract -> postprocess -> store
    Each node has a conditional edge that short-circuits to END on error.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(ProcessingState)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("extract", extract_node)
    graph.add_node("postprocess", postprocess_node)
    graph.add_node("store", store_node)
    graph.set_entry_point("preprocess")
    graph.add_conditional_edges(
        "preprocess", should_continue, {"continue": "extract", "end": END}
    )
    graph.add_conditional_edges(
        "extract", should_continue, {"continue": "postprocess", "end": END}
    )
    graph.add_conditional_edges(
        "postprocess", should_continue, {"continue": "store", "end": END}
    )
    graph.add_edge("store", END)
    return graph.compile()


processing_graph = build_processing_graph()


def run_processing_pipeline(initial_state: dict) -> dict:
    """Run the full processing pipeline.

    Invokes the compiled LangGraph with the given initial state.

    Args:
        initial_state: ProcessingState dict with document data.

    Returns:
        Final state dict after all nodes have executed.
    """
    return processing_graph.invoke(initial_state)
