"""
docmind/modules/personas/repositories.py

Persona database operations via SQLAlchemy.
Presets are visible to all users; custom personas are user-scoped.
"""

from sqlalchemy import or_, select, update

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Persona

logger = get_logger(__name__)


class PersonaRepository:
    """Repository for persona CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        system_prompt: str = "",
        tone: str = "professional",
        rules: str | None = None,
        boundaries: str | None = None,
    ) -> Persona:
        """Insert a new custom persona. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            persona = Persona(
                user_id=user_id,
                name=name,
                description=description,
                system_prompt=system_prompt,
                tone=tone,
                rules=rules,
                boundaries=boundaries,
                is_preset=False,
            )
            session.add(persona)
            await session.commit()
            await session.refresh(persona)
            return persona

    async def list_for_user(self, user_id: str) -> list[Persona]:
        """List all personas visible to a user (presets + custom)."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Persona)
                .where(
                    or_(
                        Persona.is_preset.is_(True),
                        Persona.user_id == user_id,
                    )
                )
                .order_by(Persona.is_preset.desc(), Persona.name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_id(self, persona_id: str) -> Persona | None:
        """Get a single persona by ID (no user scoping — presets are shared)."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(Persona.id == persona_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(
        self,
        persona_id: str,
        user_id: str,
        **kwargs: object,
    ) -> Persona | None:
        """Update a custom persona. Returns updated persona or None.

        Only custom personas (is_preset=False) owned by user can be updated.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                Persona.user_id == user_id,
                Persona.is_preset.is_(False),
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return None

            values = {k: v for k, v in kwargs.items() if v is not None}
            if values:
                update_stmt = (
                    update(Persona)
                    .where(Persona.id == persona_id)
                    .values(**values)
                )
                await session.execute(update_stmt)
                await session.commit()

                # Re-fetch
                result = await session.execute(
                    select(Persona).where(Persona.id == persona_id)
                )
                persona = result.scalar_one_or_none()

            return persona

    async def delete(self, persona_id: str, user_id: str) -> bool:
        """Delete a custom persona. Presets cannot be deleted."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                Persona.user_id == user_id,
                Persona.is_preset.is_(False),
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return False

            await session.delete(persona)
            await session.commit()
            return True
