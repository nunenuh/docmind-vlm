"""docmind/modules/analytics/schemas.py"""

from pydantic import BaseModel


class DocumentStats(BaseModel):
    total: int = 0
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}


class AnalyticsSummaryResponse(BaseModel):
    documents: DocumentStats = DocumentStats()
    pages_processed: int = 0
    storage_bytes: int = 0
    storage_mb: float = 0.0
    rag_chunks: int = 0
    projects: int = 0
    custom_personas: int = 0
