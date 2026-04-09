# DocMind-VLM — Product Vision

## One-Liner

**AI-powered document intelligence platform for Southeast Asian businesses transitioning from paper to digital.**

---

## Problem

Organizations in dealer finance, banking, insurance, government, and healthcare process thousands of paper documents daily — KTP, KK, invoices, contracts, medical reports. Human operators manually read and type each field into digital systems. This is:

- **Slow** — 3-5 minutes per document, 500+ documents per day
- **Error-prone** — typos, missed fields, inconsistent formatting
- **Expensive** — dedicated data entry teams
- **Unscalable** — more documents = more people

Existing OCR solutions fail on:
- Indonesian documents (mixed Bahasa + English, unique formats like KTP/KK)
- Low-quality scans (faded, skewed, stamped-over text)
- Complex layouts (tables, multi-column, handwritten notes)
- Context understanding ("Berlaku Hingga: SEUMUR HIDUP" is a date field with value "lifetime")

---

## Solution

DocMind-VLM uses Vision Language Models (VLM) to **see and understand** documents like a human would, but at machine speed. Two core capabilities:

### Mode 1: Document Extraction Engine
Upload any document → AI extracts structured data → validate → export

### Mode 2: Knowledge Base Chat
Upload multiple documents → AI indexes everything → ask questions in natural language → get cited answers

---

## Target Users

| Persona | Use Case | Pain Point |
|---------|----------|------------|
| **Dealer Finance Officer** | Process loan applications (KTP, KK, BPKB, slip gaji) | Manual data entry for 100+ applications/day |
| **Insurance Claims Agent** | Extract data from claims forms, medical reports, damage photos | Slow claims processing, missed details |
| **Legal Paralegal** | Review contracts, extract clauses, track obligations | Reading 50-page contracts manually |
| **Government Admin** | Digitize citizen documents, verify identities | Paper archives, no searchability |
| **HR Manager** | Process employee documents, onboarding paperwork | Manual form filling from CVs and certificates |
| **New Employee** | Learn company procedures from SOP documents | Information scattered across 20 PDFs |

---

## Core Capabilities

### 1. Document Extraction

```
Upload → Classify → Extract → Validate → Export
```

| Feature | Description | Priority |
|---------|-------------|----------|
| **Auto-Classification** | Drop mixed documents, system identifies each type | P0 |
| **Template Extraction** | Pre-built templates for Indonesian documents (KTP, KK, Invoice, etc.) | P0 |
| **General Extraction** | Extract from any document without a template | P0 |
| **Confidence Scoring** | Color-coded confidence per field (green/yellow/red) | P0 |
| **Bounding Box Overlay** | Click extracted field → highlight on document image | P0 |
| **Field Editing** | Correct extracted fields inline | P1 |
| **Export** | Download as JSON, CSV, Excel, or push to API | P1 |
| **Batch Processing** | Upload 50-500 documents, process queue in background | P1 |
| **Validation Rules** | NIK format (16 digits), date format, cross-field consistency | P1 |
| **Cross-Document Validation** | KTP name matches KK name? Flag mismatches | P2 |
| **Document Comparison** | Upload old + new version → highlight changes | P2 |
| **Fraud Detection** | Flag suspicious patterns (font inconsistency, copy artifacts) | P3 |
| **Auto-Fill Forms** | Extract → auto-fill a digital form or PDF | P3 |

#### Indonesian Document Templates

