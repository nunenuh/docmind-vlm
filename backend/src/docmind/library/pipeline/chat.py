"""
docmind/library/pipeline/chat.py

LangGraph StateGraph for the document chat agent.

Nodes: router -> retrieve -> reason -> cite -> END.
"""

import asyncio
import re
from typing import Any, Callable, TypedDict

from docmind.core.logging import get_logger
from docmind.library.providers.factory import get_vlm_provider

logger = get_logger(__name__)


class Citation(TypedDict):
    page: int
    bounding_box: dict
    text_span: str


class ChatState(TypedDict):
    document_id: str
    user_id: str
    message: str
    page_images: list[Any]
    extracted_fields: list[dict]
    conversation_history: list[dict]
    intent: str
    intent_confidence: float
    relevant_fields: list[dict]
    re_queried_regions: list[dict]
    raw_answer: str
    answer: str
    citations: list[Citation]
    error_message: str | None
    stream_callback: Callable | None


# --- Intent classification ---

INTENT_PATTERNS: dict[str, list[str]] = {
    "factual_lookup": [
        r"\bwhat\s+is\b",
        r"\bwhat\s+are\b",
        r"\bhow\s+much\b",
        r"\bhow\s+many\b",
        r"\bwhen\s+is\b",
        r"\bwhen\s+was\b",
        r"\bwho\s+is\b",
        r"\btell\s+me\b",
        r"\bfind\b",
        r"\bshow\s+me\b",
        r"\blist\b",
        r"\bget\b",
    ],
    "reasoning": [
        r"\bwhy\b",
        r"\bexplain\b",
        r"\bhow\s+does\b",
        r"\bhow\s+do\b",
        r"\breason\b",
        r"\bcause\b",
        r"\bbecause\b",
        r"\banalyz",
        r"\binterpret\b",
    ],
    "summarization": [
        r"\bsummar",
        r"\boverview\b",
        r"\bbrief\b",
        r"\bhighlight",
        r"\bkey\s+points\b",
        r"\bmain\s+points\b",
        r"\btl;?dr\b",
        r"\bin\s+short\b",
    ],
    "comparison": [
        r"\bcompar",
        r"\bdifference\b",
        r"\bdiffer\b",
        r"\bversus\b",
        r"\bvs\.?\b",
        r"\bbetween\b",
        r"\bcontrast\b",
        r"\bsimilar\b",
    ],
}

_INTENT_LIMITS: dict[str, int] = {
    "factual_lookup": 5,
    "reasoning": 10,
    "comparison": 15,
    "summarization": 20,
}

def _get_chat_settings():
    from docmind.core.config import get_settings
    return get_settings()


def _classify_intent(message: str) -> tuple[str, float]:
    """Classify user message intent using regex pattern matching.

    Args:
        message: User's chat message.

    Returns:
        Tuple of (intent, confidence).
    """
    if not message.strip():
        return ("factual_lookup", 0.3)

    lower = message.lower()
    scores: dict[str, int] = {}

    for intent, patterns in INTENT_PATTERNS.items():
        count = sum(1 for p in patterns if re.search(p, lower))
        if count > 0:
            scores[intent] = count

    if not scores:
        return ("factual_lookup", 0.3)

    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    # Confidence: base 0.5, boost if only one category matched
    confidence = min(0.5 + best_score * 0.1, 0.95)
    if len(scores) == 1:
        confidence = max(confidence, 0.6)

    return (best_intent, round(confidence, 2))


def router_node(state: dict) -> dict:
    """Route user message to an intent category.

    Args:
        state: ChatState dict with message.

    Returns:
        State update with intent and intent_confidence.
    """
    message = state.get("message", "")
    intent, confidence = _classify_intent(message)
    return {"intent": intent, "intent_confidence": confidence}


# --- Field search ---

def _search_fields(
    fields: list[dict], query: str, intent: str
) -> list[dict]:
    """Search extracted fields for relevance to the query.

    Scoring:
    - Exact key match: 1.0
    - Key term overlap: 0.5 per term
    - Value term overlap: 0.3 per term
    - Required field boost for factual_lookup: +0.2

    Args:
        fields: List of extracted field dicts.
        query: User's search query.
        intent: Classified intent type.

    Returns:
        Sorted list of matching fields, limited by intent.
    """
    if not fields or not query.strip():
        return []

    limit = _INTENT_LIMITS.get(intent, 5)
    query_terms = set(re.findall(r"\w+", query.lower()))

    scored: list[tuple[float, dict]] = []

    for field in fields:
        score = 0.0
        field_key = (field.get("field_key") or "").lower()
        field_value = (field.get("field_value") or "").lower()

        # Exact key match
        if field_key and field_key in query.lower():
            score += 1.0

        # Key term overlap
        key_terms = set(field_key.replace("_", " ").split())
        key_overlap = len(query_terms & key_terms)
        score += key_overlap * 0.5

        # Value term overlap
        value_terms = set(re.findall(r"\w+", field_value))
        value_overlap = len(query_terms & value_terms)
        score += value_overlap * 0.3

        # Required field boost for factual_lookup (only if already relevant)
        if score > 0 and intent == "factual_lookup" and field.get("is_required"):
            score += 0.2

        if score > 0:
            scored.append((score, field))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:limit]]


