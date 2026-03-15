# Acceptance Criteria Specification: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Product Definition

---

## Landing Page (US-0a, US-0b, US-0c, US-0d, US-0e)
- [ ] **AC 0.1:** Landing page loads in < 1.5 seconds on desktop (Lighthouse performance score > 90).
- [ ] **AC 0.2:** Hero section is visible without scrolling and communicates the core value proposition.
- [ ] **AC 0.3:** A live demo preview or auto-playing video is visible within the first scroll.
- [ ] **AC 0.4:** Four feature showcase sections are present: Extract, Understand, Compare, Chat — each with a visual.
- [ ] **AC 0.5:** "How it works" section shows the 3-4 step workflow with visual flow.
- [ ] **AC 0.6:** Tech stack badges (Qwen3-VL, LangGraph, FastAPI, React, Supabase) are visible.
- [ ] **AC 0.7:** At least two call-to-action buttons are present (hero + bottom) linking to sign-in.
- [ ] **AC 0.8:** Footer includes GitHub repo link and author website link.
- [ ] **AC 0.9:** Landing page is fully responsive (mobile, tablet, desktop).
- [ ] **AC 0.10:** Landing page is accessible without authentication — no redirect to login.

## Authentication (US-1, US-2, US-3)
- [ ] **AC 1.1:** User can log in via Google OAuth and is redirected to the dashboard after successful authentication.
- [ ] **AC 1.2:** User can log in via GitHub OAuth and is redirected to the dashboard after successful authentication.
- [ ] **AC 1.3:** Unauthenticated users accessing any protected route are redirected to the login page.
- [ ] **AC 1.4:** User A cannot see or access documents uploaded by User B (Supabase RLS enforced).
- [ ] **AC 1.5:** User session persists across browser restarts (JWT refresh token flow).

## Document Upload (US-4, US-5, US-6)
- [ ] **AC 2.1:** User can drag and drop a file onto the upload area and processing begins automatically.
- [ ] **AC 2.2:** User can click the upload area to open a file picker as a fallback.
- [ ] **AC 2.3:** Upload progress bar is visible and updates in real time.
- [ ] **AC 2.4:** Files exceeding 20MB are rejected with the message: "File too large. Maximum size is 20MB."
- [ ] **AC 2.5:** Files with unsupported formats are rejected with the message: "Unsupported format. Please upload PDF, PNG, JPG, JPEG, TIFF, or WebP."
- [ ] **AC 2.6:** Uploaded files are stored in Supabase Storage with a unique path per user.

## Document Processing (US-7, US-8)
- [ ] **AC 3.1:** Processing pipeline shows step-by-step progress to the user: "Analyzing image quality" → "Preprocessing" → "Extracting content" → "Post-processing".
- [ ] **AC 3.2:** Skewed images (> 2 degrees tilt) are automatically deskewed before VLM extraction.
- [ ] **AC 3.3:** Single-page document processing completes in < 10 seconds.
- [ ] **AC 3.4:** Processing failure displays a clear error message with the failed step identified.

## Extraction — General Mode (US-9, US-10)
- [ ] **AC 4.1:** Uploading a document without selecting a template triggers schema-free extraction.
- [ ] **AC 4.2:** Extracted output includes key-value pairs, tables, and entities as structured JSON.
- [ ] **AC 4.3:** Each extracted field includes: value, bounding box coordinates, confidence score (0.0–1.0).
- [ ] **AC 4.4:** Extracted JSON is displayed in the UI in a readable, collapsible format.

## Extraction — Template Mode (US-11, US-12, US-13)
- [ ] **AC 5.1:** User can select a document type from a dropdown: invoice, receipt, contract, certificate.
- [ ] **AC 5.2:** System auto-detects document type with > 80% accuracy on demo benchmark documents.
- [ ] **AC 5.3:** Template extraction validates required fields and flags any that are missing.
- [ ] **AC 5.4:** Missing required fields are displayed with a yellow warning indicator and message: "Field not found — verify document completeness."

## Audit Trail (US-14, US-15, US-16)
- [ ] **AC 6.1:** Clicking an extracted field highlights its source region on the document with a bounding box.
- [ ] **AC 6.2:** Each field displays a confidence score badge: green (> 0.8), yellow (0.5–0.8), red (< 0.5).
- [ ] **AC 6.3:** Audit detail panel shows: source region coordinates, preprocessing steps applied, VLM model version, extraction timestamp.

## Confidence Overlay (US-17, US-18)
- [ ] **AC 7.1:** User can toggle a confidence heatmap overlay on the document view.
- [ ] **AC 7.2:** Heatmap uses green (high) → yellow (medium) → red (low) color scale.
- [ ] **AC 7.3:** Low-confidence regions (< 0.5) display a tooltip with the reason (e.g., "Blur detected", "Low contrast", "Region truncated").

## Pipeline Comparison (US-19, US-20)
- [ ] **AC 8.1:** User can click "Compare with raw VLM" to see side-by-side extraction results.
- [ ] **AC 8.2:** Fields corrected by the enhanced pipeline are highlighted in blue.
- [ ] **AC 8.3:** Fields added by the enhanced pipeline (missed by raw VLM) are highlighted in green.
- [ ] **AC 8.4:** Comparison view loads from pre-computed baseline data in < 1 second.

## Document Chat (US-21, US-22, US-23, US-24)
- [ ] **AC 9.1:** Chat input is available after extraction completes.
- [ ] **AC 9.2:** Chat response includes a citation block: page number, bounding box region, and exact text span from the document.
- [ ] **AC 9.3:** Clicking a citation scrolls/highlights the referenced region in the document viewer.
- [ ] **AC 9.4:** Multi-turn conversation retains context from previous messages in the same session.
- [ ] **AC 9.5:** Chat response time is < 3 seconds.
- [ ] **AC 9.6:** Chat history is persisted and available when the user returns to the same document.

## Export (US-25, US-26)
- [ ] **AC 10.1:** User can download extracted data as JSON with one click.
- [ ] **AC 10.2:** User can download extracted data as CSV with one click.
- [ ] **AC 10.3:** User can copy chat summary to clipboard with a "Copy" button.

## Portfolio / Demo (US-27, US-28)
- [ ] **AC 11.1:** `docker compose up` starts the full application (backend + frontend + database) without manual configuration beyond `.env` file.
- [ ] **AC 11.2:** Application is accessible at `localhost` within 2 minutes of `docker compose up`.
- [ ] **AC 11.3:** At least 3 pre-loaded example documents are available on first launch (invoice, scanned certificate, multilingual contract).
- [ ] **AC 11.4:** Pre-loaded documents include pre-computed raw VLM baselines for comparison view.

---
#acceptance-criteria #quality-assurance #definition-of-done #docmind-vlm
