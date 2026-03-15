.PHONY: help setup dev backend frontend docker-up docker-build docker-down test test-unit test-integration test-coverage lint format

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## First-time setup: create .env + install deps
	@test -f .env || cp .env.example .env
	cd backend && poetry install
	cd frontend && npm install

dev: ## Run backend + frontend in parallel
	@make backend & make frontend

backend: ## FastAPI dev server on port 8000
	cd backend && poetry run uvicorn docmind.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Vite dev server on port 5173
	cd frontend && npm run dev

docker-up: ## Start all services
	docker compose up -d

docker-build: ## Build and start all services
	docker compose up -d --build

docker-down: ## Stop all services
	docker compose down

test: ## All tests
	cd backend && poetry run pytest tests/ -v

test-unit: ## Unit tests only
	cd backend && poetry run pytest tests/unit/ -v

test-integration: ## Integration tests (requires Supabase)
	cd backend && poetry run pytest tests/integration/ -v

test-coverage: ## Tests with coverage report
	cd backend && poetry run pytest tests/ --cov=docmind --cov-report=term-missing --cov-fail-under=80

lint: ## Lint checks (ruff)
	cd backend && poetry run ruff check src/ tests/

format: ## Auto-format (black + isort)
	cd backend && poetry run black src/ tests/
	cd backend && poetry run isort src/ tests/
