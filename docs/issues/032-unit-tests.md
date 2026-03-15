# Issue #32: Comprehensive Unit Tests — Backend + Frontend

## Summary

Write comprehensive unit tests targeting 80%+ overall coverage. Backend: test all services, repositories, CV library functions, VLM provider implementations, pipeline nodes, Pydantic schemas, and auth utilities. Frontend: test React hooks, Zustand stores, utility functions, and key components. All external dependencies (VLM providers, Supabase, database) are mocked. Tests follow the naming convention `test_{what}_{condition}_{expected_result}`.

## Context

- **Phase**: 7 — Testing + Polish
- **Priority**: P0
- **Labels**: `phase-7-testing`, `backend`, `frontend`, `tdd`
- **Dependencies**: #25-#31 (all frontend implementation), all backend implementation issues
- **Branch**: `feat/32-unit-tests`
- **Estimated scope**: L

## Specs to Read

- `specs/conventions/testing.md` — Full test structure, naming, coverage requirements, MockVLMProvider, fixtures
- `specs/conventions/python-conventions.md` — Code style context for what to test
- `specs/conventions/python-module-structure.md` — Layer rules (what each layer should do)
- `specs/backend/services.md` — Service logic to verify
- `specs/backend/cv.md` — CV functions to test
- `specs/backend/providers.md` — Provider protocol to verify

## Current State (Scaffold)

**Backend test directories exist but are empty:**
```
backend/tests/
├── conftest.py                      # Has sample_document_data and mock_user fixtures only
├── unit/
│   ├── conftest.py                  # Empty
│   ├── core/                        # Empty
│   ├── library/
│   │   ├── cv/                      # Empty
│   │   ├── pipeline/                # Empty
│   │   └── providers/               # Empty
│   └── modules/
│       ├── chat/                    # Empty
│       ├── documents/               # Empty
│       ├── extractions/             # Empty
│       └── templates/               # Empty
├── fixtures/
│   ├── documents/                   # Empty
│   └── provider_responses/
│       ├── dashscope/               # Empty
│       ├── google/                  # Empty
│       └── openai/                  # Empty
```

**`backend/tests/conftest.py`** (minimal):
```python
"""
Shared test fixtures for DocMind-VLM backend tests.
"""
import pytest


@pytest.fixture
def sample_document_data() -> dict:
    return {
        "filename": "test_invoice.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "storage_path": "test-user/test-doc/test_invoice.pdf",
    }


@pytest.fixture
def mock_user() -> dict:
    return {
        "id": "test-user-id",
        "email": "test@example.com",
    }
```

**Frontend: no test files exist yet.**

## Requirements

### Functional

1. **Backend unit tests** covering every module:
   - `core/config.py` — Settings loading, env var validation, `get_settings()` caching
   - `core/auth.py` — JWT decode, audience validation, expired token, missing token, invalid signature
   - `library/cv/deskew.py` — `detect_skew()`, `correct_skew()`, `detect_and_correct()` with numpy arrays
   - `library/cv/quality.py` — `score_quality()` with various image qualities
   - `library/cv/preprocessing.py` — preprocessing pipeline functions
   - `library/providers/factory.py` — `get_vlm_provider()` for each provider name, unknown raises ValueError
   - `library/providers/dashscope.py` — extract, classify, chat, health_check (mocked HTTP)
   - `library/providers/openai.py` — same as above
   - `library/providers/google.py` — same as above
   - `library/providers/ollama.py` — same as above
   - `library/pipeline/processing.py` — pipeline node functions with mocked provider
   - `library/pipeline/chat.py` — chat pipeline with mocked provider
   - `modules/documents/services.py` — document CRUD logic
   - `modules/documents/repositories.py` — query building, user_id filtering
   - `modules/documents/usecase.py` — orchestration of service + repo
   - `modules/extractions/services.py` — extraction result handling
   - `modules/extractions/repositories.py` — extraction queries
   - `modules/chat/services.py` — chat message handling
   - `modules/chat/repositories.py` — chat history queries
   - `modules/templates/services.py` — template loading
2. **Frontend unit tests**:
   - `stores/auth-store.ts` — setSession, setIsLoading, user derived from session
   - `stores/workspace-store.ts` — all actions, zoom clamping, resetWorkspace
   - `hooks/useDocuments.ts` — query key structure, invalidation on mutation
   - `hooks/useExtraction.ts` — enabled flag, query keys
   - `hooks/useChat.ts` — query structure, invalidation
   - `lib/api.ts` — apiFetch error handling, URL construction
   - `components/workspace/ConfidenceBadge.tsx` — render correct color for each threshold

### Non-Functional

- Overall backend coverage >= 80%
- `library/cv/` coverage >= 90%
- `library/providers/` coverage >= 85%
- All tests run in < 30 seconds (unit tests should be fast)
- No external service calls (everything mocked)

## Implementation Plan

