# DocMind-VLM — Kickoff Prompt

> This file is addressed to Claude Code (or equivalent AI) bootstrapping this repository.
> Read it fully before touching any file.

---

## What This Project Is

**DocMind-VLM** is an intelligent document extraction and chat platform powered by Vision Language Models. Users upload PDFs or images, a VLM extracts structured fields with confidence scores and bounding boxes, and users can then chat with the document ("What is the invoice total?"). Think of it as "ChatPDF but with structured extraction, confidence overlays, and audit trails."

**Stack:**
- Backend: FastAPI + Python 3.11 + LangGraph + SQLAlchemy 2.x async + Supabase (Auth + Storage + Postgres)
- Frontend: Vite + React 18 + TypeScript 5 + shadcn/ui + Tailwind + React Query + Zustand
- VLM: Qwen-VL via DashScope (primary) — provider-agnostic, OpenAI/Google/Ollama also supported
- Infra: Docker Compose

---

## Your Primary Directive

**You are scaffolding the initial repository.** This means creating the full directory structure, all configuration files, all `__init__.py` files, and all stub implementations — but **not writing business logic yet**. The goal is a repo that:

1. Has every directory and file in place
2. `poetry install` succeeds in `backend/`
3. `npm install` succeeds in `frontend/`
4. `poetry run uvicorn docmind.main:app` starts the server (returns 200 on `/api/v1/health/ping`)
5. All imports resolve correctly — no `ModuleNotFoundError`
6. Test suite can be collected by pytest (zero failures, some skips are fine)

Do not implement pipeline logic, VLM calls, or CV algorithms in this phase. Stub them.

---

## Read These Specs First — In This Order

All specs live in `specs/`. Read them **before** generating any file.

```
1. specs/README.md                           ← directory map + quick reference
2. specs/system.md                           ← full repo layout, env vars, pyproject.toml, package.json, Docker, Makefile
3. specs/conventions/repository-overview.md  ← architecture diagram, import patterns, entry points
4. specs/conventions/python-conventions.md   ← PEP 8, type hints, async patterns, naming rules
5. specs/conventions/python-module-structure.md ← Handler→UseCase→Service→Repository layering
6. specs/conventions/security.md             ← JWT auth, file validation, never expose stack traces
7. specs/backend/api.md                      ← ALL endpoints, ALL Pydantic schemas, ORM models, error table
8. specs/backend/services.md                 ← Module layer pattern, all UseCase/Service/Repository signatures
9. specs/backend/cv.md                       ← CV library interfaces (stub implementations for scaffold)
10. specs/backend/providers.md               ← VLMProvider Protocol + factory (stub providers)
11. specs/backend/pipeline-processing.md     ← ProcessingState, graph nodes (stub for scaffold)
12. specs/backend/pipeline-chat.md           ← ChatState, graph nodes (stub for scaffold)
13. specs/frontend/api-client.md             ← lib/api.ts, lib/supabase.ts, types/api.ts (generate verbatim)
14. specs/frontend/state.md                  ← React Query hooks, Zustand stores
15. specs/frontend/components.md             ← Component tree, key component implementations
```

---

## Hard Rules — Never Violate These

### Python Package Root
```
backend/src/docmind/    ← ALL Python source lives here
```
Poetry is configured as `packages = [{include = "docmind", from = "src"}]`.
Pytest uses `pythonpath = ["src"]`.
**All imports use the full package path:**
```python
from docmind.core.config import get_settings        # CORRECT
from core.config import get_settings                # WRONG
from .config import get_settings                    # WRONG (except within same package)
```

### API Routes
All endpoints are under `/api/v1/`. The prefix is split:
- `main.py` mounts the aggregated router at `/api`
- `router.py` registers each module router at `/v1/{module}`

Final paths:
```
GET  /api/v1/health/ping
GET  /api/v1/health/status
POST /api/v1/documents
GET  /api/v1/documents
GET  /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
POST /api/v1/documents/{id}/process     ← SSE stream (POST body required)
GET  /api/v1/extractions/{document_id}
GET  /api/v1/extractions/{document_id}/audit
GET  /api/v1/extractions/{document_id}/overlay
GET  /api/v1/extractions/{document_id}/comparison
POST /api/v1/chat/{document_id}         ← SSE stream (POST body required)
GET  /api/v1/chat/{document_id}/history
GET  /api/v1/templates
```

