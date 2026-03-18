"""docmind/modules/extractions/services.py"""

from docmind.core.logging import get_logger

logger = get_logger(__name__)

COLOR_HIGH = "#22c55e"
COLOR_MEDIUM = "#eab308"
COLOR_LOW = "#ef4444"


class ExtractionService:
    @staticmethod
    def confidence_color(confidence: float) -> str:
        if confidence >= 0.8:
            return COLOR_HIGH
        if confidence >= 0.5:
            return COLOR_MEDIUM
        return COLOR_LOW

    @staticmethod
    def diff_fields(
        enhanced: list[dict], raw: list[dict]
    ) -> dict[str, list[str]]:
        """Compare enhanced vs raw fields and categorize differences.

        A field is 'corrected' if field_value or confidence differs.
        A field is 'added' if it exists in enhanced but not in raw.

        Args:
            enhanced: Post-processed field dicts (must have 'id').
            raw: Original VLM output field dicts.

        Returns:
            Dict with 'corrected' and 'added' lists of field IDs.
        """
        raw_lookup: dict[tuple[str, int], dict] = {}
        for f in raw:
            key = (f.get("field_key", ""), f.get("page_number", 0))
            raw_lookup[key] = f

        corrected: list[str] = []
        added: list[str] = []

        for ef in enhanced:
            field_id = ef.get("id", "")
            key = (ef.get("field_key", ""), ef.get("page_number", 0))
            raw_field = raw_lookup.get(key)

            if raw_field is None:
                added.append(field_id)
            else:
                if (
                    ef.get("field_value") != raw_field.get("field_value")
                    or ef.get("confidence") != raw_field.get("confidence")
                ):
                    corrected.append(field_id)

        return {"corrected": corrected, "added": added}

    @staticmethod
    def build_overlay_region(field: dict) -> dict | None:
        bbox = field.get("bounding_box", {})
        if not bbox or not bbox.get("x"):
            return None
        confidence = field.get("confidence", 0.0)
        field_key = field.get("field_key", "")
        field_value = field.get("field_value", "")
        tooltip = f"{field_key}: {field_value}" if field_key else field_value
        return {
            "x": bbox["x"],
            "y": bbox["y"],
            "width": bbox["width"],
            "height": bbox["height"],
            "confidence": confidence,
            "color": ExtractionService.confidence_color(confidence),
            "tooltip": tooltip[:200],
        }
