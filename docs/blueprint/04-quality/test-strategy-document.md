# Test Strategy Document: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Quality Assurance

---

## 1. Test Architecture

Three-level test suite targeting > 80% code coverage:

### Level 1: Unit Tests (Fast, Logic-Focused)
**Framework:** pytest + pytest-asyncio
**Scope:** Individual functions and classes in isolation
**Target:** All business logic, data transformations, utilities

| Module | What to test |
|---|---|
| `app/cv/deskew.py` | Skew detection accuracy, correction at various angles, threshold behavior |
| `app/cv/quality.py` | Blur/noise/contrast scoring against known images, grid-based region mapping |
| `app/cv/preprocessing.py` | PDF-to-image conversion, image normalization |
| `app/providers/dashscope_provider.py` | Request formatting, response parsing, retry logic (mocked API) |
| `app/providers/openai_provider.py` | Request formatting, response parsing (mocked API) |
| `app/providers/google_provider.py` | Request formatting, response parsing (mocked API) |
| `app/providers/ollama_provider.py` | Request formatting, response parsing (mocked API) |
| `app/providers/provider_factory.py` | Correct provider selection by env var, missing key errors |
| `app/pipeline/processing/postprocess.py` | Confidence merging formula, template validation, missing field detection |
| `app/pipeline/chat/cite.py` | Citation extraction, bounding box matching |
| `app/pipeline/chat/router.py` | Intent classification mapping |
| `app/services/*.py` | Business logic with mocked DB and providers |
| `app/core/auth.py` | JWT validation, user extraction, expired token rejection |

### Level 2: Integration Tests (API/Service-Focused)
**Framework:** pytest + httpx (async test client for FastAPI)
**Scope:** API endpoints with real database (test Postgres), mocked VLM providers

| Test area | What to test |
|---|---|
| Document CRUD | POST/GET/DELETE /api/documents — correct status codes, RLS enforcement |
| Upload flow | File validation (type, size), storage path creation, metadata persistence |
| Processing trigger | POST /api/documents/{id}/process — pipeline starts, SSE progress events received |
| Extraction retrieval | GET extraction results — correct JSON structure, field count, confidence scores |
| Chat flow | POST /api/documents/{id}/chat — response received, citations present, history persisted |
| Comparison | GET comparison — diff computed correctly between enhanced and baseline |
| Auth enforcement | All protected endpoints return 401 without JWT, 403 for wrong user's documents |
| Template API | GET /api/templates — list returned; GET /api/templates/{type} — schema returned |

### Level 3: End-to-End Tests (System-Focused)
**Framework:** Playwright (browser automation)
**Scope:** Full user flows through the real frontend + backend

| Scenario | Steps |
|---|---|
| **Happy path: upload + extract + chat** | Login → upload demo invoice → wait for processing → verify extraction displayed → send chat message → verify response with citation |
| **Landing page** | Visit root → verify hero, features, CTA buttons → click sign in → verify redirect |
| **Template mode** | Login → upload certificate → select "certificate" template → verify required fields extracted or flagged |
| **Confidence overlay** | Login → open processed document → toggle confidence overlay → verify heatmap visible |
| **Comparison view** | Login → open demo document → click "Compare" → verify side-by-side displayed |
| **Error handling** | Login → upload invalid file → verify error message displayed |
| **Auth protection** | Visit dashboard URL without login → verify redirect to login |

## 2. Test Data Strategy

### Demo Documents (Committed to repo: `demo/documents/`)
- `invoice_simple.pdf` — Clean digital invoice, English
- `invoice_complex.png` — Scanned invoice with nested table, mixed language
- `certificate_scan.jpg` — Scanned multilingual certificate (English + Bahasa), slightly skewed
- `receipt_photo.jpg` — Tilted, partially cut off, mixed language receipt
- `contract_digital.pdf` — Clean digital contract with clauses

### Pre-Computed Baselines (Committed to repo: `demo/baselines/`)
- Raw VLM output for each demo document (for comparison view)
- Generated once, stored as JSON fixtures

### Test Fixtures
- Factory functions for creating test documents, fields, chat messages
- Mocked VLM provider that returns deterministic responses
- Test Postgres database (separate from production, created/destroyed per test run)

## 3. Test Coverage Goals

| Layer | Target | Rationale |
|---|---|---|
| CV module (`app/cv/`) | > 90% | Core differentiator — must be reliable |
| VLM providers (`app/providers/`) | > 85% | All providers must handle errors consistently |
| Pipeline (`app/pipeline/`) | > 80% | Complex orchestration, test state transitions |
| Services (`app/services/`) | > 80% | Business logic |
| API routes (`app/api/`) | > 80% | Input validation, auth enforcement |
| Frontend components | > 60% | React Testing Library for key interactions |
| Overall | > 80% | Portfolio standard |

## 4. CI Pipeline

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]

jobs:
  backend-tests:
    - Install Python dependencies
    - Run pytest with coverage
    - Fail if coverage < 80%
    - Upload coverage report

  frontend-tests:
    - Install Node dependencies
    - Run vitest with coverage
    - Run Playwright E2E tests
    - Upload test artifacts (screenshots on failure)

  lint:
    - Backend: ruff (Python linter + formatter)
    - Frontend: eslint + prettier
    - Type checking: mypy (backend) + tsc --noEmit (frontend)

  build:
    - Docker Compose build (verify all services build successfully)
```

## 5. Testing VLM Providers

VLM providers are tested with **mocked API responses** — no real API calls in CI:

- Each provider has a `tests/fixtures/{provider}_responses/` directory with sample responses
- Mock responses cover: successful extraction, classification, chat, error responses, rate limit responses
- Integration tests use a `MockVLMProvider` that returns deterministic results
- Provider factory correctly falls back when env vars are missing

**Manual smoke test (not in CI):** Run against real DashScope API with a single demo document to verify end-to-end. Documented in `Makefile` as `make test-live`.

---
#testing #quality-assurance #strategy #docmind-vlm
