"""docmind/modules/documents/apiv1/handler.py"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import (
    DocumentListResponse,
    DocumentResponse,
    ProcessRequest,
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
    """Validate file MIME type and size. Raises HTTPException on failure."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            ),
        )
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size: 20MB",
        )


def _validate_file_bytes(file_bytes: bytes) -> None:
    """Enforce actual byte-length limit (defence against missing Content-Length)."""
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size: 20MB",
        )


def _sanitize_filename(raw: str | None) -> str:
    """Clamp filename length and strip control characters."""
    name = (raw or "untitled").strip()
    if not name:
        name = "untitled"
    return name[:MAX_FILENAME_LENGTH]


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    validate_upload(file)
    file_bytes = await file.read()
    _validate_file_bytes(file_bytes)

    filename = _sanitize_filename(file.filename)
    file_type = _MIME_TO_FILE_TYPE[file.content_type]  # guaranteed by validate_upload

    usecase = DocumentUseCase()
    try:
        return await usecase.create_document(
            user_id=current_user["id"],
            filename=filename,
            file_type=file_type,
            file_size=len(file_bytes),
            file_bytes=file_bytes,
            content_type=file.content_type,
        )
    except Exception as e:
        logger.error("Document upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Document upload failed")


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    usecase = DocumentUseCase()
    return usecase.get_documents(user_id=current_user["id"], page=page, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = DocumentUseCase()
    document = usecase.get_document(user_id=current_user["id"], document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    usecase = DocumentUseCase()
    deleted = usecase.delete_document(
        user_id=current_user["id"], document_id=document_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    body: ProcessRequest,
    current_user: dict = Depends(get_current_user),
):
    usecase = DocumentUseCase()
    document = usecase.get_document(user_id=current_user["id"], document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    event_stream = usecase.trigger_processing(
        document_id=document_id, template_type=body.template_type
    )
    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
