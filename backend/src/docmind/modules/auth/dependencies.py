"""
docmind/modules/auth/dependencies.py

FastAPI dependency providers for auth module.
"""

from docmind.modules.auth.usecases import AuthUseCase


def get_auth_usecase() -> AuthUseCase:
    return AuthUseCase()
