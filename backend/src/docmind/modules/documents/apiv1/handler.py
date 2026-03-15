"""docmind/modules/documents/apiv1/handler.py"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import DocumentCreate, DocumentListResponse, DocumentResponse, ProcessRequest
from ..usecase import DocumentUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(body: DocumentCreate, current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    return usecase.create_document(
        user_id=current_user["id"], filename=body.filename,
        file_type=body.file_type, file_size=body.file_size, storage_path=body.storage_path,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    return usecase.get_documents(user_id=current_user["id"], page=page, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    document = usecase.get_document(user_id=current_user["id"], document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    deleted = usecase.delete_document(user_id=current_user["id"], document_id=document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/{document_id}/process")
async def process_document(document_id: str, body: ProcessRequest, current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    document = usecase.get_document(user_id=current_user["id"], document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    event_stream = usecase.trigger_processing(document_id=document_id, template_type=body.template_type)
    return StreamingResponse(event_stream, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
