# SEC Filing Intelligence Copilot Design

Date: 2026-04-18
Status: Draft for user review

## Purpose

Build a deployable SEC Filing Intelligence Copilot that demonstrates production-minded AI engineering over public company filings. The project should read like a broad AI engineering system, not a narrow investment app: ingestion pipelines, source-aware retrieval, structured fact grounding, evaluation, deployment, and a usable interface.

The core workflow is simple: a user selects a company and asks questions about recent 10-K or 10-Q filings. The system retrieves relevant filing passages, answers with citations, validates numeric claims against SEC XBRL facts where possible, and can summarize meaningful changes between filings.

## Resume Positioning

Primary resume message:

> Built a deployable RAG system over SEC filings using LlamaIndex, hybrid retrieval, metadata-aware chunking, cited answer generation, XBRL-backed numeric validation, and offline benchmark evaluation against closed-book and naive-RAG baselines.

The project should showcase transferable AI engineering skills:

- Public-source ingestion with rate limits and reproducibility.
- Structured and unstructured data modeling.
- Hybrid retrieval with metadata filters and reranking.
- Grounded answer generation with citations.
- Numeric validation with structured facts.
- Evaluation harnesses, ablations, failure analysis, and benchmark reporting.
- API-first deployment with a small web UI.

## Target Users

Primary users are recruiters, hiring managers, and interviewers evaluating the project. The product experience should be understandable in under one minute.

Functional users are analysts, founders, operators, or students who want to understand public company filings without reading long reports manually.

## Industry Value

The project is useful anywhere teams need fast, cited answers over long public filings and source documents. It should be framed as a document intelligence and research workflow, not as a stock-picking tool.

Potential industry users:

- Startup founders and operators tracking competitors, public customers, suppliers, or acquisition targets.
- Product and strategy teams monitoring public company risks, revenue drivers, market language, and business changes.
- Sales and account teams preparing for enterprise customer conversations using public filings.
- Finance and investor-relations teams summarizing filings and checking public statements against disclosed facts.
- Legal, compliance, and audit teams reviewing risk factors, litigation disclosures, controls language, and changes across reporting periods.
- Consulting and market research teams producing first-pass company briefs with traceable evidence.
- Journalists, students, and educators who need accessible explanations of public company filings with citations.

The transferable value is broader than SEC filings: the same architecture applies to regulatory filings, contracts, grant solicitations, audit evidence, clinical labels, policy documents, and other high-stakes corpora where answers need retrieval, citations, structured metadata, and evaluation.

## Non-Goals

- Do not provide investment advice, stock recommendations, price predictions, or portfolio guidance.
- Do not attempt full SEC coverage in the MVP.
- Do not build a complex financial terminal.
- Do not make the frontend the main project.
- Do not rely on an LLM alone for numeric claims that can be checked against structured facts.

## MVP Scope

The MVP covers:

- 5 to 10 public companies.
- 10-K and 10-Q filings.
- Company, filing, section, chunk, citation, and XBRL fact metadata.
- Cited Q&A over selected filings.
- "What changed since the previous filing?" summaries for comparable sections.
- Numeric grounding for common financial metrics when XBRL facts are available.
- Benchmarking against closed-book LLM, naive dense RAG, improved RAG, and improved RAG plus XBRL grounding.
- Deployable backend and a simple browser UI.

## Architecture

The system has five main layers:

1. Ingestion layer
   - Fetch SEC submissions JSON, filing documents, and company facts.
   - Respect SEC fair-access expectations with a declared User-Agent, request throttling, retries, caching, and resumable jobs.
   - Store raw downloaded artifacts for reproducibility.

2. Normalization layer
   - Parse filings into structured sections such as Business, Risk Factors, MD&A, Financial Statements, Notes, Legal Proceedings, and Controls.
   - Extract tables and preserve document hierarchy where practical.
   - Normalize filing metadata and XBRL facts into relational tables.
   - Create LlamaIndex nodes with stable IDs and rich metadata.

