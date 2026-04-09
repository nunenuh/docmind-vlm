"""
Integration tests for document API endpoints.

Tests cover routing, auth, validation, and response format.
Uses FastAPI TestClient with auth dependency override.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from docmind.core.auth import get_current_user
from docmind.main import create_app


FAKE_USER = {"id": "user-test-123", "email": "test@example.com"}


@pytest.fixture
def app_with_auth():
    """Create app with auth dependency overridden."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(app_with_auth):
    """Authenticated async client."""
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUploadDocument:
    """Tests for POST /api/v1/documents."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_upload_returns_201(self, MockUseCase, auth_client):
        """Successful upload returns 201 with document data."""
        mock_usecase = MagicMock()
        mock_usecase.create_document = AsyncMock(return_value=MagicMock(
            id="doc-new-123",
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            status="uploaded",
            document_type=None,
            page_count=0,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ))
        MockUseCase.return_value = mock_usecase

        response = await auth_client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 content", "application/pdf")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "doc-new-123"
        assert data["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_type(self, auth_client):
        """Unsupported file types return 400."""
        response = await auth_client.post(
            "/api/v1/documents",
            files={"file": ("script.js", b"console.log('hi')", "application/javascript")},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_file(self, auth_client):
        """Files over 20MB return 422."""
        big_content = b"x" * (20_971_520 + 1)
        response = await auth_client.post(
            "/api/v1/documents",
            files={"file": ("big.pdf", big_content, "application/pdf")},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client):
        """Upload without auth returns 401/403."""
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", b"content", "application/pdf")},
        )
        assert response.status_code in (401, 403)


class TestListDocuments:
    """Tests for GET /api/v1/documents."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_list_returns_200(self, MockUseCase, auth_client):
        """List documents returns 200."""
        mock_usecase = MagicMock()
        mock_usecase.get_documents = AsyncMock(return_value=MagicMock(
            items=[], total=0, page=1, limit=20,
        ))
        MockUseCase.return_value = mock_usecase

        response = await auth_client.get("/api/v1/documents")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        """List without auth returns 401/403."""
        response = await client.get("/api/v1/documents")
        assert response.status_code in (401, 403)


class TestGetDocument:
    """Tests for GET /api/v1/documents/{id}."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_get_returns_200(self, MockUseCase, auth_client):
        """Get existing document returns 200."""
        mock_usecase = MagicMock()
        mock_usecase.get_document = AsyncMock(return_value=MagicMock(
            id="doc-123", filename="test.pdf", file_type="pdf",
            file_size=1024, status="uploaded", document_type=None,
            page_count=0, created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ))
        MockUseCase.return_value = mock_usecase

        response = await auth_client.get("/api/v1/documents/doc-123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_get_returns_404(self, MockUseCase, auth_client):
        """Missing document returns 404."""
        from docmind.shared.exceptions import NotFoundException
        mock_usecase = MagicMock()
        mock_usecase.get_document = AsyncMock(side_effect=NotFoundException("Document not found"))
        MockUseCase.return_value = mock_usecase

        response = await auth_client.get("/api/v1/documents/nonexistent")
        assert response.status_code == 404


class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{id}."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_delete_returns_204(self, MockUseCase, auth_client):
        """Successful delete returns 204."""
        mock_usecase = MagicMock()
        mock_usecase.delete_document = AsyncMock(return_value=True)
        MockUseCase.return_value = mock_usecase

        response = await auth_client.delete("/api/v1/documents/doc-123")
        assert response.status_code == 204

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_delete_returns_404(self, MockUseCase, auth_client):
        """Deleting nonexistent document returns 404."""
        from docmind.shared.exceptions import NotFoundException
        mock_usecase = MagicMock()
        mock_usecase.delete_document = AsyncMock(side_effect=NotFoundException("Document not found"))
        MockUseCase.return_value = mock_usecase

        response = await auth_client.delete("/api/v1/documents/nonexistent")
        assert response.status_code == 404
