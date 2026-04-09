"""Project chat usecase — RAG-powered streaming chat."""

import json
from collections.abc import AsyncGenerator

from docmind.core.logging import get_logger
from docmind.modules.personas.protocols import PersonaRepositoryProtocol
from docmind.shared.exceptions import NotFoundException

from ..protocols import (
    ConversationRepositoryProtocol,
    ProjectRepositoryProtocol,
    PromptServiceProtocol,
    RAGServiceProtocol,
    VLMServiceProtocol,
)
from ..repositories import ConversationRepository, ProjectRepository
from ..services import (
    ProjectPromptService,
    ProjectRAGService,
    ProjectVLMService,
)

logger = get_logger(__name__)


class ProjectChatUseCase:
    """Orchestrates RAG chat streaming for projects."""

    def __init__(
        self,
        repo: ProjectRepositoryProtocol | None = None,
        conv_repo: ConversationRepositoryProtocol | None = None,
        prompt_service: PromptServiceProtocol | None = None,
        rag_service: RAGServiceProtocol | None = None,
        vlm_service: VLMServiceProtocol | None = None,
        persona_repo: PersonaRepositoryProtocol | None = None,
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.conv_repo = conv_repo or ConversationRepository()
        self.prompt_service = prompt_service or ProjectPromptService()
        self.rag_service = rag_service or ProjectRAGService()
        self.vlm_service = vlm_service or ProjectVLMService()

        # Cross-module dep — lazy default to avoid circular imports
        if persona_repo is not None:
            self.persona_repo = persona_repo
        else:
            from docmind.modules.personas.repositories import PersonaRepository
            self.persona_repo = PersonaRepository()

    async def project_chat_stream(
        self,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream RAG chat response with thinking + answer tokens.

        Yields SSE-formatted data strings.
        """

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
            persona_obj = await self.persona_repo.get_by_id(project.persona_id)
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

        yield _sse(
            "status",
            {"message": "Saving message...", "conversation_id": conversation_id},
        )

        # Save user message
        await self.conv_repo.add_message(conversation_id, "user", message)

        # --- Query Rewriting (via service) ---
        search_query = message
        try:
            rewritten = await self.rag_service.rewrite_query(message, history)
            if rewritten != message:
                search_query = rewritten
                yield _sse(
                    "status", {"message": f"Searching: {rewritten[:60]}..."}
                )
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
            full_answer = (
                "I encountered an error while processing your question. "
                "Please try again."
            )
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
