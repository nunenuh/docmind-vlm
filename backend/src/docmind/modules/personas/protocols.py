"""Protocols for the personas module — structural contracts for DI."""

from __future__ import annotations

from typing import Protocol


class PersonaRepositoryProtocol(Protocol):
    """Contract for persona persistence."""

    async def list_all(self, user_id: str) -> list: ...

    async def get_by_id(self, persona_id: str) -> object | None: ...

    async def create(self, user_id: str, data: dict) -> object: ...

    async def update(
        self, persona_id: str, user_id: str, data: dict
    ) -> object | None: ...

    async def delete(self, persona_id: str, user_id: str) -> bool: ...

    async def duplicate(
        self, persona_id: str, user_id: str
    ) -> object: ...


class PersonaServiceProtocol(Protocol):
    """Contract for persona business logic."""

    def validate_persona(self, data: dict) -> dict: ...

    def get_default_persona(self) -> dict: ...
