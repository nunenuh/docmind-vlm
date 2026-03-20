# Backend Spec: Chat Agent Pipeline

File: `backend/src/docmind/library/pipeline/chat.py`

Library dependencies: `backend/src/docmind/library/providers/`

See also: [[projects/docmind-vlm/specs/backend/providers]] · [[projects/docmind-vlm/specs/backend/services]]

---

## Responsibility

| Component | Does |
|-----------|------|
| `docmind/library/pipeline/chat.py` | LangGraph StateGraph definition — nodes, edges, state schema, checkpointer |
| `router_node` (in same file) | Intent classification (factual, reasoning, summarization, comparison) |
| `retrieve_node` (in same file) | Search extracted fields + optional VLM re-query on specific region |
| `reason_node` (in same file) | Grounded answer generation with document-only constraint |
| `cite_node` (in same file) | Citation extraction and bounding box matching |

The chat pipeline **never** imports from `docmind/modules/` — it communicates through state and SSE callbacks only. It lives under `library/pipeline/` because it is reusable logic, invoked by `modules/chat/usecase.py`.

---

## Imports

```python
# From module usecase or service layer:
from docmind.library.pipeline import run_chat_pipeline

# Internal imports within pipeline:
from docmind.library.providers import get_vlm_provider
from docmind.core.config import get_settings
from docmind.core.logging import get_logger
```

---

## Pipeline Overview

```
User message + document context
    |
    v  router node
intent: str (factual_lookup | reasoning | summarization | comparison)
    |
    v  retrieve node
relevant_fields: list[dict], re_queried_regions: list[dict]
    |
    v  reason node
raw_answer: str (grounded in document data only)
    |
    v  cite node
answer: str, citations: list[Citation]
    |
    v
ChatState with final response ready for SSE streaming
```

---

## `library/pipeline/chat.py`

```python
"""
docmind/library/pipeline/chat.py

LangGraph StateGraph for the document chat agent.

Defines the chat state schema and wires together the four
pipeline nodes: router -> retrieve -> reason -> cite.

Uses LangGraph checkpointer for conversation memory persistence.
"""
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class Citation(TypedDict):
    """Citation linking answer text to a document region."""
    page: int
    bounding_box: dict  # {x, y, width, height}
    text_span: str


class ChatState(TypedDict):
    """
    Full state flowing through the chat pipeline.

    Conversation history is managed by LangGraph's checkpointer,
    so only the current turn's data flows through the graph.
    """
    # Input (set before pipeline starts)
    document_id: str
    user_id: str
    message: str
    page_images: list[Any]  # list[np.ndarray]
    extracted_fields: list[dict]
    conversation_history: list[dict]  # [{"role": str, "content": str}, ...]

    # Router output
    intent: str  # factual_lookup, reasoning, summarization, comparison
    intent_confidence: float

    # Retrieve output
    relevant_fields: list[dict]
    re_queried_regions: list[dict]  # VLM re-query results for specific regions

    # Reason output
    raw_answer: str

    # Cite output
    answer: str
    citations: list[Citation]

    # Pipeline metadata
    error_message: str | None
    stream_callback: Callable | None  # SSE token streaming callback


def build_chat_graph() -> StateGraph:
    """
    Build and compile the document chat StateGraph.

    Pipeline flow:
        router -> retrieve -> reason -> cite -> END

    Uses MemorySaver checkpointer for conversation persistence.
    Each invocation with the same thread_id resumes the conversation.

    Returns:
        Compiled LangGraph StateGraph with checkpointer.
    """
    graph = StateGraph(ChatState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("reason", reason_node)
    graph.add_node("cite", cite_node)

    # Set entry point
    graph.set_entry_point("router")

    # Linear flow: router -> retrieve -> reason -> cite -> END
    graph.add_edge("router", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "cite")
    graph.add_edge("cite", END)

    # Compile with checkpointer for conversation memory
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Module-level compiled graph (reused across invocations)
chat_graph = build_chat_graph()


def run_chat_pipeline(initial_state: dict, config: dict) -> dict:
    """
    Run the full chat pipeline.

    This is the main entry point called by modules/chat/usecase.py.

    Args:
        initial_state: ChatState dict with input fields populated.
        config: LangGraph config with thread_id for conversation isolation.

    Returns:
        Final ChatState dict with all outputs.
    """
    return chat_graph.invoke(initial_state, config=config)
```

