# Backend Spec: Auth Proxy + API Keys

Files: `backend/src/docmind/modules/auth/`, `backend/src/docmind/core/auth.py`, `backend/src/docmind/core/scopes.py`

See also: [[projects/docmind-vlm/specs/conventions/security]] · [[projects/docmind-vlm/specs/backend/api]]

---

## Responsibility

| Component | Does |
|-----------|------|
| `core/auth.py` | Dual-mode auth: JWT (browser) or API token (programmatic). Extracts token, routes to correct validator |
| `core/scopes.py` | Scope enforcement dependency. JWT users bypass (full access), API token users checked against scope list |
| `modules/auth/` | Auth endpoints (signup, login, logout, session, refresh) + API token CRUD |
| `modules/auth/services/api_token_service.py` | Token generation (SHA-256 hash), validation, revocation |
| `modules/auth/repositories/api_token_repository.py` | Token CRUD via SQLAlchemy |

---

## Two Auth Methods

### 1. JWT (Browser Sessions)

```
Frontend → POST /api/v1/auth/login → Backend proxies to Supabase GoTrue
         ← { access_token, refresh_token }
         → Authorization: Bearer <jwt> on all requests
         → core/auth.py decodes JWT (HS256 local or ES256 cloud)
         → Returns { id, email, scopes: None, auth_method: "jwt" }
```

JWT users have **unrestricted access** — `scopes: None` bypasses all scope checks.

### 2. API Token (Programmatic Access)

```
User → POST /api/v1/auth/tokens → creates token
     ← { plain_token: "dm_live_abc123..." } (shown ONCE)
     → Authorization: Bearer dm_live_abc123...
       OR X-API-Key: dm_live_abc123...
     → core/auth.py detects prefix → ApiTokenService.validate_token()
     → Returns { id, email: "", scopes: [...], auth_method: "api_token", token_id }
```

API token users have **scoped access** — only the scopes assigned at creation.

---

## Token Format

```
dm_live_<24 random chars>   (production)
dm_test_<24 random chars>   (testing/development)
```

- **Prefix** (`dm_live_` or `dm_test_`): identifies token type and routes auth
- **First 12 chars**: stored as `prefix` column for fast DB lookup
- **Full token**: SHA-256 hashed → stored as `hashed_secret`
- **Plain token**: returned ONCE at creation, never stored or retrievable

---

## ORM Model

```python
class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: str               # UUID4, primary key
    user_id: str          # Owner (FK to auth.users via Supabase)
    name: str             # Human label ("Production", "CI/CD")
    prefix: str           # First 12 chars, unique, indexed
    hashed_secret: str    # SHA-256 of full token
    scopes: list[str]     # JSON array of scope strings
    token_type: str       # "live" or "test"
    expires_at: datetime  # Nullable — None means no expiry
    last_used_at: datetime # Updated on each validation
    created_at: datetime
    revoked_at: datetime  # Nullable — set on revocation (soft delete)
```

---

## Scopes

| Scope | Grants |
|-------|--------|
| `documents:read` | GET documents, GET document by ID, GET document file |
| `documents:write` | POST upload document, DELETE document, POST process document |
| `extractions:read` | GET extraction, GET audit trail, GET overlay, GET comparison, GET export |
| `extractions:write` | POST process extraction, POST classify |
| `projects:read` | GET projects, GET project, GET project documents |
| `projects:write` | POST/PUT/DELETE project, POST/DELETE project documents |
| `projects:chat` | POST project chat (SSE), GET conversations |
| `rag:read` | POST RAG search, GET chunks, GET stats |
| `templates:read` | GET templates |
| `templates:write` | (reserved for future custom templates) |
| `personas:read` | GET personas |
| `personas:write` | POST/PUT/DELETE personas |
| `admin:*` | All scopes (wildcard) |

### Scope Enforcement

```python
from docmind.core.scopes import require_scopes

# Endpoint with scope check
@router.get("")
async def list_documents(
    current_user: dict = Depends(require_scopes("documents:read")),
):
    ...

# JWT users: scopes=None → bypasses check (full access)
# API token users: scopes=["documents:read"] → checked against required
# admin:* → bypasses check (full access)
```

---

## API Endpoints

### Auth Proxy

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/signup` | No | Register new user via Supabase GoTrue |
| POST | `/api/v1/auth/login` | No | Login, returns JWT tokens |
| POST | `/api/v1/auth/logout` | JWT | Invalidate session |
| GET | `/api/v1/auth/session` | JWT | Get current session info |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |

### API Token Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/tokens` | JWT | Create new API token (returns plain token once) |
| GET | `/api/v1/auth/tokens` | JWT | List all active tokens for current user |
| PATCH | `/api/v1/auth/tokens/{id}` | JWT | Update token name and/or scopes |
| DELETE | `/api/v1/auth/tokens/{id}` | JWT | Revoke token (soft delete) |

**Note:** Token management is JWT-only. You cannot create/manage tokens using another token.

---

## Pydantic Schemas

