.PHONY: help install install-dev setup test run clean lint format

help:		## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies
	pip install -r requirements.txt

install-dev:	## Install in development mode with dev dependencies
	pip install -e ".[dev]"

setup:		## Set up the project (install + create config)
	@make install
	@echo "Creating config directory..."
	@mkdir -p config
	@if [ ! -f config/config.yaml ]; then \
		echo "Creating default config file..."; \
		cp config/config.example.yaml config/config.yaml; \
		echo "✅ Config created at config/config.yaml"; \
		echo "📝 Please edit config/config.yaml with your settings"; \
	else \
		echo "✅ Config file already exists at config/config.yaml"; \
	fi

test:		## Run tests
	python test_server.py

run:		## Run the MCP server
	python run_server.py

run-config:	## Run the MCP server with config file
	python run_server.py config/config.yaml

cli:		## Show CLI help
	python -m terragrunt_gcp_mcp.cli --help

lint:		## Run linting (if installed)
	@command -v flake8 >/dev/null 2>&1 && flake8 src/ || echo "flake8 not installed, run 'make install-dev'"
	@command -v mypy >/dev/null 2>&1 && mypy src/ || echo "mypy not installed, run 'make install-dev'"

format:		## Format code (if installed)
	@command -v black >/dev/null 2>&1 && black src/ || echo "black not installed, run 'make install-dev'"
	@command -v isort >/dev/null 2>&1 && isort src/ || echo "isort not installed, run 'make install-dev'"

clean:		## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

status:		## Show project status
	@echo "🔧 Terragrunt GCP MCP Tool Status"
	@echo "================================"
	@echo "Python: $(shell python --version)"
	@echo "Config: $(shell [ -f config/config.yaml ] && echo '✅ Found' || echo '❌ Not found')"
	@echo "Dependencies: $(shell pip list | grep -E '(mcp|fastmcp|google-cloud)' | wc -l) installed"
	@echo ""
	@echo "To get started:"
	@echo "  make setup    # Set up the project"
	@echo "  make test     # Run tests"
	@echo "  make run      # Start the server" 