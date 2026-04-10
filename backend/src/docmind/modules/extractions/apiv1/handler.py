"""
docmind/modules/extractions/apiv1/handler.py

Extraction HTTP endpoints — trigger processing, classify, read results.
"""

import csv
import io
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from docmind.core.scopes import require_scopes
from docmind.core.logging import get_logger
from docmind.shared.exceptions import AppException, BaseAppException

from ..dependencies import (
    get_extraction_process_usecase,
    get_extraction_results_usecase,
)
from ..schemas import (
    AuditEntryResponse,
    ClassifyRequest,
    ClassifyResponse,
    ComparisonResponse,
    ExtractionResponse,
    OverlayRegion,
    ProcessRequest,
)
from ..usecases import ExtractionProcessUseCase, ExtractionResultsUseCase

logger = get_logger(__name__)
router = APIRouter()


# ── Trigger Extraction ────────────────────────────────────


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    body: ProcessRequest,
    current_user: dict = Depends(require_scopes("extractions:write")),
    usecase: ExtractionProcessUseCase = Depends(get_extraction_process_usecase),
):
    """Trigger extraction pipeline for a document (SSE stream)."""
    event_stream = usecase.trigger_processing(
        document_id=document_id,
        user_id=current_user["id"],
        template_type=body.template_type,
    )
    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    body: ClassifyRequest,
    current_user: dict = Depends(require_scopes("extractions:write")),
    usecase: ExtractionProcessUseCase = Depends(get_extraction_process_usecase),
):
    """Auto-detect document type without running extraction."""
    try:
        result = await usecase.classify_document(
            document_id=body.document_id,
            user_id=current_user["id"],
        )
        return ClassifyResponse(**result)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("classify_document error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


# ── Read Results ──────────────────────────────────────────


@router.get("/{document_id}", response_model=ExtractionResponse)
async def get_extraction(
    document_id: str,
    current_user: dict = Depends(require_scopes("extractions:read")),
    usecase: ExtractionResultsUseCase = Depends(get_extraction_results_usecase),
):
    """Get the latest extraction results for a document."""
    try:
        return await usecase.get_extraction(document_id=document_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_extraction error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}/audit", response_model=list[AuditEntryResponse])
async def get_audit_trail(
    document_id: str,
    current_user: dict = Depends(require_scopes("extractions:read")),
    usecase: ExtractionResultsUseCase = Depends(get_extraction_results_usecase),
):
    """Get pipeline audit trail for a document's extraction."""
    try:
        return await usecase.get_audit_trail(document_id=document_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_audit_trail error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}/overlay", response_model=list[OverlayRegion])
async def get_overlay_data(
    document_id: str,
    current_user: dict = Depends(require_scopes("extractions:read")),
    usecase: ExtractionResultsUseCase = Depends(get_extraction_results_usecase),
):
    """Get confidence overlay bounding boxes for UI visualization."""
    try:
        return await usecase.get_overlay_data(document_id=document_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_overlay_data error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(
    document_id: str,
    current_user: dict = Depends(require_scopes("extractions:read")),
    usecase: ExtractionResultsUseCase = Depends(get_extraction_results_usecase),
):
    """Get raw vs enhanced field comparison."""
    try:
        return await usecase.get_comparison(document_id=document_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_comparison error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}/export")
async def export_extraction(
    document_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_user: dict = Depends(require_scopes("extractions:read")),
    usecase: ExtractionResultsUseCase = Depends(get_extraction_results_usecase),
):
    """Export extracted fields as JSON or CSV."""
    try:
        extraction = await usecase.get_extraction(document_id=document_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("export_extraction error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")

    fields = extraction.fields

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "field_key", "field_value", "field_type",
            "confidence", "page_number", "is_required", "is_missing",
        ])
        for f in fields:
            writer.writerow([
                f.field_key, f.field_value, f.field_type,
                f.confidence, f.page_number, f.is_required, f.is_missing,
            ])
        content = output.getvalue()
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename={document_id}_extraction.csv"
                ),
            },
        )

    data = {
        "document_id": document_id,
        "template_type": extraction.template_type,
        "processing_time_ms": extraction.processing_time_ms,
        "fields": [
            {
                "field_key": f.field_key,
                "field_value": f.field_value,
                "field_type": f.field_type,
                "confidence": f.confidence,
                "page_number": f.page_number,
                "bounding_box": f.bounding_box,
                "is_required": f.is_required,
                "is_missing": f.is_missing,
            }
            for f in fields
        ],
    }
    content = json.dumps(data, indent=2, default=str)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f"attachment; filename={document_id}_extraction.json"
            ),
        },
    )
