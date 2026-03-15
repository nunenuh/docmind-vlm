#!/usr/bin/env bash
# Creates all GitHub issues for docmind-vlm
# Usage: ./scripts/create-gh-issues.sh
# Requires: gh CLI authenticated

set -euo pipefail

REPO="nunenuh/docmind-vlm"

echo "=== Creating labels ==="
gh label create "phase-1-infra"     --color "0E8A16" --description "Phase 1: Infrastructure"        --repo "$REPO" 2>/dev/null || true
gh label create "phase-2-cv-vlm"    --color "1D76DB" --description "Phase 2: CV + VLM providers"    --repo "$REPO" 2>/dev/null || true
gh label create "phase-3-pipeline"  --color "5319E7" --description "Phase 3: Processing pipeline"   --repo "$REPO" 2>/dev/null || true
gh label create "phase-4-extraction" --color "FBCA04" --description "Phase 4: Extraction features"  --repo "$REPO" 2>/dev/null || true
gh label create "phase-5-chat"      --color "D93F0B" --description "Phase 5: Chat features"         --repo "$REPO" 2>/dev/null || true
gh label create "phase-6-frontend"  --color "F9D0C4" --description "Phase 6: Frontend UI"           --repo "$REPO" 2>/dev/null || true
gh label create "phase-7-testing"   --color "BFD4F2" --description "Phase 7: Testing + polish"      --repo "$REPO" 2>/dev/null || true
gh label create "priority-p0"       --color "B60205" --description "Must have"                      --repo "$REPO" 2>/dev/null || true
gh label create "priority-p1"       --color "E4E669" --description "Should have"                    --repo "$REPO" 2>/dev/null || true
gh label create "backend"           --color "006B75" --description "Backend work"                   --repo "$REPO" 2>/dev/null || true
gh label create "frontend"          --color "C2E0C6" --description "Frontend work"                  --repo "$REPO" 2>/dev/null || true
gh label create "tdd"               --color "0075CA" --description "TDD required"                   --repo "$REPO" 2>/dev/null || true
echo "Labels created."

echo ""
echo "=== Creating issues ==="

# Phase 1: Infrastructure
gh issue create --repo "$REPO" --title "Supabase JWT auth integration" --body "$(cat <<'EOF'
## Summary
Implement `decode_jwt()` in `core/auth.py` using PyJWT to verify Supabase JWT tokens. The `get_current_user()` dependency extracts user_id from the token.

## Detail
See [`docs/issues/001-auth-jwt.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/001-auth-jwt.md) for full TDD plan, test code, and acceptance criteria.

## Scope
- `backend/src/docmind/core/auth.py`
- `backend/tests/unit/core/test_auth.py`

## TDD
- Valid token → returns user_id
- Expired token → 401
- Invalid signature → 401
- Missing token → 401
- Malformed token → 401

## Dependencies
None

## Branch
`feat/1-auth-jwt`
EOF
)" --label "phase-1-infra,backend,tdd,priority-p0"
echo "  #1 created"

gh issue create --repo "$REPO" --title "Alembic initial migration from ORM models" --body "$(cat <<'EOF'
## Summary
Generate initial Alembic migration creating all tables: documents, extractions, extracted_fields, audit_entries, chat_messages, citations.

## Detail
See [`docs/issues/002-alembic-migration.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/002-alembic-migration.md) for full plan and verification steps.

## Scope
- `backend/alembic/env.py`
- `backend/alembic/versions/`

## Dependencies
None

## Branch
`feat/2-alembic-migration`
EOF
)" --label "phase-1-infra,backend,priority-p0"
echo "  #2 created"

gh issue create --repo "$REPO" --title "Document repository: CRUD operations" --body "$(cat <<'EOF'
## Summary
Implement DocumentRepository with full CRUD: create, get_by_id, list_for_user (paginated), delete, update_status. All queries filter by user_id.

## Detail
See [`docs/issues/003-document-repository.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/003-document-repository.md) for full TDD plan with test code.

## Scope
- `backend/src/docmind/modules/documents/repositories.py`
- `backend/tests/unit/modules/documents/test_repositories.py`

## Dependencies
- #2

## Branch
`feat/3-document-repository`
EOF
)" --label "phase-1-infra,backend,tdd,priority-p0"
echo "  #3 created"

gh issue create --repo "$REPO" --title "Document upload service + Supabase Storage" --body "$(cat <<'EOF'
## Summary
Implement document upload flow: handler validates file (type, size ≤20MB), usecase orchestrates service upload to Supabase Storage + repository DB record creation.

## Detail
See [`docs/issues/004-document-upload.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/004-document-upload.md) for full TDD plan with test code.

