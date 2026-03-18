"""
Tests for docmind.library.providers.factory module.

All provider constructors are mocked to avoid needing real API keys.
Tests verify provider selection, registry management, lazy imports,
error handling, and integration with settings.
"""
from unittest.mock import MagicMock, patch

import pytest

from docmind.library.providers.factory import (
    _PROVIDER_REGISTRY,
    get_vlm_provider,
    register_provider,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registry():
    """
    Clear the provider registry before and after each test.
    This prevents test pollution from lazy import caching.
    """
    original = _PROVIDER_REGISTRY.copy()
    _PROVIDER_REGISTRY.clear()
    yield
    _PROVIDER_REGISTRY.clear()
    _PROVIDER_REGISTRY.update(original)


def _make_mock_settings(provider: str = "dashscope", **overrides) -> MagicMock:
    """Create mock settings with given VLM_PROVIDER."""
    settings = MagicMock()
    settings.VLM_PROVIDER = provider
    settings.DASHSCOPE_API_KEY = "test-key"
    settings.DASHSCOPE_MODEL = "qwen-vl-max"
    settings.OPENAI_API_KEY = "test-key"
    settings.OPENAI_MODEL = "gpt-4o"
    settings.GOOGLE_API_KEY = "test-key"
    settings.GOOGLE_MODEL = "gemini-2.0-flash"
    settings.OLLAMA_BASE_URL = "http://localhost:11434"
    settings.OLLAMA_MODEL = "llava:13b"
    for k, v in overrides.items():
        setattr(settings, k, v)
    return settings


# ---------------------------------------------------------------------------
# register_provider
# ---------------------------------------------------------------------------

class TestRegisterProvider:
    """Tests for register_provider function."""

    def test_registers_class(self) -> None:
        mock_cls = MagicMock
        register_provider("test_provider", mock_cls)
        assert "test_provider" in _PROVIDER_REGISTRY
        assert _PROVIDER_REGISTRY["test_provider"] is mock_cls

    def test_overwrites_existing(self) -> None:
        cls1 = MagicMock
        cls2 = MagicMock
        register_provider("test", cls1)
        register_provider("test", cls2)
        assert _PROVIDER_REGISTRY["test"] is cls2


# ---------------------------------------------------------------------------
# get_vlm_provider — default from settings
# ---------------------------------------------------------------------------

class TestGetVlmProviderDefault:
    """Tests for get_vlm_provider using VLM_PROVIDER from settings."""

    def test_returns_dashscope_provider(self) -> None:
        settings = _make_mock_settings("dashscope")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.dashscope.get_settings", return_value=settings):
            provider = get_vlm_provider()
            assert provider.provider_name == "DashScope"

    def test_returns_openai_provider(self) -> None:
        settings = _make_mock_settings("openai")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.openai.get_settings", return_value=settings):
            provider = get_vlm_provider()
            assert provider.provider_name == "OpenAI"

    def test_returns_google_provider(self) -> None:
        settings = _make_mock_settings("google")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.google.get_settings", return_value=settings):
            provider = get_vlm_provider()
            assert provider.provider_name == "Google"

    def test_returns_ollama_provider(self) -> None:
        settings = _make_mock_settings("ollama")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.ollama.get_settings", return_value=settings):
            provider = get_vlm_provider()
            assert provider.provider_name == "Ollama"


# ---------------------------------------------------------------------------
# get_vlm_provider — error handling
# ---------------------------------------------------------------------------

class TestGetVlmProviderErrors:
    """Tests for error handling in get_vlm_provider."""

    def test_raises_on_empty_provider(self) -> None:
        settings = _make_mock_settings("")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings):
            with pytest.raises(ValueError, match="VLM_PROVIDER is not set"):
                get_vlm_provider()

    def test_raises_on_unknown_provider(self) -> None:
        settings = _make_mock_settings("unknown_provider")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings):
            with pytest.raises(ValueError, match="Unknown VLM provider.*unknown_provider"):
                get_vlm_provider()

    def test_error_message_lists_available_providers(self) -> None:
        """When a provider is unknown, the error should list available options."""
        register_provider("dashscope", MagicMock)
        settings = _make_mock_settings("invalid")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings):
            with pytest.raises(ValueError, match="Available.*dashscope"):
                get_vlm_provider()