3. Retrieval layer
   - Use LlamaIndex as the retrieval orchestration layer.
   - Store dense and sparse/hybrid searchable chunks in Qdrant.
   - Store filing metadata, company metadata, and XBRL facts in Postgres.
   - Apply metadata filters before retrieval where possible: company, CIK, form type, filing date, fiscal year, fiscal quarter, accession number, and section.
   - Use reranking for final context selection.

4. Answering and grounding layer
   - Generate answers only from retrieved evidence.
   - Return citations tied to filing, section, chunk, and source URL.
   - Detect questions that need numeric facts and query the XBRL fact store.
   - Validate generated numeric claims against structured facts where possible.
   - Refuse or ask for narrower scope when evidence is insufficient.

5. Application and evaluation layer
   - FastAPI exposes ingestion status, company search, filing search, question answering, change summaries, citations, and benchmark results.
   - A small Next.js/React web UI lets users select a company, ask questions, inspect citations, view numeric checks, and run a change summary.
   - Evaluation scripts run benchmark variants and output JSON plus Markdown reports.

## Main Components

### Ingestion Jobs

Responsibilities:

- Fetch company submissions from SEC EDGAR public data.
- Fetch filing HTML or text for selected 10-K and 10-Q filings.
- Fetch company facts from SEC XBRL APIs.
- Persist raw artifacts and normalized database records.
- Track job status, source URLs, timestamps, and errors.

Key design choices:

- Ingestion must be idempotent.
- Raw artifacts should be cached before parsing.
- Downloaded documents should be keyed by CIK, accession number, and source URL.
- SEC requests should be throttled below SEC fair-access limits.

### Filing Parser

Responsibilities:

- Convert filings into clean text sections.
- Preserve section names, hierarchy, and document order.
- Create chunks that avoid crossing major filing sections.
- Attach metadata needed for filtering, citations, and evals.

Chunking strategy:

- Prefer section-aware chunking over fixed-size chunking.
- Use smaller chunks for dense retrieval and include neighboring context during answer synthesis when useful.
- Keep tables as structured text with section and table metadata.
- Assign deterministic chunk IDs so benchmark labels remain stable.

### XBRL Fact Store

Responsibilities:

- Store company facts such as revenue, net income, operating income, assets, liabilities, cash flow items, and share counts.
- Preserve taxonomy concept, unit, fiscal period, form, filing date, frame, accession number, and value.
- Support queries such as "revenue for Apple FY2024" or "net income change from prior year."

The fact store is not meant to replace filing retrieval. It exists to validate numeric answers and provide exact values when available.

### LlamaIndex Retrieval Pipeline

Responsibilities:

- Convert parsed chunks into LlamaIndex nodes.
- Build retrievers over Qdrant hybrid search.
- Apply metadata filters derived from user selection and query intent.
- Rerank retrieved chunks before answer generation.
- Expose retrieval results for both the app and evaluation harness.

Baseline retrievers:

- Closed-book LLM: no retrieval.
- Naive RAG: dense retrieval over generic chunks.
- Improved RAG: section-aware chunks, metadata filters, hybrid retrieval, and reranking.
- Improved RAG plus XBRL: improved RAG with structured numeric validation.

### Answer Service

Responsibilities:

- Classify whether the question is a filing-text question, numeric fact question, comparison question, or unsupported question.
- Retrieve relevant context.
- Query XBRL facts when numeric grounding is needed.
- Generate a concise answer with citations.
- Return supporting snippets, confidence signals, and numeric validation results.

Answer rules:

- Every substantive answer must include citations.
- Numeric values should include units and period.
- If retrieved evidence is insufficient, the answer should say so.
- Generated text should not offer investment advice.

### Change Detection Service

Responsibilities:

- Compare a selected filing section against the same or closest matching section in the previous filing.
- Highlight added, removed, or materially changed claims.
- Generate a cited change summary.

MVP focus:

- Risk Factors.
- MD&A.
- Liquidity and Capital Resources.
- Legal Proceedings if present.

### Web UI

Responsibilities:

- Make the system easy to demo.
- Show company and filing selectors.
- Provide a question box.
- Show answer, citations, source snippets, and numeric checks.
- Provide a "compare with previous filing" action.
- Show benchmark summary charts or link to the evaluation report.

