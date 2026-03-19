"""Integration tests for authenticated API endpoints."""
import pytest


class TestDocumentsRequiresAuth:

    @pytest.mark.asyncio
    async def test_list_documents_returns_403_without_token(self, client):
        response = await client.get("/api/v1/documents")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_document_returns_403_without_token(self, client):
        response = await client.post("/api/v1/documents", json={})
        assert response.status_code in (401, 403)


class TestExtractionsRequiresAuth:

    @pytest.mark.asyncio
    async def test_get_extraction_returns_403_without_token(self, client):
        response = await client.get("/api/v1/extractions/doc-123")
        assert response.status_code in (401, 403)


class TestChatRequiresAuth:

    @pytest.mark.asyncio
    async def test_send_message_returns_403_without_token(self, client):
        response = await client.post("/api/v1/chat/doc-123", json={"message": "hello"})
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_history_returns_403_without_token(self, client):
        response = await client.get("/api/v1/chat/doc-123/history")
        assert response.status_code in (401, 403)
