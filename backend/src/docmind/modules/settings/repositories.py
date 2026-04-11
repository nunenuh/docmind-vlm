"""
User Provider Config repository — CRUD for user_provider_configs table.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models.user_provider_config import UserProviderConfig

logger = get_logger(__name__)


class UserProviderRepository:
    """Repository for user provider config CRUD operations."""

    async def get_by_user_and_type(
        self, user_id: str, provider_type: str
    ) -> UserProviderConfig | None:
        """Get a single config for a user and provider type."""
        async with AsyncSessionLocal() as session:
            stmt = select(UserProviderConfig).where(
                UserProviderConfig.user_id == user_id,
                UserProviderConfig.provider_type == provider_type,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all_for_user(self, user_id: str) -> list[UserProviderConfig]:
        """Get all provider configs for a user."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(UserProviderConfig)
                .where(UserProviderConfig.user_id == user_id)
                .order_by(UserProviderConfig.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def upsert(
        self,
        user_id: str,
        provider_type: str,
        provider_name: str,
        encrypted_api_key: str,
        model_name: str,
        base_url: str | None,
        is_validated: bool,
    ) -> UserProviderConfig:
        """Insert or update a provider config for a user + type pair."""
        async with AsyncSessionLocal() as session:
            stmt = select(UserProviderConfig).where(
                UserProviderConfig.user_id == user_id,
                UserProviderConfig.provider_type == provider_type,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is not None:
                existing.provider_name = provider_name
                existing.encrypted_api_key = encrypted_api_key
                existing.model_name = model_name
                existing.base_url = base_url
                existing.is_validated = is_validated
                existing.updated_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(existing)
                return existing

            config = UserProviderConfig(
                user_id=user_id,
                provider_type=provider_type,
                provider_name=provider_name,
                encrypted_api_key=encrypted_api_key,
                model_name=model_name,
                base_url=base_url,
                is_validated=is_validated,
            )
            session.add(config)
            await session.commit()
            await session.refresh(config)
            return config

    async def delete(self, user_id: str, provider_type: str) -> bool:
        """Delete a provider config. Returns True if a row was deleted."""
        async with AsyncSessionLocal() as session:
            stmt = delete(UserProviderConfig).where(
                UserProviderConfig.user_id == user_id,
                UserProviderConfig.provider_type == provider_type,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
