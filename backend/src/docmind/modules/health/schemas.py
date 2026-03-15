"""docmind/modules/health/schemas.py"""
from datetime import datetime
from pydantic import BaseModel


class PingResponse(BaseModel):
    status: str
    timestamp: datetime
    message: str


class ComponentHealth(BaseModel):
    name: str
    status: str
    message: str | None = None
    response_time_ms: float | None = None


class HealthStatusResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    components: list[ComponentHealth]
    uptime_seconds: float
