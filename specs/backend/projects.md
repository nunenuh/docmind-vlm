# Backend Spec: Projects & Personas

Files: `backend/src/docmind/modules/projects/` — contains `schemas.py`, `services.py`, `repositories.py`, `usecase.py`, `apiv1/handler.py`

See also: [[projects/docmind-vlm/specs/backend/services]] · [[projects/docmind-vlm/specs/backend/api]] · [[projects/docmind-vlm/specs/backend/pipeline-chat]]

---

## Overview

A **Project** groups multiple documents under a shared workspace with an optional **Persona** (configurable AI personality). Users can chat at the project level, with RAG across all documents in the project.

```
Project (workspace)
├── Persona (optional AI personality)
├── Documents (many, via project_id FK)
└── Conversations
    └── Messages (with citations across project docs)
```

Key design decisions:
- Documents gain an optional `project_id` FK — standalone document extraction still works (backwards compatible)
- Personas can be **presets** (system-provided, `user_id=NULL`, `is_preset=True`) or **custom** (user-created)
- Project-level chat uses RAG across all project documents, not just one
- Conversations are scoped to a project, not a single document

---

## Module Structure

```
modules/projects/
├── __init__.py
├── schemas.py        # Pydantic request/response models
├── services.py       # Business logic (no DB access)
├── repositories.py   # DB operations (SQLAlchemy)
├── usecase.py        # Orchestration — wires service + repository + pipeline
└── apiv1/
    ├── __init__.py
    └── handler.py    # API endpoints
```

---

## ORM Models — `dbase/psql/models/`

Add these models alongside the existing `Document`, `Extraction`, etc. models.

```python
"""
New ORM models for Projects & Personas.
Added to docmind/dbase/psql/models/
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Boolean, DateTime, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─────────────────────────────────────────────
# Persona
# ─────────────────────────────────────────────

class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # NULL = system preset
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tone: Mapped[str] = mapped_column(String(30), nullable=False, default="balanced")
    rules: Mapped[list] = mapped_column(JSON, nullable=False, default=list)           # ["rule1", "rule2"]
    boundaries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)      # ["don't do X", ...]
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    projects: Mapped[list["Project"]] = relationship(back_populates="persona")


# ─────────────────────────────────────────────
# Project
# ─────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    persona: Mapped["Persona | None"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(back_populates="project", foreign_keys="[Document.project_id]")
    conversations: Mapped[list["ProjectConversation"]] = relationship(back_populates="project", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# ProjectConversation
# ─────────────────────────────────────────────

class ProjectConversation(Base):
    __tablename__ = "project_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)  # auto-generated from first message
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    project: Mapped["Project"] = relationship(back_populates="conversations")
    messages: Mapped[list["ProjectMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# ProjectMessage
# ─────────────────────────────────────────────

class ProjectMessage(Base):
    __tablename__ = "project_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # [{document_id, page, chunk, text_span}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    conversation: Mapped["ProjectConversation"] = relationship(back_populates="messages")
```

### Document Model Change

Add an optional `project_id` FK to the existing `Document` model:

```python
# Add to existing Document model in docmind/dbase/psql/models/

class Document(Base):
    __tablename__ = "documents"

    # ... existing columns ...

    # NEW: optional project association
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # NEW: relationship
    project: Mapped["Project | None"] = relationship(back_populates="documents")

    # ... existing relationships ...
```

`project_id` is nullable — documents uploaded via `/api/v1/documents` (existing flow) remain standalone. Documents uploaded via `/api/v1/projects/{id}/documents` get the project association.

---

## Relationships

| Parent | Child | Cardinality | FK Column | On Delete |
|--------|-------|-------------|-----------|-----------|
| Project | Document | one-to-many | `documents.project_id` | `SET NULL` |
| Project | ProjectConversation | one-to-many | `project_conversations.project_id` | `CASCADE` |
| Project | Persona | many-to-one | `projects.persona_id` | `SET NULL` |
| ProjectConversation | ProjectMessage | one-to-many | `project_messages.conversation_id` | `CASCADE` |
| Persona | Project | one-to-many | `projects.persona_id` | `SET NULL` |

---

## Endpoint Summary

| Method | Full Path | Auth | Handler |
|--------|-----------|------|---------|
| `POST` | `/api/v1/projects` | JWT | `modules/projects/apiv1/handler.py` |
| `GET` | `/api/v1/projects` | JWT | `modules/projects/apiv1/handler.py` |
| `GET` | `/api/v1/projects/{id}` | JWT | `modules/projects/apiv1/handler.py` |
| `PUT` | `/api/v1/projects/{id}` | JWT | `modules/projects/apiv1/handler.py` |
| `DELETE` | `/api/v1/projects/{id}` | JWT | `modules/projects/apiv1/handler.py` |
| `POST` | `/api/v1/projects/{id}/documents` | JWT | `modules/projects/apiv1/handler.py` |
| `GET` | `/api/v1/projects/{id}/documents` | JWT | `modules/projects/apiv1/handler.py` |
| `DELETE` | `/api/v1/projects/{id}/documents/{doc_id}` | JWT | `modules/projects/apiv1/handler.py` |
| `POST` | `/api/v1/projects/{id}/chat` | JWT (SSE) | `modules/projects/apiv1/handler.py` |
| `GET` | `/api/v1/projects/{id}/conversations` | JWT | `modules/projects/apiv1/handler.py` |
| `GET` | `/api/v1/projects/{id}/conversations/{conv_id}` | JWT | `modules/projects/apiv1/handler.py` |
| `DELETE` | `/api/v1/projects/{id}/conversations/{conv_id}` | JWT | `modules/projects/apiv1/handler.py` |
| `GET` | `/api/v1/personas` | JWT | `modules/projects/apiv1/handler.py` |
| `POST` | `/api/v1/personas` | JWT | `modules/projects/apiv1/handler.py` |
| `PUT` | `/api/v1/personas/{id}` | JWT | `modules/projects/apiv1/handler.py` |
| `DELETE` | `/api/v1/personas/{id}` | JWT | `modules/projects/apiv1/handler.py` |

