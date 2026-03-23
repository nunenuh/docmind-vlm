.PHONY: help setup setup-backend setup-frontend dev dev-backend dev-frontend backend frontend stop docker-up docker-build docker-down test test-unit test-integration test-coverage lint format migrate migrate-create migrate-downgrade migrate-history

# ── Config ────────────────────────────────────────────
BACKEND_PORT  ?= 8009
FRONTEND_PORT ?= 5177
ROOT_DIR      := $(shell pwd)
PID_DIR       := $(ROOT_DIR)/.pids

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────

setup: setup-backend setup-frontend ## First-time setup: env files + all deps

setup-backend: ## Setup backend: .env + install deps
	@test -f backend/.env || cp backend/.env.example backend/.env
	@if command -v poetry >/dev/null 2>&1; then \
		cd backend && poetry install; \
	else \
		cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"; \
	fi

setup-frontend: ## Setup frontend: .env + npm install
	@test -f frontend/.env || cp frontend/.env.example frontend/.env
	cd frontend && npm install

# ── Dev Servers ────────────────────────────────────────

dev: stop ## Run backend + frontend (background, logs to .pids/)
	@mkdir -p $(PID_DIR)
	@echo "Starting backend on :$(BACKEND_PORT)..."
	@cd backend && .venv/bin/uvicorn docmind.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) \
		> $(PID_DIR)/backend.log 2>&1 & echo $$! > $(PID_DIR)/backend.pid
	@echo "Starting frontend on :$(FRONTEND_PORT)..."
	@cd frontend && npx vite --port $(FRONTEND_PORT) --host 0.0.0.0 \
		> $(PID_DIR)/frontend.log 2>&1 & echo $$! > $(PID_DIR)/frontend.pid
	@sleep 2
	@echo ""
	@echo "  Backend:  http://localhost:$(BACKEND_PORT)"
	@echo "  Frontend: http://localhost:$(FRONTEND_PORT)"
	@echo ""
	@echo "  Logs:     tail -f $(PID_DIR)/backend.log"
	@echo "            tail -f $(PID_DIR)/frontend.log"
	@echo "  Stop:     make stop"

dev-fg: ## Run backend + frontend (foreground, Ctrl+C to stop both)
	@bash -c 'trap "kill 0; exit" SIGINT SIGTERM; \
	cd backend && .venv/bin/uvicorn docmind.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) & \
	cd frontend && npx vite --port $(FRONTEND_PORT) --host 0.0.0.0 & \
	wait'

backend: ## FastAPI dev server (foreground)
	cd backend && .venv/bin/uvicorn docmind.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

frontend: ## Vite dev server (foreground)
	cd frontend && npx vite --port $(FRONTEND_PORT) --host 0.0.0.0

stop: ## Stop background dev servers + kill ports
	@# Kill by PID file (process group)
	@if [ -f $(PID_DIR)/backend.pid ]; then \
		kill -- -$$(cat $(PID_DIR)/backend.pid) 2>/dev/null || kill $$(cat $(PID_DIR)/backend.pid) 2>/dev/null || true; \
		rm -f $(PID_DIR)/backend.pid; \
	fi
	@if [ -f $(PID_DIR)/frontend.pid ]; then \
		kill -- -$$(cat $(PID_DIR)/frontend.pid) 2>/dev/null || kill $$(cat $(PID_DIR)/frontend.pid) 2>/dev/null || true; \
		rm -f $(PID_DIR)/frontend.pid; \
	fi
	@# Force kill anything on our ports (SIGKILL, repeat to catch respawns)
	@for i in 1 2 3; do \
		lsof -ti :$(BACKEND_PORT) 2>/dev/null | xargs -r kill -9 2>/dev/null || true; \
		lsof -ti :$(FRONTEND_PORT) 2>/dev/null | xargs -r kill -9 2>/dev/null || true; \
		fuser -k $(BACKEND_PORT)/tcp 2>/dev/null || true; \
		fuser -k $(FRONTEND_PORT)/tcp 2>/dev/null || true; \
		sleep 0.2; \
	done
	@echo "Servers stopped (ports $(BACKEND_PORT) + $(FRONTEND_PORT) freed)"

logs: ## Tail both server logs
	@tail -f $(PID_DIR)/backend.log $(PID_DIR)/frontend.log

logs-backend: ## Tail backend log
	@tail -f $(PID_DIR)/backend.log

logs-frontend: ## Tail frontend log
	@tail -f $(PID_DIR)/frontend.log

# ── Supabase Local ────────────────────────────────────

supabase-start: ## Start local Supabase (Postgres + Auth + Storage)
	npx supabase start

supabase-stop: ## Stop local Supabase
	npx supabase stop

supabase-status: ## Show local Supabase status + URLs
	npx supabase status

use-local: ## Switch to local Supabase (.env.local → .env)
	@cp backend/.env backend/.env.cloud.bak
	@cp backend/.env.local backend/.env
	@echo "Switched to LOCAL Supabase. Run 'make migrate' to set up tables."

use-cloud: ## Switch back to cloud Supabase (.env.cloud.bak → .env)
	@if [ -f backend/.env.cloud.bak ]; then \
		cp backend/.env.cloud.bak backend/.env; \
		echo "Switched to CLOUD Supabase."; \
	else \
		echo "No cloud backup found. Edit backend/.env manually."; \
	fi

# ── Docker ─────────────────────────────────────────────

docker-up: ## Start all services
	docker compose up -d

docker-build: ## Build and start all services
	docker compose up -d --build

docker-down: ## Stop all services
	docker compose down

# ── Tests ──────────────────────────────────────────────

test: ## All tests
	cd backend && .venv/bin/python -m pytest tests/ -v

test-unit: ## Unit tests only
	cd backend && .venv/bin/python -m pytest tests/unit/ -v

test-integration: ## Integration tests (requires Supabase)
	cd backend && .venv/bin/python -m pytest tests/integration/ -v

test-coverage: ## Tests with coverage report
	cd backend && .venv/bin/python -m pytest tests/ --cov=docmind --cov-report=term-missing --cov-fail-under=80

# ── Migrations ────────────────────────────────────────

migrate: ## Run database migrations to latest
	cd backend && PYTHONPATH=src .venv/bin/alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	cd backend && PYTHONPATH=src .venv/bin/alembic revision --autogenerate -m "$(msg)"

migrate-downgrade: ## Downgrade one migration
	cd backend && PYTHONPATH=src .venv/bin/alembic downgrade -1

migrate-history: ## Show migration history
	cd backend && PYTHONPATH=src .venv/bin/alembic history --verbose

# ── Lint / Format ──────────────────────────────────────

lint: ## Lint checks (ruff)
	cd backend && .venv/bin/ruff check src/ tests/

format: ## Auto-format (ruff)
	cd backend && .venv/bin/ruff format src/ tests/
	cd backend && .venv/bin/ruff check --fix src/ tests/
