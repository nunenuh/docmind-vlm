"""
E2E test fixtures.

Provides an authenticated ASGI client with mocked external services (DB, storage, VLM).
Tests verify the full request -> handler -> usecase -> service flow through the real
FastAPI app using httpx's ASGITransport (no network, no real database).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from docmind.core.auth import get_current_user
from docmind.main import create_app

FAKE_USER = {"id": "e2e-user-123", "email": "e2e@test.com"}


@pytest.fixture
def app():
    """Create a fresh FastAPI app with auth dependency overridden."""
    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """Authenticated async HTTP client for E2E tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
