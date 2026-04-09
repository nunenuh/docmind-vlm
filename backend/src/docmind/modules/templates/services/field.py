"""Template field service — field normalization and category detection."""


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
