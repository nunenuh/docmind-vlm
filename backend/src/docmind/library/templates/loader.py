"""Template configuration loader.

Reads template definitions from data/templates/*.json files.
Provides functions used by the extraction pipeline and API.

All templates include bilingual field names (Indonesian + English),
validation rules, and extraction prompts optimized for VLM.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parents[5] / "data" / "templates"


@lru_cache(maxsize=1)
def _load_all_templates() -> dict[str, dict]:
    """Load all template JSON files from data/templates/.

    Returns:
        Dict mapping template type to template config dict.
    """
    templates: dict[str, dict] = {}
    templates_dir = TEMPLATES_DIR

    if not templates_dir.exists():
        logger.warning("Templates directory not found: %s", templates_dir)
        return templates

    for path in sorted(templates_dir.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            template_type = data.get("type", path.stem)
            templates[template_type] = data
            logger.debug("Loaded template: %s from %s", template_type, path.name)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load template %s: %s", path.name, e)

    logger.info("Loaded %d templates from %s", len(templates), templates_dir)
    return templates


def get_template_config(template_type: str) -> dict | None:
    """Get template config by type.

    Args:
        template_type: Template type identifier (e.g., "ktp", "invoice").

    Returns:
        Template config dict, or None if not found.
    """
    templates = _load_all_templates()
    return templates.get(template_type)


def get_template_fields(template_type: str) -> dict | None:
    """Get required and optional field lists for a template.

    Compatible with the extraction pipeline's _get_template_config() format.

    Args:
        template_type: Template type identifier.

    Returns:
        Dict with "required_fields" and "optional_fields" as string lists,
        or None if template not found.
    """
    config = get_template_config(template_type)
    if config is None:
        return None

    required = config.get("required_fields", [])
    optional = config.get("optional_fields", [])

    # Handle both old format (list of strings) and new format (list of dicts)
    required_keys = [
        f["key"] if isinstance(f, dict) else f
        for f in required
    ]
    optional_keys = [
        f["key"] if isinstance(f, dict) else f
        for f in optional
    ]

    return {
        "required_fields": required_keys,
        "optional_fields": optional_keys,
    }


def get_extraction_prompt(template_type: str) -> str | None:
    """Get the VLM extraction prompt for a template.

    Args:
        template_type: Template type identifier.

    Returns:
        Extraction prompt string, or None if not found.
    """
    config = get_template_config(template_type)
    if config is None:
        return None
    return config.get("extraction_prompt")


def list_templates() -> list[dict]:
    """List all available templates with metadata.

    Returns:
        List of template summary dicts with type, name, description, category, field count.
    """
    templates = _load_all_templates()
    result: list[dict] = []

    for template_type, config in templates.items():
        required = config.get("required_fields", [])
        optional = config.get("optional_fields", [])

        result.append({
            "type": template_type,
            "name": config.get("name", template_type),
            "name_en": config.get("name_en", config.get("name", template_type)),
            "description": config.get("description", ""),
            "description_en": config.get("description_en", config.get("description", "")),
            "category": config.get("category", "general"),
            "required_field_count": len(required),
            "optional_field_count": len(optional),
            "total_field_count": len(required) + len(optional),
        })

    return sorted(result, key=lambda x: (x["category"], x["name"]))


def get_template_detail(template_type: str) -> dict | None:
    """Get full template detail including field definitions.

    Args:
        template_type: Template type identifier.

    Returns:
        Full template config with structured field info, or None.
    """
    config = get_template_config(template_type)
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
