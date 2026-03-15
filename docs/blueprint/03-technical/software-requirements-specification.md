# Software Requirements Specification (SRS): DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Technical Design

---

## 1. Functional Specification

### 1.1 API Endpoints

#### Authentication
All endpoints except landing page assets and `/api/health` require a valid Supabase JWT in the `Authorization: Bearer <token>` header.

#### Documents API
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/documents` | Create document record after upload to Supabase Storage |
| GET | `/api/documents` | List user's documents (paginated) |
| GET | `/api/documents/{id}` | Get document metadata + processing status |
| DELETE | `/api/documents/{id}` | Delete document + storage file + all related data |
| POST | `/api/documents/{id}/process` | Trigger processing pipeline (returns SSE stream) |
| GET | `/api/documents/{id}/status` | Get processing status and pipeline step progress |

#### Extractions API
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/documents/{id}/extraction` | Get extraction results (fields, confidence, bounding boxes) |
| GET | `/api/documents/{id}/extraction/audit` | Get full audit trail for all extracted fields |
| GET | `/api/documents/{id}/extraction/overlay` | Get confidence overlay data (regions + colors + tooltips) |
| GET | `/api/documents/{id}/comparison` | Get side-by-side comparison (enhanced vs raw baseline) |

#### Templates API
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/templates` | List available extraction templates |
| GET | `/api/templates/{type}` | Get schema for a specific template type |

#### Chat API
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/documents/{id}/chat` | Send message, returns SSE stream of response |
| GET | `/api/documents/{id}/chat/history` | Get chat history for document (paginated) |

#### System
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check (no auth required) |

### 1.2 Data Models

#### Document
```
documents
├── id: UUID (PK)
├── user_id: UUID (FK → auth.users, from JWT)
├── filename: VARCHAR(255)
├── file_type: VARCHAR(20) (pdf, png, jpg, tiff, webp)
├── file_size: INTEGER (bytes)
├── storage_path: TEXT
├── status: ENUM (uploaded, processing, ready, error)
├── document_type: VARCHAR(50) (auto-detected or user-selected, nullable)
├── page_count: INTEGER
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

#### Extraction Result
```
extraction_results
├── id: UUID (PK)
├── document_id: UUID (FK → documents)
├── mode: ENUM (general, template)
├── template_type: VARCHAR(50) (nullable, for template mode)
├── raw_response: JSONB (original VLM response)
├── processing_time_ms: INTEGER
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

#### Extracted Field
```
extracted_fields
├── id: UUID (PK)
├── extraction_id: UUID (FK → extraction_results)
├── field_type: ENUM (key_value, table_cell, entity, text_block)
├── field_key: VARCHAR(255) (nullable, for key-value pairs)
├── field_value: TEXT
├── page_number: INTEGER
├── bounding_box: JSONB {x, y, width, height}
├── confidence: FLOAT (0.0–1.0, merged VLM + CV score)
├── vlm_confidence: FLOAT (raw VLM confidence)
├── cv_quality_score: FLOAT (classical CV region quality)
├── is_required: BOOLEAN (template mode: was this a required field?)
├── is_missing: BOOLEAN (template mode: required but not found)
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

#### Audit Log Entry
```
audit_log
├── id: UUID (PK)
├── document_id: UUID (FK → documents)
├── field_id: UUID (FK → extracted_fields, nullable)
├── step_name: VARCHAR(100) (e.g., "deskew", "blur_detection", "vlm_extraction")
├── step_order: INTEGER
├── input_summary: JSONB (what went in)
├── output_summary: JSONB (what came out)
├── parameters: JSONB (e.g., {angle: 4.2, method: "hough"})
├── duration_ms: INTEGER
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

