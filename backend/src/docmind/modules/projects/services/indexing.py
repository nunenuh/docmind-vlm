"""Project indexing service — document indexing for RAG."""

from docmind.library.rag.indexer import index_document, reindex_document


class ProjectIndexingService:
    """Document indexing for RAG."""

    async def index(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> int:
        """Index a document: extract text → chunk → embed → store."""
        return await index_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=file_type,
            filename=filename,
        )

    async def reindex(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str,
    ) -> int:
        """Re-index: delete old chunks → re-extract → re-embed."""
        return await reindex_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=file_type,
            filename=filename,
        )
