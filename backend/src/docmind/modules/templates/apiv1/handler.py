"""docmind/modules/templates/apiv1/handler.py

Template CRUD + auto-detect endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..repositories import TemplateRepository
from ..schemas import (
    TemplateListResponse,
    TemplateSummary,
    TemplateDetail,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    AutoDetectResponse,
)

logger = get_logger(__name__)
router = APIRouter()


def _to_summary(t) -> TemplateSummary:
    fields = t.fields or []
    required = [f for f in fields if isinstance(f, dict) and f.get("required")]
    optional = [f for f in fields if isinstance(f, dict) and not f.get("required")]
    return TemplateSummary(
        id=t.id,
        type=t.type,
        name=t.name,
        name_en=t.name_en or "",
        description=t.description or "",
        description_en=t.description_en or "",
        category=t.category or "general",
        is_preset=t.is_preset,
        required_field_count=len(required),
        optional_field_count=len(optional),
        total_field_count=len(fields),
    )


def _to_detail(t) -> TemplateDetail:
    return TemplateDetail(
        id=t.id,
        type=t.type,
        name=t.name,
        name_en=t.name_en or "",
        description=t.description or "",
        description_en=t.description_en or "",
        category=t.category or "general",
        is_preset=t.is_preset,
        fields=t.fields or [],
        extraction_prompt=t.extraction_prompt or "",
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(current_user: dict = Depends(get_current_user)):
    """List all templates: presets + user's custom."""
    repo = TemplateRepository()

    # Seed presets on first access
    await repo.seed_presets()

    templates = await repo.list_all(user_id=current_user["id"])
    return TemplateListResponse(items=[_to_summary(t) for t in templates])


@router.post("", response_model=TemplateDetail)
async def create_template(
    body: TemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a custom template."""
    repo = TemplateRepository()
    template = await repo.create({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": body.type,
        "name": body.name,
        "name_en": body.name_en,
        "description": body.description,
        "description_en": body.description_en,
        "category": body.category or "custom",
        "is_preset": False,
        "fields": [f.model_dump() for f in body.fields] if body.fields else [],
        "extraction_prompt": body.extraction_prompt,
    })
    return _to_detail(template)


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get template detail."""
    repo = TemplateRepository()
    template = await repo.get_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_detail(template)


@router.put("/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update a custom template (presets can't be edited)."""
    repo = TemplateRepository()
    data = body.model_dump(exclude_unset=True)
    if "fields" in data and data["fields"]:
        data["fields"] = [f if isinstance(f, dict) else f for f in data["fields"]]

    template = await repo.update(template_id, current_user["id"], data)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail="Template not found or you don't have permission to edit it"
        )
    return _to_detail(template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a custom template (presets can't be deleted)."""
    repo = TemplateRepository()
    deleted = await repo.delete(template_id, current_user["id"])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Template not found or it's a preset template"
        )


@router.post("/{template_id}/duplicate", response_model=TemplateDetail)
async def duplicate_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Duplicate a template as a custom template."""
    repo = TemplateRepository()
    template = await repo.duplicate(template_id, current_user["id"])
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_detail(template)


@router.post("/detect", response_model=AutoDetectResponse)
async def auto_detect_template(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Auto-detect document type and fields from an image using VLM.

    Returns detected template type, fields, and a suggested template.
    """
    from docmind.library.providers.factory import get_vlm_provider
    from docmind.library.providers.protocol import encode_image_base64
    import numpy as np
    import cv2
    import json as json_module

    file_bytes = await file.read()

    # Convert to image for VLM
    nparr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        # Try PDF first page
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            nparr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
            image = cv2.cvtColor(nparr, cv2.COLOR_RGB2BGR) if pix.n == 3 else nparr
            doc.close()
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read file as image or PDF")

    provider = get_vlm_provider()

    # Step 1: Classify
    classify_prompt = """Analyze this document image and determine:
1. What type of document is this? (e.g., KTP, KK, invoice, contract, receipt, salary slip, etc.)
2. What language is the document in?

Return a JSON object:
{"document_type": "ktp", "document_name": "KTP (Kartu Tanda Penduduk)", "language": "id", "confidence": 0.95}"""

    classify_response = await provider.extract(
        images=[image], prompt=classify_prompt
    )

    # Step 2: Extract all fields
    extract_prompt = """Extract ALL visible fields from this document. For each field found, return:
- "key": a snake_case identifier (e.g., "nama", "nik", "total_amount")
- "label": the field label as shown on the document
- "value": the extracted value
- "required": true if this seems like a primary/important field

Return a JSON object: {"fields": [...], "document_type": "detected_type"}"""

    extract_response = await provider.extract(
        images=[image], prompt=extract_prompt
    )

    # Parse responses
    try:
        classify_data = classify_response.get("structured_data", {})
        doc_type = classify_data.get("document_type", "unknown")
        doc_name = classify_data.get("document_name", doc_type)
        language = classify_data.get("language", "unknown")
        confidence = classify_data.get("confidence", 0.5)
    except Exception:
        doc_type = "unknown"
        doc_name = "Unknown Document"
        language = "unknown"
        confidence = 0.3

    try:
        extract_data = extract_response.get("structured_data", {})
        detected_fields = extract_data.get("fields", [])
    except Exception:
        detected_fields = []

    return AutoDetectResponse(
        document_type=doc_type,
        document_name=doc_name,
        language=language,
        confidence=confidence,
        detected_fields=detected_fields,
        suggested_template={
            "type": doc_type,
            "name": doc_name,
            "category": _guess_category(doc_type),
            "fields": detected_fields,
        },
    )


def _guess_category(doc_type: str) -> str:
    """Guess template category from document type."""
    identity_types = {"ktp", "kk", "sim", "passport", "id_document"}
    vehicle_types = {"stnk", "bpkb"}
    tax_types = {"npwp", "faktur_pajak", "spt"}
    finance_types = {"invoice", "receipt", "slip_gaji", "kuitansi"}
    legal_types = {"contract", "surat_kuasa", "bast", "agreement"}

    dt = doc_type.lower()
    if dt in identity_types:
        return "identity"
    if dt in vehicle_types:
        return "vehicle"
    if dt in tax_types:
        return "tax"
    if dt in finance_types:
        return "finance"
    if dt in legal_types:
        return "legal"
    return "general"