**Graph Rules:**
- Linear flow (no conditional edges) — all four nodes always run
- Checkpointer uses `MemorySaver` (in-memory) for development; replace with `PostgresSaver` for production
- Thread ID format: `"{document_id}:{user_id}"` — one conversation per user per document
- Conversation history is loaded from checkpointer, not passed from API

---

## `router_node`

```python
"""
Intent classification node.

Classifies the user's message into one of four intent categories
to guide retrieval and reasoning strategies.
"""
import re

# Intent categories and their retrieval/reasoning strategies
INTENTS = {
    "factual_lookup": {
        "description": "Direct fact retrieval from extracted fields",
        "retrieval": "exact_match",
        "reasoning": "direct_answer",
    },
    "reasoning": {
        "description": "Requires inference or calculation from multiple fields",
        "retrieval": "multi_field",
        "reasoning": "chain_of_thought",
    },
    "summarization": {
        "description": "Summarize document content or sections",
        "retrieval": "broad_scan",
        "reasoning": "synthesize",
    },
    "comparison": {
        "description": "Compare values, fields, or sections within the document",
        "retrieval": "multi_field",
        "reasoning": "comparative",
    },
}

# Keyword patterns for rule-based intent classification
INTENT_PATTERNS = {
    "factual_lookup": [
        r"\bwhat is\b", r"\bwhat's\b", r"\bhow much\b", r"\bwhen\b",
        r"\bwho\b", r"\bwhich\b", r"\bfind\b", r"\blook up\b",
        r"\btell me the\b", r"\bwhat does .+ say\b",
    ],
    "reasoning": [
        r"\bwhy\b", r"\bhow does\b", r"\bexplain\b", r"\bcalculate\b",
        r"\bwhat would\b", r"\bif\b.+\bthen\b", r"\bimplies?\b",
        r"\bconsequence\b", r"\bmean(s|ing)?\b",
    ],
    "summarization": [
        r"\bsummar(y|ize)\b", r"\boverview\b", r"\bmain points\b",
        r"\bkey (findings|takeaways|points)\b", r"\btl;?dr\b",
        r"\bbrief(ly)?\b", r"\bhighlight\b",
    ],
    "comparison": [
        r"\bcompar(e|ison)\b", r"\bdifference\b", r"\bvs\.?\b",
        r"\bversus\b", r"\bbetween\b.+\band\b", r"\bmore than\b",
        r"\bless than\b", r"\bhigher|lower\b",
    ],
}


def _classify_intent(message: str) -> tuple[str, float]:
    """
    Classify user message intent using pattern matching.

    Uses regex patterns to score each intent category.
    Falls back to "factual_lookup" with low confidence if no patterns match.
    """
    message_lower = message.lower().strip()
    scores: dict[str, int] = {intent: 0 for intent in INTENTS}

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                scores[intent] += 1

    total_matches = sum(scores.values())

    if total_matches == 0:
        return "factual_lookup", 0.3  # Default with low confidence

    best_intent = max(scores, key=scores.get)
    confidence = scores[best_intent] / max(total_matches, 1)

    # Boost confidence if only one intent matched
    if sum(1 for s in scores.values() if s > 0) == 1:
        confidence = min(confidence + 0.3, 1.0)

    return best_intent, round(confidence, 2)


def router_node(state: dict) -> dict:
    """
    Pipeline node: classify user intent.

    Analyzes the user's message to determine the best retrieval
    and reasoning strategy.
    """
    message = state["message"]
    intent, confidence = _classify_intent(message)

    logger.info(
        "Intent classified",
        intent=intent,
        confidence=confidence,
        message_preview=message[:80],
    )

    return {
        "intent": intent,
        "intent_confidence": confidence,
    }
```

**Router Rules:**
- Pattern-based classification is fast and deterministic — no VLM call needed
- Default intent is `factual_lookup` with low confidence (0.3)
- Confidence boost when only one intent category matches
- Future improvement: replace patterns with VLM-based classification for ambiguous queries

---

## `retrieve_node`

