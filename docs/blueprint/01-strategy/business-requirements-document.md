# Business Requirements Document (BRD): DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Strategic Alignment

---

## 1. Executive Summary

DocMind-VLM is a portfolio-grade open-source web application that demonstrates end-to-end document AI capabilities: from document upload, through VLM-powered extraction and classical CV preprocessing, to conversational interaction. The project exists to position Erfan as a senior-level Document AI specialist for the international job market, proving a rare skill combination that most ML engineers cannot replicate.

## 2. Business Problem & Opportunity

**Problem:** Erfan's current GitHub profile (186 repos) does not reflect his senior-level capabilities. The international market pays $130K-$312K for senior AI/ML specialists, but hiring managers evaluate candidates by their visible portfolio. There is no public artifact demonstrating his deepest domain expertise: 7+ years of production OCR/CV combined with modern VLM understanding.

**Opportunity:** The Intelligent Document Processing (IDP) market is growing from $4.1-14B (2026) to $44-91B by 2034 at 30-40% CAGR. Document AI is a universal enterprise pain point. A polished, full-stack Document AI application with transparent, explainable extraction directly addresses the highest-demand intersection in the AI job market.

**What happens if we don't build it:** Erfan's portfolio tells a fragmented story. Hiring managers see old repos, can't evaluate depth, and default to candidates with visible, polished projects. The unique moat (classical CV + modern VLM) remains invisible.

## 3. Business Objectives

- [ ] **Objective 1:** Establish a Tier 1 portfolio project that demonstrates full-stack + ML depth to international hiring managers within Q2 2026.
- [ ] **Objective 2:** Create a live, demo-ready application that can be shown in interviews and linked from nunenuh.me, LinkedIn, and GitHub pinned repos.
- [ ] **Objective 3:** Produce a codebase that showcases architectural maturity: clean code, test coverage, CI/CD, Docker Compose one-command setup, comprehensive documentation.
- [ ] **Objective 4:** Build a reusable Document AI foundation that can be extended for future freelance/consulting opportunities in the IDP market.

## 4. Success Metrics (KPIs)

| Metric | Target | How Measured |
|---|---|---|
| Demo load time | < 3 seconds to first extraction result display | Manual + Lighthouse |
| Extraction accuracy on demo documents | > 90% field-level accuracy | Pre-scored benchmark set |
| Code test coverage | > 80% | pytest + coverage report |
| One-command setup | `docker compose up` works on fresh clone | CI verification |
| README quality | Architecture diagram, live demo link/video, clear setup instructions | Self-review against Tier 1 standard |
| Time to live demo | < 8 weeks from start | Calendar tracking |

## 5. Scope & Constraints

**In-Scope:**
- Single document upload and processing (PDF, image, scan)
- Structured extraction (general + template-driven modes)
- Chat interface for conversational document Q&A
- Extraction audit trail, confidence overlay, pipeline comparison view
- User authentication (Google/GitHub OAuth via Supabase)
- Docker Compose deployment for local demo

**Out-of-Scope:**
- Multi-document workspace (Phase 2 — architecture supports it, MVP does not)
- VLM fine-tuning (all differentiation is code/architecture)
- Commercial deployment or SaaS infrastructure
- Mobile application (separate Repo 7 in portfolio strategy)
- Any TabLogs/NDA code — entirely fresh build using public domain document types

**Constraints:**
- Budget: Minimal — DashScope API (cheap for demo), Supabase free tier, no GPU infra
- Timeline: MVP within Q2 2026
- Solo developer: Erfan only
- Must be fully open-source (MIT or Apache 2.0)

---
#brd #business #strategy #docmind-vlm
