from __future__ import annotations

from typing import Optional

from sec_copilot.evals.models import EvalRunResult, EvalVariant


def format_eval_report(result: EvalRunResult) -> str:
    lines = [
        "# SEC Copilot Evaluation Report",
        "",
        f"Generated: {result.generated_at.isoformat()}Z",
        f"Dataset: `{result.dataset_path}`",
        f"Questions: {result.question_count}",
        "",
        "## Headline Metrics",
        "",
        "| Variant | Accuracy | Numeric Accuracy | Refusal Accuracy | Evidence Recall | Avg Latency (ms) | Error Rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in result.variants:
        metrics = result.metrics.get(variant, {})
        lines.append(
            "| "
            f"{_variant_label(variant)} | "
            f"{_percent(metrics.get('accuracy'))} | "
            f"{_percent(metrics.get('numeric_accuracy'))} | "
            f"{_percent(metrics.get('refusal_accuracy'))} | "
            f"{_percent(metrics.get('evidence_recall'))} | "
            f"{_number(metrics.get('avg_latency_ms'))} | "
            f"{_percent(metrics.get('error_rate'))} |"
        )

    lines.extend(
        [
            "",
            "## Ablation Notes",
            "",
            "- `closed_book` intentionally answers without filing context.",
            "- `naive_rag` retrieves over the full filing without section metadata filters or XBRL grounding.",
            "- `improved_rag` applies the eval question's metadata filters but keeps numeric answers text-only.",
            "- `improved_rag_xbrl` adds structured SEC fact lookup for numeric questions.",
            "",
            "## Failure Examples",
            "",
        ]
    )
    failures = _failure_examples(result)
    if not failures:
        lines.append("No failing examples in this run.")
    else:
        lines.extend(failures)

    lines.append("")
    return "\n".join(lines)


def _failure_examples(result: EvalRunResult, limit: int = 10) -> list[str]:
    failures: list[str] = []
    for question_result in result.results:
        question = question_result.question
        for variant in result.variants:
            metrics = question_result.metrics[variant]
            if metrics["answer_correct"] == 1.0:
                continue
            prediction = question_result.predictions[variant]
            failures.append(
                "- "
                f"`{question.id}` / `{variant.value}`: "
                f"expected_supported={question.expected.supported}, "
                f"predicted_supported={prediction.supported}, "
                f"reason={prediction.insufficient_evidence_reason or 'n/a'}, "
                f"answer=\"{_clip(prediction.answer)}\""
            )
            if len(failures) >= limit:
                return failures
    return failures


def _variant_label(variant: EvalVariant) -> str:
    return variant.value.replace("_", " ")


def _percent(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _number(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def _clip(value: str, max_chars: int = 180) -> str:
    text = " ".join(value.split()).replace("|", "\\|")
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."
