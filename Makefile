.PHONY: setup lint typecheck test build compose-config compose-up compose-down migrate pilot-acceptance

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
	docker compose --env-file .env -f infra/compose/docker-compose.yaml up -d --build

compose-down:
	docker compose --env-file .env -f infra/compose/docker-compose.yaml down

migrate:
	docker compose --env-file .env -f infra/compose/docker-compose.yaml run --rm migrations

pilot-acceptance:
	uv run python scripts/pilot_acceptance.py
