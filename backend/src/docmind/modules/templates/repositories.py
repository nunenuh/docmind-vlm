"""Template repository — CRUD for extraction templates."""

import json
import logging
from pathlib import Path

from sqlalchemy import select, delete as sa_delete

from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Template

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parents[5] / "data" / "templates"


class TemplateRepository:
    """Repository for Template CRUD operations."""

    async def list_all(self, user_id: str | None = None) -> list[Template]:
        """List all templates: presets + user's custom templates.

        Args:
            user_id: If provided, includes user's custom templates.

        Returns:
            List of Template objects, presets first then custom.
        """
        async with AsyncSessionLocal() as session:
            if user_id:
                stmt = (
                    select(Template)
                    .where(
                        (Template.is_preset == True) | (Template.user_id == user_id)
                    )
                    .order_by(Template.is_preset.desc(), Template.category, Template.name)
                )
            else:
                stmt = (
                    select(Template)
                    .where(Template.is_preset == True)
                    .order_by(Template.category, Template.name)
                )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_id(self, template_id: str) -> Template | None:
        """Get template by ID."""
        async with AsyncSessionLocal() as session:
            stmt = select(Template).where(Template.id == template_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_type(self, template_type: str, user_id: str | None = None) -> Template | None:
        """Get template by type, preferring user's custom over preset."""
        async with AsyncSessionLocal() as session:
            if user_id:
                # First try user's custom
                stmt = select(Template).where(
                    Template.type == template_type,
                    Template.user_id == user_id,
                )
                result = await session.execute(stmt)
                custom = result.scalar_one_or_none()
                if custom:
                    return custom

            # Fall back to preset
            stmt = select(Template).where(
                Template.type == template_type,
                Template.is_preset == True,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create(self, data: dict) -> Template:
        """Create a new template."""
        async with AsyncSessionLocal() as session:
            template = Template(**data)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def update(self, template_id: str, user_id: str, data: dict) -> Template | None:
        """Update a template (only custom templates owned by user)."""
        async with AsyncSessionLocal() as session:
            stmt = select(Template).where(
                Template.id == template_id,
                Template.user_id == user_id,
                Template.is_preset == False,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if not template:
                return None

            for key, value in data.items():
                if hasattr(template, key) and key not in ("id", "user_id", "is_preset", "created_at"):
                    setattr(template, key, value)

            await session.commit()
            await session.refresh(template)
            return template

    async def delete(self, template_id: str, user_id: str) -> bool:
        """Delete a custom template (presets can't be deleted)."""
        async with AsyncSessionLocal() as session:
            stmt = sa_delete(Template).where(
                Template.id == template_id,
                Template.user_id == user_id,
                Template.is_preset == False,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def duplicate(self, template_id: str, user_id: str, new_name: str | None = None) -> Template | None:
        """Duplicate a template (preset or custom) as a user's custom template."""
        source = await self.get_by_id(template_id)
        if source is None:
            return None

        import uuid
        new_template = Template(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=f"{source.type}_custom",
            name=new_name or f"{source.name} (Copy)",
            name_en=source.name_en,
            description=source.description,
            description_en=source.description_en,
            category=source.category,
            is_preset=False,
            fields=source.fields,
            extraction_prompt=source.extraction_prompt,
        )

        async with AsyncSessionLocal() as session:
            session.add(new_template)
            await session.commit()
            await session.refresh(new_template)
            return new_template

    async def count_presets(self) -> int:
        """Count preset templates."""
        async with AsyncSessionLocal() as session:
            stmt = select(Template).where(Template.is_preset == True)
            result = await session.execute(stmt)
            return len(result.scalars().all())

    async def seed_presets(self) -> int:
        """Seed preset templates from JSON files if none exist.

        Returns:
            Number of templates seeded.
        """
        count = await self.count_presets()
        if count > 0:
            logger.info("Presets already exist (%d), skipping seed", count)
            return 0

        if not TEMPLATES_DIR.exists():
            logger.warning("Templates directory not found: %s", TEMPLATES_DIR)
            return 0

        seeded = 0
        async with AsyncSessionLocal() as session:
            for path in sorted(TEMPLATES_DIR.glob("*.json")):
                try:
                    with open(path) as f:
                        data = json.load(f)

                    # Convert field lists to the unified format
                    required = data.get("required_fields", [])
                    optional = data.get("optional_fields", [])

                    fields = []
                    for f_def in required:
                        if isinstance(f_def, dict):
                            fields.append({**f_def, "required": True})
                        else:
                            fields.append({"key": f_def, "label": f_def, "type": "string", "required": True})

                    for f_def in optional:
                        if isinstance(f_def, dict):
                            fields.append({**f_def, "required": False})
                        else:
                            fields.append({"key": f_def, "label": f_def, "type": "string", "required": False})

                    import uuid
                    template = Template(
                        id=str(uuid.uuid4()),
                        user_id=None,
                        type=data.get("type", path.stem),
                        name=data.get("name", path.stem),
                        name_en=data.get("name_en"),
                        description=data.get("description"),
                        description_en=data.get("description_en"),
                        category=data.get("category", "general"),
                        is_preset=True,
                        fields=fields,
                        extraction_prompt=data.get("extraction_prompt"),
                    )
                    session.add(template)
                    seeded += 1
                except Exception as e:
                    logger.warning("Failed to seed template %s: %s", path.name, e)

            await session.commit()

        logger.info("Seeded %d preset templates", seeded)
        return seeded
