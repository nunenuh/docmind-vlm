"""
docmind/modules/templates/usecase.py

Template use case — orchestrates template CRUD and auto-detection.
NEVER calls library directly.
"""

import uuid

from docmind.core.logging import get_logger

from .repositories import TemplateRepository
from .services import TemplateFieldService, TemplateDetectionService

logger = get_logger(__name__)


class TemplateUseCase:
    """Orchestrates template operations."""

    def __init__(self) -> None:
        self.repo = TemplateRepository()
        self.field_service = TemplateFieldService()
        self.detection_service = TemplateDetectionService()

    async def list_templates(self, user_id: str) -> list:
        """List all templates. Seeds on first call."""
        await self.repo.seed_presets()
        return await self.repo.list_all(user_id=user_id)

    async def get_template(self, template_id: str):
        return await self.repo.get_by_id(template_id)

    async def get_template_by_type(self, template_type: str, user_id: str | None = None):
        return await self.repo.get_by_type(template_type, user_id)

    async def create_template(self, user_id: str, data: dict):
        return await self.repo.create({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "is_preset": False,
            **data,
        })

    async def update_template(self, template_id: str, user_id: str, data: dict):
        return await self.repo.update(template_id, user_id, data)

    async def delete_template(self, template_id: str, user_id: str) -> bool:
        return await self.repo.delete(template_id, user_id)

    async def duplicate_template(self, template_id: str, user_id: str):
        return await self.repo.duplicate(template_id, user_id)

    async def auto_detect(self, file_bytes: bytes) -> dict:
        """Auto-detect document type and fields. Delegates to detection service."""
        return await self.detection_service.detect(file_bytes)
