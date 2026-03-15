"""docmind/modules/documents/repositories.py — Stub."""

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    async def create(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ):
        raise NotImplementedError

    async def get_by_id(self, document_id: str, user_id: str):
        raise NotImplementedError

    async def list_for_user(self, user_id: str, page: int, limit: int):
        raise NotImplementedError

    async def delete(self, document_id: str, user_id: str):
        raise NotImplementedError

    async def update_status(self, document_id: str, status: str, **kwargs):
        raise NotImplementedError
