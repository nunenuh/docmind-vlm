"""docmind/modules/health/apiv1/handler.py"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from docmind.core.config import get_settings

from ..dependencies import get_health_usecase
from ..schemas import HealthStatusResponse, PingResponse
from ..usecase import HealthUseCase

router = APIRouter()


@router.get("/ping", response_model=PingResponse)
async def ping():
    return PingResponse(status="ok", timestamp=datetime.now(timezone.utc), message="pong")


@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status(
    usecase: HealthUseCase = Depends(get_health_usecase),
):
    overall_status, components, uptime = await usecase.get_basic_health()
    return HealthStatusResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=get_settings().APP_VERSION,
        components=components,
        uptime_seconds=uptime,
    )
