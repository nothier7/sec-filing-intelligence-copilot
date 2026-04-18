from __future__ import annotations

import re

from sec_copilot.retrieval import RetrievalResult

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]*")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+|\n{2,}")
NUMBER_PATTERN = re.compile(r"[$%]|\b\d+(\.\d+)?\b")

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "and",
    "are",
    "because",
    "between",
    "can",
    "company",
    "could",
    "did",
    "does",
    "filing",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "its",
    "main",
    "may",
    "over",
    "risk",
    "risks",
    "sec",
    "that",
    "the",
    "their",
    "this",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "with",
}


def best_evidence_snippet(question: str, result: RetrievalResult, max_chars: int = 360) -> str:
    terms = _query_terms(question)
    best_fragment = ""
    best_score = -1
    for fragment in _fragments(result.text):
        fragment_terms = set(_tokens(fragment))
        score = len(terms & fragment_terms)
        if score > best_score:
            best_fragment = fragment
            best_score = score

    if not best_fragment:
        best_fragment = result.text
    return _ellipsize(_normalize_whitespace(best_fragment), max_chars=max_chars)


def has_numeric_evidence(snippets: list[str]) -> bool:
    return any(NUMBER_PATTERN.search(snippet) for snippet in snippets)


def synthesize_extractive_answer(question: str, snippets: list[str]) -> str:
    if not snippets:
        return insufficient_evidence_answer()

    unique_snippets = _dedupe(snippets)
    if len(unique_snippets) == 1:
        return f"The filing evidence states: {unique_snippets[0]}"

    joined = " ".join(unique_snippets[:3])
    return f"The filing evidence points to these disclosures: {joined}"


def insufficient_evidence_answer() -> str:
    return "I do not have enough filing evidence to answer that confidently."


def unsupported_answer() -> str:
    return (
        "I cannot answer investment advice, forecasts, or questions outside the selected "
        "filing evidence. Ask about disclosures in the filing instead."
    )


def _query_terms(question: str) -> set[str]:
    return {token for token in _tokens(question) if token not in STOPWORDS and len(token) > 2}


def _tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _fragments(text: str) -> list[str]:
    return [fragment.strip() for fragment in SENTENCE_BOUNDARY_PATTERN.split(text) if fragment.strip()]


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _ellipsize(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _dedupe(snippets: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        normalized = snippet.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(snippet)
    return unique
