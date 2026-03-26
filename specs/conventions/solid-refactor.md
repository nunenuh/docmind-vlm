# SOLID Refactor Spec

Five targeted refactors to bring the codebase in line with SOLID principles.
Execute in order — each builds on the previous.

---

## 1. Split ProjectUseCase (SRP)

### Problem

`ProjectUseCase` has **6 responsibilities** in 525 lines:
- Project CRUD (create, get, list, update, delete)
- Document management (add, remove, list, reindex)
- Chunk browsing (list_chunks)
- Conversation management (list, get, delete)
- RAG chat streaming (project_chat_stream — 150 lines alone)
- Background RAG indexing (_safe_index, _index_document_for_rag)

### Target

Split into a `usecases/` package with 4 focused classes:

```
modules/projects/usecases/
├── __init__.py           # re-exports all 4
├── project_crud.py       # ProjectCRUDUseCase
├── project_document.py   # ProjectDocumentUseCase
├── project_conversation.py  # ProjectConversationUseCase
└── project_chat.py       # ProjectChatUseCase
```

### Class Responsibilities

**ProjectCRUDUseCase** (~80 lines)
```
Dependencies: ProjectRepository, ProjectPromptService
Methods:
  - create_project(user_id, name, description, persona_id) → ProjectResponse
  - get_project(user_id, project_id) → ProjectResponse
  - get_projects(user_id, page, limit) → ProjectListResponse
  - update_project(user_id, project_id, data) → ProjectResponse
  - delete_project(user_id, project_id) → bool
```

**ProjectDocumentUseCase** (~120 lines)
```
Dependencies: ProjectRepository, ProjectIndexingService
Cross-module (injected): DocumentRepository, DocumentStorageService
Methods:
  - add_document(user_id, project_id, document_id) → bool
  - remove_document(user_id, project_id, document_id) → bool
  - list_documents(user_id, project_id) → list[ProjectDocumentResponse]
  - reindex_document(user_id, project_id, document_id) → int
  - list_chunks(user_id, project_id, document_id?) → dict
```

**ProjectConversationUseCase** (~60 lines)
```
Dependencies: ProjectRepository, ConversationRepository
Methods:
  - list_conversations(user_id, project_id) → list[ConversationResponse]
  - get_conversation(user_id, conversation_id) → ConversationDetailResponse
  - delete_conversation(user_id, conversation_id) → bool
```

**ProjectChatUseCase** (~160 lines)
```
Dependencies: ProjectRepository, ConversationRepository,
              ProjectPromptService, ProjectRAGService, ProjectVLMService
Cross-module (injected): PersonaRepository
Methods:
  - project_chat_stream(project_id, user_id, message, conversation_id?) → AsyncGenerator
```

### Handler Changes

Handler instantiates the specific usecase per endpoint group:

```python
# Before (every endpoint):
usecase = ProjectUseCase()

# After:
# CRUD endpoints
usecase = ProjectCRUDUseCase()

# Document endpoints
usecase = ProjectDocumentUseCase()

# Conversation endpoints
usecase = ProjectConversationUseCase()

# Chat endpoint
usecase = ProjectChatUseCase()
```

### Migration Steps

1. Create `modules/projects/usecases/` package
2. Move methods from `ProjectUseCase` into 4 focused classes
3. Each class gets only the dependencies it needs (not all 6)
4. Update `__init__.py` to re-export all 4 classes
5. Update handler to use the correct usecase per endpoint
6. Delete old `usecase.py`
7. Update test imports

---

## 2. Define Protocols (DIP + ISP)

### Problem

All services and repositories are concrete classes. No contracts/interfaces.
- Usecases depend on concrete `ProjectRepository`, not an abstraction
- Can't swap implementations without modifying code
- Tests must mock concrete classes instead of implementing test doubles

### Target

Create a `protocols.py` in each module defining the contracts:

```
modules/{name}/protocols.py
```

