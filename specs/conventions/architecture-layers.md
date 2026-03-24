# Architecture Layers — Strict Boundaries

## Overview

Every module follows a strict layered architecture. Each layer has a clear responsibility and boundary. Violations (e.g., usecase calling library directly) are **bugs**.

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  handler.py                                          │
│  - Parse HTTP (params, body, auth)                   │
│  - Call usecase                                      │
│  - Return HTTP response (status code, serialization) │
│  - NO business logic, NO I/O                         │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  usecase.py                                          │
│  - Orchestration + Business Logic                    │
│  - Instantiates services + repositories in __init__  │
│  - Calls service methods + repository methods        │
│  - Business decisions (validation, authorization)    │
│  - Error handling, retry logic, flow control         │
│  - SSE streaming coordination                        │
│  - NEVER calls library directly                      │
│  - NEVER does I/O directly                           │
└──────────┬─────────────────────┬────────────────────┘
           │                     │
           ▼                     ▼
┌──────────────────┐  ┌──────────────────────────────┐
│  repository.py   │  │  services.py (multiple)       │
│  - Data storage  │  │  - Sub-business logic         │
│  - DB queries    │  │  - External API calls         │
│  - File storage  │  │  - Library calls              │
│  - Can call      │  │  - Prompt building            │
│    library if    │  │  - Data transformation        │
│    needed        │  │                               │
│                  │  │  Calls library/* for:         │
│  Types:          │  │  - VLM providers              │
│  - DB repo       │  │  - RAG operations              │
│  - Storage repo  │  │  - CV processing               │
│                  │  │  - Embedding                   │
└────────┬─────────┘  └──────────────┬────────────────┘
         │                           │
         │         ┌─────────────────┘
         │         │
         ▼         ▼
┌──────────────────────────────┐
│  library/*                    │
│  - Shared, reusable code      │
│  - providers/ (VLM APIs)      │
│  - rag/ (chunking, embedding) │
│  - pipeline/ (LangGraph)      │
│  - cv/ (image processing)     │
│  - templates/ (file loader)   │
│                               │
│  NEVER imports from modules/  │
└──────────────────────────────┘
```

---

## Layer Rules

### handler.py
```
CAN:     Parse HTTP, call usecase, return response
CANNOT:  Business logic, DB queries, file I/O, call service, call library, call repository
```

### usecase.py
```
CAN:     Orchestration + business logic
         - Instantiate services + repositories in __init__
         - Call their methods, coordinate the flow
         - Business decisions (if/else, validation, authorization)
         - Error handling and retry logic
         - Data transformation between layers
         - SSE streaming coordination
CANNOT:  Call library directly, do DB queries, do file I/O, do API calls, use @staticmethod
```

### services.py
```
CAN:     Sub-business logic (delegated by usecase)
         - Call library modules for low-level operations
         - Call external APIs (VLM providers, embedding APIs)
         - Data transformation, formatting, prompt building
         - Encapsulate complex operations into simple method calls
         - Usecase says WHAT to do, service knows HOW to do it
CANNOT:  DB queries (that's repository), HTTP parsing (that's handler)
         Make high-level business decisions (that's usecase)
```

**Usecase vs Service:**
- Usecase = **high-level business logic** ("if document not processed, classify then extract then store")
- Service = **sub-business logic** ("here's how to classify: convert to image, call VLM, parse response")

### repositories.py
```
CAN:     Database queries (SQLAlchemy), file storage operations (Supabase Storage)
         Call library if needed (e.g., storage helpers, data serialization)
CANNOT:  Business logic, external API calls (VLM, embedding), prompt building
```

### schemas.py
```
CAN:     Pydantic models for request/response, type definitions
CANNOT:  Logic of any kind
```

### library/*
```
CAN:     Shared reusable code, provider abstractions, RAG components, CV tools
CANNOT:  Import from modules/, access module-specific state
```

---

## Repository Types

Repository is **any data storage**, not just database:

| Repository | Storage | Examples |
|-----------|---------|----------|
| `DocumentRepository` | PostgreSQL | CRUD documents table |
| `StorageRepository` | Supabase Storage | Upload/download files |
| `ExtractionRepository` | PostgreSQL | CRUD extractions, fields |
| `ChatRepository` | PostgreSQL | CRUD messages, citations |
| `ChunkRepository` | PostgreSQL | CRUD page_chunks (RAG) |

---

## Service Guidelines

- **Many small services > one big service**
- Each service has a focused responsibility
- Services are proper classes with `__init__`, NOT static methods
- Services call library modules for low-level operations
- If library doesn't have what you need, add it to library first, then call from service

| Service | Responsibility | Calls Library |
|---------|---------------|---------------|
| `VLMService` | VLM provider interactions (extract, classify, chat, stream) | `library/providers/` |
| `RAGService` | RAG operations (embed, retrieve, rewrite query) | `library/rag/` |
| `IndexingService` | Document indexing (extract text, chunk, embed, store) | `library/rag/indexer` |
| `ChatPromptService` | Build chat prompts, format fields, slice history | — (pure logic) |
| `ExtractionService` | Extraction pipeline orchestration | `library/pipeline/` |
| `CVService` | Image preprocessing (deskew, quality) | `library/cv/` |
| `TemplateDetectionService` | Auto-detect document type from image | `library/providers/` |

---

## Instantiation Pattern

Services and repositories are instantiated in usecase `__init__`:

```python
class ProjectUseCase:
    def __init__(self) -> None:
        # Repositories (data access)
        self.project_repo = ProjectRepository()
        self.conversation_repo = ConversationRepository()
        self.storage_repo = StorageRepository()

        # Services (business logic + external calls)
        self.rag_service = RAGService()
        self.vlm_service = VLMService()
        self.prompt_service = ProjectPromptService()

    async def project_chat_stream(self, ...):
        # Orchestrate only — delegate everything
        project = await self.project_repo.get_by_id(...)

        rewritten = await self.rag_service.rewrite_query(message, history)
        chunks = await self.rag_service.retrieve(project_id, rewritten)

        context = self.prompt_service.build_context(chunks)
        system_prompt = self.prompt_service.build_system_prompt(persona, docs)

        async for token in self.vlm_service.stream_chat(system_prompt, context, message):
            yield token
```

---

## What NOT To Do

```python
# BAD: usecase calls library directly
class ProjectUseCase:
    async def chat(self):
        from docmind.library.providers.factory import get_vlm_provider  # WRONG
        provider = get_vlm_provider()  # WRONG
        response = await provider.chat(...)  # WRONG

# BAD: usecase uses @staticmethod
class ChatUseCase:
    @staticmethod  # WRONG
    def format_fields(fields):
        ...

# BAD: handler calls repository
@router.get("/projects/{id}/chunks")
async def list_chunks(project_id: str):
    async with AsyncSessionLocal() as session:  # WRONG — should go through usecase → repo
        ...

# BAD: service does DB queries
class ChatService:
    async def get_history(self):
        async with AsyncSessionLocal() as session:  # WRONG — that's repository's job
            ...
```

---

## Flow Diagrams

### Document Upload Flow

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant UseCase
    participant DocService
    participant StorageRepo
    participant DocRepo

    Client->>Handler: POST /documents (file)
    Handler->>UseCase: create_document(user_id, file)
    UseCase->>DocService: validate_file(file)
    DocService-->>UseCase: validated
    UseCase->>StorageRepo: upload(file_bytes, path)
    StorageRepo-->>UseCase: storage_path
    UseCase->>DocRepo: create(user_id, filename, storage_path)
    DocRepo-->>UseCase: document
    UseCase-->>Handler: document
    Handler-->>Client: 201 DocumentResponse
```

### Document Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant UseCase
    participant ExtractionService
    participant VLMService
    participant DocRepo

    Client->>Handler: POST /documents/{id}/process (SSE)
    Handler->>UseCase: trigger_processing(doc_id)
    UseCase->>DocRepo: get_by_id(doc_id)
    DocRepo-->>UseCase: document
    UseCase->>DocRepo: update_status("processing")
    UseCase->>ExtractionService: classify_document(file_bytes)
    ExtractionService->>VLMService: classify(image)
    VLMService-->>ExtractionService: detected_type
    ExtractionService-->>UseCase: template_type
    UseCase->>ExtractionService: run_pipeline(file_bytes, template_type)
    ExtractionService-->>UseCase: extracted_fields (streaming SSE)
    UseCase->>DocRepo: update_status("ready")
    UseCase-->>Handler: SSE stream
    Handler-->>Client: SSE events
```

### Project RAG Chat Flow

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant UseCase
    participant RAGService
    participant VLMService
    participant PromptService
    participant ProjectRepo
    participant ConvRepo

    Client->>Handler: POST /projects/{id}/chat (SSE)
    Handler->>UseCase: project_chat_stream(project_id, message)
    UseCase->>ProjectRepo: get_by_id(project_id)
    UseCase->>ConvRepo: create_or_get_conversation()
    UseCase->>ConvRepo: add_message("user", message)

    UseCase->>RAGService: rewrite_query(message, history)
    RAGService-->>UseCase: rewritten_query

    UseCase->>RAGService: retrieve(project_id, rewritten_query)
    RAGService-->>UseCase: chunks

    UseCase->>PromptService: build_context(chunks)
    PromptService-->>UseCase: context_text, citations

    UseCase->>ProjectRepo: list_documents(project_id)
    UseCase->>PromptService: build_system_prompt(persona, docs)
    PromptService-->>UseCase: system_prompt

    UseCase->>VLMService: stream_chat(system_prompt, context, message)
    loop token streaming
        VLMService-->>UseCase: thinking/answer tokens
        UseCase-->>Handler: SSE event
        Handler-->>Client: SSE data
    end

    UseCase->>ConvRepo: add_message("assistant", answer)
    UseCase-->>Handler: SSE done
    Handler-->>Client: SSE done
```

### Document Upload to Project + RAG Indexing

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant UseCase
    participant DocService
    participant IndexingService
    participant StorageRepo
    participant DocRepo
    participant ChunkRepo

    Client->>Handler: POST /projects/{id}/documents (file)
    Handler->>UseCase: add_document(project_id, file)

    UseCase->>DocService: validate_file(file)
    UseCase->>StorageRepo: upload(file_bytes, path)
    StorageRepo-->>UseCase: storage_path
    UseCase->>DocRepo: create(user_id, filename, storage_path, project_id)
    DocRepo-->>UseCase: document

    UseCase->>IndexingService: index_document(doc_id, project_id, file_bytes)
    IndexingService->>IndexingService: extract_text(file_bytes)
    IndexingService->>IndexingService: chunk_pages(pages)
    IndexingService->>IndexingService: embed_texts(chunks)
    IndexingService->>ChunkRepo: store_chunks(chunks_with_embeddings)
    ChunkRepo-->>IndexingService: stored
    IndexingService-->>UseCase: chunk_count

    UseCase-->>Handler: document + chunk_count
    Handler-->>Client: 200 response
```

### Template Auto-Detect Flow

```mermaid
sequenceDiagram
    participant Client
    participant Handler
    participant UseCase
    participant TemplateDetectionService
    participant VLMService
    participant TemplateRepo

    Client->>Handler: POST /templates/detect (file)
    Handler->>UseCase: auto_detect(file_bytes)
    UseCase->>TemplateDetectionService: detect(file_bytes)
    TemplateDetectionService->>VLMService: classify(image)
    VLMService-->>TemplateDetectionService: document_type
    TemplateDetectionService->>VLMService: extract_fields(image)
    VLMService-->>TemplateDetectionService: detected_fields
    TemplateDetectionService-->>UseCase: detection_result
    UseCase-->>Handler: AutoDetectResponse
    Handler-->>Client: 200 JSON
```

---

## Module Structure Template

Every module MUST have:

```
modules/{name}/
├── __init__.py
├── schemas.py              # Pydantic request/response models
├── repositories.py         # Database + storage access
├── services.py             # Business logic + library/API calls (can be multiple files)
├── usecase.py              # Orchestration only
└── apiv1/
    ├── __init__.py
    └── handler.py           # HTTP interface
```

Services can be split into multiple files if they have different responsibilities:

```
modules/projects/
├── services/
│   ├── __init__.py
│   ├── prompt_service.py    # Prompt building
│   ├── rag_service.py       # RAG operations
│   └── indexing_service.py  # Document indexing
```

Or kept in one `services.py` with multiple classes if the module is small.