| Document | Indonesian Name | Key Fields |
|----------|----------------|------------|
| National ID | KTP (Kartu Tanda Penduduk) | NIK, Nama, Tempat/Tgl Lahir, Alamat, RT/RW, Kel/Desa, Kecamatan, Agama, Status, Pekerjaan, Kewarganegaraan, Berlaku Hingga |
| Family Card | KK (Kartu Keluarga) | No. KK, Kepala Keluarga, Alamat, all family members with NIK |
| Driver License | SIM | Nama, No. SIM, Tempat/Tgl Lahir, Golongan, Berlaku Hingga |
| Vehicle Registration | STNK | No. Polisi, Nama Pemilik, Merk/Type, Tahun, No. Rangka, No. Mesin |
| Vehicle Ownership | BPKB | No. BPKB, No. Polisi, Nama Pemilik, No. Rangka, No. Mesin |
| Tax ID | NPWP | NPWP Number, Nama, Alamat, KPP |
| Tax Invoice | Faktur Pajak | No. Faktur, NPWP Penjual/Pembeli, DPP, PPN, Total |
| Birth Certificate | Akta Lahir | No. Akta, Nama, Tempat/Tgl Lahir, Nama Ayah, Nama Ibu |
| Power of Attorney | Surat Kuasa | Pemberi Kuasa, Penerima Kuasa, Perihal, Tanggal |
| Handover Letter | BAST (Berita Acara Serah Terima) | Pihak 1, Pihak 2, Objek, Tanggal, Kondisi |
| Receipt | Kuitansi | Dari, Untuk, Jumlah, Tanggal, Tanda Tangan |
| Invoice | Invoice/Tagihan | No. Invoice, Tanggal, Vendor, Items, Total, PPN |
| Purchase Order | PO | No. PO, Tanggal, Vendor, Items, Total |
| Delivery Order | Surat Jalan | No. SJ, Tanggal, Pengirim, Penerima, Items |
| Salary Slip | Slip Gaji | Nama, Periode, Gaji Pokok, Tunjangan, Potongan, Gaji Bersih |
| Medical Report | Surat Keterangan Sehat | Nama Pasien, Dokter, Tanggal, Hasil Pemeriksaan |
| Employment Letter | Surat Keterangan Kerja | Nama, Jabatan, Perusahaan, Sejak Tanggal |

### 2. Knowledge Base Chat

```
Create Project → Upload Docs → Index (RAG) → Chat with Persona → Cite Sources
```

| Feature | Description | Priority |
|---------|-------------|----------|
| **Multi-Document RAG** | Upload PDFs/images → chunk → embed → pgvector retrieval | P0 |
| **Persona-Based Chat** | Configure AI personality, tone, rules, boundaries | P0 |
| **Streaming + Thinking** | See AI reasoning process before final answer | P0 |
| **Source Citations** | Click [Source 1] → see exact document + page | P0 |
| **Conversation History** | Multiple conversations per project, searchable | P0 |
| **Document Status** | See which documents are indexed, pending, or failed | P1 |
| **Chunk Browser** | View/edit RAG chunks per document | P1 |
| **Preset Personas** | Customer Service, Technical Expert, Legal Advisor, Teacher, Onboarding Guide | P1 |
| **Custom Personas** | User creates their own persona with custom instructions | P1 |
| **Query Rewriting** | Follow-up questions auto-resolved ("his education?" → full query) | P1 |
| **Hybrid Search** | Vector similarity + keyword matching (RRF fusion) | P1 |
| **Answer Feedback** | Thumbs up/down on answers | P2 |
| **Smart Suggestions** | After answer, suggest related questions | P2 |
| **Document Summarization** | One-click summary of any document | P2 |
| **FAQ Generation** | Auto-generate FAQ from document content | P3 |
| **Multi-Language** | Ask in Bahasa, answer in Bahasa (or English, or mixed) | P1 |
| **Shared Projects** | Team members access same knowledge base | P3 |

### 3. Platform / Cross-Cutting

| Feature | Description | Priority |
|---------|-------------|----------|
| **Command Palette** | Cmd+K to search documents, projects, conversations, settings | P1 |
| **Toast Notifications** | "Upload complete", "Processing finished", "Document indexed" | P1 |
| **Loading Skeletons** | Proper loading states for all pages | P1 |
| **Activity Feed** | Recent actions: uploads, processing, conversations | P2 |
| **Analytics Dashboard** | Pages processed, API usage, storage, cost tracking | P2 |
| **API/SDK** | `POST /api/extract` → get JSON back (developer-facing) | P2 |
| **Webhook Events** | Push notifications to external systems | P3 |
| **Keyboard Shortcuts** | Navigate without mouse | P2 |
| **Onboarding Tour** | First-time user walkthrough | P2 |
| **Mobile Responsive** | Works on tablet/phone for field workers | P2 |
| **Dark/Light Theme** | User preference | P3 |
| **Multi-Language UI** | Interface in Bahasa Indonesia + English | P2 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                       │
│  Landing │ Dashboard │ Workspace │ Projects │ Settings   │
└─────────────────────────┬───────────────────────────────┘
                          │ REST + SSE
