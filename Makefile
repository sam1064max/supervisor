# Supervisor - Makefile
# ----------------------------------------------------------------------
# Run all quality gates with: make all
# Run an individual target with: make <target>
# ----------------------------------------------------------------------

SHELL := /bin/bash
.PHONY: help install sync lint format type test test-cov clean run agents plan docker-build docker-run docker-down ci all

help:
	@echo "Supervisor - make targets"
	@echo "  install      : create venv and install all deps (incl. dev)"
	@echo "  sync         : uv sync"
	@echo "  lint         : ruff check ."
	@echo "  format       : black . && ruff check --fix ."
	@echo "  type         : mypy src tests"
	@echo "  test         : pytest"
	@echo "  test-cov     : pytest --cov=src --cov-report=term-missing"
	@echo "  run          : supervisor run"
	@echo "  plan         : supervisor plan"
	@echo "  agents       : supervisor agents"
	@echo "  docker-build : docker build -t supervisor:dev ."
	@echo "  docker-run   : docker compose up"
	@echo "  docker-down  : docker compose down -v"
	@echo "  ci           : lint + type + test (used by GitHub Actions)"
	@echo "  all          : format + lint + type + test-cov"
	@echo "  clean        : remove caches and build artifacts"

install:
	uv venv
	uv sync --all-extras --dev

sync:
	uv sync --all-extras --dev

lint:
	uv run ruff check .

format:
	uv run black .
	uv run ruff check --fix .

type:
	uv run mypy src tests

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src --cov-report=term-missing --cov-report=xml

run:
	uv run supervisor run

plan:
	uv run supervisor plan

agents:
	uv run supervisor agents

docker-build:
	docker build -t supervisor:dev .

docker-run:
	docker compose up

docker-down:
	docker compose down -v

ci: lint type test

all: format lint type test-cov

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
