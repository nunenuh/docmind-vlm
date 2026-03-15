---
created: 2026-03-10
status: planning
---

# docmind-vlm

**Status:** Blueprint Complete — Ready for Implementation
**Goal:** Chat with any document — powered by vision-language models, built on 7 years of production OCR expertise
**Repo:** github.com/nunenuh/docmind-vlm
**Portfolio:** Tier 1, Repo 2 (of 7-repo strategy)

## What

Upload any document (PDF, image, scan) — VLM understands layout + content — extract structured data with full transparency (confidence overlay, audit trail, pipeline comparison) — then chat with your document. Not just OCR anymore — multimodal understanding with conversational interaction.

## Why Only I Can Build This Well

Classical CV pipeline knowledge (UNet, CRNN, LayoutLM) + modern VLM = know when the model is hallucinating layout structure. Most VLM users are prompt engineers without CV fundamentals.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| Pipeline | LangGraph (processing + chat agent) |
| Classical CV | OpenCV (deskew, quality assessment) |
| VLM | Provider-agnostic: DashScope (Qwen3-VL), OpenAI, Google, Ollama |
| Auth | Supabase Auth (Google + GitHub OAuth) |
| Database | Supabase Postgres (RLS) |
| Storage | Supabase Storage |
| Frontend | React + TypeScript + Vite + shadcn/ui |

## Key Features

- **Two extraction modes:** General (schema-free) + Template-driven (invoice, receipt, contract, certificate)
- **Confidence overlay:** Visual heatmap showing where the AI is certain vs uncertain
- **Extraction audit trail:** Full provenance per field (source region, processing steps, confidence)
- **Pipeline comparison:** Side-by-side raw VLM vs enhanced output
- **Document chat:** Conversational Q&A with source citations
- **Provider-agnostic VLM:** Swap providers via one env var
- **Landing page:** Public showcase with demo preview

## Blueprint (21 docs)

All product documentation in `docs/blueprint/`:

- [[projects/docmind-vlm/docs/blueprint/product-documentation-checklist]] — Master control
- `01-strategy/` — Vision, BRD, MRD, Personas, User Journeys
- `02-product/` — PRD, User Stories, Acceptance Criteria, Functional Spec, UI Spec, UX Spec
- `03-technical/` — Architecture, 8 ADRs, SRS, Technical Design
- `04-quality/` — Test Strategy, Security, Compliance
- `05-operations/` — Handover Instructions, Maintenance Plan

## Key Links

- [[self/detail/18 - Portfolio Strategy & Market Analysis]]
- [[concepts/business/AI Market Landscape 2026]]
