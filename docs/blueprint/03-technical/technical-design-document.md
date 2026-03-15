# Technical Design Document: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Technical Design

---

## 1. Module Structure

### 1.1 Backend — Core Module (`app/core/`)

**`config.py`** — Application settings via Pydantic BaseSettings
- Reads from environment variables: DASHSCOPE_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, REDIS_URL
- Validates all required secrets are present at startup (fail fast)
- Immutable settings object shared across application

**`auth.py`** — JWT authentication middleware
- Decodes Supabase JWT from Authorization header
- Extracts `sub` (user_id) for RLS enforcement
- FastAPI dependency: `get_current_user() -> User`
- Rejects expired/invalid tokens with 401

**`dependencies.py`** — FastAPI dependency injection
- Database session factory
- Supabase client instances (storage, admin)
- DashScope client
- Shared across all route handlers

### 1.2 Backend — API Layer (`app/api/`)

Each file is a FastAPI APIRouter:
- `documents.py` — CRUD + processing trigger
- `extractions.py` — Extraction results + audit + overlay + comparison
- `chat.py` — Chat messages + SSE streaming
- `templates.py` — Template listing and schema retrieval

Route handlers are thin — they validate input, call service layer, return response. No business logic in routes.

### 1.3 Backend — Service Layer (`app/services/`)

**`document_service.py`**
- `create_document(user_id, metadata)` → Document record
- `get_documents(user_id, page, limit)` → Paginated list
- `delete_document(user_id, document_id)` → Cascading delete (storage + DB)
- `trigger_processing(document_id, template_type?)` → Starts LangGraph pipeline

**`extraction_service.py`**
- `get_extraction(document_id)` → Extraction results with fields
- `get_audit_trail(document_id)` → Ordered audit log entries
- `get_overlay_data(document_id)` → Confidence regions + colors + tooltips
- `get_comparison(document_id)` → Enhanced vs raw baseline diff

**`chat_service.py`**
- `send_message(document_id, user_id, message)` → Triggers LangGraph chat agent, streams response
- `get_history(document_id, user_id, page, limit)` → Chat message history

### 1.4 Backend — Pipeline Module (`app/pipeline/`)

#### Processing Pipeline (`app/pipeline/processing/`)

**`graph.py`** — LangGraph StateGraph definition
```python
class ProcessingState(TypedDict):
    document_id: str
    original_image: bytes
    preprocessed_image: bytes
    quality_map: dict          # region -> quality score
    extraction_mode: str       # "general" or "template"
    template_type: str | None
    raw_vlm_response: dict
    extracted_fields: list[ExtractedField]
    audit_entries: list[AuditEntry]
    status: str
    error: str | None

graph = StateGraph(ProcessingState)
graph.add_node("preprocess", preprocess_node)
graph.add_node("extract", extract_node)
graph.add_node("postprocess", postprocess_node)
graph.add_node("store", store_node)
graph.add_edge("preprocess", "extract")
graph.add_edge("extract", "postprocess")
graph.add_edge("postprocess", "store")
```

**`preprocess.py`** — Classical CV preprocessing node
- Calls `cv.deskew.detect_and_correct(image)`
- Calls `cv.quality.assess_regions(image, grid_size=8)`
- Logs all operations to audit entries in state
- Returns updated state with preprocessed image + quality map

**`extract.py`** — VLM extraction node
- Constructs prompt based on extraction mode:
  - General: "Extract all visible content..."
  - Template: "Extract these specific fields: {schema}..."
- Calls DashScope API via `VLMProvider.extract(image, prompt)`
- Parses structured response into `ExtractedField` objects
- Logs API call details to audit entries

**`postprocess.py`** — Post-processing node
- Merges VLM confidence with CV quality scores: `final_confidence = vlm_conf * 0.7 + cv_quality * 0.3`
- Template mode: validates required fields, flags missing
- Generates low-confidence explanations from quality map data (blur, noise, truncation)
- Adds postprocessing audit entries

**`store.py`** — Persistence node
- Saves extraction results, fields, and audit log to Postgres
- Updates document status to "ready" (or "error" on failure)

#### Chat Agent (`app/pipeline/chat/`)

