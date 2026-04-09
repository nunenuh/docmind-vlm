"""Protocols for the templates module — structural contracts for DI."""

from __future__ import annotations

from typing import Protocol


class TemplateRepositoryProtocol(Protocol):
    """Contract for template persistence."""

    async def list_all(self, user_id: str | None = None) -> list: ...

    async def get_by_id(self, template_id: str) -> object | None: ...

    async def get_by_type(
        self, template_type: str, user_id: str | None = None
    ) -> object | None: ...

    async def create(self, user_id: str, data: dict) -> object: ...

    async def update(
        self, template_id: str, user_id: str, data: dict
    ) -> object | None: ...

    async def delete(self, template_id: str, user_id: str) -> bool: ...

    async def duplicate(
        self, template_id: str, user_id: str
    ) -> object | None: ...


class FieldServiceProtocol(Protocol):
    """Contract for template field operations."""

    def validate_fields(self, fields: list[dict]) -> list[dict]: ...

    def merge_fields(
        self, base: list[dict], override: list[dict]
    ) -> list[dict]: ...


class DetectionServiceProtocol(Protocol):
    """Contract for auto-detection of document type."""

    async def detect(self, file_bytes: bytes) -> dict: ...
