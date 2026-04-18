from __future__ import annotations

import re

from sec_copilot.retrieval import RetrievalResult

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]*")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+|\n{2,}")
NUMBER_PATTERN = re.compile(r"[$%]|\b\d+(\.\d+)?\b")
NUMERIC_QUERY_TERMS = {
    "amount",
    "cash",
    "cost",
    "dollars",
    "earnings",
    "expense",
    "expenses",
    "income",
    "many",
    "much",
    "number",
    "percent",
    "percentage",
    "profit",
    "revenue",
    "sales",
    "spend",
    "spending",
    "spent",
    "total",
    "value",
}

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
    numeric_query = _is_numeric_query(question)
    best_fragment = ""
    best_score = float("-inf")
    for fragment in _candidate_fragments(result.text):
        score = _fragment_score(
            fragment=fragment,
            query_terms=terms,
            numeric_query=numeric_query,
        )
        if score > best_score:
            best_fragment = fragment
            best_score = score

    if not best_fragment:
        best_fragment = result.text
    return _ellipsize(_normalize_whitespace(best_fragment), max_chars=max_chars)


def has_numeric_evidence(snippets: list[str]) -> bool:
    return any(NUMBER_PATTERN.search(snippet) for snippet in snippets)


def has_no_material_change_evidence(snippets: list[str]) -> bool:
    return any("no material changes" in snippet.casefold() for snippet in snippets)


def synthesize_extractive_answer(question: str, snippets: list[str]) -> str:
    if not snippets:
        return insufficient_evidence_answer()

    unique_snippets = _dedupe(snippets)
    if len(unique_snippets) == 1:
        return f"The filing evidence states: {unique_snippets[0]}"

    joined = " ".join(unique_snippets[:3])
    return f"The filing evidence points to these disclosures: {joined}"


def synthesize_numeric_fact_answer(
    metric_label: str,
    value: str,
    unit: str,
    period: str,
    concept: str,
) -> str:
    return (
        f"The structured SEC fact for {metric_label} is {value} {unit} for {period} "
        f"(XBRL concept: {concept})."
    )


def insufficient_evidence_answer() -> str:
    return "I do not have enough filing evidence to answer that confidently."


def metric_clarification_answer() -> str:
    return (
        "I need a more specific financial metric before I can answer that from SEC facts. "
        "Try asking about operating expenses, R&D expense, SG&A expense, capital "
        "expenditures, share repurchases, dividends, revenue, net income, or operating "
        "cash flow."
    )


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


def _candidate_fragments(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for fragment in [*_fragments(text), *_forward_line_windows(text), *_line_windows(text)]:
        normalized = _normalize_whitespace(fragment)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(normalized)
    return candidates


def _forward_line_windows(text: str, after: int = 9) -> list[str]:
    lines = _content_lines(text)
    windows: list[str] = []
    for index, _line in enumerate(lines):
        end = min(len(lines), index + after + 1)
        window = " ".join(lines[index:end])
        if window:
            windows.append(window)
    return windows


def _line_windows(text: str, before: int = 4, after: int = 7) -> list[str]:
    lines = _content_lines(text)
    windows: list[str] = []
    for index, _line in enumerate(lines):
        start = max(0, index - before)
        end = min(len(lines), index + after + 1)
        window = " ".join(lines[start:end])
        if window:
            windows.append(window)
    return windows


def _content_lines(text: str) -> list[str]:
    return [
        line
        for line in (_normalize_whitespace(line) for line in text.splitlines() if line.strip())
        if not _looks_like_page_marker(line)
    ]


def _fragment_score(fragment: str, query_terms: set[str], numeric_query: bool) -> float:
    fragment_terms = set(_tokens(fragment))
    score = len(query_terms & fragment_terms) * 10.0
    token_count = len(fragment_terms)
    leading_terms = set(_tokens(" ".join(fragment.split()[:5])))
    early_terms = set(_tokens(" ".join(fragment.split()[:12])))
    numeric_terms = {term for term in query_terms if any(character.isdigit() for character in term)}
    target_numeric_terms = _target_numeric_terms(numeric_terms)

    if numeric_query and NUMBER_PATTERN.search(fragment):
        score += 6.0
    if numeric_query and "$" in fragment:
        score += 3.0
    if numeric_query and target_numeric_terms & fragment_terms:
        score += 8.0
    if numeric_query and target_numeric_terms & early_terms:
        score += 12.0
    if numeric_query:
        score += min(len(query_terms & leading_terms), 3) * 5.0
    if 60 <= len(fragment) <= 480:
        score += 2.0
    if numeric_query and _starts_with_numeric_or_symbol(fragment):
        score -= 12.0
    if token_count <= 3:
        score -= 12.0
    if _looks_like_page_marker(fragment):
        score -= 10.0
    return score


def _is_numeric_query(question: str) -> bool:
    tokens = set(_tokens(question))
    return bool(tokens & NUMERIC_QUERY_TERMS or NUMBER_PATTERN.search(question))


def _target_numeric_terms(numeric_terms: set[str]) -> set[str]:
    target_terms = {
        term
        for term in numeric_terms
        if term.strip("0") and not (len(term) == 4 and term.startswith(("19", "20")))
    }
    return target_terms or numeric_terms


def _looks_like_page_marker(fragment: str) -> bool:
    normalized = fragment.casefold()
    if "form 10-" in normalized and "|" in normalized:
        return True
    return normalized in {"apple inc.", "apple inc"}


def _starts_with_numeric_or_symbol(fragment: str) -> bool:
    stripped = fragment.lstrip("($ ")
    return bool(stripped) and (stripped[0].isdigit() or stripped[0] in {"$", "%"})


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