```python
class TokenScope(str, Enum):
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"
    EXTRACTIONS_READ = "extractions:read"
    EXTRACTIONS_WRITE = "extractions:write"
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    PROJECTS_CHAT = "projects:chat"
    RAG_READ = "rag:read"
    TEMPLATES_READ = "templates:read"
    TEMPLATES_WRITE = "templates:write"
    PERSONAS_READ = "personas:read"
    PERSONAS_WRITE = "personas:write"
    ADMIN_ALL = "admin:*"

class CreateTokenRequest(BaseModel):
    name: str                           # 1-255 chars
    scopes: list[TokenScope]            # At least one scope
    token_type: Literal["live", "test"] # Default: "live"
    expires_in_days: int | None = 90    # 1-365 or null for no expiry

class UpdateTokenRequest(BaseModel):
    name: str | None = None
    scopes: list[TokenScope] | None = None

class TokenResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    token_type: str
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    revoked_at: datetime | None

class TokenCreatedResponse(TokenResponse):
    plain_token: str    # Shown ONCE — never stored

class TokenListResponse(BaseModel):
    tokens: list[TokenResponse]
    total: int
```

---

## Scope Enforcement Map

Every authenticated endpoint must use `require_scopes()` instead of plain `get_current_user()`:

### documents/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `POST /documents` | `documents:write` |
| `GET /documents` | `documents:read` |
| `GET /documents/{id}` | `documents:read` |
| `DELETE /documents/{id}` | `documents:write` |
| `POST /documents/{id}/process` | `documents:write` |
| `GET /documents/{id}/file` | `documents:read` |
| `GET /documents/search` | `documents:read` |

### extractions/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `GET /extractions/{doc_id}` | `extractions:read` |
| `GET /extractions/{doc_id}/audit` | `extractions:read` |
| `GET /extractions/{doc_id}/overlay` | `extractions:read` |
| `GET /extractions/{doc_id}/comparison` | `extractions:read` |
| `GET /extractions/{doc_id}/export` | `extractions:read` |
| `POST /extractions/{doc_id}/process` | `extractions:write` |
| `POST /extractions/classify` | `extractions:write` |

### chat/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `POST /chat/{doc_id}` | `documents:read` |
| `GET /chat/{doc_id}/history` | `documents:read` |

### projects/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `POST /projects` | `projects:write` |
| `GET /projects` | `projects:read` |
| `GET /projects/{id}` | `projects:read` |
| `PUT /projects/{id}` | `projects:write` |
| `DELETE /projects/{id}` | `projects:write` |
| `POST /projects/{id}/documents` | `projects:write` |
| `GET /projects/{id}/documents` | `projects:read` |
| `DELETE /projects/{id}/documents/{doc_id}` | `projects:write` |
| `POST /projects/{id}/chat` | `projects:chat` |
| `GET /projects/{id}/conversations` | `projects:read` |
| `GET /projects/{id}/conversations/{conv_id}` | `projects:read` |
| `DELETE /projects/{id}/conversations/{conv_id}` | `projects:write` |

### personas/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `GET /personas` | `personas:read` |
| `POST /personas` | `personas:write` |
| `PUT /personas/{id}` | `personas:write` |
| `DELETE /personas/{id}` | `personas:write` |

### templates/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `GET /templates` | `templates:read` |

### rag/handler.py

| Endpoint | Scope Required |
|----------|---------------|
| `POST /rag/search` | `rag:read` |
| `GET /rag/chunks` | `rag:read` |
| `GET /rag/chunks/{id}` | `rag:read` |
| `GET /rag/stats` | `rag:read` |

---

## Validation Flow

```python
async def validate_token(self, raw_token: str) -> dict:
    # 1. Check prefix format (dm_live_ or dm_test_)
    # 2. Extract first 12 chars → lookup by prefix (indexed, fast)
    # 3. Check not revoked (revoked_at is NULL)
    # 4. Check not expired (expires_at > now or NULL)
    # 5. SHA-256 hash full token → compare with hashed_secret
    # 6. Fire-and-forget: update last_used_at
    # 7. Return { user_id, scopes, token_id, auth_method: "api_token" }
```

---

## Security Rules

1. **Plain token shown once** — never stored, never logged, never in error messages
2. **SHA-256 hash only** — even DB breach doesn't reveal tokens
3. **Prefix for lookup** — avoids hashing every request to find the token
4. **Token management requires JWT** — API tokens cannot create other tokens
5. **Soft delete on revoke** — keeps audit trail, token stays in DB with `revoked_at` set
6. **`last_used_at` tracking** — helps users identify unused tokens for cleanup
7. **Expiry enforcement** — checked on every validation, not via DB cron
8. **Rate limiting** — validation failures should be rate-limited (future enhancement)

---

## Migration

```sql
CREATE TABLE IF NOT EXISTS api_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    prefix VARCHAR(16) NOT NULL UNIQUE,
    hashed_secret VARCHAR(64) NOT NULL,
    scopes JSON NOT NULL DEFAULT '[]',
    token_type VARCHAR(10) NOT NULL DEFAULT 'live',
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_api_tokens_user_id ON api_tokens (user_id);
CREATE INDEX idx_api_tokens_prefix ON api_tokens (prefix);
```
