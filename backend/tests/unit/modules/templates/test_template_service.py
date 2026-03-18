"""Unit tests for TemplateService."""
import json
import tempfile
from pathlib import Path

import pytest

from docmind.modules.templates.schemas import TemplateResponse


class TestTemplateService:
    """Tests for TemplateService loading templates from JSON files."""

    def _create_template_dir(self, tmp_path: Path) -> Path:
        """Create a temp directory with template JSON files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        invoice = {
            "type": "invoice",
            "name": "Invoice",
            "description": "Commercial invoices",
            "required_fields": ["invoice_number", "date", "total_amount", "vendor_name"],
            "optional_fields": ["due_date", "tax_amount"],
        }
        (templates_dir / "invoice.json").write_text(json.dumps(invoice))

        receipt = {
            "type": "receipt",
            "name": "Receipt",
            "description": "Purchase receipts",
            "required_fields": ["date", "total_amount", "merchant_name"],
            "optional_fields": ["tax_amount", "payment_method"],
        }
        (templates_dir / "receipt.json").write_text(json.dumps(receipt))

        return templates_dir

    def test_loads_templates_from_directory(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        templates_dir = self._create_template_dir(tmp_path)
        service = TemplateService(templates_dir=templates_dir)

        templates = service.list_templates()
        assert len(templates) == 2
        types = {t.type for t in templates}
        assert "invoice" in types
        assert "receipt" in types

    def test_templates_are_template_response(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        templates_dir = self._create_template_dir(tmp_path)
        service = TemplateService(templates_dir=templates_dir)

        templates = service.list_templates()
        for t in templates:
            assert isinstance(t, TemplateResponse)

    def test_get_template_by_type(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        templates_dir = self._create_template_dir(tmp_path)
        service = TemplateService(templates_dir=templates_dir)

        result = service.get_template("invoice")
        assert result is not None
        assert result.type == "invoice"
        assert "invoice_number" in result.required_fields

    def test_get_template_returns_none_for_unknown(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        templates_dir = self._create_template_dir(tmp_path)
        service = TemplateService(templates_dir=templates_dir)

        result = service.get_template("unknown")
        assert result is None

    def test_skips_invalid_json_files(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "bad.json").write_text("not json")
        (templates_dir / "empty.json").write_text("{}")

        service = TemplateService(templates_dir=templates_dir)
        templates = service.list_templates()
        # Both should be skipped (bad JSON and missing required fields)
        assert len(templates) == 0

    def test_returns_empty_when_no_directory(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService(templates_dir=tmp_path / "nonexistent")
        templates = service.list_templates()
        assert templates == []
