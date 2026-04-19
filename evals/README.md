# Evaluation Harness

The benchmark runner compares SEC Copilot answer quality across local RAG, XBRL,
and OpenAI baseline variants:

- `closed_book`: no filing retrieval.
- `naive_rag`: retrieval over the whole filing without metadata filters.
- `improved_rag`: retrieval with section and metadata filters.
- `improved_rag_xbrl`: metadata-aware retrieval plus structured XBRL fact grounding.
- `improved_rag_xbrl_llm`: guarded LLM synthesis over the XBRL-grounded answer.
- `openai_closed_book`: configured OpenAI model without filing excerpts.
- `openai_retrieved_context`: configured OpenAI model with retrieved filing excerpts,
  but without XBRL fact grounding.
- `openai_web_search`: configured OpenAI model with web search enabled, but without
  local-corpus controls or XBRL fact grounding.

Run the default benchmark:

```bash
DATABASE_URL=sqlite:///data/sec_copilot.db .venv/bin/sec-copilot run-eval
```

The command writes JSON metrics and a Markdown report under `evals/results/`.

The checked-in seed set at `evals/questions/sec_seed.jsonl` is intentionally small and
fixture-aligned so tests can run offline. For a live benchmark, add JSONL rows whose
`accession_number`, expected citations, sections, and XBRL concepts match the filings
you ingested locally.

## Real Apple Benchmark

`evals/questions/aapl_real_2025_2026.jsonl` is a portfolio benchmark for locally
ingested Apple filings:

- FY2025 Form 10-K: `0000320193-25-000079`
- Q1 FY2026 Form 10-Q: `0000320193-26-000006`

Run it against a local database containing those filings:

```bash
PYTHONPATH=backend/src DATABASE_URL=sqlite:///data/sec_copilot_real.db \
  .venv/bin/python -m sec_copilot.cli run-eval \
  --dataset evals/questions/aapl_real_2025_2026.jsonl \
  --output evals/results/aapl_real_eval.json \
  --report evals/results/aapl_real_eval.md
```

The current tracked benchmark report is `reports/aapl_real_eval.md`. In the latest
local run, `improved_rag_xbrl` and `improved_rag_xbrl_llm` reached 100% accuracy,
100% numeric accuracy, 100% grounded numeric accuracy, 100% refusal accuracy, and
100% evidence recall across 24 real SEC questions. `openai_retrieved_context`
reached 41.7% accuracy and 58.3% numeric accuracy, but 0% grounded numeric
accuracy because it does not validate answers against structured XBRL facts.
The web-search baseline reached 62.5% accuracy and 75.0% numeric accuracy, but
still had 0% grounded numeric accuracy because web citations are not structured
XBRL validation.

## Real Microsoft Benchmark

`evals/questions/msft_real_2025_2026.jsonl` is a second-issuer portfolio benchmark
for locally ingested Microsoft filings:

- FY2025 Form 10-K: `0000950170-25-100235`
- Q2 FY2026 Form 10-Q: `0001193125-26-027207`

Run it against a local database containing those filings:

```bash
PYTHONPATH=backend/src DATABASE_URL=sqlite:///data/sec_copilot_real.db \
  .venv/bin/python -m sec_copilot.cli run-eval \
  --dataset evals/questions/msft_real_2025_2026.jsonl \
  --output evals/results/msft_real_eval.json \
  --report evals/results/msft_real_eval.md
```

The current tracked Microsoft report is `reports/msft_real_eval.md`. In the latest
local run, `improved_rag_xbrl` and `improved_rag_xbrl_llm` reached 100% accuracy,
100% numeric accuracy, 100% grounded numeric accuracy, 100% refusal accuracy, and
100% evidence recall across 24 real SEC questions. `openai_retrieved_context`
reached 33.3% accuracy and 41.7% numeric accuracy. The web-search baseline reached
20.8% accuracy and 16.7% numeric accuracy. Both OpenAI baselines had 0% grounded
numeric accuracy.

Across the Apple and Microsoft reports, the tracked benchmark now covers 48 real
questions across four filings and two issuers. The guarded LLM synthesis variant
averaged about 2.0 seconds per question across both issuers while preserving 100%
grounded numeric accuracy.

To include OpenAI baselines, add `OPENAI_API_KEY` to your local `.env` and pass the
OpenAI variants explicitly:

```bash
PYTHONPATH=backend/src DATABASE_URL=sqlite:///data/sec_copilot_real.db \
  .venv/bin/python -m sec_copilot.cli run-eval \
  --dataset evals/questions/aapl_real_2025_2026.jsonl \
  --variant closed_book \
  --variant naive_rag \
  --variant improved_rag \
  --variant improved_rag_xbrl \
  --variant improved_rag_xbrl_llm \
  --variant openai_closed_book \
  --variant openai_retrieved_context \
  --variant openai_web_search \
  --output evals/results/aapl_real_openai_eval.json \
  --report evals/results/aapl_real_openai_eval.md
```

OpenAI predictions are cached under `OPENAI_EVAL_CACHE_DIR`, which defaults to
`evals/results/cache/openai`. The cache key includes the model, output budget,
reasoning effort, context budget, question, and prompt. Use
`--refresh-openai-cache` when you intentionally want to spend API calls again.

By default, OpenAI eval baselines use `gpt-5-mini`. Override it with
`OPENAI_EVAL_MODEL` in `.env` or `--openai-model` on the CLI. GPT-5 mini runs
with `OPENAI_EVAL_REASONING_EFFORT=minimal` and
`OPENAI_EVAL_MAX_OUTPUT_TOKENS=800` by default so reasoning tokens do not crowd
out short benchmark answers.

The `improved_rag_xbrl_llm` variant uses the same `OPENAI_API_KEY` with
`OPENAI_SYNTHESIS_MODEL`, `OPENAI_SYNTHESIS_MAX_OUTPUT_TOKENS`,
`OPENAI_SYNTHESIS_REASONING_EFFORT`, and `OPENAI_SYNTHESIS_TIMEOUT_SECONDS`.
If no key is configured, the variant returns the deterministic XBRL-grounded
answer and records `missing_openai_api_key` as synthesis metadata.

The `openai_web_search` variant uses `OPENAI_EVAL_WEB_SEARCH_REASONING_EFFORT=low`
because GPT-5 web search does not support minimal reasoning. It also supports
`OPENAI_EVAL_WEB_SEARCH_CONTEXT_SIZE` and `OPENAI_EVAL_WEB_SEARCH_MAX_TOOL_CALLS`.

## JSONL Schema

Each line is one benchmark question:

```json
{
  "id": "sec_seed_numeric_revenue_001",
  "question": "How much revenue did Apple report in 2024?",
  "accession_number": "0000320193-24-000123",
  "question_type": "numeric",
  "section_type": "mda",
  "top_k": 5,
  "expected": {
    "supported": true,
    "answer_keywords": [],
    "citation_chunk_ids": [],
    "section_types": [],
    "xbrl_concepts": ["RevenueFromContractWithCustomerExcludingAssessedTax"],
    "numeric_value": "383,285,000,000",
    "numeric_unit": "USD"
  },
  "metadata": {
    "company": "AAPL",
    "source": "local_fixture"
  }
}
```

Expected fields can be sparse. Text questions usually use `answer_keywords`,
`citation_chunk_ids`, and `section_types`. Numeric questions usually use
`xbrl_concepts`, `numeric_value`, and `numeric_unit`. Unsupported questions should set
`supported` to `false` and can set `insufficient_reason`.
