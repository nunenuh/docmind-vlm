"""Integration tests for process API endpoint — routing and auth."""
import pytest

from docmind.core.auth import get_current_user
from docmind.main import create_app
from httpx import ASGITransport, AsyncClient

FAKE_USER = {"id": "user-test-123", "email": "test@example.com"}


@pytest.fixture
def app_with_auth():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(app_with_auth):
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestProcessAuth:
    @pytest.mark.asyncio
    async def test_process_requires_auth(self, client):
        response = await client.post("/api/v1/documents/doc-123/process")
        assert response.status_code in (401, 403)