┌─────────────────────────▼───────────────────────────────┐
│                    Backend (FastAPI)                      │
│  Handler → UseCase → Service → Repository                │
├──────────────┬──────────────┬───────────────────────────┤
│  Extraction  │  RAG Chat    │  Platform                  │
│  Pipeline    │  Pipeline    │  Services                  │
│  (LangGraph) │  (LangGraph) │                           │
├──────────────┼──────────────┼───────────────────────────┤
│  VLM Providers             │  Embedding Providers        │
│  (DashScope, OpenAI,       │  (DashScope, OpenAI)       │
│   Google, Ollama)          │                             │
├────────────────────────────┼───────────────────────────┤
│  PostgreSQL (Supabase)     │  Supabase Auth + Storage   │
│  + pgvector                │                             │
└────────────────────────────┴───────────────────────────┘
```

---

## Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui | Fast, modern, great DX |
| Backend | FastAPI + Python 3.11 + LangGraph | Async, type-safe, pipeline orchestration |
| Database | Supabase Postgres + pgvector | Managed, vector search, auth included |
| Auth | Supabase Auth (Google/GitHub OAuth + email) | Zero-config, JWT tokens |
| Storage | Supabase Storage | S3-compatible, integrated with auth |
| VLM | DashScope Qwen-VL (primary), OpenAI GPT-4V, Google Gemini | Multi-provider flexibility |
| Embedding | DashScope text-embedding-v4 | 1024-dim, multi-language |
| CV | OpenCV + PyMuPDF + pymupdf4llm | Preprocessing, text extraction |
| Cache | Redis (optional) | Session cache, rate limiting |
| Infra | Docker Compose (local), Vercel + Supabase (prod) | Simple deployment |

---

## Document Processing Pipeline

```
Upload → Preprocess (CV) → Classify → Extract (VLM) → Validate → Postprocess → Store
                                                          │
                                                    Confidence Merge
                                                   (VLM 70% + CV 30%)
```

## RAG Chat Pipeline

```
User Message → Rewrite Query (if follow-up)
            → Embed Query
            → Hybrid Retrieve (Vector + BM25, RRF Fusion)
            → Diversify Results (spread across documents)
            → Build Prompt (Persona + Context + Citations)
            → Stream Response (Thinking + Answer)
            → Save to Conversation History
```

---

## Competitive Landscape

| Competitor | Strength | DocMind Advantage |
|------------|----------|-------------------|
| ABBYY | Enterprise OCR, mature | VLM-based (better for complex layouts), Indonesian doc support |
| Tesseract | Free, open-source | VLM understands context, not just characters |
| Google Document AI | Cloud, scalable | On-premise option, Indonesian templates, RAG chat |
| ChatPDF / ChatDOC | Chat with PDFs | Structured extraction + chat, persona system, multi-doc projects |
| Nanonets | Template-based extraction | VLM flexibility, no training needed, RAG knowledge base |

---

## Success Metrics (Portfolio Demo)

| Metric | Target |
|--------|--------|
| Document types supported | 10+ Indonesian templates |
| Extraction accuracy | >90% on clean documents |
| Processing time | <10 seconds per page |
| RAG answer relevance | Correct citations in >80% of answers |
| UI responsiveness | <200ms for all interactions |
| Test coverage | >80% backend, basic frontend tests |
| Uptime | Works reliably on local + cloud Supabase |

---

## Phased Rollout

### Phase 1: Core (Current)
- Single document extraction with VLM
- Knowledge base chat with RAG + personas
- Basic dashboard and workspace

### Phase 2: Indonesian Documents
- 10+ Indonesian document templates
- Auto-classification
- Batch upload queue
- Export (JSON/CSV/Excel)
- Chunk browser for RAG transparency

### Phase 3: Production Polish
- Command palette, toast notifications, loading skeletons
- Analytics dashboard
- Proper settings page
- Mobile responsive
- Onboarding tour

### Phase 4: Advanced Features
- Cross-document validation
- Document comparison
- API/SDK for developers
- Webhook integrations
- Team workspaces

### Phase 5: Enterprise
- SSO, RBAC, audit logs
- White-label option
- Data residency
- Custom deployment
