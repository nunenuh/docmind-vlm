"""docmind/modules/projects/apiv1/handler.py"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException, ValidationException

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
from ..usecase import ProjectUseCase

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        return await usecase.create_project(
            user_id=current_user["id"],
            name=body.name,
            description=body.description,
            persona_id=body.persona_id,
        )
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_project error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    return await usecase.get_projects(
        user_id=current_user["id"], page=page, limit=limit
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        return await usecase.get_project(
            user_id=current_user["id"], project_id=project_id
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("get_project error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        return await usecase.update_project(
            user_id=current_user["id"],
            project_id=project_id,
            data=body,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("update_project error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        deleted = await usecase.delete_project(
            user_id=current_user["id"], project_id=project_id
        )
        if not deleted:
            raise NotFoundException("Project not found")
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_project error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{project_id}/documents",
    response_model=ProjectDocumentResponse,
    status_code=201,
)
async def add_document_to_project(
    project_id: str,
    document_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    from docmind.modules.documents.repositories import DocumentRepository

    try:
        # Fetch document info first (before long-running indexing)
        doc_repo = DocumentRepository()
        doc = await doc_repo.get_by_id(document_id, current_user["id"])
        if doc is None:
            raise NotFoundException("Document not found")

        usecase = ProjectUseCase()
        added = await usecase.add_document(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
        if not added:
            raise NotFoundException("Project not found")

        # Return document info we already have (avoid extra DB call after indexing)
        return ProjectDocumentResponse(
            id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type,
            status=doc.status,
            created_at=doc.created_at,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("add_document_to_project error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{project_id}/documents",
    response_model=list[ProjectDocumentResponse],
)
async def list_project_documents(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        return await usecase.list_documents(
            user_id=current_user["id"], project_id=project_id
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("list_project_documents error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
async def remove_document_from_project(
    project_id: str,
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        await usecase.remove_document(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("remove_document_from_project error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/documents/{document_id}/reindex")
async def reindex_document(
    project_id: str,
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Re-index a document's RAG chunks (delete old + re-extract + re-embed)."""
    usecase = ProjectUseCase()
    try:
        result = await usecase.reindex_document(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
        return {"chunks_created": result}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("reindex_document error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{project_id}/chat")
async def project_chat(
    project_id: str,
    body: ProjectChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """SSE endpoint for project-level RAG chat."""
    usecase = ProjectUseCase()
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


@router.get(
    "/{project_id}/conversations",
    response_model=list[ConversationResponse],
)
async def list_conversations(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        return await usecase.list_conversations(
            user_id=current_user["id"], project_id=project_id
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("list_conversations error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{project_id}/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    project_id: str,
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        conversation = await usecase.get_conversation(
            user_id=current_user["id"], conversation_id=conversation_id
        )
        if conversation is None:
            raise NotFoundException("Conversation not found")
        return conversation
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_conversation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{project_id}/conversations/{conversation_id}", status_code=204
)
async def delete_conversation(
    project_id: str,
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ProjectUseCase()
    try:
        deleted = await usecase.delete_conversation(
            user_id=current_user["id"], conversation_id=conversation_id
        )
        if not deleted:
            raise NotFoundException("Conversation not found")
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_conversation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/chunks")
async def list_chunks(
    project_id: str,
    document_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """List RAG chunks for a project, optionally filtered by document."""
    usecase = ProjectUseCase()
    try:
        return await usecase.list_chunks(
            user_id=current_user["id"],
            project_id=project_id,
            document_id=document_id,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("list_chunks error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
