from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from sec_copilot.db.models import Company, Filing, XbrlFact
from sec_copilot.facts import FactLookupRequest, FactLookupService, match_metric
from sec_copilot.repositories import CompanyRepository, FilingRepository, XbrlFactRepository


def test_match_metric_maps_common_financial_language() -> None:
    assert match_metric("How much revenue did Apple report?").key == "revenue"
    assert match_metric("What was net income?").key == "net_income"
    assert match_metric("How much cash from operations was reported?").key == "operating_cash_flow"
    assert match_metric("How much did Apple spend on R&D?").key == "research_and_development"
    assert match_metric("What were operating expenses?").key == "operating_expenses"
    assert match_metric("How much did Apple spend on buybacks?").key == "share_repurchases"
    assert match_metric("How much did Apple spend in 2025?") is None
    assert match_metric("What are the risk factors?") is None


def test_fact_lookup_prefers_accession_and_primary_concept(session: Session) -> None:
    filing = _create_filing(session)
    facts = XbrlFactRepository(session)
    facts.add(
        XbrlFact(
            source_key="aapl-revenues-fy2024-older",
            company_id=filing.company_id,
            cik=filing.cik,
            accession_number="other-accession",
            concept="Revenues",
            label="Revenues",
            unit="USD",
            value=Decimal("300000000000"),
            fiscal_period="FY",
            fiscal_year=2024,
            form_type="10-K",
            filed_date=date(2024, 10, 1),
        )
    )
    preferred = facts.add(
        XbrlFact(
            source_key="aapl-revenue-fy2024",
            company_id=filing.company_id,
            filing_id=filing.id,
            cik=filing.cik,
            accession_number=filing.accession_number,
            concept="RevenueFromContractWithCustomerExcludingAssessedTax",
            label="Revenue",
            unit="USD",
            value=Decimal("383285000000"),
            fiscal_period="FY",
            fiscal_year=2024,
            form_type="10-K",
            filed_date=filing.filing_date,
        )
    )
    session.commit()

    result = FactLookupService(session).lookup(
        FactLookupRequest(question="How much revenue did Apple report?", filing=filing)
    )

    assert result.found is True
    assert result.metric.key == "revenue"
    assert result.fact == preferred


def test_fact_lookup_reports_unavailable_for_missing_metric_fact(session: Session) -> None:
    filing = _create_filing(session)

    result = FactLookupService(session).lookup(
        FactLookupRequest(question="How much revenue did Apple report?", filing=filing)
    )

    assert result.found is False
    assert result.metric.key == "revenue"
    assert result.reason == "fact_not_found"


def test_fact_lookup_supports_specific_spending_categories(session: Session) -> None:
    filing = _create_filing(session)
    XbrlFactRepository(session).add(
        XbrlFact(
            source_key="aapl-rd-fy2024",
            company_id=filing.company_id,
            filing_id=filing.id,
            cik=filing.cik,
            accession_number=filing.accession_number,
            concept="ResearchAndDevelopmentExpense",
            label="Research and Development Expense",
            unit="USD",
            value=Decimal("31370000000"),
            fiscal_period="FY",
            fiscal_year=2024,
            form_type="10-K",
            filed_date=filing.filing_date,
        )
    )
    session.commit()

    result = FactLookupService(session).lookup(
        FactLookupRequest(question="How much did Apple spend on R&D?", filing=filing)
    )

    assert result.found is True
    assert result.metric.key == "research_and_development"
    assert result.fact.concept == "ResearchAndDevelopmentExpense"
    assert result.fact.value == Decimal("31370000000")


def _create_filing(session: Session) -> Filing:
    company = CompanyRepository(session).add(
        Company(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    filing = FilingRepository(session).add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-24-000123",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2024, 11, 1),
            report_date=date(2024, 9, 28),
            fiscal_year=2024,
            source_url="https://www.sec.gov/Archives/example.htm",
        )
    )
    session.commit()
    return filing