```python
"""
Retrieval node: find relevant extracted fields and optionally
re-query the VLM for specific document regions.
"""
from typing import Any


def _search_fields(
    fields: list[dict],
    query: str,
    intent: str,
) -> list[dict]:
    """
    Search extracted fields for relevance to the query.

    Uses simple keyword matching on field keys and values.
    Returns fields sorted by relevance score (descending).
    """
    query_lower = query.lower()
    query_terms = set(query_lower.split())
    scored_fields: list[tuple[float, dict]] = []

    for field in fields:
        score = 0.0
        field_key = (field.get("field_key") or "").lower()
        field_value = (field.get("field_value") or "").lower()

        # Exact key match
        if field_key and field_key in query_lower:
            score += 1.0

        # Term overlap with key
        key_terms = set(field_key.split("_"))
        key_overlap = len(query_terms & key_terms)
        score += key_overlap * 0.5

        # Term overlap with value
        value_terms = set(field_value.split())
        value_overlap = len(query_terms & value_terms)
        score += value_overlap * 0.3

        # Boost required fields for factual lookups
        if intent == "factual_lookup" and field.get("is_required"):
            score += 0.2

        if score > 0:
            scored_fields.append((score, field))

    # Sort by score descending
    scored_fields.sort(key=lambda x: x[0], reverse=True)

    # Limit based on intent
    max_fields = {
        "factual_lookup": 5,
        "reasoning": 10,
        "summarization": 20,
        "comparison": 15,
    }
    limit = max_fields.get(intent, 10)

    return [field for _, field in scored_fields[:limit]]


async def _re_query_region(
    page_images: list[Any],
    field: dict,
    question: str,
) -> dict | None:
    """
    Re-query the VLM on a specific document region for more detail.

    Crops the page image to the field's bounding box area (with padding)
    and asks the VLM for more detailed extraction.
    """
    import cv2
    import numpy as np
    from docmind.library.providers import get_vlm_provider

    bbox = field.get("bounding_box", {})
    page_num = field.get("page_number", 1) - 1  # 0-indexed

    if not bbox or page_num >= len(page_images) or page_num < 0:
        return None

    image = page_images[page_num]
    h, w = image.shape[:2]

    # Extract region with 20% padding
    padding = 0.2
    x = max(0, int((bbox.get("x", 0) - padding) * w))
    y = max(0, int((bbox.get("y", 0) - padding) * h))
    x2 = min(w, int((bbox.get("x", 0) + bbox.get("width", 0) + padding) * w))
    y2 = min(h, int((bbox.get("y", 0) + bbox.get("height", 0) + padding) * h))

    region = image[y:y2, x:x2]

    if region.size == 0:
        return None

    provider = get_vlm_provider()
    prompt = (
        f"Look at this specific region of the document and answer: {question}\n"
        f"Context: this region contains the field '{field.get('field_key', 'unknown')}' "
        f"with value '{field.get('field_value', '')}'. "
        "Provide additional detail or clarification if visible."
    )

    response = await provider.extract(images=[region], prompt=prompt)

    return {
        "field_key": field.get("field_key"),
        "original_value": field.get("field_value"),
        "detailed_value": response["content"],
        "page_number": field.get("page_number"),
        "bounding_box": bbox,
    }


def retrieve_node(state: dict) -> dict:
    """
    Pipeline node: retrieve relevant context for the user's question.

    Steps:
    1. Search extracted fields by keyword relevance
    2. For factual lookups with low-confidence matches, re-query VLM
       on the specific document region
    """
    message = state["message"]
    intent = state["intent"]
    extracted_fields = state.get("extracted_fields", [])
    page_images = state.get("page_images", [])

    # Step 1: Search extracted fields
    relevant_fields = _search_fields(extracted_fields, message, intent)

    logger.info(
        "Retrieved relevant fields",
        field_count=len(relevant_fields),
        intent=intent,
    )

    # Step 2: Optional VLM re-query for low-confidence factual lookups
    re_queried_regions: list[dict] = []

    if intent == "factual_lookup" and page_images:
        import asyncio
        for field in relevant_fields[:3]:  # Re-query top 3 at most
            if field.get("confidence", 1.0) < 0.6:
                result = asyncio.get_event_loop().run_until_complete(
                    _re_query_region(page_images, field, message)
                )
                if result:
                    re_queried_regions.append(result)

    return {
        "relevant_fields": relevant_fields,
        "re_queried_regions": re_queried_regions,
    }
```

---

## `reason_node`

