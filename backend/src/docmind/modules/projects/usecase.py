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
from .services import (
    ProjectPromptService,
    ProjectRAGService,
    ProjectIndexingService,
    ProjectVLMService,
)

logger = get_logger(__name__)


class ProjectUseCase:
    """Orchestrates project operations. NEVER calls library directly."""

    def __init__(
        self,
        repo: ProjectRepository | None = None,
        conv_repo: ConversationRepository | None = None,
        prompt_service: ProjectPromptService | None = None,
        rag_service: ProjectRAGService | None = None,
        indexing_service: ProjectIndexingService | None = None,
        vlm_service: ProjectVLMService | None = None,
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.conv_repo = conv_repo or ConversationRepository()
        self.prompt_service = prompt_service or ProjectPromptService()
        self.rag_service = rag_service or ProjectRAGService()
        self.indexing_service = indexing_service or ProjectIndexingService()
        self.vlm_service = vlm_service or ProjectVLMService()

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        persona_id: str | None = None,
    ) -> ProjectResponse:
        """Create a new project."""
        sanitized_name = self.prompt_service.validate_project_name(name)
        self.prompt_service.validate_persona_assignment(persona_id)

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
            update_fields["name"] = self.prompt_service.validate_project_name(
                update_fields["name"]
            )

        if "persona_id" in update_fields:
            self.prompt_service.validate_persona_assignment(update_fields["persona_id"])

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
        from docmind.modules.documents.repositories import DocumentRepository
        from docmind.modules.documents.services import DocumentStorageService

        doc_repo = DocumentRepository()
        storage_service = DocumentStorageService()

        doc = await doc_repo.get_by_id(document_id, user_id)
        if doc is None:
            logger.warning("Document %s not found for RAG indexing", document_id)
            return

        file_bytes = await asyncio.to_thread(storage_service.load_file_bytes, doc.storage_path)

        chunk_count = await self.indexing_service.index(
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

    async def reindex_document(
        self, user_id: str, project_id: str, document_id: str
    ) -> int | None:
        """Re-index a document: delete old RAG chunks and re-index.

        Args:
            user_id: Authenticated user.
            project_id: Project the document belongs to.
            document_id: Document to re-index.

        Returns:
            Number of new chunks created, or None if not found.
        """
        from docmind.modules.documents.services import DocumentStorageService

        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return None

        docs = await self.repo.list_documents(project_id, user_id)
        doc = next((d for d in docs if str(d.id) == document_id), None)
        if doc is None:
            return None

        storage_service = DocumentStorageService()
        file_bytes = storage_service.load_file_bytes(doc.storage_path)

        count = await self.indexing_service.reindex(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=doc.file_type,
            filename=doc.filename,
        )

        logger.info("Reindexed document %s: %d chunks", document_id, count)
        return count

    async def list_chunks(
        self, user_id: str, project_id: str, document_id: str | None = None
    ) -> dict:
        """List RAG chunks for a project."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return {"total": 0, "items": []}

        chunks, total = await self.repo.list_chunks(project_id, document_id)
        return {
            "total": total,
            "items": [
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "content": c.content[:200] + "..." if len(c.content or "") > 200 else c.content,
                    "raw_content": (c.raw_content or "")[:200] + "..." if len(c.raw_content or "") > 200 else c.raw_content,
                    "content_hash": c.content_hash,
                    "metadata": c.metadata_json,
                    "created_at": str(c.created_at) if c.created_at else None,
                }
                for c in chunks
            ],
        }

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
        """Stream RAG chat response with thinking + answer tokens.

        Uses DashScope SSE streaming. Yields thinking tokens first,
        then answer tokens, then citations, then done.

        Args:
            project_id: Project to chat within.
            user_id: Authenticated user ID.
            message: User's chat message.
            conversation_id: Existing conversation to continue, or None for new.

        Yields:
            SSE-formatted data strings.
        """
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

        yield _sse("status", {"message": "Saving message...", "conversation_id": conversation_id})

        # Save user message
        await self.conv_repo.add_message(conversation_id, "user", message)

        # --- Query Rewriting (via service) ---
        search_query = message
        try:
            rewritten = await self.rag_service.rewrite_query(message, history)
            if rewritten != message:
                search_query = rewritten
                yield _sse("status", {"message": f"Searching: {rewritten[:60]}..."})
            else:
                yield _sse("status", {"message": "Searching documents..."})
        except Exception as e:
            logger.warning("Query rewrite failed: %s", e)
            yield _sse("status", {"message": "Searching documents..."})

        # --- RAG Retrieval (via service) ---
        try:
            query_embedding = await self.rag_service.embed_query(search_query)
            chunks = await self.rag_service.retrieve_chunks(
                project_id=project_id,
                query_embedding=query_embedding,
                query_text=search_query,
            )
        except Exception as e:
            logger.error("RAG retrieval failed: %s", e)
            chunks = []

        # Build context from retrieved chunks (via service)
        context_text, citations = self.prompt_service.build_rag_context(chunks)

        # Load document metadata for the system prompt (via service)
        doc_list = await self.repo.list_documents(project_id, user_id)
        doc_metadata = self.prompt_service.format_document_metadata(doc_list)

        # Build system prompt (via service)
        system_prompt = self.prompt_service.build_system_prompt(
            persona=persona,
            doc_metadata=doc_metadata,
            doc_count=len(doc_list) if doc_list else 0,
        )

        # Build full message with context
        full_message = f"CONTEXT:\n{context_text}\n\nQUESTION: {message}"

        # --- Stream LLM Response (via service) ---
        yield _sse("status", {"message": "Generating response..."})

        full_answer = ""

        try:
            async for event in self.vlm_service.stream_chat(
                message=full_message,
                system_prompt=system_prompt,
                history=history,
            ):
                if event["type"] == "thinking":
                    yield _sse("thinking", {"content": event["content"]})
                elif event["type"] == "answer":
                    full_answer += event["content"]
                    yield _sse("token", {"content": event["content"]})
                elif event["type"] == "done":
                    pass
        except Exception as e:
            logger.error("Streaming chat failed: %s", e)
            full_answer = "I encountered an error while processing your question. Please try again."
            yield _sse("token", {"content": full_answer})

        # Yield complete answer + citations
        yield _sse(
            "answer",
            {
                "content": full_answer,
                "citations": citations,
                "conversation_id": conversation_id,
            },
        )

        # Save assistant message
        await self.conv_repo.add_message(
            conversation_id,
            "assistant",
            full_answer,
            citations=json.dumps(citations) if citations else None,
        )

        yield _sse("done", {"conversation_id": conversation_id})
