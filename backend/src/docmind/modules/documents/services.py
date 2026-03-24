"""
docmind/modules/documents/services.py

Document services — file storage, extraction pipeline, auto-classification.
Multiple focused service classes. Usecase delegates all I/O here.
"""

import uuid
from pathlib import PurePosixPath

import cv2
import numpy as np

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.dbase.supabase.storage import (
    delete_file,
    get_file_bytes,
    get_signed_url,
    upload_file,
)
from docmind.library.pipeline.extraction import run_extraction_pipeline
from docmind.library.providers.factory import get_vlm_provider

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


class DocumentExtractionService:
    """Runs the document extraction pipeline via library."""

    def run_pipeline(self, initial_state: dict) -> dict:
        """Run the full processing pipeline (preprocess → extract → postprocess → store).

        This is a blocking call — should be run in a thread from async context.

        Args:
            initial_state: Pipeline state dict with file_bytes, template_type, etc.

        Returns:
            Pipeline result dict.
        """
        return run_extraction_pipeline(initial_state)


class DocumentClassificationService:
    """Auto-detect document type using VLM."""

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()

    async def classify(self, file_bytes: bytes, file_type: str, template_types: list[str]) -> str | None:
        """Classify a document image to detect its type.

        Args:
            file_bytes: Raw file bytes.
            file_type: File extension (pdf, png, etc.).
            template_types: Available template type strings to match against.

        Returns:
            Detected template type string, or None if undetectable.
        """
        image = self._bytes_to_image(file_bytes, file_type)
        if image is None:
            return None

        types_str = ", ".join(template_types)
        provider = get_vlm_provider()
        prompt = (
            f"What type of document is this? Choose from: {types_str}, or 'unknown' if none match. "
            "Return ONLY the type name, nothing else."
        )

        response = await provider.extract(images=[image], prompt=prompt)
        content = response.get("content", "").strip().lower().replace('"', "").replace("'", "")

        for t_type in template_types:
            if t_type in content:
                return t_type

        return content if content in template_types else None

    def _bytes_to_image(self, file_bytes: bytes, file_type: str) -> np.ndarray | None:
        """Convert file bytes to OpenCV image."""
        if file_type == "pdf":
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
                image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else arr
                doc.close()
                return image
            except Exception as e:
                logger.warning("pdf_to_image_failed: %s", e)
                return None
        else:
            nparr = np.frombuffer(file_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image


# Backward compat alias
DocumentService = DocumentStorageService
