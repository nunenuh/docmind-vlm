# User Persona Definition: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Strategic Alignment

---

## Persona 1 (Primary): The Compliance Officer

**Name:** Sarah
**Role:** Regulatory Compliance Analyst at a multinational firm
**Environment:** Windows laptop, Chrome browser, receives documents via email and shared drives

### Psychographics & Characteristics
- **Key Habit 1:** Reads 20-50 regulatory documents per week in multiple languages (English, Mandarin, Arabic, Bahasa)
- **Key Habit 2:** Manually searches PDFs with Ctrl+F and highlights sections — slow, error-prone on scanned documents
- **Motivations:** Needs to extract specific clauses, dates, obligations, and penalties from contracts and regulatory filings quickly and accurately
- **Frustrations:**
  - Scanned documents are not searchable — Ctrl+F doesn't work
  - Existing OCR tools return garbled text on complex table layouts
  - No way to know if the extraction is wrong until a human catches it downstream
  - Expensive proprietary tools (Textract, Azure) are black boxes — she can't explain to auditors HOW a data point was extracted

### Goals & Tasks
1. Upload a scanned multilingual contract and extract all penalty clauses with their monetary values
2. Ask follow-up questions: "Does this contract auto-renew?", "What's the governing jurisdiction?"
3. Trust the extraction — see WHERE each data point came from in the original document and HOW confident the system is

### "A Day in the Life"
Sarah receives a batch of scanned regulatory certificates from a Southeast Asian partner — half in English, half in Bahasa Indonesia. She needs to verify that all certificates contain specific compliance fields (issuing authority, expiration date, scope of certification) before a quarterly audit deadline. Currently she manually opens each PDF, squints at low-quality scans, and types values into a spreadsheet. With DocMind-VLM, she uploads the document, sees extracted fields with confidence scores and source regions highlighted, and asks "Is there an expiration date in this document?" when a field is missing or uncertain.

---

## Persona 2 (Secondary): The Operations Analyst

**Name:** James
**Role:** Finance Operations Analyst at a mid-size company
**Environment:** MacBook, Chrome browser, processes vendor invoices and expense receipts

### Psychographics & Characteristics
- **Key Habit 1:** Processes 50-100 invoices per month from different vendors — all different formats
- **Key Habit 2:** Copies line items into Excel manually, frequently makes transcription errors
- **Motivations:** Wants structured data (vendor, date, line items, totals, tax) extracted automatically from any invoice format
- **Frustrations:**
  - Every vendor sends invoices in a different layout — no single template works
  - Photo receipts from field staff are blurry, tilted, or partially cut off
  - Current tools either fail silently or require expensive per-page pricing

### Goals & Tasks
1. Upload an invoice (PDF or photo) and get structured JSON output of all fields
2. Ask "What's the total including tax?" when the invoice layout is ambiguous
3. See which fields were extracted with high vs low confidence before trusting the output

### "A Day in the Life"
James receives a photo of a restaurant receipt from a colleague's expense claim. The photo is slightly tilted, the bottom is cut off, and the receipt is in a mix of English and local language. He uploads it to DocMind-VLM, gets the extracted line items and total with confidence scores, notices the total has a low confidence flag (bottom was cut off), and asks the chat "Can you estimate the total from the visible line items?" The system gives a computed answer with an explicit caveat about the missing region.

---

## Persona 3 (Meta): The Hiring Manager

**Name:** David
**Role:** Engineering Director at an AI-first company, evaluating senior ML candidates
**Environment:** GitHub, LinkedIn, candidate portfolio websites

### Psychographics & Characteristics
- **Key Habit 1:** Spends 5-10 minutes per candidate reviewing GitHub repos before deciding on an interview
- **Key Habit 2:** Looks for: architecture quality, test coverage, documentation, live demo, evidence of production thinking
- **Motivations:** Needs to distinguish "API callers" from engineers with genuine ML depth
- **Frustrations:**
  - 90% of ML portfolios are Jupyter notebooks or Streamlit wrappers
  - Hard to tell if a candidate can actually deploy and operate ML systems
  - No visibility into how candidates think about failure modes and reliability

### Goals & Tasks
1. Clone the repo, run `docker compose up`, and see a working application in < 5 minutes
2. Read the README and understand the architecture, tech choices, and why they were made
3. See evidence of production thinking: CI/CD, tests, monitoring, error handling, audit trail

### "A Day in the Life"
David is hiring a Senior ML Engineer for his Document AI team. He opens Erfan's GitHub, sees docmind-vlm pinned. The README has an architecture diagram, a live demo link, and a "Quick Start" with Docker Compose. He clones it, runs it, uploads a test document, and sees structured extraction with confidence overlays. He clicks "Compare with raw VLM" and sees the side-by-side. He thinks: "This person understands document AI at a level I rarely see in candidates." He schedules an interview.

---
#persona #user-centric #design #docmind-vlm
