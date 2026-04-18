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
        key="operating_expenses",
        label="operating expenses",
        concepts=("OperatingExpenses",),
        keywords=("operating expenses", "operating expense", "opex"),
    ),
    MetricDefinition(
        key="research_and_development",
        label="research and development expense",
        concepts=("ResearchAndDevelopmentExpense",),
        keywords=("research and development", "r&d", "research development"),
    ),
    MetricDefinition(
        key="selling_general_and_administrative",
        label="selling, general and administrative expense",
        concepts=("SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"),
        keywords=(
            "selling general and administrative",
            "selling, general and administrative",
            "sg&a",
            "sga",
            "general and administrative",
        ),
    ),
    MetricDefinition(
        key="cost_of_sales",
        label="cost of sales",
        concepts=("CostOfGoodsAndServicesSold", "CostOfRevenue"),
        keywords=("cost of sales", "cost of revenue", "cost of goods", "costs"),
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
        key="share_repurchases",
        label="share repurchases",
        concepts=("PaymentsForRepurchaseOfCommonStock",),
        keywords=(
            "share repurchases",
            "share repurchase",
            "stock repurchases",
            "stock repurchase",
            "buybacks",
            "stock buybacks",
        ),
    ),
    MetricDefinition(
        key="dividends",
        label="dividend payments",
        concepts=(
            "PaymentsOfDividends",
            "PaymentsOfDividendsCommonStock",
            "PaymentsOfDividendsAndDividendEquivalentsOnCommonStockAndRestrictedStockUnits",
        ),
        keywords=("dividends", "dividend payments", "paid dividends"),
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
    if " " in keyword or any(not character.isalnum() for character in keyword):
        return keyword in text
    return keyword in tokens


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())