## Scope
- `backend/src/docmind/modules/documents/services.py`
- `backend/src/docmind/modules/documents/usecase.py`
- `backend/src/docmind/modules/documents/apiv1/handler.py`
- `backend/tests/unit/modules/documents/`

## Dependencies
- #1, #3

## Branch
`feat/4-document-upload`
EOF
)" --label "phase-1-infra,backend,tdd,priority-p0"
echo "  #4 created"

gh issue create --repo "$REPO" --title "Health status: real component checks" --body "$(cat <<'EOF'
## Summary
Implement real health checks: DB connectivity (SQLAlchemy), Redis ping, VLM provider health_check(). Return component-level status.

## Detail
See [`docs/issues/005-health-status.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/005-health-status.md) for full TDD plan.

## Scope
- `backend/src/docmind/modules/health/usecase.py`
- `backend/src/docmind/modules/health/services.py`
- `backend/tests/unit/modules/health/`

## Dependencies
- #2

## Branch
`feat/5-health-status`
EOF
)" --label "phase-1-infra,backend,tdd,priority-p1"
echo "  #5 created"

# Phase 2: CV + VLM
gh issue create --repo "$REPO" --title "CV: PDF to page images (preprocessing)" --body "$(cat <<'EOF'
## Summary
Implement CV preprocessing: PDF to page images using PyMuPDF, image loading, normalization, file type dispatch.

## Detail
See [`docs/issues/006-cv-preprocessing.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/006-cv-preprocessing.md) for full TDD plan.

## Scope
- `backend/src/docmind/library/cv/preprocessing.py`
- `backend/tests/unit/library/cv/test_preprocessing.py`

## Dependencies
None

## Branch
`feat/6-cv-preprocessing`
EOF
)" --label "phase-2-cv-vlm,backend,tdd,priority-p0"
echo "  #6 created"

gh issue create --repo "$REPO" --title "CV: deskew (Hough transform)" --body "$(cat <<'EOF'
## Summary
Implement Hough transform skew detection + correction. detect_skew → angle, correct_skew → rotated image, detect_and_correct → threshold-based auto-correction.

## Detail
See [`docs/issues/007-cv-deskew.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/007-cv-deskew.md) for full TDD plan.

## Scope
- `backend/src/docmind/library/cv/deskew.py`
- `backend/tests/unit/library/cv/test_deskew.py`

## Dependencies
None

## Branch
`feat/7-cv-deskew`
EOF
)" --label "phase-2-cv-vlm,backend,tdd,priority-p0"
echo "  #7 created"

gh issue create --repo "$REPO" --title "CV: quality assessment (blur, noise, contrast)" --body "$(cat <<'EOF'
## Summary
Implement per-region quality assessment: blur (Laplacian), noise (median filter), contrast (histogram). Returns RegionQuality dataclass with scores.

## Detail
See [`docs/issues/008-cv-quality.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/008-cv-quality.md) for full TDD plan.

## Scope
- `backend/src/docmind/library/cv/quality.py`
- `backend/tests/unit/library/cv/test_quality.py`

## Dependencies
None

## Branch
`feat/8-cv-quality`
EOF
)" --label "phase-2-cv-vlm,backend,tdd,priority-p0"
echo "  #8 created"

gh issue create --repo "$REPO" --title "DashScope VLM provider: extract, classify, chat" --body "$(cat <<'EOF'
## Summary
Implement DashScope provider for Qwen-VL: extract(), classify(), chat() methods following VLMProvider Protocol.

## Detail
See [`docs/issues/009-dashscope-provider.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/009-dashscope-provider.md) for full TDD plan.

## Scope
- `backend/src/docmind/library/providers/dashscope.py`
- `backend/tests/unit/library/providers/test_dashscope.py`

## Dependencies
None

## Branch
`feat/9-dashscope-provider`
EOF
)" --label "phase-2-cv-vlm,backend,tdd,priority-p0"
echo "  #9 created"

gh issue create --repo "$REPO" --title "VLM provider factory + health checks" --body "$(cat <<'EOF'
## Summary
Implement provider factory: get_vlm_provider() with registry pattern, lazy loading, env-based default. Health check on each provider.

## Detail
See [`docs/issues/010-vlm-factory.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/010-vlm-factory.md) for full TDD plan.

## Scope
- `backend/src/docmind/library/providers/factory.py`
- `backend/tests/unit/library/providers/test_factory.py`

## Dependencies
- #9

