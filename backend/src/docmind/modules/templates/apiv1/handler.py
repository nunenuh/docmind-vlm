"""docmind/modules/templates/apiv1/handler.py"""

from fastapi import APIRouter

from docmind.core.logging import get_logger

from ..schemas import TemplateListResponse
from ..services import TemplateService

logger = get_logger(__name__)
router = APIRouter()

_service = TemplateService()


@router.get("", response_model=TemplateListResponse)
async def list_templates():
    return TemplateListResponse(items=_service.list_templates())
