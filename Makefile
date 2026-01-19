.PHONY: help install install-dev test lint format clean build publish

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package dependencies
	uv sync

install-dev: ## Install package with dev dependencies
	uv sync --extra dev

test: ## Run all tests
	uv run pytest tests/ -v

test-unit: ## Run unit tests only
	uv run pytest tests/test_terminal.py tests/test_api.py tests/test_e2e.py -v

test-vim: ## Run vim integration tests
	uv run pytest tests/test_vim.py -v

test-claude: ## Run Claude CLI tests (requires authentication)
	uv run pytest tests/test_claude.py -v

test-frontend: ## Run frontend e2e tests
	uv run pytest tests/test_frontend_e2e.py -v

lint: ## Run code quality checks (placeholder - add linters as needed)
	@echo "Linting not yet configured. Consider adding: ruff, mypy, black"

format: ## Format code (placeholder - add formatters as needed)
	@echo "Formatting not yet configured. Consider adding: black, isort, ruff format"

clean: ## Clean build artifacts
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean ## Build package for distribution
	uv build

publish: build ## Publish package to PyPI (use Release commit for automation)
	@echo "To publish to PyPI, commit with message: 'Release X.Y.Z'"
	@echo "This will trigger automated PyPI publishing via GitHub Actions"

server: ## Start the terminal wrapper server
	uv run python main.py

server-public: ## Start server on public address
	uv run python main.py --host 0.0.0.0 --port 6489
