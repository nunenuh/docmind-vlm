"""
docmind/modules/chat/services.py

Chat service — prompt building, context formatting, field summarization.
"""

from docmind.core.config import get_settings
from docmind.core.logging import get_logger

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
    """Service for chat prompt building and context formatting."""

    @staticmethod
    def format_extracted_fields(fields: list[dict]) -> str:
        """Format extracted fields as text for the system prompt.

        Args:
            fields: List of field dicts with field_key, field_value, confidence.

        Returns:
            Formatted string of fields with confidence labels.
        """
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

    @staticmethod
    def build_system_prompt(fields_text: str) -> str:
        """Build the system prompt with extracted fields.

        Args:
            fields_text: Formatted field text from format_extracted_fields.

        Returns:
            Complete system prompt string.
        """
        return DOCUMENT_CHAT_SYSTEM_PROMPT.format(fields_text=fields_text)

    @staticmethod
    def get_recent_history_slice(history: list[dict], max_turns: int | None = None) -> list[dict]:
        """Get the most recent conversation turns.

        Args:
            history: Full conversation history.
            max_turns: Maximum number of messages to include.

        Returns:
            Sliced history list.
        """
        settings = get_settings()
        limit = max_turns or settings.CHAT_MAX_HISTORY
        return history[-limit:] if len(history) > limit else history