---

## Pydantic Models — `modules/projects/schemas.py`

```python
"""
docmind/modules/projects/schemas.py

Pydantic request/response models for Projects & Personas.
"""
from datetime import datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Persona Schemas
# ─────────────────────────────────────────────

class PersonaCreate(BaseModel):
    """Request body for creating a custom persona."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    system_prompt: str = Field(..., min_length=1)
    tone: str = Field(default="balanced", max_length=30)
    rules: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)


class PersonaUpdate(BaseModel):
    """Request body for updating a custom persona. All fields optional."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str | None = Field(default=None, min_length=1)
    tone: str | None = Field(default=None, max_length=30)
    rules: list[str] | None = None
    boundaries: list[str] | None = None


class PersonaResponse(BaseModel):
    """Single persona in API responses."""
    id: str
    user_id: str | None  # NULL for presets
    name: str
    description: str
    system_prompt: str
    tone: str
    rules: list[str]
    boundaries: list[str]
    is_preset: bool
    created_at: datetime
    updated_at: datetime


class PersonaListResponse(BaseModel):
    """List of available personas."""
    items: list[PersonaResponse]


# ─────────────────────────────────────────────
# Project Schemas
# ─────────────────────────────────────────────

class ProjectCreate(BaseModel):
    """Request body for creating a project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    persona_id: str | None = None  # UUID of persona to attach


class ProjectUpdate(BaseModel):
    """Request body for updating a project. All fields optional."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    persona_id: str | None = None


class ProjectResponse(BaseModel):
    """Single project in API responses."""
    id: str
    name: str
    description: str | None
    persona_id: str | None
    persona: PersonaResponse | None = None  # Eager-loaded when available
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""
    items: list[ProjectResponse]
    total: int
    page: int
    limit: int


# ─────────────────────────────────────────────
# Project Document Schemas
# ─────────────────────────────────────────────

class ProjectDocumentAdd(BaseModel):
    """Request body for uploading a document to a project."""
    filename: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., pattern="^(pdf|png|jpg|jpeg|tiff|webp)$")
    file_size: int = Field(..., gt=0, le=20_971_520)  # 20MB max
    storage_path: str


# ─────────────────────────────────────────────
# Conversation Schemas
# ─────────────────────────────────────────────

class ProjectChatRequest(BaseModel):
    """Request body for sending a project-level chat message."""
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None  # NULL = start new conversation


class ProjectCitation(BaseModel):
    """Citation referencing a specific document, page, and chunk within a project."""
    document_id: str
    page: int
    chunk: str  # text chunk identifier or content
    text_span: str


class MessageResponse(BaseModel):
    """Single message in a project conversation."""
    id: str
    role: str  # user | assistant
    content: str
    citations: list[ProjectCitation]
    created_at: datetime


class ConversationResponse(BaseModel):
    """Single conversation in API responses."""
    id: str
    project_id: str
    title: str | None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """List of conversations for a project."""
    items: list[ConversationResponse]
    total: int
    page: int
    limit: int


class ConversationDetailResponse(BaseModel):
    """Full conversation with messages."""
    id: str
    project_id: str
    title: str | None
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime
```

---

## Repositories — `modules/projects/repositories.py`

