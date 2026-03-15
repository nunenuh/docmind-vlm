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
