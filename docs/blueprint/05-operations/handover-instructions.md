# Handover Instructions: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Operations

---

## The Execution Plan

"You are a Senior Software Engineer tasked with building DocMind-VLM — a full-stack document AI application with VLM-powered extraction and conversational Q&A."

### Source of Truth

Read and implement these specifications in order:

1. `02-product/product-requirements-document.md` — What to build (10 FRs + 5 NFRs)
2. `03-technical/architecture-design-document.md` — How it's structured (monorepo, components, data flow)
3. `03-technical/technical-design-document.md` — How to implement (modules, classes, algorithms)
4. `03-technical/architecture-decision-records.md` — Why these choices were made (8 ADRs)
5. `02-product/acceptance-criteria-specification.md` — How to verify (50+ binary checkboxes)
6. `04-quality/test-strategy-document.md` — How to test (3 levels, CI pipeline)

### Technical Requirements

- **Languages:** Python 3.11+ (backend), TypeScript 5.x (frontend)
- **Key frameworks:** FastAPI, LangGraph, React 18+, Vite, shadcn/ui
- **Test coverage:** > 80% overall; > 90% for CV module
- **Linting:** ruff (Python), eslint + prettier (TypeScript), mypy + tsc (type checking)
- **Containerization:** Docker Compose must start full application with one command

### Implementation Order (Recommended Phases)

**Phase 1: Foundation**
- Project scaffolding (monorepo, Docker Compose, CI skeleton)
- Supabase setup (Auth, Postgres schema + migrations, Storage buckets)
- FastAPI skeleton with auth middleware
- React skeleton with routing, auth flow, basic layout

**Phase 2: Core Pipeline**
- Classical CV module (deskew, quality assessment)
- VLM provider interface + DashScope implementation
- LangGraph processing pipeline (preprocess → extract → postprocess → store)
- General mode extraction working end-to-end

**Phase 3: Frontend Workspace**
- Document viewer with image rendering
- Extraction panel (fields + JSON views)
- Upload flow → processing progress → results display

**Phase 4: Advanced Features**
- Template mode extraction (4 templates)
- Confidence overlay (heatmap rendering)
- Audit trail panel
- Pipeline comparison view (pre-computed baselines)

**Phase 5: Chat**
- LangGraph chat agent (router → retrieve → reason → cite)
- Chat panel with citation rendering
- Chat history persistence

**Phase 6: Landing Page & Polish**
- Landing page (hero, features, CTA, tech badges)
- Demo documents + pre-computed baselines
- Additional VLM providers (OpenAI, Google, Ollama)
- Export functionality (JSON, CSV, clipboard)

**Phase 7: Quality & Ship**
- Test coverage to > 80%
- CI/CD pipeline complete
- README with architecture diagram, demo link, quick start
- Docker Compose verified on fresh clone

### Validation

The agent/engineer confirms success by:
1. Running `docker compose up` on a fresh clone — application accessible within 2 minutes
2. All acceptance criteria checkboxes in `02-product/acceptance-criteria-specification.md` pass
3. `pytest --cov` reports > 80% coverage
4. `make lint` passes with zero errors
5. Three demo documents process successfully with extraction + chat

---
#handover #implementation #execution #docmind-vlm
