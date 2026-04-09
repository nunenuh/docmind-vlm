"""
docmind/modules/personas/services.py

Persona service — persona validation and formatting.
"""

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class PersonaService:
    """Business logic for persona operations."""

    def validate_name(self, name: str) -> str:
        """Validate and sanitize persona name."""
        sanitized = name.strip()
        if not sanitized:
            raise ValueError("Persona name cannot be empty")
        if len(sanitized) > 255:
            sanitized = sanitized[:255]
        return sanitized

    def format_persona_dict(self, persona_obj) -> dict:
        """Convert persona ORM object to dict for usecase."""
        return {
            "name": persona_obj.name,
            "system_prompt": persona_obj.system_prompt,
            "tone": persona_obj.tone,
            "rules": persona_obj.rules,
            "boundaries": persona_obj.boundaries,
        }