## Branch
`feat/10-vlm-factory`
EOF
)" --label "phase-2-cv-vlm,backend,tdd,priority-p1"
echo "  #10 created"

# Phase 3: Processing Pipeline
gh issue create --repo "$REPO" --title "Pipeline: preprocess node" --body "$(cat <<'EOF'
## Summary
LangGraph preprocess node: convert file to page images, deskew, assess quality, build audit entries.

## Detail
See [`docs/issues/011-pipeline-preprocess.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/011-pipeline-preprocess.md) for full TDD plan.

## Dependencies
- #6, #7, #8

## Branch
`feat/11-pipeline-preprocess`
EOF
)" --label "phase-3-pipeline,backend,tdd,priority-p0"
echo "  #11 created"

gh issue create --repo "$REPO" --title "Pipeline: extract node (general mode)" --body "$(cat <<'EOF'
## Summary
General (schema-free) extraction node: calls VLM extract(), parses structured fields with confidence scores and bounding boxes.

## Detail
See [`docs/issues/012-pipeline-extract-general.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/012-pipeline-extract-general.md) for full TDD plan.

## Dependencies
- #9, #11

## Branch
`feat/12-pipeline-extract-general`
EOF
)" --label "phase-3-pipeline,backend,tdd,priority-p0"
echo "  #12 created"

gh issue create --repo "$REPO" --title "Pipeline: extract node (template mode)" --body "$(cat <<'EOF'
## Summary
Template-aware extraction: auto-detect document type via VLM classify(), load template schema, schema-aware extraction, validate required fields.

## Detail
See [`docs/issues/013-pipeline-extract-template.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/013-pipeline-extract-template.md) for full TDD plan.

## Dependencies
- #12, #20

## Branch
`feat/13-pipeline-extract-template`
EOF
)" --label "phase-3-pipeline,backend,tdd,priority-p0"
echo "  #13 created"

gh issue create --repo "$REPO" --title "Pipeline: postprocess + store nodes" --body "$(cat <<'EOF'
## Summary
Postprocess: merge VLM + CV confidence scores, generate explanations. Store: persist Extraction, ExtractedField, AuditEntry to DB.

## Detail
See [`docs/issues/014-pipeline-postprocess-store.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/014-pipeline-postprocess-store.md) for full TDD plan.

## Dependencies
- #12, #3

## Branch
`feat/14-pipeline-postprocess-store`
EOF
)" --label "phase-3-pipeline,backend,tdd,priority-p0"
echo "  #14 created"

gh issue create --repo "$REPO" --title "Document process SSE endpoint" --body "$(cat <<'EOF'
## Summary
Wire full processing pipeline to POST /api/v1/documents/{id}/process SSE endpoint. Stream step events via ServerSentEvents.

## Detail
See [`docs/issues/015-process-sse-endpoint.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/015-process-sse-endpoint.md) for full TDD plan.

## Dependencies
- #11, #12, #14

## Branch
`feat/15-process-sse-endpoint`
EOF
)" --label "phase-3-pipeline,backend,tdd,priority-p0"
echo "  #15 created"

# Phase 4: Extraction Features
gh issue create --repo "$REPO" --title "Extraction repository + usecase" --body "$(cat <<'EOF'
## Summary
Implement ExtractionRepository (get_by_document_id, get_fields, get_audit_entries) and ExtractionUseCase orchestration.

## Detail
See [`docs/issues/016-extraction-repository.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/016-extraction-repository.md) for full TDD plan.

## Dependencies
- #2, #14

## Branch
`feat/16-extraction-repository`
EOF
)" --label "phase-4-extraction,backend,tdd,priority-p0"
echo "  #16 created"

gh issue create --repo "$REPO" --title "Audit trail: recording + retrieval" --body "$(cat <<'EOF'
## Summary
Audit trail recording during pipeline + GET /extractions/{id}/audit endpoint returning step-by-step timeline.

## Detail
See [`docs/issues/017-audit-trail.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/017-audit-trail.md) for full TDD plan.

## Dependencies
- #14, #16

## Branch
`feat/17-audit-trail`
EOF
)" --label "phase-4-extraction,backend,tdd,priority-p1"
echo "  #17 created"

gh issue create --repo "$REPO" --title "Confidence overlay generation" --body "$(cat <<'EOF'
## Summary
Map confidence to colors (green >0.8, yellow 0.5-0.8, red <0.5). Generate overlay regions with bounding boxes and tooltips.

## Detail
See [`docs/issues/018-confidence-overlay.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/018-confidence-overlay.md) for full TDD plan.

## Dependencies
- #16

