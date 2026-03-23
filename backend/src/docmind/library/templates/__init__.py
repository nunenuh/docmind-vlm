"""Template configuration module."""

from .loader import (
    get_extraction_prompt,
    get_template_config,
    get_template_detail,
    get_template_fields,
    list_templates,
)

__all__ = [
    "get_extraction_prompt",
    "get_template_config",
    "get_template_detail",
    "get_template_fields",
    "list_templates",
]