### Protocol Definitions

**Shared pattern** — every repository and service gets a Protocol:

```python
# modules/documents/protocols.py
from typing import Protocol

class DocumentRepositoryProtocol(Protocol):
    async def create(self, user_id: str, filename: str, ...) -> Document: ...
    async def get_by_id(self, document_id: str, user_id: str) -> Document | None: ...
    async def list_for_user(self, user_id: str, page: int, limit: int, ...) -> tuple[list, int]: ...
    async def search(self, user_id: str, ...) -> tuple[list, int]: ...
    async def delete(self, document_id: str, user_id: str) -> str | None: ...
    async def update_status(self, document_id: str, status: str, **kwargs: object) -> None: ...

class StorageServiceProtocol(Protocol):
    def upload_file(self, user_id: str, document_id: str, ...) -> str: ...
    def load_file_bytes(self, storage_path: str) -> bytes: ...
    def delete_storage_file(self, storage_path: str) -> None: ...
    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str: ...
```

**Usecase constructor uses Protocol types:**

```python
# Before
class DocumentUseCase:
    def __init__(self, repo: DocumentRepository | None = None):
        self.repo = repo or DocumentRepository()

# After
class DocumentUseCase:
    def __init__(self, repo: DocumentRepositoryProtocol | None = None):
        self.repo = repo or DocumentRepository()
```

### Modules That Need Protocols

| Module | Protocols needed |
|--------|-----------------|
| `documents/` | `DocumentRepositoryProtocol`, `StorageServiceProtocol` |
| `extractions/` | `ExtractionRepositoryProtocol`, `PipelineServiceProtocol`, `ClassificationServiceProtocol`, `ConfidenceServiceProtocol` |
| `projects/` | `ProjectRepositoryProtocol`, `ConversationRepositoryProtocol`, `PromptServiceProtocol`, `RAGServiceProtocol`, `IndexingServiceProtocol`, `VLMServiceProtocol` |
| `rag/` | `ChunkRepositoryProtocol`, `IndexingServiceProtocol`, `RetrievalServiceProtocol`, `QueryServiceProtocol` |
| `chat/` | `ChatRepositoryProtocol`, `ChatServiceProtocol` |
| `templates/` | `TemplateRepositoryProtocol`, `FieldServiceProtocol`, `DetectionServiceProtocol` |
| `personas/` | `PersonaRepositoryProtocol`, `PersonaServiceProtocol` |

### Rules

- Protocols go in `protocols.py` per module (not a shared file)
- Protocols define ONLY the methods that the usecase actually calls
- Protocols use `typing.Protocol` (structural subtyping — no inheritance needed)
- Concrete classes don't need to explicitly inherit from Protocol
- Cross-module references use the Protocol from the other module

### Migration Steps

1. Create `protocols.py` in each module
2. Define Protocol for each repository and service
3. Update usecase constructors to use Protocol types in type hints
4. Concrete classes remain unchanged (structural subtyping)
5. Update tests to verify Protocol compliance

---

## 3. Inject Cross-Module Dependencies (DIP)

### Problem

Usecases create other modules' repositories inside methods:

```python
# projects/usecase.py line 197 — hidden dependency
async def _index_document_for_rag(self, ...):
    from docmind.modules.documents.repositories import DocumentRepository
    from docmind.modules.documents.services import DocumentStorageService
    doc_repo = DocumentRepository()
    storage_service = DocumentStorageService()
```

```python
# projects/usecase.py line 395 — hidden dependency
async def project_chat_stream(self, ...):
    from docmind.modules.personas.repositories import PersonaRepository
    persona_repo = PersonaRepository()
```

```python
# projects/handler.py line 133 — handler creates cross-module repo
from docmind.modules.documents.repositories import DocumentRepository
doc_repo = DocumentRepository()
```

### Target

All cross-module dependencies are **constructor-injected** using Protocols from spec #2.

