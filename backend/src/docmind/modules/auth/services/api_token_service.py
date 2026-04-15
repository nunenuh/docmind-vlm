"""
API Token service — generation, hashing, validation.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from docmind.core.logging import get_logger
from docmind.modules.auth.repositories.api_token_repository import ApiTokenRepository
from docmind.shared.exceptions import AuthenticationException, NotFoundException

logger = get_logger(__name__)

API_TOKEN_PREFIXES = ("dm_live_", "dm_test_")


class ApiTokenService:
    """Business logic for API token management."""

    def __init__(self, repository: ApiTokenRepository | None = None) -> None:
        self._repo = repository or ApiTokenRepository()

    def _generate_token(self, token_type: str) -> tuple[str, str, str]:
        """Generate a new token. Returns (plain_token, prefix, hashed_secret)."""
        prefix_str = f"dm_{token_type}_"
        random_part = secrets.token_urlsafe(24)
        plain_token = f"{prefix_str}{random_part}"
        prefix = plain_token[:12]
        hashed_secret = hashlib.sha256(plain_token.encode()).hexdigest()
        return plain_token, prefix, hashed_secret

    async def create_token(
        self,
        user_id: str,
        name: str,
        scopes: list[str],
        token_type: str,
        expires_in_days: int | None,
    ) -> dict:
        """Create a new API token. Returns dict with plain_token (shown once)."""
        plain_token, prefix, hashed_secret = self._generate_token(token_type)

        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        token = await self._repo.create(
            user_id=user_id,
            name=name,
            prefix=prefix,
            hashed_secret=hashed_secret,
            scopes=scopes,
            token_type=token_type,
            expires_at=expires_at,
        )

        logger.info("api_token_created", user_id=user_id, prefix=prefix)

        return {
            "id": token.id,
            "name": token.name,
            "prefix": token.prefix,
            "scopes": token.scopes,
            "token_type": token.token_type,
            "expires_at": token.expires_at,
            "last_used_at": token.last_used_at,
            "created_at": token.created_at,
            "revoked_at": token.revoked_at,
            "plain_token": plain_token,
        }

    async def validate_token(self, raw_token: str) -> dict:
        """Validate an API token. Returns user data with scopes."""
        if not any(raw_token.startswith(p) for p in API_TOKEN_PREFIXES):
            raise AuthenticationException("Invalid token format")

        prefix = raw_token[:12]
        token = await self._repo.get_by_prefix(prefix)

        if token is None:
            raise AuthenticationException("Invalid API token")

        if token.revoked_at is not None:
            raise AuthenticationException("Token has been revoked")

        if token.expires_at is not None and token.expires_at < datetime.now(
            timezone.utc
        ):
            raise AuthenticationException("Token has expired")

        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        if token.hashed_secret != expected_hash:
            raise AuthenticationException("Invalid API token")

        # Fire-and-forget last_used update
        try:
            await self._repo.update_last_used(token.id)
        except Exception:
            pass  # Non-critical

        return {
            "user_id": token.user_id,
            "scopes": token.scopes,
            "token_id": token.id,
            "auth_method": "api_token",
        }

    async def list_tokens(self, user_id: str) -> list[dict]:
        """List all active tokens for a user. Never includes secrets."""
        tokens = await self._repo.list_for_user(user_id)
        return [
            {
                "id": t.id,
                "name": t.name,
                "prefix": t.prefix,
                "scopes": t.scopes,
                "token_type": t.token_type,
                "expires_at": t.expires_at,
                "last_used_at": t.last_used_at,
                "created_at": t.created_at,
                "revoked_at": t.revoked_at,
            }
            for t in tokens
        ]

    async def revoke_token(self, token_id: str, user_id: str) -> bool:
        """Revoke a token. Raises NotFoundException if not found."""
        result = await self._repo.revoke(token_id, user_id)
        if not result:
            raise NotFoundException("Token not found")
        logger.info("api_token_revoked", user_id=user_id, token_id=token_id)
        return True

    async def regenerate_token(
        self,
        token_id: str,
        user_id: str,
    ) -> dict:
        """Regenerate a token: revoke old, create new with same name/scopes/type.

        Returns the new token dict with plain_token (shown once).
        """
        old_token = await self._repo.get_by_id(token_id, user_id)
        if old_token is None or old_token.revoked_at is not None:
            raise NotFoundException("Token not found")

        # Revoke old
        await self._repo.revoke(token_id, user_id)
        logger.info("api_token_revoked_for_rotation", user_id=user_id, old_token_id=token_id)

        # Create new with same settings
        result = await self.create_token(
            user_id=user_id,
            name=old_token.name,
            scopes=old_token.scopes,
            token_type=old_token.token_type,
            expires_in_days=None,  # new token gets no expiry; user can edit later
        )

        logger.info(
            "api_token_regenerated",
            user_id=user_id,
            old_token_id=token_id,
            new_token_id=result["id"],
        )
        return result

    async def update_token(
        self,
        token_id: str,
        user_id: str,
        name: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Update token name and/or scopes."""
        token = await self._repo.update(
            token_id=token_id,
            user_id=user_id,
            name=name,
            scopes=scopes,
        )
        if token is None:
            raise NotFoundException("Token not found")
        return {
            "id": token.id,
            "name": token.name,
            "prefix": token.prefix,
            "scopes": token.scopes,
            "token_type": token.token_type,
            "expires_at": token.expires_at,
            "last_used_at": token.last_used_at,
            "created_at": token.created_at,
            "revoked_at": token.revoked_at,
        }
