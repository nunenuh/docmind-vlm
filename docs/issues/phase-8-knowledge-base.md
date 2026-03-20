# Phase 8: Knowledge Base — Implementation Tickets

**Phase**: 8 — Knowledge Base + RAG + Personas
**Priority**: P0
**Dependencies**: Phase 1-7 complete
**Estimated tickets**: 8 (medium-to-large scope each)

---

## Ticket Overview

| # | Title | Scope | Effort | Dependencies |
|---|-------|-------|--------|-------------|
| 37 | Database: pgvector + Project/Persona/Chunk models + migrations | Backend | L | None |
| 38 | Backend: Project + Persona CRUD (module + API + tests) | Backend | L | #37 |
| 39 | Backend: RAG text extraction + chunking library | Backend | M | #37 |
| 40 | Backend: Embedding service + pgvector storage | Backend | M | #39 |
| 41 | Backend: RAG retrieval + project chat pipeline | Backend | L | #38, #40 |
| 42 | Backend: Document indexing on project upload + re-index | Backend | M | #40, #38 |
| 43 | Frontend: Project dashboard + workspace + persona UI | Frontend | L | #38, #41 |
| 44 | End-to-end: RAG chat integration + demo data | Full-stack | L | #41, #43 |

---

## Ticket #37: Database — pgvector + New Models + Migrations

### Summary
Enable pgvector extension in Supabase Postgres. Create ORM models for Project, Persona, ProjectConversation, ProjectMessage, PageChunk. Add `project_id` FK to existing Document model (nullable for backwards compat). Generate and run Alembic migrations.

### Scope
- Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
- New ORM models (5): Project, Persona, ProjectConversation, ProjectMessage, PageChunk
- Modify Document model: add nullable `project_id` FK
- PageChunk has `embedding` column: `Vector(1024)` type
- pgvector index: `ivfflat (embedding vector_cosine_ops)`
- Alembic migration for all new tables
- Seed 5 preset personas (Customer Service, Technical Expert, Onboarding Guide, Legal Advisor, General Assistant)

### Specs
- `specs/backend/projects.md` — data model section
- `specs/backend/rag.md` — PageChunk model + SQL migration

### Files Changed
| File | Action |
|------|--------|
| `backend/src/docmind/dbase/psql/models/project.py` | Create |
| `backend/src/docmind/dbase/psql/models/persona.py` | Create |
| `backend/src/docmind/dbase/psql/models/project_conversation.py` | Create |
| `backend/src/docmind/dbase/psql/models/project_message.py` | Create |
| `backend/src/docmind/dbase/psql/models/page_chunk.py` | Create |
| `backend/src/docmind/dbase/psql/models/document.py` | Modify (add project_id) |
| `backend/src/docmind/dbase/psql/models/__init__.py` | Modify (re-export new models) |
| `backend/alembic/versions/` | Create migration |
| `backend/src/docmind/core/config.py` | Add RAG settings |

---

## Ticket #38: Backend — Project + Persona CRUD

### Summary
Implement the Projects and Personas modules following the Handler → UseCase → Service → Repository pattern. Full CRUD for projects (create, list, get, update, delete with cascade). Full CRUD for personas (presets + custom). Project-document association (add/remove doc from project). All endpoints JWT-protected, scoped to user.

### Scope
- `modules/projects/` — full module (handler, schemas, usecase, services, repositories)
- `modules/personas/` — thin CRUD module (handler, schemas, repositories)
- ProjectRepository: create, get_by_id, list_for_user, update, delete (cascade), add_document, remove_document, list_documents
- PersonaRepository: create, get_by_id, list_available, update, delete
- Router registration in `router.py`
- Unit tests for repository + usecase + handler
- ~16 API endpoints total

### Specs
- `specs/backend/projects.md` — full spec
- `specs/backend/api.md` — endpoint definitions

### Files Changed
| File | Action |
|------|--------|
| `backend/src/docmind/modules/projects/` | Create (full module) |
| `backend/src/docmind/modules/personas/` | Create (full module) |
| `backend/src/docmind/router.py` | Modify (register new routers) |
| `backend/tests/unit/modules/projects/` | Create |
| `backend/tests/unit/modules/personas/` | Create |

---

## Ticket #39: Backend — RAG Text Extraction + Chunking

### Summary
Implement the text extraction and chunking library for RAG. Extract text from PDFs (PyMuPDF) and images (VLM OCR fallback). Chunk text into overlapping segments with sentence-boundary awareness. Pure library functions with no DB dependencies.

