"""Project CRUD usecase — create, read, update, delete projects."""

from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException

from ..protocols import ProjectRepositoryProtocol, PromptServiceProtocol
from ..repositories import ProjectRepository
from ..schemas import (
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from ..services import ProjectPromptService

logger = get_logger(__name__)


class ProjectCRUDUseCase:
    """Orchestrates project CRUD operations."""

    def __init__(
        self,
        repo: ProjectRepositoryProtocol | None = None,
        prompt_service: PromptServiceProtocol | None = None,
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.prompt_service = prompt_service or ProjectPromptService()

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        persona_id: str | None = None,
    ) -> ProjectResponse:
        """Create a new project."""
        sanitized_name = self.prompt_service.validate_project_name(name)
        self.prompt_service.validate_persona_assignment(persona_id)

        project = await self.repo.create(
            user_id=user_id,
            name=sanitized_name,
            description=description,
            persona_id=persona_id,
        )

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            document_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def get_project(
        self, user_id: str, project_id: str
    ) -> ProjectResponse:
        """Get a single project by ID."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            raise NotFoundException("Project not found")

        doc_count = await self.repo.get_document_count(project_id)

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            document_count=doc_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def get_projects(
        self, user_id: str, page: int, limit: int
    ) -> ProjectListResponse:
        """Get paginated projects for a user."""
        items, total = await self.repo.list_for_user(user_id, page, limit)

        response_items = []
        for project in items:
            doc_count = await self.repo.get_document_count(str(project.id))
            response_items.append(
                ProjectResponse(
                    id=str(project.id),
                    name=project.name,
                    description=project.description,
                    persona_id=project.persona_id,
                    document_count=doc_count,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
            )

        return ProjectListResponse(
            items=response_items,
            total=total,
            page=page,
            limit=limit,
        )

    async def update_project(
        self, user_id: str, project_id: str, data: ProjectUpdate
    ) -> ProjectResponse:
        """Update a project."""
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return await self.get_project(user_id, project_id)

        if "name" in update_fields and update_fields["name"] is not None:
            update_fields["name"] = self.prompt_service.validate_project_name(
                update_fields["name"]
            )

        if "persona_id" in update_fields:
            self.prompt_service.validate_persona_assignment(
                update_fields["persona_id"]
            )

        project = await self.repo.update(project_id, user_id, **update_fields)
        if project is None:
            raise NotFoundException("Project not found")

        doc_count = await self.repo.get_document_count(project_id)

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            document_count=doc_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project and all associated data."""
        return await self.repo.delete(project_id, user_id)
