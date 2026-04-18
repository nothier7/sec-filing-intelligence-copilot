# SEC Filing Intelligence Copilot Implementation Plan

Date: 2026-04-18
Spec: `docs/superpowers/specs/2026-04-18-sec-filing-intelligence-copilot-design.md`

## Execution Principles

- Keep the project demoable after each major milestone.
- Keep commits focused and professional.
- Prefer working vertical slices over large unfinished layers.
- Build evaluation early enough that retrieval decisions can be measured.
- Use Docker Compose as a local convenience for Postgres and Qdrant, not as a hard deployment requirement.
- Keep raw SEC downloads, generated indexes, local databases, credentials, and benchmark artifacts out of git unless explicitly curated as small fixtures or reports.

## Milestone 1: Repository And App Foundation

Goal: create the basic project structure, local development workflow, and documentation skeleton.

Tasks:

- Add `.gitignore`, `.env.example`, and top-level `README.md`.
- Create backend package with FastAPI health endpoint.
- Create frontend app skeleton with Next.js/React.
- Add local service configuration for Postgres and Qdrant.
- Add simple scripts or make targets for common development commands.
- Add initial architecture notes to the README.

Expected commit sequence:

- `Add project documentation skeleton`
- `Add FastAPI backend scaffold`
- `Add frontend app scaffold`
- `Add local service configuration`

Acceptance criteria:

- Backend health endpoint runs locally.
- Frontend loads locally.
- README explains local setup options with and without Docker.
- No secrets, generated databases, raw data, or dependency folders are tracked.

## Milestone 2: Data Model And Persistence

Goal: establish the relational schema and persistence interfaces before building ingestion.

Tasks:

- Add Postgres connection settings.
- Add migration tooling.
- Create tables for companies, filings, filing sections, chunks, XBRL facts, questions, and eval runs.
- Add repository/service interfaces for companies, filings, chunks, facts, and eval runs.
- Add tests for schema assumptions and basic persistence.

Expected commit sequence:

- `Add database configuration`
- `Add filing metadata schema`
- `Add XBRL fact schema`
- `Add persistence tests`

Acceptance criteria:

- Migrations can create a clean database.
- Basic insert/read tests pass for core entities.
- Schema fields support metadata needed by retrieval, citations, grounding, and benchmarks.

## Milestone 3: SEC Ingestion

Goal: ingest public SEC data reproducibly for a small MVP company set.

Tasks:

- Implement SEC client with declared User-Agent, retries, throttling, and caching.
- Fetch company submissions by CIK.
- Fetch recent 10-K and 10-Q filing documents.
- Fetch company facts from SEC XBRL APIs.
- Store raw artifacts outside git.
- Normalize company, filing, and XBRL records into Postgres.
- Add cached fixtures for one small test company or one trimmed filing sample.

Expected commit sequence:

- `Add SEC API client`
- `Implement company submissions ingestion`
- `Implement filing document ingestion`
- `Implement XBRL facts ingestion`
- `Add ingestion tests with fixtures`

Acceptance criteria:

- A command can ingest one selected company.
- Re-running ingestion is idempotent.
- SEC request behavior is rate-limited and identifies the app.
- Tests do not depend on live SEC network calls.

## Milestone 4: Filing Parsing And Chunking

Goal: convert filing documents into section-aware chunks with stable citation metadata.

Tasks:

- Parse filing HTML/text into clean text.
- Identify major 10-K and 10-Q sections.
- Normalize section names.
- Chunk within section boundaries.
- Preserve source metadata for citations.
- Generate deterministic chunk IDs.
- Store sections and chunks in Postgres.

Expected commit sequence:

- `Add filing text parser`
- `Implement section normalization`
- `Implement section-aware chunking`
- `Persist filing sections and chunks`
- `Add parser and chunking tests`

Acceptance criteria:

- At least one 10-K and one 10-Q are parsed into useful sections.
- Chunks do not cross major section boundaries.
- Chunk IDs are stable across repeated parses.
- Citations can reference filing, section, and source URL.

## Milestone 5: LlamaIndex Retrieval Pipeline

Goal: build measurable retrieval variants using LlamaIndex and Qdrant.

Tasks:

- Convert stored chunks into LlamaIndex nodes.
- Index nodes into Qdrant.
- Implement naive dense retrieval baseline.
- Implement improved retrieval with metadata filters.
- Add hybrid retrieval support.
- Add reranking.
- Expose retrieval results through backend services.

Expected commit sequence:

- `Add LlamaIndex node builder`
- `Index filing chunks in Qdrant`
- `Add naive dense retriever`
- `Add metadata-filtered hybrid retriever`
- `Add retrieval reranking`

Acceptance criteria:

- Retrieval works for a selected company and filing.
- Retrieval results include chunk IDs, scores, section names, and source metadata.
- Naive and improved retrievers can both be invoked for benchmarks.

## Milestone 6: Cited Answer Generation

Goal: answer user questions using retrieved evidence and source citations.

Tasks:

- Add `/ask` request and response models.
- Classify query type at a simple level: text, numeric, comparison, or unsupported.
- Retrieve relevant chunks with selected retriever.
- Generate answers constrained to retrieved evidence.
- Return citations and source snippets.
- Add insufficient-evidence behavior.
- Add tests for response shape and citation serialization.

