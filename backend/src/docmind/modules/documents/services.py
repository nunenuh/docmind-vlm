"""
docmind/modules/documents/services.py

Document service — file upload/download via Supabase Storage.
"""

import uuid
from pathlib import PurePosixPath

from docmind.core.logging import get_logger
from docmind.dbase.supabase.storage import (
    delete_file,
    get_file_bytes,
    upload_file,
)

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".webp"})


class DocumentService:
    """Service layer for document file operations."""

    def upload_file(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        file_bytes: bytes,
        content_type: str,
    ) -> str:
        """Upload file to Supabase Storage. Returns the storage path.

        Generates a UUID-based safe filename to prevent path traversal.
        Only preserves allowed file extensions.
        """
        ext = PurePosixPath(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            ext = ""
        safe_name = f"{uuid.uuid4().hex}{ext}"
        storage_path = f"documents/{user_id}/{document_id}/{safe_name}"

        logger.info(
            "uploading_file",
            user_id=user_id,
            document_id=document_id,
            content_type=content_type,
            file_size=len(file_bytes),
        )

        upload_file(storage_path, file_bytes, content_type)
        return storage_path

    def load_file_bytes(self, storage_path: str) -> bytes:
        """Download file bytes from Supabase storage."""
        return get_file_bytes(storage_path)

    def delete_storage_file(self, storage_path: str) -> None:
        """Delete a file from Supabase storage."""
        delete_file(storage_path)
