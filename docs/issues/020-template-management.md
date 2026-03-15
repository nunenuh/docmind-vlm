# Issue #20: Template Management

## Summary

Implement template management by loading predefined document extraction templates from JSON files in `data/templates/`. Replace the current hardcoded `TEMPLATES` list in the handler with a `TemplateService` that discovers and validates template files at startup. The `GET /api/v1/templates` endpoint returns all available templates. Template JSON files already exist but are empty (`{}`); this issue populates them and builds the loading infrastructure.

## Context

- **Phase**: 4
- **Priority**: P1
- **Labels**: `phase-4-extraction`, `backend`, `tdd`
- **Dependencies**: None
- **Branch**: `feat/20-template-management`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/api.md` — TemplateResponse, TemplateListResponse schemas, handler spec
- `specs/backend/services.md` — templates module (static data)
- `specs/conventions/python-module-structure.md`

## Current State (Scaffold)

### `backend/src/docmind/modules/templates/apiv1/handler.py` (hardcoded templates)
```python
"""docmind/modules/templates/apiv1/handler.py"""
from fastapi import APIRouter, Depends
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from ..schemas import TemplateListResponse, TemplateResponse

logger = get_logger(__name__)
router = APIRouter()

TEMPLATES = [
    TemplateResponse(type="invoice", name="Invoice", ...),
    TemplateResponse(type="receipt", name="Receipt", ...),
    TemplateResponse(type="medical_report", name="Medical Report", ...),
    TemplateResponse(type="contract", name="Contract", ...),
    TemplateResponse(type="id_document", name="ID Document", ...),
]

@router.get("", response_model=TemplateListResponse)
async def list_templates(current_user: dict = Depends(get_current_user)):
    return TemplateListResponse(items=TEMPLATES)
```

### `backend/src/docmind/modules/templates/schemas.py` (already exists)
```python
class TemplateResponse(BaseModel):
    type: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]

class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
```

### `data/templates/invoice.json` (empty)
```json
{}
```

### Other template files (all empty `{}`)
- `data/templates/receipt.json`
- `data/templates/contract.json`
- `data/templates/medical_report.json`
- `data/templates/id_document.json`

## Requirements

### Functional

1. Populate each template JSON file with the correct schema:
   ```json
   {
     "type": "invoice",
     "name": "Invoice",
     "description": "Commercial invoices with line items, totals, and vendor info",
     "required_fields": ["invoice_number", "date", "total_amount", "vendor_name"],
     "optional_fields": ["due_date", "tax_amount", "line_items", "purchase_order"]
   }
   ```
2. Create `TemplateService` in `modules/templates/services.py` that:
   - `load_templates(templates_dir: Path) -> list[TemplateResponse]` scans directory for `*.json` files, validates each against `TemplateResponse` schema, returns list.
   - `get_template(type: str) -> TemplateResponse | None` returns a single template by type.
   - Raises clear errors for invalid JSON or missing required fields.
3. Templates are loaded once at module import (cached) — not on every request.
4. Handler uses `TemplateService` instead of hardcoded list.
5. At least 5 templates: invoice, receipt, medical_report, contract, id_document.

### Non-Functional

- Template JSON files are the source of truth; changing a file changes the API response.
- Invalid template files are logged as warnings and skipped (don't crash the app).
- Template directory path comes from settings or defaults to `data/templates/`.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/templates/test_template_service.py`

