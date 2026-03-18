"""
docmind/library/pipeline/chat.py

LangGraph StateGraph for the document chat agent.

Nodes: router -> retrieve -> reason -> cite -> END.
"""

import re
from typing import Any, Callable, TypedDict

from docmind.core.logging import get_logger

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

_LOW_CONFIDENCE_THRESHOLD = 0.6
_MAX_REQUERY_FIELDS = 3


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
            if f.get("confidence", 1.0) < _LOW_CONFIDENCE_THRESHOLD
        ]
        for f in low_conf[:_MAX_REQUERY_FIELDS]:
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


# --- Placeholder nodes (implemented in #24) ---

def reason_node(state: dict) -> dict:
    """Generate answer from relevant fields (placeholder).

    Args:
        state: ChatState dict.

    Returns:
        State update with raw_answer and answer.
    """
    fields = state.get("relevant_fields", [])
    message = state.get("message", "")

    if not fields:
        answer = "I couldn't find relevant information in this document to answer your question."
    else:
        field_info = "; ".join(
            f"{f.get('field_key', '')}: {f.get('field_value', '')}"
            for f in fields[:5]
        )
        answer = f"Based on the document: {field_info}"

    return {"raw_answer": answer, "answer": answer}


def cite_node(state: dict) -> dict:
    """Generate citations from relevant fields (placeholder).

    Args:
        state: ChatState dict.

    Returns:
        State update with citations.
    """
    fields = state.get("relevant_fields", [])
    citations: list[Citation] = []

    for f in fields:
        bbox = f.get("bounding_box", {})
        if bbox:
            citations.append(Citation(
                page=f.get("page_number", 1),
                bounding_box=bbox,
                text_span=f"{f.get('field_key', '')}: {f.get('field_value', '')}",
            ))

    return {"citations": citations}


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
