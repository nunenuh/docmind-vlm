"""docmind/modules/chat/apiv1/handler.py"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.modules.documents.usecase import DocumentUseCase

from ..schemas import ChatHistoryResponse, ChatMessageRequest
from ..usecase import ChatUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.post("/{document_id}")
async def send_message(
    document_id: str,
    body: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    doc_usecase = DocumentUseCase()
    document = await doc_usecase.get_document(
        user_id=current_user["id"], document_id=document_id
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chat_usecase = ChatUseCase()
    event_stream = chat_usecase.send_message(
        document_id=document_id, user_id=current_user["id"], message=body.message
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


@router.get("/{document_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    document_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    chat_usecase = ChatUseCase()
    return await chat_usecase.get_history(
        document_id=document_id, user_id=current_user["id"], page=page, limit=limit
    )
