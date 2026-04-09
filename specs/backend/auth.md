# Backend Spec: Auth Module

Files: `backend/src/docmind/modules/auth/`

---

## Overview

The auth module proxies all authentication operations through Supabase GoTrue. **The frontend never talks to Supabase directly** — all auth flows go through the backend.

```
Frontend → POST /api/v1/auth/login → Backend → GoTrue REST → JWT returned
Frontend → stores JWT in memory (auth store)
Frontend → sends JWT in Authorization: Bearer header for all API calls
Backend → validates JWT (HS256 or ES256) → extracts user_id
```

---

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/auth/signup` | No | Create account → return session |
| `POST` | `/api/v1/auth/login` | No | Login → return session |
| `POST` | `/api/v1/auth/logout` | JWT | Revoke session |
| `GET` | `/api/v1/auth/session` | JWT | Validate token, return user info |
| `POST` | `/api/v1/auth/refresh` | No | Refresh expired token |

---

## Schemas

```python
class SignupRequest(BaseModel):
    email: EmailStr
    password: str  # min_length=6

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class AuthUserResponse(BaseModel):
    id: str
    email: str
    created_at: str | None = None

class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: AuthUserResponse

class SessionResponse(BaseModel):
    user: AuthUserResponse
```

---

## Service Layer

`AuthService` calls GoTrue REST endpoints via `httpx.AsyncClient`:

| Method | GoTrue Endpoint | Headers |
|--------|----------------|---------|
| `signup(email, pw)` | `POST {SUPABASE_URL}/auth/v1/signup` | `apikey: {PUBLISHABLE_KEY}` |
| `login(email, pw)` | `POST {SUPABASE_URL}/auth/v1/token?grant_type=password` | `apikey` |
| `logout(token)` | `POST {SUPABASE_URL}/auth/v1/logout` | `apikey` + `Bearer` |
| `refresh(token)` | `POST {SUPABASE_URL}/auth/v1/token?grant_type=refresh_token` | `apikey` |
| `get_user(token)` | `GET {SUPABASE_URL}/auth/v1/user` | `apikey` + `Bearer` |

---

## JWT Verification

`core/auth.py` supports two strategies:

1. **HS256 (local Supabase)** — if `JWT_SECRET` is set in config, verify with HMAC
2. **ES256 (cloud Supabase)** — fall back to JWKS endpoint verification

```python
def decode_jwt(token: str) -> dict:
    settings = get_settings()
    if settings.JWT_SECRET:
        # HS256 with shared secret
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    else:
        # ES256 via JWKS
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["ES256"], audience="authenticated")
    return {"id": payload["sub"], "email": payload.get("email")}
```

---

## Token Strategy (Frontend)

- `access_token` — memory only (Zustand auth store), never localStorage
- `refresh_token` — persisted in localStorage for session recovery
- On app mount: restore from localStorage refresh token → call `/auth/refresh`
- On 401: auto-refresh once, retry, if fails → redirect to `/login`

---

## OAuth (Deferred)

Google/GitHub OAuth requires redirect URL handling through the backend. Currently email/password only. OAuth buttons hidden in LoginPage.
