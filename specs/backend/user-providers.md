# Backend Spec: User-Configurable AI Providers (BYOK)

Files: `backend/src/docmind/modules/settings/`, `backend/src/docmind/core/encryption.py`, `backend/src/docmind/library/providers/factory.py` (modified)

See also: [[projects/docmind-vlm/specs/backend/providers]] . [[projects/docmind-vlm/specs/backend/services]] . [[projects/docmind-vlm/specs/backend/api]]

---

## Responsibility

| Component | Does |
|-----------|------|
| `core/encryption.py` | Fernet-based encrypt/decrypt helpers. Reads `ENCRYPTION_KEY` from settings. Never imported outside backend. |
| `modules/settings/apiv1/handler.py` | FastAPI route handlers for provider CRUD + test. Thin layer: validate, delegate, serialize. |
| `modules/settings/schemas.py` | Pydantic request/response models for provider configuration |
| `modules/settings/usecase.py` | Orchestrates service + repository calls. Handles encrypt-before-store and decrypt-at-read. |
| `modules/settings/services.py` | Business logic: provider testing, model listing, key masking. NO DB access. |
| `modules/settings/repositories.py` | SQLAlchemy CRUD for `user_provider_configs` table. Always filters by `user_id`. |
| `library/providers/factory.py` | Modified to accept optional `user_id`. Resolves user config or falls back to system default. |

---

## Data Model

### ORM: `UserProviderConfig`

Table: `user_provider_configs`

```python
class UserProviderConfig(Base):
    __tablename__ = "user_provider_configs"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)       # "vlm" | "embedding"
    provider_name: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)       # "dashscope" | "openai" | "google" | "ollama"
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)          # Fernet-encrypted
    model_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)         # e.g. "gpt-4o", "qwen-vl-max"
    base_url: Mapped[str | None] = mapped_column(VARCHAR(500), nullable=True)     # Only for Ollama / self-hosted
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)            # True after successful test
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "provider_type", name="uq_user_provider_type"),
    )
```

**Constraints:**
- One config per `(user_id, provider_type)` pair. A user can have at most one VLM config and one embedding config.
- `provider_type` is checked at the schema level via enum, not a DB check constraint.
- `encrypted_api_key` stores the Fernet-encrypted ciphertext. Never stored as plaintext.

---

## Encryption

### `core/encryption.py`

Uses `cryptography.Fernet` (symmetric AES-128-CBC with HMAC authentication).

```python
from cryptography.fernet import Fernet
from docmind.core.config import get_settings


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the ENCRYPTION_KEY from settings."""
    key = get_settings().ENCRYPTION_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not set. Generate one with Fernet.generate_key().")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns the original plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
```

### Settings Addition

Add to `core/config.py` `Settings` class:

```python
# Encryption
ENCRYPTION_KEY: str = Field(default="", description="Fernet key for encrypting user API keys. Generate with Fernet.generate_key()")
```

### Key Lifecycle

1. User submits API key via `PUT /settings/providers/vlm`
2. Usecase calls `encrypt(api_key)` before storing
3. Key stored as ciphertext in `encrypted_api_key` column
4. On provider instantiation: `decrypt(encrypted_api_key)` produces the original key
5. Decrypted key is passed directly to provider constructor. Never held in memory beyond the provider instance scope.

---

## API Endpoints

All endpoints under `/api/v1/settings/providers`. Router is registered in `modules/settings/apiv1/handler.py` and mounted at `/v1/settings` in `router.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/settings/providers` | JWT | Get user's current provider configs (API key masked) |
| `PUT` | `/api/v1/settings/providers/vlm` | JWT | Set or update VLM provider config |
| `PUT` | `/api/v1/settings/providers/embedding` | JWT | Set or update embedding provider config |
| `DELETE` | `/api/v1/settings/providers/vlm` | JWT | Remove VLM config (revert to system default) |
| `DELETE` | `/api/v1/settings/providers/embedding` | JWT | Remove embedding config (revert to system default) |
| `POST` | `/api/v1/settings/providers/test` | JWT | Test provider connection, return available models |

### Endpoint Details

#### `GET /api/v1/settings/providers`

