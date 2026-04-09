# Phase 2 Tickets — Indonesian Documents + Production Features

## Overview

Phase 2 transforms DocMind-VLM from a working prototype into a demo-ready product.
Focus: Indonesian document templates, production UI, RAG transparency, export.

Medium-to-large tickets (fewer tickets, more scope per ticket).

---

## Ticket #P2-01: Indonesian Document Templates (Backend)
**Size: L | Priority: P0**

Add 10 Indonesian document template configurations with field definitions, validation rules, and extraction prompts.

**Scope:**
- Template config system: `data/templates/{type}.json` with required_fields, optional_fields, validation_rules, extraction_prompt
- Templates: KTP, KK, SIM, STNK, BPKB, NPWP, Faktur Pajak, Invoice, Surat Kuasa, Slip Gaji
- Each template has: field names (Indonesian), field types, format validators (NIK = 16 digits, NPWP format, date format)
- Update `_get_template_config()` to load from JSON files instead of hardcoded dict
- Add `/api/v1/templates` endpoint to list available templates with descriptions
- Template extraction prompts in Bahasa Indonesia context

**Files:** `data/templates/*.json`, `library/pipeline/processing.py`, `modules/templates/`

---

## Ticket #P2-02: Auto-Classification + Batch Upload (Backend)
**Size: L | Priority: P0**

Auto-detect document type from uploaded file using VLM classification, and support batch upload queue.

**Scope:**
- Auto-classify endpoint: `POST /api/v1/documents/{id}/classify` → returns detected type + confidence
- Integration with extraction pipeline: if no template_type specified, auto-classify first
- Batch upload: `POST /api/v1/documents/batch` accepts multiple files, returns job_id
- Background job queue (asyncio.Queue or simple DB-based) for batch processing
- Status tracking: `GET /api/v1/documents/batch/{job_id}` → progress per document
- Frontend: batch upload UI with progress tracking per file

**Files:** `modules/documents/`, `library/pipeline/processing.py`, `frontend/src/components/`

---

## Ticket #P2-03: Export System (Backend + Frontend)
**Size: M | Priority: P1**

Export extracted data in multiple formats.

**Scope:**
- Backend: `GET /api/v1/extractions/{document_id}/export?format={json|csv|excel}`
- JSON export: structured field data with metadata
- CSV export: flat table (field_key, field_value, confidence, page_number)
- Excel export: formatted workbook with document info sheet + fields sheet (using openpyxl)
- Frontend: Export button dropdown in ExtractionPanel (JSON / CSV / Excel)
- Batch export: `POST /api/v1/documents/export` with list of document IDs → ZIP file

**Files:** `modules/extractions/`, `frontend/src/components/workspace/ExtractionPanel.tsx`

---

## Ticket #P2-04: Chunk Browser + RAG Transparency (Frontend + Backend)
**Size: M | Priority: P1**

Let users see RAG chunks per document, understand what was retrieved, and debug retrieval quality.

**Scope:**
- Backend: `GET /api/v1/projects/{id}/chunks?document_id={optional}` → list chunks with metadata
- Backend: `GET /api/v1/projects/{id}/chunks/{chunk_id}` → single chunk with embedding preview
- Frontend: ChunkBrowser component in project workspace — list all chunks per document
  - Show: chunk text preview, page number, section header, content hash
  - Expandable to see full chunk content
  - Highlight which chunks were used in the last chat response
- Frontend: In chat answers, clicking [Source N] scrolls to and highlights the chunk in ChunkBrowser
- Delete individual chunks (for cleaning bad extractions)

**Files:** `modules/projects/`, `frontend/src/components/project/ChunkBrowser.tsx`

---

## Ticket #P2-05: Production UI Overhaul (Frontend)
**Size: XL | Priority: P0**

Complete UI redesign for production quality.

**Scope:**
- **Toast notification system** — react-hot-toast or sonner for all actions (upload, delete, process, index, error)
- **Loading skeletons** — Skeleton components for document cards, project cards, chat messages, extraction fields
- **Command Palette (Cmd+K)** — Search documents, projects, conversations globally (use cmdk library)
- **Extraction Panel fix** — Show extracted fields in structured table after processing, not infinite spinner
- **Document thumbnails** — Generate and display first-page thumbnail for PDF/image documents
- **Conversation management** — Rename, delete, search conversations in project sidebar
- **Proper error boundaries** — Error fallback UI instead of white screen
- **Empty states** — Meaningful empty states for every page/section
- **Responsive layout** — Works on tablet (1024px) minimum
- **Breadcrumb navigation** — Consistent across all pages

**Files:** All frontend components

---

## Ticket #P2-06: Persona Management (Frontend + Backend)
**Size: M | Priority: P1**

Full persona CRUD with preview and better UX.