```python
"""
docmind/modules/projects/repositories.py

Database operations for Projects, Personas, and Conversations via SQLAlchemy.
"""
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    Document,
    Persona,
    Project,
    ProjectConversation,
    ProjectMessage,
)

logger = get_logger(__name__)


class PersonaRepository:
    """Repository for persona CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        name: str,
        description: str,
        system_prompt: str,
        tone: str,
        rules: list[str],
        boundaries: list[str],
    ) -> Persona:
        """Insert a new custom persona. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            persona = Persona(
                user_id=user_id,
                name=name,
                description=description,
                system_prompt=system_prompt,
                tone=tone,
                rules=rules,
                boundaries=boundaries,
                is_preset=False,
            )
            session.add(persona)
            await session.commit()
            await session.refresh(persona)
            return persona

    async def get_by_id(self, persona_id: str) -> Persona | None:
        """Get a single persona by ID."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(Persona.id == persona_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_available(self, user_id: str) -> list[Persona]:
        """
        List all personas available to a user.

        Returns system presets (is_preset=True) plus user's custom personas.
        Ordered by is_preset DESC (presets first), then name ASC.
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Persona)
                .where(
                    (Persona.is_preset == True) | (Persona.user_id == user_id)  # noqa: E712
                )
                .order_by(Persona.is_preset.desc(), Persona.name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        persona_id: str,
        user_id: str,
        **kwargs,
    ) -> Persona | None:
        """
        Update a custom persona. Only the owning user can update.
        Returns updated persona, or None if not found / not owned.
        Preset personas cannot be updated.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                Persona.user_id == user_id,
                Persona.is_preset == False,  # noqa: E712
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(persona, key):
                    setattr(persona, key, value)

            persona.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(persona)
            return persona

    async def delete(self, persona_id: str, user_id: str) -> bool:
        """
        Delete a custom persona. Only the owning user can delete.
        Preset personas cannot be deleted. Returns True if deleted.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                Persona.user_id == user_id,
                Persona.is_preset == False,  # noqa: E712
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return False

            await session.delete(persona)
            await session.commit()
            return True


class ProjectRepository:
    """Repository for project CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        name: str,
        description: str | None,
        persona_id: str | None,
    ) -> Project:
        """Insert a new project. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            project = Project(
                user_id=user_id,
                name=name,
                description=description,
                persona_id=persona_id,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return project

    async def get_by_id(self, project_id: str, user_id: str) -> Project | None:
        """Get a single project by ID, scoped to user. Eager-loads persona."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Project)
                .options(selectinload(Project.persona))
                .where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[Project], int]:
        """Get paginated projects for a user. Returns (items, total_count)."""
        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            # Count total
            count_stmt = select(func.count()).select_from(Project).where(
                Project.user_id == user_id
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            # Fetch page with persona eager-loaded
            stmt = (
                select(Project)
                .options(selectinload(Project.persona))
                .where(Project.user_id == user_id)
                .order_by(Project.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def update(
        self,
        project_id: str,
        user_id: str,
        **kwargs,
    ) -> Project | None:
        """Update a project. Returns updated project, or None if not found."""
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()
            if project is None:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(project, key):
                    setattr(project, key, value)

            project.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(project)
            return project

    async def delete(self, project_id: str, user_id: str) -> bool:
        """
        Delete a project and cascade-delete conversations + messages.
        Documents are NOT deleted — their project_id is set to NULL (via FK ondelete=SET NULL).
        Returns True if deleted.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()
            if project is None:
                return False

            # Unlink documents (set project_id to NULL)
            await session.execute(
                update(Document)
                .where(Document.project_id == project_id)
                .values(project_id=None)
            )

            # Delete conversations + messages (cascade via ORM)
            await session.delete(project)
            await session.commit()
            return True

    async def add_document(
        self,
        project_id: str,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Document:
        """Create a new document and associate it with a project."""
        async with AsyncSessionLocal() as session:
            doc = Document(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                storage_path=storage_path,
                project_id=project_id,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            return doc

    async def remove_document(
        self,
        project_id: str,
        document_id: str,
        user_id: str,
    ) -> bool:
        """
        Remove a document from a project by setting project_id to NULL.
        Does NOT delete the document itself. Returns True if updated.
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Document)
                .where(
                    Document.id == document_id,
                    Document.project_id == project_id,
                    Document.user_id == user_id,
                )
                .values(project_id=None)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def list_documents(
        self,
        project_id: str,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[Document], int]:
        """Get paginated documents for a project. Returns (items, total_count)."""
        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            count_stmt = (
                select(func.count())
                .select_from(Document)
                .where(
                    Document.project_id == project_id,
                    Document.user_id == user_id,
                )
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(Document)
                .where(
                    Document.project_id == project_id,
                    Document.user_id == user_id,
                )
                .order_by(Document.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total


class ConversationRepository:
    """Repository for project conversation operations via SQLAlchemy."""

    async def create(
        self,
        project_id: str,
        user_id: str,
        title: str | None = None,
    ) -> ProjectConversation:
        """Create a new conversation for a project."""
        async with AsyncSessionLocal() as session:
            conv = ProjectConversation(
                project_id=project_id,
                user_id=user_id,
                title=title,
            )
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            return conv

    async def get_by_id(
        self,
        conversation_id: str,
        project_id: str,
        user_id: str,
    ) -> ProjectConversation | None:
        """Get a single conversation by ID, scoped to project and user."""
        async with AsyncSessionLocal() as session:
            stmt = select(ProjectConversation).where(
                ProjectConversation.id == conversation_id,
                ProjectConversation.project_id == project_id,
                ProjectConversation.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_project(
        self,
        project_id: str,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[ProjectConversation], int]:
        """Get paginated conversations for a project. Returns (items, total_count)."""
        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            count_stmt = (
                select(func.count())
                .select_from(ProjectConversation)
                .where(
                    ProjectConversation.project_id == project_id,
                    ProjectConversation.user_id == user_id,
                )
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(ProjectConversation)
                .where(
                    ProjectConversation.project_id == project_id,
                    ProjectConversation.user_id == user_id,
                )
                .order_by(ProjectConversation.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def delete(
        self,
        conversation_id: str,
        project_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation and all its messages. Returns True if deleted."""
        async with AsyncSessionLocal() as session:
            stmt = select(ProjectConversation).where(
                ProjectConversation.id == conversation_id,
                ProjectConversation.project_id == project_id,
                ProjectConversation.user_id == user_id,
            )
            result = await session.execute(stmt)
            conv = result.scalar_one_or_none()
            if conv is None:
                return False

            await session.delete(conv)
            await session.commit()
            return True

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> ProjectMessage:
        """Add a message to a conversation. Returns the created message."""
        async with AsyncSessionLocal() as session:
            msg = ProjectMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                citations=citations or [],
            )
            session.add(msg)

            # Update conversation title from first user message
            if role == "user":
                conv_stmt = select(ProjectConversation).where(
                    ProjectConversation.id == conversation_id
                )
                conv_result = await session.execute(conv_stmt)
                conv = conv_result.scalar_one_or_none()
                if conv and conv.title is None:
                    conv.title = content[:100]
                    conv.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(msg)
            return msg

    async def get_messages(
        self,
        conversation_id: str,
    ) -> list[ProjectMessage]:
        """Get all messages for a conversation, ordered by created_at."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ProjectMessage)
                .where(ProjectMessage.conversation_id == conversation_id)
                .order_by(ProjectMessage.created_at)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[ProjectMessage]:
        """Get recent messages for conversation context (capped at limit)."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ProjectMessage)
                .where(ProjectMessage.conversation_id == conversation_id)
                .order_by(ProjectMessage.created_at)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
```

