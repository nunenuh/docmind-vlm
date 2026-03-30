"""
docmind/modules/personas/repositories.py

Persona database operations via SQLAlchemy.
Seeded personas (user_id=NULL) and user-created personas are all editable.
"""

import json
import logging
from pathlib import Path

from sqlalchemy import delete as sa_delete, or_, select

from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Persona

logger = logging.getLogger(__name__)

PERSONAS_DIR = Path(__file__).resolve().parents[5] / "data" / "personas"


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
        """Insert a new persona. Returns the created ORM instance."""
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
        """List all personas visible to a user (seeded + user's own)."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Persona)
                .where(
                    or_(
                        Persona.user_id.is_(None),
                        Persona.user_id == user_id,
                    )
                )
                .order_by(Persona.name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_id(self, persona_id: str) -> Persona | None:
        """Get a single persona by ID."""
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
        """Update any persona owned by user or seeded (user_id=NULL)."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                or_(
                    Persona.user_id == user_id,
                    Persona.user_id.is_(None),
                ),
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(persona, key) and key not in ("id", "created_at"):
                    setattr(persona, key, value)

            await session.commit()
            await session.refresh(persona)
            return persona

    async def delete(self, persona_id: str, user_id: str) -> bool:
        """Delete any persona owned by user or seeded (user_id=NULL)."""
        async with AsyncSessionLocal() as session:
            stmt = sa_delete(Persona).where(
                Persona.id == persona_id,
                or_(
                    Persona.user_id == user_id,
                    Persona.user_id.is_(None),
                ),
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def duplicate(
        self, persona_id: str, user_id: str
    ) -> Persona | None:
        """Duplicate a persona as a user's own copy."""
        source = await self.get_by_id(persona_id)
        if source is None:
            return None

        import uuid

        new_persona = Persona(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=f"{source.name} (Copy)",
            description=source.description,
            system_prompt=source.system_prompt,
            tone=source.tone,
            rules=source.rules,
            boundaries=source.boundaries,
            is_preset=False,
        )

        async with AsyncSessionLocal() as session:
            session.add(new_persona)
            await session.commit()
            await session.refresh(new_persona)
            return new_persona

    async def count_all(self) -> int:
        """Count all personas in the database."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona)
            result = await session.execute(stmt)
            return len(result.scalars().all())

    async def seed_presets(self) -> int:
        """Seed personas from JSON files if none exist.

        Returns:
            Number of personas seeded.
        """
        count = await self.count_all()
        if count > 0:
            logger.info("Personas already exist (%d), skipping seed", count)
            return 0

        if not PERSONAS_DIR.exists():
            logger.warning("Personas directory not found: %s", PERSONAS_DIR)
            return 0

        seeded = 0
        async with AsyncSessionLocal() as session:
            for path in sorted(PERSONAS_DIR.glob("*.json")):
                try:
                    with open(path) as f:
                        data = json.load(f)

                    import uuid

                    # Convert rules/boundaries arrays to JSON strings
                    rules = data.get("rules")
                    if isinstance(rules, list):
                        rules = json.dumps(rules)

                    boundaries = data.get("boundaries")
                    if isinstance(boundaries, list):
                        boundaries = json.dumps(boundaries)

                    persona = Persona(
                        id=str(uuid.uuid4()),
                        user_id=None,
                        name=data["name"],
                        description=data.get("description"),
                        system_prompt=data.get("system_prompt", ""),
                        tone=data.get("tone", "professional"),
                        rules=rules,
                        boundaries=boundaries,
                        is_preset=True,
                    )
                    session.add(persona)
                    seeded += 1
                except Exception as e:
                    logger.warning("Failed to seed persona %s: %s", path.name, e)

            await session.commit()

        logger.info("Seeded %d personas", seeded)
        return seeded
