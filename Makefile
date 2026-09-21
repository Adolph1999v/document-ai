UV := uv
BACKEND_DIR := backend
FRONTEND_DIR := frontend
COMPOSE := docker compose --env-file $(BACKEND_DIR)/.env
LOCAL_LLM_MODEL ?= qwen/qwen3.6-27b
LOCAL_LLM_CONTEXT_LENGTH ?= 32768

.PHONY: help setup backend-sync backend-run db-up db-init db-status db-stop model-server \
	model-server-stop model-load model-unload model-status readiness frontend-install \
	frontend-run test lint build

help:
	@echo "Available targets:"
	@echo "  make setup            Install backend and frontend dependencies"
	@echo "  make backend-sync     Create/sync the isolated backend environment with uv"
	@echo "  make backend-run      Start the FastAPI development server"
	@echo "  make db-up            Start the local PostgreSQL/pgvector container"
	@echo "  make db-init          Reapply backend/sql/schema.sql to the running database"
	@echo "  make db-status        Show the local database container status"
	@echo "  make db-stop          Stop the local database without deleting its data"
	@echo "  make model-server     Start the LM Studio local server on port 1234"
	@echo "  make model-server-stop Stop the LM Studio local server"
	@echo "  make model-load       Load Qwen with a 32K context window"
	@echo "  make model-unload     Unload Qwen and free its model memory"
	@echo "  make model-status     Show models currently loaded by LM Studio"
	@echo "  make readiness        Check whether the running API dependencies are ready"
	@echo "  make frontend-install Install frontend dependencies"
	@echo "  make frontend-run     Start the Vite development server"
	@echo "  make test             Run backend tests"
	@echo "  make lint             Run backend linting"
	@echo "  make build            Create a production frontend build"

setup: backend-sync frontend-install

backend-sync:
	cd $(BACKEND_DIR) && $(UV) sync --all-groups

backend-run:
	cd $(BACKEND_DIR) && $(UV) run uvicorn main:app --reload

db-up:
	$(COMPOSE) up -d postgres

db-init:
	$(COMPOSE) exec -T postgres sh -c \
		'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -f /docker-entrypoint-initdb.d/001-schema.sql'

db-status:
	$(COMPOSE) ps postgres

db-stop:
	$(COMPOSE) stop postgres

model-server:
	lms server start --port 1234

model-server-stop:
	lms server stop

model-load:
	lms load $(LOCAL_LLM_MODEL) --context-length $(LOCAL_LLM_CONTEXT_LENGTH) --yes

model-unload:
	lms unload $(LOCAL_LLM_MODEL)

model-status:
	lms ps

readiness:
	curl --fail --silent --show-error http://127.0.0.1:8000/api/readiness

frontend-install:
	npm --prefix $(FRONTEND_DIR) install

frontend-run:
	npm --prefix $(FRONTEND_DIR) run dev

test:
	cd $(BACKEND_DIR) && $(UV) run python -m pytest

lint:
	cd $(BACKEND_DIR) && $(UV) run ruff check .

build:
	npm --prefix $(FRONTEND_DIR) run build
