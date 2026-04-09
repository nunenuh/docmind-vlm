# Issue #10: VLM Provider Factory — Registry, Lazy Loading, and Health Check

## Summary

Implement and fully test the VLM provider factory at `get_vlm_provider()`. The factory reads `VLM_PROVIDER` from settings, lazily imports the corresponding provider class, registers it in a module-level registry, and returns an instantiated provider. It also supports explicit `provider_name` override. This issue verifies the factory returns the correct provider for each supported name, handles unknown providers with clear errors, respects the settings default, and integrates with provider health checks. All provider constructors are mocked in tests to avoid needing real API keys.

## Context

- **Phase**: 2 — CV + VLM Providers
- **Priority**: P1
- **Labels**: `phase-2-cv-vlm`, `backend`, `tdd`, `priority-p1`
- **Dependencies**: #9 (DashScope provider must be implemented; other providers are skeletons)
- **Branch**: `feat/10-vlm-factory`
- **Estimated scope**: S

## Specs to Read

- `specs/backend/providers.md` — factory section, provider registry, lazy imports, env var `VLM_PROVIDER`
- `specs/system.md` — env vars
- `specs/conventions/python-conventions.md` — PEP 8, type hints

## Current State (Scaffold)

The scaffold at `backend/src/docmind/library/providers/factory.py`:

```python
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
        raise ValueError("VLM_PROVIDER environment variable is not set. Options: dashscope, openai, google, ollama")

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
        raise ValueError(f"Unknown VLM provider: '{provider_name}'. Available: {list(_PROVIDER_REGISTRY.keys())}")
    logger.info("Creating VLM provider: %s", provider_name)
    return provider_cls()
```

The `__init__.py` re-exports:

```python
from .factory import get_vlm_provider
```

The config at `backend/src/docmind/core/config.py`:

```python
VLM_PROVIDER: str = Field(default="dashscope")
```

Each provider skeleton in the scaffold:
- `DashScopeProvider.__init__` requires `DASHSCOPE_API_KEY` (raises `RuntimeError` if empty)
- `OpenAIProvider.__init__` requires `OPENAI_API_KEY`
- `GoogleProvider.__init__` requires `GOOGLE_API_KEY`
- `OllamaProvider.__init__` needs no key (defaults to localhost)

The test directory `backend/tests/unit/library/providers/` exists but contains no test files for factory.

## Requirements

### Functional

1. `get_vlm_provider()` must read `VLM_PROVIDER` from `get_settings()` to determine which provider to create
2. `get_vlm_provider()` must raise `ValueError` when `VLM_PROVIDER` is empty/not set
3. `get_vlm_provider()` must lazily import provider classes — only import the one being requested
4. `get_vlm_provider()` must register the imported class in `_PROVIDER_REGISTRY`
5. `get_vlm_provider()` must return an instance of the correct provider class
6. `get_vlm_provider()` must raise `ValueError` for unknown provider names with a helpful error message
7. `register_provider(name, cls)` must add the class to the registry
8. The factory must support all four providers: `dashscope`, `openai`, `google`, `ollama`
9. Second calls for the same provider should reuse the registered class (not re-import)
10. The re-export `from docmind.library.providers import get_vlm_provider` must work

### Non-Functional

- Lazy imports prevent loading unused provider dependencies (e.g., `openai` SDK when using DashScope)
- Registry is module-level (singleton pattern) for performance
- Clear error messages guide users to valid provider options

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/providers/test_factory.py`

```python
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
            with pytest.raises(ValueError, match="VLM_PROVIDER environment variable is not set"):
                get_vlm_provider()

    def test_raises_on_unknown_provider(self) -> None:
        settings = _make_mock_settings("unknown_provider")
        with patch("docmind.library.providers.factory.get_settings", return_value=settings):
            with pytest.raises(ValueError, match="Unknown VLM provider.*unknown_provider"):
                get_vlm_provider()

    def test_error_message_lists_available_providers(self) -> None:
        """When a provider is unknown, the error should list available options."""
        # Pre-register some providers so the error message includes them
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
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/providers/factory.py` — The scaffold already contains the working implementation. Add full docstrings.

**Implementation guidance**:

The current scaffold code matches the spec. The main work is:

1. **Add full docstrings** from `specs/backend/providers.md` to `get_vlm_provider`, `register_provider`, and the module.
2. **Verify all tests pass** — the logic is already correct.
3. **Confirm the re-exports** in `__init__.py` work.

Key design patterns:
- **Lazy imports**: Each provider is imported only when requested. This prevents loading `openai`, `google-generativeai`, etc. when they are not needed.
- **Registry pattern**: `_PROVIDER_REGISTRY` is a module-level dict that caches imported classes. Second calls for the same provider skip the import.
- **Each call creates a new instance**: `provider_cls()` is called each time, giving a fresh provider. The registry caches the class, not the instance.

Gotchas:
- The `_PROVIDER_REGISTRY` is module-level state. Tests must clean it between runs (the `autouse` fixture handles this).
- Provider constructors validate their own API keys. Tests must mock `get_settings()` at both the factory and provider module levels.
- The factory does not validate API keys — that is the provider's responsibility.

### Step 3: Refactor (IMPROVE)

- Add full docstrings
- Ensure the ValueError messages are helpful for users
- Consider logging at debug level when reusing a cached registry entry
- Verify type annotations are complete

## Acceptance Criteria

- [ ] `get_vlm_provider()` returns DashScopeProvider when `VLM_PROVIDER=dashscope`
- [ ] `get_vlm_provider()` returns OpenAIProvider when `VLM_PROVIDER=openai`
- [ ] `get_vlm_provider()` returns GoogleProvider when `VLM_PROVIDER=google`
- [ ] `get_vlm_provider()` returns OllamaProvider when `VLM_PROVIDER=ollama`
- [ ] `get_vlm_provider()` raises ValueError when VLM_PROVIDER is empty
- [ ] `get_vlm_provider()` raises ValueError for unknown provider names
- [ ] Error message for unknown provider lists available options
- [ ] Lazy imports: only the requested provider module is imported
- [ ] Registry caches classes across calls
- [ ] Each call creates a new provider instance
- [ ] All providers have `provider_name`, `model_name`, and `health_check` attributes
- [ ] Re-exports work: `from docmind.library.providers import get_vlm_provider, VLMProvider, VLMResponse`
- [ ] All tests pass with `pytest backend/tests/unit/library/providers/test_factory.py -v`

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/tests/unit/library/providers/__init__.py` | Create | Empty `__init__.py` for test package (if not already created by #9) |
| `backend/tests/unit/library/providers/test_factory.py` | Create | Unit tests for VLM factory |
| `backend/src/docmind/library/providers/factory.py` | Modify | Add full docstrings from spec |

## Verification

```bash
# Run the tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/providers/test_factory.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/providers/test_factory.py -v --cov=docmind.library.providers.factory --cov-report=term-missing

# Verify re-exports
python -c "from docmind.library.providers import get_vlm_provider, VLMProvider, VLMResponse; print('OK')"

# Lint
ruff check backend/src/docmind/library/providers/factory.py
```
