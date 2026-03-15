# Compliance Specification: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Quality Assurance

---

## 1. Regulatory Requirements

As an open-source portfolio project (not a commercial SaaS), full regulatory compliance (GDPR, SOC2, HIPAA) is not required. However, the project follows best practices to demonstrate awareness:

- **Data minimization:** Only collect what's needed (OAuth profile, uploaded documents)
- **Right to deletion:** User can delete their documents, triggering cascading removal of all related data (storage files, extractions, chat history, audit logs)
- **Transparency:** Privacy-relevant behavior documented (VLM API calls send document images to third-party services; Ollama provider keeps data local)
- **No tracking:** No analytics, cookies, or user behavior tracking beyond what Supabase Auth requires

## 2. Data Standards

- **Timestamps:** All timestamps stored as UTC (TIMESTAMPTZ) in Postgres
- **IDs:** UUID v4 for all primary keys — no sequential IDs exposed
- **JSON output:** All API responses follow consistent envelope structure
- **Extraction output:** Structured JSON conforming to documented schemas per template type
- **Bounding boxes:** Normalized coordinates format: `{x, y, width, height}` as floats (0.0–1.0 relative to page dimensions)

## 3. Licensing & IP

- **License:** MIT or Apache 2.0 (open-source, permissive)
- **No NDA code:** Entire codebase is fresh — no code from TabLogs, Tigapilar, or any private engagement
- **Demo documents:** All demo documents are either created from scratch or sourced from public domain datasets (SROIE, CORD, FUNSD)
- **Dependencies:** All dependencies are open-source with compatible licenses
- **VLM providers:** Users bring their own API keys — no keys bundled in the project

## 4. Audit & Logging

- **Structured logging:** All backend logs in JSON format (structured, parseable)
- **Correlation IDs:** Every request tagged with a unique request_id for tracing
- **Audit trail:** Document processing pipeline logs every step with inputs, outputs, timing, and parameters — stored in database for user transparency
- **No sensitive data in logs:** Document content, extracted fields, and chat messages are NOT logged to stdout/files — only stored in database with RLS protection

---
#compliance #standards #audit #docmind-vlm
