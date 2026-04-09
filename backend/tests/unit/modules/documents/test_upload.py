"""
Unit tests for the document upload flow.

Tests cover:
- Storage upload function
- Service upload logic and path generation
- UseCase orchestration (service + repository wiring)
- Handler validation (MIME type, file size)
"""

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from docmind.dbase.psql.models import Document
from docmind.modules.documents.schemas import DocumentResponse
from docmind.modules.documents.services import DocumentStorageService
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
# Helpers
# ---------------------------------------------------------------------------


def _make_upload_file(
    filename: str = "invoice.pdf",
    content_type: str = "application/pdf",
    size: int = 1024,
    content: bytes = b"%PDF-1.4 fake content",
) -> UploadFile:
    """Create a mock UploadFile for testing."""
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        size=size,
        headers={"content-type": content_type},
    )


def _make_document_orm(
    doc_id: str = DOC_ID,
    user_id: str = USER_ID,
    filename: str = "invoice.pdf",
    storage_path: str = "documents/user-abc-123/doc-def-456/abc123.pdf",
) -> Document:
    """Create a Document ORM instance for testing."""
    return Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        file_type="pdf",
        file_size=1024,
        storage_path=storage_path,
        status="uploaded",
        document_type=None,
        page_count=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests: storage.upload_file
# ---------------------------------------------------------------------------


class TestStorageUploadFile:
    """Tests for the upload_file storage helper."""

    @patch("docmind.dbase.supabase.storage.get_supabase_client")
    @patch("docmind.dbase.supabase.storage.get_settings")
    def test_upload_file_calls_supabase_storage(self, mock_settings, mock_get_client):
        """upload_file should call Supabase storage.upload()."""
        from docmind.dbase.supabase.storage import upload_file

        mock_settings.return_value = MagicMock(STORAGE_BUCKET="docmindvlm")
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_bucket = MagicMock()
        mock_client.storage.from_.return_value = mock_bucket

        upload_file("path/to/file.pdf", b"file content", "application/pdf")

        mock_client.storage.from_.assert_called_once_with("docmindvlm")
        mock_bucket.upload.assert_called_once_with(
            "path/to/file.pdf",
            b"file content",
            {"content-type": "application/pdf"},
        )


# ---------------------------------------------------------------------------
# Tests: DocumentService upload
# ---------------------------------------------------------------------------


class TestDocumentServiceUpload:
    """Tests for DocumentStorageService.upload_file()."""

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_generates_safe_storage_path(self, mock_upload):
        """upload_file should generate a UUID-based storage path."""
        service = DocumentStorageService()

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
        service = DocumentStorageService()

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
        assert call_args[0][2] == "image/png"  # content_type

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_preserves_extension(self, mock_upload):
        """upload_file should keep the original file extension."""
        service = DocumentStorageService()

        result_pdf = service.upload_file(
            USER_ID, DOC_ID, "test.pdf", b"", "application/pdf"
        )
        assert result_pdf.endswith(".pdf")

        result_jpg = service.upload_file(
            USER_ID, DOC_ID, "photo.jpg", b"", "image/jpeg"
        )
        assert result_jpg.endswith(".jpg")

        result_png = service.upload_file(
            USER_ID, DOC_ID, "scan.png", b"", "image/png"
        )
        assert result_png.endswith(".png")

    @patch("docmind.modules.documents.services.upload_file")
    def test_upload_file_rejects_dangerous_extension(self, mock_upload):
        """upload_file should strip dangerous extensions."""
        service = DocumentStorageService()

        result = service.upload_file(
            USER_ID, DOC_ID, "evil.exe", b"", "application/pdf"
        )
        # Should not end with .exe
        assert not result.endswith(".exe")


# ---------------------------------------------------------------------------
# Tests: DocumentUseCase.create_document
# ---------------------------------------------------------------------------


class TestDocumentUseCaseCreate:
    """Tests for DocumentUseCase.create_document() orchestration."""

    @pytest.mark.asyncio
    async def test_create_document_calls_service_upload(self):
        """create_document should call storage_service.upload_file."""
        usecase = DocumentUseCase()
        usecase.storage_service = MagicMock()
        usecase.storage_service.upload_file.return_value = "documents/user/doc/file.pdf"
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

        usecase.storage_service.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_document_calls_repo_create(self):
        """create_document should call repo.create with correct args."""
        usecase = DocumentUseCase()
        usecase.storage_service = MagicMock()
        usecase.storage_service.upload_file.return_value = "documents/user/doc/file.pdf"
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
        call_kwargs = usecase.repo.create.call_args[1]
        assert call_kwargs["user_id"] == USER_ID
        assert call_kwargs["storage_path"] == "documents/user/doc/file.pdf"

    @pytest.mark.asyncio
    async def test_create_document_returns_document_response(self):
        """create_document should return a DocumentResponse."""
        usecase = DocumentUseCase()
        usecase.storage_service = MagicMock()
        usecase.storage_service.upload_file.return_value = "documents/user/doc/file.pdf"
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
        usecase.storage_service = MagicMock()
        usecase.storage_service.upload_file.return_value = "documents/user/doc/file.pdf"
        usecase.storage_service.delete_storage_file = MagicMock()
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

        usecase.storage_service.delete_storage_file.assert_called_once_with(
            "documents/user/doc/file.pdf"
        )


