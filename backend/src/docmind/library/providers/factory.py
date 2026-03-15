"""
docmind/library/providers/factory.py

Factory function for creating VLM provider instances.
"""

import logging

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: dict[str, type] = {}


def register_provider(name: str, cls: type) -> None:
    _PROVIDER_REGISTRY[name] = cls


def get_vlm_provider() -> VLMProvider:
    settings = get_settings()
    provider_name = settings.VLM_PROVIDER
    if not provider_name:
        raise ValueError(
            "VLM_PROVIDER is not set." " Options: dashscope, openai, google, ollama"
        )

    if provider_name == "dashscope" and "dashscope" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.dashscope import DashScopeProvider

        register_provider("dashscope", DashScopeProvider)
    if provider_name == "openai" and "openai" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.openai import OpenAIProvider

        register_provider("openai", OpenAIProvider)
    if provider_name == "google" and "google" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.google import GoogleProvider

        register_provider("google", GoogleProvider)
    if provider_name == "ollama" and "ollama" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.ollama import OllamaProvider

        register_provider("ollama", OllamaProvider)

    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        available = list(_PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown VLM provider: '{provider_name}'." f" Available: {available}"
        )
    logger.info("Creating VLM provider: %s", provider_name)
    return provider_cls()