## Branch
`feat/18-confidence-overlay`
EOF
)" --label "phase-4-extraction,backend,tdd,priority-p1"
echo "  #18 created"

gh issue create --repo "$REPO" --title "Pipeline comparison: raw vs enhanced diff" --body "$(cat <<'EOF'
## Summary
Store raw VLM baseline, diff against post-processed output. Categorize: corrected, added, unchanged fields.

## Detail
See [`docs/issues/019-pipeline-comparison.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/019-pipeline-comparison.md) for full TDD plan.

## Dependencies
- #16

## Branch
`feat/19-pipeline-comparison`
EOF
)" --label "phase-4-extraction,backend,tdd,priority-p1"
echo "  #19 created"

gh issue create --repo "$REPO" --title "Template management: predefined schemas" --body "$(cat <<'EOF'
## Summary
Load templates from data/templates/ JSON files. Define schemas: invoice, receipt, contract, certificate. GET /templates endpoint.

## Detail
See [`docs/issues/020-template-management.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/020-template-management.md) for full TDD plan.

## Dependencies
None

## Branch
`feat/20-template-management`
EOF
)" --label "phase-4-extraction,backend,tdd,priority-p1"
echo "  #20 created"

# Phase 5: Chat
gh issue create --repo "$REPO" --title "Chat pipeline: router + retrieve nodes" --body "$(cat <<'EOF'
## Summary
LangGraph chat pipeline: router classifies intent (factual, reasoning, summarization, comparison), retrieve searches extracted fields.

## Detail
See [`docs/issues/021-chat-pipeline-router.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/021-chat-pipeline-router.md) for full TDD plan.

## Dependencies
- #9, #16

## Branch
`feat/21-chat-pipeline-router`
EOF
)" --label "phase-5-chat,backend,tdd,priority-p0"
echo "  #21 created"

gh issue create --repo "$REPO" --title "Chat pipeline: reason + cite nodes" --body "$(cat <<'EOF'
## Summary
Reason node generates grounded answers. Cite node extracts citations with page, bounding box, text span.

## Detail
See [`docs/issues/022-chat-pipeline-reason.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/022-chat-pipeline-reason.md) for full TDD plan.

## Dependencies
- #21

## Branch
`feat/22-chat-pipeline-reason`
EOF
)" --label "phase-5-chat,backend,tdd,priority-p0"
echo "  #22 created"

gh issue create --repo "$REPO" --title "Chat repository + message persistence" --body "$(cat <<'EOF'
## Summary
ChatRepository: store/retrieve ChatMessage records. List history ordered by created_at, filter by document_id + user_id.

## Detail
See [`docs/issues/023-chat-repository.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/023-chat-repository.md) for full TDD plan.

## Dependencies
- #2

## Branch
`feat/23-chat-repository`
EOF
)" --label "phase-5-chat,backend,tdd,priority-p0"
echo "  #23 created"

gh issue create --repo "$REPO" --title "Chat SSE endpoint" --body "$(cat <<'EOF'
## Summary
Wire chat pipeline to POST /api/v1/chat/{document_id} SSE endpoint. Stream: thinking, chunk, citation, done/error. GET history.

## Detail
See [`docs/issues/024-chat-sse-endpoint.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/024-chat-sse-endpoint.md) for full TDD plan.

## Dependencies
- #22, #23

## Branch
`feat/24-chat-sse-endpoint`
EOF
)" --label "phase-5-chat,backend,tdd,priority-p0"
echo "  #24 created"

# Phase 6: Frontend
gh issue create --repo "$REPO" --title "Landing page: Hero, Features, Demo, TechStack" --body "$(cat <<'EOF'
## Summary
Build landing page with Hero section, feature showcase, demo placeholder, tech stack grid, and CTAs. Responsive, no auth required.

## Detail
See [`docs/issues/025-landing-page.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/025-landing-page.md) for component tree and implementation plan.

## Dependencies
None

## Branch
`feat/25-landing-page`
EOF
)" --label "phase-6-frontend,frontend,priority-p1"
echo "  #25 created"

gh issue create --repo "$REPO" --title "Auth UI: OAuth login + route protection" --body "$(cat <<'EOF'
## Summary
Supabase OAuth login (Google + GitHub), AuthGuard for protected routes, session management in Zustand auth-store.

## Detail
See [`docs/issues/026-auth-ui.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/026-auth-ui.md) for implementation plan.

## Dependencies
- #1

## Branch
`feat/26-auth-ui`
EOF
)" --label "phase-6-frontend,frontend,priority-p0"
echo "  #26 created"

