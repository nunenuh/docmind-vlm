"""
docmind/modules/templates/services.py

Template service — loads and serves predefined document extraction templates
from JSON files in data/templates/.
"""

import json
from pathlib import Path

from docmind.core.logging import get_logger

from .schemas import TemplateResponse

logger = get_logger(__name__)

_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "data" / "templates"


class TemplateService:
    """Service for loading and querying extraction templates."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or _DEFAULT_TEMPLATES_DIR
        self._templates: list[TemplateResponse] = []
        self._loaded = False

    def _load(self) -> None:
        """Load templates from JSON files on first access."""
        if self._loaded:
            return
        self._loaded = True

        if not self._templates_dir.is_dir():
            logger.warning("templates_dir_not_found", path=str(self._templates_dir))
            return

        for path in sorted(self._templates_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                template = TemplateResponse(**data)
                self._templates.append(template)
            except (json.JSONDecodeError, TypeError, Exception) as e:
                logger.warning(
                    "template_load_failed",
                    file=path.name,
                    error=str(e),
                )

    def list_templates(self) -> list[TemplateResponse]:
        """Return all available templates."""
        self._load()
        return list(self._templates)

    def get_template(self, template_type: str) -> TemplateResponse | None:
        """Get a template by type name.

        Args:
            template_type: The template type (e.g. "invoice").

        Returns:
            TemplateResponse or None if not found.
        """
        self._load()
        for t in self._templates:
            if t.type == template_type:
                return t
        return None
