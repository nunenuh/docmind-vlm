"""Resolve user provider config from DB into a UserProviderOverride."""

from docmind.core.encryption import decrypt
from docmind.core.logging import get_logger
from docmind.library.providers.factory import UserProviderOverride
from docmind.modules.settings.repositories import UserProviderRepository

logger = get_logger(__name__)


async def resolve_provider_override(
    user_id: str, provider_type: str
) -> UserProviderOverride | None:
    """Resolve user's provider config from DB into a UserProviderOverride.

    Returns None if user has no validated config for the given type.
    Called by usecases before entering pipeline/service code.
    """
    repo = UserProviderRepository()
    config = await repo.get_by_user_and_type(user_id, provider_type)
    if config is None or not config.is_validated:
        return None
    try:
        api_key = decrypt(config.encrypted_api_key)
    except Exception:
        logger.error("Failed to decrypt API key for user %s", user_id)
        return None
    return UserProviderOverride(
        provider_name=config.provider_name,
        api_key=api_key,
        model_name=config.model_name,
        base_url=config.base_url,
    )
