"""
Provider settings use case — orchestrates service + repository calls.

Handles encrypt-before-store and decrypt-at-read for API keys.
"""

from docmind.core.encryption import decrypt, encrypt
from docmind.core.logging import get_logger
from docmind.modules.settings.repositories import UserProviderRepository
from docmind.modules.settings.schemas import (
    ProviderConfigResponse,
    ProviderName,
    ProviderType,
    ProvidersResponse,
    SetProviderRequest,
    ValidateProviderRequest,
    ValidateProviderResponse,
)
from docmind.modules.settings.services import ProviderTestService
from docmind.shared.exceptions import ValidationException

logger = get_logger(__name__)


class ProviderSettingsUseCase:
    """Orchestrates provider settings CRUD and testing."""

    def __init__(
        self,
        repository: UserProviderRepository | None = None,
        service: ProviderTestService | None = None,
    ) -> None:
        self._repo = repository or UserProviderRepository()
        self._service = service or ProviderTestService()

    async def get_providers(self, user_id: str) -> ProvidersResponse:
        """Get all provider configs for a user, with masked API keys."""
        configs = await self._repo.get_all_for_user(user_id)
        vlm_config = None
        embedding_config = None

        for config in configs:
            # Decrypt key only to get the prefix for masking
            try:
                decrypted_key = decrypt(config.encrypted_api_key)
                api_key_prefix = ProviderTestService.mask_api_key(decrypted_key)
            except Exception:
                logger.error(
                    "failed_to_decrypt_api_key",
                    user_id=user_id,
                    provider_type=config.provider_type,
                )
                api_key_prefix = "***..."

            response = ProviderConfigResponse(
                provider_type=ProviderType(config.provider_type),
                provider_name=ProviderName(config.provider_name),
                model_name=config.model_name,
                base_url=config.base_url,
                is_validated=config.is_validated,
                api_key_prefix=api_key_prefix,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )

            if config.provider_type == ProviderType.VLM.value:
                vlm_config = response
            elif config.provider_type == ProviderType.EMBEDDING.value:
                embedding_config = response

        return ProvidersResponse(vlm=vlm_config, embedding=embedding_config)

    async def set_provider(
        self,
        user_id: str,
        provider_type: ProviderType,
        request: SetProviderRequest,
    ) -> ProviderConfigResponse:
        """Set or update a provider config after testing the connection."""
        # Test the provider connection first
        test_result = await self._service.test_connection(
            provider_name=request.provider_name,
            api_key=request.api_key,
            base_url=request.base_url,
            provider_type=provider_type.value,
        )
        if not test_result.success:
            raise ValidationException(
                f"Provider test failed: {test_result.error}"
            )

        # Encrypt the API key before storing
        encrypted_key = encrypt(request.api_key)

        config = await self._repo.upsert(
            user_id=user_id,
            provider_type=provider_type.value,
            provider_name=request.provider_name.value,
            encrypted_api_key=encrypted_key,
            model_name=request.model_name,
            base_url=request.base_url,
            is_validated=True,
        )

        api_key_prefix = ProviderTestService.mask_api_key(request.api_key)

        return ProviderConfigResponse(
            provider_type=ProviderType(config.provider_type),
            provider_name=ProviderName(config.provider_name),
            model_name=config.model_name,
            base_url=config.base_url,
            is_validated=config.is_validated,
            api_key_prefix=api_key_prefix,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    async def delete_provider(
        self, user_id: str, provider_type: ProviderType
    ) -> bool:
        """Delete a provider config. Returns True if deleted, False if not found."""
        return await self._repo.delete(user_id, provider_type.value)

    async def test_provider(
        self, request: ValidateProviderRequest
    ) -> ValidateProviderResponse:
        """Test a provider connection without saving."""
        return await self._service.test_connection(
            provider_name=request.provider_name,
            api_key=request.api_key,
            base_url=request.base_url,
            provider_type=request.provider_type.value,
        )
