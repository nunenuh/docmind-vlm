# User Journey Map: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Strategic Alignment

---

## Journey 1: "From Messy Scan to Trusted Data" (Compliance Officer — Sarah)

### 1. User Scenario
Sarah receives a scanned multilingual regulatory certificate (English + Bahasa Indonesia) from a Southeast Asian partner. She needs to extract the issuing authority, expiration date, and scope of certification before a quarterly audit deadline.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Discovery** | Sarah opens DocMind-VLM in browser | "Let's see if this handles scanned documents" | Login friction — needs to be fast (Google OAuth) |
| **Upload** | Drags the scanned PDF into the upload area | "Hope it handles the low quality" | Upload fails on large files or unsupported format |
| **Processing** | Sees a progress indicator while VLM + CV pipeline runs | "What's happening behind the scenes?" | Long wait time without feedback feels broken |
| **Extraction** | Sees structured fields with confidence scores and source regions highlighted on the document | "Okay, it found the expiration date — and I can see exactly where it read it from" | Fields extracted incorrectly but shown with high confidence (false positive) |
| **Audit** | Clicks a low-confidence field, sees the audit trail: source region, processing steps, quality metrics | "I can explain to the auditor exactly how this was extracted" | Audit trail is too technical / not readable |
| **Chat** | Types "Does this certificate cover marine equipment?" | "Let me ask about something that wasn't in the template fields" | Chat hallucinates an answer not grounded in the document |
| **Answer** | Receives an answer with a citation (page, region, exact text span) | "It shows me where it found the answer — I trust this" | Citation is wrong or points to wrong region |
| **Export** | Downloads structured JSON or copies the chat summary | "Done — this saved me 30 minutes per document" | Export format doesn't match her spreadsheet template |

### 3. Key Opportunities
- **Processing stage:** Show step-by-step pipeline progress (deskew → quality check → VLM extraction → post-processing) — this IS the moat, make it visible
- **Extraction stage:** Confidence overlay makes trust tangible — green/yellow/red heatmap on the document
- **Chat stage:** Every answer must cite its source region — no hallucinated answers without provenance
- **Export stage:** Offer JSON, CSV, and clipboard-ready formats

---

## Journey 2: "Quick Invoice Q&A" (Operations Analyst — James)

### 1. User Scenario
James receives a photo of a restaurant receipt from a colleague. The photo is tilted, partially cut off at the bottom, and contains mixed English/local language text. He needs the total, line items, and vendor name.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Upload** | Uploads the receipt photo | "This is a terrible photo — will it work?" | System rejects the image or silently fails |
| **Processing** | Sees pipeline: deskew detected → auto-corrected → quality: low (bottom truncated) → VLM extraction | "Oh, it caught the tilt AND warned about the cutoff" | Processing too slow for a quick task |
| **Extraction** | Sees line items, vendor, subtotal. Total field shows low confidence with note: "Bottom of receipt truncated" | "Smart — it didn't hallucinate a total, it told me it's unsure" | System guesses total anyway without flagging |
| **Chat** | Asks "Can you estimate the total from the visible line items?" | "Let's see if it can do the math" | Calculation error |
| **Answer** | Gets computed total with explicit caveat: "Estimated from visible items. Tax/tip may be missing." | "Perfect — I'll note this as estimated in my report" | No caveat, presented as fact |

### 3. Key Opportunities
- **Processing stage:** The classical CV preprocessing (deskew, quality detection) is visible and earns trust BEFORE VLM even runs
- **Extraction stage:** Honest uncertainty > confident wrong answer. Flag truncated/degraded regions explicitly.
- **Chat stage:** Math/reasoning over extracted data is a natural follow-up — LangGraph supports multi-step reasoning

---

## Journey 3: "5-Minute Evaluation" (Hiring Manager — David)

### 1. User Scenario
David is evaluating Erfan's portfolio. He opens the GitHub repo, reads the README, and decides whether to schedule an interview.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Discovery** | Clicks pinned repo "docmind-vlm" on GitHub | "Another VLM project... let's see" | README is a wall of text with no architecture diagram |
| **README** | Sees: architecture diagram, live demo link, "Quick Start: docker compose up", tech stack, moat explanation | "This is well-organized. And there's a live demo?" | No demo, broken link, or "coming soon" |
| **Clone & Run** | Runs `docker compose up`, opens localhost | "It actually works in one command" | Docker build fails, missing env vars, port conflicts |
| **Demo** | Uploads a test invoice, sees extraction with confidence overlay | "Okay, the confidence heatmap is interesting" | Demo is slow, errors out, or looks like a Streamlit app |
| **Comparison** | Clicks "Compare with raw VLM" — sees side-by-side | "Oh. This person actually understands where VLMs fail on documents" | Comparison doesn't show meaningful difference |
| **Code Review** | Browses src/: clean architecture, tests, CI/CD, typed Python | "Production-quality code, not a hackathon project" | Messy code, no tests, no types |
| **Decision** | Schedules interview | "This candidate is a level above the others I've seen" | — |

### 3. Key Opportunities
- **README:** Must be the best README in his portfolio. Architecture diagram (Mermaid), live demo, one-command setup, explicit moat explanation.
- **Demo:** Must work flawlessly on first try. Pre-loaded example documents for instant demo.
- **Comparison view:** This is the "aha moment" — the feature that makes David realize this is not another wrapper project.

---
#user-journey #ux-design #customer-experience #docmind-vlm
