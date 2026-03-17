---
created: 2026-03-11
---

# Testing Conventions — DocMind-VLM

Test structure, naming rules, and patterns for unit, integration, and e2e tests.

---

## Test Directory Structure

```
backend/tests/
├── conftest.py                      # Shared fixtures (mock providers, mock Supabase)
├── fixtures/
│   ├── documents/                   # Test PDFs/images (invoice.jpg, receipt.png, etc.)
│   └── provider_responses/          # Deterministic VLM responses per provider
│       ├── dashscope/
│       │   ├── invoice_response.json
│       │   └── receipt_response.json
│       ├── openai/
│       │   ├── invoice_response.json
│       │   └── receipt_response.json
│       ├── google/
│       │   └── invoice_response.json
│       └── ollama/
│           └── invoice_response.json
├── unit/                            # Unit tests — mocked deps, mirrors src/ structure
│   ├── library/
│   │   ├── cv/
│   │   │   ├── test_deskew.py
│   │   │   ├── test_quality.py
│   │   │   └── test_preprocessing.py
│   │   ├── providers/
│   │   │   ├── test_dashscope_provider.py
│   │   │   ├── test_openai_provider.py
│   │   │   ├── test_google_provider.py
│   │   │   ├── test_ollama_provider.py
│   │   │   └── test_factory.py
│   │   └── pipeline/
│   │       ├── test_processing.py
│   │       └── test_chat.py
│   ├── modules/
│   │   ├── documents/
│   │   │   ├── test_services.py
│   │   │   ├── test_repositories.py
│   │   │   └── test_usecase.py
│   │   ├── extractions/
│   │   │   ├── test_services.py
│   │   │   └── test_repositories.py
│   │   ├── chat/
│   │   │   ├── test_services.py
│   │   │   └── test_repositories.py
│   │   └── templates/
│   │       └── test_services.py
│   └── core/
│       ├── test_config.py
│       └── test_auth.py
├── integration/                     # Integration tests — real Supabase test instance
│   ├── conftest.py                  # Test database fixtures
│   └── modules/
│       ├── documents/
│       │   └── test_handler.py
│       ├── extractions/
│       │   └── test_handler.py
│       ├── chat/
│       │   └── test_handler.py
│       └── health/
│           └── test_handler.py
└── e2e/                             # End-to-end — full stack
    ├── processing/
    │   ├── test_upload_extract.py
    │   └── test_comparison.py
    └── chat/
        └── test_chat_flow.py
```

---

## Test Philosophy

| Layer | Mocked? | Speed | Purpose |
| --- | --- | --- | --- |
| `unit/` | Yes (all external deps — VLM, Supabase, storage) | Fast (<1s each) | Test logic in isolation |
| `integration/` | Partial (VLM mocked, real test Supabase) | Medium (1-5s) | Test API surface, auth flow, DB queries |
| `e2e/` | **No** (real running stack) | Slow (seconds per test) | Test critical user flows end-to-end |

---

## Tools & Dependencies

```toml
# pyproject.toml
[tool.poetry.group.test.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-cov = "^5.0"
httpx = "^0.27"               # FastAPI async test client
pytest-mock = "^3.12"         # mocker fixture
factory-boy = "^3.3"          # Test data factories
aiosqlite = "^0.20"           # In-memory SQLite for async DB tests

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
```

Run tests:
```bash
# All backend tests
cd backend && poetry run pytest tests/ --cov=src --cov-report=term-missing

# By layer
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v

# Coverage gate
poetry run pytest tests/ --cov=src --cov-fail-under=80

# Single module
poetry run pytest tests/unit/library/cv/ -v
poetry run pytest tests/unit/modules/documents/ -v
```

---

## Unit Tests (`tests/unit/`)

Test one function/class in isolation. Mock **all** external dependencies (VLM providers, Supabase, storage).

### Naming

- File: `test_{module_name}.py`
- Class: `Test{ClassName}` (optional — use classes for grouping related tests)
- Function: `test_{what}_{condition}_{expected_result}`

```python
def test_correct_skew_with_tilted_image_returns_straightened(): ...
def test_score_quality_with_blurry_image_returns_low_score(): ...
def test_factory_with_unknown_name_raises_value_error(): ...
def test_extract_node_calls_provider_with_correct_prompt(): ...
```

