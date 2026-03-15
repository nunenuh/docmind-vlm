#!/usr/bin/env bash
# Creates remaining GitHub issues #19-#34
# Usage: ./scripts/create-remaining-issues.sh
set -euo pipefail
REPO="nunenuh/docmind-vlm"

echo "=== Creating remaining issues (#19-#34) ==="


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
echo "=== Remaining issues created ==="
