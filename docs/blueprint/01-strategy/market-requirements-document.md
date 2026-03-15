# Market Requirements Document (MRD): DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Market Analysis

---

## 1. Target Market Segment

- **Primary:** International hiring managers and technical leads evaluating senior AI/ML candidates for Document AI, Computer Vision, or full-stack ML roles ($130K-$312K range).
- **Secondary:** Enterprises and teams exploring open-source IDP alternatives to proprietary APIs (AWS Textract, Azure Form Recognizer, Google Document AI).
- **Tertiary:** ML engineers and developers looking for reference architectures combining VLMs with classical CV for document processing.

## 2. Market Needs & Trends

**Intelligent Document Processing (IDP):**
- Market size: $4.1-14B (2026) → $44-91B by 2034, 30-40% CAGR
- 75% of AI job listings seek domain specialists — specialization beats generalism
- Enterprise demand for transparent, explainable extraction is growing as regulatory requirements tighten

**Vision-Language Models (VLMs):**
- Multimodal AI is the next wave after LLMs
- Qwen3-VL, GPT-4V, Gemini Pro Vision are rapidly improving on document understanding benchmarks
- Most practitioners use VLMs as black-box API calls without understanding failure modes

**The "Context Gap":**
- VLMs are powerful but hallucinate on complex document layouts (nested tables, multi-column, degraded scans)
- No open-source tool combines classical CV preprocessing with VLM inference AND provides transparency into the extraction process
- Hiring managers see hundreds of "I wrapped GPT-4V in a Streamlit app" projects — zero differentiation

## 3. Competitive Landscape

| Competitor | Strengths | Weaknesses | DocMind-VLM Advantage |
|---|---|---|---|
| **AWS Textract** | Enterprise-grade, scalable, well-documented | Proprietary, expensive, black-box, no chat interface | Open-source, transparent extraction with audit trail, conversational Q&A |
| **Azure Form Recognizer** | Strong on forms/invoices, pre-built models | Vendor lock-in, limited layout understanding on complex docs | Classical CV preprocessing catches what Azure misses, confidence overlay shows where |
| **Google Document AI** | Good multilingual support, GCP integration | Expensive at scale, no conversational interaction | Chat interface + template-driven extraction + schema-free mode |
| **LlamaParse / Unstructured.io** | Open-source, good PDF parsing | Text extraction focus, no VLM vision understanding, no UI | Full vision understanding (not just text), polished web UI, extraction audit trail |
| **Typical GitHub VLM wrappers** | Quick demos, many stars | Streamlit/Gradio UI, no architecture, no tests, no ops | Production-grade architecture: FastAPI + React + Docker Compose + CI/CD + 80%+ test coverage |

## 4. SWOT Analysis

**Strengths:**
- 7+ years production OCR/CV experience (UNet, CRNN, LayoutLM, Siamese networks)
- Classical CV + modern VLM = knows when extraction is wrong
- Full-stack capability: backend + ML + infra + frontend (learning)
- Async architecture patterns from TabLogs PDFGen epic

**Weaknesses:**
- Solo developer — limited bandwidth
- Frontend (React/TypeScript) is a learning area, not a strength yet
- No existing open-source community/following

**Opportunities:**
- IDP market growing 30-40% CAGR — hiring demand is accelerating
- Open-source Document AI with transparency is an unoccupied niche
- Portfolio project can become a real tool others adopt
- React/TypeScript learning is embedded in a real project (not tutorials)

**Threats:**
- Qwen/OpenAI could ship native document chat features that commoditize the demo
- Other ML engineers with similar backgrounds could build competing showcases
- DashScope API pricing or availability could change

## 5. Unique Value Proposition (UVP)

DocMind-VLM is the only open-source document AI tool that combines vision-language model extraction with classical computer vision expertise to show you not just WHAT was extracted, but HOW confident the system is and WHERE it might be wrong — then lets you have a conversation about it.

---
#mrd #market #analysis #docmind-vlm
