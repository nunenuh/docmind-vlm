"""Store node: persist extraction results to database."""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from .types import AuditEntry

logger = logging.getLogger(__name__)


async def _persist_results(state: dict, extraction_id: str) -> None:
    """Persist extraction results to the database."""
    from docmind.dbase.psql.core.session import AsyncSessionLocal
    from docmind.dbase.psql.models import (
        AuditEntry as AuditEntryModel,
        Document,
        ExtractedField,
        Extraction,
    )
    from sqlalchemy import update

    document_id = state.get("document_id", "")
    template_type = state.get("template_type")
    mode = "template" if template_type else "general"
    enhanced_fields = state.get("enhanced_fields", [])
    audit_entries = state.get("audit_entries", [])
    processing_time_ms = int((time.time() - state.get("_start_time", time.time())) * 1000)

    async with AsyncSessionLocal() as session:
        extraction = Extraction(
            id=extraction_id, document_id=document_id,
            mode=mode, template_type=template_type,
            processing_time_ms=processing_time_ms,
        )
        session.add(extraction)

        for field in enhanced_fields:
            session.add(ExtractedField(
                extraction_id=extraction_id,
                field_type=field.get("field_type", "key_value"),
                field_key=field.get("field_key"),
                field_value=field.get("field_value") or "",
                page_number=field.get("page_number", 1),
                bounding_box=field.get("bounding_box", {}),
                confidence=field.get("confidence", 0.0),
                vlm_confidence=field.get("vlm_confidence", 0.0),
                cv_quality_score=field.get("cv_quality_score", 0.0),
                is_required=field.get("is_required", False),
                is_missing=field.get("is_missing", False),
            ))

        for entry in audit_entries:
            session.add(AuditEntryModel(
                extraction_id=extraction_id,
                step_name=entry.get("step_name", ""),
                step_order=entry.get("step_order", 0),
                input_summary=entry.get("input_summary", {}),
                output_summary=entry.get("output_summary", {}),
                parameters=entry.get("parameters", {}),
                duration_ms=entry.get("duration_ms", 0),
            ))

        stmt = (
            update(Document).where(Document.id == document_id)
            .values(
                status="ready",
                page_count=state.get("page_count", 0),
                document_type=state.get("document_type"),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.execute(stmt)
        await session.commit()

    logger.info("Persisted extraction %s for document %s", extraction_id, document_id)


def store_node(state: dict) -> dict:
    """Store extraction results to the database.

    Args:
        state: ExtractionState with enhanced_fields, audit_entries, etc.

    Returns:
        State update with extraction_id, status, audit_entries.
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
            "step_name": "store", "step_order": 4,
            "input_summary": {"document_id": state.get("document_id", ""), "field_count": len(state.get("enhanced_fields", []))},
            "output_summary": {"extraction_id": extraction_id},
            "parameters": {},
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        existing_entries = list(state.get("audit_entries", []))
        existing_entries.append(audit_entry)

        _notify(1.0, "Storage complete")
        return {"extraction_id": extraction_id, "status": "ready", "audit_entries": existing_entries}

    except Exception as e:
        logger.error("Storage failed: %s", e, exc_info=True)
        return {"status": "error", "error_message": "Storage failed. See server logs for details."}
