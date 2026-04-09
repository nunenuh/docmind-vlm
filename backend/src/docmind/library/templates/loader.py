"""Template configuration loader.

Reads from DB (primary) with JSON file fallback.
The DB is seeded from JSON files on first access.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parents[5] / "data" / "templates"


@lru_cache(maxsize=1)
def _load_json_templates() -> dict[str, dict]:
    """Load template JSON files as fallback when DB is not available."""
    templates: dict[str, dict] = {}

    if not TEMPLATES_DIR.exists():
        return templates

    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            template_type = data.get("type", path.stem)
            templates[template_type] = data
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load template %s: %s", path.name, e)

    return templates


def get_template_fields(template_type: str) -> dict | None:
    """Get required and optional field lists for a template.

    Reads from JSON files (DB access is async, use repository for DB).

    Args:
        template_type: Template type identifier.

    Returns:
        Dict with required_fields and optional_fields as string lists.
    """
    templates = _load_json_templates()
    config = templates.get(template_type)
    if config is None:
        return None

    required = config.get("required_fields", [])
    optional = config.get("optional_fields", [])

    required_keys = [f["key"] if isinstance(f, dict) else f for f in required]
    optional_keys = [f["key"] if isinstance(f, dict) else f for f in optional]

    return {
        "required_fields": required_keys,
        "optional_fields": optional_keys,
    }


def get_extraction_prompt(template_type: str) -> str | None:
    """Get the VLM extraction prompt for a template."""
    templates = _load_json_templates()
    config = templates.get(template_type)
    if config is None:
        return None
    return config.get("extraction_prompt")


def get_template_detail(template_type: str) -> dict | None:
    """Get full template detail from JSON files."""
    templates = _load_json_templates()
    config = templates.get(template_type)
    if config is None:
        return None

    return {
        "type": config.get("type", template_type),
        "name": config.get("name", template_type),
        "name_en": config.get("name_en", ""),
        "description": config.get("description", ""),
        "description_en": config.get("description_en", ""),
        "category": config.get("category", "general"),
        "required_fields": config.get("required_fields", []),
        "optional_fields": config.get("optional_fields", []),
        "extraction_prompt": config.get("extraction_prompt", ""),
    }


def list_templates() -> list[dict]:
    """List all JSON file templates (fallback, use DB repository for primary)."""
    templates = _load_json_templates()
    result: list[dict] = []

    for template_type, config in templates.items():
        required = config.get("required_fields", [])
        optional = config.get("optional_fields", [])

        result.append({
            "type": template_type,
            "name": config.get("name", template_type),
            "name_en": config.get("name_en", ""),
            "description": config.get("description", ""),
            "description_en": config.get("description_en", ""),
            "category": config.get("category", "general"),
            "required_field_count": len(required),
            "optional_field_count": len(optional),
            "total_field_count": len(required) + len(optional),
        })

    return sorted(result, key=lambda x: (x["category"], x["name"]))
