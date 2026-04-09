# Backend Spec: Document Processing Pipeline

File: `backend/src/docmind/library/pipeline/processing.py`

Library dependencies: `backend/src/docmind/library/cv/` · `backend/src/docmind/library/providers/`

See also: [[projects/docmind-vlm/specs/backend/cv]] · [[projects/docmind-vlm/specs/backend/providers]] · [[projects/docmind-vlm/specs/backend/services]]

---

## Responsibility

| Component | Does |
|-----------|------|
| `docmind/library/pipeline/processing.py` | LangGraph StateGraph definition — nodes, edges, state schema |
| `preprocess_node` (in same file) | Node: PDF/image to normalized pages + deskew + quality map |
| `extract_node` (in same file) | Node: VLM extraction (general or template mode) |
| `postprocess_node` (in same file) | Node: confidence merging, template validation, low-confidence explanations |
| `store_node` (in same file) | Node: persist extraction results and audit trail to Supabase |

The pipeline **never** imports from `docmind/modules/` — it communicates through state and callbacks only. It lives under `library/pipeline/` because it is reusable logic, invoked by `modules/documents/usecase.py`.

---

## Imports

```python
# From module usecase or service layer:
from docmind.library.pipeline import run_processing_pipeline

# Internal imports within pipeline:
from docmind.library.cv import deskew_image, assess_quality, convert_to_page_images
from docmind.library.providers import get_vlm_provider
from docmind.dbase.supabase.client import get_supabase_client
from docmind.core.config import get_settings
from docmind.core.logging import get_logger
```

---

## Pipeline Overview

```
DocumentFile (bytes + metadata)
    |
    v  preprocess node
page_images: list[ndarray], quality_map: dict, skew_angles: list[float]
    |
    v  extract node
raw_fields: list[dict], vlm_response: VLMResponse, document_type: str
    |
    v  postprocess node
enhanced_fields: list[dict] (confidence merged, validated, explained)
    |
    v  store node
extraction_id: str (persisted to Supabase)
    |
    v
ProcessingState.status = "ready"
```

---

## `library/pipeline/processing.py`

```python
"""
docmind/library/pipeline/processing.py

LangGraph StateGraph for the document processing pipeline.

Defines the processing state schema and wires together the four
pipeline nodes: preprocess -> extract -> postprocess -> store.
"""
import logging
from datetime import datetime
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class AuditEntry(TypedDict):
    """Single audit trail entry recorded by each pipeline node."""
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int
    timestamp: str


class ProcessingState(TypedDict):
    """
    Full state flowing through the processing pipeline.

    Each node reads what it needs and writes its outputs.
    State is immutable per convention — nodes return new dicts,
    LangGraph merges them into the next state.
    """
    # Input (set before pipeline starts)
    document_id: str
    user_id: str
    file_bytes: bytes
    file_type: str
    template_type: str | None

    # Preprocess outputs
    page_images: list[Any]  # list[np.ndarray] — Any to avoid numpy in TypedDict
    page_count: int
    quality_map: dict  # {(row, col): RegionQuality} serialized
    skew_angles: list[float]

    # Extract outputs
    raw_fields: list[dict]
    vlm_response: dict  # Serialized VLMResponse
    document_type: str | None

    # Postprocess outputs
    enhanced_fields: list[dict]
    comparison_data: dict  # {corrected: [...], added: [...]}

    # Store outputs
    extraction_id: str

    # Pipeline metadata
    status: str  # processing, ready, error
    error_message: str | None
    audit_entries: list[AuditEntry]
    progress_callback: Callable | None  # SSE callback


def should_continue(state: ProcessingState) -> str:
    """
    Conditional edge: stop pipeline on error, continue otherwise.

    Returns:
        "end" if status is "error", next node name otherwise.
    """
    if state.get("status") == "error":
        return "end"
    return "continue"


def build_processing_graph() -> StateGraph:
    """
    Build and compile the document processing StateGraph.

    Pipeline flow:
        preprocess -> extract -> postprocess -> store -> END

    Each transition checks for errors. If any node sets
    status="error", the pipeline short-circuits to END.

    Returns:
        Compiled LangGraph StateGraph ready for invocation.
    """
    graph = StateGraph(ProcessingState)

    # Add nodes
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("extract", extract_node)
    graph.add_node("postprocess", postprocess_node)
    graph.add_node("store", store_node)

    # Set entry point
    graph.set_entry_point("preprocess")

    # Add conditional edges (error checking after each node)
    graph.add_conditional_edges(
        "preprocess",
        should_continue,
        {"continue": "extract", "end": END},
    )
    graph.add_conditional_edges(
        "extract",
        should_continue,
        {"continue": "postprocess", "end": END},
    )
    graph.add_conditional_edges(
        "postprocess",
        should_continue,
        {"continue": "store", "end": END},
    )
    graph.add_edge("store", END)

    return graph.compile()


# Module-level compiled graph (reused across invocations)
processing_graph = build_processing_graph()


def run_processing_pipeline(initial_state: dict) -> dict:
    """
    Run the full processing pipeline.

    This is the main entry point called by modules/documents/usecase.py.

    Args:
        initial_state: ProcessingState dict with input fields populated.

    Returns:
        Final ProcessingState dict with all outputs.
    """
    return processing_graph.invoke(initial_state)
```

