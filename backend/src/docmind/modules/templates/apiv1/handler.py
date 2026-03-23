"""docmind/modules/templates/apiv1/handler.py"""

from fastapi import APIRouter, HTTPException

from docmind.core.logging import get_logger
from docmind.library.templates.loader import list_templates, get_template_detail

from ..schemas import TemplateListResponse, TemplateSummary, TemplateDetail

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=TemplateListResponse)
async def list_all_templates():
    """List all available document extraction templates."""
    summaries = list_templates()
    return TemplateListResponse(
        items=[TemplateSummary(**s) for s in summaries]
    )


@router.get("/{template_type}", response_model=TemplateDetail)
async def get_template(template_type: str):
    """Get full template detail with field definitions."""
    detail = get_template_detail(template_type)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_type}' not found")
    return TemplateDetail(**detail)
