from collections.abc import Generator
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sec_copilot.comparison import CompareRequest, FilingComparisonService
from sec_copilot.db.models import Chunk, Company, Filing
from sec_copilot.main import app, get_db_session
from sec_copilot.repositories import CompanyRepository, FilingRepository


def test_comparison_service_returns_added_removed_and_prior_citations(session: Session) -> None:
    _create_comparable_filings(session)

    response = FilingComparisonService(session=session).compare(
        CompareRequest(
            accession_number="0000320193-24-000124",
            section_type="risk_factors",
        )
    )

    assert response.supported is True
    assert response.prior_accession_number == "0000320193-23-000123"
    assert response.unchanged_claim_count == 1
    assert response.added_claims[0].text == (
        "New artificial intelligence regulations may increase compliance costs."
    )
    assert response.added_claims[0].citations[0].filing_role == "current"
    assert response.removed_claims[0].text == (
        "The company relies on a limited number of third-party suppliers."
    )
    assert response.removed_claims[0].citations[0].filing_role == "prior"
    assert {citation.filing_role for citation in response.citations} == {"current", "prior"}


def test_comparison_service_uses_explicit_prior_accession(session: Session) -> None:
    _create_comparable_filings(session)

    response = FilingComparisonService(session=session).compare(
        CompareRequest(
            accession_number="0000320193-24-000124",
            previous_accession_number="0000320193-23-000123",
            section_type="risk_factors",
        )
    )

    assert response.supported is True
    assert response.summary.startswith(
        "Compared risk_factors in 0000320193-24-000124 against 0000320193-23-000123"
    )


def test_comparison_service_handles_missing_prior_filing(session: Session) -> None:
    _create_single_parsed_filing(session)

    response = FilingComparisonService(session=session).compare(
        CompareRequest(
            accession_number="0000320193-24-000124",
            section_type="risk_factors",
        )
    )

    assert response.supported is False
    assert response.insufficient_evidence_reason == "previous_filing_missing"
    assert response.citations == []


def test_comparison_service_handles_missing_prior_section(session: Session) -> None:
    current, prior = _create_comparable_filings(session)
    _add_section_with_chunk(
        session=session,
        filing=current,
        section_type="mda",
        text="Current management discusses liquidity and operating expenses.",
        sequence=2,
    )
    session.commit()

    response = FilingComparisonService(session=session).compare(
        CompareRequest(
            accession_number=current.accession_number,
            section_type="mda",
        )
    )

    assert response.supported is False
    assert response.prior_accession_number == prior.accession_number
    assert response.insufficient_evidence_reason == "prior_section_missing"


def test_compare_endpoint_serializes_change_citations(session: Session) -> None:
    _create_comparable_filings(session)

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).post(
            "/compare",
            json={
                "accession_number": "0000320193-24-000124",
                "section_type": "risk_factors",
                "max_claims": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is True
    assert payload["added_claims"][0]["citations"][0]["filing_role"] == "current"
    assert payload["removed_claims"][0]["citations"][0]["filing_role"] == "prior"


def test_compare_endpoint_returns_404_for_missing_current_filing(session: Session) -> None:
    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).post(
            "/compare",
            json={
                "accession_number": "missing-filing",
                "section_type": "risk_factors",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Filing not found: missing-filing"


def _create_comparable_filings(session: Session) -> tuple[Filing, Filing]:
    company = CompanyRepository(session).add(
        Company(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    filing_repository = FilingRepository(session)
    prior = filing_repository.add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-23-000123",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2023, 11, 1),
            report_date=date(2023, 9, 30),
            fiscal_year=2023,
            source_url="https://www.sec.gov/Archives/prior.htm",
        )
    )
    current = filing_repository.add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-24-000124",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2024, 11, 1),
            report_date=date(2024, 9, 28),
            fiscal_year=2024,
            source_url="https://www.sec.gov/Archives/current.htm",
        )
    )
    _add_section_with_chunk(
        session=session,
        filing=prior,
        section_type="risk_factors",
        text=(
            "Supply chain constraints may affect operations. "
            "The company relies on a limited number of third-party suppliers."
        ),
        sequence=1,
    )
    _add_section_with_chunk(
        session=session,
        filing=current,
        section_type="risk_factors",
        text=(
            "Supply chain constraints may affect operations. "
            "New artificial intelligence regulations may increase compliance costs."
        ),
        sequence=1,
    )
    session.commit()
    return current, prior


def _create_single_parsed_filing(session: Session) -> Filing:
    company = CompanyRepository(session).add(
        Company(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    filing = FilingRepository(session).add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-24-000124",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2024, 11, 1),
            report_date=date(2024, 9, 28),
            fiscal_year=2024,
            source_url="https://www.sec.gov/Archives/current.htm",
        )
    )
    _add_section_with_chunk(
        session=session,
        filing=filing,
        section_type="risk_factors",
        text="Supply chain constraints may affect operations.",
        sequence=1,
    )
    session.commit()
    return filing


def _add_section_with_chunk(
    session: Session,
    filing: Filing,
    section_type: str,
    text: str,
    sequence: int,
) -> None:
    section = FilingRepository(session).add_section(
        filing_id=filing.id,
        section_name="Item 1A. Risk Factors" if section_type == "risk_factors" else "Item 7. MD&A",
        normalized_section_type=section_type,
        sequence=sequence,
        text_hash=f"{filing.accession_number}-{section_type}",
    )
    session.add(
        Chunk(
            id=f"{filing.accession_number}:s{sequence:04d}:c0001",
            filing_id=filing.id,
            section_id=section.id,
            text=text,
            token_count=len(text.split()),
            metadata_json={
                "accession_number": filing.accession_number,
                "section_name": section.section_name,
                "section_type": section_type,
                "source_url": filing.source_url,
            },
            source_start=100 * sequence,
            source_end=100 * sequence + len(text),
        )
    )
