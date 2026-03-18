"""docmind/modules/extractions/apiv1/handler.py"""

from fastapi import APIRouter, Depends, HTTPException

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

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
    extraction = await usecase.get_extraction(document_id=document_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return extraction


@router.get("/{document_id}/audit", response_model=list[AuditEntryResponse])
async def get_audit_trail(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    return await usecase.get_audit_trail(document_id=document_id)


@router.get("/{document_id}/overlay", response_model=list[OverlayRegion])
async def get_overlay_data(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    return await usecase.get_overlay_data(document_id=document_id)


@router.get("/{document_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = ExtractionUseCase()
    comparison = await usecase.get_comparison(document_id=document_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison not available")
    return comparison