---

## `preprocess_node`

```python
"""
Preprocess node: convert document to images, deskew, assess quality.

Calls into the library/cv/ module for all image operations.
"""
import time

from docmind.library.cv.preprocessing import convert_to_page_images
from docmind.library.cv.deskew import detect_and_correct
from docmind.library.cv.quality import assess_regions


def preprocess_node(state: dict) -> dict:
    """
    Pipeline node: preprocess document images.

    Steps:
    1. Convert PDF/image bytes to page images (library/cv/preprocessing.py)
    2. Deskew each page if needed (library/cv/deskew.py)
    3. Assess quality per region grid (library/cv/quality.py)
    4. Record audit entry

    Args:
        state: ProcessingState dict.

    Returns:
        State updates: page_images, page_count, quality_map,
        skew_angles, audit_entries.
    """
    start = time.time()
    callback = state.get("progress_callback")

    if callback:
        callback(step="preprocess", progress=5, message="Converting document to images...")

    try:
        # Step 1: Convert to page images
        raw_images = convert_to_page_images(
            file_bytes=state["file_bytes"],
            file_type=state["file_type"],
        )

        if callback:
            callback(step="preprocess", progress=10, message="Deskewing pages...")

        # Step 2: Deskew each page
        corrected_images = []
        skew_angles = []
        for page_img in raw_images:
            corrected, angle = detect_and_correct(page_img)
            corrected_images.append(corrected)
            skew_angles.append(angle)

        if callback:
            callback(step="preprocess", progress=20, message="Assessing image quality...")

        # Step 3: Quality assessment on first page (representative)
        quality_map = {}
        if corrected_images:
            raw_quality = assess_regions(corrected_images[0])
            # Serialize tuple keys to strings for JSON compatibility
            quality_map = {
                f"{row},{col}": {
                    "blur_score": q.blur_score,
                    "noise_score": q.noise_score,
                    "contrast_score": q.contrast_score,
                    "overall_score": q.overall_score,
                }
                for (row, col), q in raw_quality.items()
            }

        duration_ms = int((time.time() - start) * 1000)

        audit_entry = {
            "step_name": "preprocess",
            "step_order": 1,
            "input_summary": {
                "file_type": state["file_type"],
                "file_size_bytes": len(state["file_bytes"]),
            },
            "output_summary": {
                "page_count": len(corrected_images),
                "skew_angles": skew_angles,
                "mean_quality": (
                    sum(q["overall_score"] for q in quality_map.values()) / len(quality_map)
                    if quality_map else 0.0
                ),
            },
            "parameters": {"deskew_threshold": 2.0, "quality_grid": "4x4"},
            "duration_ms": duration_ms,
        }

        if callback:
            callback(step="preprocess", progress=25, message="Preprocessing complete")

        return {
            "page_images": corrected_images,
            "page_count": len(corrected_images),
            "quality_map": quality_map,
            "skew_angles": skew_angles,
            "audit_entries": state.get("audit_entries", []) + [audit_entry],
        }

    except Exception as e:
        logger.error("Preprocess failed: %s", e)
        return {
            "status": "error",
            "error_message": f"Preprocessing failed: {e}",
        }
```

