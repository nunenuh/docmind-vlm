"""docmind/modules/personas/apiv1/handler.py

Persona CRUD + duplicate. All logic through PersonaUseCase.
"""

from fastapi import APIRouter, Depends, HTTPException

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException, ValidationException

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
    try:
        personas = await usecase.list_personas(user_id=current_user["id"])
        return [_to_response(p) for p in personas]
    except Exception as e:
        logger.error("list_personas error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("create_persona error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    body: PersonaUpdate,
    current_user: dict = Depends(get_current_user),
):
    usecase = PersonaUseCase()
    try:
        update_fields = body.model_dump(exclude_unset=True)
        if not update_fields:
            persona = await usecase.get_persona(persona_id)
            if persona is None:
                raise NotFoundException("Persona not found")
            return _to_response(persona)

        persona = await usecase.update_persona(persona_id, current_user["id"], update_fields)
        if persona is None:
            raise NotFoundException("Persona not found or cannot be modified")
        return _to_response(persona)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("update_persona error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    persona_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = PersonaUseCase()
    try:
        deleted = await usecase.delete_persona(persona_id, current_user["id"])
        if not deleted:
            raise NotFoundException("Persona not found or cannot be deleted")
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_persona error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{persona_id}/duplicate", response_model=PersonaResponse)
async def duplicate_persona(
    persona_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Duplicate a persona (preset or custom) as user's custom persona."""
    usecase = PersonaUseCase()
    try:
        persona = await usecase.duplicate_persona(persona_id, current_user["id"])
        if persona is None:
            raise NotFoundException("Persona not found")
        return _to_response(persona)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("duplicate_persona error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
