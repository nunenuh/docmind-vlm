"""
docmind/library/providers/ollama.py

Ollama local model provider (skeleton).
"""

import logging

import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMResponse

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "llava:13b"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.OLLAMA_BASE_URL or DEFAULT_BASE_URL
        self._model = model_name or settings.OLLAMA_MODEL or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "Ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(
        self, images: list[np.ndarray], prompt: str, schema: dict | None = None
    ) -> VLMResponse:
        raise NotImplementedError("Ollama extract not yet implemented")

    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse:
        raise NotImplementedError("Ollama classify not yet implemented")

    async def chat(
        self,
        images: list[np.ndarray],
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> VLMResponse:
        raise NotImplementedError("Ollama chat not yet implemented")

    async def health_check(self) -> bool:
        return False