Returns the user's configured providers. API keys are masked (first 8 chars + `...`).

**Response:** `ProvidersResponse`

```json
{
  "vlm": {
    "provider_type": "vlm",
    "provider_name": "openai",
    "model_name": "gpt-4o",
    "base_url": null,
    "is_validated": true,
    "api_key_prefix": "sk-proj-...",
    "created_at": "2026-04-10T12:00:00Z",
    "updated_at": "2026-04-10T12:00:00Z"
  },
  "embedding": null
}
```

#### `PUT /api/v1/settings/providers/{type}`

Sets or updates a provider config. The config is saved only after a successful connectivity test (`is_validated=True`).

**Request body:** `SetProviderRequest`

```json
{
  "provider_name": "openai",
  "api_key": "sk-proj-abc123...",
  "model_name": "gpt-4o",
  "base_url": null
}
```

**Flow:**
1. Validate request schema
2. Test the provider connection using the submitted key (same logic as `/test`)
3. If test fails: return `400` with error message. Config is NOT saved.
4. If test passes: encrypt key, upsert config with `is_validated=True`
5. Return `ProviderConfigResponse`

**Response:** `ProviderConfigResponse` (201 on create, 200 on update)

#### `DELETE /api/v1/settings/providers/{type}`

Removes the user's config for the given type. User reverts to the system default provider.

**Response:** `204 No Content`

If no config exists for the type, return `204` (idempotent).

#### `POST /api/v1/settings/providers/test`

Tests a provider connection without saving. Returns available models on success.

**Request body:** `TestProviderRequest`

```json
{
  "provider_name": "openai",
  "api_key": "sk-proj-abc123...",
  "base_url": null
}
```

**Response:** `TestProviderResponse`

```json
{
  "success": true,
  "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  "error": null
}
```

On failure:

```json
{
  "success": false,
  "models": [],
  "error": "Authentication failed: invalid API key"
}
```

---

## Pydantic Schemas

File: `modules/settings/schemas.py`

```python
from enum import Enum
from datetime import datetime


class ProviderType(str, Enum):
    VLM = "vlm"
    EMBEDDING = "embedding"


class ProviderName(str, Enum):
    DASHSCOPE = "dashscope"
    OPENAI = "openai"
    GOOGLE = "google"
    OLLAMA = "ollama"


class SetProviderRequest(BaseModel):
    provider_name: ProviderName
    api_key: str = Field(..., min_length=1, max_length=500)
    model_name: str = Field(..., min_length=1, max_length=100)
    base_url: str | None = Field(default=None, max_length=500)


class TestProviderRequest(BaseModel):
    provider_name: ProviderName
    api_key: str = Field(..., min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)


class TestProviderResponse(BaseModel):
    success: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None


class ProviderConfigResponse(BaseModel):
    provider_type: ProviderType
    provider_name: ProviderName
    model_name: str
    base_url: str | None
    is_validated: bool
    api_key_prefix: str          # First 8 chars + "..."
    created_at: datetime
    updated_at: datetime


class ProvidersResponse(BaseModel):
    vlm: ProviderConfigResponse | None = None
    embedding: ProviderConfigResponse | None = None
```

---

## Module Structure

```
modules/settings/
├── __init__.py
├── apiv1/
│   ├── __init__.py
│   └── handler.py          # FastAPI router: GET, PUT, DELETE, POST /test
├── schemas.py              # Pydantic models (above)
├── usecase.py              # Orchestration: encrypt/decrypt, call service + repo
├── services.py             # Provider testing, model listing, key masking
└── repositories.py         # SQLAlchemy CRUD for user_provider_configs
```

### Layer Responsibilities

**handler.py** — Receives HTTP request, extracts `user_id` from JWT via `get_current_user` dependency, calls usecase, returns serialized response. No business logic.

**usecase.py** — Wires together service and repository:
- `get_providers(user_id)` -> reads from repo, masks keys via service, returns response
- `set_provider(user_id, provider_type, request)` -> calls service to test, encrypts key, upserts via repo
- `delete_provider(user_id, provider_type)` -> deletes via repo
- `test_provider(request)` -> delegates to service