---

## Services — `modules/projects/services.py`

```python
"""
docmind/modules/projects/services.py

Project business logic — persona prompt building, RAG context assembly.
NO direct DB access.
"""
from docmind.core.logging import get_logger
from docmind.dbase.supabase.storage import get_file_bytes
from docmind.library.cv import convert_to_page_images

logger = get_logger(__name__)


class ProjectService:
    """Business logic for project operations (no DB)."""

    @staticmethod
    def build_system_prompt(
        persona_system_prompt: str,
        persona_tone: str,
        persona_rules: list[str],
        persona_boundaries: list[str],
    ) -> str:
        """
        Build the full system prompt from persona configuration.

        Combines the persona's base system prompt with tone, rules,
        and boundary directives into a single LLM system prompt.
        """
        parts = [persona_system_prompt]

        if persona_tone:
            parts.append(f"\nTone: Respond in a {persona_tone} manner.")

        if persona_rules:
            rules_block = "\n".join(f"- {rule}" for rule in persona_rules)
            parts.append(f"\nRules:\n{rules_block}")

        if persona_boundaries:
            boundaries_block = "\n".join(f"- {b}" for b in persona_boundaries)
            parts.append(f"\nBoundaries (DO NOT do the following):\n{boundaries_block}")

        return "\n".join(parts)

    @staticmethod
    def load_document_pages(
        storage_path: str,
        file_type: str,
    ) -> list:
        """Load and convert a single document to page images for VLM context."""
        file_bytes = get_file_bytes(storage_path)
        return convert_to_page_images(file_bytes, file_type)

    @staticmethod
    def default_system_prompt() -> str:
        """Fallback system prompt when no persona is attached to a project."""
        return (
            "You are a helpful document assistant. Answer questions based on "
            "the provided documents. Always cite specific documents and pages "
            "when referencing information. If the answer is not found in the "
            "documents, say so clearly."
        )
```

---

## UseCase — `modules/projects/usecase.py`

