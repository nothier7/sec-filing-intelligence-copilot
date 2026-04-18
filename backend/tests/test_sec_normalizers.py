import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sec_copilot.sec.normalizers import (
    normalize_company,
    normalize_company_facts,
    normalize_recent_filings,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_normalize_company_and_recent_filings() -> None:
    submissions = json.loads((FIXTURE_DIR / "submissions_aapl.json").read_text())

    company = normalize_company(submissions)
    filings = normalize_recent_filings(
        submissions,
        form_types=("10-K", "10-Q"),
        limit=10,
        archives_base_url="https://www.sec.gov/Archives",
    )

    assert company.cik == "0000320193"
    assert company.ticker == "AAPL"
    assert company.name == "Apple Inc."
    assert [filing.form_type for filing in filings] == ["10-K", "10-Q"]
    assert filings[0].accession_number == "0000320193-24-000123"
    assert filings[0].filing_date == date(2024, 11, 1)
    assert filings[0].report_date == date(2024, 9, 28)
    assert filings[0].fiscal_year == 2024
    assert filings[0].source_url.endswith("/320193/000032019324000123/aapl-20240928.htm")


def test_normalize_company_facts_flattens_units_and_concepts() -> None:
    company_facts = json.loads((FIXTURE_DIR / "companyfacts_aapl.json").read_text())

    facts = normalize_company_facts(company_facts)

    assert len(facts) == 3
    revenue = next(fact for fact in facts if fact.concept == "Revenues" and fact.fiscal_period == "FY")
    assert revenue.cik == "0000320193"
    assert revenue.value == Decimal("391035000000")
    assert revenue.fiscal_year == 2024
    assert revenue.fiscal_quarter is None
    assert revenue.source_key

