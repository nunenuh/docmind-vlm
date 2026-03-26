# Documents & Extractions Module Refactor

## Goal

Clean separation of concerns between the two Mode 1 modules:

- **documents/** — Pure file CRUD + search. No extraction logic.
- **extractions/** — Owns the entire extraction pipeline: trigger, classify, run, store, read results.

## Current State (problems)

```
documents/
├── handler.py      POST /documents/{id}/process  ← extraction in documents!
├── usecase.py      trigger_processing()           ← 120 lines of pipeline orchestration
├── services.py     DocumentExtractionService      ← runs the pipeline
│                   DocumentClassificationService  ← auto-detect document type
└── schemas.py      ProcessRequest                 ← extraction schema in documents!

extractions/
├── handler.py      GET only (read results)        ← can't trigger extraction
├── usecase.py      Read-only operations           ← no write capability
├── services.py     ExtractionService              ← only confidence_color + diff_fields
└── repositories.py Read-only queries              ← no write capability
```

**Problems:**
1. Documents module has 3 services — only 1 (StorageService) belongs there
2. `trigger_processing()` is 120 lines in DocumentUseCase — wrong module
3. ProcessRequest schema in documents — extraction concern
4. Extractions module is read-only — can't trigger its own pipeline
5. No document search capability anywhere

## Target State

```
documents/
├── handler.py      CRUD + search endpoints only
├── usecase.py      Upload, list, get, delete, search
├── services.py     DocumentStorageService only
├── repositories.py CRUD + full-text search queries
└── schemas.py      Document CRUD + search schemas

extractions/
├── handler.py      Trigger + read endpoints
├── usecase.py      Trigger pipeline, classify, read results
├── services.py     ExtractionPipelineService, ClassificationService, ConfidenceService
├── repositories.py Read + write (extraction records, audit entries)
└── schemas.py      ProcessRequest, ExtractionResponse, etc.
```

## API Changes

### Documents Module (after refactor)

Only file CRUD + search. No extraction endpoints.

| Method | Path | Purpose | Change |
|--------|------|---------|--------|
| `POST` | `/api/v1/documents` | Upload file | Stays |
| `GET` | `/api/v1/documents` | List documents | Stays (has `standalone` filter) |
| `GET` | `/api/v1/documents/{id}` | Get document | Stays |
| `DELETE` | `/api/v1/documents/{id}` | Delete document | Stays |
| `GET` | `/api/v1/documents/{id}/url` | Signed download URL | Stays |
| `GET` | `/api/v1/documents/search` | **NEW** — Search by filename/type/status | New |
| ~~`POST`~~ | ~~`/documents/{id}/process`~~ | ~~Trigger extraction~~ | **Removed** (moves to extractions) |
| ~~`POST`~~ | ~~`/documents/batch`~~ | ~~Batch upload~~ | Stays if exists |

### Extractions Module (after refactor)

Owns the full extraction lifecycle.

| Method | Path | Purpose | Change |
|--------|------|---------|--------|
| `POST` | `/api/v1/extractions/{document_id}/process` | **NEW** — Trigger extraction (SSE) | Moved from documents |
| `POST` | `/api/v1/extractions/classify` | **NEW** — Auto-detect document type | Moved from documents |
| `GET` | `/api/v1/extractions/{document_id}` | Get extraction results | Stays |
| `GET` | `/api/v1/extractions/{document_id}/audit` | Audit trail | Stays |
| `GET` | `/api/v1/extractions/{document_id}/overlay` | Confidence overlay | Stays |
| `GET` | `/api/v1/extractions/{document_id}/comparison` | Raw vs enhanced | Stays |
| `GET` | `/api/v1/extractions/{document_id}/export` | Export JSON/CSV | Stays |

## Module Details

### documents/ — File CRUD + Search

#### Handler

```
POST   /api/v1/documents                           Upload file
GET    /api/v1/documents                            List (paginated, standalone filter)
GET    /api/v1/documents/search?q=&file_type=&status=  Search documents
GET    /api/v1/documents/{id}                       Get single
DELETE /api/v1/documents/{id}                       Delete (cascade)
GET    /api/v1/documents/{id}/url                   Signed URL
```

#### UseCase — DocumentUseCase

Methods:
- `create_document(user_id, filename, file_type, file_size, file_bytes, content_type)` — upload + DB record
- `get_document(user_id, document_id)` — single doc
- `get_documents(user_id, page, limit, standalone_only)` — paginated list
- `search_documents(user_id, query, file_type, status, page, limit)` — **NEW** search
- `get_document_url(user_id, document_id)` — signed URL
- `delete_document(user_id, document_id)` — delete + storage cleanup

**Removed from DocumentUseCase:**
- `trigger_processing()` → moves to ExtractionUseCase
- `_processing_stream()` → moves to ExtractionUseCase

#### Services — DocumentStorageService (only)

```python
class DocumentStorageService:
    def upload_file(user_id, document_id, filename, file_bytes, content_type) -> str
    def load_file_bytes(storage_path) -> bytes
    def delete_storage_file(storage_path) -> None
    def get_signed_url(storage_path, expires_in) -> str
    def load_document_image(storage_path, file_type) -> np.ndarray | None
```

**Removed from documents/services.py:**
- `DocumentExtractionService` → moves to extractions/services.py
- `DocumentClassificationService` → moves to extractions/services.py

#### Repository — DocumentRepository

Existing methods stay. Add search:

```python
class DocumentRepository:
    # Existing
    async def create(...) -> Document
    async def get_by_id(document_id, user_id) -> Document | None
    async def list_for_user(user_id, page, limit, standalone_only) -> tuple[list, int]
    async def delete(document_id, user_id) -> str | None
    async def update_status(document_id, status) -> None

    # NEW — search
    async def search(
        user_id: str,
        query: str | None = None,         # filename ILIKE %query%
        file_type: str | None = None,      # exact match
        status: str | None = None,         # exact match
        standalone_only: bool = True,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Document], int]
```

#### Schemas

```python
class DocumentCreate(BaseModel): ...    # stays
class DocumentResponse(BaseModel): ...  # stays
class DocumentListResponse(BaseModel): ...  # stays

# NEW
class DocumentSearchRequest(BaseModel):
    q: str | None = None                 # filename search
    file_type: str | None = None         # pdf, png, jpg, etc.
    status: str | None = None            # uploaded, processing, ready, error
    standalone: bool = True

# REMOVED
# ProcessRequest → moves to extractions/schemas.py
```

### extractions/ — Full Extraction Lifecycle

#### Handler

```
POST /api/v1/extractions/{document_id}/process     Trigger pipeline (SSE)
POST /api/v1/extractions/classify                   Auto-detect type
GET  /api/v1/extractions/{document_id}              Get results
GET  /api/v1/extractions/{document_id}/audit        Audit trail
GET  /api/v1/extractions/{document_id}/overlay      Confidence overlay
GET  /api/v1/extractions/{document_id}/comparison   Raw vs enhanced
GET  /api/v1/extractions/{document_id}/export       Export JSON/CSV
```

#### UseCase — ExtractionUseCase

```python
class ExtractionUseCase:
    def __init__(
        self,
        repo: ExtractionRepository,
        pipeline_service: ExtractionPipelineService,
        classification_service: ClassificationService,
        confidence_service: ConfidenceService,
        # To read document info (file bytes, metadata) — read-only cross-module
        doc_repo: DocumentRepository,
        storage_service: DocumentStorageService,
    ): ...

    # NEW — trigger extraction
    async def process_document(
        document_id: str,
        user_id: str,
        template_type: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """SSE stream: classify → preprocess → extract → postprocess → store.

        1. Fetch document from doc_repo (read-only)
        2. Load file bytes from storage_service
        3. Auto-classify if no template_type
        4. Run pipeline via pipeline_service
        5. Update document status via doc_repo
        6. Yield SSE events throughout
        """

    # NEW — classify without processing
    async def classify_document(
        document_id: str,
        user_id: str,
    ) -> dict:
        """Auto-detect document type without running extraction."""

    # Existing (stays)
    async def get_extraction(document_id) -> ExtractionResponse
    async def get_audit_trail(document_id) -> list[AuditEntryResponse]
    async def get_overlay_data(document_id) -> list[OverlayRegion]
    async def get_comparison(document_id) -> ComparisonResponse
```

#### Services

```python
class ExtractionPipelineService:
    """Runs the LangGraph extraction pipeline."""
    def run_pipeline(initial_state: dict) -> dict
    # Moved from DocumentExtractionService

class ClassificationService:
    """Auto-detect document type using VLM."""
    async def classify(file_bytes, file_type, template_types) -> str | None
    # Moved from DocumentClassificationService

class ConfidenceService:
    """Confidence scoring and visualization helpers."""
    def confidence_color(confidence: float) -> str
    def diff_fields(enhanced, raw) -> dict[str, list[str]]
    # Existing ExtractionService renamed for clarity
```

#### Repository — ExtractionRepository

Existing read methods stay. No new write methods needed — the pipeline's `store` node writes directly via SQLAlchemy (in `library/pipeline/extraction/store.py`).

```python
class ExtractionRepository:
    # Existing (stays)
    async def get_latest_extraction(document_id) -> Extraction | None
    async def get_fields(extraction_id) -> list[ExtractedField]
    async def get_audit_trail(extraction_id) -> list[AuditEntry]
```

#### Schemas

```python
# Moved from documents/schemas.py
class ProcessRequest(BaseModel):
    template_type: str | None = None

# NEW
class ClassifyResponse(BaseModel):
    document_type: str | None
    confidence: float
    available_templates: list[str]

# Existing (stays)
class ExtractionResponse(BaseModel): ...
class ExtractedFieldResponse(BaseModel): ...
class AuditEntryResponse(BaseModel): ...
class OverlayRegion(BaseModel): ...
class ComparisonResponse(BaseModel): ...
```

## Cross-Module Dependencies

Extractions needs to read document info (file bytes, metadata) but should NOT own document CRUD:

```
extractions/usecase.py
    imports:
        from docmind.modules.documents.repositories import DocumentRepository  # read-only
        from docmind.modules.documents.services import DocumentStorageService  # read-only
```

This is a **read-only dependency**. Extractions reads document metadata and file bytes but never creates/updates/deletes documents. The only write-back is `doc_repo.update_status(document_id, "ready")` after processing completes.

```
documents/ ←────── extractions/ (reads document data)
    ↑                    ↑
    │                    │
    └── library/pipeline/extraction/  (shared pipeline code)
```

## Migration Steps

1. **Create `extractions/services.py`** — Add `ExtractionPipelineService` and `ClassificationService` (moved from documents)
2. **Update `extractions/usecase.py`** — Add `process_document()` and `classify_document()`
3. **Update `extractions/schemas.py`** — Add `ProcessRequest` and `ClassifyResponse`
4. **Update `extractions/apiv1/handler.py`** — Add process and classify endpoints
5. **Add search to `documents/repositories.py`** — ILIKE query on filename
6. **Add search to `documents/usecase.py`** — `search_documents()` method
7. **Add search to `documents/apiv1/handler.py`** — `GET /documents/search` endpoint
8. **Add search to `documents/schemas.py`** — `DocumentSearchRequest`
9. **Remove from `documents/services.py`** — Delete `DocumentExtractionService` and `DocumentClassificationService`
10. **Remove from `documents/usecase.py`** — Delete `trigger_processing()` and `_processing_stream()`
11. **Remove from `documents/apiv1/handler.py`** — Delete `process_document` endpoint
12. **Remove `ProcessRequest` from `documents/schemas.py`**
13. **Update `router.py`** — No path changes needed (extractions already registered)
14. **Update frontend** — Change process endpoint from `/documents/{id}/process` to `/extractions/{id}/process`
15. **Update tests** — Adjust imports and endpoint paths

## Document Search Spec

### Endpoint

```
GET /api/v1/documents/search?q=invoice&file_type=pdf&status=ready&page=1&limit=20
```

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | null | Filename search (case-insensitive ILIKE) |
| `file_type` | string | null | Filter by type: pdf, png, jpg, jpeg, tiff, webp |
| `status` | string | null | Filter by status: uploaded, processing, ready, error |
| `standalone` | bool | true | Only standalone documents (not in projects) |
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |

### Response

Same as `DocumentListResponse`:
```json
{
  "items": [DocumentResponse],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

### Repository Query

```sql
SELECT * FROM documents
WHERE user_id = :user_id
  AND (:q IS NULL OR filename ILIKE '%' || :q || '%')
  AND (:file_type IS NULL OR file_type = :file_type)
  AND (:status IS NULL OR status = :status)
  AND (:standalone IS FALSE OR project_id IS NULL)
ORDER BY created_at DESC
LIMIT :limit OFFSET :offset
```

## Notes

- `DocumentStorageService` stays in documents module — it's file management
- Extractions imports it for read-only file access (load bytes, load image)
- The `library/pipeline/extraction/` code is unchanged — it's the shared pipeline
- Templates module is unchanged — extractions reads template config from it
- Frontend needs to update the process API call URL