**services.py** — Business logic, no DB access:
- `test_provider_connection(provider_name, api_key, base_url)` -> hits provider API, returns success + models
- `filter_models(provider_name, models, provider_type)` -> filters model list to relevant type (vision vs embedding)
- `mask_api_key(api_key)` -> returns first 8 chars + `"..."`

**repositories.py** — SQLAlchemy only:
- `get_by_user_id(user_id)` -> list of configs for user
- `get_by_user_and_type(user_id, provider_type)` -> single config or None
- `upsert(config)` -> insert or update
- `delete_by_user_and_type(user_id, provider_type)` -> delete

---

## Provider Testing Logic

For each provider, the service hits a lightweight endpoint to validate the API key and retrieve available models.

### DashScope

```
POST https://dashscope-intl.aliyuncs.com/api/v1/models
Headers: Authorization: Bearer <api_key>
```

Parse response for model list. Filter to multimodal/vision models for VLM type, embedding models for embedding type.

If the models endpoint is unavailable, fall back to a minimal generation request:

```
POST /api/v1/services/aigc/multimodal-generation/generation
Body: minimal payload with a trivial prompt
```

Success = 200 status. On auth failure, DashScope returns 401.

### OpenAI

```
GET https://api.openai.com/v1/models
Headers: Authorization: Bearer <api_key>
```

Parse `data[].id` for model list. Filter:
- VLM type: models containing `gpt-4o`, `gpt-4-turbo`, or `gpt-4-vision` in their ID
- Embedding type: models containing `embedding` in their ID

### Google (Gemini)

```
GET https://generativelanguage.googleapis.com/v1/models?key=<api_key>
```

Parse `models[].name` for model list. Filter:
- VLM type: models supporting `generateContent` method
- Embedding type: models supporting `embedContent` method

### Ollama

```
GET <base_url>/api/tags
```

No authentication needed. Tests connectivity only. Parse `models[].name` for model list.

Filter:
- VLM type: models with vision capability (check model details or known vision model names)
- Embedding type: models with embedding capability

**Timeout:** All test requests use a 15-second timeout. Connection errors are caught and returned as `TestProviderResponse(success=False, error="...")`.

---

## Provider Factory Changes

File: `library/providers/factory.py`

### Modified Signatures

```python
def get_vlm_provider(user_id: str | None = None) -> VLMProvider:
    """Create and return a VLM provider.

    If user_id is provided and the user has a validated VLM config,
    use the user's provider with their decrypted API key.
    Otherwise, fall back to the system default from get_settings().
    """
    ...


def get_embedding_provider(user_id: str | None = None) -> EmbeddingProvider:
    """Create and return an embedding provider.

    If user_id is provided and the user has a validated embedding config,
    use the user's provider with their decrypted API key.
    Otherwise, fall back to the system default from get_settings().
    """
    ...
```

### Resolution Flow

```
get_vlm_provider(user_id="abc123")
  │
  ├─ user_id is not None
  │   ├─ Query user_provider_configs WHERE user_id="abc123" AND provider_type="vlm"
  │   ├─ Found AND is_validated=True?
  │   │   ├─ YES → decrypt(encrypted_api_key) → instantiate provider with user's key + model
  │   │   └─ NO  → fall through to system default
  │   └─ Not found → fall through to system default
  │
  └─ user_id is None
      └─ Use system default from get_settings() (existing behavior)
```

### Factory Accepts Overrides

Provider constructors must accept optional overrides for `api_key`, `model_name`, and `base_url`:

```python
# Existing (system default)
provider = OpenAIProvider()  # reads from get_settings()

# User override
provider = OpenAIProvider(
    api_key="sk-user-key-...",
    model_name="gpt-4o",
    base_url=None,
)
```

Each provider class adds optional kwargs to `__init__`. If provided, they override the settings-based defaults.

### Database Access in Factory

The factory needs to read user configs from the database. To avoid importing the repository directly into the library layer (which would violate the architecture), the factory accepts an optional `UserProviderConfig` dataclass:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class UserProviderOverride:
    provider_name: str
    api_key: str          # Already decrypted
    model_name: str
    base_url: str | None


def get_vlm_provider(override: UserProviderOverride | None = None) -> VLMProvider:
    ...