```python
"""
docmind/modules/projects/usecase.py

Orchestrates project operations — wires service + repository + pipeline.
"""
import asyncio
import json
from typing import AsyncGenerator

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Document, Extraction, ExtractedField
from docmind.library.pipeline import run_chat_pipeline
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .repositories import ConversationRepository, PersonaRepository, ProjectRepository
from .schemas import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
    PersonaListResponse,
    PersonaResponse,
    ProjectCitation,
    ProjectListResponse,
    ProjectResponse,
)
from .services import ProjectService

logger = get_logger(__name__)


class ProjectUseCase:
    """Orchestrates the full project lifecycle."""

    def __init__(self):
        self.project_repo = ProjectRepository()
        self.persona_repo = PersonaRepository()
        self.conv_repo = ConversationRepository()
        self.service = ProjectService()

    # ── Projects ───────────────────────────────

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str | None,
        persona_id: str | None,
    ) -> ProjectResponse:
        """Create a new project."""
        # Validate persona exists if provided
        if persona_id:
            persona = await self.persona_repo.get_by_id(persona_id)
            if persona is None:
                raise ValueError("Persona not found")

        project = await self.project_repo.create(
            user_id=user_id,
            name=name,
            description=description,
            persona_id=persona_id,
        )
        return self._to_project_response(project)

    async def get_project(
        self,
        user_id: str,
        project_id: str,
    ) -> ProjectResponse | None:
        """Get a single project by ID, scoped to user."""
        project = await self.project_repo.get_by_id(project_id, user_id)
        if project is None:
            return None
        return self._to_project_response(project)

    async def list_projects(
        self,
        user_id: str,
        page: int,
        limit: int,
    ) -> ProjectListResponse:
        """Get paginated list of projects for a user."""
        items, total = await self.project_repo.list_for_user(user_id, page, limit)
        return ProjectListResponse(
            items=[self._to_project_response(p) for p in items],
            total=total,
            page=page,
            limit=limit,
        )

    async def update_project(
        self,
        user_id: str,
        project_id: str,
        **kwargs,
    ) -> ProjectResponse | None:
        """Update a project."""
        project = await self.project_repo.update(project_id, user_id, **kwargs)
        if project is None:
            return None
        return self._to_project_response(project)

    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project and cascade-delete conversations."""
        return await self.project_repo.delete(project_id, user_id)

    # ── Project Documents ──────────────────────

    async def add_document(
        self,
        user_id: str,
        project_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ):
        """Upload a document and associate it with a project."""
        # Verify project exists and belongs to user
        project = await self.project_repo.get_by_id(project_id, user_id)
        if project is None:
            raise ValueError("Project not found")

        return await self.project_repo.add_document(
            project_id=project_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
        )

    async def remove_document(
        self,
        user_id: str,
        project_id: str,
        document_id: str,
    ) -> bool:
        """Remove a document from a project (does not delete the document)."""
        return await self.project_repo.remove_document(project_id, document_id, user_id)

    async def list_documents(
        self,
        user_id: str,
        project_id: str,
        page: int,
        limit: int,
    ):
        """List documents in a project."""
        return await self.project_repo.list_documents(project_id, user_id, page, limit)

    # ── Project Chat ───────────────────────────

    async def send_message(
        self,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: str | None,
    ) -> AsyncGenerator[str, None]:
        """Send a project-level chat message and return an SSE stream."""
        async for event in self._chat_stream(project_id, user_id, message, conversation_id):
            yield event

    async def _chat_stream(
        self,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: str | None,
    ) -> AsyncGenerator[str, None]:
        """Internal SSE stream generator for project chat."""
        token_queue: asyncio.Queue = asyncio.Queue()

        # Step 1: Get or create conversation
        if conversation_id:
            conv = await self.conv_repo.get_by_id(conversation_id, project_id, user_id)
            if conv is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Conversation not found'})}\n\n"
                return
        else:
            conv = await self.conv_repo.create(project_id, user_id)
            yield f"data: {json.dumps({'type': 'conversation_created', 'conversation_id': conv.id})}\n\n"

        # Step 2: Persist user message
        await self.conv_repo.add_message(conv.id, "user", message)

        # Step 3: Load context (all project documents + conversation history)
        try:
            page_images, extracted_fields, conversation_history, system_prompt = (
                await self._load_project_context(project_id, user_id, conv.id)
            )
        except Exception as e:
            logger.error("Failed to load project chat context: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to load project context'})}\n\n"
            return

        # Step 4: Set up streaming callback
        def on_stream(type: str, **kwargs) -> None:
            token_queue.put_nowait({"type": type, **kwargs})

        initial_state = {
            "document_id": project_id,  # project acts as document context
            "user_id": user_id,
            "message": message,
            "page_images": page_images,
            "extracted_fields": extracted_fields,
            "conversation_history": conversation_history,
            "system_prompt": system_prompt,
            "intent": "",
            "intent_confidence": 0.0,
            "relevant_fields": [],
            "re_queried_regions": [],
            "raw_answer": "",
            "answer": "",
            "citations": [],
            "error_message": None,
            "stream_callback": on_stream,
        }

        config = {"configurable": {"thread_id": f"project:{project_id}:{conv.id}"}}
        task = asyncio.create_task(
            asyncio.to_thread(run_chat_pipeline, initial_state, config)
        )

        # Stream events
        while not task.done():
            try:
                event = await asyncio.wait_for(token_queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        # Drain remaining events
        while not token_queue.empty():
            event = token_queue.get_nowait()
            yield f"data: {json.dumps(event)}\n\n"

        # Step 5: Persist assistant response
        result = task.result()
        answer = result.get("answer", "")
        citations = result.get("citations", [])

        assistant_msg = await self.conv_repo.add_message(
            conv.id, "assistant", answer, citations
        )

        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id, 'conversation_id': conv.id})}\n\n"

    async def _load_project_context(
        self,
        project_id: str,
        user_id: str,
        conversation_id: str,
    ) -> tuple[list, list, list[dict], str]:
        """
        Load project context: page images from all docs, extracted fields,
        conversation history, and system prompt from persona.

        Returns:
            Tuple of (page_images, extracted_fields, conversation_history, system_prompt).
        """
        async with AsyncSessionLocal() as session:
            # Load project with persona
            proj_stmt = (
                select(Project)
                .options(selectinload(Project.persona))
                .where(Project.id == project_id, Project.user_id == user_id)
            )
            proj_result = await session.execute(proj_stmt)
            project = proj_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Build system prompt from persona
        if project.persona:
            system_prompt = self.service.build_system_prompt(
                persona_system_prompt=project.persona.system_prompt,
                persona_tone=project.persona.tone,
                persona_rules=project.persona.rules,
                persona_boundaries=project.persona.boundaries,
            )
        else:
            system_prompt = self.service.default_system_prompt()

        # Load all project documents
        docs, _ = await self.project_repo.list_documents(project_id, user_id, page=1, limit=100)

        # Load page images and extracted fields from all documents
        all_page_images = []
        all_extracted_fields = []

        for doc in docs:
            if doc.status == "ready":
                try:
                    images = self.service.load_document_pages(doc.storage_path, doc.file_type)
                    all_page_images.extend(images)
                except Exception as e:
                    logger.warning("Failed to load pages for doc %s: %s", doc.id, e)

                # Load extracted fields
                async with AsyncSessionLocal() as session:
                    ext_stmt = (
                        select(Extraction.id)
                        .where(Extraction.document_id == doc.id)
                        .order_by(Extraction.created_at.desc())
                        .limit(1)
                    )
                    ext_result = await session.execute(ext_stmt)
                    ext_row = ext_result.first()

                    if ext_row:
                        fields_stmt = (
                            select(ExtractedField)
                            .where(ExtractedField.extraction_id == ext_row[0])
                            .order_by(ExtractedField.page_number)
                        )
                        fields_result = await session.execute(fields_stmt)
                        all_extracted_fields.extend(list(fields_result.scalars().all()))

        # Load conversation history
        history_msgs = await self.conv_repo.get_recent_messages(conversation_id)
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_msgs
        ]

        return all_page_images, all_extracted_fields, conversation_history, system_prompt

    # ── Conversations ──────────────────────────

    async def list_conversations(
        self,
        user_id: str,
        project_id: str,
        page: int,
        limit: int,
    ) -> ConversationListResponse:
        """List conversations for a project."""
        items, total = await self.conv_repo.list_for_project(project_id, user_id, page, limit)
        return ConversationListResponse(
            items=[
                ConversationResponse(
                    id=conv.id,
                    project_id=conv.project_id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                )
                for conv in items
            ],
            total=total,
            page=page,
            limit=limit,
        )

    async def get_conversation(
        self,
        user_id: str,
        project_id: str,
        conversation_id: str,
    ) -> ConversationDetailResponse | None:
        """Get a conversation with all its messages."""
        conv = await self.conv_repo.get_by_id(conversation_id, project_id, user_id)
        if conv is None:
            return None

        messages = await self.conv_repo.get_messages(conversation_id)
        return ConversationDetailResponse(
            id=conv.id,
            project_id=conv.project_id,
            title=conv.title,
            messages=[
                MessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    citations=[ProjectCitation(**c) for c in msg.citations] if msg.citations else [],
                    created_at=msg.created_at,
                )
                for msg in messages
            ],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    async def delete_conversation(
        self,
        user_id: str,
        project_id: str,
        conversation_id: str,
    ) -> bool:
        """Delete a conversation and all its messages."""
        return await self.conv_repo.delete(conversation_id, project_id, user_id)

    # ── Personas ───────────────────────────────

    async def list_personas(self, user_id: str) -> PersonaListResponse:
        """List all personas available to a user (presets + custom)."""
        items = await self.persona_repo.list_available(user_id)
        return PersonaListResponse(
            items=[self._to_persona_response(p) for p in items]
        )

    async def create_persona(
        self,
        user_id: str,
        name: str,
        description: str,
        system_prompt: str,
        tone: str,
        rules: list[str],
        boundaries: list[str],
    ) -> PersonaResponse:
        """Create a custom persona."""
        persona = await self.persona_repo.create(
            user_id=user_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tone=tone,
            rules=rules,
            boundaries=boundaries,
        )
        return self._to_persona_response(persona)

    async def update_persona(
        self,
        user_id: str,
        persona_id: str,
        **kwargs,
    ) -> PersonaResponse | None:
        """Update a custom persona."""
        persona = await self.persona_repo.update(persona_id, user_id, **kwargs)
        if persona is None:
            return None
        return self._to_persona_response(persona)

    async def delete_persona(self, user_id: str, persona_id: str) -> bool:
        """Delete a custom persona."""
        return await self.persona_repo.delete(persona_id, user_id)

    # ── Helpers ────────────────────────────────

    @staticmethod
    def _to_project_response(project) -> ProjectResponse:
        """Map ORM Project to ProjectResponse."""
        persona_resp = None
        if project.persona:
            persona_resp = PersonaResponse(
                id=project.persona.id,
                user_id=project.persona.user_id,
                name=project.persona.name,
                description=project.persona.description,
                system_prompt=project.persona.system_prompt,
                tone=project.persona.tone,
                rules=project.persona.rules,
                boundaries=project.persona.boundaries,
                is_preset=project.persona.is_preset,
                created_at=project.persona.created_at,
                updated_at=project.persona.updated_at,
            )

        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            persona_id=project.persona_id,
            persona=persona_resp,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    @staticmethod
    def _to_persona_response(persona) -> PersonaResponse:
        """Map ORM Persona to PersonaResponse."""
        return PersonaResponse(
            id=persona.id,
            user_id=persona.user_id,
            name=persona.name,
            description=persona.description,
            system_prompt=persona.system_prompt,
            tone=persona.tone,
            rules=persona.rules,
            boundaries=persona.boundaries,
            is_preset=persona.is_preset,
            created_at=persona.created_at,
            updated_at=persona.updated_at,
        )
```

