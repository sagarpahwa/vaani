PYTHON := $(shell [ -d .venv ] && echo .venv/bin/python3 || echo python3)
PIP    := $(shell [ -d .venv ] && echo .venv/bin/pip || echo pip3)

.PHONY: help install venv lint format lint-fix test test-unit test-integration test-all \
        db-up db-down db-init db-indexes db-seed db-verify db-setup \
        pre-commit-install pre-commit-run secrets-baseline \
        coverage-ratchet coverage-update-baseline clean clean-pyc

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Vaani — Developer Commands"
	@echo ""
	@echo "Setup"
	@echo "  make install              Install all Python + Node.js deps"
	@echo "  make venv                 Create .venv virtual environment"
	@echo "  make pre-commit-install   Install git hooks"
	@echo "  make secrets-baseline     Create .secrets.baseline for detect-secrets"
	@echo ""
	@echo "Quality"
	@echo "  make lint                 ruff + black --check (no changes)"
	@echo "  make format               black (fix in place)"
	@echo "  make lint-fix             ruff --fix + black (fix in place)"
	@echo "  make pre-commit-run       Run all hooks on all tracked files"
	@echo ""
	@echo "Tests"
	@echo "  make test                 Unit tests only (fast, no Docker)"
	@echo "  make test-integration     Integration tests (requires make db-up)"
	@echo "  make test-all             All tests"
	@echo "  make coverage-ratchet     Check coverage against quality-baseline.json"
	@echo "  make coverage-update-baseline  Update quality-baseline.json"
	@echo ""
	@echo "Database"
	@echo "  make db-up                Start MongoDB + mongo-express"
	@echo "  make db-down              Stop containers"
	@echo "  make db-setup             Full init + indexes + seed + verify"
	@echo "  make db-init              Create collections with validators"
	@echo "  make db-indexes           Create all indexes"
	@echo "  make db-seed              Seed taxonomies + speakers"
	@echo "  make db-verify            Run verification checks"
	@echo ""
	@echo "Cleanup"
	@echo "  make clean                Remove build artifacts"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────
venv:
	python3 -m venv .venv
	@echo "Activate: source .venv/bin/activate"

install: venv
	$(PIP) install -e ".[dev]"
	npm ci
	@echo "All dependencies installed."

pre-commit-install:
	$(PIP) install pre-commit
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "Git hooks installed."

secrets-baseline:
	$(PIP) install detect-secrets
	detect-secrets scan \
		--exclude-files '\.env\.example' \
		--exclude-files '\.secrets\.baseline' \
		> .secrets.baseline
	@echo ".secrets.baseline created. Commit this file."

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	ruff check scripts/python/
	black --check scripts/python/

format:
	black scripts/python/

lint-fix:
	ruff check --fix scripts/python/
	black scripts/python/

pre-commit-run:
	pre-commit run --all-files

# ── Tests ─────────────────────────────────────────────────────────────────────
test: test-unit

test-unit:
	$(PYTHON) -m pytest tests/unit/ \
		--cov=scripts/python \
		--cov-report=term-missing \
		--cov-report=json \
		--cov-report=html \
		--cov-fail-under=70 \
		-v

test-integration:
	$(PYTHON) -m pytest tests/integration/ -m integration -v --tb=short

test-all:
	$(PYTHON) -m pytest tests/ -m "integration or not integration" -v --tb=short

coverage-ratchet:
	$(PYTHON) scripts/ci/ratchet_coverage.py

coverage-update-baseline:
	$(PYTHON) scripts/ci/update_baseline.py

# ── Database ──────────────────────────────────────────────────────────────────
db-up:
	docker-compose up -d
	@echo "Waiting for MongoDB to be healthy..."
	@until docker inspect --format='{{.State.Health.Status}}' vaani_mongo 2>/dev/null | grep -q "healthy"; do \
		printf '.'; sleep 2; \
	done
	@echo ""
	@echo "MongoDB ready — mongo-express: http://localhost:8081"

db-down:
	docker-compose down

db-init:
	node scripts/node/db_init.js

db-indexes:
	node scripts/node/create_indexes.js

db-seed:
	$(PYTHON) scripts/python/seed_taxonomies.py
	$(PYTHON) scripts/python/seed_speakers.py

db-verify:
	node scripts/node/verify.js

db-setup: db-init db-indexes db-seed db-verify
	@echo ""
	@echo "Database setup complete."

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: clean-pyc
	rm -rf .pytest_cache htmlcov .coverage coverage.json
	@echo "Build artifacts removed."

clean-pyc:
	find . -path ./.venv -prune -o -type f -name "*.pyc" -print -delete
	find . -path ./.venv -prune -o -type d -name "__pycache__" -print -exec rm -rf {} + 2>/dev/null || true
