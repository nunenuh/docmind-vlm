"""docmind/modules/templates/apiv1/handler.py

Template CRUD + auto-detect. All logic goes through TemplateUseCase.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException, ValidationException

from ..usecase import TemplateUseCase
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
    usecase = TemplateUseCase()
    try:
        templates = await usecase.list_templates(user_id=current_user["id"])
        return TemplateListResponse(items=[_to_summary(t) for t in templates])
    except Exception as e:
        logger.error("list_templates error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=TemplateDetail)
async def create_template(
    body: TemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a custom template."""
    usecase = TemplateUseCase()
    try:
        template = await usecase.create_template(
            user_id=current_user["id"],
            data={
                "type": body.type,
                "name": body.name,
                "name_en": body.name_en,
                "description": body.description,
                "description_en": body.description_en,
                "category": body.category or "custom",
                "fields": [f.model_dump() for f in body.fields] if body.fields else [],
                "extraction_prompt": body.extraction_prompt,
            },
        )
        return _to_detail(template)
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("create_template error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get template detail."""
    usecase = TemplateUseCase()
    try:
        template = await usecase.get_template(template_id)
        if template is None:
            raise NotFoundException("Template not found")
        return _to_detail(template)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_template error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update a custom template (presets can't be edited)."""
    usecase = TemplateUseCase()
    try:
        data = body.model_dump(exclude_unset=True)
        template = await usecase.update_template(template_id, current_user["id"], data)
        if template is None:
            raise NotFoundException("Template not found or you don't have permission to edit it")
        return _to_detail(template)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("update_template error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a custom template (presets can't be deleted)."""
    usecase = TemplateUseCase()
    try:
        deleted = await usecase.delete_template(template_id, current_user["id"])
        if not deleted:
            raise NotFoundException("Template not found or it's a preset template")
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_template error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{template_id}/duplicate", response_model=TemplateDetail)
async def duplicate_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Duplicate a template as a custom template."""
    usecase = TemplateUseCase()
    try:
        template = await usecase.duplicate_template(template_id, current_user["id"])
        if template is None:
            raise NotFoundException("Template not found")
        return _to_detail(template)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("duplicate_template error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/detect", response_model=AutoDetectResponse)
async def auto_detect_template(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Auto-detect document type and fields from an image using VLM."""
    usecase = TemplateUseCase()
    try:
        file_bytes = await file.read()
        result = await usecase.auto_detect(file_bytes)
        return AutoDetectResponse(**result)
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("auto_detect_template error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
