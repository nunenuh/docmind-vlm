"""
Unit tests for docmind/modules/health/usecase.py.

Tests cover:
- All components healthy
- Database down
- Redis down
- VLM provider not configured
- Uptime tracking
- Response time measurement
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.modules.health.usecase import HealthUseCase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def usecase():
    return HealthUseCase()


@pytest.fixture
def mock_db_healthy():
    session = AsyncMock()
    session.execute = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def mock_db_unhealthy():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=ConnectionRefusedError("Connection refused")
    )
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def mock_redis_healthy():
    redis_client = AsyncMock()
    redis_client.ping = AsyncMock(return_value=True)
    redis_client.aclose = AsyncMock()
    return redis_client


@pytest.fixture
def mock_redis_unhealthy():
    redis_client = AsyncMock()
    redis_client.ping = AsyncMock(
        side_effect=ConnectionError("Redis not available")
    )
    redis_client.aclose = AsyncMock()
    return redis_client


@pytest.fixture
def mock_settings_with_vlm():
    settings = MagicMock()
    settings.VLM_PROVIDER = "dashscope"
    settings.DASHSCOPE_API_KEY = "sk-test-key"
    settings.OPENAI_API_KEY = ""
    settings.GOOGLE_API_KEY = ""
    settings.REDIS_URL = "redis://localhost:6379/0"
    return settings


@pytest.fixture
def mock_settings_no_vlm():
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_unhealthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_unhealthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_unhealthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_unhealthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_no_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_no_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
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
        self,
        mock_async_session_local,
        mock_redis_from_url,
        mock_get_settings,
        usecase,
        mock_db_healthy,
        mock_redis_healthy,
        mock_settings_with_vlm,
    ):
        mock_async_session_local.return_value = mock_db_healthy
        mock_redis_from_url.return_value = mock_redis_healthy
        mock_get_settings.return_value = mock_settings_with_vlm

        _, _, uptime = await usecase.get_basic_health()

        assert isinstance(uptime, float)
