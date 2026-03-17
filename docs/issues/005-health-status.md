# Issue #5: Implement Real Health Checks (DB, Redis, VLM Provider)

## Summary

Replace the stub `HealthUseCase.get_basic_health()` with real health checks that verify connectivity to the database (SQLAlchemy async `SELECT 1`), Redis (`PING`), and the VLM provider (`health_check()` or configuration validation). Each component reports its own status with response time. The overall status is "healthy" only when all components are healthy, otherwise "degraded". Uses dependency injection for testability.

## Context

- **Phase**: 1 — Infrastructure
- **Priority**: P1
- **Labels**: `phase-1-infra`, `backend`, `tdd`, `priority-p1`
- **Dependencies**: #2 (Alembic migration — DB must be reachable)
- **Branch**: `feat/5-health-status`
- **Estimated scope**: S

## Specs to Read

- `specs/backend/api.md` — Section "Health Handler", PingResponse, HealthStatusResponse, ComponentHealth schemas
- `specs/backend/services.md` — Section "Health Module > usecase.py" for full implementation spec
- `specs/conventions/python-module-structure.md` — Section "modules/*/usecase.py" layer rules

## Current State (Scaffold)

**File: `backend/src/docmind/modules/health/usecase.py`**

```python
"""docmind/modules/health/usecase.py"""
import time
from .schemas import ComponentHealth

_start_time = time.time()


class HealthUseCase:
    def get_basic_health(self) -> tuple[str, list[ComponentHealth], float]:
        components = [
            ComponentHealth(name="database", status="healthy", message="Stub — not connected"),
            ComponentHealth(name="vlm_provider", status="healthy", message="Stub — not connected"),
        ]
        overall = "healthy"
        uptime = time.time() - _start_time
        return overall, components, uptime
```

**File: `backend/src/docmind/modules/health/services.py`**

```python
"""docmind/modules/health/services.py — Stub."""


class HealthService:
    pass
```

**File: `backend/src/docmind/modules/health/apiv1/handler.py`**

```python
"""docmind/modules/health/apiv1/handler.py"""
from datetime import datetime, UTC
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
```

**File: `backend/src/docmind/modules/health/schemas.py`**

```python
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
```

**File: `backend/src/docmind/core/config.py`** (relevant)

```python
class Settings(BaseSettings):
    # ...
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    VLM_PROVIDER: str = Field(default="dashscope")
    # ...
```

## Requirements

### Functional

1. `get_basic_health()` must be `async` (DB and Redis checks are I/O operations)
2. **Database check**: Execute `SELECT 1` via SQLAlchemy async session. Report response time in ms
3. **Redis check**: Execute `PING` via `redis.asyncio`. Report response time in ms
4. **VLM provider check**: Verify VLM provider is configured (API key is non-empty for the selected provider). No actual API call needed — just configuration validation
5. Each component returns `ComponentHealth(name=..., status="healthy"|"unhealthy", message=..., response_time_ms=...)`
6. Overall status is `"healthy"` if ALL components are healthy, `"degraded"` if ANY component is unhealthy
7. If a component check throws an exception, catch it and report `"unhealthy"` with the error message (no stack trace)
8. Handler must `await` the usecase call (update to async)
9. Uptime is tracked from module import time via `_start_time`

### Non-Functional

- Health checks must not block for more than 5 seconds per component
- Error messages in ComponentHealth should be informative but not leak internal details (e.g., "Connection refused" is OK, full traceback is not)
- Redis check should gracefully handle Redis not being available (return unhealthy, not crash)
- VLM provider check should not make any external API calls

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/health/test_usecase.py`

```python
"""
Unit tests for docmind/modules/health/usecase.py.

Tests cover:
- All components healthy
- Database down
- Redis down
- VLM provider not configured
- Mixed healthy/unhealthy states
- Uptime tracking
- Response time measurement
"""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.modules.health.schemas import ComponentHealth
from docmind.modules.health.usecase import HealthUseCase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def usecase():
    """Create a HealthUseCase instance."""
    return HealthUseCase()


@pytest.fixture
def mock_db_healthy():
    """Mock a healthy database connection."""
    session = AsyncMock()
    session.execute = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    return cm


