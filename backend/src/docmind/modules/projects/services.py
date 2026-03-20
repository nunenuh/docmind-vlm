"""
docmind/modules/projects/services.py

Project service — business logic layer for project operations.
Currently thin pass-through; will grow with RAG pipeline integration.
"""

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Service layer for project business logic."""

    def validate_project_name(self, name: str) -> str:
        """Validate and sanitize project name."""
        sanitized = name.strip()
        if not sanitized:
            raise ValueError("Project name cannot be empty")
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        return sanitized

    def validate_persona_assignment(self, persona_id: str | None) -> None:
        """Validate persona can be assigned to a project.

        Future: check persona exists and user has access.
        """
        if persona_id is not None and not persona_id.strip():
            raise ValueError("persona_id cannot be an empty string")
