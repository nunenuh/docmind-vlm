"""
Fixtures for REAL E2E tests that hit the actual Supabase database.

These tests require:
- A running Supabase PostgreSQL instance
- Tables created via `make migrate`
- Network access to Supabase

Skip with: pytest -m "not real_e2e"
"""
import pytest
from httpx import ASGITransport, AsyncClient

from docmind.core.auth import get_current_user
from docmind.main import create_app

# Real test user ID (matches Supabase auth)
REAL_USER = {"id": "e2e-real-user-001", "email": "e2e-real@test.com"}


@pytest.fixture
def real_app():
    """Create app with auth override but REAL database."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: REAL_USER
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def real_client(real_app):
    """Async client that hits the real database."""
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
