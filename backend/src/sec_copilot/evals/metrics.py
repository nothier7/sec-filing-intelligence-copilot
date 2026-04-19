from __future__ import annotations

from collections.abc import Iterable

from sec_copilot.evals.models import EvalPrediction, EvalQuestion


def score_prediction(question: EvalQuestion, prediction: EvalPrediction) -> dict[str, float]:
    expected = question.expected
    keyword_match = _keyword_match(expected.answer_keywords, _answer_context(prediction))
    citation_recall = _recall(
        expected.citation_chunk_ids,
        [citation.chunk_id for citation in prediction.citations],
    )
    section_recall = _recall(
        expected.section_types,
        [
            citation.section_type
            for citation in prediction.citations
            if citation.section_type is not None
        ],
    )
    numeric_match = _numeric_match(question, prediction)
    numeric_grounding_match = _numeric_grounding_match(question, prediction)
    supported_match = float(prediction.supported == expected.supported)
    refusal_match = _refusal_match(question, prediction)

    return {
        "answer_correct": _answer_correct(
            question=question,
            prediction=prediction,
            keyword_match=keyword_match,
            numeric_match=numeric_match,
            refusal_match=refusal_match,
        ),
        "supported_match": supported_match,
        "keyword_match": keyword_match,
        "citation_recall": citation_recall,
        "section_recall": section_recall,
        "evidence_recall": citation_recall if expected.citation_chunk_ids else section_recall,
        "numeric_match": numeric_match,
        "numeric_grounding_match": numeric_grounding_match,
        "refusal_match": refusal_match,
        "latency_ms": prediction.latency_ms,
        "error": float(prediction.error is not None),
    }


def aggregate_metrics(scores: Iterable[dict[str, float]]) -> dict[str, float]:
    score_list = list(scores)
    if not score_list:
        return {}

    metrics = {
        "accuracy": _mean(score["answer_correct"] for score in score_list),
        "supported_accuracy": _mean(score["supported_match"] for score in score_list),
        "evidence_recall": _mean(score["evidence_recall"] for score in score_list),
        "citation_recall": _mean(score["citation_recall"] for score in score_list),
        "avg_latency_ms": _mean(score["latency_ms"] for score in score_list),
        "error_rate": _mean(score["error"] for score in score_list),
    }

    numeric_scores = [
        score["numeric_match"] for score in score_list if score["numeric_match"] >= 0.0
    ]
    if numeric_scores:
        metrics["numeric_accuracy"] = _mean(numeric_scores)

    grounded_numeric_scores = [
        score["numeric_grounding_match"]
        for score in score_list
        if score["numeric_grounding_match"] >= 0.0
    ]
    if grounded_numeric_scores:
        metrics["numeric_grounding_accuracy"] = _mean(grounded_numeric_scores)

    refusal_scores = [
        score["refusal_match"] for score in score_list if score["refusal_match"] >= 0.0
    ]
    if refusal_scores:
        metrics["refusal_accuracy"] = _mean(refusal_scores)

    return metrics


def _answer_correct(
    question: EvalQuestion,
    prediction: EvalPrediction,
    keyword_match: float,
    numeric_match: float,
    refusal_match: float,
) -> float:
    if prediction.error is not None:
        return 0.0
    if not question.expected.supported:
        return refusal_match
    if not prediction.supported:
        return 0.0
    if question.expected.numeric_value is not None or question.expected.xbrl_concepts:
        return 1.0 if numeric_match == 1.0 else 0.0
    if question.expected.answer_keywords:
        return 1.0 if keyword_match == 1.0 else 0.0
    return 1.0


def _keyword_match(expected_keywords: list[str], context: str) -> float:
    if not expected_keywords:
        return 1.0
    normalized_context = context.casefold()
    matches = sum(1 for keyword in expected_keywords if keyword.casefold() in normalized_context)
    return matches / len(expected_keywords)


def _numeric_match(question: EvalQuestion, prediction: EvalPrediction) -> float:
    expected = question.expected
    if expected.numeric_value is None and not expected.xbrl_concepts:
        return -1.0
    if _numeric_grounding_match(question, prediction) == 1.0:
        return 1.0
    if expected.numeric_value is None:
        return 0.0

    expected_tokens = _expected_numeric_tokens(expected.numeric_value)
    observed_tokens = _observed_numeric_tokens(_answer_context(prediction))
    return float(bool(expected_tokens & observed_tokens))


def _numeric_grounding_match(question: EvalQuestion, prediction: EvalPrediction) -> float:
    expected = question.expected
    if expected.numeric_value is None and not expected.xbrl_concepts:
        return -1.0

    normalized_expected_value = _digits(expected.numeric_value or "")
    expected_concepts = set(expected.xbrl_concepts)
    for grounding in prediction.numeric_grounding:
        value_matches = (
            not normalized_expected_value
            or _digits(grounding.value or "") == normalized_expected_value
        )
        concept_matches = not expected_concepts or grounding.concept in expected_concepts
        unit_matches = expected.numeric_unit is None or grounding.unit == expected.numeric_unit
        if value_matches and concept_matches and unit_matches:
            return 1.0
    return 0.0


def _refusal_match(question: EvalQuestion, prediction: EvalPrediction) -> float:
    if question.expected.supported:
        return -1.0
    reason_matches = (
        question.expected.insufficient_reason is None
        or prediction.insufficient_evidence_reason == question.expected.insufficient_reason
    )
    return float(not prediction.supported and reason_matches)


def _recall(expected_values: list[str], observed_values: list[str]) -> float:
    if not expected_values:
        return 1.0
    observed = set(observed_values)
    hits = sum(1 for value in expected_values if value in observed)
    return hits / len(expected_values)


def _answer_context(prediction: EvalPrediction) -> str:
    snippets = " ".join(citation.snippet for citation in prediction.citations)
    return f"{prediction.answer} {snippets}"


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _expected_numeric_tokens(value: str) -> set[str]:
    digits = _digits(value)
    if not digits:
        return set()
    tokens = {digits}
    integer_value = int(digits)
    for divisor in (1_000, 1_000_000, 1_000_000_000):
        if integer_value % divisor == 0:
            tokens.add(str(integer_value // divisor))
    return tokens


def _observed_numeric_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    normalized = text.replace(",", "")
    for raw_token in normalized.split():
        digits = _digits(raw_token)
        if digits:
            tokens.add(digits)
    return tokens


def _mean(values: Iterable[float]) -> float:
    value_list = list(values)
    return sum(value_list) / len(value_list) if value_list else 0.0
