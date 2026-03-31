# Deployment Conventions

---

## Docker Images

| Image | Registry | Build Context |
|-------|----------|---------------|
| `ghcr.io/nunenuh/docmind-vlm-backend:latest` | GHCR | `./backend` |
| `ghcr.io/nunenuh/docmind-vlm-frontend:latest` | GHCR | `./frontend` |

### Backend Dockerfile

- Multi-stage: builder (poetry install) → runtime (slim + venv)
- `PYTHONPATH=/app/src` — resolves `docmind` package
- `CMD: uvicorn docmind.main:app --host 0.0.0.0 --port 8009`
- Data directory mounted at runtime (templates, personas, alembic)

### Frontend Dockerfile

- Multi-stage: node build → nginx serve
- Build args: `VITE_API_URL` (baked into JS bundle at build time)
- No `VITE_SUPABASE_*` env vars — frontend never talks to Supabase
- Served on port 5177

---

## Production Stack (docker-compose)

```
┌─────────────────────────────────────────────┐
│  Cloudflare Zero Trust Tunnels              │
│  docmind.nunenuh.me → :5177 (frontend)     │
│  api.docmind.nunenuh.me → :8009 (backend)  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│  Docker Network (internal)                   │
│                                              │
│  frontend:5177        ← nginx + static SPA   │
│  backend:8009         ← FastAPI + uvicorn     │
│  redis:6379           ← cache                 │
│  supabase-db:5432     ← PostgreSQL 15         │
│  supabase-auth:9999   ← GoTrue               │
│  supabase-rest:3000   ← PostgREST            │
│  supabase-storage:5000 ← Storage API         │
│  supabase-kong:8000   ← API Gateway          │
└─────────────────────────────────────────────┘
```

---

## Deploy Workflow (Manual)

```bash
# 1. Build locally
docker build --build-arg VITE_API_URL=https://api.docmind.nunenuh.me \
  -t ghcr.io/nunenuh/docmind-vlm-frontend:latest ./frontend
docker build -t ghcr.io/nunenuh/docmind-vlm-backend:latest ./backend

# 2. Transfer via SSH (faster than GHCR push from dev machine)
docker save ghcr.io/nunenuh/docmind-vlm-backend:latest \
  ghcr.io/nunenuh/docmind-vlm-frontend:latest | \
  ssh erfan@192.168.100.137 "docker load"

# 3. Restart
ssh erfan@192.168.100.137 "cd /workspace/deployments/docmind-vlm && \
  docker compose up -d frontend backend"

# 4. Run migrations (if schema changed)
ssh erfan@192.168.100.137 "docker exec docmind-backend python -m alembic upgrade head"
```

---

## Environment Variables

### Backend (.env)

| Variable | Example | Purpose |
|----------|---------|---------|
| `APP_ENVIRONMENT` | `production` | Controls debug, docs exposure |
| `ALLOWED_ORIGINS_STR` | `https://docmind.nunenuh.me` | CORS origins |
| `JWT_SECRET` | `super-secret-...` | HS256 JWT verification (local Supabase) |
| `SUPABASE_URL` | `http://supabase-kong:8000` | Internal GoTrue/Storage access |
| `SUPABASE_PUBLISHABLE_KEY` | `eyJ...` | GoTrue API key header |
| `DB_HOST` | `supabase-db` | Docker service hostname |
| `REDIS_URL` | `redis://redis:6379/0` | Docker service hostname |
| `DASHSCOPE_API_KEY` | `sk-...` | VLM provider |

### Frontend (build args only)

| Variable | Example | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `https://api.docmind.nunenuh.me` | Backend API base URL |

No `VITE_SUPABASE_*` variables — frontend uses backend auth proxy.

---

## Key Rules

1. **Frontend never talks to Supabase** — all auth/storage goes through backend
2. **File serving via backend** — `/api/v1/documents/{id}/file` serves bytes directly (no Supabase signed URLs)
3. **Seed data mounted read-only** — `templates/` and `personas/` JSON files mounted into container
4. **Alembic migrations manual** — run after schema changes, not on startup
5. **GHCR images are latest tag** — no version tags yet (portfolio stage)
