"""Template detection service — auto-detect document type and fields using VLM."""

import cv2
import numpy as np

from docmind.core.logging import get_logger
from docmind.library.providers.factory import UserProviderOverride, get_vlm_provider

from .field import TemplateFieldService

logger = get_logger(__name__)


class TemplateDetectionService:
    """Auto-detect document type and fields using VLM."""

    async def detect(self, file_bytes: bytes, override: UserProviderOverride | None = None) -> dict:
        """Auto-detect document type and fields from file bytes.

        Args:
            file_bytes: Raw file bytes (image or PDF).

        Returns:
            Dict with document_type, document_name, language, confidence,
            detected_fields, and suggested_template.
        """
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

        provider = get_vlm_provider(override=override)

        classify_response = await provider.extract(
            images=[image],
            prompt=(
                'Analyze this document image. Return JSON: '
                '{"document_type": "ktp", "document_name": "KTP (Kartu Tanda Penduduk)", '
                '"language": "id", "confidence": 0.95}'
            ),
        )

        extract_response = await provider.extract(
            images=[image],
            prompt=(
                'Extract ALL visible fields. For each: '
                '{"key": "snake_case_id", "label": "Label on doc", "value": "extracted_value", "required": true}. '
                'Return: {"fields": [...], "document_type": "type"}'
            ),
        )

        try:
            classify_data = classify_response.get("structured_data", {})
            doc_type = classify_data.get("document_type", "unknown")
            doc_name = classify_data.get("document_name", doc_type)
            language = classify_data.get("language", "unknown")
            confidence = classify_data.get("confidence", 0.5)
        except Exception as e:
            logger.warning("classify_response_parse_failed: %s", e)
            doc_type, doc_name, language, confidence = "unknown", "Unknown", "unknown", 0.3

        try:
            extract_data = extract_response.get("structured_data", {})
            detected_fields = extract_data.get("fields", [])
        except Exception as e:
            logger.warning("extract_response_parse_failed: %s", e)
            detected_fields = []

        field_service = TemplateFieldService()
        return {
            "document_type": doc_type,
            "document_name": doc_name,
            "language": language,
            "confidence": confidence,
            "detected_fields": detected_fields,
            "suggested_template": {
                "type": doc_type,
                "name": doc_name,
                "category": field_service.guess_category(doc_type),
                "fields": detected_fields,
            },
        }

    def _bytes_to_image(self, file_bytes: bytes) -> np.ndarray | None:
        """Convert file bytes to OpenCV image."""
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
        except Exception as e:
            logger.warning("pdf_to_image_failed: %s", e)
            return None