```python
"""
Reasoning node: generate a grounded answer using VLM.

The answer MUST be grounded in document data only. The system prompt
enforces this constraint strictly.
"""
from docmind.library.providers import get_vlm_provider


# Grounding System Prompt
GROUNDING_SYSTEM_PROMPT = """You are a document analysis assistant. You answer questions about a specific document the user has uploaded.

CRITICAL RULES:
1. ONLY answer based on information visible in the document images and extracted data provided below.
2. NEVER use external knowledge, training data, or assumptions not supported by the document.
3. If the document does not contain enough information to answer the question, say: "I cannot find this information in the document."
4. When referencing specific values, mention which page and region they come from.
5. If a field has low confidence (< 0.5), mention that the value may be uncertain due to image quality.
6. For calculations, show your work step by step using only values from the document.
7. Do not hallucinate or infer values that are not explicitly present.

RESPONSE FORMAT:
- Be concise and direct.
- Use the extracted field data as your primary source.
- Reference page numbers when citing specific information.
- If multiple interpretations exist, present the most likely one and note the uncertainty."""


def _build_context(state: dict) -> str:
    """Build the document context string for the reasoning prompt."""
    lines = ["EXTRACTED DOCUMENT DATA:"]

    for field in state.get("relevant_fields", []):
        key = field.get("field_key", "text")
        value = field.get("field_value", "")
        page = field.get("page_number", "?")
        conf = field.get("confidence", 0.0)
        conf_label = "high" if conf >= 0.8 else "medium" if conf >= 0.5 else "LOW"

        lines.append(f"- [{key}] = \"{value}\" (page {page}, confidence: {conf_label})")

    # Include re-queried regions if available
    re_queried = state.get("re_queried_regions", [])
    if re_queried:
        lines.append("")
        lines.append("DETAILED RE-ANALYSIS:")
        for region in re_queried:
            lines.append(
                f"- [{region['field_key']}] detailed reading: \"{region['detailed_value']}\" "
                f"(page {region['page_number']})"
            )

    # Include conversation history for context
    history = state.get("conversation_history", [])
    if history:
        lines.append("")
        lines.append("CONVERSATION HISTORY:")
        for msg in history[-6:]:  # Last 6 messages max
            role = msg["role"].upper()
            content = msg["content"][:200]  # Truncate long messages
            lines.append(f"[{role}]: {content}")

    return "\n".join(lines)


def _get_reasoning_instruction(intent: str) -> str:
    """Get intent-specific reasoning instructions."""
    instructions = {
        "factual_lookup": (
            "The user is looking for a specific fact. Find and return the "
            "exact value from the extracted data. Be precise."
        ),
        "reasoning": (
            "The user needs you to reason about the document content. "
            "Think step by step, showing your reasoning chain. "
            "Only use values explicitly present in the document."
        ),
        "summarization": (
            "The user wants a summary. Synthesize the key information "
            "from the extracted data into a concise overview. "
            "Cover the most important fields and their values."
        ),
        "comparison": (
            "The user wants to compare values or sections. "
            "Present the relevant values side by side and note "
            "similarities and differences."
        ),
    }
    return instructions.get(intent, instructions["factual_lookup"])


def reason_node(state: dict) -> dict:
    """
    Pipeline node: generate a grounded answer.

    Constructs a prompt with document context and conversation history,
    then calls the VLM to generate an answer grounded in document data.

    If a stream_callback is provided, streams tokens as they arrive.
    """
    import asyncio

    message = state["message"]
    intent = state["intent"]
    page_images = state.get("page_images", [])
    history = state.get("conversation_history", [])
    stream_callback = state.get("stream_callback")

    context = _build_context(state)
    reasoning_instruction = _get_reasoning_instruction(intent)

    user_prompt = f"""{context}

TASK: {reasoning_instruction}

USER QUESTION: {message}"""

    try:
        provider = get_vlm_provider()

        response = asyncio.get_event_loop().run_until_complete(
            provider.chat(
                images=page_images[:4],  # Limit to 4 pages for token efficiency
                message=user_prompt,
                history=history,
                system_prompt=GROUNDING_SYSTEM_PROMPT,
            )
        )

        raw_answer = response["content"]

        # Stream tokens if callback is provided
        if stream_callback:
            # In production, use streaming API and call per-token
            # For now, simulate by splitting on spaces
            for token in raw_answer.split(" "):
                stream_callback(type="token", content=token + " ")

        logger.info("Generated answer", char_count=len(raw_answer), intent=intent)

        return {"raw_answer": raw_answer}

    except Exception as e:
        logger.error("Reasoning failed", error=str(e))
        return {
            "raw_answer": "I encountered an error while analyzing the document. Please try again.",
            "error_message": str(e),
        }
```

**Grounding Rules (enforced by system prompt):**
- ONLY answer from document content — never use external knowledge
- Explicitly state when information is not found in the document
- Flag low-confidence values (< 0.5) as uncertain
- Show calculation work using only document values
- Reference page numbers for all cited information
- Limit conversation history to last 6 messages for context window efficiency
- Limit page images to 4 for token efficiency