### Example: `tests/unit/library/cv/test_deskew.py`

```python
"""Unit tests for docmind/library/cv/deskew.py"""
import numpy as np
import pytest

from docmind.library.cv.deskew import correct_skew, detect_skew, detect_and_correct


class TestCorrectSkew:
    def test_returns_new_array(self):
        """correct_skew returns a new ndarray, does not mutate input."""
        image = np.zeros((100, 100), dtype=np.uint8)
        result = correct_skew(image, 5.0)
        assert result is not image
        assert isinstance(result, np.ndarray)

    def test_preserves_dimensions(self):
        """correct_skew output has same shape as input."""
        image = np.random.randint(0, 255, (200, 300), dtype=np.uint8)
        result = correct_skew(image, 3.0)
        assert result.shape == image.shape


class TestDetectSkew:
    def test_returns_float(self):
        """detect_skew returns a float angle."""
        image = np.zeros((100, 100), dtype=np.uint8)
        angle = detect_skew(image)
        assert isinstance(angle, float)

    def test_angle_within_range(self):
        """Detected skew angle should be within [-45, 45] degrees."""
        image = np.random.randint(0, 255, (200, 300), dtype=np.uint8)
        angle = detect_skew(image)
        assert -45.0 <= angle <= 45.0
```

### Example: `tests/unit/library/providers/test_factory.py`

```python
"""Unit tests for docmind/library/providers/factory.py"""
import pytest
from unittest.mock import patch

from docmind.library.providers.factory import get_vlm_provider


class TestGetVLMProvider:
    @patch("docmind.library.providers.factory.get_settings")
    def test_dashscope_by_config(self, mock_settings):
        mock_settings.return_value.VLM_PROVIDER = "dashscope"
        mock_settings.return_value.DASHSCOPE_API_KEY = "test-key"
        provider = get_vlm_provider()
        assert provider.provider_name == "DashScope"

    @patch("docmind.library.providers.factory.get_settings")
    def test_unknown_provider_raises_value_error(self, mock_settings):
        mock_settings.return_value.VLM_PROVIDER = "nonexistent"
        with pytest.raises(ValueError, match="Unknown VLM provider"):
            get_vlm_provider()
```

---

## VLM Provider Mocking Strategy

VLM providers are expensive and non-deterministic. Mock them consistently across all test layers.

### `MockVLMProvider` class

```python
# tests/conftest.py
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockVLMProvider:
    """Deterministic VLM provider for testing."""

    def __init__(self, responses_dir: str = "dashscope") -> None:
        self._responses_dir = FIXTURES_DIR / "provider_responses" / responses_dir

    @property
    def provider_name(self) -> str:
        return "Mock"

    @property
    def model_name(self) -> str:
        return "mock-vlm"

    async def extract(
        self,
        images: list,
        prompt: str,
        schema: dict | None = None,
    ) -> dict:
        """Return deterministic extraction from fixture file."""
        return {
            "content": '{"invoice_number": "INV-2024-001"}',
            "structured_data": {
                "fields": [
                    {"field_key": "invoice_number", "field_value": "INV-2024-001", "confidence": 0.95},
                ],
                "document_type": "invoice",
            },
            "confidence": 0.92,
            "model": "mock-vlm",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "raw_response": {},
        }

    async def classify(self, image, categories: list[str]) -> dict:
        return {
            "content": "",
            "structured_data": {"document_type": categories[0], "confidence": 0.9},
            "confidence": 0.9,
            "model": "mock-vlm",
            "usage": {"input_tokens": 50, "output_tokens": 10},
            "raw_response": {},
        }

    async def chat(self, images, message, history, system_prompt) -> dict:
        return {
            "content": "Based on the document, the invoice number is INV-2024-001.",
            "structured_data": {},
            "confidence": 0.85,
            "model": "mock-vlm",
            "usage": {"input_tokens": 200, "output_tokens": 30},
            "raw_response": {},
        }

    async def health_check(self) -> bool:
        return True

    def load_fixture(self, template_type: str) -> dict:
        """Load a specific fixture response by template type."""
        fixture_path = self._responses_dir / f"{template_type}_response.json"
        if fixture_path.exists():
            return json.loads(fixture_path.read_text())
        return {}
```

