"""
docmind/library/providers/factory.py

Factory function for creating VLM provider instances.

Provider selection is driven by the VLM_PROVIDER environment variable.
Each provider validates its own required env vars on construction.
"""

import logging

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider

logger = logging.getLogger(__name__)

# Provider registry — maps env var values to constructor callables.
# Module-level singleton; classes are cached after first lazy import.
_PROVIDER_REGISTRY: dict[str, type] = {}


def register_provider(name: str, cls: type) -> None:
    """Register a provider class in the factory registry.

    Args:
        name: Provider name matching VLM_PROVIDER env var value.
        cls: Provider class to register.
    """
    _PROVIDER_REGISTRY[name] = cls


def get_vlm_provider() -> VLMProvider:
    """Create and return the configured VLM provider.

    Reads VLM_PROVIDER from settings to determine which provider to use.
    Lazily imports the provider class on first use, then caches it in
    the module-level registry. Each call creates a new provider instance.

    Returns:
        Configured VLMProvider instance.

    Raises:
        ValueError: If VLM_PROVIDER is not set or not recognized.
        RuntimeError: If the provider's required env vars are missing.
    """
    settings = get_settings()
    provider_name = settings.VLM_PROVIDER
    if not provider_name:
        raise ValueError(
            "VLM_PROVIDER is not set. Options: dashscope, openai, google, ollama"
        )

    # Lazy imports to avoid loading unused provider dependencies
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
            f"Unknown VLM provider: '{provider_name}'. Available: {available}"
        )
    logger.info("Creating VLM provider: %s", provider_name)
    return provider_cls()
