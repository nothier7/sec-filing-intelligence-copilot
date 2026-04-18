from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_\-]*")


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    concepts: tuple[str, ...]
    keywords: tuple[str, ...]


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        key="revenue",
        label="revenue",
        concepts=(
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ),
        keywords=("revenue", "revenues", "sales", "net sales"),
    ),
    MetricDefinition(
        key="net_income",
        label="net income",
        concepts=("NetIncomeLoss", "ProfitLoss"),
        keywords=("net income", "profit", "profits", "earnings"),
    ),
    MetricDefinition(
        key="operating_income",
        label="operating income",
        concepts=("OperatingIncomeLoss",),
        keywords=("operating income", "operating profit"),
    ),
    MetricDefinition(
        key="assets",
        label="total assets",
        concepts=("Assets",),
        keywords=("assets", "total assets"),
    ),
    MetricDefinition(
        key="liabilities",
        label="total liabilities",
        concepts=("Liabilities",),
        keywords=("liabilities", "total liabilities"),
    ),
    MetricDefinition(
        key="operating_cash_flow",
        label="operating cash flow",
        concepts=("NetCashProvidedByUsedInOperatingActivities",),
        keywords=("operating cash flow", "cash from operations", "operating activities"),
    ),
    MetricDefinition(
        key="cash",
        label="cash and cash equivalents",
        concepts=(
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            "CashAndCashEquivalentsAndShortTermInvestments",
        ),
        keywords=("cash", "cash equivalents", "cash and cash equivalents"),
    ),
    MetricDefinition(
        key="capital_expenditures",
        label="capital expenditures",
        concepts=("PaymentsToAcquirePropertyPlantAndEquipment",),
        keywords=("capital expenditures", "capex", "capital expenditure"),
    ),
    MetricDefinition(
        key="diluted_eps",
        label="diluted earnings per share",
        concepts=("EarningsPerShareDiluted",),
        keywords=("diluted eps", "diluted earnings per share"),
    ),
    MetricDefinition(
        key="basic_eps",
        label="basic earnings per share",
        concepts=("EarningsPerShareBasic",),
        keywords=("basic eps", "basic earnings per share"),
    ),
)


def match_metric(question: str) -> MetricDefinition | None:
    normalized = _normalize(question)
    tokens = set(TOKEN_PATTERN.findall(normalized))
    for metric in METRIC_DEFINITIONS:
        if any(_keyword_matches(normalized, tokens, keyword) for keyword in metric.keywords):
            return metric
    return None


def _keyword_matches(text: str, tokens: set[str], keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return keyword in tokens


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
