"""
docmind/modules/analytics/services.py

Analytics service — formats raw repository data into response shapes.
"""


class AnalyticsService:
    """Formats analytics data. No business logic — pure transformation."""

    @staticmethod
    def format_summary(
        doc_count: int,
        status_counts: dict[str, int],
        type_counts: dict[str, int],
        total_pages: int,
        total_storage: int,
        chunk_count: int,
        project_count: int,
        persona_count: int,
    ) -> dict:
        return {
            "documents": {
                "total": doc_count,
                "by_status": status_counts,
                "by_type": type_counts,
            },
            "pages_processed": total_pages,
            "storage_bytes": total_storage,
            "storage_mb": round(total_storage / (1024 * 1024), 2) if total_storage else 0,
            "rag_chunks": chunk_count,
            "projects": project_count,
            "custom_personas": persona_count,
        }
