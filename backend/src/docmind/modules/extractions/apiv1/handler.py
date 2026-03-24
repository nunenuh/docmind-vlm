"""docmind/modules/extractions/apiv1/handler.py"""

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException, ValidationException

from ..schemas import (
    AuditEntryResponse,
    ComparisonResponse,
    ExtractionResponse,
    OverlayRegion,
)
from ..usecase import ExtractionUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{document_id}", response_model=ExtractionResponse)
async def get_extraction(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    try:
        return await usecase.get_extraction(document_id=document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("get_extraction error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}/audit", response_model=list[AuditEntryResponse])
async def get_audit_trail(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    try:
        return await usecase.get_audit_trail(document_id=document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_audit_trail error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}/overlay", response_model=list[OverlayRegion])
async def get_overlay_data(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    try:
        return await usecase.get_overlay_data(document_id=document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_overlay_data error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    try:
        return await usecase.get_comparison(document_id=document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("get_comparison error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}/export")
async def export_extraction(
    document_id: str,
    format: str = Query(default="json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user),
):
    """Export extracted fields as JSON or CSV.

    Args:
        format: "json" or "csv"
    """
    usecase = ExtractionUseCase()
    try:
        extraction = await usecase.get_extraction(document_id=document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_extraction error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    fields = extraction.fields

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["field_key", "field_value", "field_type", "confidence", "page_number", "is_required", "is_missing"])
        for f in fields:
            writer.writerow([
                f.field_key, f.field_value, f.field_type,
                f.confidence, f.page_number, f.is_required, f.is_missing,
            ])
        content = output.getvalue()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={document_id}_extraction.csv"},
        )

    # JSON format
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
        headers={"Content-Disposition": f"attachment; filename={document_id}_extraction.json"},
    )
