"""Conversation-aware query rewriting for RAG.

Resolves pronouns and contextual references in follow-up questions
by rewriting them into self-contained queries using the LLM.

Example:
    history: [{"role": "user", "content": "tell me about the resume"}]
    query: "what about his education?"
    rewritten: "What is the education background mentioned in the resume?"
"""

from __future__ import annotations

import logging

from docmind.core.config import get_settings
from docmind.library.providers.factory import UserProviderOverride

logger = logging.getLogger(__name__)

# Markers that suggest the query references prior conversation context
AMBIGUOUS_MARKERS = [
    "his", "her", "their", "its", "that", "this", "it", "they",
    "the same", "those", "these", "he", "she", "him", "them",
    "nya", "itu", "ini", "dia", "mereka",  # Indonesian pronouns
]

REWRITE_SYSTEM_PROMPT = "You rewrite follow-up questions to be self-contained. Return ONLY the rewritten question, nothing else."

REWRITE_TEMPLATE = """Given this conversation:
{history}

Rewrite this follow-up question to be self-contained (resolve all pronouns and references):
"{query}"

Return ONLY the rewritten question, nothing else."""


def _needs_rewrite(query: str) -> bool:
    """Check if a query likely references prior conversation context.

    Args:
        query: The user's query.

    Returns:
        True if the query contains ambiguous references.
    """
    query_lower = query.lower()
    return any(f" {marker} " in f" {query_lower} " for marker in AMBIGUOUS_MARKERS)


async def rewrite_query_with_context(
    query: str,
    conversation_history: list[dict],
    override: UserProviderOverride | None = None,
) -> str:
    """Rewrite an ambiguous query using conversation context.

    If the query is self-contained (no pronouns/references), returns it unchanged.
    Otherwise, rewrites via LLM to resolve references.

    Args:
        query: The user's follow-up question.
        conversation_history: Previous conversation messages.

    Returns:
        Self-contained rewritten query, or original if no rewrite needed.
    """
    settings = get_settings()

    if not settings.RAG_ENABLE_QUERY_REWRITE:
        return query

    if not conversation_history:
        return query

    if not _needs_rewrite(query):
        return query

    # Build history text from last 2 turns (4 messages max)
    recent = conversation_history[-4:]
    history_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content'][:200]}"
        for msg in recent
    )

    rewrite_prompt = REWRITE_TEMPLATE.format(
        history=history_text,
        query=query,
    )

    try:
        from docmind.library.providers.factory import get_vlm_provider

        provider = get_vlm_provider(override=override)
        response = await provider.chat(
            images=[],
            message=rewrite_prompt,
            history=[],
            system_prompt=REWRITE_SYSTEM_PROMPT,
        )
        rewritten = response.get("content", query).strip().strip('"').strip("'")

        if rewritten and len(rewritten) > 3:
            logger.info(
                "Query rewritten: '%s' → '%s'",
                query[:50], rewritten[:50],
            )
            return rewritten
        return query

    except Exception as e:
        logger.warning("Query rewrite failed, using original: %s", e)
        return query
