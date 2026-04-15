"""
docmind/library/providers/factory.py

Factory function for creating VLM provider instances.

Provider selection is driven by the VLM_PROVIDER environment variable,
or by user-level overrides passed via UserProviderOverride.
"""

import logging
from dataclasses import dataclass

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider

logger = logging.getLogger(__name__)

# Provider registry — maps env var values to constructor callables.
# Module-level singleton; classes are cached after first lazy import.
_PROVIDER_REGISTRY: dict[str, type] = {}


@dataclass(frozen=True)
class UserProviderOverride:
    """User-level provider override. API key must already be decrypted."""

    provider_name: str
    api_key: str
    model_name: str
    base_url: str | None = None


def register_provider(name: str, cls: type) -> None:
    """Register a provider class in the factory registry.

    Args:
        name: Provider name matching VLM_PROVIDER env var value.
        cls: Provider class to register.
    """
    _PROVIDER_REGISTRY[name] = cls


def _ensure_registered(provider_name: str) -> None:
    """Lazily import and register a provider class if not already registered."""
    if provider_name == "openrouter" and "openrouter" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.openrouter import OpenRouterProvider

        register_provider("openrouter", OpenRouterProvider)
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


def get_vlm_provider(
    override: UserProviderOverride | None = None,
) -> VLMProvider:
    """Create and return a VLM provider.

    If an override is provided, instantiate the specified provider with
    the user's decrypted API key and model. Otherwise, fall back to the
    system default from get_settings().

    Args:
        override: Optional user-level provider config (already decrypted).

    Returns:
        Configured VLMProvider instance.

    Raises:
        ValueError: If provider name is not set or not recognized.
        RuntimeError: If the provider's required env vars are missing.
    """
    if override is not None:
        provider_name = override.provider_name
        _ensure_registered(provider_name)
        provider_cls = _PROVIDER_REGISTRY.get(provider_name)
        if provider_cls is None:
            available = list(_PROVIDER_REGISTRY.keys())
            raise ValueError(
                f"Unknown VLM provider: '{provider_name}'. Available: {available}"
            )
        logger.info("Creating user-override VLM provider: %s", provider_name)
        return provider_cls(
            api_key=override.api_key,
            model_name=override.model_name,
            base_url=override.base_url,
        )

    settings = get_settings()
    provider_name = settings.VLM_PROVIDER
    if not provider_name:
        raise ValueError(
            "VLM_PROVIDER is not set. Options: dashscope, openai, google, ollama"
        )

    _ensure_registered(provider_name)

    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        available = list(_PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown VLM provider: '{provider_name}'. Available: {available}"
        )
    logger.info("Creating VLM provider: %s", provider_name)
    return provider_cls()
