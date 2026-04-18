# SEC Filing Intelligence Copilot

A deployable RAG system for asking cited questions over public SEC filings. The project is designed to demonstrate production-minded AI engineering: ingestion, metadata-aware retrieval, structured fact grounding, evaluation, and a small web interface.

## Current Status

Milestones 1-5 are implemented locally: app scaffolding, persistence, SEC ingestion,
filing parsing, chunking, and LlamaIndex retrieval plumbing. Cited answer generation,
numeric grounding, evaluation, and the polished web demo are still planned work.

## Project Shape

- Backend: FastAPI
- Frontend: Next.js and React
- Metadata store: Postgres
- Vector store: Qdrant
- Retrieval orchestration: LlamaIndex
- Evaluation: FinanceBench-compatible benchmark flow plus a custom SEC filing eval set

## Why This Is Useful

The SEC corpus is the demo domain, but the architecture generalizes to any high-stakes document set where answers need retrieval, citations, structured metadata, and evaluation. Potential users include strategy teams, sales teams, legal and compliance teams, finance teams, consultants, researchers, journalists, students, and operators tracking public companies.

The product is a research assistant for public filings. It is not investment advice.

## Repository Layout

```text
backend/   FastAPI service
frontend/  Next.js app
docs/      Design specs and implementation plans
```

## Local Development

Copy the sample environment file before running services:

```bash
cp .env.example .env
```

Docker is optional. It is useful for running Postgres and Qdrant locally, but the public deployment can use managed services instead.

### Backend

```bash
python3 -m venv .venv
.venv/bin/python3 -m ensurepip --upgrade
.venv/bin/pip install "./backend[dev]"
.venv/bin/uvicorn sec_copilot.main:app --app-dir backend/src --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Database Migrations

The backend uses SQLAlchemy models and Alembic migrations. With `DATABASE_URL` pointed at a running Postgres database:

```bash
make db-upgrade
```

Milestone 2 tests use SQLite in memory, so the persistence layer can be verified without Docker.

### SEC Ingestion

After running migrations against a configured database, ingest one company by CIK:

```bash
.venv/bin/sec-copilot ingest-sec-company 320193 --limit 2
```

The command fetches SEC submissions, selected 10-K/10-Q filing documents, and company facts. Raw SEC artifacts are cached under `SEC_RAW_DATA_DIR`, which defaults to `data/raw/sec` and is intentionally ignored by git.

For the current local workflow, SQLite is enough:

```bash
mkdir -p data
DATABASE_URL=sqlite:///data/sec_copilot.db make db-upgrade
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot ingest-sec-company 320193 --limit 1
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot parse-sec-filing <ACCESSION_NUMBER>
```

Use an `accession_number` value from the ingestion command output. Parsing converts
a cached filing document into normalized filing sections and deterministic chunks.

### Retrieval

Milestone 5 adds LlamaIndex node construction and local retrieval over parsed chunks:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot retrieve-sec-filing \
  <ACCESSION_NUMBER> "supply chain regulatory risks" --section-type risk_factors
```

For Qdrant-backed indexing, use either a running Qdrant URL or local Qdrant storage path:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot index-sec-filing \
  <ACCESSION_NUMBER> --qdrant-path data/qdrant-local --collection sec_filings
```

The project currently uses deterministic local dense and sparse hash embeddings for
tests and offline smoke workflows. Production retrieval can swap in stronger
embedding and sparse retrieval models without changing the stored chunk schema.
Pass `--hybrid` to enable Qdrant hybrid indexing with the built-in sparse hashing
path, or `--fastembed-sparse-model` if you have FastEmbed installed and want to
use a named sparse model.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

### Local Data Services

If Docker is installed, run:

```bash
docker compose up -d postgres qdrant
```

Without Docker, use managed Postgres and Qdrant, then set `DATABASE_URL` and `QDRANT_URL` in `.env`.

## Planning Docs

- [Design spec](docs/superpowers/specs/2026-04-18-sec-filing-intelligence-copilot-design.md)
- [Implementation plan](docs/superpowers/plans/2026-04-18-sec-filing-intelligence-copilot-implementation-plan.md)

## Commit Standards

This repo is intended to be public. Commits should be focused, descriptive, and professional. Avoid committing secrets, local caches, raw SEC dumps, generated indexes, local databases, virtual environments, or dependency folders.