---

## `extract_node`

```python
"""
Extract node: call VLM provider for document extraction.

Constructs appropriate prompts for general vs template mode,
calls the configured VLM provider, and parses the response
into a list of raw extracted fields.
"""
import json
import time

from docmind.library.providers import get_vlm_provider

# General extraction prompt (no template)
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

# Template-specific extraction prompt
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


def _get_template_config(template_type: str) -> dict | None:
    """Get template configuration for a given template type."""
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
    """
    Pipeline node: VLM extraction.

    Steps:
    1. Build extraction prompt (general or template-specific)
    2. Call VLM provider with page images
    3. Optionally classify document type (general mode only)
    4. Parse response into raw field list
    5. Record audit entry
    """
    start = time.time()
    callback = state.get("progress_callback")

    if callback:
        callback(step="extract", progress=30, message="Preparing VLM extraction...")

    try:
        provider = get_vlm_provider()
        page_images = state["page_images"]
        template_type = state.get("template_type")

        # Build prompt
        if template_type:
            config = _get_template_config(template_type)
            if config is None:
                return {
                    "status": "error",
                    "error_message": f"Unknown template type: {template_type}",
                }
            prompt = TEMPLATE_EXTRACTION_PROMPT.format(
                template_type=template_type,
                required_fields=", ".join(config["required_fields"]),
                optional_fields=", ".join(config["optional_fields"]),
            )
        else:
            prompt = GENERAL_EXTRACTION_PROMPT

        if callback:
            callback(step="extract", progress=40, message="Running VLM extraction...")

        # Call VLM provider
        import asyncio
        vlm_response = asyncio.get_event_loop().run_until_complete(
            provider.extract(images=page_images, prompt=prompt)
        )

        if callback:
            callback(step="extract", progress=55, message="Parsing extraction results...")

        # Parse fields from VLM response
        structured = vlm_response["structured_data"]
        raw_fields = structured.get("fields", [])
        document_type = structured.get("document_type", template_type)

        # Classify document type if not template mode and not detected
        if not template_type and not document_type and page_images:
            categories = ["invoice", "receipt", "medical_report", "contract", "id_document", "letter", "form", "other"]
            classify_response = asyncio.get_event_loop().run_until_complete(
                provider.classify(image=page_images[0], categories=categories)
            )
            document_type = classify_response["structured_data"].get("document_type", "other")

        # Attach VLM confidence to each field
        for field in raw_fields:
            field["vlm_confidence"] = field.get("confidence", vlm_response["confidence"])

        duration_ms = int((time.time() - start) * 1000)

        audit_entry = {
            "step_name": "extract",
            "step_order": 2,
            "input_summary": {
                "page_count": len(page_images),
                "mode": "template" if template_type else "general",
                "template_type": template_type,
            },
            "output_summary": {
                "field_count": len(raw_fields),
                "document_type": document_type,
                "vlm_model": vlm_response["model"],
            },
            "parameters": {
                "provider": provider.provider_name,
                "model": provider.model_name,
            },
            "duration_ms": duration_ms,
        }

        if callback:
            callback(step="extract", progress=60, message="Extraction complete")

        return {
            "raw_fields": raw_fields,
            "vlm_response": {
                "content": vlm_response["content"],
                "confidence": vlm_response["confidence"],
                "model": vlm_response["model"],
                "usage": vlm_response["usage"],
            },
            "document_type": document_type,
            "audit_entries": state.get("audit_entries", []) + [audit_entry],
        }

    except Exception as e:
        logger.error("Extract failed: %s", e)
        return {
            "status": "error",
            "error_message": f"Extraction failed: {e}",
        }
```

