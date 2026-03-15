# Architecture Decision Records (ADR): DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Technical Design

---

## ADR 1: VLM via DashScope API (Not Self-Hosted)

- **Status:** Approved
- **Context:** Qwen3-VL can be run locally (7B model on GPU) or via Alibaba Model Studio (DashScope API). The project needs VLM inference for document extraction and chat.
- **Decision:** Use DashScope API for Qwen3-VL inference.
- **Consequences:**
  - Positive: No GPU infrastructure needed; cheap for demo/dev usage; fast to iterate on prompts; reduces Docker Compose complexity
  - Positive: Portfolio demonstrates "I make pragmatic infrastructure decisions" (not "I must self-host everything")
  - Negative: External dependency — API availability and pricing can change
  - Negative: Network latency added to processing time
- **Alternatives Considered:**
  - Self-hosted Qwen3-VL-7B: Rejected — requires GPU in Docker Compose; hiring managers can't easily run `docker compose up` without a GPU
  - OpenAI GPT-4V: Rejected — more expensive, proprietary, doesn't demonstrate open-source VLM expertise
- **Mitigation:** Model layer is behind a provider-agnostic interface (`VLMProvider`). See ADR 8.

## ADR 8: Provider-Agnostic VLM Architecture

- **Status:** Approved
- **Context:** The VLM market is evolving rapidly. Locking the system to a single provider (DashScope/Qwen) creates vendor risk and limits the portfolio's appeal. Different users may prefer different providers based on cost, privacy, or capability. The system should support multiple VLM backends by design.
- **Decision:** Implement a `VLMProvider` protocol (Python Protocol class) that abstracts all VLM operations. Ship 4 provider implementations out of the box: DashScope (Qwen3-VL), OpenAI (GPT-4o), Google (Gemini Pro Vision), Ollama (local self-hosted). Provider selection via `VLM_PROVIDER` environment variable and a factory function.
- **Consequences:**
  - Positive: Zero vendor lock-in — switch providers by changing one env var
  - Positive: Ollama provider enables fully offline operation (no API keys, no cost)
  - Positive: Portfolio signal — "I design for extensibility, not just the happy path"
  - Positive: Comparison view can show results from DIFFERENT providers side-by-side (future feature)
  - Positive: Audit trail records which provider/model produced each extraction — full traceability
  - Negative: Must maintain 4 provider implementations; API differences require normalization
  - Negative: Each provider has different response formats — parsing layer per provider
- **Alternatives Considered:**
  - Single provider (DashScope only): Rejected — vendor lock-in, limits portfolio appeal, doesn't demonstrate architectural thinking
  - LiteLLM as abstraction layer: Considered — provides multi-provider support out of the box, but adds a dependency and hides the architectural work we want to showcase in the portfolio
  - Abstract base class (ABC): Rejected in favor of Protocol — Protocol is more Pythonic (structural subtyping), doesn't require inheritance, easier to test with mocks
- **Design details:**
  - `VLMProvider` protocol defines: `extract()`, `classify()`, `chat()`, `health_check()`, `provider_name`, `model_name`
  - `VLMResponse` typed dict normalizes output across all providers
  - `get_vlm_provider()` factory handles instantiation and configuration
  - Each provider handles its own auth, rate limiting, retry logic, and response parsing
  - Default provider: DashScope (cheapest for demo); configurable per deployment

## ADR 2: LangGraph for Pipeline Orchestration (Not Plain Functions)

- **Status:** Approved
- **Context:** The document processing pipeline has distinct steps (preprocess → extract → postprocess → store) with state passing between them. The chat agent needs stateful multi-turn conversation with routing logic.
- **Decision:** Use LangGraph for both the processing pipeline and the chat agent.
- **Consequences:**
  - Positive: Graph-based orchestration makes pipeline steps explicit, testable, and independently replaceable
  - Positive: LangGraph's checkpointer handles chat memory natively
  - Positive: Portfolio signal — "AI agent orchestration" is the #1 hiring signal in 2026
  - Positive: Built-in support for streaming, retries, and state persistence
  - Negative: Added dependency and learning curve; overkill if pipeline were truly linear
- **Alternatives Considered:**
  - Plain Python functions chained together: Rejected — loses graph visibility, no built-in state management for chat, harder to add branching logic later
  - Celery task chains: Rejected — heavier infrastructure (needs broker), designed for distributed async not graph orchestration
  - Custom pipeline framework: Rejected — reinventing the wheel when LangGraph exists

## ADR 3: Supabase for Managed Infrastructure (Not Self-Hosted Postgres)

- **Status:** Approved
- **Context:** The application needs authentication (OAuth), a relational database (documents, extractions, chat), and file storage. These are commodity infrastructure, not the differentiating part of the product.
- **Decision:** Use Supabase for Auth + Postgres + Storage.
- **Consequences:**
  - Positive: Auth, DB, and storage in one platform — fast to set up
  - Positive: Row Level Security built into Supabase — user isolation without custom middleware
  - Positive: Free tier sufficient for demo/portfolio usage
  - Positive: Backend still fully custom FastAPI — Supabase is just the infrastructure layer
  - Negative: Vendor dependency; adds external service to local development
