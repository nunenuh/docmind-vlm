"""Integration tests for health API endpoints."""
import pytest


class TestHealthPing:

    @pytest.mark.asyncio
    async def test_ping_returns_pong(self, client):
        response = await client.get("/api/v1/health/ping")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "pong"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_ping_no_auth_required(self, client):
        response = await client.get("/api/v1/health/ping")
        assert response.status_code == 200


class TestHealthStatus:

    @pytest.mark.asyncio
    async def test_status_returns_components(self, client):
        response = await client.get("/api/v1/health/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "uptime_seconds" in data
