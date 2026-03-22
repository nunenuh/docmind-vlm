"""
docmind/modules/projects/usecase.py

Project use case — orchestrates service + repository calls.
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from docmind.core.logging import get_logger

from .repositories import ConversationRepository, ProjectRepository
from .schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    ProjectDocumentResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from .services import ProjectService

logger = get_logger(__name__)


class ProjectUseCase:
    """Orchestrates project operations across service and repository layers."""

    def __init__(
        self,
        service: ProjectService | None = None,
        repo: ProjectRepository | None = None,
        conv_repo: ConversationRepository | None = None,
    ) -> None:
        self.service = service or ProjectService()
        self.repo = repo or ProjectRepository()
        self.conv_repo = conv_repo or ConversationRepository()

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        persona_id: str | None = None,
    ) -> ProjectResponse:
        """Create a new project."""
        sanitized_name = self.service.validate_project_name(name)
        self.service.validate_persona_assignment(persona_id)

        project = await self.repo.create(
            user_id=user_id,
            name=sanitized_name,
            description=description,
            persona_id=persona_id,
        )

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            document_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def get_project(
        self, user_id: str, project_id: str
    ) -> ProjectResponse | None:
        """Get a single project by ID."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return None

        doc_count = await self.repo.get_document_count(project_id)

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            document_count=doc_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def get_projects(
        self, user_id: str, page: int, limit: int
    ) -> ProjectListResponse:
        """Get paginated projects for a user."""
        items, total = await self.repo.list_for_user(user_id, page, limit)

        response_items = []
        for project in items:
            doc_count = await self.repo.get_document_count(str(project.id))
            response_items.append(
                ProjectResponse(
                    id=str(project.id),
                    name=project.name,
                    description=project.description,
                    persona_id=project.persona_id,
                    document_count=doc_count,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
            )

        return ProjectListResponse(
            items=response_items,
            total=total,
            page=page,
            limit=limit,
        )

    async def update_project(
        self, user_id: str, project_id: str, data: ProjectUpdate
    ) -> ProjectResponse | None:
        """Update a project."""
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return await self.get_project(user_id, project_id)

        if "name" in update_fields and update_fields["name"] is not None:
            update_fields["name"] = self.service.validate_project_name(
                update_fields["name"]
            )

        if "persona_id" in update_fields:
            self.service.validate_persona_assignment(update_fields["persona_id"])

        project = await self.repo.update(project_id, user_id, **update_fields)
        if project is None:
            return None

        doc_count = await self.repo.get_document_count(project_id)

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            document_count=doc_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project and all associated data."""
        return await self.repo.delete(project_id, user_id)

    async def add_document(
        self, user_id: str, project_id: str, document_id: str
    ) -> bool:
        """Link a document to a project and trigger RAG indexing."""
        # Verify project ownership
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return False

        added = await self.repo.add_document(project_id, document_id)
        if not added:
            return False

        # Trigger RAG indexing in background (non-blocking)
        import asyncio
        asyncio.create_task(self._safe_index(project_id, document_id, user_id))

        return True

    async def _safe_index(
        self, project_id: str, document_id: str, user_id: str
    ) -> None:
        """Background wrapper for RAG indexing with error handling."""
        try:
            await self._index_document_for_rag(project_id, document_id, user_id)
        except Exception as e:
            logger.error("RAG indexing failed for doc %s: %s", document_id, e)

    async def _index_document_for_rag(
        self, project_id: str, document_id: str, user_id: str
    ) -> None:
        """Download file and run RAG indexing pipeline."""
        from docmind.dbase.supabase.storage import get_file_bytes
        from docmind.library.rag.indexer import index_document
        from docmind.modules.documents.repositories import DocumentRepository

        doc_repo = DocumentRepository()
        doc = await doc_repo.get_by_id(document_id, user_id)
        if doc is None:
            logger.warning("Document %s not found for RAG indexing", document_id)
            return

        # Download file bytes from storage
        import asyncio
        file_bytes = await asyncio.to_thread(get_file_bytes, doc.storage_path)

        # Run indexing
        chunk_count = await index_document(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=doc.file_type,
            filename=doc.filename,
        )
        logger.info(
            "RAG indexed doc %s: %d chunks for project %s",
            document_id, chunk_count, project_id,
        )

    async def list_documents(
        self, user_id: str, project_id: str
    ) -> list[ProjectDocumentResponse]:
        """List all documents in a project."""
        docs = await self.repo.list_documents(project_id, user_id)
        return [
            ProjectDocumentResponse(
                id=str(doc.id),
                filename=doc.filename,
                file_type=doc.file_type,
                status=doc.status,
                created_at=doc.created_at,
            )
            for doc in docs
        ]

    async def remove_document(
        self, user_id: str, project_id: str, document_id: str
    ) -> bool:
        """Unlink a document from a project."""
        # Verify project ownership
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return False
        return await self.repo.remove_document(project_id, document_id)

    async def list_conversations(
        self, user_id: str, project_id: str
    ) -> list[ConversationResponse]:
        """List all conversations for a project."""
        # Verify project ownership
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return []

        conversations = await self.conv_repo.list_for_project(project_id, user_id)
        result = []
        for conv in conversations:
            msg_count = await self.conv_repo.get_message_count(str(conv.id))
            result.append(
                ConversationResponse(
                    id=str(conv.id),
                    title=conv.title,
                    message_count=msg_count,
                    created_at=conv.created_at,
                )
            )
        return result

    async def get_conversation(
        self, user_id: str, conversation_id: str
    ) -> ConversationDetailResponse | None:
        """Get a conversation with all messages."""
        conversation = await self.conv_repo.get_by_id(conversation_id, user_id)
        if conversation is None:
            return None

        return ConversationDetailResponse(
            id=str(conversation.id),
            title=conversation.title,
            messages=[
                MessageResponse(
                    id=str(msg.id),
                    role=msg.role,
                    content=msg.content,
                    citations=msg.citations,
                    created_at=msg.created_at,
                )
                for msg in conversation.messages
            ],
            created_at=conversation.created_at,
        )

    async def delete_conversation(
        self, user_id: str, conversation_id: str
    ) -> bool:
        """Delete a conversation and all its messages."""
        return await self.conv_repo.delete(conversation_id, user_id)

    async def project_chat_stream(
        self,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream RAG chat response for a project.

        Args:
            project_id: Project to chat within.
            user_id: Authenticated user ID.
            message: User's chat message.
            conversation_id: Existing conversation to continue, or None for new.

        Yields:
            SSE-formatted data strings.
        """
        from docmind.library.pipeline.rag import run_rag_chat_pipeline
        from docmind.modules.personas.repositories import PersonaRepository

        def _sse(event: str, data: dict) -> str:
            return f"data: {json.dumps({'event': event, **data})}\n\n"

        # Verify project access
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            yield _sse("error", {"message": "Project not found"})
            return

        # Load persona
        persona = None
        if project.persona_id:
            persona_repo = PersonaRepository()
            persona_obj = await persona_repo.get_by_id(project.persona_id)
            if persona_obj:
                persona = {
                    "name": persona_obj.name,
                    "system_prompt": persona_obj.system_prompt,
                    "tone": persona_obj.tone,
                    "rules": persona_obj.rules,
                    "boundaries": persona_obj.boundaries,
                }

        # Load conversation history
        history: list[dict] = []
        if conversation_id:
            conv = await self.conv_repo.get_by_id(conversation_id, user_id)
            if conv and hasattr(conv, "messages"):
                history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in conv.messages
                ]

        # Create or reuse conversation
        if not conversation_id:
            conv = await self.conv_repo.create(
                project_id, user_id, title=message[:50]
            )
            conversation_id = str(conv.id)

        # Save user message
        await self.conv_repo.add_message(conversation_id, "user", message)

        # Build initial state
        events_buffer: list[str] = []

        def stream_callback(event_type: str, content: str = "", **kwargs: object) -> None:
            events_buffer.append(
                _sse(event_type, {"message": content, **kwargs})
            )

        initial_state = {
            "project_id": project_id,
            "user_id": user_id,
            "message": message,
            "persona": persona,
            "conversation_history": history,
            "stream_callback": stream_callback,
        }

        # Run pipeline in thread to avoid blocking the event loop
        result = await asyncio.to_thread(run_rag_chat_pipeline, initial_state)

        # Yield buffered events
        for event in events_buffer:
            yield event

        # Yield final answer
        answer = result.get("answer", "")
        citations = result.get("citations", [])

        yield _sse(
            "answer",
            {
                "content": answer,
                "citations": citations,
                "conversation_id": conversation_id,
            },
        )

        # Save assistant message
        await self.conv_repo.add_message(
            conversation_id,
            "assistant",
            answer,
            citations=json.dumps(citations) if citations else None,
        )

        yield _sse("done", {"conversation_id": conversation_id})
