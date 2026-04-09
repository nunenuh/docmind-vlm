# Demo Data

Pre-computed extraction baselines for portfolio demonstration.

## Structure

```
demo/
├── baselines/
│   ├── invoice_extraction.json    # Acme Corp invoice, 6 fields
│   ├── receipt_extraction.json    # Coffee shop receipt, 4 fields
│   └── contract_extraction.json   # Service agreement, 5 fields
└── documents/
    └── (add sample PDFs/images here)
```

## Usage

Baselines can be loaded into the Compare tab without requiring a live VLM API key.
Each baseline contains: fields, confidence scores, bounding boxes, and audit trail.

## Adding Demo Documents

Place sample PDF/image files in `documents/` and create corresponding baselines in `baselines/`.
