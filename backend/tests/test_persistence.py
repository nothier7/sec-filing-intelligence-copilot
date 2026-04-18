from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from sec_copilot.db.models import (
    BenchmarkQuestion,
    Chunk,
    Company,
    EvalRun,
    Filing,
    XbrlFact,
)
from sec_copilot.repositories import (
    BenchmarkQuestionRepository,
    ChunkRepository,
    CompanyRepository,
    EvalRunRepository,
    FilingRepository,
    XbrlFactRepository,
)


def test_schema_contains_core_tables(session: Session) -> None:
    inspector = inspect(session.bind)

    assert set(inspector.get_table_names()) == {
        "benchmark_questions",
        "chunks",
        "companies",
        "eval_runs",
        "filing_sections",
        "filings",
        "xbrl_facts",
    }


def test_company_filing_section_and_chunk_repositories(session: Session) -> None:
    companies = CompanyRepository(session)
    filings = FilingRepository(session)
    chunks = ChunkRepository(session)

    company = companies.add(
        Company(
            cik="0000320193",
            ticker="AAPL",
            name="Apple Inc.",
            exchange="Nasdaq",
            sic="3571",
            fiscal_year_end="0928",
        )
    )
    filing = filings.add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-24-000123",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2024, 11, 1),
            report_date=date(2024, 9, 28),
            fiscal_year=2024,
            source_url="https://www.sec.gov/Archives/example.txt",
        )
    )
    section = filings.add_section(
        filing_id=filing.id,
        section_name="Item 1A. Risk Factors",
        normalized_section_type="risk_factors",
        sequence=1,
        text_hash="risk-hash",
    )
    chunk = chunks.add(
        Chunk(
            id="0000320193-24-000123:risk_factors:0001",
            filing_id=filing.id,
            section_id=section.id,
            text="The company faces supply chain and regulatory risks.",
            token_count=9,
            metadata_json={"section": "risk_factors", "form_type": "10-K"},
            source_start=100,
            source_end=168,
        )
    )

    session.commit()

    assert companies.get_by_cik("0000320193").id == company.id
    assert companies.get_by_ticker("AAPL").name == "Apple Inc."
    assert filings.get_by_accession_number("0000320193-24-000123").company_id == company.id
    assert list(filings.list_for_company(company.id, form_types=["10-K"])) == [filing]
    assert list(filings.list_sections(filing.id)) == [section]
    assert chunks.get(chunk.id).metadata_json["section"] == "risk_factors"
    assert list(chunks.list_for_filing(filing.id)) == [chunk]


def test_xbrl_fact_repository_filters_by_period(session: Session) -> None:
    company = CompanyRepository(session).add(
        Company(cik="0000789019", ticker="MSFT", name="Microsoft Corporation")
    )
    fact_repository = XbrlFactRepository(session)
    fact = fact_repository.add(
        XbrlFact(
            source_key="msft-revenues-2024-fy",
            company_id=company.id,
            cik=company.cik,
            concept="Revenues",
            label="Revenue",
            unit="USD",
            value=Decimal("245122000000"),
            fiscal_period="FY",
            fiscal_year=2024,
            form_type="10-K",
            filed_date=date(2024, 7, 30),
            frame="CY2024",
        )
    )

    session.commit()

    matches = fact_repository.find_by_concept(
        company_id=company.id,
        concept="Revenues",
        fiscal_year=2024,
    )

    assert list(matches) == [fact]
    assert fact.value == Decimal("245122000000")


def test_benchmark_question_and_eval_run_repositories(session: Session) -> None:
    question_repository = BenchmarkQuestionRepository(session)
    eval_repository = EvalRunRepository(session)

    question = question_repository.add(
        BenchmarkQuestion(
            question="What were the main risk factors?",
            question_type="section_lookup",
            expected_answer="Risk factors are disclosed in Item 1A.",
            expected_evidence={"sections": ["risk_factors"]},
            expected_facts={},
            metadata_json={"company": "AAPL"},
        )
    )
    eval_run = eval_repository.add(
        EvalRun(
            id="eval-2026-04-18-naive",
            system_variant="naive_rag",
            started_at=datetime(2026, 4, 18, 12, 0, 0),
            model_config={"model": "test-model"},
            retriever_config={"top_k": 5},
            metrics={"recall_at_5": 0.75},
            output_path="evals/results/eval-2026-04-18-naive.json",
        )
    )

    session.commit()

    assert list(question_repository.list_by_type("section_lookup")) == [question]
    assert eval_repository.get("eval-2026-04-18-naive") == eval_run
    assert list(eval_repository.list_by_variant("naive_rag")) == [eval_run]