The UI should be clean and functional. The core value is the retrieval, grounding, and evaluation pipeline.

## Data Model

Core relational tables:

- `companies`: CIK, ticker, name, exchange, SIC, fiscal year end.
- `filings`: accession number, CIK, form type, filing date, report date, fiscal year, fiscal quarter, source URL, local raw artifact path.
- `filing_sections`: filing ID, section name, normalized section type, order, text hash.
- `chunks`: chunk ID, filing ID, section ID, text, token count, metadata JSON, source offsets when available.
- `xbrl_facts`: CIK, accession number, concept, label, unit, value, fiscal period, fiscal year, fiscal quarter, form type, filed date, frame.
- `questions`: benchmark question, type, expected answer, expected evidence, expected facts.
- `eval_runs`: run ID, system variant, timestamp, model config, retriever config, metrics, output paths.

Qdrant stores chunk embeddings, sparse vectors or hybrid-search payloads, and metadata needed for filtering.

## API Surface

Representative endpoints:

- `GET /health`
- `GET /companies`
- `GET /companies/{cik}/filings`
- `POST /ingest/company`
- `GET /ingest/jobs/{job_id}`
- `POST /ask`
- `POST /compare`
- `GET /citations/{chunk_id}`
- `POST /evals/run`
- `GET /evals/runs`
- `GET /evals/runs/{run_id}`

The public demo can disable expensive ingestion and benchmark execution endpoints while still showing precomputed data and results.

## Evaluation Strategy

Evaluation is a first-class deliverable.

### Benchmark Sets

1. FinanceBench open-source sample
   - Use as an external benchmark for financial QA over public filings and related financial documents.
   - Use only examples whose documents are included or can be mapped cleanly to the local corpus.

2. Custom SEC Filing Eval Set
   - 60 to 100 questions across the selected MVP companies.
   - Include direct lookup, numeric fact, section-specific, cross-period comparison, and unsupported questions.
   - Store expected answers, expected source filings, expected sections or chunks, and expected XBRL concepts where relevant.

### System Variants

Run each benchmark against:

- Closed-book LLM.
- Naive dense RAG.
- Improved RAG with section-aware chunking, metadata filters, hybrid retrieval, and reranking.
- Improved RAG plus XBRL numeric grounding.

### Metrics

Retrieval metrics:

- Recall@k.
- Hit rate.
- MRR.
- nDCG.
- Context precision.
- Evidence recall.

Answer metrics:

- Exact or normalized correctness for numeric facts.
- LLM-graded correctness for narrative answers.
- Faithfulness or groundedness.
- Citation precision.
- Refusal accuracy for unsupported questions.
- Numeric consistency against XBRL facts.

System metrics:

- End-to-end latency.
- Retrieval latency.
- Answer generation latency.
- Token usage.
- Estimated cost per answer.

### Tooling

- LlamaIndex evals for retrieval metrics and retriever comparisons.
- RAGAS for RAG metrics such as context precision, context recall, faithfulness, response relevancy, and noise sensitivity.
- RAGChecker for claim-level diagnosis of retriever and generator behavior.
- DeepEval or pytest-style checks for regression tests in CI.
- Optional TruLens for observability and visual inspection of context relevance, groundedness, and answer relevance.

### Evaluation Report

The repo should include a generated evaluation report with:

- Benchmark setup.
- Dataset summary.
- Model and retriever configs.
- Results table by system variant.
- Ablation chart.
- Latency and cost table.
- Failure analysis with examples.
- Clear explanation of how the final pipeline improves over closed-book and naive-RAG baselines.

## Deployment

The deployable version should use:

- FastAPI backend.
- Next.js/React frontend.
- Postgres database.
- Qdrant vector database.
- Docker Compose for local development reproducibility when available.

Docker is not essential for public deployability. The app can be deployed with managed services: the frontend on Vercel, the API on Render/Fly.io/Railway, Postgres through a managed provider, and Qdrant through Qdrant Cloud or another hosted service. Docker Compose is still valuable because it gives reviewers and future contributors a one-command way to run the multi-service stack locally.

