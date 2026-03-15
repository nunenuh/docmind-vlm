#!/usr/bin/env bash
# Creates remaining GitHub issues #21-#34 one at a time
# If it fails mid-way, just comment out the ones already created and re-run
set -uo pipefail
REPO="nunenuh/docmind-vlm"

create_issue() {
  local title="$1" body="$2" labels="$3" num="$4"
  echo -n "  Creating #${num}... "
  if gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels" 2>/dev/null; then
    echo "done"
  else
    echo "FAILED (retry later)"
    return 1
  fi
  sleep 2
}

echo "=== Creating issues #21-#34 ==="

create_issue "Chat pipeline: router + retrieve nodes" \
"See [docs/issues/021-chat-pipeline-router.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/021-chat-pipeline-router.md)

Deps: #9, #16 | Branch: feat/21-chat-pipeline-router" \
"phase-5-chat,backend,tdd,priority-p0" 21 || true

create_issue "Chat pipeline: reason + cite nodes" \
"See [docs/issues/022-chat-pipeline-reason.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/022-chat-pipeline-reason.md)

Deps: #21 | Branch: feat/22-chat-pipeline-reason" \
"phase-5-chat,backend,tdd,priority-p0" 22 || true

create_issue "Chat repository + message persistence" \
"See [docs/issues/023-chat-repository.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/023-chat-repository.md)

Deps: #2 | Branch: feat/23-chat-repository" \
"phase-5-chat,backend,tdd,priority-p0" 23 || true

create_issue "Chat SSE endpoint" \
"See [docs/issues/024-chat-sse-endpoint.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/024-chat-sse-endpoint.md)

Deps: #22, #23 | Branch: feat/24-chat-sse-endpoint" \
"phase-5-chat,backend,tdd,priority-p0" 24 || true

create_issue "Landing page: Hero, Features, Demo, TechStack" \
"See [docs/issues/025-landing-page.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/025-landing-page.md)

Deps: None | Branch: feat/25-landing-page" \
"phase-6-frontend,frontend,priority-p1" 25 || true

create_issue "Auth UI: OAuth login + route protection" \
"See [docs/issues/026-auth-ui.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/026-auth-ui.md)

Deps: #1 | Branch: feat/26-auth-ui" \
"phase-6-frontend,frontend,priority-p0" 26 || true

create_issue "Dashboard: document list + upload" \
"See [docs/issues/027-dashboard.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/027-dashboard.md)

Deps: #4, #26 | Branch: feat/27-dashboard" \
"phase-6-frontend,frontend,priority-p0" 27 || true

create_issue "Workspace: DocumentViewer with canvas" \
"See [docs/issues/028-workspace-viewer.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/028-workspace-viewer.md)

Deps: #26 | Branch: feat/28-workspace-viewer" \
"phase-6-frontend,frontend,priority-p0" 28 || true

create_issue "ExtractionPanel + AuditPanel" \
"See [docs/issues/029-extraction-panel.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/029-extraction-panel.md)

Deps: #16, #28 | Branch: feat/29-extraction-panel" \
"phase-6-frontend,frontend,priority-p1" 29 || true

create_issue "ChatPanel: messages + SSE + citations" \
"See [docs/issues/030-chat-panel.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/030-chat-panel.md)

Deps: #24, #28 | Branch: feat/30-chat-panel" \
"phase-6-frontend,frontend,priority-p1" 30 || true

create_issue "ComparePanel + ProcessingProgress" \
"See [docs/issues/031-compare-progress.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/031-compare-progress.md)

Deps: #15, #19, #28 | Branch: feat/31-compare-progress" \
"phase-6-frontend,frontend,priority-p1" 31 || true

create_issue "Unit tests: 80%+ coverage" \
"See [docs/issues/032-unit-tests.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/032-unit-tests.md)

Deps: Phase 1-5 | Branch: feat/32-unit-tests" \
"phase-7-testing,backend,tdd,priority-p0" 32 || true

create_issue "Integration tests: API endpoints + pipeline" \
"See [docs/issues/033-integration-tests.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/033-integration-tests.md)

Deps: Phase 1-5 | Branch: feat/33-integration-tests" \
"phase-7-testing,backend,priority-p1" 33 || true

create_issue "Demo data: pre-loaded example documents" \
"See [docs/issues/034-demo-data.md](https://github.com/nunenuh/docmind-vlm/blob/dev/docs/issues/034-demo-data.md)

Deps: Phase 3-4 | Branch: feat/34-demo-data" \
"phase-7-testing,priority-p1" 34 || true

echo ""
echo "=== Done ==="
echo "Check: https://github.com/$REPO/issues"
