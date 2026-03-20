"""docmind/modules/personas/apiv1/handler.py"""

from fastapi import APIRouter, Depends, HTTPException

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..repositories import PersonaRepository
from ..schemas import (
    PersonaCreate,
    PersonaResponse,
    PersonaUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


def _to_response(persona: object) -> PersonaResponse:
    """Convert a Persona ORM instance to a response schema."""
    return PersonaResponse(
        id=str(persona.id),  # type: ignore[attr-defined]
        name=persona.name,  # type: ignore[attr-defined]
        description=persona.description,  # type: ignore[attr-defined]
        system_prompt=persona.system_prompt,  # type: ignore[attr-defined]
        tone=persona.tone,  # type: ignore[attr-defined]
        rules=persona.rules,  # type: ignore[attr-defined]
        boundaries=persona.boundaries,  # type: ignore[attr-defined]
        is_preset=persona.is_preset,  # type: ignore[attr-defined]
        created_at=persona.created_at,  # type: ignore[attr-defined]
    )


@router.get("", response_model=list[PersonaResponse])
async def list_personas(
    current_user: dict = Depends(get_current_user),
):
    repo = PersonaRepository()
    personas = await repo.list_for_user(user_id=current_user["id"])
    return [_to_response(p) for p in personas]


@router.post("", response_model=PersonaResponse, status_code=201)
async def create_persona(
    body: PersonaCreate,
    current_user: dict = Depends(get_current_user),
):
    repo = PersonaRepository()
    try:
        persona = await repo.create(
            user_id=current_user["id"],
            name=body.name,
            description=body.description,
            system_prompt=body.system_prompt,
            tone=body.tone,
            rules=body.rules,
            boundaries=body.boundaries,
        )
        return _to_response(persona)
    except Exception as e:
        logger.error("Persona creation failed: %s", e)
        raise HTTPException(status_code=500, detail="Persona creation failed")


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    body: PersonaUpdate,
    current_user: dict = Depends(get_current_user),
):
    repo = PersonaRepository()
    update_fields = body.model_dump(exclude_unset=True)
    if not update_fields:
        # No fields to update — return existing
        persona = await repo.get_by_id(persona_id)
        if persona is None:
            raise HTTPException(status_code=404, detail="Persona not found")
        return _to_response(persona)

    persona = await repo.update(persona_id, current_user["id"], **update_fields)
    if persona is None:
        raise HTTPException(
            status_code=404,
            detail="Persona not found or cannot be modified",
        )
    return _to_response(persona)


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    persona_id: str,
    current_user: dict = Depends(get_current_user),
):
    repo = PersonaRepository()
    deleted = await repo.delete(persona_id, current_user["id"])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Persona not found or cannot be deleted",
        )
