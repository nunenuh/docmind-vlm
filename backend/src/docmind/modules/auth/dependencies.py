"""
docmind/modules/auth/dependencies.py

FastAPI dependency providers for auth module.
"""

from docmind.modules.auth.usecases import ApiTokenUseCase, AuthUseCase


def get_auth_usecase() -> AuthUseCase:
    return AuthUseCase()


def get_api_token_usecase() -> ApiTokenUseCase:
    return ApiTokenUseCase()
