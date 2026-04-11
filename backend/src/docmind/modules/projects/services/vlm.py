"""Project VLM service — streaming chat via VLM provider."""

from collections.abc import AsyncGenerator

from docmind.core.config import get_settings
from docmind.library.providers.factory import UserProviderOverride, get_vlm_provider


class ProjectVLMService:
    """VLM streaming for project chat."""

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()

    async def stream_chat(
        self,
        message: str,
        system_prompt: str,
        history: list[dict],
        override: UserProviderOverride | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream VLM response with thinking."""
        provider = get_vlm_provider(override=override)
        async for event in provider.chat_stream(
            images=[],
            message=message,
            history=history[-6:],
            system_prompt=system_prompt,
            enable_thinking=self._settings.ENABLE_THINKING,
        ):
            yield event