---

## `cite_node`

```python
"""
Citation node: extract citations from the answer and match them
to document regions (bounding boxes).
"""
import re


def _extract_page_references(answer: str) -> list[int]:
    """Extract page number references from the answer text."""
    patterns = [
        r"page\s+(\d+)",
        r"p\.\s*(\d+)",
        r"p(\d+)",
    ]

    pages = set()
    for pattern in patterns:
        for match in re.finditer(pattern, answer, re.IGNORECASE):
            pages.add(int(match.group(1)))

    return sorted(pages)


def _match_citations(
    answer: str,
    relevant_fields: list[dict],
) -> list[dict]:
    """
    Match answer content to extracted fields to generate citations.

    For each relevant field whose value appears in the answer,
    creates a citation with the field's bounding box.
    """
    citations: list[dict] = []
    seen_spans: set[str] = set()  # Deduplicate

    for field in relevant_fields:
        field_value = field.get("field_value", "")
        if not field_value or len(field_value) < 2:
            continue

        # Check if the field value appears in the answer
        if field_value.lower() in answer.lower():
            span_key = f"{field.get('page_number')}:{field_value}"
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)

            citations.append({
                "page": field.get("page_number", 1),
                "bounding_box": field.get("bounding_box", {}),
                "text_span": field_value,
            })

    # Also add citations for page references without specific field matches
    referenced_pages = _extract_page_references(answer)
    cited_pages = {c["page"] for c in citations}

    for page_num in referenced_pages:
        if page_num not in cited_pages:
            # Find any field on that page to use as an anchor
            page_fields = [
                f for f in relevant_fields
                if f.get("page_number") == page_num
            ]
            if page_fields:
                best_field = max(page_fields, key=lambda f: f.get("confidence", 0))
                citations.append({
                    "page": page_num,
                    "bounding_box": best_field.get("bounding_box", {}),
                    "text_span": best_field.get("field_value", ""),
                })

    return citations


def cite_node(state: dict) -> dict:
    """
    Pipeline node: extract citations from the answer.

    Matches answer content to extracted fields to create clickable
    citations that link to specific document regions.
    """
    raw_answer = state.get("raw_answer", "")
    relevant_fields = state.get("relevant_fields", [])
    stream_callback = state.get("stream_callback")

    citations = _match_citations(raw_answer, relevant_fields)

    logger.info("Generated citations", citation_count=len(citations))

    # Stream citations if callback is provided
    if stream_callback:
        for citation in citations:
            stream_callback(type="citation", citation=citation)
        stream_callback(type="done", message_id="pending")  # ID set by usecase layer

    return {
        "answer": raw_answer,
        "citations": citations,
    }
```

---

## `library/pipeline/__init__.py`

```python
"""
docmind/library/pipeline/__init__.py

Re-exports for convenient access to pipeline entry points.
"""
from .processing import run_processing_pipeline
from .chat import run_chat_pipeline
```

---

## Memory: LangGraph Checkpointer

Conversation state is persisted using LangGraph's checkpointer:

```python
# Thread ID format for conversation isolation
thread_id = f"{document_id}:{user_id}"

# Invoke with thread config
config = {"configurable": {"thread_id": thread_id}}
result = chat_graph.invoke(initial_state, config=config)
```

**Checkpointer behavior:**
- Each `(document_id, user_id)` pair gets its own conversation thread
- History accumulates across invocations with the same thread ID
- `MemorySaver` is used for development (in-memory, lost on restart)
- Production should use `PostgresSaver` for persistence

---

## SSE Streaming Pattern

The chat pipeline streams tokens and citations via SSE:

```python
import asyncio
import json
from typing import AsyncGenerator

from docmind.library.pipeline import run_chat_pipeline


async def chat_sse_stream(
    document_id: str,
    user_id: str,
    message: str,
    page_images: list,
    extracted_fields: list[dict],
    conversation_history: list[dict],
) -> AsyncGenerator[str, None]:
    """Create an SSE stream for chat responses."""
    token_queue: asyncio.Queue = asyncio.Queue()

    def on_stream(type: str, **kwargs) -> None:
        token_queue.put_nowait({"type": type, **kwargs})

    initial_state = {
        "document_id": document_id,
        "user_id": user_id,
        "message": message,
        "page_images": page_images,
        "extracted_fields": extracted_fields,
        "conversation_history": conversation_history,
        "stream_callback": on_stream,
    }

    config = {"configurable": {"thread_id": f"{document_id}:{user_id}"}}
    task = asyncio.create_task(
        asyncio.to_thread(run_chat_pipeline, initial_state, config)
    )

    while not task.done():
        try:
            event = await asyncio.wait_for(token_queue.get(), timeout=30.0)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
```