### SSE Endpoints Are POST
`/api/v1/documents/{id}/process` and `/api/v1/chat/{document_id}` are **POST** endpoints that return `StreamingResponse` with `media_type="text/event-stream"`. They accept a JSON body. **Never make them GET.**

### Module Layer — Strict Separation
```
handler.py   → validates HTTP, calls usecase, serializes response. NO business logic.
usecase.py   → orchestrates service + repository calls. NO direct DB queries.
services.py  → business logic, calls library. NO direct DB access.
repositories.py → SQLAlchemy queries ONLY. Always filter by user_id.
```
Cross-module access only via `shared/` or at usecase level. Services never import from other modules.

### Settings
Always use `get_settings()` (cached via `@lru_cache`). Never instantiate `Settings()` directly. Never hardcode URLs, keys, or magic strings — everything comes from `core/config.py`.

### Error Handling
Never expose stack traces or internal errors in HTTP responses. Log server-side with structlog, return a generic message to the client. See error table in `specs/backend/api.md`.

### Supabase Client Scope
The Supabase client (`dbase/supabase/`) is **Auth + Storage ONLY**. All database queries go through SQLAlchemy (`dbase/sqlalchemy/`). Never query Supabase Postgres via the Supabase client.

---

## Scaffold Approach — Step by Step

### Phase 1: Repo Root
Create:
- `Makefile` — per `specs/system.md`
- `docker-compose.yml` — per `specs/system.md`
- `.env.example` — per `specs/system.md` env vars table
- `.gitignore` — standard Python + Node + secrets
- `README.md` — minimal (project name, one-liner, setup steps)
- `data/templates/` — create 5 empty JSON stubs: `invoice.json`, `receipt.json`, `medical_report.json`, `contract.json`, `id_document.json`
- `data/demo/documents/` and `data/demo/baselines/` — empty directories with `.gitkeep`

### Phase 2: Backend Scaffold
Create `backend/pyproject.toml` and `backend/poetry.toml` exactly as specified in `specs/system.md`.

Create every directory and `__init__.py` file in the `backend/src/docmind/` tree.

For each Python file, implement:
- **Leaf files** (`config.py`, `logging.py`, `auth.py`, `engine.py`, `base.py`, `models.py`, `client.py`, `storage.py`): implement fully — these have no external dependencies that need stubbing
- **Library files** (`cv/`, `providers/`, `pipeline/`): implement the correct function/class signatures with `raise NotImplementedError` bodies — the Protocol and TypedDict definitions go in verbatim
- **Module schemas** (`modules/*/schemas.py`): implement all Pydantic models verbatim from `specs/backend/api.md`
- **Module handlers** (`modules/*/apiv1/handler.py`): implement all routes with stubs — handlers call usecase but usecase returns a hardcoded stub response
- **Module usecases** (`modules/*/usecase.py`): stub methods that return minimal valid objects
- **Module services** (`modules/*/services.py`): stub methods with `raise NotImplementedError`
- **Module repositories** (`modules/*/repositories.py`): stub methods with `raise NotImplementedError`

Create `backend/alembic/` with `alembic.ini` and `env.py` (standard async setup pointing to `DATABASE_URL`).

Create `backend/tests/` directory tree with `conftest.py` stubs.

### Phase 3: Frontend Scaffold
Create `frontend/package.json` and config files (`vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`) exactly as specified in `specs/system.md`.

Generate these files **verbatim** from their specs — they are fully defined:
- `src/lib/supabase.ts` — from `specs/frontend/api-client.md`
- `src/lib/api.ts` — from `specs/frontend/api-client.md`
- `src/types/api.ts` — from `specs/frontend/api-client.md`

Scaffold with stub implementations:
- `src/App.tsx` — router setup (landing vs dashboard vs workspace routes)
- `src/main.tsx` — React entry point
- `src/index.css` — Tailwind directives + CSS variables
- `src/pages/LandingPage.tsx` — stub (`<div>Landing</div>`)
- `src/pages/Dashboard.tsx` — stub
- `src/pages/Workspace.tsx` — stub
- `src/stores/workspace-store.ts` — from `specs/frontend/state.md`
- `src/stores/auth-store.ts` — from `specs/frontend/state.md`
- `src/hooks/` — all React Query hooks from `specs/frontend/state.md`
- `src/components/ui/` — empty directory (shadcn will populate via CLI)
- `src/components/workspace/` — stub component files (one per component in `specs/frontend/components.md`)
- `src/components/landing/` — stub component files