Initial public deployment target:

- Deploy the frontend to Vercel.
- Deploy the API to Render, Fly.io, or Railway.
- Use managed Postgres through Neon, Supabase, or the API host.
- Use Qdrant Cloud or a managed/self-hosted Qdrant service.
- Preload a small fixed corpus to avoid requiring live SEC ingestion during demos.
- Keep API keys and model credentials out of the repo.

The public demo should include a disclaimer that it is a research assistant for public filings and not investment advice.

## Error Handling

Expected failure modes and responses:

- SEC download failures: retry with backoff, preserve failed job state, allow resume.
- Rate limiting: throttle requests and avoid concurrent bursts.
- Parser failures: preserve raw artifact and mark filing as partially parsed.
- Missing XBRL facts: answer from filing text if available and mark numeric validation as unavailable.
- Weak retrieval: return insufficient-evidence response rather than unsupported claims.
- Model failures: return a structured error and log model, prompt, and request metadata without exposing secrets.
- Eval failures: save partial results and report failed examples separately.

## Testing

Unit tests:

- SEC URL and identifier normalization.
- Filing metadata parsing.
- Section normalization.
- Chunk ID determinism.
- XBRL fact query helpers.
- Citation serialization.

Integration tests:

- Ingest one known company filing from cached fixtures.
- Build retriever index from fixture chunks.
- Ask a known question and verify cited source IDs.
- Validate a known numeric answer against stored XBRL facts.

Evaluation tests:

- Run a small smoke benchmark in CI.
- Fail CI if core metrics regress below configured thresholds after the baseline is established.
- Store full benchmark outputs as artifacts when run locally or in release workflows.

## Security and Compliance

- Public corpus only for the initial project.
- No private company data, private financial data, or user portfolios.
- No investment advice.
- Secrets stored in environment variables.
- Public demo uses preloaded filings and avoids exposing ingestion controls unless protected.
- Logs should avoid storing full API keys or sensitive environment values.

## Repository Standards

The public repository should read professionally.

- Use focused commits with descriptive imperative messages, such as `Add SEC ingestion client`, `Implement section-aware chunking`, or `Add RAG benchmark runner`.
- Keep generated artifacts, local caches, raw downloaded filings, credentials, virtual environments, and database files out of git.
- Commit design, implementation, tests, benchmark scripts, documentation, and selected small fixtures intentionally.
- Avoid large "misc cleanup" commits.
- Keep README updates close to the feature or milestone they explain.
- Before publishing, verify author name and email, remove local-only paths from docs, and ensure the default branch history tells a coherent project story.

## Milestones

1. Project foundation
   - Repo setup, optional Docker Compose, FastAPI skeleton, Postgres, Qdrant, web app skeleton.

2. SEC ingestion
   - Company lookup, submissions download, filing download, company facts download, raw cache, normalized metadata.

3. Parsing and indexing
   - Section parser, chunking, LlamaIndex node creation, Qdrant indexing, Postgres metadata records.

4. Cited Q&A
   - Question endpoint, metadata filters, hybrid retrieval, reranking, answer generation, citations.

5. XBRL grounding
   - Fact queries, numeric validation, fact panel in API/UI, unsupported/missing fact behavior.

6. Change detection
   - Section matching across filings, diff generation, cited change summaries.

7. Evaluation harness
   - FinanceBench mapping, custom SEC eval set, benchmark runner, metric calculation, report generation.

8. Deployment polish
   - Demo corpus, local run instructions, hosted deployment, README, screenshots, evaluation report, resume bullets.

## Acceptance Criteria

The project is ready to showcase when:

- A reviewer can run or visit the app and ask filing questions with cited answers.
- The app can compare at least one section across two filings for a selected company.
- Numeric answers for common financial facts are validated or explicitly marked as unvalidated.
- The repo includes a benchmark report comparing closed-book, naive-RAG, improved-RAG, and improved-RAG plus XBRL variants.
- The README explains architecture, setup, evaluation results, failure modes, and resume-relevant engineering decisions.
- The deployed demo works against a preloaded corpus without requiring live ingestion.
