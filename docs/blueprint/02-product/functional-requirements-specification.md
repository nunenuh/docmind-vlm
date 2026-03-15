# Functional Requirements Specification: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Product Definition

---

## 1. Feature: Authentication

- **Input:** User clicks "Sign in with Google" or "Sign in with GitHub"
- **Processing:** Supabase Auth handles OAuth flow → returns JWT access token + refresh token → frontend stores tokens → backend validates JWT on every request
- **Output:** Authenticated session; user redirected to dashboard

## 2. Feature: Document Upload & Storage

- **Input:** File (PDF, PNG, JPG, JPEG, TIFF, WebP), max 20MB
- **Processing:**
  1. Frontend validates file type and size
  2. File uploaded to Supabase Storage at path: `{user_id}/{document_id}/{filename}`
  3. Document metadata record created in Postgres: id, user_id, filename, file_type, file_size, storage_path, status (uploaded), created_at
- **Output:** Document record with status "uploaded"; file available in storage

## 3. Feature: Classical CV Preprocessing

- **Input:** Document image (converted from PDF if needed)
- **Processing:**
  1. **Page conversion:** PDF pages rendered to images (pdf2image / PyMuPDF)
  2. **Skew detection:** Hough transform to detect tilt angle
  3. **Deskew correction:** Rotate image if tilt > 2 degrees
  4. **Quality assessment per region:** Grid-based analysis
     - Blur detection: Laplacian variance per region
     - Noise estimation: median filter comparison
     - Contrast assessment: histogram analysis
  5. **Region quality map:** Each grid cell gets a quality score (0.0–1.0)
  6. All steps logged with parameters and results to audit trail
- **Output:** Preprocessed image + region quality map + audit log entries

## 4. Feature: VLM Extraction (General Mode)

- **Input:** Preprocessed image + region quality map
- **Processing:**
  1. Construct prompt for Qwen3-VL: "Extract all visible content from this document. For each item, provide: type (key-value, table, entity, text-block), value, and bounding box coordinates."
  2. Send to DashScope API with image
  3. Parse structured response into extraction result objects
  4. Merge VLM confidence with classical CV region quality scores → final confidence per field
  5. Store extraction results in Postgres linked to document
- **Output:** List of extracted fields, each with: type, key, value, bounding_box, confidence, audit_steps

## 5. Feature: VLM Extraction (Template Mode)

- **Input:** Preprocessed image + document type (auto-detected or user-selected)
- **Processing:**
  1. **Auto-detection:** Send image to Qwen3-VL with classification prompt → returns document type with confidence
  2. **Schema lookup:** Load predefined schema for detected type (e.g., invoice schema: vendor, date, line_items, subtotal, tax, total)
  3. **Targeted extraction:** Construct schema-aware prompt: "Extract the following fields from this [document_type]: {field_list}. For each field, provide value and bounding box."
  4. **Validation:** Check all required fields present; flag missing fields
  5. Merge confidence scores (VLM + classical CV quality)
  6. Store results in Postgres
- **Output:** Schema-validated extraction result with field status (found/missing/low_confidence)

### Predefined Templates (MVP)

| Template | Required Fields | Optional Fields |
|---|---|---|
| Invoice | vendor_name, invoice_number, date, total | line_items, subtotal, tax, currency, due_date |
| Receipt | vendor_name, date, total | line_items, payment_method, tax |
| Contract | parties, effective_date, governing_law | termination_clause, penalty_clause, auto_renewal, signatures |
| Certificate | issuing_authority, holder_name, issue_date, expiry_date | scope, certificate_number, standard_reference |

## 6. Feature: Confidence Overlay Generation

- **Input:** Extraction results with confidence scores + region quality map
- **Processing:**
  1. Map confidence scores to color scale: green (> 0.8), yellow (0.5–0.8), red (< 0.5)
  2. Generate overlay image: semi-transparent colored rectangles over source regions
  3. Attach tooltip data per low-confidence region: reason string from quality assessment
- **Output:** Overlay image data (SVG or canvas coordinates) + tooltip metadata

## 7. Feature: Pipeline Comparison

- **Input:** Enhanced extraction results + pre-computed raw VLM baseline (for demo documents)
- **Processing:**
  1. Load pre-computed raw baseline for the document (stored in Postgres/seed data)
  2. Diff: identify fields corrected (value changed), fields added (in enhanced but not raw), fields unchanged
  3. Generate diff metadata with highlight type per field (corrected=blue, added=green, unchanged=none)
- **Output:** Comparison data structure with both extraction results + diff highlights

## 8. Feature: Document Chat (LangGraph Agent)

- **Input:** User message + document context (extraction results + original image)
- **Processing (LangGraph graph):**
  1. **Router node:** Classify user intent (factual lookup, reasoning, summarization, comparison)
  2. **Retrieval node:** Search extraction results for relevant fields; if needed, send follow-up query to Qwen3-VL with specific region of document
  3. **Reasoning node:** Generate answer using extraction data + VLM response
  4. **Citation node:** Attach source citation (page, bounding box, text span) to every claim in the answer
  5. **Response node:** Format final response with inline citations
  6. Store message pair (user + assistant) in Postgres chat_messages table
- **Output:** Answer with citations; chat history updated

## 9. Feature: Export

- **Input:** User clicks export button; selects format
- **Processing:**
  - **JSON:** Serialize extraction results to formatted JSON
  - **CSV:** Flatten extraction results to tabular format (key, value, confidence, source_region)
  - **Chat summary:** Concatenate chat messages into Markdown format
- **Output:** Downloadable file or clipboard content

---
#functional-requirements #features #engineering-spec #docmind-vlm
