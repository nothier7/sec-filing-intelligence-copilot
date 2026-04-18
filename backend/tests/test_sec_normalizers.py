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


def test_normalize_recent_filings_prefers_sec_fiscal_period_fields() -> None:
    submissions = {
        "cik": 320193,
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000006"],
                "form": ["10-Q"],
                "filingDate": ["2026-01-30"],
                "reportDate": ["2025-12-27"],
                "primaryDocument": ["aapl-20251227.htm"],
                "fy": [2026],
                "fp": ["Q1"],
            }
        },
    }

    filing = normalize_recent_filings(submissions, form_types=("10-Q",))[0]

    assert filing.fiscal_year == 2026
    assert filing.fiscal_quarter == 1


def test_normalize_recent_filings_infers_fiscal_period_from_year_end() -> None:
    submissions = {
        "cik": 320193,
        "fiscalYearEnd": "0926",
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0000320193-26-000006",
                    "0000320193-25-000079",
                ],
                "form": ["10-Q", "10-K"],
                "filingDate": ["2026-01-30", "2025-10-31"],
                "reportDate": ["2025-12-27", "2025-09-27"],
                "primaryDocument": ["aapl-20251227.htm", "aapl-20250927.htm"],
            }
        },
    }

    filings = normalize_recent_filings(submissions, form_types=("10-K", "10-Q"))

    assert filings[0].fiscal_year == 2026
    assert filings[0].fiscal_quarter == 1
    assert filings[1].fiscal_year == 2025
    assert filings[1].fiscal_quarter is None


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
