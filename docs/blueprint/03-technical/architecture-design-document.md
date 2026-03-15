# Architecture Design Document: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Technical Design

---

## 1. System Overview

DocMind-VLM is a full-stack web application with a clear separation between frontend (React SPA), backend (FastAPI), and managed infrastructure (Supabase). The backend orchestrates a document processing pipeline via LangGraph, combining classical computer vision preprocessing with VLM inference via DashScope API. All state is stored in Supabase Postgres, files in Supabase Storage.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      FRONTEND                            │
│              React + TypeScript + Vite                    │
│         shadcn/ui + Tailwind CSS + Lucide                │
│                                                          │
│  Landing Page ─── Dashboard ─── Document Workspace       │
│                                    ├── Document Viewer   │
│                                    ├── Extraction Tab    │
│                                    ├── Chat Tab          │
│                                    ├── Audit Tab         │
│                                    └── Compare Tab       │
└──────────────┬──────────────────────┬────────────────────┘
               │ REST API             │ Supabase Auth
               │ (JWT validated)      │ (OAuth flow)
               ▼                      ▼
┌──────────────────────────┐  ┌────────────────────────────┐
│      FASTAPI BACKEND     │  │         SUPABASE           │
│                          │  │                            │
│  ┌────────────────────┐  │  │  ┌──────────────────────┐  │
│  │   API Layer        │  │  │  │  Auth (Google/GitHub) │  │
│  │   (routes, auth    │  │  │  │  JWT issuing          │  │
│  │    middleware)      │  │  │  └──────────────────────┘  │
│  └────────┬───────────┘  │  │                            │
│           │              │  │  ┌──────────────────────┐  │
│  ┌────────▼───────────┐  │  │  │  Postgres             │  │
│  │  Service Layer      │  │  │  │  (documents, fields,  │  │
│  │  (business logic)   │──┼──┼─▶│   chat, audit, users) │  │
│  └────────┬───────────┘  │  │  │  + Row Level Security  │  │
│           │              │  │  └──────────────────────┘  │
│  ┌────────▼───────────┐  │  │                            │
│  │  Pipeline Layer     │  │  │  ┌──────────────────────┐  │
│  │  (LangGraph)        │  │  │  │  Storage              │  │
│  │                     │──┼──┼─▶│  (uploaded documents)  │  │
│  │  ┌───────────────┐  │  │  │  └──────────────────────┘  │
│  │  │ Preprocess    │  │  │  │                            │
│  │  │ (OpenCV)      │  │  │  └────────────────────────────┘
│  │  └──────┬────────┘  │  │
│  │  ┌──────▼────────┐  │  │
│  │  │ Extract       │  │  │   ┌─────────────────────────┐
│  │  │ (VLMProvider  │──┼──┼──▶│  VLM Providers          │
│  │  │  interface)   │  │  │   │  ├─ DashScope (Qwen3-VL)│
│  │  └──────┬────────┘  │  │   │  ├─ OpenAI (GPT-4o)     │
│  │  ┌──────▼────────┐  │  │   │  ├─ Google (Gemini)     │
│  │  │ Post-process  │  │  │   │  └─ Ollama (local)      │
│  │  │ (merge scores │  │  │   └─────────────────────────┘
│  │  │  validate)    │  │  │
│  │  └──────┬────────┘  │  │
│  │  ┌──────▼────────┐  │  │
│  │  │ Chat Agent    │  │  │
│  │  │ (LangGraph    │──┼──┼──▶ (uses same VLMProvider)
│  │  │  stateful)    │  │  │
│  │  └───────────────┘  │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │  Redis (optional)   │  │
│  │  (job queue,        │  │
│  │   caching)          │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

## 2. High-Level Components

### 2.1 Frontend (React SPA)
- **Responsibility:** All user interaction — landing page, auth flow, document upload, workspace (viewer, extraction, chat, audit, compare), export
- **Auth:** Supabase JS SDK handles OAuth flow; JWT tokens sent to backend on every API call
- **State:** React Query for server state (documents, extractions, chat); Zustand for local UI state (active tab, overlay toggle, zoom level)
- **Document viewer:** Canvas-based renderer with overlay support (confidence heatmap, bounding boxes)

### 2.2 FastAPI Backend
- **Responsibility:** All business logic, pipeline orchestration, data access, API security
- **Auth middleware:** Validates Supabase JWT on every request; extracts user_id for RLS
- **API Layer:** RESTful endpoints for documents, extractions, chat, templates, comparison
- **Service Layer:** Business logic (document lifecycle, extraction orchestration, chat session management)
- **Pipeline Layer:** LangGraph-based document processing and chat agent

### 2.3 LangGraph Pipeline — Document Processing
- **Responsibility:** Orchestrates the full extraction pipeline as a directed graph
- **Nodes:**
  1. `preprocess` — OpenCV: deskew, quality assessment, region quality map
  2. `extract` — DashScope API: send preprocessed image + prompt, receive structured output
  3. `postprocess` — Merge VLM confidence with CV quality scores, validate against template schema
  4. `store` — Persist results to Postgres
- **State:** Pipeline state object carries: original image, preprocessed image, quality map, extraction results, audit log
- **Logging:** Every node logs its inputs, outputs, timing, and parameters to the audit trail

### 2.4 LangGraph Pipeline — Chat Agent
- **Responsibility:** Stateful conversational agent for document Q&A
- **Nodes:**
  1. `router` — Classify user intent (factual lookup, reasoning, summarization)
  2. `retrieve` — Search extraction results; optionally query Qwen3-VL with specific document region
  3. `reason` — Generate answer grounded in extraction data + VLM response
  4. `cite` — Attach source citations (page, bounding box, text span) to every claim
  5. `respond` — Format final response with inline citations
