"""
docmind/modules/documents/apiv1/handler.py

Document HTTP endpoints — pure file CRUD + search.
Extraction is handled by the extractions module.
"""

import asyncio

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response

from docmind.core.scopes import require_scopes
from docmind.core.logging import get_logger
from docmind.shared.exceptions import (
    AppException,
    BaseAppException,
    ValidationException,
)

from ..dependencies import get_document_usecase
from ..schemas import DocumentListResponse, DocumentResponse
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
            from docmind.shared.exceptions import NotFoundException
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