@pytest.fixture
def mock_db_unhealthy():
    """Mock an unhealthy database connection."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    return cm


@pytest.fixture
def mock_redis_healthy():
    """Mock a healthy Redis connection."""
    redis_client = AsyncMock()
    redis_client.ping = AsyncMock(return_value=True)
    redis_client.aclose = AsyncMock()
    return redis_client


@pytest.fixture
def mock_redis_unhealthy():
    """Mock an unhealthy Redis connection."""
    redis_client = AsyncMock()
    redis_client.ping = AsyncMock(side_effect=ConnectionError("Redis not available"))
    redis_client.aclose = AsyncMock()
    return redis_client


@pytest.fixture
def mock_settings_with_vlm():
    """Mock settings with a configured VLM provider."""
    settings = MagicMock()
    settings.VLM_PROVIDER = "dashscope"
    settings.DASHSCOPE_API_KEY = "sk-test-key"
    settings.OPENAI_API_KEY = ""
    settings.GOOGLE_API_KEY = ""
    settings.REDIS_URL = "redis://localhost:6379/0"
    return settings


@pytest.fixture
def mock_settings_no_vlm():
    """Mock settings with NO VLM provider API key."""
    settings = MagicMock()
    settings.VLM_PROVIDER = "dashscope"
    settings.DASHSCOPE_API_KEY = ""
    settings.OPENAI_API_KEY = ""
    settings.GOOGLE_API_KEY = ""
    settings.REDIS_URL = "redis://localhost:6379/0"
    return settings


# ---------------------------------------------------------------------------
# Tests: All Healthy
# ---------------------------------------------------------------------------


class TestAllHealthy:
    """Tests when all components are healthy."""

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_all_healthy_returns_healthy_status(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """When all components are healthy, overall status should be 'healthy'."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        overall, components, uptime = await usecase.get_basic_health()

        assert overall == "healthy"
        assert all(c.status == "healthy" for c in components)

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_all_healthy_returns_three_components(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """Should report database, redis, and vlm_provider components."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, components, _ = await usecase.get_basic_health()

        component_names = {c.name for c in components}
        assert "database" in component_names
        assert "redis" in component_names
        assert "vlm_provider" in component_names

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_healthy_db_includes_response_time(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """Database component should include response_time_ms."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, components, _ = await usecase.get_basic_health()

        db_component = next(c for c in components if c.name == "database")
        assert db_component.response_time_ms is not None
        assert db_component.response_time_ms >= 0


# ---------------------------------------------------------------------------
# Tests: Database Down
# ---------------------------------------------------------------------------


class TestDatabaseDown:
    """Tests when the database is unhealthy."""

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_db_down_returns_degraded(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_unhealthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """When database is down, overall status should be 'degraded'."""
        mock_async_session_local.return_value = mock_db_unhealthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        overall, components, _ = await usecase.get_basic_health()

        assert overall == "degraded"

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_db_down_reports_unhealthy_component(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_unhealthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """When database is down, database component should be 'unhealthy'."""
        mock_async_session_local.return_value = mock_db_unhealthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, components, _ = await usecase.get_basic_health()

        db_component = next(c for c in components if c.name == "database")
        assert db_component.status == "unhealthy"
        assert db_component.message is not None


# ---------------------------------------------------------------------------
# Tests: Redis Down
# ---------------------------------------------------------------------------


class TestRedisDown:
    """Tests when Redis is unhealthy."""

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_redis_down_returns_degraded(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_unhealthy, mock_settings_with_vlm,
    ):
        """When Redis is down, overall status should be 'degraded'."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_unhealthy
        mock_get_settings.return_value = mock_settings_with_vlm

        overall, components, _ = await usecase.get_basic_health()

        assert overall == "degraded"

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_redis_down_reports_unhealthy_component(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_unhealthy, mock_settings_with_vlm,
    ):
        """When Redis is down, redis component should be 'unhealthy'."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_unhealthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, components, _ = await usecase.get_basic_health()

        redis_component = next(c for c in components if c.name == "redis")
        assert redis_component.status == "unhealthy"
        assert redis_component.message is not None


# ---------------------------------------------------------------------------
# Tests: VLM Provider Not Configured
# ---------------------------------------------------------------------------


class TestVlmProviderDown:
    """Tests when VLM provider is not configured."""

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_vlm_not_configured_returns_degraded(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_no_vlm,
    ):
        """When VLM API key is empty, overall status should be 'degraded'."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_no_vlm

        overall, components, _ = await usecase.get_basic_health()

        assert overall == "degraded"

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_vlm_not_configured_reports_unhealthy(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_no_vlm,
    ):
        """When VLM API key is empty, vlm_provider should be 'unhealthy'."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_no_vlm

        _, components, _ = await usecase.get_basic_health()

        vlm_component = next(c for c in components if c.name == "vlm_provider")
        assert vlm_component.status == "unhealthy"
        assert "not configured" in vlm_component.message.lower()


# ---------------------------------------------------------------------------
# Tests: Uptime
# ---------------------------------------------------------------------------


class TestUptime:
    """Tests for uptime tracking."""

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_uptime_is_positive(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """Uptime should be a positive number."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, _, uptime = await usecase.get_basic_health()

        assert uptime > 0

    @pytest.mark.asyncio
    @patch("docmind.modules.health.usecase.get_settings")
    @patch("docmind.modules.health.usecase.redis_from_url")
    @patch("docmind.modules.health.usecase.AsyncSessionLocal")
    async def test_uptime_is_float(
        self, mock_async_session_local, mock_redis_from_url,
        mock_get_settings, usecase, mock_db_healthy,
        mock_redis_healthy, mock_settings_with_vlm,
    ):
        """Uptime should be a float representing seconds."""
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, _, uptime = await usecase.get_basic_health()

        assert isinstance(uptime, float)
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/modules/health/usecase.py` — Replace stub with real async health checks
- `backend/src/docmind/modules/health/apiv1/handler.py` — Update handler to `await` the async usecase call

**Implementation guidance**:

**usecase.py**:

```python
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

# VLM provider to API key setting mapping
_VLM_API_KEY_MAP = {
    "dashscope": "DASHSCOPE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "ollama": None,  # Ollama runs locally, no API key needed
}


class HealthUseCase:
    """Orchestrates health checks for all system components."""

    async def get_basic_health(self) -> tuple[str, list[ComponentHealth], float]:
        """
        Check all components and return overall status.

        Returns:
            Tuple of (overall_status, components, uptime_seconds).
        """
        components: list[ComponentHealth] = []

        # 1. Database check
        components.append(await self._check_database())

        # 2. Redis check
        components.append(await self._check_redis())

        # 3. VLM provider check
        components.append(self._check_vlm_provider())

        overall = (
            "healthy"
            if all(c.status == "healthy" for c in components)
            else "degraded"
        )
        uptime = time.time() - _start_time

        return overall, components, uptime

    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity via SQLAlchemy."""
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
            logger.warning("Database health check failed", error=str(e))
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
            logger.warning("Redis health check failed", error=str(e))
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
            # Ollama — just report configured
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
```

**handler.py** — Update to await async usecase:

```python
@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status():
    usecase = HealthUseCase()
    overall_status, components, uptime = await usecase.get_basic_health()  # <-- add await
    return HealthStatusResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        version=get_settings().APP_VERSION,
        components=components,
        uptime_seconds=uptime,
    )
```

### Step 3: Refactor (IMPROVE)

- Extract each check into a private async method (already done in the target implementation)
- Consider adding a timeout wrapper for each health check (e.g., `asyncio.wait_for(..., timeout=5.0)`)
- Ensure Redis client is always closed (use `try/finally`)
- Make the VLM provider key mapping a module-level constant for clarity

## Acceptance Criteria

- [ ] `get_basic_health()` is async and checks 3 components
- [ ] Database check executes `SELECT 1` and reports response_time_ms
- [ ] Database failure returns `status="unhealthy"` with error message
- [ ] Redis check executes `PING` and reports response_time_ms
- [ ] Redis failure returns `status="unhealthy"` with error message
- [ ] Redis client is always closed after check (no connection leak)
- [ ] VLM provider check validates API key configuration (no external call)
- [ ] Missing VLM API key returns `status="unhealthy"` with descriptive message
- [ ] Overall status is `"healthy"` only when ALL components are healthy
- [ ] Overall status is `"degraded"` when ANY component is unhealthy
- [ ] Uptime is tracked as positive float in seconds
- [ ] Handler awaits the async usecase method
- [ ] All 12 unit tests pass
- [ ] No exceptions propagate to the client (all caught and reported)

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/modules/health/usecase.py` | Modify | Replace stub with real async health checks for DB, Redis, VLM |
| `backend/src/docmind/modules/health/apiv1/handler.py` | Modify | Update handler to `await` the async `get_basic_health()` call |
| `backend/tests/unit/modules/health/test_usecase.py` | Create | 12 unit tests covering all healthy, DB down, Redis down, VLM down, uptime |

## Verification

```bash
# Run the health check tests
cd backend && python -m pytest tests/unit/modules/health/test_usecase.py -v

# Run with coverage
cd backend && python -m pytest tests/unit/modules/health/test_usecase.py -v --cov=docmind.modules.health.usecase --cov-report=term-missing

# Verify handler uses await
grep -n "await" backend/src/docmind/modules/health/apiv1/handler.py
# Should show: await usecase.get_basic_health()

# Verify all three components are checked
grep -n "def _check" backend/src/docmind/modules/health/usecase.py
# Should show: _check_database, _check_redis, _check_vlm_provider
```
