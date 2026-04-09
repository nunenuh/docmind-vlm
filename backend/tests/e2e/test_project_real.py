"""
REAL E2E tests for Project + Document + Persona flow.

These tests hit the ACTUAL Supabase database — no mocks.
Tables must exist (run `make migrate` first).

Run: pytest tests/e2e/test_project_real.py -v
Skip: pytest -m "not real_e2e" to exclude these
"""
import pytest

from docmind.core.auth import get_current_user
from docmind.main import create_app
from httpx import ASGITransport, AsyncClient

REAL_USER = {"id": "e2e-real-user-001", "email": "e2e-real@test.com"}

pytestmark = pytest.mark.real_e2e


@pytest.fixture
def real_app():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: REAL_USER
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def real_client(real_app):
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestProjectLifecycleReal:
    """Full project lifecycle: create → get → update → delete."""

    @pytest.mark.asyncio
    async def test_create_project(self, real_client):
        resp = await real_client.post("/api/v1/projects", json={
            "name": "E2E Test Project",
            "description": "Created by real E2E test",
        })
        assert resp.status_code == 201, f"Create failed: {resp.text}"
        data = resp.json()
        assert data["name"] == "E2E Test Project"
        assert "id" in data
        # Store for cleanup
        self.__class__._project_id = data["id"]

    @pytest.mark.asyncio
    async def test_get_project(self, real_client):
        pid = getattr(self.__class__, "_project_id", None)
        if not pid:
            pytest.skip("No project created")

        resp = await real_client.get(f"/api/v1/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "E2E Test Project"

    @pytest.mark.asyncio
    async def test_list_projects(self, real_client):
        resp = await real_client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_update_project(self, real_client):
        pid = getattr(self.__class__, "_project_id", None)
        if not pid:
            pytest.skip("No project created")

        resp = await real_client.put(f"/api/v1/projects/{pid}", json={
            "name": "E2E Updated Project",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "E2E Updated Project"

    @pytest.mark.asyncio
    async def test_delete_project(self, real_client):
        pid = getattr(self.__class__, "_project_id", None)
        if not pid:
            pytest.skip("No project created")

        resp = await real_client.delete(f"/api/v1/projects/{pid}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_deleted_project_returns_404(self, real_client):
        pid = getattr(self.__class__, "_project_id", None)
        if not pid:
            pytest.skip("No project created")

        resp = await real_client.get(f"/api/v1/projects/{pid}")
        assert resp.status_code == 404


class TestDocumentUploadReal:
    """Real document upload and retrieval."""

    @pytest.mark.asyncio
    async def test_upload_document(self, real_client):
        resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("e2e_test.pdf", b"%PDF-1.4 fake content for e2e", "application/pdf")},
        )
        assert resp.status_code == 201, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["filename"] == "e2e_test.pdf"
        assert data["status"] == "uploaded"
        self.__class__._doc_id = data["id"]

    @pytest.mark.asyncio
    async def test_get_uploaded_document(self, real_client):
        doc_id = getattr(self.__class__, "_doc_id", None)
        if not doc_id:
            pytest.skip("No document uploaded")

        resp = await real_client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["filename"] == "e2e_test.pdf"

    @pytest.mark.asyncio
    async def test_list_documents(self, real_client):
        resp = await real_client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_delete_document(self, real_client):
        doc_id = getattr(self.__class__, "_doc_id", None)
        if not doc_id:
            pytest.skip("No document uploaded")

        resp = await real_client.delete(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 204


class TestProjectDocumentFlowReal:
    """Upload doc → create project → add doc to project → list → remove → delete."""

    @pytest.mark.asyncio
    async def test_full_project_document_flow(self, real_client):
        # 1. Upload document
        upload_resp = await real_client.post(
            "/api/v1/documents",
            files={"file": ("flow_test.pdf", b"%PDF-1.4 flow test", "application/pdf")},
        )
        assert upload_resp.status_code == 201, f"Upload: {upload_resp.text}"
        doc_id = upload_resp.json()["id"]

        # 2. Create project
        proj_resp = await real_client.post("/api/v1/projects", json={
            "name": "Flow Test Project",
        })
        assert proj_resp.status_code == 201, f"Create project: {proj_resp.text}"
        proj_id = proj_resp.json()["id"]

        try:
            # 3. Add document to project
            add_resp = await real_client.post(
                f"/api/v1/projects/{proj_id}/documents?document_id={doc_id}"
            )
            assert add_resp.status_code == 201, f"Add doc: {add_resp.text}"

            # 4. List project documents
            list_resp = await real_client.get(f"/api/v1/projects/{proj_id}/documents")
            assert list_resp.status_code == 200
            docs = list_resp.json()
            assert len(docs) >= 1
            assert any(d["id"] == doc_id for d in docs)

            # 5. Remove document from project
            rm_resp = await real_client.delete(
                f"/api/v1/projects/{proj_id}/documents/{doc_id}"
            )
            assert rm_resp.status_code == 204

            # 6. Verify removed
            list_resp2 = await real_client.get(f"/api/v1/projects/{proj_id}/documents")
            docs2 = list_resp2.json()
            assert not any(d["id"] == doc_id for d in docs2)

        finally:
            # Cleanup
            await real_client.delete(f"/api/v1/projects/{proj_id}")
            await real_client.delete(f"/api/v1/documents/{doc_id}")


class TestPersonaFlowReal:
    """Persona CRUD with real database."""

    @pytest.mark.asyncio
    async def test_list_personas(self, real_client):
        resp = await real_client.get("/api/v1/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_custom_persona(self, real_client):
        resp = await real_client.post("/api/v1/personas", json={
            "name": "E2E Test Persona",
            "description": "A test persona",
            "system_prompt": "You are a test assistant.",
            "tone": "friendly",
        })
        assert resp.status_code == 201, f"Create persona: {resp.text}"
        data = resp.json()
        assert data["name"] == "E2E Test Persona"
        assert data["is_preset"] is False
        self.__class__._persona_id = data["id"]

    @pytest.mark.asyncio
    async def test_update_persona(self, real_client):
        pid = getattr(self.__class__, "_persona_id", None)
        if not pid:
            pytest.skip("No persona created")

        resp = await real_client.put(f"/api/v1/personas/{pid}", json={
            "name": "E2E Updated Persona",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "E2E Updated Persona"

    @pytest.mark.asyncio
    async def test_delete_persona(self, real_client):
        pid = getattr(self.__class__, "_persona_id", None)
        if not pid:
            pytest.skip("No persona created")

        resp = await real_client.delete(f"/api/v1/personas/{pid}")
        assert resp.status_code == 204


class TestProjectWithPersonaReal:
    """Create project with persona attached."""

    @pytest.mark.asyncio
    async def test_project_with_persona(self, real_client):
        # 1. Create persona
        persona_resp = await real_client.post("/api/v1/personas", json={
            "name": "Project Persona",
            "system_prompt": "You help with project docs.",
        })
        assert persona_resp.status_code == 201
        persona_id = persona_resp.json()["id"]

        # 2. Create project with persona
        proj_resp = await real_client.post("/api/v1/projects", json={
            "name": "Persona Project",
            "persona_id": persona_id,
        })
        assert proj_resp.status_code == 201
        proj_id = proj_resp.json()["id"]
        assert proj_resp.json()["persona_id"] == persona_id

        # 3. Get project — persona_id should be set
        get_resp = await real_client.get(f"/api/v1/projects/{proj_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["persona_id"] == persona_id

        # Cleanup
        await real_client.delete(f"/api/v1/projects/{proj_id}")
        await real_client.delete(f"/api/v1/personas/{persona_id}")
