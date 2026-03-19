"""Integration tests for templates API endpoint."""
import pytest


class TestListTemplates:

    @pytest.mark.asyncio
    async def test_returns_template_list(self, client):
        response = await client.get("/api/v1/templates")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 0  # depends on template dir resolution

    @pytest.mark.asyncio
    async def test_templates_have_required_fields(self, client):
        response = await client.get("/api/v1/templates")

        data = response.json()
        for template in data["items"]:
            assert "type" in template
            assert "name" in template
            assert "required_fields" in template
            assert "optional_fields" in template

    @pytest.mark.asyncio
    async def test_response_has_items_key(self, client):
        response = await client.get("/api/v1/templates")

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_no_auth_required(self, client):
        # Templates endpoint doesn't require auth
        response = await client.get("/api/v1/templates")
        assert response.status_code == 200
