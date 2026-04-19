# Guarded LLM Synthesis Design

Date: 2026-04-19
Status: Draft for user review

## Purpose

Add an optional LLM-written answer mode to SEC Filing Intelligence Copilot while
preserving the project's main advantage: deterministic retrieval, citations,
refusals, and XBRL-grounded numeric validation.

The goal is not to turn the system into a generic chatbot. The goal is to make
supported answers read like a polished analyst response while the existing
pipeline remains the authority for what may be answered.

## Product Decision

The API keeps `extractive` as the default answer mode for stable tests and
deterministic behavior. The UI defaults to LLM mode for demo polish when an
OpenAI key is configured, but clearly falls back to extractive answers when LLM
synthesis is unavailable.

## User Experience

The Ask workflow gets a visible answer mode control:

- `Extractive`: current deterministic answer behavior.
- `Polished`: LLM-written answer constrained by retrieved evidence and XBRL facts.

When `Polished` succeeds, the UI still shows the same citations, retrieved chunk
count, confidence, and numeric grounding badges. When the LLM is unavailable or
fails validation, the UI shows the deterministic answer and can expose a concise
metadata note such as `LLM fallback: missing OpenAI key` or `LLM fallback:
numeric value not preserved`.

Unsupported questions, investment advice, forecasts, ambiguous metric questions,
and insufficient-evidence responses are not sent to the LLM. They keep the
existing deterministic refusal wording.

## Architecture

The existing `CitedAnswerService` remains the orchestrator:

1. Classify the query.
2. Retrieve filing chunks.
3. Build citations.
4. Query XBRL facts for numeric questions.
5. Decide whether evidence is sufficient.
6. Produce the deterministic answer.
7. Optionally pass the supported deterministic result to LLM synthesis.
8. Validate the LLM result.
9. Return the LLM answer or the deterministic fallback.

This keeps the answer contract stable and prevents the LLM from changing support
status, citations, numeric grounding, or refusal behavior.

## Data Model And API Changes

`AskRequest` adds:

- `answer_mode`: enum, default `extractive`, allowed values `extractive` and `llm`.

`AskResponse` adds:

- `answer_mode`: mode actually returned.
- `fallback_answer`: optional deterministic answer when LLM mode was requested.
- `synthesis_model`: optional model name used for LLM synthesis.
- `synthesis_status`: `not_requested`, `succeeded`, `fallback`, or `unavailable`.
- `synthesis_reason`: optional short reason for fallback or unavailability.

Existing clients that do not send `answer_mode` continue to receive extractive
answers.

## LLM Synthesis Service

Add a small `LlmSynthesisService` under the answering package. It depends on
settings and an HTTP client boundary rather than importing eval-specific code.

Input:

- question
- deterministic answer
- query type
- citations and snippets
- numeric grounding facts

Output:

- rewritten answer text
- model metadata
- validation status

The service calls the OpenAI Responses API with the configured synthesis model.
The prompt instructs the model to:

- answer only from the supplied deterministic answer, citations, and numeric facts
- keep exact numeric values, units, periods, and XBRL concepts when present
- avoid investment advice, forecasts, ratings, and price targets
- not invent citations or cite sources outside the provided snippets
- write a concise answer suitable for a filing research workflow

The LLM does not receive the full filing or raw database rows, only the selected
evidence already approved by the deterministic pipeline.

## Configuration

Add settings and `.env.example` entries:

- `OPENAI_SYNTHESIS_MODEL=gpt-5-mini`
- `OPENAI_SYNTHESIS_MAX_OUTPUT_TOKENS=600`
- `OPENAI_SYNTHESIS_REASONING_EFFORT=minimal`
- `OPENAI_SYNTHESIS_TIMEOUT_SECONDS=60`

The service reuses `OPENAI_API_KEY` and `OPENAI_BASE_URL`.

If `OPENAI_API_KEY` is missing, `answer_mode=llm` returns the deterministic answer
with `synthesis_status=unavailable` and `synthesis_reason=missing_openai_api_key`.

## Guardrails

The deterministic answer remains authoritative.

LLM synthesis is skipped when:

- `supported` is false
- query type is `unsupported`
- no citations are available
- numeric grounding is required but not validated

LLM output is rejected when:

- it is empty
- it contains investment-advice language
- it omits the exact validated numeric value for numeric questions
- it changes the unit, fiscal year, fiscal quarter, or fiscal period for a numeric fact
- it references citation IDs or URLs not present in the deterministic response

On rejection, the API returns the deterministic answer, `synthesis_status=fallback`,
and a short machine-readable `synthesis_reason`.

## Evaluation

Add a new eval variant:

- `improved_rag_xbrl_llm`

This variant runs the same retrieval, citation, refusal, and XBRL grounding path
as `improved_rag_xbrl`, but requests `answer_mode=llm`. The current scoring
metrics still apply:

- exact numeric accuracy
- grounded numeric accuracy
- refusal accuracy
- citation and evidence recall
- answer keyword matching for text questions

Success criteria for the first version:

- Apple and Microsoft `improved_rag_xbrl_llm` keeps 100% numeric accuracy.
- Apple and Microsoft `improved_rag_xbrl_llm` keeps 100% grounded numeric accuracy.
- Unsupported and insufficient-evidence questions keep deterministic refusal behavior.
- Text answers are at least as readable as the extractive baseline in manual review.

If the LLM variant falls back on some examples, that is acceptable when the
fallback protects correctness. Reports should include fallback rate.

## Frontend Changes

The Ask form adds an answer mode toggle near the question box.

The result panel shows:

- answer text
- synthesis mode and status
- fallback reason when applicable
- existing citations
- existing numeric grounding details

The benchmark tab adds the `Filtered RAG + XBRL + LLM` row once the variant is
implemented and benchmarked. It should not replace the deterministic row; the
point is to show that polish is layered on top of grounding.

## Testing

Backend tests:

- default `AskRequest` uses extractive mode
- `answer_mode=llm` skips unsupported questions
- missing OpenAI key falls back without failing the request
- numeric LLM output must preserve exact validated values
- invalid LLM output falls back to deterministic answer
- eval parser accepts `improved_rag_xbrl_llm`

Frontend tests/checks:

- TypeScript compiles with the new request and response fields
- UI mode toggle sends the selected `answer_mode`
- fallback metadata renders without layout breakage

Manual verification:

- ask Apple FY2025 revenue in polished mode
- ask Microsoft FY2025 revenue in polished mode
- ask a Microsoft risk-factor question in polished mode
- ask an investment-advice question and confirm no LLM call is attempted

## Rollout

Implement behind explicit request mode first. Keep extractive mode stable and
documented. After benchmark results are available, update the public README and
reports with the LLM variant only if it preserves the grounded metrics.