def retrieve_node(state: dict) -> dict:
    """Retrieve relevant fields for the user's query.

    For factual_lookup with low-confidence fields and available page images,
    marks fields for VLM re-query (limited to 3).

    Args:
        state: ChatState dict with message, intent, extracted_fields, page_images.

    Returns:
        State update with relevant_fields and re_queried_regions.
    """
    message = state.get("message", "")
    intent = state.get("intent", "factual_lookup")
    fields = state.get("extracted_fields", [])
    page_images = state.get("page_images", [])

    relevant = _search_fields(fields, message, intent)

    re_queried: list[dict] = []
    if intent == "factual_lookup" and page_images:
        low_conf = [
            f for f in relevant
            if f.get("confidence", 1.0) < _get_chat_settings().CHAT_LOW_CONFIDENCE
        ]
        for f in low_conf[:_get_chat_settings().CHAT_MAX_REQUERY_FIELDS]:
            bbox = f.get("bounding_box", {})
            if bbox:
                re_queried.append({
                    "field_key": f.get("field_key", ""),
                    "page_number": f.get("page_number", 1),
                    "bounding_box": bbox,
                    "original_confidence": f.get("confidence", 0.0),
                })

    return {
        "relevant_fields": relevant,
        "re_queried_regions": re_queried,
    }


# --- Reasoning ---

GROUNDING_SYSTEM_PROMPT = """You are a document analysis assistant. You MUST answer based ONLY on the extracted document data provided below. Do NOT hallucinate or infer information not present in the data. If the data does not contain the answer, say so clearly.

When referencing specific data, mention the page number (e.g., "on page 1")."""


_REASONING_INSTRUCTIONS: dict[str, str] = {
    "factual_lookup": "Provide a precise, exact answer based on the document data. Quote the relevant values directly.",
    "reasoning": "Provide a step-by-step explanation based on the document data. Show your reasoning clearly.",
    "summarization": "Synthesize and summarize the key information from the document data provided.",
    "comparison": "Compare the relevant values side-by-side, highlighting similarities and differences.",
}


def _confidence_label(confidence: float) -> str:
    """Map confidence score to human label."""
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.5:
        return "medium"
    return "LOW"


def _build_context(state: dict) -> str:
    """Build document context string from state.

    Args:
        state: ChatState dict with relevant_fields, re_queried_regions,
               conversation_history.

    Returns:
        Formatted context string for the VLM prompt.
    """
    parts: list[str] = []

    # Relevant fields
    fields = state.get("relevant_fields", [])
    if fields:
        parts.append("EXTRACTED DOCUMENT DATA:")
        for f in fields:
            key = f.get("field_key", "unknown")
            value = f.get("field_value", "")
            page = f.get("page_number", "?")
            conf = _confidence_label(f.get("confidence", 0.0))
            parts.append(f'- [{key}] = "{value}" (page {page}, confidence: {conf})')

    # Re-queried regions
    regions = state.get("re_queried_regions", [])
    if regions:
        parts.append("\nDETAILED RE-ANALYSIS:")
        for r in regions:
            key = r.get("field_key", "unknown")
            detail = r.get("detailed_value", "")
            page = r.get("page_number", "?")
            parts.append(f"- [{key}] page {page}: {detail}")

    # Conversation history (capped)
    history = state.get("conversation_history", [])
    if history:
        recent = history[-_get_chat_settings().CHAT_MAX_HISTORY:]
        parts.append("\nCONVERSATION HISTORY:")
        for msg in recent:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")

    return "\n".join(parts)


def _get_reasoning_instruction(intent: str) -> str:
    """Get intent-specific reasoning instruction.

    Args:
        intent: Classified intent type.

    Returns:
        Instruction string for the VLM prompt.
    """
    return _REASONING_INSTRUCTIONS.get(intent, _REASONING_INSTRUCTIONS["factual_lookup"])


