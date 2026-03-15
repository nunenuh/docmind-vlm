"""docmind/modules/extractions/repositories.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class ExtractionRepository:
    async def get_latest_extraction(self, document_id: str):
        raise NotImplementedError

    async def get_fields(self, extraction_id: str):
        raise NotImplementedError

    async def get_audit_trail(self, extraction_id: str):
        raise NotImplementedError
