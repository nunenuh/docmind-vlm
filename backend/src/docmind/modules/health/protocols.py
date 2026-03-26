"""Protocols for the health module — structural contracts for DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .schemas import ComponentHealth


class HealthUseCaseProtocol(Protocol):
    """Contract for health check operations."""

    async def get_basic_health(
        self,
    ) -> tuple[str, list[ComponentHealth], float]: ...