---

## Key Files to Generate Verbatim

These files are fully specified — copy them exactly, do not improvise:

| File | Source |
|------|--------|
| `backend/src/docmind/main.py` | `specs/backend/api.md` → `main.py` section |
| `backend/src/docmind/router.py` | `specs/backend/api.md` → `router.py` section |
| `backend/src/docmind/core/config.py` | `specs/system.md` → config section |
| `backend/src/docmind/core/auth.py` | `specs/backend/api.md` → auth section |
| `backend/src/docmind/core/dependencies.py` | `specs/backend/api.md` → dependencies section |
| `backend/src/docmind/dbase/sqlalchemy/engine.py` | `specs/backend/api.md` → engine section |
| `backend/src/docmind/dbase/sqlalchemy/base.py` | `specs/backend/api.md` → base section |
| `backend/src/docmind/dbase/sqlalchemy/models.py` | `specs/backend/api.md` → models section |
| `backend/src/docmind/dbase/supabase/client.py` | `specs/backend/api.md` → client section |
| `backend/src/docmind/dbase/supabase/storage.py` | `specs/backend/api.md` → storage section |
| `backend/src/docmind/modules/*/schemas.py` | `specs/backend/api.md` → Pydantic models section |
| `backend/src/docmind/modules/*/apiv1/handler.py` | `specs/backend/api.md` → handlers section |
| `backend/src/docmind/library/providers/protocol.py` | `specs/backend/providers.md` |
| `backend/src/docmind/library/providers/factory.py` | `specs/backend/providers.md` |
| `frontend/src/lib/supabase.ts` | `specs/frontend/api-client.md` |
| `frontend/src/lib/api.ts` | `specs/frontend/api-client.md` |
| `frontend/src/types/api.ts` | `specs/frontend/api-client.md` |
| `frontend/src/stores/workspace-store.ts` | `specs/frontend/state.md` |
| `frontend/src/stores/auth-store.ts` | `specs/frontend/state.md` |

---

## Done Criteria

The scaffold is complete when:

- [ ] `cd backend && poetry install` — exits 0
- [ ] `cd backend && poetry run python -c "from docmind.main import app; print('ok')"` — prints `ok`
- [ ] `cd backend && poetry run uvicorn docmind.main:app --reload` — starts without import errors
- [ ] `GET /api/v1/health/ping` returns `{"status": "ok", ...}`
- [ ] `cd backend && poetry run pytest --collect-only` — collects without errors (tests may skip/xfail)
- [ ] `cd frontend && npm install` — exits 0
- [ ] `cd frontend && npm run build` — compiles without TypeScript errors
- [ ] No file has a hardcoded secret, URL, or magic string — all come from `core/config.py` or env vars

---

## What NOT to Do

- ❌ Do not implement LangGraph pipeline logic — stub with `raise NotImplementedError`
- ❌ Do not make real VLM API calls — stub the provider methods
- ❌ Do not implement CV algorithms — stub with `raise NotImplementedError`
- ❌ Do not write Alembic migration scripts yet — leave `alembic/versions/` empty
- ❌ Do not install shadcn/ui components — leave `src/components/ui/` empty
- ❌ Do not write any test assertions yet — just the directory tree and empty conftest fixtures
- ❌ Do not invent fields, routes, or schemas not in the specs — if something is unclear, check the spec again
- ❌ Do not use relative imports across module boundaries — always use full `from docmind.*` paths
- ❌ Do not put business logic in handlers — delegate to usecase, always

---

## When You're Unsure

The specs are the source of truth. Priority order:

1. `specs/backend/api.md` — endpoint paths, Pydantic schemas, ORM models
2. `specs/system.md` — file layout, env vars, config
3. `specs/conventions/python-module-structure.md` — layer rules
4. Other specs — fill in details

If two specs conflict, `api.md` wins for backend contracts, `system.md` wins for structure.
