"""E2E test: Project CRUD flow."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@dataclass
class FakeProject:
    """Fake project object that Pydantic can serialize via attribute access."""

    id: str
    name: str
    description: str | None
    persona_id: str | None
    document_count: int
    created_at: str
    updated_at: str


class TestProjectFlow:
    """Full project lifecycle through the real FastAPI app."""

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.apiv1.handler.ProjectUseCase")
    async def test_create_list_delete_project(self, MockUseCase, client):
        """Create a project, list projects, then delete."""
        fake_project = FakeProject(
            id="proj-1",
            name="Test Project",
            description="A test project",
            persona_id=None,
            document_count=0,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        fake_list = MagicMock()
        fake_list.items = [fake_project]
        fake_list.total = 1
        fake_list.page = 1
        fake_list.limit = 20

        mock_usecase = MagicMock()
        mock_usecase.create_project = AsyncMock(return_value=fake_project)
        mock_usecase.get_projects = AsyncMock(return_value=fake_list)
        mock_usecase.delete_project = AsyncMock(return_value=True)
        MockUseCase.return_value = mock_usecase

        # 1. Create
        create_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "A test project"},
        )
        assert create_resp.status_code == 201
        project_data = create_resp.json()
        assert project_data["name"] == "Test Project"
        assert project_data["id"] == "proj-1"

        # 2. List
        list_resp = await client.get("/api/v1/projects")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert len(list_data["items"]) >= 1

        # 3. Delete
        del_resp = await client.delete("/api/v1/projects/proj-1")
        assert del_resp.status_code == 204

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.apiv1.handler.ProjectUseCase")
    async def test_get_project_by_id(self, MockUseCase, client):
        """GET /api/v1/projects/{id} returns project details."""
        fake_project = FakeProject(
            id="proj-2",
            name="Another Project",
            description="Details test",
            persona_id=None,
            document_count=3,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        mock_usecase = MagicMock()
        mock_usecase.get_project = AsyncMock(return_value=fake_project)
        MockUseCase.return_value = mock_usecase

        resp = await client.get("/api/v1/projects/proj-2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "proj-2"
        assert data["document_count"] == 3

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.apiv1.handler.ProjectUseCase")
    async def test_get_nonexistent_project_returns_404(self, MockUseCase, client):
        """GET for a missing project returns 404."""
        mock_usecase = MagicMock()
        mock_usecase.get_project = AsyncMock(return_value=None)
        MockUseCase.return_value = mock_usecase

        resp = await client.get("/api/v1/projects/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.apiv1.handler.ProjectUseCase")
    async def test_update_project(self, MockUseCase, client):
        """PUT /api/v1/projects/{id} updates and returns the project."""
        fake_project = FakeProject(
            id="proj-3",
            name="Updated Name",
            description="Updated desc",
            persona_id=None,
            document_count=0,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
        )
        mock_usecase = MagicMock()
        mock_usecase.update_project = AsyncMock(return_value=fake_project)
        MockUseCase.return_value = mock_usecase

        resp = await client.put(
            "/api/v1/projects/proj-3",
            json={"name": "Updated Name", "description": "Updated desc"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    @patch("docmind.modules.projects.apiv1.handler.ProjectUseCase")
    async def test_delete_nonexistent_project_returns_404(self, MockUseCase, client):
        """DELETE for a missing project returns 404."""
        mock_usecase = MagicMock()
        mock_usecase.delete_project = AsyncMock(return_value=False)
        MockUseCase.return_value = mock_usecase

        resp = await client.delete("/api/v1/projects/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_project_validation_rejects_empty_name(self, client):
        """POST /api/v1/projects rejects an empty name."""
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "", "description": "No name"},
        )
        assert resp.status_code == 422  # Pydantic validation error