- **Alternatives Considered:**
  - Full custom (Postgres + MinIO + custom OAuth): Rejected — more impressive to demo but slower to build; auth is not the showcase, the pipeline is
  - Firebase: Rejected — better for mobile; Postgres is more natural for structured document data
- **Mitigation:** Database access via SQLAlchemy — switching from Supabase Postgres to any Postgres is a connection string change. Storage via S3-compatible API — portable.

## ADR 4: Monorepo Structure (Not Separate Repos)

- **Status:** Approved
- **Context:** The project has a React frontend and a FastAPI backend. They could live in separate repos or a single monorepo.
- **Decision:** Single monorepo with `frontend/` and `backend/` directories.
- **Consequences:**
  - Positive: One `docker compose up` runs everything — critical for portfolio demo experience
  - Positive: Single repo to clone, star, and evaluate — hiring managers see everything in one place
  - Positive: Shared CI/CD pipeline; coordinated versioning
  - Negative: Larger repo size; frontend and backend CI run together
- **Alternatives Considered:**
  - Separate repos (docmind-vlm-api, docmind-vlm-web): Rejected — splits the evaluation experience; hiring manager has to clone two repos

## ADR 5: Classical CV Preprocessing (Not Pure VLM)

- **Status:** Approved
- **Context:** Qwen3-VL can process raw document images directly. However, degraded scans (skewed, blurry, noisy) reduce VLM accuracy. Classical computer vision preprocessing can improve input quality before VLM inference.
- **Decision:** Add an OpenCV-based preprocessing step before VLM extraction. Preprocessing includes deskew correction, blur detection, noise estimation, and per-region quality scoring.
- **Consequences:**
  - Positive: Improved extraction accuracy on degraded documents — the core moat
  - Positive: Quality scores per region feed directly into confidence overlay — the signature UX feature
  - Positive: Demonstrates classical CV expertise that differentiates from VLM API callers
  - Positive: Audit trail records what preprocessing was applied — transparency
  - Negative: Added processing time (~0.5s); added code complexity
- **Alternatives Considered:**
  - Pure VLM (no preprocessing): Rejected — misses the entire portfolio differentiation story; VLMs degrade on poor scans without warning
  - Full classical OCR pipeline + VLM: Rejected — overengineered; the VLM handles text recognition, classical CV handles image quality

## ADR 6: SSE for Progress Streaming (Not WebSockets)

- **Status:** Approved
- **Context:** The frontend needs real-time updates during document processing (pipeline step progress) and chat (response streaming). Options are WebSockets, Server-Sent Events (SSE), or polling.
- **Decision:** Use Server-Sent Events (SSE) for both processing progress and chat response streaming.
- **Consequences:**
  - Positive: SSE is simpler than WebSockets — unidirectional (server → client), works over standard HTTP, auto-reconnects
  - Positive: FastAPI supports SSE natively via StreamingResponse
  - Positive: No WebSocket infrastructure needed (some proxies/firewalls block WS)
  - Negative: Unidirectional only — but our use case is server-push (progress updates, chat streaming); user input goes via regular POST
- **Alternatives Considered:**
  - WebSockets: Rejected for MVP — bidirectional not needed; adds complexity (connection management, heartbeat, reconnection logic)
  - Polling: Rejected — poor UX (latency), unnecessary server load
- **Note:** Can upgrade to WebSockets in Phase 2 if bidirectional communication needed (e.g., collaborative document annotation)

## ADR 7: shadcn/ui + Tailwind (Not Material UI or Ant Design)

- **Status:** Approved
- **Context:** The frontend needs a component library for consistent, accessible, professional UI. Erfan is learning React — the library should be approachable and well-documented.
- **Decision:** Use shadcn/ui (copy-paste components built on Radix UI) with Tailwind CSS.
- **Consequences:**
  - Positive: Components are copied into the project, not imported — full control, no version lock-in
  - Positive: Tailwind is utility-first — fast to style, consistent, great for learning CSS
  - Positive: shadcn/ui has excellent documentation and is widely adopted in 2026
  - Positive: Built on Radix UI — accessible by default (keyboard nav, ARIA, focus management)
  - Negative: More manual styling than opinionated libraries like Material UI
- **Alternatives Considered:**
  - Material UI: Rejected — heavy bundle, opinionated design that's hard to customize, Google aesthetic doesn't fit "modern dark mode" vision
  - Ant Design: Rejected — enterprise aesthetic, heavy, less common in Western portfolio context
  - Headless UI + custom CSS: Rejected — too much work for learning-phase frontend

---
#adr #architecture #decisions #rationale #docmind-vlm
