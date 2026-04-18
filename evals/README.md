# Evaluation Harness

The benchmark runner compares SEC Copilot answer quality across four variants:

- `closed_book`: no filing retrieval.
- `naive_rag`: retrieval over the whole filing without metadata filters.
- `improved_rag`: retrieval with section and metadata filters.
- `improved_rag_xbrl`: metadata-aware retrieval plus structured XBRL fact grounding.

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
local run, `improved_rag_xbrl` reached 100% accuracy, 100% numeric accuracy, 100%
refusal accuracy, and 100% evidence recall across 24 real SEC questions.

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
