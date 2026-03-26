"""Protocols for the documents module — structural contracts for DI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    from docmind.core.database import Document


class DocumentRepositoryProtocol(Protocol):
    """Contract for document persistence."""

    async def create(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Document: ...

    async def get_by_id(
        self, document_id: str, user_id: str
    ) -> Document | None: ...

    async def list_for_user(
        self,
        user_id: str,
        page: int,
        limit: int,
        standalone_only: bool = False,
    ) -> tuple[list[Document], int]: ...

    async def search(
        self,
        user_id: str,
        query: str | None = None,
        file_type: str | None = None,
        status: str | None = None,
        standalone_only: bool = True,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Document], int]: ...

    async def delete(
        self, document_id: str, user_id: str
    ) -> str | None: ...

    async def update_status(
        self, document_id: str, status: str, **kwargs: object
    ) -> None: ...


class StorageServiceProtocol(Protocol):
    """Contract for file storage operations."""

    def upload_file(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        file_bytes: bytes,
        content_type: str,
    ) -> str: ...

    def load_file_bytes(self, storage_path: str) -> bytes: ...

    def delete_storage_file(self, storage_path: str) -> None: ...

    def get_signed_url(
        self, storage_path: str, expires_in: int = 3600
    ) -> str: ...

    def load_document_image(
        self, storage_path: str, file_type: str
    ) -> np.ndarray | None: ...