---

## Handler — `modules/projects/apiv1/handler.py`

```python
"""
docmind/modules/projects/apiv1/handler.py

API endpoints for Projects, Personas, and Project Chat.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import (
    ConversationDetailResponse,
    ConversationListResponse,
    PersonaCreate,
    PersonaListResponse,
    PersonaResponse,
    PersonaUpdate,
    ProjectChatRequest,
    ProjectCreate,
    ProjectDocumentAdd,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from ..usecase import ProjectUseCase

logger = get_logger(__name__)
router = APIRouter()


# ── Projects ───────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new project workspace."""
    usecase = ProjectUseCase()
    try:
        return await usecase.create_project(
            user_id=current_user["id"],
            name=body.name,
            description=body.description,
            persona_id=body.persona_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List all projects for the current user."""
    usecase = ProjectUseCase()
    return await usecase.list_projects(
        user_id=current_user["id"],
        page=page,
        limit=limit,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get project details by ID."""
    usecase = ProjectUseCase()
    project = await usecase.get_project(
        user_id=current_user["id"],
        project_id=project_id,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update project name, description, or persona."""
    usecase = ProjectUseCase()
    project = await usecase.update_project(
        user_id=current_user["id"],
        project_id=project_id,
        name=body.name,
        description=body.description,
        persona_id=body.persona_id,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a project. Documents are unlinked, not deleted."""
    usecase = ProjectUseCase()
    deleted = await usecase.delete_project(
        user_id=current_user["id"],
        project_id=project_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")


# ── Project Documents ──────────────────────────

@router.post("/{project_id}/documents", status_code=201)
async def add_document_to_project(
    project_id: str,
    body: ProjectDocumentAdd,
    current_user: dict = Depends(get_current_user),
):
    """Upload a document and associate it with a project."""
    usecase = ProjectUseCase()
    try:
        return await usecase.add_document(
            user_id=current_user["id"],
            project_id=project_id,
            filename=body.filename,
            file_type=body.file_type,
            file_size=body.file_size,
            storage_path=body.storage_path,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/documents")
async def list_project_documents(
    project_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List all documents in a project."""
    usecase = ProjectUseCase()
    items, total = await usecase.list_documents(
        user_id=current_user["id"],
        project_id=project_id,
        page=page,
        limit=limit,
    )
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
async def remove_document_from_project(
    project_id: str,
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a document from a project (does not delete the document)."""
    usecase = ProjectUseCase()
    removed = await usecase.remove_document(
        user_id=current_user["id"],
        project_id=project_id,
        document_id=document_id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found in project")


# ── Project Chat ───────────────────────────────

@router.post("/{project_id}/chat")
async def project_chat(
    project_id: str,
    body: ProjectChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a project-level chat message with RAG across all project documents.

    Returns an SSE stream with the assistant response:
        data: {"type": "conversation_created", "conversation_id": "uuid"}
        data: {"type": "token", "content": "The"}
        data: {"type": "token", "content": " invoice"}
        data: {"type": "citation", "citation": {"document_id": "...", "page": 1, ...}}
        data: {"type": "done", "message_id": "uuid", "conversation_id": "uuid"}

    Pass conversation_id in the request body to continue an existing conversation.
    Omit it to start a new one.
    """
    usecase = ProjectUseCase()

    # Verify project exists
    project = await usecase.get_project(
        user_id=current_user["id"],
        project_id=project_id,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    event_stream = usecase.send_message(
        project_id=project_id,
        user_id=current_user["id"],
        message=body.message,
        conversation_id=body.conversation_id,
    )

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Conversations ──────────────────────────────

@router.get("/{project_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    project_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List all conversations for a project."""
    usecase = ProjectUseCase()
    return await usecase.list_conversations(
        user_id=current_user["id"],
        project_id=project_id,
        page=page,
        limit=limit,
    )


@router.get("/{project_id}/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    project_id: str,
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a conversation with all its messages."""
    usecase = ProjectUseCase()
    conv = await usecase.get_conversation(
        user_id=current_user["id"],
        project_id=project_id,
        conversation_id=conversation_id,
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{project_id}/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    project_id: str,
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    usecase = ProjectUseCase()
    deleted = await usecase.delete_conversation(
        user_id=current_user["id"],
        project_id=project_id,
        conversation_id=conversation_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
```

