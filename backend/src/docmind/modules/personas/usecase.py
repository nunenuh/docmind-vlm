"""
docmind/modules/personas/usecase.py

Persona use case — orchestrates persona CRUD and seeding.
"""

import uuid

from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException

from .repositories import PersonaRepository
from .services import PersonaService
from .seed import seed_preset_personas

logger = get_logger(__name__)


class PersonaUseCase:
    """Orchestrates persona operations."""

    def __init__(
        self,
        repo: PersonaRepository | None = None,
        service: PersonaService | None = None,
    ) -> None:
        self.repo = repo or PersonaRepository()
        self.service = service or PersonaService()

    async def list_personas(self, user_id: str) -> list:
        """List all personas (presets + user custom). Seeds on first call."""
        await seed_preset_personas()
        return await self.repo.list_for_user(user_id=user_id)

    async def get_persona(self, persona_id: str) -> object | None:
        """Get persona by ID."""
        return await self.repo.get_by_id(persona_id)

    async def create_persona(self, user_id: str, data: dict) -> object | None:
        """Create a custom persona."""
        return await self.repo.create(
            user_id=user_id,
            name=data["name"],
            description=data.get("description"),
            system_prompt=data.get("system_prompt"),
            tone=data.get("tone"),
            rules=data.get("rules"),
            boundaries=data.get("boundaries"),
        )

    async def update_persona(self, persona_id: str, user_id: str, data: dict) -> object | None:
        """Update a custom persona."""
        return await self.repo.update(persona_id, user_id, **data)

    async def delete_persona(self, persona_id: str, user_id: str) -> bool:
        """Delete a custom persona."""
        return await self.repo.delete(persona_id, user_id)

    async def duplicate_persona(self, persona_id: str, user_id: str) -> object:
        """Duplicate a persona as user's custom."""
        source = await self.repo.get_by_id(persona_id)
        if source is None:
            raise NotFoundException("Persona not found")

        return await self.repo.create(
            user_id=user_id,
            name=f"{source.name} (Copy)",
            description=source.description,
            system_prompt=source.system_prompt,
            tone=source.tone,
            rules=source.rules,
            boundaries=source.boundaries,
        )