---

## `postprocess_node`

```python
"""
Postprocess node: merge confidence scores, validate against template,
generate explanations for low-confidence fields.

The confidence merging formula combines VLM confidence with CV quality:
    final_confidence = vlm_confidence * 0.7 + cv_quality_score * 0.3
"""
import time
import uuid

CONFIDENCE_VLM_WEIGHT = 0.7
CONFIDENCE_CV_WEIGHT = 0.3
LOW_CONFIDENCE_THRESHOLD = 0.5


def _lookup_cv_quality(bounding_box: dict, quality_map: dict, page_height: int = 4, page_width: int = 4) -> float:
    """Map bounding box center to nearest grid cell in quality map. Returns 0.5 as fallback."""
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
    """Merge VLM confidence with CV quality score. Formula: final = vlm * 0.7 + cv * 0.3"""
    merged = (vlm_confidence * CONFIDENCE_VLM_WEIGHT) + (cv_quality * CONFIDENCE_CV_WEIGHT)
    return round(max(0.0, min(1.0, merged)), 4)


def _generate_low_confidence_explanation(field: dict, cv_quality: float) -> str | None:
    """Generate human-readable explanation for low-confidence fields."""
    confidence = field.get("confidence", 0.0)
    if confidence >= LOW_CONFIDENCE_THRESHOLD:
        return None
    reasons = []
    vlm_conf = field.get("vlm_confidence", 0.0)
    if vlm_conf < 0.5:
        reasons.append("VLM had low confidence in reading this field")
    if cv_quality < 0.4:
        reasons.append("image quality in this region is poor (possible blur or noise)")
    if field.get("is_missing"):
        reasons.append("field was expected but not found in the document")
    if not reasons:
        reasons.append("combined confidence from VLM and image quality is below threshold")
    return "; ".join(reasons)


def _validate_template_fields(fields: list[dict], template_type: str | None) -> list[dict]:
    """Validate extracted fields against template requirements. Adds missing required fields as placeholders."""
    if not template_type:
        return fields
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
    """
    Pipeline node: postprocess extraction results.

    Steps:
    1. Merge VLM confidence with CV quality score per field
    2. Validate against template (if template mode)
    3. Generate explanations for low-confidence fields
    4. Build comparison data (enhanced vs raw)
    5. Record audit entry
    """
    start = time.time()
    callback = state.get("progress_callback")

    if callback:
        callback(step="postprocess", progress=65, message="Merging confidence scores...")

    try:
        raw_fields = state.get("raw_fields", [])
        quality_map = state.get("quality_map", {})
        template_type = state.get("template_type")

        enhanced_fields = []
        corrected_ids = []
        added_ids = []

        for field in raw_fields:
            field_id = field.get("id", str(uuid.uuid4()))
            bbox = field.get("bounding_box", {})
            cv_quality = _lookup_cv_quality(bbox, quality_map)
            vlm_conf = field.get("vlm_confidence", field.get("confidence", 0.5))
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

        if callback:
            callback(step="postprocess", progress=75, message="Validating template fields...")

        enhanced_fields = _validate_template_fields(enhanced_fields, template_type)

        for field in enhanced_fields:
            if field.get("is_missing") and field["id"] not in [f.get("id") for f in raw_fields]:
                added_ids.append(field["id"])

        if callback:
            callback(step="postprocess", progress=80, message="Generating explanations...")

        for field in enhanced_fields:
            bbox = field.get("bounding_box", {})
            cv_quality = _lookup_cv_quality(bbox, quality_map)
            explanation = _generate_low_confidence_explanation(field, cv_quality)
            if explanation:
                field["low_confidence_reason"] = explanation

        comparison_data = {
            "corrected": corrected_ids,
            "added": added_ids,
        }

        duration_ms = int((time.time() - start) * 1000)

        audit_entry = {
            "step_name": "postprocess",
            "step_order": 3,
            "input_summary": {
                "raw_field_count": len(raw_fields),
                "quality_regions": len(quality_map),
            },
            "output_summary": {
                "enhanced_field_count": len(enhanced_fields),
                "corrected_count": len(corrected_ids),
                "added_count": len(added_ids),
                "low_confidence_count": sum(
                    1 for f in enhanced_fields
                    if f.get("confidence", 1.0) < LOW_CONFIDENCE_THRESHOLD
                ),
            },
            "parameters": {
                "vlm_weight": CONFIDENCE_VLM_WEIGHT,
                "cv_weight": CONFIDENCE_CV_WEIGHT,
                "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
            },
            "duration_ms": duration_ms,
        }

        if callback:
            callback(step="postprocess", progress=85, message="Postprocessing complete")

        return {
            "enhanced_fields": enhanced_fields,
            "comparison_data": comparison_data,
            "audit_entries": state.get("audit_entries", []) + [audit_entry],
        }

    except Exception as e:
        logger.error("Postprocess failed: %s", e)
        return {
            "status": "error",
            "error_message": f"Postprocessing failed: {e}",
        }
```

