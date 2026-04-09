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
    required: bool = True


class TemplateSummary(BaseModel):
    id: str
    type: str
    name: str
    name_en: str = ""
    description: str = ""
    description_en: str = ""
    category: str = "general"
    is_preset: bool = False
    required_field_count: int = 0
    optional_field_count: int = 0
    total_field_count: int = 0


class TemplateDetail(BaseModel):
    id: str
    type: str
    name: str
    name_en: str = ""
    description: str = ""
    description_en: str = ""
    category: str = "general"
    is_preset: bool = False
    fields: list[Any] = []
    extraction_prompt: str = ""


class TemplateCreateRequest(BaseModel):
    type: str
    name: str
    name_en: str | None = None
    description: str | None = None
    description_en: str | None = None
    category: str | None = "custom"
    fields: list[TemplateFieldDef] | None = None
    extraction_prompt: str | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    name_en: str | None = None
    description: str | None = None
    description_en: str | None = None
    category: str | None = None
    fields: list[Any] | None = None
    extraction_prompt: str | None = None


class AutoDetectResponse(BaseModel):
    document_type: str
    document_name: str
    language: str = "unknown"
    confidence: float = 0.0
    detected_fields: list[Any] = []
    suggested_template: dict = {}


class TemplateListResponse(BaseModel):
    items: list[TemplateSummary]
