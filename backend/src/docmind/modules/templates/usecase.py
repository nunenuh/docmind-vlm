"""
docmind/modules/templates/usecase.py

Template use case — orchestrates template operations.
Handler calls this, never the repository directly.
"""

import uuid

import cv2
import numpy as np

from docmind.core.logging import get_logger

from .repositories import TemplateRepository
from .services import TemplateService

logger = get_logger(__name__)


class TemplateUseCase:
    """Orchestrates template CRUD, seeding, and auto-detection."""

    def __init__(
        self,
        repo: TemplateRepository | None = None,
        service: TemplateService | None = None,
    ) -> None:
        self.repo = repo or TemplateRepository()
        self.service = service or TemplateService()

    async def list_templates(self, user_id: str) -> list:
        """List all templates for user (presets + custom). Seeds on first call."""
        await self.repo.seed_presets()
        return await self.repo.list_all(user_id=user_id)

    async def get_template(self, template_id: str):
        """Get template by ID."""
        return await self.repo.get_by_id(template_id)

    async def get_template_by_type(self, template_type: str, user_id: str | None = None):
        """Get template by type, preferring user custom over preset."""
        return await self.repo.get_by_type(template_type, user_id)

    async def create_template(self, user_id: str, data: dict):
        """Create a custom template for user."""
        return await self.repo.create({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "is_preset": False,
            **data,
        })

    async def update_template(self, template_id: str, user_id: str, data: dict):
        """Update a custom template (presets can't be edited)."""
        return await self.repo.update(template_id, user_id, data)

    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """Delete a custom template (presets can't be deleted)."""
        return await self.repo.delete(template_id, user_id)

    async def duplicate_template(self, template_id: str, user_id: str):
        """Duplicate a template as user's custom template."""
        return await self.repo.duplicate(template_id, user_id)

    async def auto_detect(self, file_bytes: bytes) -> dict:
        """Auto-detect document type and fields from file using VLM.

        Args:
            file_bytes: Raw file bytes (image or PDF).

        Returns:
            Dict with document_type, document_name, language, confidence,
            detected_fields, and suggested_template.
        """
        from docmind.library.providers.factory import get_vlm_provider

        image = self._bytes_to_image(file_bytes)
        if image is None:
            return {
                "document_type": "unknown",
                "document_name": "Unknown",
                "language": "unknown",
                "confidence": 0.0,
                "detected_fields": [],
                "suggested_template": {},
            }

        provider = get_vlm_provider()

        classify_prompt = (
            'Analyze this document image. Return JSON: '
            '{"document_type": "ktp", "document_name": "KTP (Kartu Tanda Penduduk)", '
            '"language": "id", "confidence": 0.95}'
        )
        classify_response = await provider.extract(images=[image], prompt=classify_prompt)

        extract_prompt = (
            'Extract ALL visible fields. For each: '
            '{"key": "snake_case_id", "label": "Label on doc", "value": "extracted_value", "required": true}. '
            'Return: {"fields": [...], "document_type": "type"}'
        )
        extract_response = await provider.extract(images=[image], prompt=extract_prompt)

        try:
            classify_data = classify_response.get("structured_data", {})
            doc_type = classify_data.get("document_type", "unknown")
            doc_name = classify_data.get("document_name", doc_type)
            language = classify_data.get("language", "unknown")
            confidence = classify_data.get("confidence", 0.5)
        except Exception:
            doc_type, doc_name, language, confidence = "unknown", "Unknown", "unknown", 0.3

        try:
            extract_data = extract_response.get("structured_data", {})
            detected_fields = extract_data.get("fields", [])
        except Exception:
            detected_fields = []

        return {
            "document_type": doc_type,
            "document_name": doc_name,
            "language": language,
            "confidence": confidence,
            "detected_fields": detected_fields,
            "suggested_template": {
                "type": doc_type,
                "name": doc_name,
                "category": self.service.guess_category(doc_type),
                "fields": detected_fields,
            },
        }

    @staticmethod
    def _bytes_to_image(file_bytes: bytes) -> np.ndarray | None:
        """Convert raw bytes to OpenCV image (handles image + PDF)."""
        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is not None:
            return image

        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
            image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else arr
            doc.close()
            return image
        except Exception:
            return None

