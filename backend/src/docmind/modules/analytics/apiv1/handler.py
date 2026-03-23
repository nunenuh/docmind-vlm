"""docmind/modules/analytics/apiv1/handler.py

Analytics endpoint. All logic through AnalyticsUseCase.
"""

from fastapi import APIRouter, Depends

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..usecase import AnalyticsUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.get("/summary")
async def get_analytics_summary(
    current_user: dict = Depends(get_current_user),
):
    """Get analytics summary for the dashboard."""
    usecase = AnalyticsUseCase()
    return await usecase.get_summary(user_id=current_user["id"])
