"""
docmind/library/pipeline/rag.py

Project-level RAG chat pipeline.

Nodes: embed_query -> retrieve -> reason -> cite -> END
Each node is a pure function: takes state dict, returns state update dict.
"""

import asyncio

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.providers.factory import get_vlm_provider
from docmind.library.rag.embedder import embed_texts
from docmind.library.rag.retriever import retrieve_similar_chunks

logger = get_logger(__name__)

# System prompt template for persona-grounded RAG
PERSONA_SYSTEM_PROMPT = """You are {persona_name}.

{system_prompt}

TONE: {tone}
RULES: {rules}
BOUNDARIES: {boundaries}

IMPORTANT: You MUST answer based ONLY on the provided context from the project documents.
If the answer is not in the context, say so clearly. Always cite the source document and page number."""

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful document assistant.\n"
    "Answer questions based ONLY on the provided context from the project documents.\n"
    "If the answer is not in the context, say so clearly. "
    "Always cite the source document and page number."
)


def _format_history(history: list[dict]) -> str:
    """Format conversation history for context.

    Args:
        history: List of message dicts with role and content.

    Returns:
        Formatted string of conversation history.
    """
    if not history:
        return "No previous conversation."
    parts = []
    for msg in history:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


def embed_query_node(state: dict) -> dict:
    """Embed the user's query for similarity search.

    Args:
        state: Pipeline state dict with message.

    Returns:
        State update with query_embedding.
    """
    message = state.get("message", "")

    loop = asyncio.new_event_loop()
    try:
        embeddings = loop.run_until_complete(embed_texts([message]))
        query_embedding = embeddings[0]
    finally:
        loop.close()

    return {"query_embedding": query_embedding}


def retrieve_node(state: dict) -> dict:
    """Retrieve relevant chunks from project documents.

    Args:
        state: Pipeline state dict with query_embedding and project_id.

    Returns:
        State update with retrieved_chunks.
    """
    settings = get_settings()
    query_embedding = state.get("query_embedding", [])
    project_id = state.get("project_id", "")

    loop = asyncio.new_event_loop()
    try:
        chunks = loop.run_until_complete(
            retrieve_similar_chunks(
                query_embedding=query_embedding,
                project_id=project_id,
                top_k=settings.RAG_TOP_K,
                threshold=settings.RAG_SIMILARITY_THRESHOLD,
            )
        )
    finally:
        loop.close()

    return {"retrieved_chunks": chunks}


def reason_node(state: dict) -> dict:
    """Generate answer using LLM with persona + retrieved context.

    Args:
        state: Pipeline state dict with message, retrieved_chunks, persona,
               conversation_history, and optional stream_callback.

    Returns:
        State update with raw_answer.
    """
    message = state.get("message", "")
    chunks = state.get("retrieved_chunks", [])
    persona = state.get("persona")
    history = state.get("conversation_history", [])[-10:]  # last 10 messages
    callback = state.get("stream_callback")

    # Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i + 1}: document={chunk.get('document_id', 'unknown')}, "
            f"page={chunk.get('page_number', '?')}]\n{chunk['content']}"
        )
    context = (
        "\n\n".join(context_parts)
        if context_parts
        else "No relevant context found in project documents."
    )

    # Build system prompt from persona
    if persona:
        system_prompt = PERSONA_SYSTEM_PROMPT.format(
            persona_name=persona.get("name", "Assistant"),
            system_prompt=persona.get("system_prompt", ""),
            tone=persona.get("tone", "professional"),
            rules=persona.get("rules", "None"),
            boundaries=persona.get("boundaries", "None"),
        )
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    # Build full message with context
    full_message = (
        f"CONTEXT FROM PROJECT DOCUMENTS:\n{context}\n\n"
        f"CONVERSATION HISTORY:\n{_format_history(history)}\n\n"
        f"USER QUESTION: {message}\n\n"
        "Provide a helpful answer based on the context above. "
        "Cite sources using [Source N] format."
    )

    # Call LLM
    provider = get_vlm_provider()

    loop = asyncio.new_event_loop()
    try:
        response = loop.run_until_complete(
            provider.chat(
                images=[],
                message=full_message,
                history=[],
                system_prompt=system_prompt,
            )
        )
    finally:
        loop.close()

    answer = (
        response.get("content", "") if isinstance(response, dict) else str(response)
    )

    if callback and answer:
        callback("token", content=answer)

    return {"raw_answer": answer}


def cite_node(state: dict) -> dict:
    """Extract citations from the answer and map to document sources.

    Args:
        state: Pipeline state dict with raw_answer and retrieved_chunks.

    Returns:
        State update with answer and citations.
    """
    answer = state.get("raw_answer", "")
    chunks = state.get("retrieved_chunks", [])

    citations = []
    for i, chunk in enumerate(chunks):
        marker = f"[Source {i + 1}]"
        if marker in answer:
            citations.append(
                {
                    "source_index": i + 1,
                    "document_id": chunk.get("document_id", ""),
                    "page_number": chunk.get("page_number", 0),
                    "content_preview": chunk.get("content", "")[:100],
                    "similarity": chunk.get("similarity", 0.0),
                }
            )

    return {
        "answer": answer,
        "citations": citations,
    }


def run_rag_chat_pipeline(initial_state: dict) -> dict:
    """Run the full RAG chat pipeline.

    Nodes: embed_query -> retrieve -> reason -> cite

    Args:
        initial_state: Dict with project_id, user_id, message, persona,
                       conversation_history, and optional stream_callback.

    Returns:
        Final state dict with answer and citations.
    """
    state = dict(initial_state)
    callback = state.get("stream_callback")

    try:
        if callback:
            callback("intent", content="Processing query...")

        # embed_query
        state.update(embed_query_node(state))

        if callback:
            callback("retrieval", content="Searching documents...")

        # retrieve
        state.update(retrieve_node(state))

        if callback:
            callback("reasoning", content="Generating answer...")

        # reason
        state.update(reason_node(state))

        # cite
        state.update(cite_node(state))

        if callback:
            callback("done", content="Complete")

        return state
    except Exception as e:
        logger.error("RAG chat pipeline error: %s", e, exc_info=True)
        return {
            **state,
            "answer": "I encountered an error processing your question. Please try again.",
            "citations": [],
            "error": str(e),
        }
