"""Integration tests for templates API endpoint."""
import pytest


class TestListTemplates:

    @pytest.mark.asyncio
    async def test_returns_template_list(self, auth_client):
        response = await auth_client.get("/api/v1/templates")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_templates_have_required_fields(self, auth_client):
        response = await auth_client.get("/api/v1/templates")

        data = response.json()
        for template in data["items"]:
            assert "type" in template
            assert "name" in template
            assert "category" in template
            assert "total_field_count" in template

    @pytest.mark.asyncio
    async def test_response_has_items_key(self, auth_client):
        response = await auth_client.get("/api/v1/templates")

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_requires_auth(self, client):
        """Templates endpoint requires auth now (DB-backed)."""
        response = await client.get("/api/v1/templates")
        assert response.status_code in (401, 403)