### Fixture files

```json
// tests/fixtures/provider_responses/dashscope/invoice_response.json
{
    "fields": [
        {"field_key": "invoice_number", "field_value": "INV-2024-001", "confidence": 0.95},
        {"field_key": "date", "field_value": "2024-01-15", "confidence": 0.92},
        {"field_key": "total_amount", "field_value": "1,500.00", "confidence": 0.88},
        {"field_key": "vendor_name", "field_value": "Test Vendor Corp", "confidence": 0.96}
    ],
    "document_type": "invoice"
}
```

### Shared fixtures: `tests/conftest.py`

```python
"""Shared fixtures for all test layers."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_vlm_provider() -> MockVLMProvider:
    """Mock VLM provider returning deterministic responses."""
    return MockVLMProvider()


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for storage operations (Auth + Storage only)."""
    mock = MagicMock()
    mock.storage.from_.return_value.upload.return_value = {"Key": "documents/test.jpg"}
    mock.storage.from_.return_value.download.return_value = b"fake-image-bytes"
    return mock


@pytest.fixture
async def db_session():
    """In-memory SQLite async session for testing (replaces real Supabase Postgres)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from docmind.dbase.psql.core.base import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_document() -> dict:
    """Sample document record for testing."""
    return {
        "id": "doc-001",
        "user_id": "user-abc-123",
        "filename": "invoice.jpg",
        "file_type": "jpg",
        "file_size": 524288,
        "status": "uploaded",
        "storage_path": "documents/user-abc-123/invoice.jpg",
    }


@pytest.fixture
def sample_extraction() -> dict:
    """Sample extraction result for testing."""
    return {
        "id": "ext-001",
        "document_id": "doc-001",
        "template_type": "invoice",
        "provider": "dashscope",
        "fields": [
            {"field_key": "invoice_number", "field_value": "INV-2024-001", "confidence": 0.92},
        ],
    }


@pytest.fixture
def mock_jwt_payload() -> dict:
    """Valid JWT payload for testing authenticated routes."""
    return {
        "sub": "user-abc-123",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": 9999999999,
    }


@pytest.fixture
def auth_headers(mock_jwt_payload) -> dict:
    """Authorization headers with a valid test JWT."""
    import jwt as pyjwt
    token = pyjwt.encode(mock_jwt_payload, "test-jwt-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_jwt_secret(monkeypatch):
    """Set test JWT secret for all tests."""
    monkeypatch.setattr(
        "docmind.core.config.Settings.supabase_jwt_secret",
        "test-jwt-secret",
    )
```

---

## Integration Tests (`tests/integration/`)

Test against a **real Supabase test instance**. VLM providers remain mocked.

### Test Setup

```python
# tests/integration/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport

from docmind.main import create_app


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
async def client(app, auth_headers):
    """Async test client with auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=auth_headers) as c:
        yield c
```

### Example: `tests/integration/modules/documents/test_handler.py`

```python
"""Integration tests for documents API handler."""
import pytest
from httpx import AsyncClient, ASGITransport

from docmind.main import create_app


@pytest.mark.asyncio
async def test_upload_document_returns_201(client):
    """POST /api/v1/documents returns 201 with document metadata."""
    response = await client.post(
        "/api/v1/documents",
        files={"file": ("invoice.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "invoice.jpg"
    assert data["status"] == "uploaded"


@pytest.mark.asyncio
async def test_get_document_returns_404_for_other_user(client):
    """GET /api/v1/documents/{id} returns 404 for document owned by another user."""
    response = await client.get("/api/v1/documents/doc-other")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_returns_200_without_auth(app):
    """GET /api/v1/health returns 200 with no auth required."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
```

---

## E2E Tests (`tests/e2e/`)

End-to-end tests run against the full deployed stack (frontend + backend + Supabase). These test critical user flows.

### Example: `tests/e2e/processing/test_upload_extract.py`

