"""docmind/modules/projects/apiv1/handler.py"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from docmind.core.scopes import require_scopes
from docmind.core.logging import get_logger
from docmind.shared.exceptions import (
    AppException,
    BaseAppException,
    NotFoundException,
    ValidationException,
)

from ..dependencies import (
    get_project_chat_usecase,
    get_project_conversation_usecase,
    get_project_crud_usecase,
    get_project_document_usecase,
)
from ..schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    ProjectChatRequest,
    ProjectCreate,
    ProjectDocumentResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from ..usecases import (
    ProjectChatUseCase,
    ProjectConversationUseCase,
    ProjectCRUDUseCase,
    ProjectDocumentUseCase,
)

logger = get_logger(__name__)
router = APIRouter()


# ── Project CRUD ──────────────────────────────────────────


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectCRUDUseCase = Depends(get_project_crud_usecase),
):
    try:
        return await usecase.create_project(
            user_id=current_user["id"],
            name=body.name,
            description=body.description,
            persona_id=body.persona_id,
        )
    except BaseAppException:
        raise
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        logger.error("create_project error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_scopes("projects:read")),
    usecase: ProjectCRUDUseCase = Depends(get_project_crud_usecase),
):
    return await usecase.get_projects(
        user_id=current_user["id"], page=page, limit=limit
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(require_scopes("projects:read")),
    usecase: ProjectCRUDUseCase = Depends(get_project_crud_usecase),
):
    try:
        return await usecase.get_project(
            user_id=current_user["id"], project_id=project_id
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_project error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectCRUDUseCase = Depends(get_project_crud_usecase),
):
    try:
        return await usecase.update_project(
            user_id=current_user["id"],
            project_id=project_id,
            data=body,
        )
    except BaseAppException:
        raise
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        logger.error("update_project error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectCRUDUseCase = Depends(get_project_crud_usecase),
):
    try:
        deleted = await usecase.delete_project(
            user_id=current_user["id"], project_id=project_id
        )
        if not deleted:
            raise NotFoundException("Project not found")
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("delete_project error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


# ── Project Documents ─────────────────────────────────────


@router.post(
    "/{project_id}/documents",
    response_model=ProjectDocumentResponse,
    status_code=201,
)
async def add_document_to_project(
    project_id: str,
    document_id: str = Query(...),
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectDocumentUseCase = Depends(get_project_document_usecase),
):
    try:
        doc = await usecase.doc_repo.get_by_id(document_id, current_user["id"])
        if doc is None:
            raise NotFoundException("Document not found")

        added = await usecase.add_document(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
        if not added:
            raise NotFoundException("Project not found")

        return ProjectDocumentResponse(
            id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type,
            status=doc.status,
            created_at=doc.created_at,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("add_document_to_project error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get(
    "/{project_id}/documents",
    response_model=list[ProjectDocumentResponse],
)
async def list_project_documents(
    project_id: str,
    current_user: dict = Depends(require_scopes("projects:read")),
    usecase: ProjectDocumentUseCase = Depends(get_project_document_usecase),
):
    try:
        return await usecase.list_documents(
            user_id=current_user["id"], project_id=project_id
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("list_project_documents error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
async def remove_document_from_project(
    project_id: str,
    document_id: str,
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectDocumentUseCase = Depends(get_project_document_usecase),
):
    try:
        await usecase.remove_document(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("remove_document_from_project error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.post("/{project_id}/documents/{document_id}/reindex")
async def reindex_document(
    project_id: str,
    document_id: str,
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectDocumentUseCase = Depends(get_project_document_usecase),
):
    """Re-index a document's RAG chunks (delete old + re-extract + re-embed)."""
    try:
        result = await usecase.reindex_document(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
        return {"chunks_created": result}
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("reindex_document error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


# ── Project Chat ──────────────────────────────────────────


@router.post("/{project_id}/chat")
async def project_chat(
    project_id: str,
    body: ProjectChatRequest,
    current_user: dict = Depends(require_scopes("projects:chat")),
    usecase: ProjectChatUseCase = Depends(get_project_chat_usecase),
):
    """SSE endpoint for project-level RAG chat."""
    event_stream = usecase.project_chat_stream(
        project_id=project_id,
        user_id=current_user["id"],
        message=body.message,
        conversation_id=body.conversation_id,
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


# ── Conversations ─────────────────────────────────────────


@router.get(
    "/{project_id}/conversations",
    response_model=list[ConversationResponse],
)
async def list_conversations(
    project_id: str,
    current_user: dict = Depends(require_scopes("projects:read")),
    usecase: ProjectConversationUseCase = Depends(get_project_conversation_usecase),
):
    try:
        return await usecase.list_conversations(
            user_id=current_user["id"], project_id=project_id
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("list_conversations error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.get(
    "/{project_id}/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    project_id: str,
    conversation_id: str,
    current_user: dict = Depends(require_scopes("projects:read")),
    usecase: ProjectConversationUseCase = Depends(get_project_conversation_usecase),
):
    try:
        conversation = await usecase.get_conversation(
            user_id=current_user["id"], conversation_id=conversation_id
        )
        if conversation is None:
            raise NotFoundException("Conversation not found")
        return conversation
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("get_conversation error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


@router.delete(
    "/{project_id}/conversations/{conversation_id}", status_code=204
)
async def delete_conversation(
    project_id: str,
    conversation_id: str,
    current_user: dict = Depends(require_scopes("projects:write")),
    usecase: ProjectConversationUseCase = Depends(get_project_conversation_usecase),
):
    try:
        deleted = await usecase.delete_conversation(
            user_id=current_user["id"], conversation_id=conversation_id
        )
        if not deleted:
            raise NotFoundException("Conversation not found")
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("delete_conversation error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")


# ── Chunks ────────────────────────────────────────────────


@router.get("/{project_id}/chunks")
async def list_chunks(
    project_id: str,
    document_id: str | None = Query(default=None),
    current_user: dict = Depends(require_scopes("projects:read")),
    usecase: ProjectDocumentUseCase = Depends(get_project_document_usecase),
):
    """List RAG chunks for a project, optionally filtered by document."""
    try:
        return await usecase.list_chunks(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
    except BaseAppException:
        raise
    except Exception as e:
        logger.error("list_chunks error: %s", e, exc_info=True)
        raise AppException(message="Internal server error")
