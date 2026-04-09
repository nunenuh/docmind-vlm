"""
API Token repository — CRUD for api_tokens table.
"""

from datetime import datetime, timezone

from sqlalchemy import select, update

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models.api_token import ApiToken

logger = get_logger(__name__)


class ApiTokenRepository:
    """Repository for API token CRUD operations."""

    async def create(
        self,
        user_id: str,
        name: str,
        prefix: str,
        hashed_secret: str,
        scopes: list[str],
        token_type: str,
        expires_at: datetime | None,
    ) -> ApiToken:
        async with AsyncSessionLocal() as session:
            token = ApiToken(
                user_id=user_id,
                name=name,
                prefix=prefix,
                hashed_secret=hashed_secret,
                scopes=scopes,
                token_type=token_type,
                expires_at=expires_at,
            )
            session.add(token)
            await session.commit()
            await session.refresh(token)
            return token

    async def get_by_prefix(self, prefix: str) -> ApiToken | None:
        """Lookup token by prefix. No user_id filter — used during auth."""
        async with AsyncSessionLocal() as session:
            stmt = select(ApiToken).where(ApiToken.prefix == prefix)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[ApiToken]:
        """List all non-revoked tokens for a user."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ApiToken)
                .where(
                    ApiToken.user_id == user_id,
                    ApiToken.revoked_at.is_(None),
                )
                .order_by(ApiToken.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_id(self, token_id: str, user_id: str) -> ApiToken | None:
        async with AsyncSessionLocal() as session:
            stmt = select(ApiToken).where(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def revoke(self, token_id: str, user_id: str) -> bool:
        """Set revoked_at timestamp. Returns False if token not found."""
        async with AsyncSessionLocal() as session:
            stmt = select(ApiToken).where(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            if token is None:
                return False
            token.revoked_at = datetime.now(timezone.utc)
            await session.commit()
            return True

    async def update(
        self,
        token_id: str,
        user_id: str,
        name: str | None = None,
        scopes: list[str] | None = None,
    ) -> ApiToken | None:
        async with AsyncSessionLocal() as session:
            stmt = select(ApiToken).where(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            if token is None:
                return None
            if name is not None:
                token.name = name
            if scopes is not None:
                token.scopes = scopes
            await session.commit()
            await session.refresh(token)
            return token

    async def update_last_used(self, token_id: str) -> None:
        """Fire-and-forget timestamp update."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(ApiToken)
                .where(ApiToken.id == token_id)
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await session.execute(stmt)
            await session.commit()
