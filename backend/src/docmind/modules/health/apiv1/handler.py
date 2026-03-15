"""docmind/modules/health/apiv1/handler.py"""

from datetime import UTC, datetime

from fastapi import APIRouter

from docmind.core.config import get_settings

from ..schemas import HealthStatusResponse, PingResponse
from ..usecase import HealthUseCase

router = APIRouter()


@router.get("/ping", response_model=PingResponse)
async def ping():
    return PingResponse(status="ok", timestamp=datetime.now(UTC), message="pong")


@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status():
    usecase = HealthUseCase()
    overall_status, components, uptime = usecase.get_basic_health()
    return HealthStatusResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        version=get_settings().APP_VERSION,
        components=components,
        uptime_seconds=uptime,
    )