# ---------------------------------------------------------------------------
# Lazy import behavior
# ---------------------------------------------------------------------------

class TestLazyImports:
    """Tests verifying lazy import behavior."""

    def test_dashscope_registered_after_first_call(self) -> None:
        """After calling get_vlm_provider with dashscope, it should be in the registry."""
        settings = _make_mock_settings("dashscope")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.dashscope.get_settings", return_value=settings):
            assert "dashscope" not in _PROVIDER_REGISTRY
            get_vlm_provider()
            assert "dashscope" in _PROVIDER_REGISTRY

    def test_second_call_reuses_registry(self) -> None:
        """Second call should not re-import — should use cached registry entry."""
        mock_cls = MagicMock()
        mock_cls.return_value = MagicMock(provider_name="DashScope")
        register_provider("dashscope", mock_cls)

        settings = _make_mock_settings("dashscope")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings):
            provider1 = get_vlm_provider()
            provider2 = get_vlm_provider()

        # The class constructor should be called each time (new instance)
        assert mock_cls.call_count == 2

    def test_only_requested_provider_imported(self) -> None:
        """Requesting 'ollama' should not import dashscope, openai, or google modules."""
        settings = _make_mock_settings("ollama")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.ollama.get_settings", return_value=settings):
            get_vlm_provider()
            # Only ollama should be in registry
            assert "ollama" in _PROVIDER_REGISTRY
            assert "dashscope" not in _PROVIDER_REGISTRY
            assert "openai" not in _PROVIDER_REGISTRY
            assert "google" not in _PROVIDER_REGISTRY


# ---------------------------------------------------------------------------
# Provider properties
# ---------------------------------------------------------------------------

class TestProviderProperties:
    """Tests verifying provider instances have correct properties."""

    @pytest.mark.parametrize(
        "provider_name,expected_name,expected_model",
        [
            ("dashscope", "DashScope", "qwen-vl-max"),
            ("openai", "OpenAI", "gpt-4o"),
            ("google", "Google", "gemini-2.0-flash"),
            ("ollama", "Ollama", "llava:13b"),
        ],
    )
    def test_provider_properties(
        self,
        provider_name: str,
        expected_name: str,
        expected_model: str,
    ) -> None:
        settings = _make_mock_settings(provider_name)
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch(f"docmind.library.providers.{provider_name}.get_settings", return_value=settings):
            provider = get_vlm_provider()
            assert provider.provider_name == expected_name
            assert provider.model_name == expected_model


# ---------------------------------------------------------------------------
# Health check integration
# ---------------------------------------------------------------------------

class TestHealthCheckIntegration:
    """Tests verifying factory-created providers have health_check method."""

    def test_provider_has_health_check(self) -> None:
        """All providers from factory should have health_check method."""
        settings = _make_mock_settings("ollama")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings), \
             patch("docmind.library.providers.ollama.get_settings", return_value=settings):
            provider = get_vlm_provider()
            assert hasattr(provider, "health_check")
            assert callable(provider.health_check)

    @pytest.mark.asyncio
    async def test_mock_provider_health_check(self) -> None:
        """Verify health_check can be called on factory-created provider."""
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.health_check = MagicMock(return_value=True)
        mock_cls.return_value = mock_instance
        register_provider("test_provider", mock_cls)

        settings = _make_mock_settings("test_provider")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings):
            provider = get_vlm_provider()
            result = provider.health_check()
            assert result is True


# ---------------------------------------------------------------------------
# Re-export via __init__.py
# ---------------------------------------------------------------------------

class TestReExport:
    """Verify the get_vlm_provider re-export works."""

    def test_import_from_providers_package(self) -> None:
        from docmind.library.providers import get_vlm_provider as factory_fn
        assert callable(factory_fn)

    def test_is_same_function(self) -> None:
        from docmind.library.providers import get_vlm_provider as factory_fn
        assert factory_fn is get_vlm_provider

    def test_vlm_provider_protocol_importable(self) -> None:
        from docmind.library.providers import VLMProvider
        assert VLMProvider is not None

    def test_vlm_response_importable(self) -> None:
        from docmind.library.providers import VLMResponse
        assert VLMResponse is not None
