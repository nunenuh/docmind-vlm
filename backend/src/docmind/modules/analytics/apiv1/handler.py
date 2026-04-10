"""docmind/modules/analytics/apiv1/handler.py

Analytics endpoint. All logic through AnalyticsUseCase.
"""

from fastapi import APIRouter, Depends

from docmind.core.scopes import require_scopes
from docmind.core.logging import get_logger

from ..dependencies import get_analytics_usecase
from ..schemas import AnalyticsSummaryResponse
from ..usecase import AnalyticsUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: AnalyticsUseCase = Depends(get_analytics_usecase),
):
    """Get analytics summary for the dashboard."""
    return await usecase.get_summary(user_id=current_user["id"])
