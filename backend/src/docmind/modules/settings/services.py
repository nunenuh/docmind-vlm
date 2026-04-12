"""
Provider test service — validates provider connections and lists models.

Business logic only, NO database access.
"""

import httpx

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.modules.settings.schemas import ProviderName, ValidateProviderResponse

logger = get_logger(__name__)

_TEST_TIMEOUT = 15.0


class ProviderTestService:
    """Tests provider connections and retrieves available models."""

    async def test_connection(
        self,
        provider_name: ProviderName,
        api_key: str,
        base_url: str | None = None,
    ) -> ValidateProviderResponse:
        """Test a provider connection and return available models."""
        try:
            if provider_name == ProviderName.DASHSCOPE:
                return await self._test_dashscope(api_key, base_url)
            elif provider_name == ProviderName.OPENAI:
                return await self._test_openai(api_key, base_url)
            elif provider_name == ProviderName.OPENROUTER:
                return await self._test_openrouter(api_key)
            elif provider_name == ProviderName.GOOGLE:
                return await self._test_google(api_key)
            elif provider_name == ProviderName.OLLAMA:
                return await self._test_ollama(base_url)
            else:
                return ValidateProviderResponse(
                    success=False,
                    error=f"Unknown provider: {provider_name}",
                )
        except httpx.TimeoutException:
            logger.warning("provider_test_timeout", provider=provider_name.value)
            return ValidateProviderResponse(
                success=False,
                error=f"Connection timed out for {provider_name.value}",
            )
        except httpx.ConnectError:
            logger.warning("provider_test_connect_error", provider=provider_name.value)
            return ValidateProviderResponse(
                success=False,
                error=f"Could not connect to {provider_name.value}",
            )
        except Exception as exc:
            logger.error(
                "provider_test_error",
                provider=provider_name.value,
                error=str(exc),
            )
            return ValidateProviderResponse(
                success=False,
                error=f"Provider test failed: {exc}",
            )

    async def _test_dashscope(
        self, api_key: str, base_url: str | None
    ) -> ValidateProviderResponse:
        """Test DashScope connection via models endpoint or generation fallback."""
        settings = get_settings()
        # Try the models listing endpoint first
        models_url = base_url or "https://dashscope-intl.aliyuncs.com"
        models_url = models_url.rstrip("/")

        # If the base_url is the full generation URL, extract the base
        if "/api/v1/services/" in models_url:
            models_url = models_url.split("/api/v1/services/")[0]

        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            # Try models endpoint
            try:
                resp = await client.get(
                    f"{models_url}/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [
                        m.get("id", m.get("model_id", ""))
                        for m in data.get("data", data.get("models", []))
                    ]
                    return ValidateProviderResponse(success=True, models=models)
            except Exception:
                pass  # Fall through to generation endpoint test

            # Fallback: test with a minimal generation request
            gen_url = (
                base_url
                or settings.DASHSCOPE_BASE_URL
            )
            resp = await client.post(
                gen_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DASHSCOPE_MODEL,
                    "input": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"text": "hi"}],
                            }
                        ]
                    },
                    "parameters": {"max_tokens": 1},
                },
            )
            if resp.status_code == 200:
                return ValidateProviderResponse(
                    success=True,
                    models=[settings.DASHSCOPE_MODEL],
                )
            return ValidateProviderResponse(
                success=False,
                error=f"Authentication failed (HTTP {resp.status_code})",
            )

    async def _test_openai(
        self, api_key: str, base_url: str | None
    ) -> ValidateProviderResponse:
        """Test OpenAI connection via /v1/models endpoint."""
        url = (base_url or "https://api.openai.com").rstrip("/")
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            resp = await client.get(
                f"{url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code != 200:
                return ValidateProviderResponse(
                    success=False,
                    error=f"Authentication failed (HTTP {resp.status_code})",
                )
            data = resp.json()
            all_models = [m["id"] for m in data.get("data", [])]
            # Filter for vision-capable and embedding models
            vision_keywords = ("gpt-4o", "gpt-4-turbo", "gpt-4-vision")
            embedding_keywords = ("embedding",)
            relevant = [
                m
                for m in all_models
                if any(k in m for k in vision_keywords + embedding_keywords)
            ]
            return ValidateProviderResponse(
                success=True,
                models=sorted(relevant) if relevant else sorted(all_models[:20]),
            )

    async def _test_openrouter(self, api_key: str) -> ValidateProviderResponse:
        """Test OpenRouter connection via /api/v1/models endpoint."""
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code != 200:
                return ValidateProviderResponse(
                    success=False,
                    error=f"Authentication failed (HTTP {resp.status_code})",
                )
            data = resp.json()
            all_models = [m["id"] for m in data.get("data", [])]
            # Filter for vision/multimodal and embedding models
            vision_keywords = (
                "gpt-4o", "claude-3", "claude-4", "gemini",
                "qwen", "llava", "pixtral", "vision",
            )
            embedding_keywords = ("embedding",)
            relevant = [
                m for m in all_models
                if any(k in m.lower() for k in vision_keywords + embedding_keywords)
            ]
            return ValidateProviderResponse(
                success=True,
                models=sorted(relevant) if relevant else sorted(all_models[:30]),
            )

    async def _test_google(self, api_key: str) -> ValidateProviderResponse:
        """Test Google Gemini connection via models listing endpoint."""
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            resp = await client.get(
                "https://generativelanguage.googleapis.com/v1/models",
                params={"key": api_key},
            )
            if resp.status_code != 200:
                return ValidateProviderResponse(
                    success=False,
                    error=f"Authentication failed (HTTP {resp.status_code})",
                )
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                # Strip "models/" prefix
                if name.startswith("models/"):
                    name = name[7:]
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods or "embedContent" in methods:
                    models.append(name)
            return ValidateProviderResponse(success=True, models=sorted(models))

    async def _test_ollama(self, base_url: str | None) -> ValidateProviderResponse:
        """Test Ollama connection via /api/tags endpoint."""
        settings = get_settings()
        url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            resp = await client.get(f"{url}/api/tags")
            if resp.status_code != 200:
                return ValidateProviderResponse(
                    success=False,
                    error=f"Ollama returned HTTP {resp.status_code}",
                )
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return ValidateProviderResponse(success=True, models=sorted(models))

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """Return first 8 chars + '...' for display."""
        if len(api_key) <= 8:
            return api_key + "..."
        return api_key[:8] + "..."