### Persona Routes

Persona endpoints are registered on a separate router and mounted at `/api/v1/personas` in `router.py`:

```python
"""
docmind/modules/projects/apiv1/handler.py (continued)

Persona endpoints — mounted separately at /api/v1/personas in router.py.
"""
persona_router = APIRouter()


@persona_router.get("", response_model=PersonaListResponse)
async def list_personas(
    current_user: dict = Depends(get_current_user),
):
    """List all available personas (system presets + user custom)."""
    usecase = ProjectUseCase()
    return await usecase.list_personas(user_id=current_user["id"])


@persona_router.post("", response_model=PersonaResponse, status_code=201)
async def create_persona(
    body: PersonaCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a custom persona."""
    usecase = ProjectUseCase()
    return await usecase.create_persona(
        user_id=current_user["id"],
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        tone=body.tone,
        rules=body.rules,
        boundaries=body.boundaries,
    )


@persona_router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    body: PersonaUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a custom persona. Preset personas cannot be modified."""
    usecase = ProjectUseCase()
    persona = await usecase.update_persona(
        user_id=current_user["id"],
        persona_id=persona_id,
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        tone=body.tone,
        rules=body.rules,
        boundaries=body.boundaries,
    )
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found or not editable")
    return persona


@persona_router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    persona_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a custom persona. Preset personas cannot be deleted."""
    usecase = ProjectUseCase()
    deleted = await usecase.delete_persona(
        user_id=current_user["id"],
        persona_id=persona_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found or not deletable")
```

---

## Router Registration — `router.py`

Add the new routers to the aggregating `router.py`:

```python
# Add to docmind/router.py

from .modules.projects.apiv1.handler import router as projects_router
from .modules.projects.apiv1.handler import persona_router as personas_router

api_router.include_router(projects_router, prefix="/v1/projects", tags=["Projects"])
api_router.include_router(personas_router, prefix="/v1/personas", tags=["Personas"])
```

---

## Preset Personas — Seed Data

Five system-provided personas are seeded on first startup (or via migration). They have `user_id=NULL` and `is_preset=True`.

