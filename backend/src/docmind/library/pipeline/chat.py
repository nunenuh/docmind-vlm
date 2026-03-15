"""
docmind/library/pipeline/chat.py

LangGraph StateGraph for the document chat agent.
Stub implementation for scaffold.
"""

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


def run_chat_pipeline(initial_state: dict, config: dict) -> dict:
    """
    Run the full chat pipeline.
    Stub implementation — raises NotImplementedError.
    """
    raise NotImplementedError("Chat pipeline not yet implemented")