**SSE event types:**

| Event type | Payload | When |
|------------|---------|------|
| `token` | `{"type": "token", "content": "The "}` | Each answer token |
| `citation` | `{"type": "citation", "citation": {...}}` | After answer generation |
| `done` | `{"type": "done", "message_id": "uuid"}` | Pipeline complete |
| `heartbeat` | `{"type": "heartbeat"}` | Every 30s if no events |
| `error` | `{"type": "error", "message": "..."}` | On pipeline failure |

---

## Rules

- **Chat pipeline never imports from `docmind/modules/`** — communication is through state and SSE callbacks.
- **Grounding is non-negotiable**: the system prompt strictly forbids external knowledge. If the document does not contain the answer, say so.
- **Citations must reference real document regions**: every citation must have a valid bounding box from an extracted field.
- **Conversation history is capped at 6 messages** in the reasoning prompt to manage token usage.
- **Page images are capped at 4** when sent to VLM for chat to manage token costs.
- **Re-querying is limited to 3 fields per turn** and only for factual lookups with low confidence (< 0.6).
- **Thread isolation**: each `(document_id, user_id)` pair is a separate conversation. No cross-contamination.
- **Stream callbacks are optional**: all nodes must work without a callback (for testing and batch use).

---

## Project RAG Chat Pipeline

File: `backend/src/docmind/library/pipeline/project_chat.py`

This is a **separate pipeline** from the per-document VLM chat above. It provides multi-document RAG chat within a project, using text embeddings and pgvector similarity search instead of VLM image analysis.

### Key Differences from Per-Document Chat

| Aspect | Per-Document Chat (above) | Project RAG Chat |
|--------|--------------------------|-----------------|
| Input | Single document images + extracted fields | Multiple documents' text chunks |
| Retrieval | Keyword search on extracted fields + VLM re-query | pgvector similarity search across page_chunks |
| Model | VLM provider (vision + language) | Embedding provider + LLM (text only) |
| Citations | Bounding boxes on document image | Document name + page number |
| Persona | Fixed grounding system prompt | Configurable persona system prompt |
| Scope | One document per conversation | All documents in a project |

---

### State Schema

```python
class ProjectChatState(TypedDict):
    """
    Full state flowing through the project RAG chat pipeline.

    Unlike the per-document ChatState, this pipeline operates on
    text chunks from multiple documents within a project.
    """
    # Input (set before pipeline starts)
    project_id: str
    user_id: str
    conversation_id: str
    message: str
    persona_prompt: str  # Persona system prompt (from persona config)

    # Embed output
    query_embedding: list[float]  # Vector embedding of user message

    # Retrieve output
    retrieved_chunks: list[dict]  # [{document_id, document_name, page_number, chunk_text, score}, ...]

    # Conversation context
    conversation_history: list[dict]  # [{"role": str, "content": str}, ...]

    # Reason output
    answer: str

    # Cite output
    citations: list[dict]  # [{document_name, page_number, chunk_text}, ...]

    # Pipeline metadata
    status: str  # "pending" | "embedding" | "retrieving" | "reasoning" | "citing" | "done" | "error"
    error_message: str | None
```

---

### Pipeline Overview

```
User message + persona prompt + conversation history
    |
    v  embed_query node
query_embedding: list[float]
    |
    v  retrieve node
retrieved_chunks: list[dict] (pgvector similarity search across project's page_chunks)
    |
    v  reason node
answer: str (persona prompt + retrieved context + history → LLM)
    |
    v  cite node
citations: list[dict] (document name + page number extracted from answer)
    |
    v
ProjectChatState with final response ready for SSE streaming
```

---

### `embed_query` Node

```python
"""
Embedding node: convert user message to a vector embedding.

Uses the configured embedding provider (e.g., OpenAI text-embedding-3-small,
DashScope embedding) to produce a dense vector for similarity search.
"""
from docmind.library.providers import get_embedding_provider


def embed_query_node(state: dict) -> dict:
    """
    Pipeline node: embed the user's message.

    Calls the embedding provider to convert the message into a
    dense vector for pgvector similarity search.
    """
    message = state["message"]
    provider = get_embedding_provider()

    embedding = provider.embed(message)

    logger.info("Embedded query", dimensions=len(embedding))

    return {
        "query_embedding": embedding,
        "status": "embedding",
    }
```

