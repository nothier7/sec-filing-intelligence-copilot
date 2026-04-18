from collections.abc import Generator
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sec_copilot.answering import AskRequest, CitedAnswerService, QueryType, classify_query
from sec_copilot.db.models import Chunk, Company, Filing, XbrlFact
from sec_copilot.filings import FilingParseService
from sec_copilot.main import app, get_db_session
from sec_copilot.repositories import CompanyRepository, FilingRepository, XbrlFactRepository
from sec_copilot.retrieval import HashEmbedding

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_classify_query_types() -> None:
    assert classify_query("What are the main regulatory risks?") == QueryType.TEXT
    assert classify_query("How much revenue did the company report?") == QueryType.NUMERIC
    assert classify_query("What were operating expenses?") == QueryType.NUMERIC
    assert classify_query("What changed compared with the prior filing?") == QueryType.COMPARISON
    assert classify_query("Should I buy this stock?") == QueryType.UNSUPPORTED


def test_cited_answer_service_returns_supported_answer_with_citations(session: Session) -> None:
    _create_parsed_fixture_filing(session)

    response = CitedAnswerService(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).answer(
        AskRequest(
            accession_number="0000320193-24-000123",
            question="What supply chain regulatory risks are described?",
            section_type="risk_factors",
            top_k=2,
        )
    )

    assert response.supported is True
    assert response.query_type == QueryType.TEXT
    assert response.citations
    assert response.citations[0].chunk_id == "0000320193-24-000123:s0002:c0001"
    assert response.citations[0].section_type == "risk_factors"
    assert "supply chain" in response.answer


def test_cited_answer_service_marks_numeric_question_without_numbers_insufficient(
    session: Session,
) -> None:
    _create_parsed_fixture_filing(session)

    response = CitedAnswerService(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).answer(
        AskRequest(
            accession_number="0000320193-24-000123",
            question="How much revenue came from supply chain risks?",
            section_type="risk_factors",
            top_k=2,
        )
    )

    assert response.supported is False
    assert response.query_type == QueryType.NUMERIC
    assert response.insufficient_evidence_reason == "fact_not_found"
    assert response.numeric_grounding[0].status == "unavailable"
    assert response.citations


def test_cited_answer_service_uses_structured_xbrl_fact_for_numeric_answer(
    session: Session,
) -> None:
    filing_id = _create_parsed_fixture_filing(session)
    _add_revenue_fact(session, filing_id)

    response = CitedAnswerService(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).answer(
        AskRequest(
            accession_number="0000320193-24-000123",
            question="How much revenue did Apple report in 2024?",
            top_k=2,
        )
    )

    assert response.supported is True
    assert response.query_type == QueryType.NUMERIC
    assert response.confidence == 1.0
    assert "383,285,000,000 USD" in response.answer
    assert response.numeric_grounding[0].status == "validated"
    assert response.numeric_grounding[0].metric == "revenue"
    assert response.numeric_grounding[0].concept == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert response.numeric_grounding[0].value == "383,285,000,000"


def test_cited_answer_service_asks_for_specific_spending_metric(session: Session) -> None:
    _create_parsed_fixture_filing(session)

    response = CitedAnswerService(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).answer(
        AskRequest(
            accession_number="0000320193-24-000123",
            question="How much did Apple spend in 2024?",
            top_k=2,
        )
    )

    assert response.supported is False
    assert response.query_type == QueryType.NUMERIC
    assert response.insufficient_evidence_reason == "no_metric_match"
    assert "specific financial metric" in response.answer
    assert "capital expenditures" in response.answer


def test_cited_answer_service_uses_structured_spending_fact_for_specific_metric(
    session: Session,
) -> None:
    filing_id = _create_parsed_fixture_filing(session)
    _add_xbrl_fact(
        session=session,
        filing_id=filing_id,
        concept="ResearchAndDevelopmentExpense",
        label="Research and Development Expense",
        value=Decimal("31370000000"),
        source_suffix="rd-fy2024",
    )

    response = CitedAnswerService(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).answer(
        AskRequest(
            accession_number="0000320193-24-000123",
            question="How much did Apple spend on R&D in 2024?",
            top_k=2,
        )
    )

    assert response.supported is True
    assert "31,370,000,000 USD" in response.answer
    assert response.numeric_grounding[0].metric == "research_and_development"
    assert response.numeric_grounding[0].concept == "ResearchAndDevelopmentExpense"