**Scope:**
- Backend: Seed 5 preset personas on first startup (if none exist)
- Frontend: Persona management page in Settings
  - List all personas (preset + custom)
  - Create/edit custom persona with rich form (name, description, system_prompt, tone, rules, boundaries)
  - Preview: test a persona by sending a sample message and seeing the response style
  - Duplicate preset persona to customize
  - Delete custom personas (presets can't be deleted)
- Frontend: Persona selector in project settings with preview card showing description + tone
- Frontend: Show active persona name + icon in project chat header

**Files:** `frontend/src/pages/Settings.tsx`, `frontend/src/components/project/PersonaSelector.tsx`

---

## Ticket #P2-07: Document Management Improvements (Frontend + Backend)
**Size: M | Priority: P1**

Separate standalone documents from project documents, improve document lifecycle.

**Scope:**
- Backend: `GET /api/v1/documents?project_id={optional}` — filter by project or standalone
- Frontend: Dashboard shows only standalone documents (not linked to projects)
- Frontend: Document card shows project name badge if linked
- Frontend: Document detail page shows: file info, processing status, extraction status, RAG index status
- Frontend: Re-process button (re-run extraction pipeline)
- Frontend: Re-index button (re-run RAG indexing for project documents)
- Backend: `POST /api/v1/projects/{id}/documents/{doc_id}/reindex` endpoint
- Backend: Delete document also deletes RAG chunks (CASCADE or explicit)

**Files:** `modules/documents/`, `modules/projects/`, `frontend/src/pages/Dashboard.tsx`

---

## Ticket #P2-08: Analytics & Activity (Frontend + Backend)
**Size: M | Priority: P2**

Dashboard analytics and activity feed.

**Scope:**
- Backend: `GET /api/v1/analytics/summary` → total docs, total pages, total chunks, total conversations, storage used
- Backend: `GET /api/v1/analytics/activity?limit=20` → recent actions (upload, process, chat, create project)
- Activity model: store events in `activity_log` table (user_id, action, resource_type, resource_id, timestamp)
- Frontend: Analytics cards on Dashboard (replace simple stat cards)
  - Total documents, Pages processed, RAG chunks, Conversations, Storage used
  - Mini sparkline charts (last 7 days)
- Frontend: Activity feed component — recent actions with timestamps and links
- Frontend: Per-project analytics in project settings

**Files:** `modules/analytics/`, `frontend/src/components/dashboard/`

---

## Ticket #P2-09: Settings Page (Frontend + Backend)
**Size: M | Priority: P1**

Real settings page with user preferences.

**Scope:**
- **Profile section**: Display name, email, avatar, change password
- **AI Settings**: Default VLM provider, default embedding model, enable/disable thinking, temperature
- **RAG Settings**: Chunk size, overlap, top-K, similarity threshold (with explanations)
- **Appearance**: Theme (dark only for now, placeholder for light), language (EN/ID)
- **API Keys**: Show/manage DashScope API key (masked), test connection button
- **Data**: Export all data, delete account
- Backend: `GET/PUT /api/v1/settings` — user settings CRUD (stored in `user_settings` table)
- Frontend: Settings page with tabbed sections

**Files:** `modules/settings/`, `frontend/src/pages/Settings.tsx`

---

## Ticket #P2-10: Document Chat Fix + VLM Integration (Backend + Frontend)
**Size: M | Priority: P0**

Fix per-document chat to actually use document content and page images.

**Scope:**
- Backend: Chat handler downloads document image from Supabase Storage
- Backend: For PDFs, convert pages to images using PyMuPDF
- Backend: Pass page images + extracted fields as context to VLM chat
- Backend: Chat streams with thinking (reuse DashScope streaming from project chat)
- Frontend: ChatPanel shows thinking section (reuse ThinkingSection component)
- Frontend: ChatPanel shows extraction fields as context cards
- Frontend: "Ask about this field" — click on extracted field → prefill chat input

**Files:** `modules/chat/`, `library/pipeline/chat.py`, `frontend/src/components/workspace/ChatPanel.tsx`

---

## Implementation Order

| Order | Ticket | Why First |
|-------|--------|-----------|
| 1 | **P2-05** Production UI Overhaul | Everything else looks bad without this |
| 2 | **P2-10** Document Chat Fix | Core feature is broken |
| 3 | **P2-01** Indonesian Templates | The demo centerpiece |
| 4 | **P2-02** Auto-Classification + Batch | Makes templates useful |
| 5 | **P2-07** Document Management | Clean up the data model |
| 6 | **P2-06** Persona Management | Needed for KB demo |
| 7 | **P2-04** Chunk Browser | RAG transparency |
| 8 | **P2-03** Export System | Practical output |
| 9 | **P2-09** Settings Page | Polish |
| 10 | **P2-08** Analytics & Activity | Nice to have |

---

## Estimated Effort

| Size | Tickets | Estimated Time |
|------|---------|---------------|
| XL | 1 (P2-05) | 2-3 sessions |
| L | 2 (P2-01, P2-02) | 1-2 sessions each |
| M | 7 (P2-03 through P2-10) | 1 session each |
| **Total** | **10 tickets** | **~12-15 sessions** |