---

### `retrieve` Node

```python
"""
Retrieval node: pgvector similarity search across the project's page_chunks.

Queries the page_chunks table for chunks belonging to documents in the
project, ranked by cosine similarity to the query embedding.
"""
from docmind.core.database import get_async_session


async def _pgvector_search(
    project_id: str,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[dict]:
    """
    Search page_chunks by cosine similarity within a project.

    Joins page_chunks → documents to filter by project_id.
    Returns top_k chunks sorted by similarity score descending.
    """
    async with get_async_session() as session:
        # pgvector cosine similarity query
        # SELECT pc.chunk_text, pc.page_number, d.filename, d.id,
        #        1 - (pc.embedding <=> :query_embedding) AS score
        # FROM page_chunks pc
        # JOIN documents d ON pc.document_id = d.id
        # WHERE d.project_id = :project_id
        # ORDER BY pc.embedding <=> :query_embedding
        # LIMIT :top_k
        ...

    return results  # [{document_id, document_name, page_number, chunk_text, score}, ...]


def retrieve_node(state: dict) -> dict:
    """
    Pipeline node: retrieve relevant chunks via pgvector similarity search.

    Searches across all documents in the project for chunks most
    similar to the user's query embedding.
    """
    import asyncio

    project_id = state["project_id"]
    query_embedding = state["query_embedding"]

    results = asyncio.get_event_loop().run_until_complete(
        _pgvector_search(project_id, query_embedding, top_k=10)
    )

    logger.info(
        "Retrieved chunks",
        chunk_count=len(results),
        project_id=project_id,
    )

    return {
        "retrieved_chunks": results,
        "status": "retrieving",
    }
```

---

### `reason` Node

```python
"""
Reasoning node: generate an answer using the persona prompt,
retrieved context, and conversation history.

Unlike the per-document reason node, this uses a text-only LLM
(no VLM/images) and prepends the persona system prompt.
"""
from docmind.library.providers import get_chat_provider


def _build_project_context(state: dict) -> str:
    """Build the retrieval context string for the reasoning prompt."""
    lines = ["RETRIEVED DOCUMENT CONTEXT:"]

    for chunk in state.get("retrieved_chunks", []):
        doc_name = chunk.get("document_name", "unknown")
        page = chunk.get("page_number", "?")
        text = chunk.get("chunk_text", "")
        score = chunk.get("score", 0.0)

        lines.append(f"- [{doc_name}, page {page}] (relevance: {score:.2f})")
        lines.append(f"  \"{text}\"")

    # Include conversation history for context
    history = state.get("conversation_history", [])
    if history:
        lines.append("")
        lines.append("CONVERSATION HISTORY:")
        for msg in history[-6:]:  # Last 6 messages max
            role = msg["role"].upper()
            content = msg["content"][:200]
            lines.append(f"[{role}]: {content}")

    return "\n".join(lines)


def reason_node(state: dict) -> dict:
    """
    Pipeline node: generate an answer grounded in retrieved chunks.

    Constructs a prompt with:
    1. Persona system prompt (defines tone, rules, boundaries)
    2. Retrieved chunk context (document name + page + text)
    3. Conversation history (last 6 messages)
    4. User message

    Calls a text LLM (not VLM) to generate the answer.
    """
    import asyncio

    message = state["message"]
    persona_prompt = state.get("persona_prompt", "You are a helpful document assistant.")
    history = state.get("conversation_history", [])

    context = _build_project_context(state)

    user_prompt = f"""{context}

USER QUESTION: {message}"""

    try:
        provider = get_chat_provider()

        response = asyncio.get_event_loop().run_until_complete(
            provider.chat(
                message=user_prompt,
                history=history,
                system_prompt=persona_prompt,
            )
        )

        answer = response["content"]

        logger.info("Generated project chat answer", char_count=len(answer))

        return {
            "answer": answer,
            "status": "reasoning",
        }

    except Exception as e:
        logger.error("Project chat reasoning failed", error=str(e))
        return {
            "answer": "I encountered an error while analyzing your documents. Please try again.",
            "error_message": str(e),
            "status": "error",
        }
```

---

### `cite` Node