```python
"""Unit tests for TemplateService."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from docmind.modules.templates.schemas import TemplateResponse


@pytest.fixture
def tmp_templates_dir(tmp_path):
    """Create a temporary templates directory with valid JSON files."""
    invoice = {
        "type": "invoice",
        "name": "Invoice",
        "description": "Commercial invoices with line items, totals, and vendor info",
        "required_fields": ["invoice_number", "date", "total_amount", "vendor_name"],
        "optional_fields": ["due_date", "tax_amount", "line_items", "purchase_order"],
    }
    receipt = {
        "type": "receipt",
        "name": "Receipt",
        "description": "Purchase receipts with itemized costs",
        "required_fields": ["date", "total_amount", "merchant_name"],
        "optional_fields": ["tax_amount", "payment_method", "line_items"],
    }

    (tmp_path / "invoice.json").write_text(json.dumps(invoice))
    (tmp_path / "receipt.json").write_text(json.dumps(receipt))

    return tmp_path


@pytest.fixture
def dir_with_invalid_json(tmp_path):
    """Create a directory with one valid and one invalid JSON file."""
    valid = {
        "type": "invoice",
        "name": "Invoice",
        "description": "Test invoice",
        "required_fields": ["invoice_number"],
        "optional_fields": [],
    }
    (tmp_path / "invoice.json").write_text(json.dumps(valid))
    (tmp_path / "broken.json").write_text("{invalid json")
    return tmp_path


@pytest.fixture
def dir_with_missing_fields(tmp_path):
    """Create a directory with a JSON file missing required schema fields."""
    incomplete = {
        "type": "invoice",
        "name": "Invoice",
        # missing description, required_fields, optional_fields
    }
    (tmp_path / "invoice.json").write_text(json.dumps(incomplete))
    return tmp_path


class TestTemplateServiceLoadTemplates:
    """Tests for TemplateService.load_templates."""

    def test_loads_valid_templates(self, tmp_templates_dir):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        templates = service.load_templates(tmp_templates_dir)

        assert len(templates) == 2
        assert all(isinstance(t, TemplateResponse) for t in templates)

        types = {t.type for t in templates}
        assert "invoice" in types
        assert "receipt" in types

    def test_invoice_template_has_correct_fields(self, tmp_templates_dir):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        templates = service.load_templates(tmp_templates_dir)

        invoice = next(t for t in templates if t.type == "invoice")
        assert invoice.name == "Invoice"
        assert "invoice_number" in invoice.required_fields
        assert "vendor_name" in invoice.required_fields
        assert "due_date" in invoice.optional_fields

    def test_skips_invalid_json_files(self, dir_with_invalid_json):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        templates = service.load_templates(dir_with_invalid_json)

        # Should load the valid one and skip the broken one
        assert len(templates) == 1
        assert templates[0].type == "invoice"

    def test_skips_files_with_missing_schema_fields(self, dir_with_missing_fields):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        templates = service.load_templates(dir_with_missing_fields)

        # Missing required fields in schema -- should be skipped
        assert len(templates) == 0

    def test_returns_empty_for_nonexistent_directory(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        templates = service.load_templates(tmp_path / "nonexistent")

        assert templates == []

    def test_returns_empty_for_empty_directory(self, tmp_path):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        templates = service.load_templates(tmp_path)

        assert templates == []

    def test_ignores_non_json_files(self, tmp_templates_dir):
        from docmind.modules.templates.services import TemplateService

        # Add a non-JSON file
        (tmp_templates_dir / "README.md").write_text("# Templates")

        service = TemplateService()
        templates = service.load_templates(tmp_templates_dir)

        assert len(templates) == 2  # Only the 2 JSON files


class TestTemplateServiceGetTemplate:
    """Tests for TemplateService.get_template."""

    def test_returns_template_by_type(self, tmp_templates_dir):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        service.load_templates(tmp_templates_dir)

        result = service.get_template("invoice")

        assert result is not None
        assert result.type == "invoice"

    def test_returns_none_for_unknown_type(self, tmp_templates_dir):
        from docmind.modules.templates.services import TemplateService

        service = TemplateService()
        service.load_templates(tmp_templates_dir)

        result = service.get_template("unknown_type")

        assert result is None


class TestTemplateDataFiles:
    """Tests that the actual template JSON files in data/templates/ are valid."""

    def test_all_template_files_are_valid(self):
        from docmind.modules.templates.services import TemplateService

        templates_dir = Path(__file__).resolve().parents[5] / "data" / "templates"
        if not templates_dir.exists():
            pytest.skip("data/templates/ directory not found")

        service = TemplateService()
        templates = service.load_templates(templates_dir)

        assert len(templates) >= 4, f"Expected at least 4 templates, got {len(templates)}"

        expected_types = {"invoice", "receipt", "contract", "id_document"}
        loaded_types = {t.type for t in templates}
        for expected in expected_types:
            assert expected in loaded_types, f"Missing template type: {expected}"

    def test_invoice_template_has_required_fields(self):
        from docmind.modules.templates.services import TemplateService

        templates_dir = Path(__file__).resolve().parents[5] / "data" / "templates"
        if not templates_dir.exists():
            pytest.skip("data/templates/ directory not found")

        service = TemplateService()
        templates = service.load_templates(templates_dir)
        invoice = next((t for t in templates if t.type == "invoice"), None)

        assert invoice is not None
        assert "invoice_number" in invoice.required_fields
        assert "date" in invoice.required_fields
        assert "total_amount" in invoice.required_fields
        assert "vendor_name" in invoice.required_fields
```

### Step 2: Implement (GREEN)

1. **Populate template JSON files** (`data/templates/invoice.json`, `receipt.json`, `contract.json`, `medical_report.json`, `id_document.json`) with full schema data matching the hardcoded `TEMPLATES` in the current handler.
2. **Create `modules/templates/services.py`**: `TemplateService` with `load_templates(dir)` and `get_template(type)`.
3. **Update handler**: Replace hardcoded `TEMPLATES` with `TemplateService().load_templates(...)` call, cached at module level.

### Step 3: Refactor (IMPROVE)

- Make templates directory configurable via `get_settings()`.
- Sort templates alphabetically by type for consistent API output.
- Add structlog context logging for loaded/skipped template counts.

## Acceptance Criteria

- [ ] All 5 template JSON files populated with correct schema data
- [ ] `TemplateService.load_templates` discovers and validates JSON files
- [ ] Invalid JSON files are skipped with warning log (no crash)
- [ ] `TemplateService.get_template` returns single template by type
- [ ] Handler uses `TemplateService` instead of hardcoded list
- [ ] `GET /templates` returns at least 5 templates (invoice, receipt, medical_report, contract, id_document)
- [ ] All unit tests pass

## Files Changed

- `data/templates/invoice.json` — populate with schema data
- `data/templates/receipt.json` — populate with schema data
- `data/templates/contract.json` — populate with schema data
- `data/templates/medical_report.json` — populate with schema data
- `data/templates/id_document.json` — populate with schema data
- `backend/src/docmind/modules/templates/services.py` — new file
- `backend/src/docmind/modules/templates/apiv1/handler.py` — use TemplateService
- `backend/tests/unit/modules/templates/test_template_service.py` — new

## Verification

```bash
cd backend
pytest tests/unit/modules/templates/test_template_service.py -v
```
