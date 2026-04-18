.PHONY: backend-install backend-dev backend-test db-upgrade db-downgrade frontend-install frontend-dev frontend-lint services-up services-down

backend-install:
	.venv/bin/python3 -m ensurepip --upgrade
	.venv/bin/pip install "./backend[dev]"

backend-dev:
	.venv/bin/uvicorn sec_copilot.main:app --app-dir backend/src --reload

backend-test:
	.venv/bin/pytest backend/tests

db-upgrade:
	cd backend && ../.venv/bin/alembic upgrade head

db-downgrade:
	cd backend && ../.venv/bin/alembic downgrade -1

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-lint:
	cd frontend && npm run lint

services-up:
	docker compose up -d postgres qdrant

services-down:
	docker compose down
