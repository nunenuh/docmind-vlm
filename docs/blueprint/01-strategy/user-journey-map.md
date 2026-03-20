# User Journey Map: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-20 (revised)
**Status:** Strategic Alignment — Updated for Knowledge Base + Persona features

---

## Journey 1: "Build a Knowledge Base from Documents" (Customer Success — Maya)

### 1. User Scenario
Maya manages 15+ product documentation PDFs for her SaaS company. She wants to create an AI assistant that her team can query about product features, troubleshooting steps, and policies — grounded in actual docs, not hallucinations.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Login** | Opens DocMind-VLM, signs in with Google | "Simple, quick login" | OAuth redirect loop or session expiry |
| **Create Project** | Clicks "New Project", names it "Product Support KB" | "Like creating a project in Claude or ChatGPT" | Unclear what a project is vs a single doc upload |
| **Upload Docs** | Drags 15 PDFs into the project upload area | "Let me load everything in one go" | Upload fails on large files, unclear progress |
| **Indexing** | Sees progress: "Indexing 15 documents... 847 chunks created" | "Good, it's processing all my docs" | Indexing takes too long without feedback |
| **Choose Persona** | Selects "Customer Service Agent" from presets, tweaks rules | "I want it to be friendly and always cite which doc" | Persona options are confusing or too technical |
| **First Chat** | Asks "How do I reset my password?" | "Let's see if it actually read the docs" | AI hallucinates, doesn't cite sources |
| **Answer** | Gets step-by-step answer citing "User Guide, page 23" | "It found the exact page — I trust this" | Citation is wrong or missing |
| **Iterate** | Asks follow-up: "What if I forgot my email too?" | "Can it handle context from the previous answer?" | Loses conversation context |
| **Share** | Shares project link with team | "Now everyone can use this" | No sharing functionality (future feature) |

### 3. Key Opportunities
- **Indexing stage:** Show chunk count and per-doc progress — makes the RAG pipeline visible
- **Persona stage:** Preset templates with one-click customization lower the barrier
- **Chat stage:** Every answer MUST cite document name + page number — this is the trust mechanism
- **Multi-turn:** Conversation history should persist across sessions

---

## Journey 2: "From Messy Scan to Trusted Data" (Compliance Officer — Sarah)

### 1. User Scenario
Sarah receives a scanned multilingual regulatory certificate. She needs to extract the issuing authority, expiration date, and scope of certification before a quarterly audit deadline.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Dashboard** | Opens DocMind-VLM, sees two paths: "Extract Documents" and "Knowledge Projects" | "I need the extraction mode today" | Confusing navigation between modes |
| **Upload** | Drags the scanned PDF into the extraction upload area | "Hope it handles the low quality" | Upload fails on large files |
| **Processing** | Sees pipeline progress: deskew → quality check → VLM extraction → postprocess | "I can see what's happening step by step" | Long wait without feedback |
| **Extraction** | Sees structured fields with confidence scores and source regions highlighted | "It found the expiration date — I can see exactly where" | False positive high-confidence on wrong field |
| **Audit** | Clicks a low-confidence field, sees the audit trail | "I can explain to the auditor how this was extracted" | Audit trail too technical |
| **Chat** | Types "Does this certificate cover marine equipment?" | "Let me ask about something not in the template" | Chat hallucinates |
| **Answer** | Receives answer with citation (page, region, exact text span) | "It shows me where it found the answer" | Citation points to wrong region |

### 3. Key Opportunities
- **Dashboard:** Clear separation between Extraction mode (single doc, structured output) and KB mode (multi-doc, RAG chat)
- **Pipeline visibility:** The CV preprocessing steps ARE the moat — make them visible
- **Confidence overlay:** Green/yellow/red heatmap makes trust tangible

---

## Journey 3: "Cross-Document Research" (Compliance Officer — Sarah, KB mode)

### 1. User Scenario
Sarah has 30+ regulatory documents from various jurisdictions. She needs to find which documents mention data retention requirements and compare the clauses.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Create Project** | Creates "Regulatory Corpus 2026" project, uploads 30 PDFs | "One place for all my regulations" | Slow upload/indexing for many docs |
| **Persona** | Selects "Legal Advisor" preset | "I want formal, precise answers with clause citations" | Can't customize enough |
| **Query** | Asks "Which documents mention data retention requirements?" | "Let's see if it can search across everything" | Returns irrelevant results |
| **Results** | Gets a summary citing 5 documents with specific sections | "Perfect — it cross-referenced all 30 docs" | Missing a document that should have matched |
| **Follow-up** | Asks "Compare the retention periods across these 5 documents" | "Can it synthesize across sources?" | Can't handle multi-doc comparison |
| **Export** | Copies the comparison table | "This would've taken me 3 hours manually" | No export functionality |

### 3. Key Opportunities
- **Multi-doc retrieval:** RAG across all project documents is the key differentiator
- **Legal persona:** Formal tone, clause citations, risk flagging
- **Comparison queries:** The ability to compare across documents is a power feature

---

## Journey 4: "Quick Invoice Q&A" (Operations Analyst — James)

### 1. User Scenario
James receives a photo of a restaurant receipt. The photo is tilted, partially cut off, and mixed language. He needs the total, line items, and vendor name.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Upload** | Uploads the receipt photo to extraction mode | "This is a terrible photo — will it work?" | System rejects or silently fails |
| **Processing** | Sees: deskew detected → auto-corrected → quality: low (truncated) | "It caught the tilt AND warned about the cutoff" | Processing too slow |
| **Extraction** | Sees line items, vendor, subtotal. Total shows low confidence: "Bottom truncated" | "Smart — it didn't hallucinate a total" | Guesses total without flagging |
| **Chat** | Asks "Estimate total from visible line items?" | "Let's see if it can do the math" | Calculation error |
| **Answer** | Gets computed total with caveat: "Estimated. Tax/tip may be missing." | "Perfect — I'll note as estimated" | No caveat, presented as fact |

---

## Journey 5: "5-Minute Portfolio Evaluation" (Hiring Manager — David)

### 1. User Scenario
David is evaluating Erfan's portfolio. He opens the GitHub repo and decides whether to schedule an interview.

### 2. Journey Stages

| Stage | Action | Thought/Feeling | Potential Pain Point |
|---|---|---|---|
| **Discovery** | Clicks pinned repo "docmind-vlm" on GitHub | "Another AI project... let's see" | README is a wall of text |
| **README** | Sees: architecture diagram, dual-mode (Extraction + Knowledge Base), tech stack | "This isn't just a wrapper — it has RAG, personas, VLM" | No demo, broken link |
| **Clone & Run** | Runs `docker compose up`, opens localhost | "It actually works in one command" | Build fails, missing env vars |
| **Demo: Extraction** | Uploads test invoice, sees extraction with confidence overlay | "The confidence heatmap is smart" | Demo errors out |
| **Demo: Knowledge Base** | Creates project, uploads docs, picks persona, chats | "RAG + configurable personas + VLM — this is impressive" | RAG returns irrelevant results |
| **Code Review** | Browses src/: clean architecture, pgvector, LangGraph, tests | "Production-quality, not a hackathon project" | Messy code, no tests |
| **Decision** | Schedules interview | "This candidate understands RAG, VLM, and system design at a senior level" | — |

### 3. Key Opportunities
- **README:** Must clearly show BOTH modes — extraction and knowledge base
- **Demo:** Pre-loaded example project with docs and persona for instant demo
- **Architecture:** The dual-pipeline design (VLM extraction + RAG knowledge base) is the "aha moment"

---
#user-journey #ux-design #docmind-vlm #rag #knowledge-base #persona
