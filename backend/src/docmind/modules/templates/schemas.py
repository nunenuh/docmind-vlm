"""docmind/modules/templates/schemas.py"""

from pydantic import BaseModel
from typing import Any


class TemplateFieldDef(BaseModel):
    key: str
    label: str
    label_en: str = ""
    type: str = "string"
    validation: str | None = None
    values: list[str] | None = None
    columns: list[str] | None = None


class TemplateSummary(BaseModel):
    """Summary for listing templates."""
    type: str
    name: str
    name_en: str = ""
    description: str = ""
    description_en: str = ""
    category: str = "general"
    required_field_count: int = 0
    optional_field_count: int = 0
    total_field_count: int = 0


class TemplateDetail(BaseModel):
    """Full template with field definitions."""
    type: str
    name: str
    name_en: str = ""
    description: str = ""
    description_en: str = ""
    category: str = "general"
    required_fields: list[TemplateFieldDef | str] = []
    optional_fields: list[TemplateFieldDef | str] = []
    extraction_prompt: str = ""


class TemplateResponse(BaseModel):
    """Backward-compatible response (used by existing handler)."""
    type: str
    name: str
    description: str = ""
    required_fields: list[Any] = []
    optional_fields: list[Any] = []
    name_en: str = ""
    description_en: str = ""
    category: str = "general"
    extraction_prompt: str = ""


class TemplateListResponse(BaseModel):
    items: list[TemplateSummary]
