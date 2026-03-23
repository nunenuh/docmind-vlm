# Dynamic Template System

## Problem

Current template system is static JSON files. Users can't create or customize templates. The AI should auto-detect document types and let users refine.

## Solution

Templates become **database records** that are:
- **AI-generated** — VLM auto-detects document type + fields on first extraction
- **User-editable** — rename fields, add/remove, adjust validation
- **Shareable** — presets are global, custom templates are per-user
- **Versioned** — editing creates a new version, old extractions keep their template version

## Data Model

```sql
CREATE TABLE templates (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),             -- NULL for preset/system templates
    type VARCHAR(100) NOT NULL,      -- "ktp", "invoice", "custom_001"
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    is_preset BOOLEAN DEFAULT FALSE, -- system templates can't be deleted
    fields JSONB NOT NULL,           -- [{key, label, label_en, type, validation, required}]
    extraction_prompt TEXT,          -- custom VLM prompt
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed preset templates from JSON files on first migration
-- Users can duplicate presets to customize
```

## Flow

### Auto-Detect (new document, no template selected)

```
Upload image → VLM classify: "What type of document is this?"
           → VLM extract: "Extract ALL fields you can see"
           → System creates a new template from extracted fields
           → User sees: "Detected: KTP. Fields: NIK, Nama, ..."
           → User can: Accept / Edit / Rename / Delete fields
           → Template saved to DB for next time
```

### Template Selection (user picks template before extraction)

```
Upload image → User selects "KTP" from template list
           → System uses KTP template fields + extraction prompt
           → VLM extracts only the specified fields
           → User sees extracted fields
```

### Template Editor

```
Settings → Templates → [KTP, Invoice, My Custom Template, ...]
  → Click to edit:
    - Rename template
    - Add/remove/reorder fields
    - Edit field names, types, validation
    - Edit extraction prompt
    - Preview with a sample document
    - Duplicate to create variant
    - Delete (custom only, not presets)
```

## API Endpoints

```
GET    /api/v1/templates                    — list all (presets + user's custom)
POST   /api/v1/templates                    — create custom template
GET    /api/v1/templates/{id}               — get template detail
PUT    /api/v1/templates/{id}               — update template
DELETE /api/v1/templates/{id}               — delete (custom only)
POST   /api/v1/templates/{id}/duplicate     — duplicate a preset to customize
POST   /api/v1/templates/detect             — auto-detect from image (VLM classify + extract)
```

## Migration Path

1. Seed DB with current JSON template data (KTP, KK, SIM, etc.) as presets
2. Keep JSON files as backup/reference but DB is source of truth
3. `_get_template_config()` reads from DB instead of JSON files
4. Template list endpoint reads from DB

## Priority

Part of P2-01 (replace current static implementation).

## Implementation Order

1. Create `templates` table + migration
2. Seed presets from JSON files
3. Template CRUD endpoints (create, read, update, delete, duplicate)
4. Auto-detect endpoint (VLM classify + extract → create template)
5. Frontend template editor page
6. Frontend template selector in workspace (before processing)
7. Wire template to extraction pipeline
