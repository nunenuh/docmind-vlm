"""RAG query service — query rewriting with conversation context."""

from __future__ import annotations

from docmind.core.config import Settings, get_settings
from docmind.core.logging import get_logger
from docmind.library.rag.query_rewriter import rewrite_query_with_context

logger = get_logger(__name__)


class RAGQueryService:
    """Query rewriting with conversation context.

    Resolves ambiguous references (pronouns, "that document", etc.)
    in follow-up questions using LLM-based rewriting.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def rewrite_query(self, message: str, history: list[dict]) -> str:
        """Rewrite a query to resolve ambiguous references.

        If RAG_ENABLE_QUERY_REWRITE is disabled, returns the original message.
        """
        if not self._settings.RAG_ENABLE_QUERY_REWRITE:
            return message

        try:
            return await rewrite_query_with_context(message, history)
        except Exception as e:
            logger.warning("query_rewrite_failed, using original: %s", e)
            return message