```python
# After — dependencies visible in constructor
class ProjectDocumentUseCase:
    def __init__(
        self,
        repo: ProjectRepositoryProtocol | None = None,
        indexing_service: IndexingServiceProtocol | None = None,
        doc_repo: DocumentRepositoryProtocol | None = None,          # cross-module
        storage_service: StorageServiceProtocol | None = None,       # cross-module
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.indexing_service = indexing_service or ProjectIndexingService()
        self.doc_repo = doc_repo or DocumentRepository()
        self.storage_service = storage_service or DocumentStorageService()
```

### Current Hidden Dependencies

| UseCase | Hidden import | Should be |
|---------|--------------|-----------|
| `ProjectUseCase._index_document_for_rag` | `DocumentRepository`, `DocumentStorageService` | Constructor of `ProjectDocumentUseCase` |
| `ProjectUseCase._index_document_for_rag` | `DocumentStorageService` | Constructor of `ProjectDocumentUseCase` |
| `ProjectUseCase.reindex_document` | `DocumentStorageService` | Constructor of `ProjectDocumentUseCase` |
| `ProjectUseCase.project_chat_stream` | `PersonaRepository` | Constructor of `ProjectChatUseCase` |
| `ExtractionUseCase._processing_stream` | `DocumentRepository`, `DocumentStorageService` | Constructor of `ExtractionUseCase` |
| `ExtractionUseCase._processing_stream` | `TemplateRepository` | Constructor of `ExtractionUseCase` |
| `ExtractionUseCase.classify_document` | `DocumentRepository`, `DocumentStorageService`, `TemplateRepository` | Constructor of `ExtractionUseCase` |
| `ChatUseCase` (module level) | `DocumentRepository`, `DocumentStorageService` | Already injected (good!) |

### Handler Cross-Module Fix

```python
# Before (handler.py line 133):
from docmind.modules.documents.repositories import DocumentRepository
doc_repo = DocumentRepository()
doc = await doc_repo.get_by_id(document_id, current_user["id"])

# After — handler calls usecase, usecase has the dependency:
usecase = ProjectDocumentUseCase()
result = await usecase.add_document(user_id=current_user["id"], ...)
```

The handler should NEVER import from another module's repository directly.

### Migration Steps

1. For each hidden import, move to constructor parameter
2. Use Protocol types from spec #2 for the parameter type hints
3. Default to concrete implementation (backward compat)
4. Remove all lazy `from docmind.modules.X import Y` inside methods
5. Remove all cross-module repo instantiation from handlers

---

## 4. Split ExtractionUseCase (SRP)

### Problem

`ExtractionUseCase` bundles 3 concerns:
- **Trigger** extraction pipeline (SSE streaming, 130 lines)
- **Classify** document type (30 lines)
- **Read** extraction results, audit trails, overlays, comparisons (100 lines)

### Target

```
modules/extractions/usecases/
├── __init__.py
├── process.py           # ExtractionProcessUseCase — trigger + classify
└── results.py           # ExtractionResultsUseCase — read results, audit, overlay, comparison
```

### Class Responsibilities

**ExtractionProcessUseCase** (~170 lines)
```
Dependencies: ExtractionPipelineService, ClassificationService
Cross-module (injected): DocumentRepository, DocumentStorageService, TemplateRepository
Methods:
  - trigger_processing(document_id, user_id, template_type?) → AsyncGenerator
  - classify_document(document_id, user_id) → dict
```

**ExtractionResultsUseCase** (~100 lines)
```
Dependencies: ExtractionRepository, ConfidenceService
Methods:
  - get_extraction(document_id) → ExtractionResponse
  - get_audit_trail(document_id) → list[AuditEntryResponse]
  - get_overlay_data(document_id) → list[OverlayRegion]
  - get_comparison(document_id) → ComparisonResponse
```

### Handler Changes

