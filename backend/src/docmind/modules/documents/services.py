"""
docmind/modules/documents/services.py

Document storage service — file upload, download, delete via Supabase Storage.
Extraction and classification services live in the extractions module.
"""

import uuid
from pathlib import PurePosixPath

import cv2
import numpy as np

from docmind.core.logging import get_logger
from docmind.dbase.supabase.storage import (
    delete_file,
    get_file_bytes,
    get_signed_url,
    upload_file,
)

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".webp"})


class DocumentStorageService:
    """File upload/download via Supabase Storage."""

    def upload_file(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        file_bytes: bytes,
        content_type: str,
    ) -> str:
        """Upload file to storage. Returns the storage path."""
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
        """Download file bytes from storage."""
        return get_file_bytes(storage_path)

    def delete_storage_file(self, storage_path: str) -> None:
        """Delete a file from storage."""
        delete_file(storage_path)

    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for a stored file."""
        return get_signed_url(storage_path, expires_in)

    def load_document_image(self, storage_path: str, file_type: str) -> np.ndarray | None:
        """Download file and convert to OpenCV image for VLM.

        Args:
            storage_path: Supabase storage path.
            file_type: File extension (png, jpg, pdf, etc.).

        Returns:
            OpenCV image array, or None if conversion fails.
        """
        try:
            file_bytes = self.load_file_bytes(storage_path)
            if file_type == "pdf":
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
                image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else arr
                doc.close()
                return image
            else:
                nparr = np.frombuffer(file_bytes, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.warning("Failed to load document image: %s", e)
            return None


# Backward compat alias
DocumentService = DocumentStorageService
