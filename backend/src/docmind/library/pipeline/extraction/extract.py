"""Extract node: VLM extraction with template/general mode."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from docmind.library.providers import get_vlm_provider
from docmind.library.templates.loader import get_template_fields

# Alias for backward compat with tests
_get_template_config = get_template_fields

from .types import AuditEntry

logger = logging.getLogger(__name__)

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


def extract_node(state: dict) -> dict:
    """Extract structured data from document images using VLM.

    Args:
        state: ExtractionState dict with page_images and template_type.

    Returns:
        State update with raw_fields, vlm_response, document_type, audit_entries.
    """
    start_time = time.time()
    progress_callback = state.get("progress_callback")

    def _notify(progress: float, message: str) -> None:
        if progress_callback is not None:
            progress_callback("extract", progress, message)

    try:
        page_images = state["page_images"]
        template_type = state.get("template_type")

        _notify(0.1, "Initializing VLM provider")
        provider = get_vlm_provider()

        # Build prompt
        if template_type:
            config = get_template_fields(template_type)
            if config is None:
                logger.warning("Unknown template type requested: %s", template_type)
                return {"status": "error", "error_message": "Unknown template type. See server logs for details."}
            prompt = TEMPLATE_EXTRACTION_PROMPT.format(
                template_type=template_type,
                required_fields=", ".join(config["required_fields"]),
                optional_fields=", ".join(config["optional_fields"]),
            )
        else:
            prompt = GENERAL_EXTRACTION_PROMPT

        _notify(0.3, "Running VLM extraction")

        async def _run_extraction():
            vlm_resp = await provider.extract(images=page_images, prompt=prompt)
            doc_type = vlm_resp["structured_data"].get("document_type", template_type)

            if not template_type and not doc_type and page_images:
                _notify(0.8, "Classifying document type")
                classify_resp = await provider.classify(image=page_images[0], categories=DOCUMENT_CATEGORIES)
                doc_type = classify_resp["structured_data"].get("document_type", "other")

            return vlm_resp, doc_type

        loop = asyncio.new_event_loop()
        try:
            vlm_response, document_type = loop.run_until_complete(_run_extraction())
        finally:
            loop.close()

        _notify(0.6, "Parsing extraction results")

        structured = vlm_response["structured_data"]
        raw_fields = structured.get("fields", [])

        response_confidence = vlm_response["confidence"]
        raw_fields = [
            {**field, "vlm_confidence": field.get("confidence", response_confidence)}
            for field in raw_fields
        ]

        serialized_vlm = {
            "content": vlm_response.get("content", ""),
            "confidence": vlm_response.get("confidence", 0.0),
            "model": vlm_response.get("model", ""),
            "usage": vlm_response.get("usage", {}),
        }

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
            "parameters": {"provider": provider.provider_name, "model": provider.model_name},
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
        return {"status": "error", "error_message": "Extraction failed. See server logs for details."}
