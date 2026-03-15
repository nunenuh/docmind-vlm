# Issue #34: Demo Data for Portfolio — Pre-loaded Documents + Baselines

## Summary

Create demo data for the portfolio showcase: 3 pre-loaded example documents (1 invoice PDF, 1 receipt image, 1 contract PDF), pre-computed extraction baselines in `data/demo/baselines/`, and a Docker Compose seed mechanism that auto-loads demo data on first launch. The demo data enables the Compare tab to show raw-vs-enhanced diffs without requiring a live VLM API key. Visitors can experience the full product flow immediately after `docker compose up`.

## Context

- **Phase**: 7 — Testing + Polish
- **Priority**: P1
- **Labels**: `phase-7-testing`, `backend`, `frontend`
- **Dependencies**: #28-#31 (workspace components render demo data), all backend implementation
- **Branch**: `feat/34-demo-data`
- **Estimated scope**: M

## Specs to Read

- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 11.1-11.4
- `specs/system.md` — Docker Compose configuration, env vars
- `specs/backend/services.md` — Document and extraction service interfaces
- `specs/backend/api.md` — Document and extraction API schemas

## Current State (Scaffold)

**Data directories exist but are empty:**
```
data/
├── demo/
│   ├── baselines/               # Empty — needs pre-computed extraction results
│   └── documents/               # Empty — needs sample PDFs/images
├── templates/
│   ├── contract.json            # {} (empty JSON)
│   ├── id_document.json         # {} (empty JSON)
│   ├── invoice.json             # {} (empty JSON)
│   ├── medical_report.json      # {} (empty JSON)
│   └── receipt.json             # {} (empty JSON)
```

**No seed script exists.**

## Requirements

### Functional

1. **Demo Documents** (3 files in `data/demo/documents/`):
   - `invoice-sample.pdf` — A realistic-looking invoice with vendor name, invoice number, date, line items, tax, total
   - `receipt-sample.jpg` — A receipt image (scanned, slightly skewed to demonstrate deskew capability)
   - `contract-sample.pdf` — A multi-page contract with parties, dates, clauses
2. **Pre-computed Baselines** (in `data/demo/baselines/`):
   - For each document: a JSON file containing the extraction result as if the full pipeline had run
   - Includes both raw VLM extraction and enhanced (post-processed) extraction for comparison
   - Fields include realistic confidence scores, bounding boxes, and field values
3. **Raw VLM Baselines** (for Compare tab):
   - Separate JSON files showing what a raw VLM call would return (lower accuracy, missing fields)
   - The enhanced baseline shows corrections and additions made by the pipeline
4. **Seed Script** (`backend/scripts/seed_demo.py`):
   - Reads documents from `data/demo/documents/`
   - Creates document records in the database
   - Uploads files to Supabase Storage (or local storage in dev)
   - Inserts pre-computed extraction results from baselines
   - Inserts audit trail entries
   - Idempotent: skip if demo data already exists (check by filename or tag)
5. **Docker Integration**:
   - Docker Compose runs seed script on first boot
   - Demo documents appear in dashboard without manual action
   - Demo documents tagged with a "demo" badge in the UI

### Non-Functional

- `docker compose up` starts fully functional app within 2 minutes — AC 11.2
- At least 3 pre-loaded documents available on first launch — AC 11.3
- Pre-loaded documents include raw VLM baselines for comparison — AC 11.4
- Demo data is deterministic and reproducible
- Seed script is idempotent (safe to run multiple times)

## Implementation Plan

### File Structure

```
data/demo/
├── documents/
│   ├── invoice-sample.pdf
│   ├── receipt-sample.jpg
│   └── contract-sample.pdf
├── baselines/
│   ├── invoice-sample/
│   │   ├── extraction.json          # Enhanced pipeline extraction result
│   │   ├── raw_extraction.json      # Raw VLM extraction (for comparison)
│   │   ├── audit_trail.json         # Pipeline step timeline
│   │   └── metadata.json            # Document metadata (type, pages, etc.)
│   ├── receipt-sample/
│   │   ├── extraction.json
│   │   ├── raw_extraction.json
│   │   ├── audit_trail.json
│   │   └── metadata.json
│   └── contract-sample/
│       ├── extraction.json
│       ├── raw_extraction.json
│       ├── audit_trail.json
│       └── metadata.json
```

### Baseline JSON Format

**`data/demo/baselines/invoice-sample/metadata.json`**:
```json
{
  "filename": "invoice-sample.pdf",
  "file_type": "pdf",
  "document_type": "invoice",
  "page_count": 1,
  "is_demo": true,
  "description": "Sample invoice from Test Vendor Corp"
}
```