def test_cited_answer_service_flags_numeric_fact_mismatch(session: Session) -> None:
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
    section = FilingRepository(session).add_section(
        filing_id=filing.id,
        section_name="Item 7. MD&A",
        normalized_section_type="mda",
        sequence=1,
        text_hash="mda-hash",
    )
    session.add(
        Chunk(
            id="0000320193-24-000123:s0001:c0001",
            filing_id=filing.id,
            section_id=section.id,
            text="The filing text says revenue was 999,000,000 in 2024.",
            token_count=9,
            metadata_json={
                "accession_number": filing.accession_number,
                "cik": filing.cik,
                "fiscal_year": 2024,
                "form_type": "10-K",
                "section_name": "Item 7. MD&A",
                "section_type": "mda",
                "source_url": filing.source_url,
            },
            source_start=0,
            source_end=58,
        )
    )
    session.commit()
    _add_revenue_fact(session, filing.id)

    response = CitedAnswerService(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).answer(
        AskRequest(
            accession_number="0000320193-24-000123",
            question="How much revenue did Apple report in 2024?",
            top_k=1,
        )
    )

    assert response.supported is False
    assert response.insufficient_evidence_reason == "numeric_fact_mismatch"
    assert response.numeric_grounding[0].status == "mismatched"


def test_cited_answer_service_refuses_unsupported_investment_advice(session: Session) -> None:
    response = CitedAnswerService(session=session).answer(
        AskRequest(
            accession_number="missing-filing",
            question="Should I buy this stock?",
        )
    )

    assert response.supported is False
    assert response.query_type == QueryType.UNSUPPORTED
    assert response.citations == []
    assert response.insufficient_evidence_reason == "unsupported_query_type"


def test_ask_endpoint_serializes_citations(session: Session) -> None:
    _create_parsed_fixture_filing(session)

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).post(
            "/ask",
            json={
                "accession_number": "0000320193-24-000123",
                "question": "What supply chain regulatory risks are described?",
                "section_type": "risk_factors",
                "top_k": 1,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is True
    assert payload["query_type"] == "text"
    assert payload["numeric_grounding"] == []
    assert payload["citations"][0]["chunk_id"] == "0000320193-24-000123:s0002:c0001"
    assert payload["citations"][0]["source_url"] == "https://www.sec.gov/Archives/example.htm"


def test_ask_endpoint_returns_404_for_missing_filing(session: Session) -> None:
    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).post(
            "/ask",
            json={
                "accession_number": "missing-filing",
                "question": "What are the risk factors?",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Filing not found: missing-filing"


def _create_parsed_fixture_filing(session: Session) -> int:
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
            raw_artifact_path=(FIXTURE_DIR / "aapl-20240928.htm").as_posix(),
        )
    )
    session.commit()

    FilingParseService(session=session, max_tokens=12, overlap_tokens=2).parse_filing(filing.id)
    session.commit()
    return filing.id


def _add_revenue_fact(session: Session, filing_id: int) -> None:
    _add_xbrl_fact(
        session=session,
        filing_id=filing_id,
        concept="RevenueFromContractWithCustomerExcludingAssessedTax",
        label="Revenue",
        value=Decimal("383285000000"),
        source_suffix="revenue-fy2024",
    )


def _add_xbrl_fact(
    session: Session,
    filing_id: int,
    concept: str,
    label: str,
    value: Decimal,
    source_suffix: str,
) -> None:
    filing = FilingRepository(session).get(filing_id)
    assert filing is not None
    XbrlFactRepository(session).add(
        XbrlFact(
            source_key=f"{filing.accession_number}-{source_suffix}",
            company_id=filing.company_id,
            filing_id=filing.id,
            cik=filing.cik,
            accession_number=filing.accession_number,
            concept=concept,
            label=label,
            unit="USD",
            value=value,
            fiscal_period="FY",
            fiscal_year=2024,
            form_type=filing.form_type,
            filed_date=filing.filing_date,
        )
    )
    session.commit()
