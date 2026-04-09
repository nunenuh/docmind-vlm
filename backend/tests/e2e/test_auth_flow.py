"""E2E test: Authentication enforcement across endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from docmind.main import create_app


class TestAuthEnforcement:
    """Verify all protected endpoints reject unauthenticated requests."""

    @pytest.fixture
    async def unauth_client(self):
        """Client WITHOUT auth override — requests have no Bearer token."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/documents"),
            ("POST", "/api/v1/documents"),
            ("GET", "/api/v1/documents/any-id"),
            ("DELETE", "/api/v1/documents/any-id"),
            ("POST", "/api/v1/documents/any-id/process"),
            ("GET", "/api/v1/extractions/any-id"),
            ("GET", "/api/v1/extractions/any-id/audit"),
            ("POST", "/api/v1/chat/any-id"),
            ("GET", "/api/v1/chat/any-id/history"),
            ("GET", "/api/v1/projects"),
            ("POST", "/api/v1/projects"),
            ("GET", "/api/v1/personas"),
            ("POST", "/api/v1/personas"),
        ],
    )
    async def test_protected_endpoint_rejects_no_auth(
        self, unauth_client, method, path
    ):
        """All protected endpoints return 401 or 403 without a valid token."""
        if method == "GET":
            resp = await unauth_client.get(path)
        elif method == "POST":
            resp = await unauth_client.post(path, json={})
        elif method == "DELETE":
            resp = await unauth_client.delete(path)
        else:
            pytest.fail(f"Unhandled HTTP method: {method}")

        assert resp.status_code in (
            401,
            403,
        ), f"{method} {path} returned {resp.status_code}, expected 401 or 403"

    @pytest.mark.asyncio
    async def test_health_ping_accessible_without_auth(self, unauth_client):
        """Health ping is public and does NOT require auth."""
        resp = await unauth_client.get("/api/v1/health/ping")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_templates_accessible_without_auth(self, unauth_client):
        """Templates listing is public and does NOT require auth."""
        resp = await unauth_client.get("/api/v1/templates")
        assert resp.status_code == 200
