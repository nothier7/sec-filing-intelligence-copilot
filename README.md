# SEC Filing Intelligence Copilot

A deployable RAG system for asking cited questions over public SEC filings. The project is designed to demonstrate production-minded AI engineering: ingestion, metadata-aware retrieval, structured fact grounding, evaluation, and a small web interface.

## Current Status

The public portfolio demo is implemented and deployed end to end: SEC ingestion,
filing parsing, chunking, LlamaIndex retrieval, cited answer generation, XBRL
numeric grounding, guarded OpenAI answer synthesis, filing change detection,
benchmarking, and a Next.js web UI.

- Live app: https://sec-filing-intelligence-copilot-rag.vercel.app
- API health: https://sec-filing-intelligence-copilot.onrender.com/health

## Project Shape

- Backend: FastAPI
- Frontend: Next.js and React
- Database: Supabase Postgres in production, SQLite/Postgres for local workflows
- Retrieval orchestration: LlamaIndex with an in-memory vector index for the deployed demo
- Optional vector indexing: Qdrant support exists in the CLI, but Qdrant is not used by the live deployment
- LLM layer: OpenAI guarded synthesis over already-cited and XBRL-grounded answers
- Evaluation: deterministic benchmark harness plus OpenAI baseline comparisons

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

Docker is optional. It is useful for running local Postgres, but the public deployment uses managed Supabase Postgres.

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

Persistence tests use SQLite in memory, so the data layer can be verified without Docker.

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

The main retrieval path builds LlamaIndex nodes from parsed chunks and uses an
in-memory vector index for local and deployed demo queries:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot retrieve-sec-filing \
  <ACCESSION_NUMBER> "supply chain regulatory risks" --section-type risk_factors
```

The project also includes optional Qdrant indexing support for future persistent
vector-store experiments. This is not part of the current public deployment. To
try it locally, use either a running Qdrant URL or a local Qdrant storage path:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot index-sec-filing \
  <ACCESSION_NUMBER> --qdrant-path data/qdrant-local --collection sec_filings
```

The project currently uses deterministic local dense and sparse hash embeddings
for tests, offline smoke workflows, and the public demo retrieval path. A later
upgrade can replace this with persistent Qdrant retrieval and stronger embedding
models without changing the stored chunk schema. Pass `--hybrid` to enable Qdrant
hybrid indexing with the built-in sparse hashing path, or
`--fastembed-sparse-model` if you have FastEmbed installed and want to use a
named sparse model.

### Cited Answers

After a filing is parsed, ask an evidence-constrained question from the CLI:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot ask-sec-filing \
  <ACCESSION_NUMBER> "What supply chain regulatory risks are described?" \
  --section-type risk_factors
```

Or call the API:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "accession_number": "<ACCESSION_NUMBER>",
    "question": "What supply chain regulatory risks are described?",
    "section_type": "risk_factors"
  }'
```

The deterministic answer generator only answers from retrieved chunks, returns
citation snippets, and uses structured XBRL facts when numeric grounding is
available. It uses insufficient-evidence responses for unsupported prompts, weak
retrieval, missing structured numeric facts, and mismatches between retrieved
numeric text and structured facts. Guarded LLM mode can then polish supported
answers with OpenAI while preserving exact numeric values, citations, refusal
behavior, and XBRL grounding.

Numeric answers include a `numeric_grounding` array with validation status:

- `validated`: a matching XBRL fact was found and used in the answer.
- `unavailable`: the system recognized the metric but could not find a structured fact.
- `mismatched`: retrieved numeric text conflicts with the structured fact.

### Filing Change Detection

Compare a section against the previous filing for the same company and form type:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot compare-sec-filing \
  <ACCESSION_NUMBER> --section-type risk_factors
```

Or call the API:

```bash
curl -X POST http://127.0.0.1:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "accession_number": "<ACCESSION_NUMBER>",
    "section_type": "risk_factors"
  }'
```

The response includes added claims, removed claims, an unchanged claim count, and
citations from both the current and prior filings when comparable evidence exists.
If a prior filing or comparable section is missing, the response is marked
unsupported with an explicit reason.

### Evaluation

Run the local benchmark from one command:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot run-eval
```

The runner compares closed-book, naive RAG, metadata-aware RAG, and metadata-aware
RAG plus XBRL grounding. It writes JSON metrics and a Markdown report under
`evals/results/`, including an ablation table, retrieval/evidence recall,
numeric accuracy, refusal accuracy, latency, and failure examples.

To evaluate the guarded LLM synthesis layer, pass `--variant improved_rag_xbrl_llm`.
That variant rewrites only already-supported XBRL-grounded answers and falls back
to the deterministic cited answer when the OpenAI key is missing or validation
fails.

The checked-in seed set is intentionally small and fixture-aligned so the harness
can be tested offline. For live portfolio demos, create or extend JSONL benchmark
rows that point at filings you ingested locally, then run:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot run-eval \
  --dataset evals/questions/sec_seed.jsonl
```

The tracked real-filing benchmarks cover 48 questions across Apple and Microsoft
filings. Apple uses the FY2025 10-K and Q1 FY2026 10-Q. Microsoft uses the
FY2025 10-K and Q2 FY2026 10-Q.

Across both issuers, `improved_rag_xbrl` and `improved_rag_xbrl_llm` reached
100% accuracy, 100% numeric accuracy, 100% grounded numeric accuracy, 100%
refusal accuracy, and 100% evidence recall. The guarded LLM variant averaged
about 2.0 seconds per question while preserving the deterministic XBRL checks.
The OpenAI retrieved-context baseline averaged 37.5% accuracy and 50.0% numeric
accuracy. The OpenAI web-search baseline averaged 41.7% accuracy and 45.8%
numeric accuracy. Both OpenAI baselines had 0% grounded numeric accuracy because
they do not validate answers against XBRL.

See [reports/aapl_real_eval.md](reports/aapl_real_eval.md),
[reports/msft_real_eval.md](reports/msft_real_eval.md), and
[evals/README.md](evals/README.md) for the tracked reports and benchmark schema.

### Deployment

The recommended public demo setup is a Vercel frontend, Render FastAPI backend,
and Supabase Postgres database. See
[docs/deployment-render-supabase.md](docs/deployment-render-supabase.md) for the
environment variables, migration commands, seed commands, and smoke tests.

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
docker compose up -d postgres
```

Without Docker, use managed Postgres and set `DATABASE_URL` in `.env`. Set
`QDRANT_URL` only if you are experimenting with the optional Qdrant indexing path.
For local Qdrant experiments, start it separately:

```bash
docker compose up -d qdrant
```

## Planning Docs

- [Design spec](docs/superpowers/specs/2026-04-18-sec-filing-intelligence-copilot-design.md)
- [Implementation plan](docs/superpowers/plans/2026-04-18-sec-filing-intelligence-copilot-implementation-plan.md)

## Commit Standards

This repo is intended to be public. Commits should be focused, descriptive, and professional. Avoid committing secrets, local caches, raw SEC dumps, generated indexes, local databases, virtual environments, or dependency folders.
