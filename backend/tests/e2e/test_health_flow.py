"""E2E test: Health check endpoints work end-to-end."""

from unittest.mock import AsyncMock, patch

import pytest

from docmind.modules.health.schemas import ComponentHealth


class TestHealthFlow:
    """Verify /health/ping and /health/status return valid responses."""

    @pytest.mark.asyncio
    async def test_ping_returns_ok(self, client):
        """GET /api/v1/health/ping returns 200 with status 'ok'."""
        resp = await client.get("/api/v1/health/ping")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["message"] == "pong"

    @pytest.mark.asyncio
    @patch("docmind.modules.health.apiv1.handler.HealthUseCase")
    async def test_status_returns_components_and_uptime(self, MockUseCase, client):
        """GET /api/v1/health/status returns components list and uptime."""
        mock_components = [
            ComponentHealth(name="database", status="healthy", message="Connected", response_time_ms=1.2),
            ComponentHealth(name="redis", status="healthy", message="Connected", response_time_ms=0.5),
            ComponentHealth(name="vlm_provider", status="healthy", message="dashscope configured"),
        ]
        mock_usecase = MockUseCase.return_value
        mock_usecase.get_basic_health = AsyncMock(
            return_value=("healthy", mock_components, 42.5)
        )

        resp = await client.get("/api/v1/health/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert len(data["components"]) == 3
        assert data["uptime_seconds"] >= 0
        assert "version" in data

    @pytest.mark.asyncio
    @patch("docmind.modules.health.apiv1.handler.HealthUseCase")
    async def test_status_degraded_when_component_unhealthy(self, MockUseCase, client):
        """Status is 'degraded' when any component reports unhealthy."""
        mock_components = [
            ComponentHealth(name="database", status="unhealthy", message="Connection refused"),
            ComponentHealth(name="redis", status="healthy", message="Connected"),
            ComponentHealth(name="vlm_provider", status="healthy", message="ok"),
        ]
        mock_usecase = MockUseCase.return_value
        mock_usecase.get_basic_health = AsyncMock(
            return_value=("degraded", mock_components, 10.0)
        )

        resp = await client.get("/api/v1/health/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
