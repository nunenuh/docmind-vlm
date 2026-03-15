# Issue #4: Implement Document Upload Flow

## Summary

Implement the end-to-end document upload flow: the handler accepts a multipart file upload, validates file type and size (max 20MB), the usecase orchestrates the upload to Supabase Storage at `{user_id}/{document_id}/{filename}` via the service, then creates a database record via the repository. This connects the handler, usecase, service, and repository layers for the `POST /api/v1/documents` endpoint.

## Context

- **Phase**: 1 — Infrastructure
- **Priority**: P0
- **Labels**: `phase-1-infra`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #1 (Auth JWT), #3 (Document Repository)
- **Branch**: `feat/4-document-upload`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/api.md` — Section "Documents Handler", DocumentCreate schema, error handling rules
- `specs/backend/services.md` — Section "Documents Module > services.py" and "usecase.py"
- `specs/conventions/security.md` — Section "File Upload Validation", MIME type check, filename sanitization
- `specs/conventions/python-module-structure.md` — Layer separation rules

## Current State (Scaffold)

**File: `backend/src/docmind/modules/documents/services.py`**

```python
"""docmind/modules/documents/services.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    def load_file_bytes(self, storage_path: str) -> bytes:
        raise NotImplementedError

    def delete_storage_file(self, storage_path: str) -> None:
        raise NotImplementedError
```

**File: `backend/src/docmind/modules/documents/usecase.py`**

```python
"""docmind/modules/documents/usecase.py — Stub."""
from datetime import datetime, UTC
from typing import AsyncGenerator
from docmind.core.logging import get_logger
from .schemas import DocumentListResponse, DocumentResponse

logger = get_logger(__name__)


class DocumentUseCase:
    def create_document(self, user_id: str, filename: str, file_type: str, file_size: int, storage_path: str) -> DocumentResponse:
        return DocumentResponse(
            id="stub-id", filename=filename, file_type=file_type, file_size=file_size,
            status="uploaded", document_type=None, page_count=0,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
    # ... other stubs
```

**File: `backend/src/docmind/modules/documents/apiv1/handler.py`** (current — uses DocumentCreate body, not file upload)

```python
@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(body: DocumentCreate, current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    return usecase.create_document(
        user_id=current_user["id"], filename=body.filename,
        file_type=body.file_type, file_size=body.file_size, storage_path=body.storage_path,
    )
```

**File: `backend/src/docmind/dbase/supabase/storage.py`** (no upload function yet)

```python
"""File upload/download/signed-URL helpers using Supabase Storage."""
from docmind.core.logging import get_logger
from docmind.dbase.supabase.client import get_supabase_client

logger = get_logger(__name__)
BUCKET_NAME = "documents"

def get_file_bytes(storage_path: str) -> bytes:
    client = get_supabase_client()
    return client.storage.from_(BUCKET_NAME).download(storage_path)

def delete_file(storage_path: str) -> None:
    client = get_supabase_client()
    client.storage.from_(BUCKET_NAME).remove([storage_path])

def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    client = get_supabase_client()
    result = client.storage.from_(BUCKET_NAME).create_signed_url(storage_path, expires_in)
    return result["signedURL"]
```

**File: `backend/src/docmind/modules/documents/schemas.py`**

```python
class DocumentCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., pattern="^(pdf|png|jpg|jpeg|tiff|webp)$")
    file_size: int = Field(..., gt=0, le=20_971_520)
    storage_path: str
```

## Requirements

### Functional

1. **Handler** (`handler.py`): Accept `UploadFile` via multipart form data instead of (or in addition to) the `DocumentCreate` JSON body
2. **Handler**: Validate file MIME type against allowed types: `application/pdf`, `image/jpeg`, `image/png`, `image/tiff`, `image/webp`
3. **Handler**: Validate file size does not exceed 20MB (20,971,520 bytes)
4. **Handler**: Return HTTP 400 for unsupported MIME type, HTTP 413 for oversized files
5. **Service** (`services.py`): Add `upload_file(user_id, document_id, filename, file_bytes) -> str` that uploads to Supabase Storage and returns the storage path
6. **Service**: Generate safe storage path: `documents/{user_id}/{document_id}/{sanitized_filename}`
7. **Service**: Sanitize filename — use UUID-based name with original extension only
8. **UseCase** (`usecase.py`): Orchestrate the flow — generate document_id, call service to upload, call repository to create DB record
9. **UseCase**: Convert the ORM `Document` instance to `DocumentResponse` schema for the handler
10. **Storage** (`storage.py`): Add `upload_file(storage_path, file_bytes, content_type)` function

### Non-Functional

- Never use the original filename directly in storage paths (path traversal prevention)
- File bytes must not be logged
- Upload errors should be caught and logged, returning a generic error to the client
- The handler remains thin — validation and delegation only

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/documents/test_upload.py`

```python
"""
Unit tests for the document upload flow.

