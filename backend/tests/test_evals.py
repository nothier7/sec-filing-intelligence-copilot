from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from sec_copilot.db.models import Company, Filing, XbrlFact
from sec_copilot.evals import EvaluationRunner, EvalVariant, format_eval_report, load_eval_questions
from sec_copilot.filings import FilingParseService
from sec_copilot.repositories import CompanyRepository, FilingRepository, XbrlFactRepository
from sec_copilot.retrieval import HashEmbedding

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_eval_questions_from_jsonl() -> None:
    questions = load_eval_questions(REPO_ROOT / "evals" / "questions" / "sec_seed.jsonl")

    assert len(questions) == 4
    assert questions[0].id == "sec_seed_text_risk_001"
    assert questions[0].expected.citation_chunk_ids == ["0000320193-24-000123:s0002:c0001"]


def test_evaluation_runner_compares_rag_variants(session: Session) -> None:
    filing_id = _create_parsed_fixture_filing(session)
    _add_revenue_fact(session, filing_id)

    result = EvaluationRunner(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).run(
        dataset_path=REPO_ROOT / "evals" / "questions" / "sec_seed.jsonl",
        variants=[
            EvalVariant.CLOSED_BOOK,
            EvalVariant.IMPROVED_RAG,
            EvalVariant.IMPROVED_RAG_XBRL,
        ],
    )

    assert result.question_count == 4
    assert result.metrics[EvalVariant.CLOSED_BOOK]["accuracy"] < result.metrics[
        EvalVariant.IMPROVED_RAG_XBRL
    ]["accuracy"]
    assert result.metrics[EvalVariant.CLOSED_BOOK]["refusal_accuracy"] == 1.0
    assert result.metrics[EvalVariant.IMPROVED_RAG]["numeric_accuracy"] == 0.0
    assert result.metrics[EvalVariant.IMPROVED_RAG_XBRL]["numeric_accuracy"] == 1.0
    assert "improved_rag_xbrl" in result.model_dump_json()


def test_eval_report_includes_ablation_table(session: Session) -> None:
    filing_id = _create_parsed_fixture_filing(session)
    _add_revenue_fact(session, filing_id)
    result = EvaluationRunner(
        session=session,
        embed_model=HashEmbedding(dimensions=32),
    ).run(
        dataset_path=REPO_ROOT / "evals" / "questions" / "sec_seed.jsonl",
        variants=[EvalVariant.CLOSED_BOOK, EvalVariant.IMPROVED_RAG_XBRL],
    )

    report = format_eval_report(result)

    assert "## Headline Metrics" in report
    assert "improved rag xbrl" in report
    assert "| Variant | Accuracy | Numeric Accuracy |" in report


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
    filing = FilingRepository(session).get(filing_id)
    assert filing is not None
    XbrlFactRepository(session).add(
        XbrlFact(
            source_key=f"{filing.accession_number}-revenue-fy2024",
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
            form_type=filing.form_type,
            filed_date=filing.filing_date,
        )
    )
    session.commit()
