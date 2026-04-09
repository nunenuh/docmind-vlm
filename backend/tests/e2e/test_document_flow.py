"""E2E test: Document upload -> list -> get -> delete flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDocumentUploadFlow:
    """Full document lifecycle through the real FastAPI app."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_upload_then_list_then_get_then_delete(self, MockUseCase, client):
        """Upload a document, list it, fetch it, delete it."""
        mock_doc = MagicMock(
            id="e2e-doc-1",
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            status="uploaded",
            document_type=None,
            page_count=0,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        mock_usecase = MagicMock()
        mock_usecase.create_document = AsyncMock(return_value=mock_doc)
        mock_usecase.get_documents = AsyncMock(
            return_value=MagicMock(
                items=[mock_doc], total=1, page=1, limit=20,
            )
        )
        mock_usecase.get_document = AsyncMock(return_value=mock_doc)
        mock_usecase.delete_document = AsyncMock(return_value=True)
        MockUseCase.return_value = mock_usecase

        # 1. Upload
        upload_resp = await client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
        assert upload_resp.status_code == 201
        doc_data = upload_resp.json()
        assert doc_data["id"] == "e2e-doc-1"
        assert doc_data["filename"] == "test.pdf"
        doc_id = doc_data["id"]

        # 2. List
        list_resp = await client.get("/api/v1/documents")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert len(list_data["items"]) >= 1

        # 3. Get
        get_resp = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["filename"] == "test.pdf"

        # 4. Delete
        del_resp = await client.delete(f"/api/v1/documents/{doc_id}")
        assert del_resp.status_code == 204

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_get_nonexistent_document_returns_404(self, MockUseCase, client):
        """GET for a missing document returns 404."""
        mock_usecase = MagicMock()
        mock_usecase.get_document = AsyncMock(return_value=None)
        MockUseCase.return_value = mock_usecase

        resp = await client.get("/api/v1/documents/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.apiv1.handler.DocumentUseCase")
    async def test_delete_nonexistent_document_returns_404(self, MockUseCase, client):
        """DELETE for a missing document returns 404."""
        mock_usecase = MagicMock()
        mock_usecase.delete_document = AsyncMock(return_value=False)
        MockUseCase.return_value = mock_usecase

        resp = await client.delete("/api/v1/documents/nonexistent-id")
        assert resp.status_code == 404


class TestDocumentUploadValidation:
    """Verify file upload validation at the HTTP boundary."""

    @pytest.mark.asyncio
    async def test_upload_rejects_disallowed_mime_type(self, client):
        """Upload rejects non-allowed MIME types with 400."""
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_file(self, client):
        """Upload rejects files over 20MB with 413."""
        big = b"x" * (20_971_520 + 1)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("big.pdf", big, "application/pdf")},
        )
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_accepts_jpeg(self, client):
        """Upload accepts JPEG images."""
        # Minimal JPEG header
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100

        with patch("docmind.modules.documents.apiv1.handler.DocumentUseCase") as MockUC:
            mock_doc = MagicMock(
                id="img-1", filename="photo.jpg", file_type="jpeg",
                file_size=104, status="uploaded", document_type=None,
                page_count=0, created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
            MockUC.return_value.create_document = AsyncMock(return_value=mock_doc)

            resp = await client.post(
                "/api/v1/documents",
                files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
            )
            assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_accepts_png(self, client):
        """Upload accepts PNG images."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch("docmind.modules.documents.apiv1.handler.DocumentUseCase") as MockUC:
            mock_doc = MagicMock(
                id="img-2", filename="image.png", file_type="png",
                file_size=108, status="uploaded", document_type=None,
                page_count=0, created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
            MockUC.return_value.create_document = AsyncMock(return_value=mock_doc)

            resp = await client.post(
                "/api/v1/documents",
                files={"file": ("image.png", png_bytes, "image/png")},
            )
            assert resp.status_code == 201