---

## `store_node`

```python
"""
Store node: persist extraction results and audit trail to database.

Uses SQLAlchemy async sessions for all database operations.
Note: This node runs in a sync context (via asyncio.to_thread from usecase),
so it uses asyncio.run() to execute async DB calls.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone

from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    AuditEntry as AuditEntryModel,
    Document,
    ExtractedField,
    Extraction,
)
from sqlalchemy import update


async def _persist_results(state: dict, extraction_id: str) -> None:
    """Async helper to persist all results in a single transaction."""
    document_id = state["document_id"]
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # Step 1: Insert extraction record
        extraction = Extraction(
            id=uuid.UUID(extraction_id),
            document_id=document_id,
            mode="template" if state.get("template_type") else "general",
            template_type=state.get("template_type"),
            processing_time_ms=0,  # Updated at end
            created_at=now,
        )
        session.add(extraction)

        # Step 2: Insert extracted fields
        for field in state.get("enhanced_fields", []):
            ef = ExtractedField(
                id=uuid.UUID(field.get("id", str(uuid.uuid4()))),
                extraction_id=uuid.UUID(extraction_id),
                field_type=field.get("field_type", "text_block"),
                field_key=field.get("field_key"),
                field_value=field.get("field_value", ""),
                page_number=field.get("page_number", 1),
                bounding_box=field.get("bounding_box", {}),
                confidence=field.get("confidence", 0.0),
                vlm_confidence=field.get("vlm_confidence", 0.0),
                cv_quality_score=field.get("cv_quality_score", 0.0),
                is_required=field.get("is_required", False),
                is_missing=field.get("is_missing", False),
            )
            session.add(ef)

        # Step 3: Insert audit trail
        for entry in state.get("audit_entries", []):
            ae = AuditEntryModel(
                extraction_id=uuid.UUID(extraction_id),
                step_name=entry["step_name"],
                step_order=entry["step_order"],
                input_summary=entry["input_summary"],
                output_summary=entry["output_summary"],
                parameters=entry["parameters"],
                duration_ms=entry["duration_ms"],
            )
            session.add(ae)

        # Step 4: Update document status
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(
                status="ready",
                document_type=state.get("document_type"),
                page_count=state.get("page_count", 0),
                updated_at=now,
            )
        )
        await session.execute(stmt)
        await session.commit()


def store_node(state: dict) -> dict:
    """
    Pipeline node: persist results to database.

    Steps:
    1. Insert extraction record
    2. Insert all enhanced fields
    3. Insert audit trail entries
    4. Update document status to "ready"
    5. Record audit entry
    """
    start = time.time()
    callback = state.get("progress_callback")

    if callback:
        callback(step="store", progress=90, message="Saving extraction results...")

    try:
        extraction_id = str(uuid.uuid4())

        # Run async DB operations
        asyncio.run(_persist_results(state, extraction_id))

        duration_ms = int((time.time() - start) * 1000)

        audit_entry = {
            "step_name": "store",
            "step_order": 4,
            "input_summary": {
                "field_count": len(state.get("enhanced_fields", [])),
                "audit_entry_count": len(state.get("audit_entries", [])),
            },
            "output_summary": {
                "extraction_id": extraction_id,
                "document_status": "ready",
            },
            "parameters": {"database": "sqlalchemy"},
            "duration_ms": duration_ms,
        }

        if callback:
            callback(step="store", progress=100, message="Processing complete")

        return {
            "extraction_id": extraction_id,
            "status": "ready",
            "audit_entries": state.get("audit_entries", []) + [audit_entry],
        }

    except Exception as e:
        logger.error("Store failed: %s", e)
        return {
            "status": "error",
            "error_message": f"Storage failed: {e}",
        }
```

