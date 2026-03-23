"""
docmind/modules/templates/services.py

Template service — field normalization, prompt building, category detection.
"""

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class TemplateService:
    """Business logic for templates: normalization, formatting, detection."""

    @staticmethod
    def normalize_fields(fields: list) -> list[dict]:
        """Normalize field definitions to a consistent format.

        Handles both old format (list of strings) and new format (list of dicts).

        Args:
            fields: Raw field definitions from JSON or DB.

        Returns:
            List of normalized field dicts with key, label, type, required.
        """
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
                    "key": f,
                    "label": f,
                    "label_en": "",
                    "type": "string",
                    "validation": None,
                    "values": None,
                    "required": True,
                })
        return normalized

    @staticmethod
    def get_required_field_keys(fields: list) -> list[str]:
        """Extract required field keys from field definitions.

        Args:
            fields: Normalized field definitions.

        Returns:
            List of field key strings that are required.
        """
        return [
            f["key"] if isinstance(f, dict) else f
            for f in fields
            if (isinstance(f, dict) and f.get("required", True)) or isinstance(f, str)
        ]

    @staticmethod
    def get_optional_field_keys(fields: list) -> list[str]:
        """Extract optional field keys from field definitions."""
        return [
            f["key"]
            for f in fields
            if isinstance(f, dict) and not f.get("required", True)
        ]

    @staticmethod
    def guess_category(doc_type: str) -> str:
        """Guess template category from document type string.

        Args:
            doc_type: Document type identifier.

        Returns:
            Category string.
        """
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
