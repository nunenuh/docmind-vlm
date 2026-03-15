# Product Requirements Document (PRD): DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Product Definition

---

## 1. Executive Summary

DocMind-VLM is a web application that lets users upload documents (PDF, image, scan), extract structured data using a vision-language model enhanced by classical computer vision preprocessing, and then chat with their document to ask contextual questions. The system provides full transparency into the extraction process via audit trails, confidence overlays, and pipeline comparison views.

## 2. Problem Statement

Document processing remains a manual, error-prone, and opaque process:
- Scanned documents with degraded quality, complex layouts, and mixed languages break commodity OCR and VLM tools silently.
- Existing proprietary solutions (AWS Textract, Azure Form Recognizer) are expensive black boxes with no visibility into extraction confidence or failure modes.
- Open-source alternatives are either text-only parsers (no vision) or thin VLM wrappers with no architecture, tests, or production thinking.
- Users cannot ask follow-up questions about their documents after extraction — it's a one-shot process with no conversational interaction.

## 3. Goals & Success Metrics

| Goal | Metric | Target |
|---|---|---|
| Accurate extraction | Field-level accuracy on demo benchmark | > 90% |
| Fast processing | Time from upload to first extraction result | < 3 seconds |
| Transparent AI | Every extracted field has provenance and confidence | 100% of fields |
| Chat grounding | Chat answers cite source region in document | 100% of answers |
| Portfolio quality | One-command setup, tests, CI/CD, docs | Tier 1 standard |
| Code quality | Test coverage | > 80% |

## 4. Target Audience

- **Primary:** Compliance Officers processing multilingual, scanned, layout-heavy regulatory documents
- **Secondary:** Operations Analysts processing invoices, receipts, and financial documents
- **Meta:** Hiring managers evaluating portfolio quality (see User Persona Definition)

## 5. Functional Requirements

### FR 0: Landing Page (Public — No Auth Required)
- Public-facing landing page at root URL — no login needed to view
- **Hero section:** Headline + subline communicating the core value proposition ("Chat with any document. See exactly what the AI sees.") with a compelling hero image or animated demo preview
- **Live demo preview:** Embedded interactive demo or auto-playing video showing the full workflow: upload → extract → confidence overlay → chat — so visitors SEE the product before signing up
- **Feature showcase sections:**
  - "Extract" — show structured extraction from a messy scanned document with confidence badges
  - "Understand" — show confidence overlay heatmap on a real document
  - "Compare" — show side-by-side raw VLM vs enhanced pipeline output
  - "Chat" — show a conversation with a document, with cited answers
- **How it works:** 3-4 step visual flow (Upload → Extract → Verify → Chat)
- **Tech credibility section:** "Built with" badges (Qwen3-VL, LangGraph, FastAPI, React, Supabase) — signals to technical hiring managers
- **Social proof / moat statement:** Brief section explaining WHY this is different — "7 years of production OCR meets modern vision-language models. We know when the AI is wrong."
- **Call-to-action:** Prominent "Try it free" / "Sign in with Google" / "Sign in with GitHub" buttons — appears in hero and at bottom
- **Footer:** GitHub repo link, MIT license badge, author link (nunenuh.me)
- Page must be fast (< 1.5s load), responsive, and visually polished — this is the first impression for hiring managers

### FR 1: Authentication
- User login via Google OAuth or GitHub OAuth (Supabase Auth)
- Protected routes — unauthenticated users redirected to login
- User session management with JWT tokens

### FR 2: Document Upload
- Support formats: PDF, PNG, JPG, JPEG, TIFF, WebP
- Max file size: 20MB
- Drag-and-drop upload area + file picker fallback
- Upload progress indicator
- Document stored in Supabase Storage, metadata in Postgres

### FR 3: Document Processing Pipeline
- Classical CV preprocessing: deskew detection/correction, blur detection, noise assessment, quality scoring per region
- VLM extraction via Qwen3-VL (DashScope API): layout understanding, text recognition, table detection, entity extraction
- Pipeline orchestrated via LangGraph with step-by-step logging
- Real-time progress feedback to frontend during processing

### FR 4: Extraction — General Mode (Schema-Free)
- VLM extracts all detected content: key-value pairs, tables, text blocks, entities
- Output as structured JSON
- Each extracted field includes: value, source region (bounding box), confidence score, processing steps

### FR 5: Extraction — Template Mode (Schema-Driven)
- Predefined templates for common document types (invoice, receipt, contract, certificate)
- Auto-detection of document type with fallback to manual selection
- Extraction against specific schema with field validation
- Missing required fields flagged explicitly

### FR 6: Extraction Audit Trail
- Every extracted field records: source region coordinates, confidence score, preprocessing steps applied, VLM model used, timestamp
- Audit trail viewable per field via UI interaction (click field to see provenance)

### FR 7: Confidence Overlay
- Visual heatmap rendered on the document image
- Green (high confidence) → Yellow (medium) → Red (low confidence) per region
- Low-confidence regions flagged with explanatory notes (e.g., "blur detected", "region truncated")

### FR 8: Pipeline Comparison View
- Side-by-side display: "Raw VLM Output" vs "DocMind-VLM Enhanced Output"
- Pre-computed raw VLM baseline for demo documents
- Visual diff highlighting fields that were corrected or added by the enhanced pipeline

### FR 9: Document Chat
- Chat interface for conversational Q&A about the uploaded document
- Powered by LangGraph agent with access to extracted data + original document
- Every chat answer must include citation: page number, region, exact text span
- Multi-turn conversation with context retention
- Chat history stored per document per user

### FR 10: Export
- Export extracted data as: JSON, CSV
- Copy chat summary to clipboard
- Download annotated document (with confidence overlay baked in) as PDF

## 6. Non-Functional Requirements

### NFR 1: Security
- All API keys (DashScope, Supabase) stored in environment variables, never in code
- Supabase Row Level Security: users can only access their own documents
- HTTPS only in production
- File upload validation: type checking, size limits, malware scan consideration

### NFR 2: Performance
- Document processing: < 10 seconds for a single-page document
- Chat response: < 3 seconds per answer
- Frontend: < 2 second initial page load (Lighthouse)
- API response: < 500ms for non-processing endpoints

### NFR 3: Reliability
- Graceful error handling: processing failures show clear error message, not a blank screen
- Retry logic for DashScope API calls (transient failures)
- Document processing is idempotent — re-processing same document produces same results

### NFR 4: Portability
- Full application runs via `docker compose up` on Linux/macOS
- No GPU required (VLM inference via DashScope API)
- Environment variables for all configuration (no hardcoded values)

### NFR 5: Observability
- Structured logging (JSON) for all backend operations
- Request tracing with correlation IDs
- Processing pipeline timing metrics exposed

## 7. Assumptions & Dependencies

**Assumptions:**
- DashScope API remains available and affordable for demo usage
- Qwen3-VL supports document understanding with bounding box output
- Supabase free tier is sufficient for demo-scale usage
- Users have a modern browser (Chrome, Firefox, Safari, Edge)

**Dependencies:**
- Alibaba Model Studio (DashScope) — Qwen3-VL API
- Supabase — Auth, Postgres, Storage
- LangGraph — agent orchestration
- OpenCV — classical CV preprocessing
- React + TypeScript — frontend

---
#prd #product-scope #features #docmind-vlm
