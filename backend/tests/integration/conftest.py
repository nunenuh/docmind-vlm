"""
Integration test fixtures.

Provides a TestClient wired to the real FastAPI app.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from docmind.main import create_app


@pytest.fixture
def app():
    """Create a fresh FastAPI app for each test."""
    return create_app()


@pytest.fixture
async def client(app):
    """Async HTTP client for integration tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
