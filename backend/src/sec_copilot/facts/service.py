from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from sec_copilot.db.models import Filing, XbrlFact
from sec_copilot.facts.metrics import MetricDefinition, match_metric
from sec_copilot.repositories import XbrlFactRepository


@dataclass(frozen=True)
class FactLookupRequest:
    question: str
    filing: Filing
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    form_type: Optional[str] = None


@dataclass(frozen=True)
class FactLookupResult:
    metric: Optional[MetricDefinition]
    fact: Optional[XbrlFact]
    reason: Optional[str] = None

    @property
    def found(self) -> bool:
        return self.fact is not None


class FactLookupService:
    def __init__(self, session: Session) -> None:
        self.facts = XbrlFactRepository(session)

    def lookup(self, request: FactLookupRequest) -> FactLookupResult:
        metric = match_metric(request.question)
        if metric is None:
            return FactLookupResult(metric=None, fact=None, reason="no_metric_match")

        fiscal_year = request.fiscal_year or request.filing.fiscal_year
        fiscal_quarter = _coalesce_quarter(request.fiscal_quarter, request.filing.fiscal_quarter)
        form_type = request.form_type or request.filing.form_type
        fiscal_period = _fiscal_period_for(form_type=form_type, fiscal_quarter=fiscal_quarter)

        matches = self.facts.find_by_concepts(
            company_id=request.filing.company_id,
            concepts=metric.concepts,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            fiscal_period=fiscal_period,
            form_type=form_type,
            accession_number=request.filing.accession_number,
        )
        if not matches:
            matches = self.facts.find_by_concepts(
                company_id=request.filing.company_id,
                concepts=metric.concepts,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                fiscal_period=fiscal_period,
                form_type=form_type,
            )
        if not matches:
            matches = self.facts.find_by_concepts(
                company_id=request.filing.company_id,
                concepts=metric.concepts,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
            )

        if not matches:
            return FactLookupResult(metric=metric, fact=None, reason="fact_not_found")
        return FactLookupResult(metric=metric, fact=_best_fact(matches, metric))


def format_fact_value(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return f"{int(normalized):,}"
    return f"{normalized:f}"


def _best_fact(facts: Sequence[XbrlFact], metric: MetricDefinition) -> XbrlFact:
    concept_rank = {concept: rank for rank, concept in enumerate(metric.concepts)}
    return sorted(
        facts,
        key=lambda fact: (
            concept_rank.get(fact.concept, len(metric.concepts)),
            -fact.filed_date.toordinal() if fact.filed_date is not None else 0,
            -fact.id if fact.id is not None else 0,
        ),
    )[0]


def _coalesce_quarter(
    request_quarter: Optional[int],
    filing_quarter: Optional[int],
) -> Optional[int]:
    if request_quarter is not None:
        return request_quarter
    return filing_quarter


def _fiscal_period_for(form_type: Optional[str], fiscal_quarter: Optional[int]) -> Optional[str]:
    if form_type == "10-K":
        return "FY"
    if fiscal_quarter is not None:
        return f"Q{fiscal_quarter}"
    return None
