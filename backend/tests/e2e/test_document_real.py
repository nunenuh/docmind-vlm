"""
REAL E2E tests for Document endpoints.

Hits the actual Supabase database + storage — no mocks.

Run: pytest tests/e2e/test_document_real.py -v
"""
import pytest

from docmind.core.auth import get_current_user
from docmind.main import create_app
from httpx import ASGITransport, AsyncClient

REAL_USER = {"id": "e2e-real-user-001", "email": "e2e-real@test.com"}

pytestmark = pytest.mark.real_e2e


@pytest.fixture
def real_app():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: REAL_USER
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def real_client(real_app):
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUploadValidationReal:
    """Upload validation with real ASGI transport."""

    @pytest.mark.asyncio
    async def test_rejects_unsupported_mime(self, real_client):
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("bad.exe", b"MZ\x90", "application/x-msdownload")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_oversized(self, real_client):
        big = b"x" * (20_971_520 + 1)
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("big.pdf", big, "application/pdf")},
        )
        assert resp.status_code == 413

    @pytest.mark.asyncio
    async def test_accepts_pdf(self, real_client):
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "uploaded"
        # Cleanup
        await real_client.delete(f"/api/v1/documents/{data['id']}")

    @pytest.mark.asyncio
    async def test_accepts_jpeg(self, real_client):
        # Minimal JPEG header
        jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("photo.jpg", jpeg_header + b"\x00" * 100, "image/jpeg")},
        )
        assert resp.status_code == 201
        await real_client.delete(f"/api/v1/documents/{resp.json()['id']}")

    @pytest.mark.asyncio
    async def test_accepts_png(self, real_client):
        png_header = b"\x89PNG\r\n\x1a\n"
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("image.png", png_header + b"\x00" * 100, "image/png")},
        )
        assert resp.status_code == 201
        await real_client.delete(f"/api/v1/documents/{resp.json()['id']}")


class TestDocumentCRUDReal:
    """Full CRUD with real DB."""

    @pytest.mark.asyncio
    async def test_upload_get_delete(self, real_client):
        # Upload
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("crud_test.pdf", b"%PDF-1.4 crud", "application/pdf")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        # Get
        get_resp = await real_client.get(f"/api/v1/documents/{doc_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["filename"] == "crud_test.pdf"

        # List (should include our doc)
        list_resp = await real_client.get("/api/v1/documents")
        assert list_resp.status_code == 200
        ids = [d["id"] for d in list_resp.json()["items"]]
        assert doc_id in ids

        # Delete
        del_resp = await real_client.delete(f"/api/v1/documents/{doc_id}")
        assert del_resp.status_code == 204

        # Verify deleted
        get_resp2 = await real_client.get(f"/api/v1/documents/{doc_id}")
        assert get_resp2.status_code == 404

    @pytest.mark.asyncio
    async def test_nonexistent_returns_404(self, real_client):
        resp = await real_client.get("/api/v1/documents/nonexistent-id-12345")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, real_client):
        resp = await real_client.delete("/api/v1/documents/nonexistent-id-12345")
        assert resp.status_code == 404