**`data/demo/baselines/invoice-sample/extraction.json`** (enhanced):
```json
{
  "mode": "template",
  "template_type": "invoice",
  "processing_time_ms": 3200,
  "fields": [
    {
      "field_type": "key_value",
      "field_key": "invoice_number",
      "field_value": "INV-2024-001",
      "page_number": 1,
      "bounding_box": { "x": 0.62, "y": 0.08, "width": 0.18, "height": 0.03 },
      "confidence": 0.97,
      "vlm_confidence": 0.91,
      "cv_quality_score": 0.95,
      "is_required": true,
      "is_missing": false
    },
    {
      "field_type": "key_value",
      "field_key": "date",
      "field_value": "2024-01-15",
      "page_number": 1,
      "bounding_box": { "x": 0.62, "y": 0.12, "width": 0.15, "height": 0.03 },
      "confidence": 0.94,
      "vlm_confidence": 0.88,
      "cv_quality_score": 0.95,
      "is_required": true,
      "is_missing": false
    },
    {
      "field_type": "key_value",
      "field_key": "vendor_name",
      "field_value": "Test Vendor Corp",
      "page_number": 1,
      "bounding_box": { "x": 0.05, "y": 0.05, "width": 0.25, "height": 0.04 },
      "confidence": 0.96,
      "vlm_confidence": 0.94,
      "cv_quality_score": 0.95,
      "is_required": true,
      "is_missing": false
    },
    {
      "field_type": "key_value",
      "field_key": "total_amount",
      "field_value": "$1,500.00",
      "page_number": 1,
      "bounding_box": { "x": 0.70, "y": 0.82, "width": 0.15, "height": 0.03 },
      "confidence": 0.92,
      "vlm_confidence": 0.85,
      "cv_quality_score": 0.95,
      "is_required": true,
      "is_missing": false
    },
    {
      "field_type": "key_value",
      "field_key": "tax_amount",
      "field_value": "$150.00",
      "page_number": 1,
      "bounding_box": { "x": 0.70, "y": 0.78, "width": 0.12, "height": 0.03 },
      "confidence": 0.88,
      "vlm_confidence": 0.72,
      "cv_quality_score": 0.95,
      "is_required": false,
      "is_missing": false
    },
    {
      "field_type": "key_value",
      "field_key": "payment_terms",
      "field_value": "Net 30",
      "page_number": 1,
      "bounding_box": { "x": 0.05, "y": 0.88, "width": 0.10, "height": 0.02 },
      "confidence": 0.78,
      "vlm_confidence": 0.45,
      "cv_quality_score": 0.82,
      "is_required": false,
      "is_missing": false
    }
  ]
}
```

**`data/demo/baselines/invoice-sample/raw_extraction.json`** (raw VLM, lower quality):
```json
{
  "fields": [
    {
      "field_key": "invoice_number",
      "field_value": "INV-2024-001",
      "confidence": 0.91
    },
    {
      "field_key": "date",
      "field_value": "01/15/2024",
      "confidence": 0.78
    },
    {
      "field_key": "vendor_name",
      "field_value": "Test Vendor Corp",
      "confidence": 0.94
    },
    {
      "field_key": "total_amount",
      "field_value": "1500.00",
      "confidence": 0.75
    }
  ]
}
```

Note: Raw extraction is missing `tax_amount` and `payment_terms` (added by enhanced pipeline), and has lower confidence and inconsistent date format (corrected by pipeline).

**`data/demo/baselines/invoice-sample/audit_trail.json`**:
```json
[
  {
    "step_name": "Image Quality Analysis",
    "step_order": 0,
    "input_summary": { "filename": "invoice-sample.pdf", "pages": 1 },
    "output_summary": { "quality_score": 0.95, "deskew_angle": 0.3, "needs_enhancement": false },
    "parameters": { "blur_threshold": 100, "contrast_threshold": 50 },
    "duration_ms": 180
  },
  {
    "step_name": "Document Preprocessing",
    "step_order": 1,
    "input_summary": { "quality_score": 0.95 },
    "output_summary": { "deskew_applied": false, "contrast_enhanced": false },
    "parameters": { "deskew_threshold_degrees": 2.0 },
    "duration_ms": 50
  },
  {
    "step_name": "VLM Extraction",
    "step_order": 2,
    "input_summary": { "provider": "dashscope", "model": "qwen-vl-max", "template": "invoice" },
    "output_summary": { "fields_extracted": 4, "avg_confidence": 0.845 },
    "parameters": { "temperature": 0.1, "max_tokens": 4096 },
    "duration_ms": 2100
  },
  {
    "step_name": "Post-Processing",
    "step_order": 3,
    "input_summary": { "raw_fields": 4 },
    "output_summary": { "final_fields": 6, "fields_corrected": 1, "fields_added": 2 },
    "parameters": { "confidence_threshold": 0.5 },
    "duration_ms": 320
  }
]
```

### Seed Script

