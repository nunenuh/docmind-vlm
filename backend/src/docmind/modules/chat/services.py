"""
docmind/modules/chat/services.py

Chat service — VLM interaction, prompt building, context formatting.
Usecase delegates all VLM/library calls here.
"""

from typing import AsyncGenerator

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.providers.factory import get_vlm_provider

logger = get_logger(__name__)

DOCUMENT_CHAT_SYSTEM_PROMPT = """You are a document analysis assistant. You MUST answer based ONLY on the extracted data and document context provided below.

EXTRACTED FIELDS:
{fields_text}

INSTRUCTIONS:
- Answer questions about the document using ONLY the extracted fields above
- If a field has low confidence (<0.5), mention that the value might be uncertain
- If asked about something not in the extracted fields, say you don't have that information
- Be precise and cite specific field values
- For Indonesian documents (KTP, KK, etc.), use the correct Indonesian field names"""


class ChatService:
    """VLM interaction + prompt building for per-document chat."""

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()

    def format_extracted_fields(self, fields: list[dict]) -> str:
        """Format extracted fields as text for the system prompt."""
        if not fields:
            return "No fields have been extracted yet. The document has not been processed."

        lines = []
        for f in fields:
            conf = f.get("confidence", 0)
            conf_label = "HIGH" if conf >= 0.8 else "MEDIUM" if conf >= 0.5 else "LOW"
            value = f.get("field_value", "N/A") or "N/A"
            key = f.get("field_key", "unknown")
            lines.append(f"- {key}: {value} (confidence: {conf_label}, {conf:.0%})")

        return "\n".join(lines)

    def build_system_prompt(self, fields_text: str) -> str:
        """Build the system prompt with extracted fields."""
        return DOCUMENT_CHAT_SYSTEM_PROMPT.format(fields_text=fields_text)

    def get_history_slice(self, history: list[dict]) -> list[dict]:
        """Get the most recent conversation turns."""
        limit = self._settings.CHAT_MAX_HISTORY
        return history[-limit:] if len(history) > limit else history

    async def stream_chat(
        self,
        message: str,
        system_prompt: str,
        history: list[dict],
        document_image=None,
    ) -> AsyncGenerator[dict, None]:
        """Stream VLM chat response with thinking.

        Args:
            message: User message.
            system_prompt: System prompt with extracted fields.
            history: Conversation history.
            document_image: Optional OpenCV image for visual grounding.

        Yields dicts: {"type": "thinking"|"answer"|"done", "content": "..."}
        """
        provider = get_vlm_provider()
        images = [document_image] if document_image is not None else []

        async for event in provider.chat_stream(
            images=images,
            message=message,
            history=history,
            system_prompt=system_prompt,
            enable_thinking=self._settings.ENABLE_THINKING,
        ):
            yield event
