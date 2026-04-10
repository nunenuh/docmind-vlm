"""E2E test: Template listing works without auth."""

from unittest.mock import patch

import pytest

from docmind.modules.templates.schemas import TemplateSummary

FAKE_TEMPLATES = [
    TemplateSummary(
        id="tmpl-invoice",
        type="invoice",
        name="Invoice",
        description="Extract invoice fields",
        required_fields=["invoice_number", "total_amount", "date"],
        optional_fields=["vendor_name", "tax_amount"],
    ),
    TemplateSummary(
        id="tmpl-receipt",
        type="receipt",
        name="Receipt",
        description="Extract receipt fields",
        required_fields=["store_name", "total", "date"],
        optional_fields=["items", "payment_method"],
    ),
]


class TestTemplateFlow:
    """Verify template endpoints return valid data."""

    @pytest.mark.asyncio
    async def test_templates_returns_200_with_items(self, client):
        """GET /api/v1/templates returns 200 with an items list."""
        resp = await client.get("/api/v1/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    @patch("docmind.modules.templates.apiv1.handler._service")
    async def test_templates_have_correct_structure(self, mock_service, client):
        """Each template has type, name, required_fields, optional_fields."""
        mock_service.list_templates.return_value = FAKE_TEMPLATES

        resp = await client.get("/api/v1/templates")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        for template in items:
            assert "type" in template
            assert "name" in template
            assert "required_fields" in template
            assert "optional_fields" in template
            assert isinstance(template["required_fields"], list)
            assert isinstance(template["optional_fields"], list)

    @pytest.mark.asyncio
    @patch("docmind.modules.templates.apiv1.handler._service")
    async def test_templates_include_known_document_types(self, mock_service, client):
        """Templates should cover common document types (invoice, receipt, etc.)."""
        mock_service.list_templates.return_value = FAKE_TEMPLATES

        resp = await client.get("/api/v1/templates")
        types = {t["type"] for t in resp.json()["items"]}
        assert "invoice" in types, f"Expected 'invoice' in template types, got: {types}"
        assert "receipt" in types, f"Expected 'receipt' in template types, got: {types}"

    @pytest.mark.asyncio
    @patch("docmind.modules.templates.apiv1.handler._service")
    async def test_templates_empty_when_none_configured(self, mock_service, client):
        """Endpoint returns 200 with empty list when no templates loaded."""
        mock_service.list_templates.return_value = []

        resp = await client.get("/api/v1/templates")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