```python
"""E2E test: document upload and extraction flow."""
import pytest
import httpx


@pytest.mark.e2e
async def test_upload_and_extract_invoice():
    """Upload an invoice, trigger processing, verify extraction results."""
    base_url = "http://localhost:8000"

    # Upload document
    async with httpx.AsyncClient(base_url=base_url) as client:
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("invoice.jpg", open("tests/fixtures/documents/invoice.jpg", "rb"), "image/jpeg")},
            headers={"Authorization": "Bearer <test-token>"},
        )
        assert upload_response.status_code == 201
        doc_id = upload_response.json()["id"]

        # Trigger processing
        process_response = await client.post(
            f"/api/v1/documents/{doc_id}/process",
            json={"template_type": "invoice"},
            headers={"Authorization": "Bearer <test-token>"},
        )
        assert process_response.status_code == 202
```

---

## Test Data Factories

Use `factory-boy` for generating consistent test entities:

```python
# tests/factories.py
import factory


class DocumentFactory(factory.DictFactory):
    id = factory.Sequence(lambda n: f"doc-{n:03d}")
    user_id = "user-abc-123"
    filename = factory.Sequence(lambda n: f"document-{n}.jpg")
    file_type = "jpg"
    file_size = 524288
    status = "uploaded"
    storage_path = factory.LazyAttribute(lambda o: f"documents/{o.user_id}/{o.filename}")


class ExtractionFactory(factory.DictFactory):
    id = factory.Sequence(lambda n: f"ext-{n:03d}")
    document_id = factory.Sequence(lambda n: f"doc-{n:03d}")
    template_type = "invoice"
    provider = "dashscope"
    confidence = 0.92
    fields = factory.LazyFunction(lambda: [
        {"field_key": "invoice_number", "field_value": "INV-2024-001", "confidence": 0.95},
    ])


# Usage in tests
documents = DocumentFactory.create_batch(5)
document = DocumentFactory(filename="custom.pdf", status="processing")
extraction = ExtractionFactory(provider="openai", confidence=0.88)
```

---

## Coverage Requirements

| Layer | Min Coverage |
| --- | --- |
| `library/cv/` (deskew, quality, preprocessing) | 90% |
| `library/providers/` (all VLM providers) | 85% |
| `library/pipeline/` (processing + chat) | 80% |
| `modules/*/services.py` (all module services) | 80% |
| `modules/*/repositories.py` (all repositories) | 80% |
| `modules/*/apiv1/handler.py` (all handlers) | 80% |
| `core/` (config, auth, logging) | 80% |
| **Overall backend** | **80%** |

```bash
poetry run pytest tests/unit/ tests/integration/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-fail-under=80
```

---

## CI Strategy

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Poetry
        run: pip install poetry

      - name: Install backend deps
        working-directory: backend
        run: poetry install

      - name: Run linting
        working-directory: backend
        run: |
          poetry run ruff check src/
          poetry run mypy src/

      - name: Run unit tests
        working-directory: backend
        run: poetry run pytest tests/unit/ -v --cov=src

      - name: Run integration tests
        working-directory: backend
        env:
          SUPABASE_URL: ${{ secrets.TEST_SUPABASE_URL }}
          SUPABASE_JWT_SECRET: test-jwt-secret
          SUPABASE_SERVICE_KEY: ${{ secrets.TEST_SUPABASE_SERVICE_KEY }}
        run: poetry run pytest tests/integration/ -v

      - name: Coverage gate
        working-directory: backend
        run: poetry run pytest tests/unit/ tests/integration/ --cov=src --cov-fail-under=80

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install frontend deps
        working-directory: frontend
        run: npm ci

      - name: Lint & typecheck
        working-directory: frontend
        run: |
          npm run lint
          npm run typecheck

  e2e:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [backend-tests, frontend-tests]
    steps:
      - uses: actions/checkout@v4

      - name: Start full stack
        run: docker compose up --build -d && sleep 30

      - name: Run E2E tests
        working-directory: backend
        run: poetry run pytest tests/e2e/ -v -m e2e

      - name: Stop stack
        if: always()
        run: docker compose down
```

---

## Related Conventions

- [[projects/docmind-vlm/specs/conventions/python-conventions]] — Code style, error handling patterns
- [[projects/docmind-vlm/specs/conventions/python-module-structure]] — Architecture layers to test
- [[projects/docmind-vlm/specs/conventions/security]] — JWT auth testing patterns
