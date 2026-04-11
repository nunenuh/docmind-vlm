"""
Dependency injection for settings module.
"""

from docmind.modules.settings.usecase import ProviderSettingsUseCase


def get_provider_settings_usecase() -> ProviderSettingsUseCase:
    """Create a ProviderSettingsUseCase instance."""
    return ProviderSettingsUseCase()
