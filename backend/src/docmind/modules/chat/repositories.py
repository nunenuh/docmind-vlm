"""docmind/modules/chat/repositories.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class ChatRepository:
    async def save_message(self, document_id: str, user_id: str, role: str, content: str, citations: list[dict] | None = None) -> str:
        raise NotImplementedError

    async def get_history(self, document_id: str, user_id: str, page: int, limit: int):
        raise NotImplementedError

    async def get_recent_messages(self, document_id: str, user_id: str, limit: int = 20):
        raise NotImplementedError

    async def get_extracted_fields(self, document_id: str):
        raise NotImplementedError
