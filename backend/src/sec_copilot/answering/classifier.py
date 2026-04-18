from __future__ import annotations

import re

from sec_copilot.answering.models import QueryType

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_\-]*")

UNSUPPORTED_TERMS = {
    "buy",
    "sell",
    "hold",
    "invest",
    "investment",
    "outperform",
    "price target",
    "stock price",
    "share price",
    "forecast",
    "predict",
    "prediction",
}

COMPARISON_TERMS = {
    "compare",
    "compared",
    "comparison",
    "change",
    "changed",
    "difference",
    "different",
    "trend",
    "versus",
    "vs",
    "previous",
    "prior",
}

NUMERIC_TERMS = {
    "amount",
    "cash",
    "cost",
    "debt",
    "dollars",
    "earnings",
    "expense",
    "expenses",
    "income",
    "margin",
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


def classify_query(question: str) -> QueryType:
    normalized = _normalize(question)
    tokens = set(TOKEN_PATTERN.findall(normalized))

    if _contains_any_phrase(normalized, UNSUPPORTED_TERMS):
        return QueryType.UNSUPPORTED
    if tokens & COMPARISON_TERMS:
        return QueryType.COMPARISON
    if tokens & NUMERIC_TERMS or re.search(r"[$%]|\b\d+(\.\d+)?\b", normalized):
        return QueryType.NUMERIC
    return QueryType.TEXT


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _contains_any_phrase(text: str, phrases: set[str]) -> bool:
    return any(phrase in text for phrase in phrases)