**`graph.py`** — LangGraph StateGraph for chat
```python
class ChatState(TypedDict):
    document_id: str
    extraction_context: list[ExtractedField]
    chat_history: list[ChatMessage]
    user_message: str
    intent: str
    retrieved_context: list[dict]
    response: str
    citations: list[Citation]

graph = StateGraph(ChatState)
graph.add_node("router", router_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("reason", reason_node)
graph.add_node("cite", cite_node)
graph.add_edge("router", "retrieve")
graph.add_edge("retrieve", "reason")
graph.add_edge("reason", "cite")
```

**`router.py`** — Intent classification
- Classifies user message: factual_lookup, reasoning, summarization, comparison
- Uses Qwen3-VL with lightweight classification prompt

**`retrieve.py`** — Context retrieval
- Searches extracted fields by semantic similarity to user question
- If insufficient, sends targeted Qwen3-VL query on specific document region

**`reason.py`** — Answer generation
- Constructs grounded prompt with retrieved context + extraction data
- System prompt enforces: "Only answer based on information found in the document. If you cannot find the answer, say so."
- Streams response via DashScope API

**`cite.py`** — Citation attachment
- Parses response for factual claims
- Matches each claim to source field (bounding box, page, text span)
- Attaches citation objects to response

### 1.5 Backend — CV Module (`app/cv/`)

**`deskew.py`**
- `detect_skew(image) -> float` — Hough line transform, returns angle in degrees
- `correct_skew(image, angle) -> ndarray` — Affine rotation
- `detect_and_correct(image, threshold=2.0) -> tuple[ndarray, float]` — Combined; skips if angle < threshold

**`quality.py`**
- `assess_blur(region) -> float` — Laplacian variance (0.0 = very blurry, 1.0 = sharp)
- `assess_noise(region) -> float` — Median filter deviation (0.0 = very noisy, 1.0 = clean)
- `assess_contrast(region) -> float` — Histogram spread analysis
- `assess_regions(image, grid_size=8) -> dict[tuple, RegionQuality]` — Grid-based quality map for entire image

**`preprocessing.py`**
- `convert_pdf_to_images(pdf_bytes) -> list[ndarray]` — PDF pages to OpenCV images
- `normalize_image(image) -> ndarray` — Resize to standard processing resolution, convert color space

### 1.6 Backend — VLM Provider (`app/providers/`)

**Provider-agnostic design.** The VLM layer is fully abstracted behind a protocol interface. The system supports multiple providers out of the box and can be extended with new ones by implementing a single class. The active provider is selected via environment variable (`VLM_PROVIDER`).

**`vlm_provider.py`** — Abstract interface (Protocol)
```python
class VLMResponse(TypedDict):
    content: str
    fields: list[dict]          # extracted fields with bounding boxes
    confidence: float           # model-reported confidence
    model: str                  # model identifier for audit trail
    usage: dict                 # token/cost tracking

class VLMProvider(Protocol):
    """Provider-agnostic interface for vision-language model operations."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def extract(self, image: bytes, prompt: str) -> VLMResponse:
        """Extract structured data from document image."""
        ...

    async def classify(self, image: bytes, prompt: str) -> str:
        """Classify document type."""
        ...

    async def chat(
        self, image: bytes, messages: list, stream: bool = False
    ) -> AsyncIterator[str]:
        """Chat about a document image. Supports streaming."""
        ...

    async def health_check(self) -> bool:
        """Verify provider API is reachable and authenticated."""
        ...
```

**`provider_factory.py`** — Factory for provider selection
```python
def get_vlm_provider(provider_name: str | None = None) -> VLMProvider:
    """
    Returns configured VLM provider instance.

    Provider selected by:
    1. Explicit provider_name argument
    2. VLM_PROVIDER environment variable
    3. Default: "dashscope"

    Supported providers: dashscope, openai, google, ollama
    """
```

**`dashscope_provider.py`** — Alibaba DashScope (Qwen3-VL)
- Default provider
- Implements VLMProvider for Qwen3-VL via DashScope API
- Handles API key auth, request formatting, response parsing
- Retry logic with exponential backoff for transient failures
- Rate limiting to prevent cost overrun
- Config: `DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL` (default: `qwen-vl-max`)

**`openai_provider.py`** — OpenAI (GPT-4V / GPT-4o)
- Implements VLMProvider for OpenAI vision models
- Supports GPT-4V, GPT-4o with vision
- Config: `OPENAI_API_KEY`, `OPENAI_MODEL` (default: `gpt-4o`)

