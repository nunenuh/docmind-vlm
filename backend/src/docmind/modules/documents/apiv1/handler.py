"""
docmind/modules/documents/apiv1/handler.py

Document HTTP endpoints — pure file CRUD + search + embedding management.
Extraction is handled by the extractions module.
"""

import asyncio

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select

from docmind.core.config import get_settings
from docmind.core.scopes import require_scopes
from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import ChunkEmbedding, PageChunk
from docmind.library.rag.indexer import index_existing_chunks
from docmind.shared.exceptions import (
    AppException,
    BaseAppException,
    NotFoundException,
    ValidationException,
)

from ..dependencies import get_document_usecase
from ..schemas import (
    DocumentListResponse,
    DocumentResponse,
    EmbeddingModelInfo,
    EmbeddingStatusResponse,
    IndexDocumentResponse,
)
from ..usecase import DocumentUseCase

logger = get_logger(__name__)
router = APIRouter()

ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
    }
)
MAX_UPLOAD_SIZE = 20_971_520  # 20MB

_MIME_TO_FILE_TYPE: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/tiff": "tiff",
    "image/webp": "webp",
}

MAX_FILENAME_LENGTH = 255


def validate_upload(file: UploadFile) -> None:
    """Validate file MIME type and size. Raises ValidationException on failure."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationException(
            f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise ValidationException("File too large. Maximum size: 20MB")


def _validate_file_bytes(file_bytes: bytes) -> None:
    """Enforce actual byte-length limit (defence against missing Content-Length)."""
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise ValidationException("File too large. Maximum size: 20MB")


def _sanitize_filename(raw: str | None) -> str:
    """Clamp filename length and strip control characters."""
    name = (raw or "untitled").strip()
    if not name:
        name = "untitled"
    return name[:MAX_FILENAME_LENGTH]


# ── CRUD ──────────────────────────────────────────────────


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_scopes("documents:write")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Upload a document file."""
    validate_upload(file)
    file_bytes = await file.read()
    _validate_file_bytes(file_bytes)

    filename = _sanitize_filename(file.filename)
    file_type = _MIME_TO_FILE_TYPE[file.content_type]

    try:
        return await usecase.create_document(
            user_id=current_user["id"],
            filename=filename,
            file_type=file_type,
            file_size=len(file_bytes),
            file_bytes=file_bytes,
            content_type=file.content_type,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("create_document error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    standalone: bool = Query(default=False, description="If true, only return documents not linked to a project"),
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """List documents with pagination."""
    return await usecase.get_documents(
        user_id=current_user["id"], page=page, limit=limit, standalone_only=standalone
    )


@router.get("/search", response_model=DocumentListResponse)
async def search_documents(
    q: str | None = Query(default=None, description="Filename search (case-insensitive)"),
    file_type: str | None = Query(default=None, description="Filter by file type: pdf, png, jpg, etc."),
    status: str | None = Query(default=None, description="Filter by status: uploaded, processing, ready, error"),
    standalone: bool = Query(default=True, description="Only standalone documents (not in projects)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Search documents by filename, file type, and/or status."""
    try:
        return await usecase.search_documents(
            user_id=current_user["id"],
            query=q,
            file_type=file_type,
            status=status,
            standalone_only=standalone,
            page=page,
            limit=limit,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("search_documents error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Get a single document by ID."""
    try:
        return await usecase.get_document(user_id=current_user["id"], document_id=document_id)
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_document error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}/url")
async def get_document_url(
    document_id: str,
    request: Request,
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Get a URL for viewing the document file (proxied through backend)."""
    try:
        # Return a backend-proxied URL instead of Supabase signed URL
        base_url = str(request.base_url).rstrip("/")
        proxy_url = f"{base_url}/api/v1/documents/{document_id}/file"
        return {"url": proxy_url}
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_document_url error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Serve the document file bytes directly (proxied from Supabase Storage)."""
    try:
        # Get raw ORM doc (not schema) to access storage_path
        raw_doc = await usecase.repo.get_by_id(document_id, current_user["id"])
        if raw_doc is None:
            raise NotFoundException("Document not found")
        file_bytes = await asyncio.to_thread(
            usecase.storage_service.load_file_bytes, raw_doc.storage_path
        )
        content_type = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "tiff": "image/tiff",
            "webp": "image/webp",
        }.get(raw_doc.file_type, "application/octet-stream")
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={"Content-Disposition": f'inline; filename="{raw_doc.filename}"'},
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_document_file error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(require_scopes("documents:write")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Delete a document and all associated data."""
    try:
        await usecase.delete_document(
            user_id=current_user["id"], document_id=document_id
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("delete_document error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


# ── Embedding Management ─────────────────────────────────


@router.get("/{document_id}/embedding-status", response_model=EmbeddingStatusResponse)
async def get_embedding_status(
    document_id: str,
    current_user: dict = Depends(require_scopes("documents:read")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Get embedding status for a document relative to the current embedding model."""
    try:
        # Verify document ownership
        doc = await usecase.repo.get_by_id(document_id, current_user["id"])
        if doc is None:
            raise NotFoundException("Document not found")

        settings = get_settings()
        current_model = settings.EMBEDDING_MODEL

        async with AsyncSessionLocal() as session:
            # Total chunks for this document
            total_stmt = (
                select(func.count())
                .select_from(PageChunk)
                .where(PageChunk.document_id == document_id)
            )
            total_result = await session.execute(total_stmt)
            total_chunks = total_result.scalar() or 0

            if total_chunks == 0:
                return EmbeddingStatusResponse(
                    current_model=current_model,
                    status="no_chunks",
                    indexed_chunks=0,
                    total_chunks=0,
                    available_models=[],
                )

            # Per-model embedding stats
            model_stmt = (
                select(
                    ChunkEmbedding.model_name,
                    ChunkEmbedding.provider_name,
                    func.count().label("cnt"),
                    func.max(ChunkEmbedding.embedded_at).label("last_embedded"),
                )
                .where(ChunkEmbedding.document_id == document_id)
                .group_by(ChunkEmbedding.model_name, ChunkEmbedding.provider_name)
            )
            model_result = await session.execute(model_stmt)
            model_rows = model_result.all()

        available_models = [
            EmbeddingModelInfo(
                model=row.model_name,
                provider=row.provider_name,
                chunks=row.cnt,
                last_embedded=row.last_embedded,
            )
            for row in model_rows
        ]

        # Determine status for current model
        current_info = next(
            (m for m in available_models if m.model == current_model), None
        )
        if current_info is None:
            status = "not_indexed"
            indexed_chunks = 0
        elif current_info.chunks >= total_chunks:
            status = "indexed"
            indexed_chunks = current_info.chunks
        else:
            status = "partial"
            indexed_chunks = current_info.chunks

        return EmbeddingStatusResponse(
            current_model=current_model,
            status=status,
            indexed_chunks=indexed_chunks,
            total_chunks=total_chunks,
            available_models=available_models,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_embedding_status error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.post("/{document_id}/index", response_model=IndexDocumentResponse)
async def index_document_endpoint(
    document_id: str,
    current_user: dict = Depends(require_scopes("documents:write")),
    usecase: DocumentUseCase = Depends(get_document_usecase),
):
    """Index a document with the current embedding model.

    If chunks exist, only creates embeddings for the current model.
    Idempotent: returns current status if already indexed.
    """
    try:
        # Verify document ownership
        doc = await usecase.repo.get_by_id(document_id, current_user["id"])
        if doc is None:
            raise NotFoundException("Document not found")

        settings = get_settings()
        current_model = settings.EMBEDDING_MODEL
        current_provider = settings.EMBEDDING_PROVIDER
        current_dimensions = settings.EMBEDDING_DIMENSIONS

        chunks_indexed = await index_existing_chunks(
            document_id=document_id,
            provider_name=current_provider,
            model_name=current_model,
            dimensions=current_dimensions,
        )

        # Determine final status
        async with AsyncSessionLocal() as session:
            total_stmt = (
                select(func.count())
                .select_from(PageChunk)
                .where(PageChunk.document_id == document_id)
            )
            total_result = await session.execute(total_stmt)
            total_chunks = total_result.scalar() or 0

            indexed_stmt = (
                select(func.count())
                .select_from(ChunkEmbedding)
                .where(
                    ChunkEmbedding.document_id == document_id,
                    ChunkEmbedding.model_name == current_model,
                )
            )
            indexed_result = await session.execute(indexed_stmt)
            indexed_count = indexed_result.scalar() or 0

        if total_chunks == 0:
            status = "no_chunks"
        elif indexed_count >= total_chunks:
            status = "indexed"
        else:
            status = "partial"

        return IndexDocumentResponse(
            document_id=document_id,
            model=current_model,
            chunks_indexed=chunks_indexed,
            status=status,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("index_document error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")
