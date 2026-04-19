# Apple SEC Filing Evaluation Report

Generated on 2026-04-19 from `evals/questions/aapl_real_2025_2026.jsonl`.

This benchmark uses locally ingested Apple SEC filings:

- Apple FY2025 Form 10-K: `0000320193-25-000079`
- Apple Q1 FY2026 Form 10-Q: `0000320193-26-000006`

The dataset contains 24 questions:

- 12 numeric questions with expected XBRL concepts and values.
- 8 disclosure or comparison questions with expected citation chunks.
- 4 refusal questions for investment advice, forecasts, ambiguous metrics, or unavailable periods.

The OpenAI baselines used `gpt-5-mini` with cached predictions under
`evals/results/cache/openai`.
Latency for the tracked OpenAI predictions reflects fresh API calls; cached reruns
may be much faster.

## Headline Metrics

| Variant | Accuracy | Numeric Accuracy | Grounded Numeric Accuracy | Refusal Accuracy | Evidence Recall | Avg Latency (ms) | Error Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed book | 8.3% | 0.0% | 0.0% | 50.0% | 16.7% | 0.0 | 0.0% |
| naive rag | 33.3% | 16.7% | 0.0% | 50.0% | 83.3% | 65.6 | 0.0% |
| improved rag | 54.2% | 16.7% | 0.0% | 75.0% | 100.0% | 38.4 | 0.0% |
| openai closed book | 8.3% | 0.0% | 0.0% | 50.0% | 16.7% | 1791.1 | 0.0% |
| openai retrieved context | 50.0% | 66.7% | 0.0% | 50.0% | 100.0% | 1717.2 | 0.0% |
| improved rag xbrl | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 40.2 | 0.0% |

## What The Ablation Shows

`closed_book` intentionally has no filing context. It behaves like a generic assistant that refuses most evidence-dependent questions.

`naive_rag` retrieves filing chunks but does not use metadata filters or structured SEC facts. It can often find relevant snippets, but it has low numeric accuracy and no grounded numeric validation.

`improved_rag` applies metadata filters such as form type, fiscal period, and section type. It reaches perfect evidence recall on this dataset, but still has no structured numeric grounding.

`openai_closed_book` asks `gpt-5-mini` without filing excerpts. It correctly
refuses many evidence-dependent questions, which is safer than hallucinating but
still not useful for filing analysis.

`openai_retrieved_context` asks `gpt-5-mini` with retrieved filing excerpts. It
answers several numeric questions correctly from context, but still misses some
supported questions and has 0% grounded numeric accuracy because it has no
structured XBRL validation layer.

`improved_rag_xbrl` combines metadata-aware retrieval with XBRL fact lookup and citation validation. It is the only variant that reaches 100% numeric accuracy, 100% grounded numeric accuracy, and 100% refusal accuracy on this dataset.

## Example Baseline Failures

OpenAI closed-book refused the 2025 revenue question because it had no filing
evidence. The validated SEC/XBRL value is `$416,161,000,000`.

OpenAI with retrieved context answered the 2025 revenue question correctly from
retrieved excerpts, but it still lacked grounded XBRL validation.

OpenAI with retrieved context refused the 2025 R&D and operating expense
questions even though the relevant retrieved filing excerpt contained the
operating expense table. The XBRL-grounded variant answered both with validated
structured facts.

## Resume Signal

This benchmark demonstrates more than a chatbot wrapper:

- Evidence-constrained answers over real SEC filings.
- Deterministic citation checks against expected filing chunks.
- Structured XBRL validation for financial metrics.
- Refusal behavior for unsupported, ambiguous, or unavailable questions.
- A repeatable ablation comparing closed-book, naive RAG, filtered RAG, OpenAI
  baselines, and filtered RAG plus XBRL.

## Reproduce

Run against a local database containing the two Apple filings:

```bash
PYTHONPATH=backend/src DATABASE_URL=sqlite:///data/sec_copilot_real.db \
  .venv/bin/python -m sec_copilot.cli run-eval \
  --dataset evals/questions/aapl_real_2025_2026.jsonl \
  --variant closed_book \
  --variant naive_rag \
  --variant improved_rag \
  --variant improved_rag_xbrl \
  --variant openai_closed_book \
  --variant openai_retrieved_context \
  --output evals/results/aapl_real_openai_eval.json \
  --report evals/results/aapl_real_openai_eval.md
```

`evals/results/` is ignored because it is generated output. This report records the benchmark result used for the portfolio demo.

## Current Limitations

This is a focused portfolio benchmark, not a broad public leaderboard. It covers one issuer and two filings. The next evaluation step is to add more issuers, more filing types, and harder questions where citation coverage and answer phrasing are graded separately.