### Backend Test Files to Create

**`backend/tests/conftest.py`** (expand):
```python
"""Shared test fixtures for DocMind-VLM backend tests."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockVLMProvider:
    """Deterministic VLM provider for testing."""

    @property
    def provider_name(self) -> str:
        return "Mock"

    @property
    def model_name(self) -> str:
        return "mock-vlm"

    async def extract(self, images, prompt, schema=None):
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

    async def classify(self, image, categories):
        return {
            "content": "",
            "structured_data": {"document_type": categories[0], "confidence": 0.9},
            "confidence": 0.9,
            "model": "mock-vlm",
            "usage": {"input_tokens": 50, "output_tokens": 10},
            "raw_response": {},
        }

    async def chat(self, images, message, history, system_prompt):
        return {
            "content": "The invoice number is INV-2024-001.",
            "structured_data": {},
            "confidence": 0.85,
            "model": "mock-vlm",
            "usage": {"input_tokens": 200, "output_tokens": 30},
            "raw_response": {},
        }

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def mock_vlm_provider():
    return MockVLMProvider()


@pytest.fixture
def mock_supabase_client():
    mock = MagicMock()
    mock.storage.from_.return_value.upload.return_value = {"Key": "documents/test.jpg"}
    mock.storage.from_.return_value.download.return_value = b"fake-image-bytes"
    return mock


@pytest.fixture
async def db_session():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from docmind.dbase.sqlalchemy.base import Base
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def sample_document_data():
    return {
        "filename": "test_invoice.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "storage_path": "test-user/test-doc/test_invoice.pdf",
    }


@pytest.fixture
def mock_user():
    return {"id": "test-user-id", "email": "test@example.com"}


@pytest.fixture
def mock_jwt_payload():
    return {
        "sub": "test-user-id",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": 9999999999,
    }


@pytest.fixture
def auth_headers(mock_jwt_payload):
    import jwt as pyjwt
    token = pyjwt.encode(mock_jwt_payload, "test-jwt-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
```

### Key Test Files

**`backend/tests/unit/core/test_auth.py`**:
```python
"""Unit tests for JWT authentication."""
import pytest
from unittest.mock import patch


class TestDecodeJWT:
    def test_valid_token_returns_user_data(self, mock_jwt_payload, auth_headers): ...
    def test_expired_token_raises_401(self): ...
    def test_invalid_signature_raises_401(self): ...
    def test_missing_token_raises_401(self): ...
    def test_wrong_audience_raises_401(self): ...
    def test_missing_sub_claim_raises_401(self): ...
```

**`backend/tests/unit/library/cv/test_deskew.py`**:
```python
"""Unit tests for deskew functions."""
import numpy as np
import pytest
from docmind.library.cv.deskew import correct_skew, detect_skew


class TestDetectSkew:
    def test_returns_float(self): ...
    def test_angle_within_range(self): ...
    def test_straight_image_returns_near_zero(self): ...

class TestCorrectSkew:
    def test_returns_new_array(self): ...
    def test_preserves_dimensions(self): ...
    def test_zero_angle_returns_similar(self): ...
```

**`backend/tests/unit/library/cv/test_quality.py`**:
```python
class TestScoreQuality:
    def test_returns_float_between_0_and_1(self): ...
    def test_blank_image_returns_low_score(self): ...
    def test_high_contrast_image_returns_high_score(self): ...
```

**`backend/tests/unit/library/providers/test_factory.py`**:
```python
class TestGetVLMProvider:
    def test_dashscope_by_config(self, mock_settings): ...
    def test_openai_by_config(self, mock_settings): ...
    def test_google_by_config(self, mock_settings): ...
    def test_ollama_by_config(self, mock_settings): ...
    def test_unknown_provider_raises_value_error(self, mock_settings): ...
```

**`backend/tests/unit/modules/documents/test_services.py`**:
```python
class TestDocumentService:
    async def test_create_document_returns_document(self): ...
    async def test_get_document_filters_by_user_id(self): ...
    async def test_delete_document_removes_record(self): ...
    async def test_list_documents_returns_paginated(self): ...
```

### Frontend Test Files

**`frontend/src/stores/__tests__/auth-store.test.ts`**:
```typescript
import { useAuthStore } from "@/stores/auth-store";

describe("auth-store", () => {
  beforeEach(() => {
    useAuthStore.setState({ session: null, user: null, isLoading: true });
  });

  it("setSession updates session and derives user", () => {
    const mockSession = { user: { id: "u1", email: "a@b.com" } } as any;
    useAuthStore.getState().setSession(mockSession);
    expect(useAuthStore.getState().session).toBe(mockSession);
    expect(useAuthStore.getState().user?.id).toBe("u1");
  });

  it("setSession with null clears user", () => {
    useAuthStore.getState().setSession(null);
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("setIsLoading updates loading state", () => {
    useAuthStore.getState().setIsLoading(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});
```

