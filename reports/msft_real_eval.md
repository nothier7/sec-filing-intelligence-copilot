# Microsoft SEC Filing Evaluation Report

Generated on 2026-04-19 from `evals/questions/msft_real_2025_2026.jsonl`.

This benchmark uses locally ingested Microsoft SEC filings:

- Microsoft FY2025 Form 10-K: `0000950170-25-100235`
- Microsoft Q2 FY2026 Form 10-Q: `0001193125-26-027207`

The local database also contains Microsoft Q1 FY2026 and Q3 FY2025 Form 10-Q
filings for manual testing and future comparisons.

The dataset contains 24 questions:

- 12 numeric questions with expected XBRL concepts and exact values.
- 8 disclosure questions with expected citation chunks.
- 4 refusal questions for investment advice, forecasts, ambiguous metrics, or unavailable periods.

The OpenAI baselines used `gpt-5-mini`. Cached predictions live under
`evals/results/cache/openai`. The web-search baseline uses the OpenAI Responses
API `web_search` tool. Unlike the Apple tracked report, the OpenAI latency here
reflects a fresh API run for Microsoft.

## Headline Metrics

| Variant | Accuracy | Numeric Accuracy | Grounded Numeric Accuracy | Refusal Accuracy | Evidence Recall | Avg Latency (ms) | Error Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| closed book | 8.3% | 0.0% | 0.0% | 50.0% | 16.7% | 0.0 | 0.0% |
| naive rag | 29.2% | 16.7% | 0.0% | 50.0% | 64.6% | 83.5 | 0.0% |
| improved rag | 50.0% | 8.3% | 0.0% | 75.0% | 100.0% | 55.6 | 0.0% |
| openai closed book | 8.3% | 0.0% | 0.0% | 50.0% | 16.7% | 1850.6 | 0.0% |
| openai retrieved context | 33.3% | 41.7% | 0.0% | 50.0% | 100.0% | 1918.1 | 0.0% |
| openai web search | 20.8% | 16.7% | 0.0% | 50.0% | 16.7% | 20216.1 | 0.0% |
| improved rag xbrl | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 58.8 | 0.0% |

## What The Ablation Shows

`closed_book` and `openai_closed_book` intentionally have no filing excerpts, so
they mostly refuse evidence-dependent filing questions.

`naive_rag` retrieves relevant Microsoft chunks but cannot reliably answer exact
financial values because it has no structured fact validation.

`improved_rag` reaches 100% evidence recall through metadata filters, but still
has weak numeric accuracy because it must infer values from text snippets only.

`openai_retrieved_context` receives the same local excerpts and reaches 100%
evidence recall, but it answers only 33.3% of the benchmark correctly and has 0%
grounded numeric accuracy because it lacks the XBRL validation layer.

`openai_web_search` answers some public Microsoft values, but this benchmark
requires exact values and local evidence. It often returns rounded values,
refuses after finding only filing index pages, or cites web pages outside the
local corpus. It also has 0% grounded numeric accuracy.

`improved_rag_xbrl` combines metadata-aware retrieval with structured SEC fact
lookup and citation validation. It reaches 100% accuracy, 100% numeric accuracy,
100% grounded numeric accuracy, 100% refusal accuracy, and 100% evidence recall
on the Microsoft dataset.

## Example Baseline Failures

OpenAI retrieved-context refused Microsoft FY2025 revenue even though local
retrieval supplied filing context. The XBRL-grounded system returned the exact
validated value `$281,724,000,000`.

OpenAI web search answered Microsoft FY2025 revenue as `$281.7 billion`, which is
directionally right but fails exact numeric scoring. The XBRL-grounded answer
returns the exact SEC fact and associated concept.

OpenAI web search answered Microsoft FY2025 net income as `$74.599 billion`,
which does not match the FY2025 XBRL value `$101,832,000,000`.

OpenAI retrieved-context and web search both had 0% grounded numeric accuracy
because neither baseline validates final answers against parsed XBRL facts.

## Resume Signal

The second issuer matters because it shows the project is not tuned only for
Apple. The same ingestion, parsing, retrieval, citation, refusal, and XBRL
grounding path works on Microsoft filings with no issuer-specific code.

This is the comparison a hiring manager can understand:

- Generic model without filing context: safe refusals but low utility.
- Generic model with retrieved excerpts: useful context but no structured validation.
- Generic model with web search: can find public numbers but may round, cite outside the corpus, or miss exact table values.
- SEC Copilot with XBRL grounding: exact financial facts, local citations, and deterministic refusal behavior.

## Reproduce

Run against a local database containing the Microsoft filings:

```bash
PYTHONPATH=backend/src DATABASE_URL=sqlite:///data/sec_copilot_real.db \
  .venv/bin/python -m sec_copilot.cli run-eval \
  --dataset evals/questions/msft_real_2025_2026.jsonl \
  --variant closed_book \
  --variant naive_rag \
  --variant improved_rag \
  --variant improved_rag_xbrl \
  --variant openai_closed_book \
  --variant openai_retrieved_context \
  --variant openai_web_search \
  --output evals/results/msft_real_openai_eval.json \
  --report evals/results/msft_real_openai_eval.md
```

`evals/results/` is ignored because it is generated output. This report records
the Microsoft benchmark result used for the portfolio demo.
