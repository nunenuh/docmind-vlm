"""docmind/modules/documents/services.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    def load_file_bytes(self, storage_path: str) -> bytes:
        raise NotImplementedError

    def delete_storage_file(self, storage_path: str) -> None:
        raise NotImplementedError
