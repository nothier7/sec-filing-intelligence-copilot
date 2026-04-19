# Render + Supabase Deployment

This project can run as a production-style three-service deployment:

- Backend API: Render Python web service.
- Database: Supabase Postgres.
- Frontend: Vercel Next.js app.

The backend already uses SQLAlchemy and Alembic, so Supabase works as a managed
Postgres target without changing the persistence layer.

## What You Need

Create or collect these values before deployment:

- Supabase Postgres connection string.
- Supabase database password.
- Render service URL, after the backend deploys.
- Vercel frontend URL, after the frontend deploys.
- OpenAI API key for guarded answer synthesis.
- SEC user agent string, preferably with your email or portfolio URL.

Do not commit any of those secrets to git.

## Supabase

1. Create a Supabase project.
2. Open the project dashboard and choose **Connect**.
3. Copy the **Session pooler** connection string for a persistent backend service.
4. Convert the scheme for SQLAlchemy:

```text
postgres://...        -> postgresql+psycopg://...
postgresql://...     -> postgresql+psycopg://...
```

Use the session pooler first. Supabase recommends session mode for persistent
backend services when IPv4 support is needed. Transaction mode is better for
short-lived serverless functions and can require prepared-statement workarounds.

Run migrations against Supabase from this repo:

```bash
DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
```

Then ingest and parse the demo filings. Ingestion stores filing metadata,
downloads source documents to the local cache, and stores XBRL facts in Supabase.
Parsing creates the filing sections and chunks that the deployed API retrieves.

```bash
PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli ingest-sec-company 320193 \
  --limit 4 --forms 10-K 10-Q

PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli ingest-sec-company 789019 \
  --limit 4 --forms 10-K 10-Q
```

Parse the filings used by the UI and tracked benchmarks:

```bash
PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli parse-sec-filing 0000320193-25-000079

PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli parse-sec-filing 0000320193-26-000006

PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli parse-sec-filing 0000950170-25-100235

PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli parse-sec-filing 0001193125-25-256321

PYTHONPATH=backend/src DATABASE_URL="postgresql+psycopg://..." \
  .venv/bin/python -m sec_copilot.cli parse-sec-filing 0001193125-26-027207
```

If you need exact control over which filings are available in the public demo,
run the benchmark after ingestion and verify the expected Apple/Microsoft
accession numbers exist in Supabase.

## Render Backend

Use the checked-in `render.yaml` blueprint, or create a Python web service
manually with these values:

```text
Build Command: pip install -e backend
Start Command: uvicorn sec_copilot.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Set these Render environment variables:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
OPENAI_API_KEY=...
OPENAI_SYNTHESIS_MODEL=gpt-5-mini
OPENAI_SYNTHESIS_MAX_OUTPUT_TOKENS=600
OPENAI_SYNTHESIS_REASONING_EFFORT=minimal
OPENAI_SYNTHESIS_TIMEOUT_SECONDS=60
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app,http://127.0.0.1:3000,http://localhost:3000
SEC_USER_AGENT=SEC Filing Intelligence Copilot your-email@example.com
```

After deployment, verify:

```bash
curl https://your-render-service.onrender.com/health
```

## Vercel Frontend

Deploy the `frontend/` directory as the Next.js project. Set:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
```

After the Vercel production URL exists, update Render's
`CORS_ALLOWED_ORIGINS` with that URL and redeploy/restart the backend.

## Public Demo Smoke Test

Run these checks before putting the link on a resume:

```bash
curl https://your-render-service.onrender.com/health
```

Then use the Vercel UI to ask:

```text
How much revenue did Apple report in 2025?
```

Expected behavior:

- The answer is supported.
- Citations render.
- XBRL grounding shows `416,161,000,000 USD`.
- Guarded LLM synthesis either succeeds or clearly falls back.

## Platform Notes

- Render's FastAPI guide uses `uvicorn ... --host 0.0.0.0 --port $PORT` for
  Python web services.
- Supabase's connection docs recommend session pooler connections for persistent
  app servers when IPv4 support is needed, and transaction pooler connections
  for serverless or edge workloads.
- Next.js exposes browser-readable environment variables only when they use the
  `NEXT_PUBLIC_` prefix, which is why the frontend uses
  `NEXT_PUBLIC_API_BASE_URL`.
