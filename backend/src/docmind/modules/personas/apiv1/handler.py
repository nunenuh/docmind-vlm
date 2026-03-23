"""docmind/modules/personas/apiv1/handler.py

Persona CRUD + duplicate. All logic through PersonaUseCase.
"""

from fastapi import APIRouter, Depends, HTTPException

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..usecase import PersonaUseCase
from ..schemas import PersonaCreate, PersonaResponse, PersonaUpdate

logger = get_logger(__name__)
router = APIRouter()


def _to_response(persona: object) -> PersonaResponse:
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
async def list_personas(current_user: dict = Depends(get_current_user)):
    usecase = PersonaUseCase()
    personas = await usecase.list_personas(user_id=current_user["id"])
    return [_to_response(p) for p in personas]


@router.post("", response_model=PersonaResponse, status_code=201)
async def create_persona(
    body: PersonaCreate,
    current_user: dict = Depends(get_current_user),
):
    usecase = PersonaUseCase()
    try:
        persona = await usecase.create_persona(
            user_id=current_user["id"],
            data=body.model_dump(),
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
    usecase = PersonaUseCase()
    update_fields = body.model_dump(exclude_unset=True)
    if not update_fields:
        persona = await usecase.get_persona(persona_id)
        if persona is None:
            raise HTTPException(status_code=404, detail="Persona not found")
        return _to_response(persona)

    persona = await usecase.update_persona(persona_id, current_user["id"], update_fields)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found or cannot be modified")
    return _to_response(persona)


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    persona_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = PersonaUseCase()
    deleted = await usecase.delete_persona(persona_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found or cannot be deleted")


@router.post("/{persona_id}/duplicate", response_model=PersonaResponse)
async def duplicate_persona(
    persona_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Duplicate a persona (preset or custom) as user's custom persona."""
    usecase = PersonaUseCase()
    persona = await usecase.duplicate_persona(persona_id, current_user["id"])
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return _to_response(persona)