```

The **usecase layer** (not the factory) handles:
1. Querying the repository for user config
2. Decrypting the API key
3. Constructing the `UserProviderOverride`
4. Passing it to the factory

This preserves the architecture: `usecase -> repository` for DB, `usecase -> library/factory` for provider creation.

---

## Security Rules

1. **Encrypted at rest.** API keys are encrypted with Fernet (AES-128-CBC + HMAC-SHA256) before storage. The `encrypted_api_key` column never contains plaintext.

2. **ENCRYPTION_KEY in env.** The Fernet key is loaded from the `ENCRYPTION_KEY` environment variable. It is never hardcoded in source code. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

3. **Decrypt on demand.** Decryption only happens at the moment of provider instantiation. The decrypted key is passed to the provider constructor and not stored in any cache, session, or long-lived object.

4. **Masked in API responses.** The API never returns the full API key. `api_key_prefix` shows only the first 8 characters followed by `"..."`. If the key is shorter than 8 characters, show the full key followed by `"..."`.

5. **Validate before save.** A provider config can only be persisted with `is_validated=True`. The PUT endpoint always tests the connection first. If the test fails, the config is rejected with a 400 error.

6. **DELETE reverts to default.** Removing a config means the user falls back to the system-level provider configured via environment variables. There is no "disabled" state.

7. **User isolation.** Repository queries always filter by `user_id`. A user can never read, modify, or delete another user's provider config.

8. **Rate limiting.** The `/test` endpoint is rate-limited to prevent API key enumeration. Apply the same rate limit as other authenticated endpoints.

9. **No key logging.** API keys (plaintext or ciphertext) are never written to application logs. Log the provider name and whether the test succeeded, not the key value.

10. **Key rotation.** If `ENCRYPTION_KEY` is rotated, all existing `encrypted_api_key` values become unreadable. A migration script must re-encrypt all keys: decrypt with old key, encrypt with new key. Document this in the migration notes.

---

## Migration SQL

```sql
-- Create user_provider_configs table
CREATE TABLE IF NOT EXISTS user_provider_configs (
    id              VARCHAR(36)     PRIMARY KEY,
    user_id         VARCHAR(36)     NOT NULL,
    provider_type   VARCHAR(20)     NOT NULL,   -- 'vlm' or 'embedding'
    provider_name   VARCHAR(50)     NOT NULL,   -- 'dashscope', 'openai', 'google', 'ollama'
    encrypted_api_key TEXT          NOT NULL,
    model_name      VARCHAR(100)    NOT NULL,
    base_url        VARCHAR(500)    NULL,
    is_validated    BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_user_provider_type UNIQUE (user_id, provider_type)
);

-- Index for fast lookups by user_id
CREATE INDEX IF NOT EXISTS idx_user_provider_configs_user_id
    ON user_provider_configs (user_id);

-- Trigger to auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_provider_configs_updated_at
    BEFORE UPDATE ON user_provider_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## Error Handling

| Scenario | HTTP Status | Error Message |
|----------|-------------|---------------|
| Test fails (invalid key) | 400 | `"Provider test failed: <provider error>"` |
| Test fails (timeout) | 400 | `"Provider test failed: connection timed out"` |
| Test fails (unreachable) | 400 | `"Provider test failed: could not connect to <provider>"` |
| Unknown provider_name | 422 | Pydantic validation error |
| Missing api_key | 422 | Pydantic validation error |
| Config not found on DELETE | 204 | No body (idempotent) |
| ENCRYPTION_KEY not set | 500 | `"Internal server error"` (logged server-side as RuntimeError) |
| Decryption failure (key rotated) | 500 | `"Internal server error"` (logged: `"Failed to decrypt API key for user {user_id}"`) |

---

## Integration Points

### Pipeline (Processing + Chat)

The document processing pipeline and chat pipeline currently call `get_vlm_provider()` without a user context. After this feature:

1. Pipeline entry points receive `user_id` from the authenticated request
2. Pipeline passes `user_id` through the LangGraph state
3. At provider instantiation nodes, the usecase constructs a `UserProviderOverride` (if config exists) and passes it to the factory