### Scope
- `library/rag/text_extract.py` — `extract_text_from_pdf(file_bytes)` returns per-page text, `extract_text_from_image(image)` uses VLM OCR
- `library/rag/chunker.py` — `chunk_text(text, chunk_size=512, overlap=64)` returns list of chunk dicts
- Sentence-boundary splitting (split on `.!?` then merge until chunk_size)
- Handle edge cases: empty pages, scanned PDFs with no extractable text, very short documents
- Unit tests with sample PDFs and text

### Specs
- `specs/backend/rag.md` — chunker and text_extract sections

### Files Changed
| File | Action |
|------|--------|
| `backend/src/docmind/library/rag/__init__.py` | Create |
| `backend/src/docmind/library/rag/text_extract.py` | Create |
| `backend/src/docmind/library/rag/chunker.py` | Create |
| `backend/tests/unit/library/rag/test_text_extract.py` | Create |
| `backend/tests/unit/library/rag/test_chunker.py` | Create |

---

## Ticket #40: Backend — Embedding Service + pgvector Storage

### Summary
Implement the embedding provider abstraction (DashScope text-embedding-v3 primary, OpenAI fallback) and pgvector chunk storage. Embed text chunks in batches, store with vector column, support bulk insert.

### Scope
- `library/rag/embedder.py` — EmbeddingProvider protocol, DashScopeEmbedder, OpenAIEmbedder, `get_embedder()` factory
- DashScope embedding: POST to text-embedding API, batch up to 25 texts per call
- `library/rag/retriever.py` — `store_chunks(chunks, embeddings, document_id, project_id)` bulk insert to page_chunks
- `library/rag/retriever.py` — `retrieve_chunks(project_id, query_embedding, top_k, threshold)` pgvector cosine similarity search
- Settings: EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, RAG_TOP_K, RAG_SIMILARITY_THRESHOLD
- Unit tests (mock API calls), integration test with real pgvector

### Specs
- `specs/backend/rag.md` — embedder and retriever sections

### Files Changed
| File | Action |
|------|--------|
| `backend/src/docmind/library/rag/embedder.py` | Create |
| `backend/src/docmind/library/rag/retriever.py` | Create |
| `backend/tests/unit/library/rag/test_embedder.py` | Create |
| `backend/tests/unit/library/rag/test_retriever.py` | Create |

---

## Ticket #41: Backend — RAG Chat Pipeline (Project-Level)

### Summary
Implement the LangGraph RAG chat pipeline for project-level conversations. Nodes: embed_query → retrieve → reason → cite. Uses persona system prompt + retrieved chunks as context. SSE streaming endpoint. Conversation persistence.

### Scope
- `library/pipeline/rag_chat.py` — LangGraph StateGraph with 4 nodes
- embed_query node: embed user message using embedding provider
- retrieve node: pgvector similarity search across project chunks
- reason node: build prompt (persona + context + history + message) → LLM → answer
- cite node: extract document citations (doc name, page number)
- `modules/projects/usecase.py` — `trigger_project_chat()` SSE stream method
- ConversationRepository: create conversation, add messages, get history
- POST `/api/v1/projects/{id}/chat` SSE endpoint
- GET `/api/v1/projects/{id}/conversations` + `/{conv_id}` endpoints
- Unit tests for each pipeline node

### Specs
- `specs/backend/pipeline-chat.md` — RAG chat pipeline section
- `specs/backend/projects.md` — conversation endpoints

### Files Changed
| File | Action |
|------|--------|
| `backend/src/docmind/library/pipeline/rag_chat.py` | Create |
| `backend/src/docmind/modules/projects/usecase.py` | Modify (add chat methods) |
| `backend/src/docmind/modules/projects/apiv1/handler.py` | Modify (add chat + conversation endpoints) |
| `backend/tests/unit/library/pipeline/test_rag_chat.py` | Create |

---

## Ticket #42: Backend — Document Indexing on Project Upload

### Summary
When a document is added to a project, automatically index it for RAG: extract text → chunk → embed → store in pgvector. Support re-indexing when a document is replaced. Delete chunks when document is removed from project.

### Scope
- `library/rag/indexer.py` — `index_document_for_rag(document_id, project_id, file_bytes, file_type)` orchestration function
- Pipeline: extract_text → chunk_text → embed_chunks (batched) → bulk insert page_chunks
- Re-index: delete existing chunks for document → re-index
- Delete: when doc removed from project, cascade delete chunks
- Called from ProjectUseCase.add_document() after file upload
- Background task (asyncio.to_thread) so upload returns quickly
- SSE progress events: "Indexing document... 234 chunks created"
- Unit + integration tests

