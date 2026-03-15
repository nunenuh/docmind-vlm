# Git Workflow

Standard git workflow for all development on this project.

---

## Branch Strategy

| Branch | Purpose | Protected |
|--------|---------|-----------|
| `main` | Production-ready code | Yes — merge via PR only |
| `dev` | Integration branch, all features merge here | Yes — merge via PR only |
| `feat/<issue-id>-<slug>` | Feature work | No |
| `fix/<issue-id>-<slug>` | Bug fixes | No |
| `chore/<issue-id>-<slug>` | Maintenance, docs, CI | No |
| `test/<issue-id>-<slug>` | Test-only changes | No |

**All work branches are created from `dev`.** Never branch from `main` directly.

---

## Commit Message Convention

**This convention applies to commit messages and branch names only — NOT issue titles.**

Issue titles should be plain, descriptive, and readable (e.g., "Implement document upload service"). The `type(scope):` prefix is for git commits.

```
<type>(<scope>): <description> #<issue-id>
```

### Types

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Build, CI, tooling, dependencies |
| `perf` | Performance improvement |
| `ci` | CI/CD pipeline changes |

### Scope

Scope matches the module or area being changed:

| Scope | Area |
|-------|------|
| `documents` | Documents module (upload, list, delete, process) |
| `extractions` | Extractions module (results, audit, overlay, comparison) |
| `chat` | Chat module (chat stream, history) |
| `templates` | Templates module |
| `health` | Health module |
| `cv` | CV library (deskew, quality, preprocessing) |
| `vlm` | VLM providers (DashScope, OpenAI, Google, Ollama) |
| `pipeline` | LangGraph pipelines (processing, chat) |
| `core` | Config, auth, logging, dependencies |
| `dbase` | SQLAlchemy, Supabase client, storage |
| `api` | Router, middleware, shared API concerns |
| `ui` | Frontend components |
| `state` | Frontend state management |
| `api-client` | Frontend API client layer |
| `docker` | Docker, compose files |
| `deps` | Dependency updates |

### Examples

```
feat(documents): add file upload handler #12
fix(vlm): handle empty DashScope response #34
test(extractions): add edge cases for overlay service #12
refactor(dbase): extract base repository class #45
chore(deps): bump fastapi to 0.115.x #50
feat(ui): implement workspace document viewer #18
docs(api): update endpoint documentation #22
```

### Rules

- Issue ID is **required** in every commit message — append `#<issue-id>` at the end
- Description is imperative, lowercase, no period: "add upload handler" not "Added upload handler."
- Scope is required for `feat`, `fix`, `refactor`, `test`
- Scope is optional for `docs`, `chore`, `ci`
- Body is optional — use it for context when the description alone is not enough

### Co-Authorship

When Claude (AI assistant) helps write code, **always** add a `Co-Authored-By` trailer to the commit message:

```
feat(ui): implement ChatPanel component #3

Co-Authored-By: Claude <noreply@anthropic.com>
```

This is required for transparency and proper attribution. The trailer goes after a blank line at the end of the commit body.

---

## Workflow: Issue to Merge

### 1. Pick an Issue

Every unit of work starts from a GitHub issue. The issue defines what to build, fix, or change.

**Issue title format**: Plain, descriptive, and readable. Use `Component: what it does` or just a clear description.

```
Good:  "DocumentViewer: page navigation and zoom"
Good:  "Frontend project scaffold (Vite + React + TS)"
Good:  "Fix empty extraction results in processing pipeline"
Bad:   "feat(ui): implement DocumentViewer"       ← commit convention, not for issues
Bad:   "Update stuff"                              ← too vague
```

### 2. Create Branch from `dev`

```bash
git checkout dev
git pull origin dev
git fetch --all

# Create and push the branch immediately
git checkout -b feat/<issue-id>-<short-slug>
git push -u origin feat/<issue-id>-<short-slug>
```

Push the empty branch first so it is visible to the team.

### 3. Do the Work

The work follows this order depending on the type:

#### Backend Work

1. **Implement the feature** — write the code based on the issue and related specs
2. **Write tests** — unit tests at minimum, integration if applicable
3. **Verify** — run `make test-unit` and `make lint`
4. **Commit** — atomic commits following the convention above

#### Frontend Work

1. **Implement the feature** — build components, state, API client based on specs
2. **Pause for review** — present the implementation for user review before proceeding
3. **Get agreement** — wait for explicit approval
4. **Write tests** — after approval, add tests
5. **Commit** — atomic commits following the convention above

> **Frontend requires review before PR.** Do not create a PR for frontend work until the user has reviewed and approved the implementation.

### 4. Keep Branch Updated

Rebase on `dev` regularly to avoid merge conflicts:

```bash
git fetch origin
git rebase origin/dev
```

If conflicts arise, resolve them and continue the rebase.

### 5. Create Pull Request

When all work is complete (code + tests + passing CI):

```bash
# Ensure branch is up to date
git fetch origin
git rebase origin/dev
git push --force-with-lease
```

Create a PR targeting `dev` with this format:

```markdown
## Summary

<One-line description of what this PR does>

Closes #<issue-id>

## Changes

- <Bullet list of what changed and why>

## Type

- [ ] feat
- [ ] fix
- [ ] refactor
- [ ] test
- [ ] docs
- [ ] chore

## Checklist

- [ ] Code follows project conventions (`specs/conventions/`)
- [ ] Tests added/updated
- [ ] `make test-unit` passes
- [ ] `make lint` passes
- [ ] No hardcoded secrets or credentials
- [ ] Commit messages follow convention with issue ID
```

### 6. Review

- Wait for reviewer approval
- Address any feedback with new commits (do not force-push during review unless asked)
- Once approved, proceed to merge

### 7. Merge and Clean Up

After PR is approved:

```bash
# Merge via GitHub (squash or merge commit — reviewer decides)
# Then locally:
git checkout dev
git pull origin dev
git fetch --all

# Delete the feature branch
git branch -d feat/<issue-id>-<short-slug>
git push origin --delete feat/<issue-id>-<short-slug>
```

---

## Flow Diagram

```
Issue
  |
  v
git checkout dev && git pull
  |
  v
git checkout -b feat/<id>-<slug>
  |
  v
git push -u origin feat/<id>-<slug>    (push empty branch)
  |
  v
+---------------------------+
| Do the Work               |
|  Backend: code -> tests   |
|  Frontend: code -> review |
|           -> agree -> tests|
+---------------------------+
  |
  v
git rebase origin/dev
  |
  v
Create PR -> dev
  |
  v
Review & Approval
  |
  v
Merge PR
  |
  v
git checkout dev
git pull origin dev
git fetch --all
  |
  v
Delete feature branch
  |
  v
Done. Pick next issue.
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start work | `git checkout dev && git pull && git checkout -b feat/<id>-<slug>` |
| Push new branch | `git push -u origin feat/<id>-<slug>` |
| Sync with dev | `git fetch origin && git rebase origin/dev` |
| Push updates | `git push` (or `--force-with-lease` after rebase) |
| Switch back to dev | `git checkout dev && git pull origin dev && git fetch --all` |
| Delete local branch | `git branch -d feat/<id>-<slug>` |
| Delete remote branch | `git push origin --delete feat/<id>-<slug>` |
