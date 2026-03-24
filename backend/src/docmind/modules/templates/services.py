"""
docmind/modules/templates/services.py

Template services — field normalization, category detection, VLM auto-detect.
"""

import cv2
import numpy as np

from docmind.core.logging import get_logger
from docmind.library.providers.factory import get_vlm_provider

logger = get_logger(__name__)


class TemplateFieldService:
    """Field normalization and category detection."""

    def normalize_fields(self, fields: list) -> list[dict]:
        """Normalize field definitions to a consistent format."""
        normalized = []
        for f in fields:
            if isinstance(f, dict):
                normalized.append({
                    "key": f.get("key", ""),
                    "label": f.get("label", f.get("key", "")),
                    "label_en": f.get("label_en", ""),
                    "type": f.get("type", "string"),
                    "validation": f.get("validation"),
                    "values": f.get("values"),
                    "required": f.get("required", True),
                })
            elif isinstance(f, str):
                normalized.append({
                    "key": f, "label": f, "label_en": "", "type": "string",
                    "validation": None, "values": None, "required": True,
                })
        return normalized

    def get_required_field_keys(self, fields: list) -> list[str]:
        """Extract required field keys from field definitions."""
        return [
            f["key"] if isinstance(f, dict) else f
            for f in fields
            if (isinstance(f, dict) and f.get("required", True)) or isinstance(f, str)
        ]

    def get_optional_field_keys(self, fields: list) -> list[str]:
        """Extract optional field keys from field definitions."""
        return [
            f["key"] for f in fields
            if isinstance(f, dict) and not f.get("required", True)
        ]

    def guess_category(self, doc_type: str) -> str:
        """Guess template category from document type string."""
        mapping = {
            "identity": {"ktp", "kk", "sim", "passport", "id_document"},
            "vehicle": {"stnk", "bpkb"},
            "tax": {"npwp", "faktur_pajak", "spt"},
            "finance": {"invoice", "receipt", "slip_gaji", "kuitansi"},
            "legal": {"contract", "surat_kuasa", "bast", "agreement"},
        }
        dt = doc_type.lower()
        for category, types in mapping.items():
            if dt in types:
                return category
        return "general"


class TemplateDetectionService:
    """Auto-detect document type and fields using VLM."""

    async def detect(self, file_bytes: bytes) -> dict:
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

        provider = get_vlm_provider()

        # Classify
        classify_response = await provider.extract(
            images=[image],
            prompt=(
                'Analyze this document image. Return JSON: '
                '{"document_type": "ktp", "document_name": "KTP (Kartu Tanda Penduduk)", '
                '"language": "id", "confidence": 0.95}'
            ),
        )

        # Extract fields
        extract_response = await provider.extract(
            images=[image],
            prompt=(
                'Extract ALL visible fields. For each: '
                '{"key": "snake_case_id", "label": "Label on doc", "value": "extracted_value", "required": true}. '
                'Return: {"fields": [...], "document_type": "type"}'
            ),
        )

        # Parse responses
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
        except Exception:
            return None
