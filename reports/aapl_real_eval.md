# Apple SEC Filing Evaluation Report

Generated on 2026-04-18 from `evals/questions/aapl_real_2025_2026.jsonl`.

This benchmark uses locally ingested Apple SEC filings:

- Apple FY2025 Form 10-K: `0000320193-25-000079`
- Apple Q1 FY2026 Form 10-Q: `0000320193-26-000006`

The dataset contains 24 questions:

- 12 numeric questions with expected XBRL concepts and values.
- 8 disclosure or comparison questions with expected citation chunks.
- 4 refusal questions for investment advice, forecasts, ambiguous metrics, or unavailable periods.

## Headline Metrics

| Variant | Accuracy | Numeric Accuracy | Refusal Accuracy | Evidence Recall | Avg Latency (ms) | Error Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| closed book | 8.3% | 0.0% | 50.0% | 16.7% | 0.0 | 0.0% |
| naive rag | 25.0% | 0.0% | 50.0% | 83.3% | 46.7 | 0.0% |
| improved rag | 45.8% | 0.0% | 75.0% | 100.0% | 41.5 | 0.0% |
| improved rag xbrl | 100.0% | 100.0% | 100.0% | 100.0% | 44.6 | 0.0% |

## What The Ablation Shows

`closed_book` intentionally has no filing context. It behaves like a generic assistant that refuses most evidence-dependent questions.

`naive_rag` retrieves filing chunks but does not use metadata filters or structured SEC facts. It can often find relevant snippets, but numeric answers are not considered correct because they are not grounded to validated XBRL facts.

`improved_rag` applies metadata filters such as form type, fiscal period, and section type. It reaches perfect evidence recall on this dataset, but still cannot pass numeric fact checks without structured grounding.

`improved_rag_xbrl` combines metadata-aware retrieval with XBRL fact lookup and citation validation. It is the only variant that reaches 100% numeric accuracy and 100% refusal accuracy on this dataset.

## Resume Signal

This benchmark demonstrates more than a chatbot wrapper:

- Evidence-constrained answers over real SEC filings.
- Deterministic citation checks against expected filing chunks.
- Structured XBRL validation for financial metrics.
- Refusal behavior for unsupported, ambiguous, or unavailable questions.
- A repeatable ablation comparing closed-book, naive RAG, filtered RAG, and filtered RAG plus XBRL.

## Reproduce

Run against a local database containing the two Apple filings:

```bash
PYTHONPATH=backend/src DATABASE_URL=sqlite:///data/sec_copilot_real.db \
  .venv/bin/python -m sec_copilot.cli run-eval \
  --dataset evals/questions/aapl_real_2025_2026.jsonl \
  --output evals/results/aapl_real_eval.json \
  --report evals/results/aapl_real_eval.md
```

`evals/results/` is ignored because it is generated output. This report records the benchmark result used for the portfolio demo.

## Current Limitations

This is a focused portfolio benchmark, not a broad public leaderboard. It covers one issuer and two filings. The next evaluation step is to add more issuers, more filing types, and harder questions where citation coverage and answer phrasing are graded separately.