### Specs
- `specs/backend/rag.md` — indexer section

### Files Changed
| File | Action |
|------|--------|
| `backend/src/docmind/library/rag/indexer.py` | Create |
| `backend/src/docmind/modules/projects/usecase.py` | Modify (call indexer on add_document) |
| `backend/tests/unit/library/rag/test_indexer.py` | Create |

---

## Ticket #43: Frontend — Project Dashboard + Workspace + Persona UI

### Summary
Build the frontend for Knowledge Base mode: project dashboard (list/create projects), project workspace (multi-doc list + RAG chat + persona selector), persona editor modal. New pages and components.

### Scope
- `pages/ProjectDashboard.tsx` — project list with cards, "New Project" button
- `pages/ProjectWorkspace.tsx` — split layout: left (doc list + upload), right (chat + conversations)
- `components/project/ProjectCard.tsx` — card showing name, doc count, persona, updated
- `components/project/ProjectDocList.tsx` — document list with upload, delete, index status
- `components/project/ProjectChatPanel.tsx` — RAG chat with conversation sidebar
- `components/project/PersonaSelector.tsx` — dropdown with presets + custom
- `components/project/PersonaEditor.tsx` — modal with system_prompt, tone, rules, boundaries
- `hooks/useProjects.ts` — React Query hooks for project CRUD
- `hooks/usePersonas.ts` — React Query hooks for persona CRUD
- `stores/project-store.ts` — Zustand store for active project state
- `lib/api.ts` — add project + persona API functions
- Routes: `/projects`, `/projects/:id`
- Navigation: Dashboard shows both "Documents" and "Projects" sections

### Specs
- `specs/frontend/components.md` — project components section
- `specs/frontend/state.md` — project store

### Files Changed
| File | Action |
|------|--------|
| `frontend/src/pages/ProjectDashboard.tsx` | Create |
| `frontend/src/pages/ProjectWorkspace.tsx` | Create |
| `frontend/src/components/project/` | Create (6 components) |
| `frontend/src/hooks/useProjects.ts` | Create |
| `frontend/src/hooks/usePersonas.ts` | Create |
| `frontend/src/stores/project-store.ts` | Create |
| `frontend/src/lib/api.ts` | Modify |
| `frontend/src/App.tsx` | Modify (add routes) |
| `frontend/src/pages/Dashboard.tsx` | Modify (add Projects section) |

---

## Ticket #44: End-to-End — RAG Chat Integration + Demo Data

### Summary
Wire everything together end-to-end. Create demo project with sample documents. Test full flow: create project → upload docs → index → select persona → chat → get cited answers. Fix integration issues. Update landing page to showcase Knowledge Base mode.

### Scope
- E2E test: create project → upload 3 PDFs → wait for indexing → chat → verify citations
- Demo data: create a pre-loaded "Product Support" project with 3-5 sample docs
- Demo persona: pre-configured "Customer Service Agent"
- Landing page: add Knowledge Base feature section
- Fix any integration bugs between frontend and backend
- Verify: persona system prompt affects response tone
- Verify: citations reference correct document + page
- Verify: conversation persistence works across page reloads
- Update README with Knowledge Base feature description

### Files Changed
| File | Action |
|------|--------|
| `data/demo/projects/` | Create (sample docs) |
| `frontend/src/components/landing/Features.tsx` | Modify |
| `frontend/src/pages/LandingPage.tsx` | Modify |
| `backend/tests/e2e/` | Create (RAG e2e tests) |
| `README.md` | Modify |

---

## Dependency Graph

```
#37 (DB models + pgvector)
  ├── #38 (Project + Persona CRUD) ──┐
  ├── #39 (Text extraction + chunking)│
  │     └── #40 (Embedding + storage) │
  │           ├── #41 (RAG chat pipeline) ← #38
  │           └── #42 (Document indexing) ← #38
  └──────────────────────────────────────┘
                                      │
                              #43 (Frontend) ← #38, #41
                                      │
                              #44 (E2E integration) ← #41, #43
```

## Execution Order (suggested)

1. **#37** — DB models (blocks everything)
2. **#38 + #39** — in parallel (CRUD + text extraction)
3. **#40** — embedding + storage (needs #39)
4. **#41 + #42** — in parallel (chat pipeline + indexing, both need #38 + #40)
5. **#43** — frontend (needs #38 + #41)
6. **#44** — E2E integration (needs everything)