**`google_provider.py`** — Google (Gemini Pro Vision)
- Implements VLMProvider for Google Gemini vision models
- Config: `GOOGLE_API_KEY`, `GOOGLE_MODEL` (default: `gemini-pro-vision`)

**`ollama_provider.py`** — Ollama (Local self-hosted models)
- Implements VLMProvider for locally hosted VLMs via Ollama
- Enables fully offline operation — no API keys needed
- Config: `OLLAMA_BASE_URL` (default: `http://localhost:11434`), `OLLAMA_MODEL`

**Provider comparison (for README / docs):**

| Provider | Model | Cost | Latency | Offline | Setup |
|---|---|---|---|---|---|
| DashScope | Qwen3-VL | Cheap | Low | No | API key |
| OpenAI | GPT-4o | Moderate | Low | No | API key |
| Google | Gemini Pro Vision | Moderate | Low | No | API key |
| Ollama | Any local VLM | Free | Varies | Yes | Local install |

**Audit trail integration:** Every VLM call logs `provider_name` and `model_name` in the audit trail, so the comparison view can show which model produced which result.

### 1.7 Frontend — Key Components

**`DocumentViewer`** — Canvas-based document renderer
- Renders document pages as images
- Overlay layer for confidence heatmap (togglable)
- Overlay layer for bounding boxes (togglable)
- Zoom (mouse wheel), pan (drag), page navigation
- Click handler: maps canvas coordinates to field bounding boxes

**`ExtractionPanel`** — Extraction results display
- Fields view: table with confidence badges
- JSON view: collapsible formatted JSON
- Click field → emits event → DocumentViewer highlights source region

**`ChatPanel`** — Conversational interface
- Message thread with user/assistant message bubbles
- Citation blocks: clickable references to document regions
- Input box with send button
- SSE-based streaming for assistant responses

**`AuditPanel`** — Pipeline transparency
- Vertical timeline of processing steps
- Per-field drill-down showing full provenance chain

**`ComparePanel`** — Side-by-side comparison
- Two-column extraction result display
- Color-coded diff highlighting

## 2. API & Integration Details

### 2.1 DashScope API (External)
- **Base URL:** `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
- **Auth:** API key in header (`Authorization: Bearer <DASHSCOPE_API_KEY>`)
- **Model:** `qwen-vl-max` (or latest Qwen3-VL model identifier)
- **Payload:** Multimodal message with image (base64) + text prompt
- **Response:** Structured text with extracted content
- **Rate limit:** Configured per deployment; default 10 RPM for demo

### 2.2 Supabase (External)
- **Auth:** Supabase JS SDK on frontend; JWT validation on backend
- **Database:** Direct Postgres connection from backend via SQLAlchemy (connection string from SUPABASE_URL)
- **Storage:** Supabase Storage SDK for upload (frontend) and signed URL generation (backend)
- **RLS:** Postgres policies: `auth.uid() = user_id` on all tables

## 3. Algorithm & Logic

### 3.1 Confidence Score Merging
```
final_confidence = vlm_confidence * 0.7 + cv_quality_score * 0.3

Where:
  vlm_confidence = VLM's reported confidence for the extracted field (0.0–1.0)
  cv_quality_score = average of blur, noise, contrast scores for the field's region
```

Rationale: VLM confidence is the primary signal (it did the extraction), but CV quality catches cases where the VLM is confidently wrong on degraded input. The 70/30 split can be tuned based on benchmark evaluation.

### 3.2 Document Type Auto-Detection
```
1. Send document image to Qwen3-VL with classification prompt:
   "What type of document is this? Options: invoice, receipt, contract, certificate, other"
2. Parse response → document_type + confidence
3. If confidence > 0.8: use detected type
4. If confidence 0.5–0.8: suggest detected type, let user confirm
5. If confidence < 0.5: default to general mode (schema-free)
```

### 3.3 Chat Grounding Rule
```
System prompt includes:
"You are a document analysis assistant. ONLY answer based on information
visible in the uploaded document. For every factual claim, cite the specific
page and region where you found the information. If the information is not
in the document, respond: 'I could not find information about that in this
document.' NEVER fabricate information."
```

---
#technical-design #implementation #coding-plan #docmind-vlm