**`backend/scripts/seed_demo.py`**:
```python
"""
Seed demo data for portfolio demonstration.

Reads demo documents and pre-computed baselines from data/demo/
and inserts them into the database + storage.

Usage:
    python -m scripts.seed_demo
    # Or via Makefile: make seed-demo
"""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

# Import your services/repositories to create records

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "demo"
DEMO_USER_ID = "demo-user-00000000-0000-0000-0000-000000000000"

DEMO_DOCUMENTS = [
    {"slug": "invoice-sample", "filename": "invoice-sample.pdf", "file_type": "pdf"},
    {"slug": "receipt-sample", "filename": "receipt-sample.jpg", "file_type": "jpg"},
    {"slug": "contract-sample", "filename": "contract-sample.pdf", "file_type": "pdf"},
]


async def seed():
    """Seed demo documents and extractions."""
    # 1. Check if demo data already exists (idempotent)
    # 2. For each demo document:
    #    a. Read metadata.json for document info
    #    b. Create document record with is_demo=True tag
    #    c. Upload file to storage (or skip if using local)
    #    d. Read extraction.json and insert extraction record
    #    e. Read raw_extraction.json and store for comparison
    #    f. Read audit_trail.json and insert audit entries
    print(f"Seeding {len(DEMO_DOCUMENTS)} demo documents...")
    for doc in DEMO_DOCUMENTS:
        baseline_dir = DATA_DIR / "baselines" / doc["slug"]
        if not baseline_dir.exists():
            print(f"  Skipping {doc['slug']} — no baselines found")
            continue

        metadata = json.loads((baseline_dir / "metadata.json").read_text())
        extraction = json.loads((baseline_dir / "extraction.json").read_text())
        audit = json.loads((baseline_dir / "audit_trail.json").read_text())

        # Create document record...
        # Create extraction record...
        # Create audit trail entries...
        print(f"  Seeded: {doc['filename']}")

    print("Demo data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
```

### Docker Integration

**Add to `docker-compose.yml`** (or `docker-compose.override.yml`):
```yaml
services:
  backend:
    # ... existing config ...
    volumes:
      - ./data:/app/data:ro
    environment:
      - SEED_DEMO_DATA=true

  seed:
    build:
      context: ./backend
    command: python -m scripts.seed_demo
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
    volumes:
      - ./data:/app/data:ro
    restart: "no"
```

### Dashboard Demo Badge

In `DocumentCard.tsx`, check for demo flag:
```typescript
// If document has a "demo" tag or specific metadata
{document.document_type && (
  <Badge variant="outline" className="text-xs border-primary text-primary">
    Demo
  </Badge>
)}
```

### Demo Document Content

Since we cannot generate real PDFs in code, the approach is:

1. **Invoice**: Create a simple PDF with `reportlab` or use a publicly available sample invoice
2. **Receipt**: Use a photographed/scanned receipt image (JPEG)
3. **Contract**: Use a multi-page text-based contract PDF

For the scaffold, create placeholder files and document the process for generating real samples:

```bash
# Generate sample invoice PDF (example with Python reportlab)
python backend/scripts/generate_demo_docs.py
```

## Acceptance Criteria

- [ ] `docker compose up` starts full app without manual config beyond `.env` — AC 11.1
- [ ] Application accessible at localhost within 2 minutes — AC 11.2
- [ ] At least 3 pre-loaded demo documents visible on dashboard — AC 11.3
- [ ] Demo documents include pre-computed raw VLM baselines for Compare tab — AC 11.4
- [ ] Demo documents have realistic extraction fields with confidence scores
- [ ] Audit trail data present for each demo document
- [ ] Comparison data shows corrected/added fields with diff highlighting
- [ ] Seed script is idempotent (running twice does not duplicate data)
- [ ] Demo documents marked with "Demo" badge in dashboard
- [ ] Baseline JSON files follow the ExtractionResponse and AuditEntryResponse schemas

## Files Changed

### New files:
- `data/demo/documents/invoice-sample.pdf` — sample invoice
- `data/demo/documents/receipt-sample.jpg` — sample receipt
- `data/demo/documents/contract-sample.pdf` — sample contract
- `data/demo/baselines/invoice-sample/metadata.json`
- `data/demo/baselines/invoice-sample/extraction.json`
- `data/demo/baselines/invoice-sample/raw_extraction.json`
- `data/demo/baselines/invoice-sample/audit_trail.json`
- `data/demo/baselines/receipt-sample/metadata.json`
- `data/demo/baselines/receipt-sample/extraction.json`
- `data/demo/baselines/receipt-sample/raw_extraction.json`
- `data/demo/baselines/receipt-sample/audit_trail.json`
- `data/demo/baselines/contract-sample/metadata.json`
- `data/demo/baselines/contract-sample/extraction.json`
- `data/demo/baselines/contract-sample/raw_extraction.json`
- `data/demo/baselines/contract-sample/audit_trail.json`
- `backend/scripts/seed_demo.py` — seed script
- `backend/scripts/generate_demo_docs.py` — PDF generation script (optional)

### Modified files:
- `docker-compose.yml` — add seed service
- `Makefile` — add `seed-demo` target
- `frontend/src/components/dashboard/DocumentCard.tsx` — add Demo badge

## Verification

```bash
# Generate demo documents (if using generation script)
cd backend && python scripts/generate_demo_docs.py

# Run seed script locally
cd backend && python -m scripts.seed_demo

# Full Docker verification
docker compose up --build
# Wait for services to start
# Visit http://localhost:5173/ → dashboard should show 3 demo documents
# Click invoice → workspace with extraction data, audit trail, comparison
# Compare tab shows raw vs enhanced with blue/green diff highlights

# Idempotency check
docker compose restart seed
# No duplicate documents in dashboard
```
