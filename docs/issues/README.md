# GitHub Issues — DocMind-VLM

Master index of all implementation issues. Each issue has a detailed doc in this directory and a corresponding GitHub issue.

## How to Use

1. **Pick an issue** from the table below (respect phase order for dependencies)
2. **Read the detailed doc** linked in the "Doc" column
3. **Create branch** from `dev`: `git checkout -b feat/<issue-id>-<slug>`
4. **Follow TDD** (backend): write tests first → run (RED) → implement → run (GREEN) → refactor
5. **Create PR** targeting `dev` when done

## Phase Dependencies

```
Phase 1 (Infrastructure) ← no dependencies
Phase 2 (CV + VLM)       ← Phase 1
Phase 3 (Pipeline)        ← Phase 1 + Phase 2
Phase 4 (Extraction)      ← Phase 3
Phase 5 (Chat)            ← Phase 3
Phase 6 (Frontend)        ← Phase 1 (auth), Phase 3+ (features)
Phase 7 (Testing)         ← All phases
```

## Issue Map

### Phase 1: Infrastructure

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #1 | Supabase JWT auth integration | P0 | [001-auth-jwt.md](001-auth-jwt.md) | None |
| #2 | Alembic initial migration | P0 | [002-alembic-migration.md](002-alembic-migration.md) | None |
| #3 | Document repository CRUD | P0 | [003-document-repository.md](003-document-repository.md) | #2 |
| #4 | Document upload + Supabase Storage | P0 | [004-document-upload.md](004-document-upload.md) | #1, #3 |
| #5 | Health status: real component checks | P1 | [005-health-status.md](005-health-status.md) | #2 |

### Phase 2: CV + VLM Providers

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #6 | CV: PDF to page images | P0 | [006-cv-preprocessing.md](006-cv-preprocessing.md) | None |
| #7 | CV: deskew (Hough transform) | P0 | [007-cv-deskew.md](007-cv-deskew.md) | None |
| #8 | CV: quality assessment | P0 | [008-cv-quality.md](008-cv-quality.md) | None |
| #9 | DashScope VLM provider | P0 | [009-dashscope-provider.md](009-dashscope-provider.md) | None |
| #10 | VLM provider factory + health | P1 | [010-vlm-factory.md](010-vlm-factory.md) | #9 |

### Phase 3: Processing Pipeline

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #11 | Pipeline: preprocess node | P0 | [011-pipeline-preprocess.md](011-pipeline-preprocess.md) | #6, #7, #8 |
| #12 | Pipeline: extract node (general) | P0 | [012-pipeline-extract-general.md](012-pipeline-extract-general.md) | #9, #11 |
| #13 | Pipeline: extract node (template) | P0 | [013-pipeline-extract-template.md](013-pipeline-extract-template.md) | #12, #20 |
| #14 | Pipeline: postprocess + store nodes | P0 | [014-pipeline-postprocess-store.md](014-pipeline-postprocess-store.md) | #12, #3 |
| #15 | Document process SSE endpoint | P0 | [015-process-sse-endpoint.md](015-process-sse-endpoint.md) | #11, #12, #14 |

### Phase 4: Extraction Features

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #16 | Extraction repository + usecase | P0 | [016-extraction-repository.md](016-extraction-repository.md) | #2, #14 |
| #17 | Audit trail recording + retrieval | P1 | [017-audit-trail.md](017-audit-trail.md) | #14, #16 |
| #18 | Confidence overlay generation | P1 | [018-confidence-overlay.md](018-confidence-overlay.md) | #16 |
| #19 | Pipeline comparison: raw vs enhanced | P1 | [019-pipeline-comparison.md](019-pipeline-comparison.md) | #16 |
| #20 | Template management | P1 | [020-template-management.md](020-template-management.md) | None |

### Phase 5: Chat

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #21 | Chat pipeline: router + retrieve | P0 | [021-chat-pipeline-router.md](021-chat-pipeline-router.md) | #9, #16 |
| #22 | Chat pipeline: reason + cite | P0 | [022-chat-pipeline-reason.md](022-chat-pipeline-reason.md) | #21 |
| #23 | Chat repository + persistence | P0 | [023-chat-repository.md](023-chat-repository.md) | #2 |
| #24 | Chat SSE endpoint | P0 | [024-chat-sse-endpoint.md](024-chat-sse-endpoint.md) | #22, #23 |

### Phase 6: Frontend

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #25 | Landing page | P1 | [025-landing-page.md](025-landing-page.md) | None |
| #26 | Auth UI + route protection | P0 | [026-auth-ui.md](026-auth-ui.md) | #1 |
| #27 | Dashboard: document list + upload | P0 | [027-dashboard.md](027-dashboard.md) | #4, #26 |
| #28 | Workspace: DocumentViewer | P0 | [028-workspace-viewer.md](028-workspace-viewer.md) | #26 |
| #29 | ExtractionPanel + AuditPanel | P1 | [029-extraction-panel.md](029-extraction-panel.md) | #16, #28 |
| #30 | ChatPanel + citations | P1 | [030-chat-panel.md](030-chat-panel.md) | #24, #28 |
| #31 | ComparePanel + ProcessingProgress | P1 | [031-compare-progress.md](031-compare-progress.md) | #15, #19, #28 |

### Phase 7: Testing + Polish

| Issue | Title | Priority | Doc | Dependencies |
|-------|-------|----------|-----|--------------|
| #32 | Unit tests: 80%+ coverage | P0 | [032-unit-tests.md](032-unit-tests.md) | Phase 1-5 |
| #33 | Integration tests: API + pipeline | P1 | [033-integration-tests.md](033-integration-tests.md) | Phase 1-5 |
| #34 | Demo data + example documents | P1 | [034-demo-data.md](034-demo-data.md) | Phase 3-4 |

## Labels

| Label | Color | Purpose |
|-------|-------|---------|
| `phase-1-infra` | `#0E8A16` | Infrastructure |
| `phase-2-cv-vlm` | `#1D76DB` | CV + VLM providers |
| `phase-3-pipeline` | `#5319E7` | Processing pipeline |
| `phase-4-extraction` | `#FBCA04` | Extraction features |
| `phase-5-chat` | `#D93F0B` | Chat features |
| `phase-6-frontend` | `#F9D0C4` | Frontend UI |
| `phase-7-testing` | `#BFD4F2` | Testing + polish |
| `priority-p0` | `#B60205` | Must have |
| `priority-p1` | `#E4E669` | Should have |
| `backend` | `#006B75` | Backend work |
| `frontend` | `#C2E0C6` | Frontend work |
| `tdd` | `#0075CA` | TDD required |
