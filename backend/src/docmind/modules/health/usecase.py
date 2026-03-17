"""
docmind/modules/health/usecase.py

Health check orchestration — checks DB, Redis, VLM provider.
"""

import time

from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal

from .schemas import ComponentHealth

logger = get_logger(__name__)

_start_time = time.time()

_VLM_API_KEY_MAP: dict[str, str | None] = {
    "dashscope": "DASHSCOPE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "ollama": None,
}


class HealthUseCase:
    """Orchestrates health checks for all system components."""

    async def get_basic_health(self) -> tuple[str, list[ComponentHealth], float]:
        """Check all components and return (overall_status, components, uptime_seconds)."""
        components: list[ComponentHealth] = []

        components.append(await self._check_database())
        components.append(await self._check_redis())
        components.append(self._check_vlm_provider())

        overall = (
            "healthy"
            if all(c.status == "healthy" for c in components)
            else "degraded"
        )
        uptime = time.time() - _start_time

        return overall, components, uptime

    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity via SQLAlchemy SELECT 1."""
        try:
            t0 = time.time()
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            ms = (time.time() - t0) * 1000
            return ComponentHealth(
                name="database",
                status="healthy",
                message="Connected",
                response_time_ms=round(ms, 1),
            )
        except Exception as e:
            logger.warning("database_health_check_failed", error=str(e))
            return ComponentHealth(
                name="database",
                status="unhealthy",
                message=str(e),
            )

    async def _check_redis(self) -> ComponentHealth:
        """Check Redis connectivity via PING."""
        settings = get_settings()
        try:
            t0 = time.time()
            client = redis_from_url(settings.REDIS_URL)
            try:
                await client.ping()
                ms = (time.time() - t0) * 1000
                return ComponentHealth(
                    name="redis",
                    status="healthy",
                    message="Connected",
                    response_time_ms=round(ms, 1),
                )
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning("redis_health_check_failed", error=str(e))
            return ComponentHealth(
                name="redis",
                status="unhealthy",
                message=str(e),
            )

    def _check_vlm_provider(self) -> ComponentHealth:
        """Check VLM provider configuration (no API call)."""
        settings = get_settings()
        provider = settings.VLM_PROVIDER
        api_key_attr = _VLM_API_KEY_MAP.get(provider)

        if api_key_attr is None:
            return ComponentHealth(
                name="vlm_provider",
                status="healthy",
                message=f"{provider} (local)",
            )

        api_key = getattr(settings, api_key_attr, "")
        if api_key:
            return ComponentHealth(
                name="vlm_provider",
                status="healthy",
                message=f"{provider} configured",
            )

        return ComponentHealth(
            name="vlm_provider",
            status="unhealthy",
            message=f"{provider} API key not configured",
        )
