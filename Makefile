.PHONY: setup lint typecheck test build compose-config compose-up compose-down compose-ps migrate pilot-acceptance pilot-recovery pilot-semantic-acceptance live-demo live-demo-smoke live-demo-check

setup:
	uv sync --all-packages --group dev
	pnpm install --frozen-lockfile

lint:
	uv run ruff check .
	pnpm lint

typecheck:
	uv run mypy apps/api/src packages/contracts/src packages/sdk-python/src services/stream-worker/src
	pnpm typecheck

test:
	uv run pytest
	pnpm test

build:
	uv build --all-packages
	pnpm build

compose-config:
	docker compose --env-file .env.example -f infra/compose/docker-compose.yaml config --quiet

compose-up:
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example — edit secrets before production use")
	docker compose --env-file .env -f infra/compose/docker-compose.yaml up -d --build

compose-down:
	@test -f .env || cp .env.example .env
	docker compose --env-file .env -f infra/compose/docker-compose.yaml down

compose-ps:
	@test -f .env || cp .env.example .env
	docker compose --env-file .env -f infra/compose/docker-compose.yaml ps -a

migrate:
	@test -f .env || cp .env.example .env
	docker compose --env-file .env -f infra/compose/docker-compose.yaml run --rm migrations

pilot-acceptance:
	uv run python scripts/pilot_acceptance.py

pilot-recovery:
	uv run python scripts/pilot_recovery.py

pilot-semantic-acceptance:
	@test -f .env || (echo "Missing .env — copy from .env.example and set OPENAI_API_KEY" && exit 1)
	@set -a; . ./.env; set +a; \
	if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "OPENAI_API_KEY is empty in .env"; \
		exit 1; \
	fi; \
	uv run python scripts/semantic_acceptance.py

live-demo:
	uv run python scripts/live_demo.py --mode full

live-demo-smoke:
	uv run python scripts/live_demo.py --mode structural

live-demo-check:
	uv run python scripts/live_demo.py --mode check --skip-compose
