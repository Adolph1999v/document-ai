UV := uv
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help setup backend-sync backend-run db-init frontend-install frontend-run test lint build

help:
	@echo "Available targets:"
	@echo "  make setup            Install backend and frontend dependencies"
	@echo "  make backend-sync     Create/sync the isolated backend environment with uv"
	@echo "  make backend-run      Start the FastAPI development server"
	@echo "  make db-init          Apply backend/sql/schema.sql to the local document_ai database"
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

db-init:
	psql -d document_ai -f $(BACKEND_DIR)/sql/schema.sql

frontend-install:
	npm --prefix $(FRONTEND_DIR) install

frontend-run:
	npm --prefix $(FRONTEND_DIR) run dev

test:
	cd $(BACKEND_DIR) && $(UV) run pytest

lint:
	cd $(BACKEND_DIR) && $(UV) run ruff check .

build:
	npm --prefix $(FRONTEND_DIR) run build