```python
# Process endpoint → ExtractionProcessUseCase
@router.post("/{document_id}/process")
async def process_document(...):
    usecase = ExtractionProcessUseCase()
    ...

# Read endpoints → ExtractionResultsUseCase
@router.get("/{document_id}")
async def get_extraction(...):
    usecase = ExtractionResultsUseCase()
    ...
```

### Migration Steps

1. Create `modules/extractions/usecases/` package
2. Move trigger/classify methods → `process.py`
3. Move read methods → `results.py`
4. Update handler to use the correct usecase
5. Delete old `usecase.py`

---

## 5. DI Factory for Handlers (DIP)

### Problem

Every handler endpoint creates usecases with `UseCase()`:

```python
@router.get("")
async def list_projects(...):
    usecase = ProjectUseCase()  # hardcoded, every time
    return await usecase.get_projects(...)
```

- No way to inject test doubles at the handler level
- Can't swap implementations globally
- Each endpoint creates new instances (no singleton/scoped control)

### Target

Use FastAPI's `Depends()` pattern with a factory function per module:

```python
# modules/projects/dependencies.py

from functools import lru_cache
from .usecases import ProjectCRUDUseCase, ProjectDocumentUseCase, ...

def get_project_crud_usecase() -> ProjectCRUDUseCase:
    return ProjectCRUDUseCase()

def get_project_document_usecase() -> ProjectDocumentUseCase:
    return ProjectDocumentUseCase()

def get_project_conversation_usecase() -> ProjectConversationUseCase:
    return ProjectConversationUseCase()

def get_project_chat_usecase() -> ProjectChatUseCase:
    return ProjectChatUseCase()
```

```python
# modules/projects/apiv1/handler.py

from ..dependencies import get_project_crud_usecase

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    usecase: ProjectCRUDUseCase = Depends(get_project_crud_usecase),
):
    return await usecase.create_project(
        user_id=current_user["id"],
        name=body.name,
        ...
    )
```

### Benefits

- **Testing**: Override dependency in test client:
  ```python
  app.dependency_overrides[get_project_crud_usecase] = lambda: mock_usecase
  ```
- **Scoping**: Can make usecases request-scoped, singleton, etc.
- **Consistency**: One place to wire up all dependencies per module

### Modules That Need `dependencies.py`

| Module | Factory functions |
|--------|------------------|
| `projects/` | `get_project_crud_usecase`, `get_project_document_usecase`, `get_project_conversation_usecase`, `get_project_chat_usecase` |
| `documents/` | `get_document_usecase` |
| `extractions/` | `get_extraction_process_usecase`, `get_extraction_results_usecase` |
| `rag/` | `get_rag_usecase` |
| `chat/` | `get_chat_usecase` |
| `templates/` | `get_template_usecase` |
| `personas/` | `get_persona_usecase` |
| `analytics/` | `get_analytics_usecase` |

### Migration Steps

1. Create `dependencies.py` in each module
2. Define factory functions that return usecase instances
3. Update handler endpoints to use `Depends(get_X_usecase)`
4. Remove `usecase = XUseCase()` from handler bodies
5. Add `dependency_overrides` pattern to test conftest

---

## Execution Order

```
Spec #2 (Protocols)     ← foundation, no breaking changes
    ↓
Spec #1 (Split ProjectUseCase) + Spec #4 (Split ExtractionUseCase)
    ↓                              ↓
Spec #3 (Inject cross-module deps)
    ↓
Spec #5 (DI factory for handlers)
```

**Spec #2 first** because Protocols don't change any behavior — they just add type contracts. Then split usecases (#1, #4) which uses those Protocols. Then wire up DI (#3, #5).

## Rules

- Each spec is a separate PR
- Run full test suite after each spec
- No behavior changes — only structural refactoring
- Keep backward-compat aliases during transition (remove in follow-up)
- `__init__.py` re-exports preserve existing import paths