- **Memory:** LangGraph checkpointer stores conversation state per document per user
- **Grounding rule:** If the agent cannot find evidence in the document, it must say so explicitly — no hallucinated answers

### 2.5 Supabase (Managed Infrastructure)
- **Auth:** Google + GitHub OAuth providers; JWT issuance and refresh
- **Postgres:** All application data with Row Level Security (users see only their own data)
- **Storage:** Uploaded documents stored at `{user_id}/{document_id}/{filename}`; pre-signed URLs for frontend access

### 2.6 Redis (Optional — Docker Compose)
- **Responsibility:** Job queue for async processing (if needed for long documents), response caching for repeated chat queries
- **Note:** MVP may process synchronously via SSE (Server-Sent Events) for progress streaming; Redis becomes important at scale or for multi-page documents

## 3. Data Flow

### 3.1 Document Upload & Processing

```
User drops file
  → Frontend uploads to Supabase Storage (direct upload with signed URL)
  → Frontend calls POST /api/documents (metadata: filename, storage_path)
  → Backend creates document record (status: "processing")
  → Backend triggers LangGraph processing pipeline
    → preprocess node (OpenCV) → quality map + preprocessed image
    → extract node (DashScope API) → raw extraction results
    → postprocess node → merged confidence scores, template validation
    → store node → extraction results saved to Postgres
  → Backend updates document status to "ready"
  → Frontend receives SSE progress updates at each pipeline step
  → Frontend loads extraction results and renders workspace
```

### 3.2 Chat Flow

```
User sends message
  → Frontend calls POST /api/documents/{id}/chat (message)
  → Backend loads document context (extraction results, chat history)
  → Backend triggers LangGraph chat agent
    → router → retrieve → reason → cite → respond
  → Backend streams response via SSE
  → Backend stores message pair in Postgres
  → Frontend renders response with clickable citations
```

### 3.3 Comparison Flow

```
User clicks "Compare with raw VLM"
  → Frontend calls GET /api/documents/{id}/comparison
  → Backend loads enhanced results + pre-computed raw baseline
  → Backend computes diff (corrected, added, unchanged)
  → Returns comparison data structure
  → Frontend renders side-by-side with color-coded highlights
```

## 4. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | React 18+ / TypeScript / Vite | Modern, fast, portfolio target skill |
| **UI Components** | shadcn/ui + Tailwind CSS | Accessible, composable, professional |
| **Frontend State** | React Query + Zustand | Server state + local UI state separation |
| **Backend** | FastAPI (Python 3.11+) | Async, typed, fast — core strength |
| **Pipeline** | LangGraph | Stateful graph-based agent orchestration |
| **Classical CV** | OpenCV (cv2) | Deskew, quality assessment, image preprocessing |
| **VLM** | Qwen3-VL via DashScope API | Best open-source VLM for documents, cheap API |
| **Auth** | Supabase Auth | Google + GitHub OAuth, JWT |
| **Database** | Supabase Postgres | Managed, RLS, free tier |
| **File Storage** | Supabase Storage | S3-compatible, integrated with auth |
| **Cache/Queue** | Redis (optional) | Async jobs, caching |
| **Containerization** | Docker + Docker Compose | One-command local setup |
| **CI/CD** | GitHub Actions | Automated tests, linting, build verification |

## 5. Project Structure (Monorepo)

```
docmind-vlm/
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── components/          # UI components (shadcn/ui based)
│   │   ├── pages/               # Landing, Dashboard, Workspace
│   │   ├── hooks/               # Custom React hooks
│   │   ├── lib/                 # Supabase client, API client, utils
│   │   ├── stores/              # Zustand stores
│   │   └── types/               # TypeScript type definitions
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── api/                 # Route handlers
│   │   │   ├── documents.py
│   │   │   ├── extractions.py
│   │   │   ├── chat.py
│   │   │   └── templates.py
│   │   ├── core/                # Config, auth middleware, dependencies
│   │   ├── models/              # SQLAlchemy/Pydantic models
│   │   ├── services/            # Business logic layer
│   │   ├── pipeline/            # LangGraph pipelines
│   │   │   ├── processing/      # Document processing graph
│   │   │   │   ├── graph.py
│   │   │   │   ├── preprocess.py
│   │   │   │   ├── extract.py
│   │   │   │   └── postprocess.py
│   │   │   └── chat/            # Chat agent graph
│   │   │       ├── graph.py
│   │   │       ├── router.py
│   │   │       ├── retrieve.py
│   │   │       ├── reason.py
│   │   │       └── cite.py
│   │   ├── cv/                  # Classical CV module
│   │   │   ├── deskew.py
│   │   │   ├── quality.py
│   │   │   └── preprocessing.py
│   │   └── templates/           # Extraction schema templates
│   │       ├── invoice.json
│   │       ├── receipt.json
│   │       ├── contract.json
│   │       └── certificate.json
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── docs/
│   └── blueprint/               # Product blueprint (this documentation)
│       ├── 01-strategy/
│       ├── 02-product/
│       ├── 03-technical/
│       ├── 04-quality/
│       └── 05-operations/
├── demo/                        # Pre-loaded demo documents + baselines
│   ├── documents/
│   └── baselines/
├── docker-compose.yml
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── README.md
├── LICENSE
└── Makefile
```

---
#architecture-design #technical #system-flow #docmind-vlm
