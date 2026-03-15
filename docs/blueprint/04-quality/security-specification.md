# Security Specification: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Quality Assurance

---

## 1. Secrets Management

- All API keys and credentials stored in environment variables, NEVER in source code
- `.env` file listed in `.gitignore`
- `.env.example` committed with placeholder values and comments
- Application fails fast at startup if required secrets are missing (Pydantic validation)
- Only the active VLM provider's API key is required — others can be omitted
- Supabase service role key used ONLY on backend — never exposed to frontend

## 2. Authentication & Authorization

- **Authentication:** Supabase Auth handles OAuth flow (Google/GitHub); issues JWT tokens
- **Token validation:** FastAPI middleware validates Supabase JWT on every protected endpoint
- **User isolation:** Supabase Row Level Security (RLS) policies enforce `auth.uid() = user_id` on all tables
- **Double enforcement:** Backend validates user ownership in service layer (defense in depth — don't rely solely on RLS)
- **Token refresh:** Supabase JS SDK handles automatic token refresh on frontend
- **Session expiry:** JWTs expire per Supabase default (1 hour); refresh tokens handle renewal

## 3. Data Privacy & Encryption

- **In transit:** HTTPS enforced for all non-localhost deployments
- **At rest:** Supabase encrypts Postgres data at rest (managed by Supabase)
- **Document storage:** Files stored in Supabase Storage with user-scoped paths (`{user_id}/{doc_id}/`)
- **No PII collection:** System only stores what Supabase Auth provides (email, OAuth profile name)
- **Document content:** Uploaded documents may contain sensitive content — stored encrypted (Supabase), deleted when user requests deletion (cascading delete)
- **VLM API calls:** Document images sent to external VLM APIs (DashScope, OpenAI, Google) — users should be aware their documents are processed by third-party APIs. Ollama provider keeps all data local.

## 4. Input Validation & Upload Security

- **File type:** Server-side MIME type validation (not just extension check)
- **File size:** 20MB limit enforced on both frontend and backend
- **Filename:** Sanitized — strip path traversal characters, limit length, use UUID-based storage paths
- **Content validation:** Reject files that don't match expected magic bytes for declared type
- **Rate limiting:** Upload endpoint rate-limited (e.g., 10 uploads per minute per user)

## 5. API Security

- **CORS:** Configured to allow only the frontend origin (no wildcard in production)
- **Rate limiting:** Applied to all VLM-calling endpoints to prevent cost overrun
- **Error messages:** Return generic errors to client; log detailed errors server-side only
- **Request size:** Limit request body size on all endpoints
- **SQL injection:** Prevented via SQLAlchemy parameterized queries (never raw SQL with user input)
- **XSS:** React escapes output by default; no dangerouslySetInnerHTML without sanitization

## 6. Security Best Practices Checklist

- [ ] `.env` in `.gitignore`
- [ ] `.env.example` committed with placeholders
- [ ] No hardcoded secrets in source code (grep for API keys in CI)
- [ ] All API endpoints require valid JWT (except landing page, health check)
- [ ] RLS policies active on all tables
- [ ] CORS restricted to frontend origin
- [ ] File upload validation (type, size, content)
- [ ] Rate limiting on VLM-calling endpoints
- [ ] Cascading delete removes storage files + all DB records
- [ ] Error responses don't leak internal details
- [ ] Dependency audit: `pip audit` / `npm audit` in CI

---
#security #data-privacy #compliance #docmind-vlm
