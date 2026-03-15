# Specs — DocMind-VLM

Implementation guide for engineers building this project. These specs are the **"how to build it"** — not what to build (see `docs/blueprint/`) or in what order (see `docs/plans/`).

---

## Directory Structure

```
specs/
├── README.md            ← You are here
├── system.md            ← Overall conventions: env vars, Docker, file layout, shared patterns
├── conventions/
│   ├── repository-overview.md       ← Project layout, tech stack, development workflow
│   ├── python-conventions.md        ← PEP 8, type hints, naming, imports, error handling
│   ├── python-module-structure.md   ← Module layering (Handler → UseCase → Service → Repo)
│   ├── testing.md                   ← Test structure: units / integrations / e2e
│   └── security.md                  ← Supabase JWT auth, RLS, file validation
├── backend/
│   ├── api.md           ← FastAPI routes, Pydantic schemas, error handling, CORS
│   ├── cv.md            ← Classical CV module: deskew, quality assessment, preprocessing
│   ├── providers.md     ← VLM provider protocol, factory, 4 provider implementations
│   ├── pipeline-processing.md  ← LangGraph document processing pipeline
│   ├── pipeline-chat.md        ← LangGraph chat agent pipeline
│   └── services.md      ← Per-module services, repositories, use cases
└── frontend/
    ├── components.md    ← React component tree, shadcn/ui usage, key components
    ├── state.md         ← State management: React Query + Zustand
    └── api-client.md    ← Supabase client + backend API client layer
```

---

## How to Use These Specs

1. **Start with `system.md`** — understand env vars, project layout, Docker, and shared patterns.
2. **Read the relevant layer spec** before touching that layer's code.
3. **Check `conventions/`** for language/framework-level rules that apply across all files.
4. **Cross-reference `docs/blueprint/`** for the authoritative design decisions (architecture, PRD, SRS, ADRs).

---

## Quick Reference

| Topic | Spec | Key Files |
|-------|------|-----------|
| **Conventions** | | |
| Repo layout & workflow | `conventions/repository-overview.md` | `pyproject.toml`, `docker-compose.yml`, `Makefile` |
| Python style & patterns | `conventions/python-conventions.md` | All `.py` files in `docmind/` |
| Module layering | `conventions/python-module-structure.md` | `docmind/modules/documents/`, `docmind/modules/extractions/` |
| Tests | `conventions/testing.md` | `tests/unit/`, `tests/integration/`, `tests/e2e/` |
| Security (JWT + RLS) | `conventions/security.md` | `docmind/core/auth.py` |
| **System** | | |
| System-wide | `system.md` | `.env`, `docker-compose.yml`, `docmind/main.py` |
| **Backend** | | |
| API Layer + ORM Models | `backend/api.md` | `docmind/modules/*/apiv1/handler.py`, `docmind/router.py`, `docmind/dbase/sqlalchemy/models.py` |
| CV Module | `backend/cv.md` | `docmind/library/cv/deskew.py`, `quality.py`, `preprocessing.py` |
| VLM Providers | `backend/providers.md` | `docmind/library/providers/protocol.py`, `factory.py`, `dashscope.py` |
| Processing Pipeline | `backend/pipeline-processing.md` | `docmind/library/pipeline/processing.py` |
| Chat Pipeline | `backend/pipeline-chat.md` | `docmind/library/pipeline/chat.py` |
| Module Services | `backend/services.md` | `docmind/modules/*/services.py`, `repositories.py`, `usecase.py` |
| **Frontend** | | |
| Components | `frontend/components.md` | `src/components/workspace/`, `src/components/landing/` |
| State | `frontend/state.md` | `src/stores/`, `src/hooks/` |
| API Client | `frontend/api-client.md` | `src/lib/`, `src/types/` |

---

## Related Documents

- [[projects/docmind-vlm/docs/blueprint/03-technical/architecture-design-document]] — System architecture
- [[projects/docmind-vlm/docs/blueprint/03-technical/software-requirements-specification]] — API endpoints, data models
- [[projects/docmind-vlm/docs/blueprint/03-technical/technical-design-document]] — Module designs
- [[projects/docmind-vlm/docs/blueprint/03-technical/architecture-decision-records]] — ADRs
