from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from sec_copilot.answering import Citation
from sec_copilot.answering.models import QueryType
from sec_copilot.config import Settings
from sec_copilot.db.models import Company, Filing, XbrlFact
from sec_copilot.evals import EvaluationRunner, EvalVariant, format_eval_report, load_eval_questions
from sec_copilot.evals.openai_baseline import (
    OpenAIEvalClient,
    OpenAIEvalRequest,
    _extract_web_citations,
    _insufficient_reason,
    _supports_reasoning,
)
from sec_copilot.evals.metrics import score_prediction
from sec_copilot.evals.models import EvalExpected, EvalPrediction, EvalQuestion
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


def test_numeric_value_scoring_handles_external_llm_answer_without_grounding() -> None:
    question = EvalQuestion(
        id="numeric",
        question="How much revenue did Apple report?",
        accession_number="0000320193-24-000123",
        expected=EvalExpected(
            xbrl_concepts=["RevenueFromContractWithCustomerExcludingAssessedTax"],
            numeric_value="383,285,000,000",
            numeric_unit="USD",
        ),
    )
    prediction = EvalPrediction(
        question_id=question.id,
        variant=EvalVariant.OPENAI_RETRIEVED_CONTEXT,
        supported=True,
        answer="Apple reported revenue of $383.285 billion.",
        citations=[
            Citation(
                chunk_id="chunk",
                snippet="Total net sales $ 383,285",
            )
        ],
        latency_ms=1.0,
    )

    score = score_prediction(question, prediction)

    assert score["numeric_match"] == 1.0
    assert score["numeric_grounding_match"] == 0.0
    assert score["answer_correct"] == 1.0


def test_openai_cache_key_includes_model_runtime_settings(tmp_path: Path) -> None:
    question = EvalQuestion(
        id="numeric",
        question="How much revenue did Apple report?",
        accession_number="0000320193-25-000079",
        expected=EvalExpected(supported=True),
    )
    settings = Settings(
        openai_eval_cache_dir=tmp_path.as_posix(),
        openai_eval_model="gpt-5-mini",
        openai_eval_max_output_tokens=800,
        openai_eval_reasoning_effort="minimal",
        openai_eval_context_chars=3500,
    )
    client = OpenAIEvalClient(settings=settings)
    request = OpenAIEvalRequest(question=question, variant=EvalVariant.OPENAI_CLOSED_BOOK)
    prompt = "Question: How much revenue did Apple report?"

    first_path = client._cache_path(
        request=request,
        prompt=prompt,
    )
    changed_budget_client = OpenAIEvalClient(
        settings=settings.model_copy(update={"openai_eval_max_output_tokens": 1200})
    )
    changed_reasoning_client = OpenAIEvalClient(
        settings=settings.model_copy(update={"openai_eval_reasoning_effort": "low"})
    )

    assert first_path != changed_budget_client._cache_path(
        request=request,
        prompt=prompt,
    )
    assert first_path != changed_reasoning_client._cache_path(
        request=request,
        prompt=prompt,
    )


def test_openai_reasoning_support_detection() -> None:
    assert _supports_reasoning("gpt-5-mini")
    assert _supports_reasoning("o4-mini")
    assert not _supports_reasoning("gpt-4.1-mini")


def test_openai_web_search_payload_uses_web_tool_and_low_reasoning(tmp_path: Path) -> None:
    question = EvalQuestion(
        id="web",
        question="How much revenue did Apple report in 2025?",
        accession_number="0000320193-25-000079",
        expected=EvalExpected(supported=True),
    )
    settings = Settings(
        openai_eval_cache_dir=tmp_path.as_posix(),
        openai_eval_model="gpt-5-mini",
        openai_eval_reasoning_effort="minimal",
        openai_eval_web_search_reasoning_effort="low",
        openai_eval_web_search_context_size="low",
        openai_eval_web_search_max_tool_calls=3,
    )
    client = OpenAIEvalClient(settings=settings)

    payload = client._payload_for(
        request=OpenAIEvalRequest(question=question, variant=EvalVariant.OPENAI_WEB_SEARCH),
        prompt="Question: How much revenue did Apple report in 2025?",
    )

    assert payload["tools"] == [{"type": "web_search", "search_context_size": "low"}]
    assert payload["tool_choice"] == "auto"
    assert payload["max_tool_calls"] == 3
    assert payload["include"] == ["web_search_call.action.sources"]
    assert payload["reasoning"] == {"effort": "low"}


def test_extract_web_citations_from_response_annotations() -> None:
    citations = _extract_web_citations(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Apple reported revenue.",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://www.sec.gov/example",
                                    "title": "Apple 10-K",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    assert len(citations) == 1
    assert citations[0].chunk_id.startswith("web:")
    assert citations[0].section_type == "web"
    assert citations[0].source_url == "https://www.sec.gov/example"
    assert citations[0].snippet == "Apple 10-K"


def test_openai_refusal_reason_handles_advice_and_metric_clarification() -> None:
    advice_question = EvalQuestion(
        id="advice",
        question="Should I buy Apple stock?",
        accession_number="0000320193-25-000079",
        expected=EvalExpected(supported=False),
    )
    spend_question = EvalQuestion(
        id="spend",
        question="How much did Apple spend in 2025?",
        accession_number="0000320193-25-000079",
        expected=EvalExpected(supported=False),
    )

    assert (
        _insufficient_reason(
            "I can’t tell you to buy or not.",
            QueryType.UNSUPPORTED,
            advice_question,
        )
        == "unsupported_query_type"
    )
    assert (
        _insufficient_reason(
            "Do you mean operating expenses or capital expenditures?",
            QueryType.NUMERIC,
            spend_question,
        )
        == "no_metric_match"
    )


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
    assert result.metrics[EvalVariant.IMPROVED_RAG]["numeric_grounding_accuracy"] == 0.0
    assert result.metrics[EvalVariant.IMPROVED_RAG_XBRL]["numeric_accuracy"] == 1.0
    assert result.metrics[EvalVariant.IMPROVED_RAG_XBRL]["numeric_grounding_accuracy"] == 1.0
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
    assert "| Variant | Accuracy | Numeric Accuracy | Grounded Numeric Accuracy |" in report


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