**`frontend/src/stores/__tests__/workspace-store.test.ts`**:
```typescript
import { useWorkspaceStore } from "@/stores/workspace-store";

describe("workspace-store", () => {
  beforeEach(() => {
    useWorkspaceStore.getState().resetWorkspace();
  });

  it("setActiveTab updates tab", () => { ... });
  it("setOverlayMode updates mode", () => { ... });
  it("selectField updates selectedFieldId", () => { ... });
  it("setZoomLevel clamps to min 0.25", () => { ... });
  it("setZoomLevel clamps to max 5.0", () => { ... });
  it("resetWorkspace restores initial state", () => { ... });
});
```

**`frontend/src/components/workspace/__tests__/ConfidenceBadge.test.tsx`**:
```typescript
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "../ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("renders High for confidence >= 0.8", () => { ... });
  it("renders Medium for confidence 0.5-0.79", () => { ... });
  it("renders Low for confidence < 0.5", () => { ... });
  it("shows percentage when showValue is true", () => { ... });
});
```

### Test Fixture Files to Create

**`backend/tests/fixtures/provider_responses/dashscope/invoice_response.json`**:
```json
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

### Coverage Requirements

| Module | Target | Test File |
|--------|--------|-----------|
| `library/cv/` | 90% | `tests/unit/library/cv/test_*.py` |
| `library/providers/` | 85% | `tests/unit/library/providers/test_*.py` |
| `library/pipeline/` | 80% | `tests/unit/library/pipeline/test_*.py` |
| `modules/*/services.py` | 80% | `tests/unit/modules/*/test_services.py` |
| `modules/*/repositories.py` | 80% | `tests/unit/modules/*/test_repositories.py` |
| `core/` | 80% | `tests/unit/core/test_*.py` |
| **Overall** | **80%** | All unit tests |

## Acceptance Criteria

- [ ] Overall backend test coverage >= 80%
- [ ] `library/cv/` coverage >= 90%
- [ ] `library/providers/` coverage >= 85%
- [ ] All unit tests pass with `pytest tests/unit/ -v`
- [ ] No external API calls made during tests (all mocked)
- [ ] Test fixtures created for VLM provider responses
- [ ] MockVLMProvider in conftest.py covers extract, classify, chat, health_check
- [ ] Frontend store tests pass
- [ ] Frontend component tests pass
- [ ] Test naming follows `test_{what}_{condition}_{expected}` convention
- [ ] All tests run in < 30 seconds total

## Files Changed

### Backend (new test files):
- `backend/tests/conftest.py` — expand with full fixtures
- `backend/tests/unit/core/test_config.py`
- `backend/tests/unit/core/test_auth.py`
- `backend/tests/unit/library/cv/test_deskew.py`
- `backend/tests/unit/library/cv/test_quality.py`
- `backend/tests/unit/library/cv/test_preprocessing.py`
- `backend/tests/unit/library/providers/test_factory.py`
- `backend/tests/unit/library/providers/test_dashscope_provider.py`
- `backend/tests/unit/library/providers/test_openai_provider.py`
- `backend/tests/unit/library/providers/test_google_provider.py`
- `backend/tests/unit/library/providers/test_ollama_provider.py`
- `backend/tests/unit/library/pipeline/test_processing.py`
- `backend/tests/unit/library/pipeline/test_chat.py`
- `backend/tests/unit/modules/documents/test_services.py`
- `backend/tests/unit/modules/documents/test_repositories.py`
- `backend/tests/unit/modules/documents/test_usecase.py`
- `backend/tests/unit/modules/extractions/test_services.py`
- `backend/tests/unit/modules/extractions/test_repositories.py`
- `backend/tests/unit/modules/chat/test_services.py`
- `backend/tests/unit/modules/chat/test_repositories.py`
- `backend/tests/unit/modules/templates/test_services.py`
- `backend/tests/fixtures/provider_responses/dashscope/invoice_response.json`
- `backend/tests/fixtures/provider_responses/dashscope/receipt_response.json`
- `backend/tests/fixtures/provider_responses/openai/invoice_response.json`
- `backend/tests/fixtures/provider_responses/google/invoice_response.json`

### Frontend (new test files):
- `frontend/src/stores/__tests__/auth-store.test.ts`
- `frontend/src/stores/__tests__/workspace-store.test.ts`
- `frontend/src/components/workspace/__tests__/ConfidenceBadge.test.tsx`
- `frontend/src/hooks/__tests__/useDocuments.test.ts`
- `frontend/src/hooks/__tests__/useExtraction.test.ts`
- `frontend/src/hooks/__tests__/useChat.test.ts`

## Verification

```bash
# Backend
cd backend
poetry run pytest tests/unit/ -v --cov=src --cov-report=term-missing
poetry run pytest tests/unit/ --cov=src --cov-fail-under=80

# Frontend
cd frontend
npm run test -- --coverage
```