#### Chat Message
```
chat_messages
├── id: UUID (PK)
├── document_id: UUID (FK → documents)
├── user_id: UUID (FK → auth.users)
├── role: ENUM (user, assistant)
├── content: TEXT
├── citations: JSONB (array of {page, bounding_box, text_span})
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

#### Raw Baseline (for comparison view)
```
raw_baselines
├── id: UUID (PK)
├── document_id: UUID (FK → documents)
├── raw_fields: JSONB (array of {field_key, field_value, bounding_box, confidence})
├── created_at: TIMESTAMPTZ
└── updated_at: TIMESTAMPTZ
```

## 2. Performance Specification

| Metric | Target | Condition |
|---|---|---|
| Single-page processing | < 10 seconds | Including CV preprocessing + VLM API call (varies by provider) |
| Chat response | < 3 seconds | Single-turn, grounded answer |
| Chat streaming first token | < 500ms | Time to first streamed token |
| API response (non-processing) | < 500ms | Document list, extraction results, chat history |
| Frontend initial load | < 2 seconds | Lighthouse, desktop, cached assets |
| Landing page load | < 1.5 seconds | Lighthouse performance score > 90 |
| Docker Compose startup | < 2 minutes | Cold start to accessible application |
| Concurrent users | 5–10 | Portfolio demo scale, not enterprise |

## 3. Software Environment

- **Operating Systems:** Linux (primary), macOS (development)
- **Python:** 3.11+
- **Node.js:** 20+ LTS
- **Docker:** 24+
- **Docker Compose:** v2+
- **Browser support:** Chrome 120+, Firefox 120+, Safari 17+, Edge 120+

### External Dependencies

| Dependency | Purpose | Version |
|---|---|---|
| FastAPI | Backend framework | latest stable |
| LangGraph | Pipeline + chat orchestration | latest stable |
| OpenCV (cv2) | Classical CV preprocessing | 4.x |
| Pydantic | Data validation + serialization | 2.x |
| SQLAlchemy | Database ORM | 2.x |
| Alembic | Database migrations | latest stable |
| supabase-py | Supabase client (storage) | latest stable |
| PyJWT | JWT validation | latest stable |
| pdf2image / PyMuPDF | PDF to image conversion | latest stable |
| React | Frontend framework | 18+ |
| TypeScript | Type safety | 5.x |
| Vite | Frontend build tool | 5+ |
| @supabase/supabase-js | Supabase client (auth, storage) | latest stable |
| @tanstack/react-query | Server state management | 5.x |
| zustand | Local state management | latest stable |
| openai | OpenAI provider (optional) | latest stable |
| google-generativeai | Google Gemini provider (optional) | latest stable |
| ollama | Ollama local provider (optional) | latest stable |

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VLM_PROVIDER` | No | `dashscope` | Active VLM provider: `dashscope`, `openai`, `google`, `ollama` |
| `DASHSCOPE_API_KEY` | If provider=dashscope | — | Alibaba DashScope API key |
| `DASHSCOPE_MODEL` | No | `qwen-vl-max` | DashScope model identifier |
| `OPENAI_API_KEY` | If provider=openai | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model identifier |
| `GOOGLE_API_KEY` | If provider=google | — | Google AI API key |
| `GOOGLE_MODEL` | No | `gemini-pro-vision` | Google model identifier |
| `OLLAMA_BASE_URL` | If provider=ollama | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | If provider=ollama | — | Ollama model name |
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | — | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key |
| `REDIS_URL` | No | — | Redis connection URL (optional) |

## 4. Security & Compliance

- All secrets (VLM API keys, Supabase keys) via environment variables — only the active provider's key is required
- `.env` in `.gitignore` — `.env.example` committed with placeholder values
- Supabase RLS policies enforce user isolation at database level
- JWT validation on every backend request — no trust of frontend claims
- File upload validation: MIME type check, file size limit, filename sanitization
- No PII stored beyond what Supabase Auth collects (email, OAuth profile)
- HTTPS enforced in any non-localhost deployment
- CORS configured to allow only the frontend origin
- Rate limiting on DashScope API calls to prevent cost overrun

---
#srs #technical-spec #engineering #docmind-vlm