# ---------------------------------------------------------------------------
# Tests: Handler validation
# ---------------------------------------------------------------------------


class TestHandlerValidation:
    """Tests for upload endpoint validation logic."""

    def test_allowed_mime_types_are_correct(self):
        """Verify the set of allowed MIME types."""
        from docmind.modules.documents.apiv1.handler import (
            ALLOWED_MIME_TYPES as handler_types,
        )

        assert handler_types == ALLOWED_MIME_TYPES

    def test_validate_upload_rejects_unsupported_mime_type(self):
        """Unsupported MIME type should raise ValidationException."""
        from docmind.modules.documents.apiv1.handler import validate_upload
        from docmind.shared.exceptions import ValidationException

        file = _make_upload_file(
            filename="script.js",
            content_type="application/javascript",
            size=100,
        )

        with pytest.raises(ValidationException) as exc_info:
            validate_upload(file)

        assert "Unsupported file type" in exc_info.value.message

    def test_validate_upload_rejects_oversized_file(self):
        """File exceeding 20MB should raise ValidationException."""
        from docmind.modules.documents.apiv1.handler import validate_upload
        from docmind.shared.exceptions import ValidationException

        file = _make_upload_file(
            filename="huge.pdf",
            content_type="application/pdf",
            size=MAX_FILE_SIZE + 1,
        )

        with pytest.raises(ValidationException) as exc_info:
            validate_upload(file)

        assert "too large" in exc_info.value.message.lower()

    def test_validate_upload_accepts_valid_pdf(self):
        """Valid PDF under size limit should pass validation."""
        from docmind.modules.documents.apiv1.handler import validate_upload

        file = _make_upload_file(
            filename="invoice.pdf",
            content_type="application/pdf",
            size=1024,
        )

        # Should not raise
        validate_upload(file)

    def test_validate_upload_accepts_all_image_types(self):
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

    def test_validate_file_bytes_rejects_oversized_actual_bytes(self):
        """Actual byte count exceeding limit should raise ValidationException."""
        from docmind.modules.documents.apiv1.handler import _validate_file_bytes
        from docmind.shared.exceptions import ValidationException

        oversized = b"x" * (MAX_FILE_SIZE + 1)

        with pytest.raises(ValidationException) as exc_info:
            _validate_file_bytes(oversized)

        assert "too large" in exc_info.value.message.lower()

    def test_validate_file_bytes_accepts_valid_size(self):
        """Bytes within limit should not raise."""
        from docmind.modules.documents.apiv1.handler import _validate_file_bytes

        _validate_file_bytes(b"small file content")  # Should not raise

    def test_sanitize_filename_truncates_long_names(self):
        """Filenames over 255 chars should be truncated."""
        from docmind.modules.documents.apiv1.handler import _sanitize_filename

        long_name = "a" * 500 + ".pdf"
        result = _sanitize_filename(long_name)
        assert len(result) <= 255

    def test_sanitize_filename_handles_none(self):
        """None filename should return 'untitled'."""
        from docmind.modules.documents.apiv1.handler import _sanitize_filename

        assert _sanitize_filename(None) == "untitled"

    def test_sanitize_filename_handles_empty(self):
        """Empty filename should return 'untitled'."""
        from docmind.modules.documents.apiv1.handler import _sanitize_filename

        assert _sanitize_filename("") == "untitled"
        assert _sanitize_filename("   ") == "untitled"


# ---------------------------------------------------------------------------
# Tests: Cleanup failure resilience
# ---------------------------------------------------------------------------


class TestCleanupFailureResilience:
    """Tests that cleanup failure does not mask the original error."""

    @pytest.mark.asyncio
    async def test_cleanup_failure_preserves_original_exception(self):
        """If delete_storage_file fails during cleanup, original error is still raised."""
        usecase = DocumentUseCase()
        usecase.storage_service = MagicMock()
        usecase.storage_service.upload_file.return_value = "documents/user/doc/file.pdf"
        usecase.storage_service.delete_storage_file.side_effect = RuntimeError("Storage down")
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

        # Cleanup was attempted even though it failed
        usecase.storage_service.delete_storage_file.assert_called_once()