Expected commit sequence:

- `Add question answering API models`
- `Implement cited answer service`
- `Add insufficient-evidence handling`
- `Add answer service tests`

Acceptance criteria:

- Users can ask questions over selected filings.
- Every substantive answer includes citations.
- Unsupported or weakly supported questions avoid confident unsupported claims.

## Milestone 7: XBRL Numeric Grounding

Goal: make numeric answers more reliable by validating them against structured SEC facts.

Tasks:

- Add fact lookup helpers for common financial metrics.
- Map common user language to XBRL concepts where practical.
- Detect when a question needs numeric grounding.
- Query facts by company, fiscal period, form, and concept.
- Attach fact validation results to answer responses.
- Add UI/API fields for validated, mismatched, or unavailable numeric grounding.

Expected commit sequence:

- `Add XBRL fact lookup helpers`
- `Map common financial metrics to XBRL concepts`
- `Add numeric grounding to answer service`
- `Add numeric grounding tests`

Acceptance criteria:

- Common metric questions can return exact facts with units and periods.
- Numeric claims are marked validated, unavailable, or mismatched.
- The system does not hide missing structured facts.

## Milestone 8: Filing Change Detection

Goal: compare comparable sections across filing periods and generate cited summaries.

Tasks:

- Match sections between current and previous filings.
- Compute text-level and claim-level differences.
- Retrieve supporting chunks from both filings.
- Generate concise cited change summaries.
- Add `/compare` endpoint.
- Add tests with controlled fixture sections.

Expected commit sequence:

- `Add filing section matching`
- `Implement filing change detection`
- `Add cited change summary endpoint`
- `Add change detection tests`

Acceptance criteria:

- Users can compare Risk Factors or MD&A across two filings.
- Summaries cite both current and prior filing evidence.
- The system handles missing comparable sections gracefully.

## Milestone 9: Evaluation Harness

Goal: prove the system improves over closed-book and naive-RAG baselines.

Tasks:

- Add benchmark question schema and JSONL format.
- Add a small custom SEC eval seed set.
- Add FinanceBench mapping support for examples whose documents are available locally.
- Implement benchmark runner for closed-book, naive RAG, improved RAG, and improved RAG plus XBRL variants.
- Add retrieval metrics using LlamaIndex eval utilities.
- Add RAG metrics with RAGAS and/or RAGChecker.
- Add latency and token/cost tracking.
- Generate Markdown evaluation report.

Expected commit sequence:

- `Add benchmark question schema`
- `Add SEC evaluation seed set`
- `Add benchmark runner`
- `Add retrieval metrics`
- `Add RAG quality metrics`
- `Generate evaluation report`

Acceptance criteria:

- Benchmarks can run from one command.
- Results compare all planned system variants.
- Report includes metrics, ablation table, and failure examples.
- README summarizes the headline evaluation results.

## Milestone 10: Web Demo

Goal: expose the system through a simple professional UI.

Tasks:

- Build company and filing selectors.
- Build question input and answer panel.
- Render citations and source snippets.
- Render numeric grounding status.
- Add compare-with-previous-filing action.
- Add evaluation summary section or link to report.
- Add responsive styling suitable for a public portfolio demo.

Expected commit sequence:

- `Add company and filing selectors`
- `Add cited answer interface`
- `Add numeric grounding display`
- `Add filing comparison interface`
- `Add evaluation summary view`
- `Polish web demo styling`

Acceptance criteria:

- A reviewer can understand and try the core workflow in under one minute.
- The UI does not obscure citations or grounding status.
- The UI works against a preloaded demo corpus.

## Milestone 11: Deployment And Public Polish

Goal: make the project public, reproducible, and useful for interviews.

Tasks:

- Prepare deployment configuration for frontend and API.
- Configure managed Postgres and Qdrant for demo environment.
- Preload selected filings and indexes.
- Add production environment documentation.
- Add screenshots or short demo GIF/video if practical.
- Finalize README with architecture, setup, eval results, tradeoffs, and resume bullets.
- Verify git history and author metadata.

Expected commit sequence:

- `Add deployment configuration`
- `Document demo deployment`
- `Add evaluation results to README`
- `Add project screenshots`
- `Finalize public portfolio documentation`

Acceptance criteria:

- Public demo runs against preloaded data.
- README is useful to recruiters and engineers.
- Commit history is clean and coherent.
- No secrets, raw data dumps, local caches, or generated indexes are committed.

## Suggested MVP Company Set

Start with a small set that creates useful variety without increasing scope too much:

- Apple
- Microsoft
- NVIDIA
- Amazon
- Tesla

These companies are familiar, widely discussed, and have filings that support questions about business segments, risks, revenue drivers, margins, capital spending, and operations.

## First Implementation Slice

The first slice should be:

1. Backend health endpoint.
2. Postgres and Qdrant local setup.
3. SEC client.
4. Ingest one company submission and one 10-K.
5. Parse and chunk that filing.
6. Index chunks.
7. Ask one cited question through the API.

This creates an end-to-end vertical path early. After that, each milestone improves quality, grounding, evaluation, and demo polish.