---

## SSE Progress Callback Pattern

Each pipeline node receives an optional `progress_callback` in state. The callback signature:

```python
def progress_callback(step: str, progress: int, message: str) -> None:
    """
    Report progress to the SSE stream.

    Args:
        step: Current pipeline step name.
        progress: Percentage complete (0-100).
        message: Human-readable status message.
    """
```

The usecase layer creates this callback and connects it to the SSE generator:

```python
import asyncio
import json
from typing import AsyncGenerator


async def create_sse_stream(document_id: str, template_type: str | None) -> AsyncGenerator[str, None]:
    """Create an SSE stream connected to the processing pipeline."""
    progress_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(step: str, progress: int, message: str) -> None:
        progress_queue.put_nowait({"step": step, "progress": progress, "message": message})

    # Run pipeline in background
    from docmind.library.pipeline import run_processing_pipeline

    initial_state = {
        "document_id": document_id,
        "template_type": template_type,
        "progress_callback": on_progress,
        # ... other state fields
    }

    task = asyncio.create_task(asyncio.to_thread(run_processing_pipeline, initial_state))

    while not task.done():
        try:
            event = await asyncio.wait_for(progress_queue.get(), timeout=30.0)
            yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'step': 'heartbeat', 'progress': -1, 'message': 'alive'})}\n\n"

    # Drain remaining events
    while not progress_queue.empty():
        event = progress_queue.get_nowait()
        yield f"data: {json.dumps(event)}\n\n"
```

---

## State Flow Summary

| Node | Reads from state | Writes to state |
|------|-----------------|-----------------|
| **preprocess** | `file_bytes`, `file_type` | `page_images`, `page_count`, `quality_map`, `skew_angles` |
| **extract** | `page_images`, `template_type` | `raw_fields`, `vlm_response`, `document_type` |
| **postprocess** | `raw_fields`, `quality_map`, `template_type` | `enhanced_fields`, `comparison_data` |
| **store** | `document_id`, `enhanced_fields`, `audit_entries`, `document_type`, `page_count` | `extraction_id`, `status` |

---

## Rules

- **Pipeline never imports from `docmind/modules/`** — communication is through state and callbacks only.
- **Each node returns a new dict** — LangGraph merges it into the next state. Never mutate state.
- **Error handling**: any node that catches an exception must set `status="error"` and `error_message` in the returned dict. The `should_continue` edge function routes to END on error.
- **Audit entries accumulate**: each node appends to the `audit_entries` list by creating a new list (`state.get("audit_entries", []) + [new_entry]`).
- **All DB writes use SQLAlchemy** — the store node uses async sessions via `asyncio.run()` since it runs in a sync thread context.
- **Progress callbacks are optional** — nodes must check `if callback` before calling.
