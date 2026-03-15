# Maintenance & Operations Plan: DocMind-VLM

**Project:** DocMind-VLM
**Owner:** Erfan
**Date:** 2026-03-11
**Status:** Operations

---

## 1. Monitoring & Alerts

### Local Development
- **Structured logs:** JSON logging to stdout — visible in `docker compose logs`
- **Health endpoint:** `GET /api/health` returns service status + VLM provider connectivity
- **Processing metrics:** Pipeline step timing logged per document (visible in audit trail)

### Production (If Deployed)
- **Uptime monitoring:** External health check on `/api/health` (e.g., UptimeRobot free tier)
- **Error tracking:** Sentry free tier for backend exceptions
- **VLM API monitoring:** Track DashScope API response times and error rates via structured logs
- **Cost monitoring:** DashScope dashboard for API usage tracking

## 2. Secrets Rotation

| Secret | Rotation Schedule | How |
|---|---|---|
| DashScope API key | On suspicion of compromise | Regenerate in Alibaba Cloud console → update `.env` |
| OpenAI API key | On suspicion of compromise | Regenerate in OpenAI dashboard → update `.env` |
| Google API key | On suspicion of compromise | Regenerate in Google Cloud console → update `.env` |
| Supabase anon key | Rarely (project-level) | Regenerate in Supabase dashboard → update `.env` + frontend config |
| Supabase service role key | On suspicion of compromise | Regenerate in Supabase dashboard → update `.env` (backend only) |

## 3. Regular Maintenance

### Monthly
- [ ] Review DashScope API usage and costs
- [ ] Check for Python dependency security updates (`pip audit`)
- [ ] Check for Node dependency security updates (`npm audit`)

### Quarterly
- [ ] Review VLM provider API changelogs for breaking changes
- [ ] Update Supabase client libraries if new versions available
- [ ] Review LangGraph releases for new features or breaking changes
- [ ] Test `docker compose up` on a fresh clone to verify nothing has drifted

### As Needed
- [ ] Update Qwen model version when new versions released on DashScope
- [ ] Add new extraction templates based on user feedback or portfolio needs
- [ ] Add new VLM provider implementations as new models become available

## 4. Backup & Recovery

- **Database:** Supabase provides automatic daily backups (free tier: 7-day retention)
- **Storage:** Supabase Storage is durable; user documents backed up within Supabase infrastructure
- **Code:** GitHub repository is the source of truth; all configuration via environment variables
- **Demo data:** Committed to repo (`demo/` directory) — always reproducible

## 5. Scaling Considerations (Future)

Current architecture supports portfolio-scale usage (5–10 concurrent users). If the project gains real adoption:

- **Processing queue:** Add Redis-backed job queue (Celery/ARQ) for async document processing
- **Rate limiting:** Per-user rate limits on processing and chat endpoints
- **CDN:** Serve frontend via Vercel/Cloudflare for global performance
- **Database:** Supabase Pro tier for connection pooling and larger storage
- **Multi-region:** DashScope API is Asia-optimized; add OpenAI/Google providers for other regions

---
#operations #maintenance #lifecycle #docmind-vlm