```python
PRESET_PERSONAS = [
    {
        "name": "Customer Service Agent",
        "description": "Friendly and patient assistant focused on helping users understand their documents step by step.",
        "system_prompt": (
            "You are a friendly customer service agent helping users understand their documents. "
            "Break down complex information into simple, digestible steps. Always be patient and "
            "encouraging. When referencing document content, cite the specific page and section."
        ),
        "tone": "friendly",
        "rules": [
            "Always cite the source document and page number",
            "Break complex answers into numbered steps",
            "Suggest next steps or related questions the user might want to ask",
            "Use simple, non-technical language unless asked otherwise",
            "Confirm understanding before moving to complex topics",
        ],
        "boundaries": [
            "Do not make assumptions about information not in the documents",
            "Do not provide legal, medical, or financial advice",
            "Do not speculate about document authenticity",
        ],
        "is_preset": True,
    },
    {
        "name": "Technical Expert",
        "description": "Precise and thorough analyst who uses domain-specific terminology and provides detailed explanations.",
        "system_prompt": (
            "You are a technical expert analyzing documents with precision. Use domain-specific "
            "terminology appropriate to the document type. Provide detailed, accurate explanations "
            "with references to specific sections, clauses, or data points in the documents."
        ),
        "tone": "technical",
        "rules": [
            "Use precise domain terminology relevant to the document type",
            "Reference specific sections, page numbers, and data points",
            "Provide detailed explanations with technical depth",
            "Compare and cross-reference data across documents when relevant",
            "Highlight discrepancies or notable patterns in the data",
        ],
        "boundaries": [
            "Do not oversimplify technical content",
            "Do not make claims unsupported by the document data",
            "Do not provide opinions on matters outside the document scope",
        ],
        "is_preset": True,
    },
    {
        "name": "Onboarding Guide",
        "description": "Patient educator who assumes no prior knowledge and walks users through documents step by step.",
        "system_prompt": (
            "You are an onboarding guide helping users who may be seeing these documents for the "
            "first time. Assume no prior knowledge. Explain every term, acronym, and concept. "
            "Use analogies and examples to make content accessible."
        ),
        "tone": "friendly",
        "rules": [
            "Define every technical term and acronym on first use",
            "Use analogies and real-world examples to explain concepts",
            "Break down information into small, manageable pieces",
            "Ask clarifying questions when the user's intent is ambiguous",
            "Provide a brief summary at the end of each explanation",
        ],
        "boundaries": [
            "Do not skip explanations assuming prior knowledge",
            "Do not use jargon without defining it first",
            "Do not overwhelm with too much information at once",
        ],
        "is_preset": True,
    },
    {
        "name": "Legal Advisor",
        "description": "Formal and precise assistant that focuses on clauses, risks, and compliance aspects of documents.",
        "system_prompt": (
            "You are a legal document advisor. Analyze documents with a focus on clauses, terms, "
            "conditions, obligations, and potential risks. Always cite specific sections and clause "
            "numbers. Add appropriate disclaimers about the advisory nature of your responses."
        ),
        "tone": "formal",
        "rules": [
            "Always cite specific clause numbers, sections, and page references",
            "Flag potential risks, ambiguities, or unusual terms",
            "Compare terms against common industry standards when relevant",
            "Add a disclaimer that responses are informational, not legal advice",
            "Highlight key dates, deadlines, and obligations",
        ],
        "boundaries": [
            "Do not provide definitive legal advice or opinions",
            "Do not interpret jurisdiction-specific laws without disclaimers",
            "Do not guarantee legal outcomes based on document content",
            "Do not modify or suggest modifications to legal documents",
        ],
        "is_preset": True,
    },
    {
        "name": "General Assistant",
        "description": "Balanced, adaptive assistant that provides straightforward answers to document questions.",
        "system_prompt": (
            "You are a helpful document assistant. Answer questions clearly and concisely based on "
            "the provided documents. Adapt your communication style to match the user's level of "
            "expertise. Always cite your sources."
        ),
        "tone": "balanced",
        "rules": [
            "Cite specific documents and pages when referencing information",
            "Adapt tone and detail level to match the user's questions",
            "Provide concise answers by default, with detail available on request",
            "Clearly distinguish between information found in documents and general knowledge",
        ],
        "boundaries": [
            "Do not fabricate information not present in the documents",
            "Do not provide professional advice (legal, medical, financial)",
            "Do not share information from one user's documents with another",
        ],
        "is_preset": True,
    },
]
```

---

## Error Handling

| Scenario | HTTP Status | `detail` message |
|----------|-------------|-----------------|
| Project not found | 404 | `"Project not found"` |
| Persona not found | 404 | `"Persona not found or not editable"` |
| Conversation not found | 404 | `"Conversation not found"` |
| Document not in project | 404 | `"Document not found in project"` |
| Invalid persona_id on project create | 400 | `"Persona not found"` |
| Attempt to update/delete preset persona | 404 | `"Persona not found or not deletable"` |
| Missing/invalid JWT | 401 | `"Invalid or expired token"` |
| VLM provider error during chat | 500 | `"Processing failed"` (generic) |

---

## Rules

- **Project delete does NOT delete documents.** Documents have their `project_id` set to `NULL` via `ON DELETE SET NULL`. Only conversations and messages are cascade-deleted.
- **Persona delete does NOT delete projects.** Projects have their `persona_id` set to `NULL` via `ON DELETE SET NULL`.
- **Preset personas are immutable.** `PersonaRepository.update()` and `PersonaRepository.delete()` filter by `is_preset=False`, preventing modification of system presets.
- **Conversation title auto-generated.** The first user message in a conversation sets `title` to the first 100 characters of that message.
- **Conversation history capped at 20 messages** when loading context for the chat pipeline, matching the existing chat module behavior.
- **SSE heartbeats every 30 seconds** prevent proxy/load balancer timeouts, consistent with the existing chat and processing SSE pattern.
- **Project chat loads ALL project documents** (up to 100) for RAG context. Only documents with `status=ready` are included.
- **Services never import from `docmind/modules/{other_module}/`**. The project chat pipeline reuses `run_chat_pipeline` from `library/pipeline` with an extended initial state that includes the persona system prompt.
- **All repository queries filter by `user_id`** to enforce per-user data isolation.
