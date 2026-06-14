# Fluidra Pool Assistant — developer convenience targets
# Requires: Git Bash / WSL on Windows, or any POSIX shell on macOS/Linux.
# All Python commands go through `uv`; all JS commands go through `pnpm`/`turbo`.

.PHONY: bootstrap dev test db-migrate db-rollback help

bootstrap: ## one-time machine setup (run once after clone)
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@command -v pnpm >/dev/null 2>&1 || npm install -g pnpm
	uv sync
	pnpm install
	docker compose -f infrastructure/docker/compose.dev.yml pull
	@for d in services/*/; do \
		if [ -f "$$d.env.example" ] && [ ! -f "$$d.env" ]; then \
			cp "$$d.env.example" "$$d.env"; \
			echo "Created $$d.env from example"; \
		fi; \
	done
	@echo ""
	@echo "Bootstrap complete. Run 'make dev' next."

dev: ## start full local stack (postgres + redis, migrations, all services)
	docker compose -f infrastructure/docker/compose.dev.yml up -d
	@echo "Waiting for Postgres..."
	@until docker compose -f infrastructure/docker/compose.dev.yml exec -T postgres pg_isready -U postgres -q; do sleep 1; done
	uv run alembic -c services/chat-api/alembic.ini upgrade head
	turbo run dev --parallel

test: ## run all tests (turbo for JS, pytest for Python)
	turbo run test
	uv run pytest tests/safety services packages -q

test-safety: ## run only the safety corpus (the hard gate)
	uv run pytest tests/safety -v

db-migrate: ## apply pending Alembic migrations
	uv run alembic -c services/chat-api/alembic.ini upgrade head

db-rollback: ## rollback the last Alembic migration
	uv run alembic -c services/chat-api/alembic.ini downgrade -1

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