def reason_node(state: dict) -> dict:
    """Generate a grounded answer using the VLM provider.

    Constructs context from relevant fields, calls VLM with grounding
    system prompt, and streams tokens via callback if provided.

    Args:
        state: ChatState dict.

    Returns:
        State update with raw_answer.
    """
    try:
        context = _build_context(state)
        instruction = _get_reasoning_instruction(state.get("intent", "factual_lookup"))
        message = state.get("message", "")
        page_images = state.get("page_images", [])[:_get_chat_settings().CHAT_MAX_PAGE_IMAGES]
        callback = state.get("stream_callback")

        full_message = f"{context}\n\n{instruction}\n\nUser question: {message}"
        history = state.get("conversation_history", [])[-_get_chat_settings().CHAT_MAX_HISTORY:]

        provider = get_vlm_provider()

        # Use a single event loop for all async provider calls
        # to avoid httpx.AsyncClient being bound to a closed loop
        async def _run_reasoning():
            return await provider.chat(
                images=page_images,
                message=full_message,
                history=history,
                system_prompt=GROUNDING_SYSTEM_PROMPT,
            )

        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(_run_reasoning())
        finally:
            loop.close()

        answer = response.content if hasattr(response, "content") else response.get("content", "")

        # Stream tokens via callback
        if callback and answer:
            callback("token", content=answer)

        return {"raw_answer": answer}

    except Exception as e:
        logger.error("reason_node_error: %s", e, exc_info=True)
        return {"raw_answer": "I encountered an error while processing your question. Please try again."}


# --- Citation extraction ---

def _extract_page_references(answer: str) -> list[int]:
    """Extract page number references from answer text.

    Matches patterns like "page 1", "p. 2", "p2".

    Args:
        answer: The generated answer text.

    Returns:
        Sorted, deduplicated list of page numbers.
    """
    pattern = r'\bpage\s+(\d+)\b|\bp\.?\s*(\d+)\b'
    matches = re.findall(pattern, answer, re.IGNORECASE)
    pages: set[int] = set()
    for groups in matches:
        for g in groups:
            if g:
                pages.add(int(g))
    return sorted(pages)


def _match_citations(
    answer: str, relevant_fields: list[dict]
) -> list[Citation]:
    """Match field values in the answer to generate citations.

    Args:
        answer: The generated answer text.
        relevant_fields: Fields from retrieval.

    Returns:
        Deduplicated list of Citation dicts.
    """
    if not answer or not relevant_fields:
        return []

    citations: list[Citation] = []
    seen: set[str] = set()
    answer_lower = answer.lower()

    # Match field values in answer
    for f in relevant_fields:
        value = f.get("field_value", "")
        if len(value) < 2:
            continue

        if value.lower() in answer_lower:
            dedup_key = f"{f.get('page_number', 0)}:{value}"
            if dedup_key not in seen:
                seen.add(dedup_key)
                citations.append(Citation(
                    page=f.get("page_number", 1),
                    bounding_box=f.get("bounding_box", {}),
                    text_span=value,
                ))

    # Match page references to fields
    page_refs = _extract_page_references(answer)
    for page in page_refs:
        for f in relevant_fields:
            if f.get("page_number") == page:
                value = f.get("field_value", "")
                dedup_key = f"{page}:{value}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    citations.append(Citation(
                        page=page,
                        bounding_box=f.get("bounding_box", {}),
                        text_span=value,
                    ))

    return citations


def cite_node(state: dict) -> dict:
    """Extract citations from the answer and relevant fields.

    Matches field values in the answer text, extracts page references,
    and streams citation events via callback.

    Args:
        state: ChatState dict with raw_answer, relevant_fields.

    Returns:
        State update with answer and citations.
    """
    answer = state.get("raw_answer", "")
    fields = state.get("relevant_fields", [])
    callback = state.get("stream_callback")

    citations = _match_citations(answer, fields)

    if callback:
        for c in citations:
            callback("citation", citation=c)
        callback("done")

    return {"answer": answer, "citations": citations}


# --- Graph wiring ---

def build_chat_graph():
    """Build and compile the LangGraph chat pipeline.

    Graph: router -> retrieve -> reason -> cite -> END.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(ChatState)
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("reason", reason_node)
    graph.add_node("cite", cite_node)

    graph.set_entry_point("router")
    graph.add_edge("router", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "cite")
    graph.add_edge("cite", END)

    return graph.compile()


chat_graph = build_chat_graph()


def run_chat_pipeline(initial_state: dict, config: dict | None = None) -> dict:
    """Run the full chat pipeline.

    Args:
        initial_state: ChatState dict with document data and message.
        config: Optional LangGraph config.

    Returns:
        Final state dict after all nodes have executed.
    """
    return chat_graph.invoke(initial_state, config=config)