gh issue create --repo "$REPO" --title "Dashboard: document list + upload" --body "$(cat <<'EOF'
## Summary
Dashboard with DocumentCard grid, UploadArea (drag-drop + file picker), empty state, loading skeleton, pagination.

## Detail
See [`docs/issues/027-dashboard.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/027-dashboard.md) for implementation plan.

## Dependencies
- #4, #26

## Branch
`feat/27-dashboard`
EOF
)" --label "phase-6-frontend,frontend,priority-p0"
echo "  #27 created"

gh issue create --repo "$REPO" --title "Workspace: DocumentViewer with canvas" --body "$(cat <<'EOF'
## Summary
Workspace layout: DocumentViewer (left, canvas with zoom/pan) + sidebar tabs (right). Tab navigation for Extraction, Chat, Audit, Compare.

## Detail
See [`docs/issues/028-workspace-viewer.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/028-workspace-viewer.md) for implementation plan.

## Dependencies
- #26

## Branch
`feat/28-workspace-viewer`
EOF
)" --label "phase-6-frontend,frontend,priority-p0"
echo "  #28 created"

gh issue create --repo "$REPO" --title "ExtractionPanel + AuditPanel" --body "$(cat <<'EOF'
## Summary
ExtractionPanel: field list with ConfidenceBadge, JSON toggle, field selection. AuditPanel: processing step timeline.

## Detail
See [`docs/issues/029-extraction-panel.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/029-extraction-panel.md) for implementation plan.

## Dependencies
- #16, #28

## Branch
`feat/29-extraction-panel`
EOF
)" --label "phase-6-frontend,frontend,priority-p1"
echo "  #29 created"

gh issue create --repo "$REPO" --title "ChatPanel: messages + SSE + citations" --body "$(cat <<'EOF'
## Summary
Chat panel: message thread, input area, SSE streaming display, CitationBlock inline. Citation clicks highlight on DocumentViewer.

## Detail
See [`docs/issues/030-chat-panel.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/030-chat-panel.md) for implementation plan.

## Dependencies
- #24, #28

## Branch
`feat/30-chat-panel`
EOF
)" --label "phase-6-frontend,frontend,priority-p1"
echo "  #30 created"

gh issue create --repo "$REPO" --title "ComparePanel + ProcessingProgress" --body "$(cat <<'EOF'
## Summary
ComparePanel: side-by-side raw vs enhanced with color-coded diffs. ProcessingProgress: SSE step-by-step progress bar.

## Detail
See [`docs/issues/031-compare-progress.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/031-compare-progress.md) for implementation plan.

## Dependencies
- #15, #19, #28

## Branch
`feat/31-compare-progress`
EOF
)" --label "phase-6-frontend,frontend,priority-p1"
echo "  #31 created"

# Phase 7: Testing + Polish
gh issue create --repo "$REPO" --title "Unit tests: 80%+ coverage" --body "$(cat <<'EOF'
## Summary
Comprehensive unit tests across all backend modules. Target 80%+ coverage. Services, repositories, CV library, providers, pipeline nodes, schemas, auth.

## Detail
See [`docs/issues/032-unit-tests.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/032-unit-tests.md) for test plan and file list.

## Dependencies
Phase 1-5 complete

## Branch
`feat/32-unit-tests`
EOF
)" --label "phase-7-testing,backend,tdd,priority-p0"
echo "  #32 created"

gh issue create --repo "$REPO" --title "Integration tests: API endpoints + pipeline" --body "$(cat <<'EOF'
## Summary
Integration tests with TestClient + async DB (SQLite). Test full API endpoints and pipeline end-to-end with mocked VLM.

## Detail
See [`docs/issues/033-integration-tests.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/033-integration-tests.md) for test plan.

## Dependencies
Phase 1-5 complete

## Branch
`feat/33-integration-tests`
EOF
)" --label "phase-7-testing,backend,priority-p1"
echo "  #33 created"

gh issue create --repo "$REPO" --title "Demo data: pre-loaded example documents" --body "$(cat <<'EOF'
## Summary
Pre-loaded demo documents: invoice PDF, receipt image, contract PDF. Pre-computed baselines in data/demo/baselines/. Docker auto-load.

## Detail
See [`docs/issues/034-demo-data.md`](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/034-demo-data.md) for data format and structure.

## Dependencies
Phase 3-4 complete

## Branch
`feat/34-demo-data`
EOF
)" --label "phase-7-testing,priority-p1"
echo "  #34 created"

echo ""
echo "=== All 34 issues created ==="
echo "View at: https://github.com/$REPO/issues"
