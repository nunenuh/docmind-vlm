"""docmind/modules/templates/schemas.py"""
from pydantic import BaseModel


class TemplateResponse(BaseModel):
    type: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