```python
"""
Citation node: extract document-level citations from the answer.

Unlike the per-document cite node which produces bounding boxes,
this node produces document name + page number citations.
"""
import re


def _extract_project_citations(
    answer: str,
    retrieved_chunks: list[dict],
) -> list[dict]:
    """
    Match answer content to retrieved chunks to generate citations.

    For each retrieved chunk whose text appears in the answer,
    creates a citation with document name and page number.
    """
    citations: list[dict] = []
    seen: set[str] = set()  # Deduplicate by (document_name, page_number)

    for chunk in retrieved_chunks:
        chunk_text = chunk.get("chunk_text", "")
        if not chunk_text or len(chunk_text) < 10:
            continue

        # Check if key phrases from the chunk appear in the answer
        # Use first 50 chars as a fingerprint for matching
        fingerprint = chunk_text[:50].lower().strip()
        answer_lower = answer.lower()

        # Check for substantial overlap
        chunk_words = set(chunk_text.lower().split())
        answer_words = set(answer_lower.split())
        overlap = len(chunk_words & answer_words) / max(len(chunk_words), 1)

        if overlap > 0.3 or fingerprint in answer_lower:
            doc_name = chunk.get("document_name", "unknown")
            page = chunk.get("page_number", 1)
            key = f"{doc_name}:{page}"

            if key in seen:
                continue
            seen.add(key)

            citations.append({
                "document_name": doc_name,
                "document_id": chunk.get("document_id"),
                "page_number": page,
                "chunk_text": chunk_text[:200],  # Truncate for display
            })

    return citations


def cite_node(state: dict) -> dict:
    """
    Pipeline node: extract document citations from the answer.

    Matches answer content to retrieved chunks to create citations
    that reference specific documents and pages.
    """
    answer = state.get("answer", "")
    retrieved_chunks = state.get("retrieved_chunks", [])

    citations = _extract_project_citations(answer, retrieved_chunks)

    logger.info("Generated project citations", citation_count=len(citations))

    return {
        "citations": citations,
        "status": "done",
    }
```

---

### Graph Definition

```python
"""
Build and compile the project RAG chat StateGraph.

Pipeline flow:
    embed_query -> retrieve -> reason -> cite -> END
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph


def build_project_chat_graph() -> StateGraph:
    """
    Build the project RAG chat pipeline.

    Linear flow: embed_query -> retrieve -> reason -> cite -> END

    Uses MemorySaver checkpointer for conversation persistence.
    Each invocation with the same thread_id resumes the conversation.
    """
    graph = StateGraph(ProjectChatState)

    graph.add_node("embed_query", embed_query_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("reason", reason_node)
    graph.add_node("cite", cite_node)

    graph.set_entry_point("embed_query")

    graph.add_edge("embed_query", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "cite")
    graph.add_edge("cite", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Module-level compiled graph (reused across invocations)
project_chat_graph = build_project_chat_graph()


def run_project_chat_pipeline(initial_state: dict, config: dict) -> dict:
    """
    Run the full project RAG chat pipeline.

    Entry point called by modules/project_chat/usecase.py.

    Args:
        initial_state: ProjectChatState dict with input fields populated.
        config: LangGraph config with thread_id for conversation isolation.

    Returns:
        Final ProjectChatState dict with all outputs.
    """
    return project_chat_graph.invoke(initial_state, config=config)
```

**Thread ID format:** `"{project_id}:{user_id}:{conversation_id}"` — supports multiple conversations per user per project.

---

### Project RAG Chat Rules

- **No VLM / no images** — this pipeline is pure text RAG. It uses an embedding provider for query vectorization and a text LLM for answer generation.
- **Embedding provider, not VLM provider** — `get_embedding_provider()` returns the configured embedding model (e.g., OpenAI `text-embedding-3-small`, DashScope text embedding).
- **Retrieval from pgvector** — chunks are stored in `page_chunks` table with pgvector embeddings. Similarity search uses cosine distance (`<=>`).
- **Persona system prompt** — the persona's `system_prompt` is prepended to the LLM context, replacing the fixed grounding prompt used in per-document chat.
- **Citations reference documents, not bounding boxes** — each citation includes `document_name` and `page_number`, not pixel-level regions.
- **Multiple conversations per project** — thread ID includes `conversation_id` to support parallel conversation threads.
- **Conversation history capped at 6 messages** in the reasoning prompt, consistent with the per-document pipeline.
- **Top-k retrieval defaults to 10 chunks** — adjustable based on context window budget.
- **Pipeline never imports from `docmind/modules/`** — consistent with the per-document pipeline isolation rule.
