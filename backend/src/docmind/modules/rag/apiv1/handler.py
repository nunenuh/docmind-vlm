"""
docmind/modules/rag/apiv1/handler.py

RAG HTTP endpoints — search, chunk browsing, and stats.
All endpoints are JWT-authenticated.
"""

from fastapi import APIRouter, Depends, Query

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.shared.exceptions import AppException, BaseAppException

from ..dependencies import get_rag_usecase
from ..schemas import (
    ChunkListResult,
    ChunkResult,
    RAGSearchRequest,
    RAGStatsResponse,
    RetrievalResult,
)
from ..usecase import RAGUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.post("/search", response_model=RetrievalResult)
async def rag_search(
    body: RAGSearchRequest,
    current_user: dict = Depends(get_current_user),
    usecase: RAGUseCase = Depends(get_rag_usecase),
):
    """Semantic search across a project's indexed documents."""
    try:
        if body.history:
            return await usecase.retrieve_with_rewrite(
                project_id=body.project_id,
                query=body.query,
                history=body.history,
                top_k=body.top_k,
                threshold=body.threshold,
            )
        return await usecase.retrieve(
            project_id=body.project_id,
            query=body.query,
            top_k=body.top_k,
            threshold=body.threshold,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("rag_search error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/chunks", response_model=ChunkListResult)
async def list_chunks(
    project_id: str = Query(...),
    document_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    usecase: RAGUseCase = Depends(get_rag_usecase),
):
    """List RAG chunks for a project, optionally filtered by document."""
    try:
        return await usecase.list_chunks(
            project_id=project_id,
            document_id=document_id,
            limit=limit,
            offset=offset,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("list_chunks error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/chunks/{chunk_id}", response_model=ChunkResult)
async def get_chunk(
    chunk_id: str,
    project_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    usecase: RAGUseCase = Depends(get_rag_usecase),
):
    """Get a single chunk with full content."""
    try:
        return await usecase.get_chunk(chunk_id=chunk_id, project_id=project_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_chunk error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/stats", response_model=RAGStatsResponse)
async def rag_stats(
    project_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    usecase: RAGUseCase = Depends(get_rag_usecase),
):
    """Get chunk statistics for a project."""
    try:
        total = await usecase.get_chunk_count(project_id)
        return RAGStatsResponse(
            project_id=project_id,
            total_chunks=total,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("rag_stats error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")