### RAG Pipeline

The RAG pipeline calls `get_embedding_provider()`. Same pattern applies:

1. RAG entry points receive `user_id`
2. Usecase checks for user embedding config
3. If found, passes `UserProviderOverride` to the embedding factory
4. If not found, uses system default

### Provider Override Wiring

The override is resolved **once** in the usecase layer, then passed through the pipeline state dict as a plain field. No DB access happens in the library layer.

#### Shared Resolver

```python
# shared/provider_resolver.py

from docmind.core.encryption import decrypt
from docmind.library.providers.factory import UserProviderOverride
from docmind.modules.settings.repositories import UserProviderRepository


async def resolve_provider_override(
    user_id: str, provider_type: str
) -> UserProviderOverride | None:
    """Resolve user's provider config from DB into a UserProviderOverride.

    Returns None if user has no validated config for the given type.
    Called by usecases before entering pipeline/service code.
    """
    repo = UserProviderRepository()
    config = await repo.get_by_user_and_type(user_id, provider_type)
    if config is None or not config.is_validated:
        return None
    return UserProviderOverride(
        provider_name=config.provider_name,
        api_key=decrypt(config.encrypted_api_key),
        model_name=config.model_name,
        base_url=config.base_url,
    )
```

#### Usecase Injection

Each usecase resolves the override and injects it into the pipeline state or service call:

```python
# modules/documents/usecase.py — processing pipeline
class DocumentUseCase:
    async def _processing_stream(self, document_id, template_type, user_id):
        from docmind.shared.provider_resolver import resolve_provider_override
        
        vlm_override = await resolve_provider_override(user_id, "vlm")
        initial_state = {
            ...,
            "provider_override": vlm_override,  # UserProviderOverride | None
        }
        # Pipeline nodes read state.get("provider_override")

# modules/chat/usecase.py — chat pipeline
class ChatUseCase:
    async def _chat_stream(self, document_id, message, user_id):
        vlm_override = await resolve_provider_override(user_id, "vlm")
        # Pass to chat service or pipeline state

# modules/projects/usecase.py — project chat
class ProjectUseCase:
    async def _project_chat_stream(self, project_id, message, user_id):
        vlm_override = await resolve_provider_override(user_id, "vlm")
        embedding_override = await resolve_provider_override(user_id, "embedding")
        # Pass both to RAG + VLM pipelines
```

#### Pipeline Nodes — Read Override from State

Each pipeline node reads the override from the state dict and passes it to the factory:

```python
# library/pipeline/extraction/extract.py
def extract_node(state: dict) -> dict:
    override = state.get("provider_override")
    provider = get_vlm_provider(override=override)
    # ... rest of extraction logic

# library/pipeline/extraction/postprocess.py
def postprocess_node(state: dict) -> dict:
    override = state.get("provider_override")
    provider = get_vlm_provider(override=override)
    # ... rest of postprocess logic
```

#### Services — Accept Override Parameter

Services that call `get_vlm_provider()` accept an optional override parameter:

```python
# modules/extractions/services/classification.py
class ClassificationService:
    async def classify(self, image, categories, override=None):
        provider = get_vlm_provider(override=override)

# modules/chat/services.py
class ChatService:
    async def chat(self, document_id, message, override=None):
        provider = get_vlm_provider(override=override)

# modules/templates/services/detection.py
class DetectionService:
    async def detect(self, image, override=None):
        provider = get_vlm_provider(override=override)
```

#### Call Sites Summary

| File | How Override is Received |
|------|------------------------|
| `library/pipeline/extraction/extract.py` | `state.get("provider_override")` |
| `library/pipeline/extraction/postprocess.py` | `state.get("provider_override")` |
| `library/rag/query_rewriter.py` | `override` parameter |
| `modules/extractions/services/classification.py` | `override` parameter |
| `modules/chat/services.py` | `override` parameter |
| `modules/projects/services/vlm.py` | `override` parameter |
| `modules/templates/services/detection.py` | `override` parameter |

### Existing Callers

All existing callers of `get_vlm_provider()` and `get_embedding_provider()` continue to work without changes because the `override` parameter defaults to `None`, preserving the current system-default behavior.
