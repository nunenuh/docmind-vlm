# User Persona Definition: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-20 (revised)
**Status:** Strategic Alignment — Updated for Knowledge Base + Persona features

---

## Persona 1 (Primary): The Knowledge Base Builder

**Name:** Maya
**Role:** Customer Success Manager at a SaaS company
**Environment:** Chrome browser, manages product docs, FAQs, and onboarding guides

### Psychographics & Characteristics
- **Key Habit 1:** Answers the same customer questions repeatedly — wishes she could hand off to an AI trained on their docs
- **Key Habit 2:** Maintains 20+ PDF guides, policy documents, and FAQ sheets that change quarterly
- **Motivations:** Wants to create an AI assistant that knows their product inside-out, answers like a friendly support agent, and always cites which document the answer came from
- **Frustrations:**
  - Generic chatbots hallucinate or give wrong answers because they aren't grounded in real docs
  - Manually searching through 20 PDFs to find the right answer takes too long
  - Can't control the AI's tone — sometimes too formal, sometimes too casual for their brand
  - When docs update, the AI doesn't know about the changes

### Goals & Tasks
1. Create a project, upload all product documentation (PDFs, guides, FAQs)
2. Configure a "Customer Service Agent" persona — friendly, step-by-step, always cites sources
3. Ask questions and get accurate answers grounded in the uploaded docs with page citations
4. Update docs and have the AI's knowledge refresh automatically

### "A Day in the Life"
Maya creates a project called "Product Support KB" and uploads 15 PDF guides covering their product. She selects the "Customer Service Agent" persona and tweaks the rules: "Always suggest the next step", "If unsure, say so and recommend contacting support." She tests by asking "How do I reset my password?" — the AI responds with step-by-step instructions citing the User Guide page 23. She shares the project with her team. When a new product version ships, she replaces the outdated PDFs and the knowledge base updates automatically.

---

## Persona 2 (Secondary): The Compliance Officer

**Name:** Sarah
**Role:** Regulatory Compliance Analyst at a multinational firm
**Environment:** Windows laptop, Chrome browser, receives documents via email and shared drives

### Psychographics & Characteristics
- **Key Habit 1:** Reads 20-50 regulatory documents per week in multiple languages (English, Mandarin, Arabic, Bahasa)
- **Key Habit 2:** Manually searches PDFs with Ctrl+F and highlights sections — slow, error-prone on scanned documents
- **Motivations:** Needs to extract specific clauses, dates, obligations, and penalties from contracts AND chat across a corpus of regulations
- **Frustrations:**
  - Scanned documents are not searchable — Ctrl+F doesn't work
  - Existing OCR tools return garbled text on complex table layouts
  - No way to cross-reference across multiple regulatory documents at once
  - Expensive proprietary tools are black boxes — she can't explain to auditors HOW a data point was extracted

### Goals & Tasks
1. **Extract mode:** Upload a scanned contract and extract all penalty clauses with monetary values, confidence scores, and source regions
2. **Knowledge Base mode:** Create a project with all regulatory documents, set "Legal Advisor" persona, and ask "Which documents mention data retention requirements?"
3. Trust the output — see WHERE each data point came from and HOW confident the system is

### "A Day in the Life"
Sarah has two workflows. For individual documents (certificates, invoices), she uses the **extraction workspace** — uploads a scanned certificate, sees extracted fields with confidence overlays, and verifies them. For cross-document research, she uses a **Knowledge Base project** — she's uploaded 30+ regulatory documents with the "Legal Advisor" persona. She asks "What are the GDPR penalties for data breaches?" and gets a precise answer citing three different regulation documents with page numbers.

---

## Persona 3 (Secondary): The Operations Analyst

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
James uses the **extraction workspace** for daily invoice processing — upload, extract, verify, done. For month-end reporting, he creates a **Knowledge Base project** with all vendor contracts and asks "Which vendors have payment terms over 60 days?" The AI searches across all contracts and gives him a list with citations.

---

## Persona 4 (Meta): The Hiring Manager

**Name:** David
**Role:** Engineering Director at an AI-first company, evaluating senior ML candidates
**Environment:** GitHub, LinkedIn, candidate portfolio websites

### Psychographics & Characteristics
- **Key Habit 1:** Spends 5-10 minutes per candidate reviewing GitHub repos before deciding on an interview
- **Key Habit 2:** Looks for: architecture quality, test coverage, documentation, live demo, evidence of production thinking
- **Motivations:** Needs to distinguish "API callers" from engineers with genuine ML/AI depth
- **Frustrations:**
  - 90% of ML portfolios are Jupyter notebooks or Streamlit wrappers
  - Hard to tell if a candidate can actually deploy and operate AI systems
  - No visibility into how candidates think about RAG, multi-modal AI, and system design

### Goals & Tasks
1. Clone the repo, run `docker compose up`, and see a working application in < 5 minutes
2. Read the README and understand the architecture, tech choices, and why they were made
3. See evidence of production thinking: RAG pipeline, VLM integration, persona system, CI/CD, tests, audit trail

### "A Day in the Life"
David is hiring a Senior AI Engineer for his Document AI team. He opens Erfan's GitHub, sees docmind-vlm pinned. The README shows a dual-mode platform: structured document extraction with confidence overlays AND a RAG-powered Knowledge Base with configurable AI personas. He runs the demo, creates a project, uploads some docs, configures a persona, and chats with grounded answers citing specific pages. He thinks: "This person understands RAG, VLM, prompt engineering, and full-stack at a level I rarely see." He schedules an interview.

---

## Persona Summary

| Persona | Primary Use | Mode |
|---------|------------|------|
| Maya (Customer Success) | Build AI knowledge bases from docs | Knowledge Base + Persona |
| Sarah (Compliance) | Extract fields + cross-doc research | Both modes |
| James (Finance) | Extract invoice data + vendor queries | Extraction + KB for research |
| David (Hiring Manager) | Evaluate portfolio | Demo experience |

## Two Product Modes

| Mode | For Whom | What It Does |
|------|----------|-------------|
| **Document Extraction** | Sarah, James | Upload single doc → VLM extracts structured fields → confidence overlays → per-doc chat |
| **Knowledge Base** | Maya, Sarah, James | Create project → upload many docs → RAG indexes everything → persona-aware chat across all docs |

---
#persona #user-centric #design #docmind-vlm #rag #knowledge-base