Tests cover:
- Storage upload function
- Service upload logic and path generation
- UseCase orchestration (service + repository wiring)
- Handler validation (MIME type, file size)
"""
import uuid
from datetime import datetime, UTC
from io import BytesIO
from pathlib import PurePosixPath
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from docmind.dbase.sqlalchemy.models import Document
from docmind.modules.documents.schemas import DocumentResponse
from docmind.modules.documents.services import DocumentService
from docmind.modules.documents.usecase import DocumentUseCase


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-abc-123"
DOC_ID = "doc-def-456"
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_FILE_SIZE = 20_971_520  # 20MB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_upload_file(
    filename: str = "invoice.pdf",
    content_type: str = "application/pdf",
    size: int = 1024,
    content: bytes = b"%PDF-1.4 fake content",
) -> UploadFile:
    """Create a mock UploadFile for testing."""
    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
        size=size,
    )
    file.content_type = content_type
    return file


def _make_document_orm(
    doc_id: str = DOC_ID,
    user_id: str = USER_ID,
    filename: str = "invoice.pdf",
    storage_path: str = "documents/user-abc-123/doc-def-456/abc123.pdf",
) -> Document:
    """Create a Document ORM instance for testing."""
    doc = Document()
    doc.id = doc_id
    doc.user_id = user_id
    doc.filename = filename
    doc.file_type = "pdf"
    doc.file_size = 1024
    doc.storage_path = storage_path
    doc.status = "uploaded"
    doc.document_type = None
    doc.page_count = 0
    doc.created_at = datetime.now(UTC)
    doc.updated_at = datetime.now(UTC)
    return doc


# ---------------------------------------------------------------------------
# Tests: storage.upload_file
# ---------------------------------------------------------------------------


class TestStorageUploadFile:
    """Tests for the upload_file storage helper."""

    @patch("docmind.dbase.supabase.storage.get_supabase_client")
    def test_upload_file_calls_supabase_storage(self, mock_get_client):
        """upload_file should call Supabase storage.upload()."""
        from docmind.dbase.supabase.storage import upload_file

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_bucket = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket

        upload_file("path/to/file.pdf", b"file content", "application/pdf")

        mock_client.storage.from_.assert_called_once_with("documents")
        mock_bucket.upload.assert_called_once_with(
            "path/to/file.pdf",
            b"file content",
            {"content-type": "application/pdf"},
        )


# ---------------------------------------------------------------------------
# Tests: DocumentService upload
# ---------------------------------------------------------------------------


class TestDocumentServiceUpload:
    """Tests for DocumentService.upload_file()."""

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_generates_safe_storage_path(self, mock_upload):
        """upload_file should generate a UUID-based storage path."""
        service = DocumentService()

        result = service.upload_file(
            user_id=USER_ID,
            document_id=DOC_ID,
            filename="my invoice (2).pdf",
            file_bytes=b"content",
            content_type="application/pdf",
        )

        # Path should be documents/{user_id}/{doc_id}/{uuid}.pdf
        assert result.startswith(f"documents/{USER_ID}/{DOC_ID}/")
        assert result.endswith(".pdf")
        # Should NOT contain the original filename
        assert "my invoice" not in result
        assert "(2)" not in result

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_calls_storage_upload(self, mock_upload):
        """upload_file should delegate to storage.upload_file."""
        service = DocumentService()

        service.upload_file(
            user_id=USER_ID,
            document_id=DOC_ID,
            filename="test.png",
            file_bytes=b"image data",
            content_type="image/png",
        )

        mock_upload.assert_called_once()
        call_args = mock_upload.call_args
        assert call_args[0][1] == b"image data"  # file_bytes
        assert call_args[0][2] == "image/png"    # content_type

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_preserves_extension(self, mock_upload):
        """upload_file should keep the original file extension."""
        service = DocumentService()

        result_pdf = service.upload_file(USER_ID, DOC_ID, "test.pdf", b"", "application/pdf")
        assert result_pdf.endswith(".pdf")

        result_jpg = service.upload_file(USER_ID, DOC_ID, "photo.jpg", b"", "image/jpeg")
        assert result_jpg.endswith(".jpg")

        result_png = service.upload_file(USER_ID, DOC_ID, "scan.png", b"", "image/png")
        assert result_png.endswith(".png")

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_rejects_dangerous_extension(self, mock_upload):
        """upload_file should strip dangerous extensions."""
        service = DocumentService()

        result = service.upload_file(USER_ID, DOC_ID, "evil.exe", b"", "application/pdf")
        # Should not end with .exe
        assert not result.endswith(".exe")


# ---------------------------------------------------------------------------
# Tests: DocumentUseCase.create_document
# ---------------------------------------------------------------------------


class TestDocumentUseCaseCreate:
    """Tests for DocumentUseCase.create_document() orchestration."""

    @pytest.mark.asyncio
    async def test_create_document_calls_service_upload(self):
        """create_document should call service.upload_file."""
        usecase = DocumentUseCase()
        usecase.service = MagicMock()
        usecase.service.upload_file.return_value = "documents/user/doc/file.pdf"
        usecase.repo = AsyncMock()
        usecase.repo.create = AsyncMock(return_value=_make_document_orm())

        await usecase.create_document(
            user_id=USER_ID,
            filename="invoice.pdf",
            file_type="pdf",
            file_size=1024,
            file_bytes=b"content",
            content_type="application/pdf",
        )

        usecase.service.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document_calls_repo_create(self):
        """create_document should call repo.create with correct args."""
        usecase = DocumentUseCase()
        usecase.service = MagicMock()
        usecase.service.upload_file.return_value = "documents/user/doc/file.pdf"
        usecase.repo = AsyncMock()
        usecase.repo.create = AsyncMock(return_value=_make_document_orm())

        await usecase.create_document(
            user_id=USER_ID,
            filename="invoice.pdf",
            file_type="pdf",
            file_size=1024,
            file_bytes=b"content",
            content_type="application/pdf",
        )

        usecase.repo.create.assert_awaited_once()
        call_kwargs = usecase.repo.create.call_args[1] if usecase.repo.create.call_args[1] else {}
        call_args = usecase.repo.create.call_args[0] if usecase.repo.create.call_args[0] else ()
        # Verify user_id and storage_path are passed
        all_args = {**dict(zip(["user_id", "filename", "file_type", "file_size", "storage_path"], call_args)), **call_kwargs}
        assert all_args.get("user_id") == USER_ID
        assert all_args.get("storage_path") == "documents/user/doc/file.pdf"

    @pytest.mark.asyncio
    async def test_create_document_returns_document_response(self):
        """create_document should return a DocumentResponse."""
        usecase = DocumentUseCase()
        usecase.service = MagicMock()
        usecase.service.upload_file.return_value = "documents/user/doc/file.pdf"
        usecase.repo = AsyncMock()
        usecase.repo.create = AsyncMock(return_value=_make_document_orm())

        result = await usecase.create_document(
            user_id=USER_ID,
            filename="invoice.pdf",
            file_type="pdf",
            file_size=1024,
            file_bytes=b"content",
            content_type="application/pdf",
        )

        assert isinstance(result, DocumentResponse)
        assert result.status == "uploaded"

    @pytest.mark.asyncio
    async def test_create_document_cleans_up_on_repo_failure(self):
        """If repo.create fails, uploaded file should be cleaned up."""
        usecase = DocumentUseCase()
        usecase.service = MagicMock()
        usecase.service.upload_file.return_value = "documents/user/doc/file.pdf"
        usecase.service.delete_storage_file = MagicMock()
        usecase.repo = AsyncMock()
        usecase.repo.create = AsyncMock(side_effect=Exception("DB error"))

        with pytest.raises(Exception, match="DB error"):
            await usecase.create_document(
                user_id=USER_ID,
                filename="invoice.pdf",
                file_type="pdf",
                file_size=1024,
                file_bytes=b"content",
                content_type="application/pdf",
            )

        usecase.service.delete_storage_file.assert_called_once_with(
            "documents/user/doc/file.pdf"
        )


# ---------------------------------------------------------------------------
# Tests: Handler validation
# ---------------------------------------------------------------------------


class TestHandlerValidation:
    """Tests for upload endpoint validation logic."""

    def test_allowed_mime_types_are_correct(self):
        """Verify the set of allowed MIME types."""
        from docmind.modules.documents.apiv1.handler import ALLOWED_MIME_TYPES as handler_types

        assert handler_types == ALLOWED_MIME_TYPES

    @pytest.mark.asyncio
    async def test_validate_upload_rejects_unsupported_mime_type(self):
        """Unsupported MIME type should raise HTTPException 400."""
        from docmind.modules.documents.apiv1.handler import validate_upload

        file = _make_upload_file(
            filename="script.js",
            content_type="application/javascript",
            size=100,
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_upload(file)

        assert exc_info.value.status_code == 400
        assert "Unsupported file type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_upload_rejects_oversized_file(self):
        """File exceeding 20MB should raise HTTPException 413."""
        from docmind.modules.documents.apiv1.handler import validate_upload

        file = _make_upload_file(
            filename="huge.pdf",
            content_type="application/pdf",
            size=MAX_FILE_SIZE + 1,
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_upload(file)

        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_upload_accepts_valid_pdf(self):
        """Valid PDF under size limit should pass validation."""
        from docmind.modules.documents.apiv1.handler import validate_upload

        file = _make_upload_file(
            filename="invoice.pdf",
            content_type="application/pdf",
            size=1024,
        )

        # Should not raise
        validate_upload(file)

    @pytest.mark.asyncio
    async def test_validate_upload_accepts_all_image_types(self):
        """All allowed image MIME types should pass validation."""
        from docmind.modules.documents.apiv1.handler import validate_upload

        for mime_type, ext in [
            ("image/jpeg", "photo.jpg"),
            ("image/png", "scan.png"),
            ("image/tiff", "doc.tiff"),
            ("image/webp", "page.webp"),
        ]:
            file = _make_upload_file(
                filename=ext,
                content_type=mime_type,
                size=1024,
            )
            validate_upload(file)  # Should not raise
```

### Step 2: Implement (GREEN)

**Files to modify**:

1. `backend/src/docmind/dbase/supabase/storage.py` — Add `upload_file` function
2. `backend/src/docmind/modules/documents/services.py` — Implement `upload_file`, keep existing `load_file_bytes` and `delete_storage_file`
3. `backend/src/docmind/modules/documents/usecase.py` — Implement `create_document` as async, wire service + repository
4. `backend/src/docmind/modules/documents/apiv1/handler.py` — Add `validate_upload` function, update handler to accept `UploadFile`

**Implementation guidance**:

**storage.py** — Add upload:
```python
def upload_file(storage_path: str, file_bytes: bytes, content_type: str) -> None:
    """Upload file bytes to Supabase storage."""
    client = get_supabase_client()
    client.storage.from_(BUCKET_NAME).upload(
        storage_path, file_bytes, {"content-type": content_type}
    )
```

**services.py** — Add upload with safe path generation:
```python
import uuid
from pathlib import PurePosixPath
from docmind.dbase.supabase.storage import upload_file, get_file_bytes, delete_file

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".webp"}

class DocumentService:
    def upload_file(
        self, user_id: str, document_id: str,
        filename: str, file_bytes: bytes, content_type: str,
    ) -> str:
        """Upload file to Supabase Storage. Returns the storage path."""
        ext = PurePosixPath(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            ext = ""
        safe_name = f"{uuid.uuid4().hex}{ext}"
        storage_path = f"documents/{user_id}/{document_id}/{safe_name}"
        upload_file(storage_path, file_bytes, content_type)
        return storage_path
    # ... existing methods
```

**usecase.py** — Async create with cleanup:
```python
async def create_document(
    self, user_id, filename, file_type, file_size,
    file_bytes, content_type,
) -> DocumentResponse:
    doc_id = str(uuid.uuid4())
    storage_path = self.service.upload_file(
        user_id, doc_id, filename, file_bytes, content_type,
    )
    try:
        doc = await self.repo.create(
            user_id=user_id, filename=filename, file_type=file_type,
            file_size=file_size, storage_path=storage_path,
        )
    except Exception:
        self.service.delete_storage_file(storage_path)
        raise
    return DocumentResponse(
        id=doc.id, filename=doc.filename, file_type=doc.file_type,
        file_size=doc.file_size, status=doc.status,
        document_type=doc.document_type, page_count=doc.page_count,
        created_at=doc.created_at, updated_at=doc.updated_at,
    )
```

**handler.py** — Validation and file upload endpoint:
```python
from fastapi import UploadFile, File

ALLOWED_MIME_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/tiff", "image/webp",
}
MAX_UPLOAD_SIZE = 20_971_520  # 20MB

def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: 20MB",
        )

@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    validate_upload(file)
    file_bytes = await file.read()
    # ... determine file_type from extension
    usecase = DocumentUseCase()
    return await usecase.create_document(...)
```

### Step 3: Refactor (IMPROVE)

- Extract MIME type to file_type mapping into a helper (e.g., `"application/pdf" -> "pdf"`)
- Ensure `validate_upload` is a standalone function (not a method) so tests can import it directly
- Add structured logging for upload operations (file size, type — never log content)
- Verify cleanup on failure is wrapped in try/except to not mask the original error

## Acceptance Criteria

- [ ] `upload_file` in storage.py uploads bytes to Supabase Storage
- [ ] `DocumentService.upload_file` generates UUID-based safe storage path
- [ ] Original filename is never used in the storage path
- [ ] Allowed extensions are preserved; dangerous extensions are stripped
- [ ] `DocumentUseCase.create_document` orchestrates upload + DB create
- [ ] If DB create fails, the uploaded file is cleaned up
- [ ] `validate_upload` rejects unsupported MIME types (HTTP 400)
- [ ] `validate_upload` rejects files over 20MB (HTTP 413)
- [ ] `validate_upload` accepts all allowed MIME types
- [ ] Handler delegates to usecase after validation
- [ ] All 15 unit tests pass

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/dbase/supabase/storage.py` | Modify | Add `upload_file(storage_path, file_bytes, content_type)` |
| `backend/src/docmind/modules/documents/services.py` | Modify | Implement `upload_file` with safe path generation, `load_file_bytes`, `delete_storage_file` |
| `backend/src/docmind/modules/documents/usecase.py` | Modify | Implement async `create_document` with service upload + repo create + cleanup |
| `backend/src/docmind/modules/documents/apiv1/handler.py` | Modify | Add `validate_upload`, update `create_document` to accept `UploadFile` |
| `backend/tests/unit/modules/documents/test_upload.py` | Create | 15 unit tests covering storage, service, usecase, and handler validation |

## Verification

```bash
# Run the upload tests
cd backend && python -m pytest tests/unit/modules/documents/test_upload.py -v

# Run with coverage
cd backend && python -m pytest tests/unit/modules/documents/test_upload.py -v --cov=docmind.modules.documents --cov-report=term-missing

# Verify no original filenames leak into storage paths
grep -n "filename" backend/src/docmind/modules/documents/services.py
# upload_file should generate UUID-based names, not use filename directly

# Verify validation function is importable
python -c "from docmind.modules.documents.apiv1.handler import validate_upload, ALLOWED_MIME_TYPES; print('OK')"
```
