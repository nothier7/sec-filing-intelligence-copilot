from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Optional

from sqlalchemy.orm import Session

from sec_copilot.answering import AskRequest, CitedAnswerService, classify_query
from sec_copilot.answering.models import QueryType
from sec_copilot.answering.synthesis import insufficient_evidence_answer, unsupported_answer
from sec_copilot.evals.dataset import load_eval_questions
from sec_copilot.evals.metrics import aggregate_metrics, score_prediction
from sec_copilot.evals.models import (
    EvalPrediction,
    EvalQuestion,
    EvalQuestionResult,
    EvalRunResult,
    EvalVariant,
)
from sec_copilot.retrieval import HashEmbedding


DEFAULT_VARIANTS = [
    EvalVariant.CLOSED_BOOK,
    EvalVariant.NAIVE_RAG,
    EvalVariant.IMPROVED_RAG,
    EvalVariant.IMPROVED_RAG_XBRL,
]


class EvaluationRunner:
    def __init__(
        self,
        session: Session,
        embed_model: Optional[HashEmbedding] = None,
    ) -> None:
        self.session = session
        self.embed_model = embed_model

    def run(
        self,
        dataset_path: Path,
        variants: Optional[list[EvalVariant]] = None,
    ) -> EvalRunResult:
        selected_variants = variants or DEFAULT_VARIANTS
        questions = load_eval_questions(dataset_path)
        question_results: list[EvalQuestionResult] = []
        scores_by_variant: dict[EvalVariant, list[dict[str, float]]] = {
            variant: [] for variant in selected_variants
        }

        for question in questions:
            predictions: dict[EvalVariant, EvalPrediction] = {}
            metrics: dict[EvalVariant, dict[str, float]] = {}
            for variant in selected_variants:
                prediction = self._predict(question=question, variant=variant)
                score = score_prediction(question, prediction)
                predictions[variant] = prediction
                metrics[variant] = score
                scores_by_variant[variant].append(score)

            question_results.append(
                EvalQuestionResult(
                    question=question,
                    predictions=predictions,
                    metrics=metrics,
                )
            )

        return EvalRunResult(
            generated_at=datetime.utcnow(),
            dataset_path=dataset_path.as_posix(),
            variants=selected_variants,
            question_count=len(questions),
            metrics={
                variant: aggregate_metrics(scores)
                for variant, scores in scores_by_variant.items()
            },
            results=question_results,
        )

    def _predict(self, question: EvalQuestion, variant: EvalVariant) -> EvalPrediction:
        started_at = perf_counter()
        try:
            if variant == EvalVariant.CLOSED_BOOK:
                return self._closed_book_prediction(question, started_at)
            return self._rag_prediction(question, variant, started_at)
        except Exception as exc:  # noqa: BLE001 - eval runs should capture failures per example.
            return EvalPrediction(
                question_id=question.id,
                variant=variant,
                supported=False,
                answer=insufficient_evidence_answer(),
                latency_ms=_elapsed_ms(started_at),
                error=str(exc),
                insufficient_evidence_reason="eval_variant_error",
            )

    def _closed_book_prediction(
        self,
        question: EvalQuestion,
        started_at: float,
    ) -> EvalPrediction:
        query_type = classify_query(question.question)
        is_unsupported = query_type == QueryType.UNSUPPORTED
        return EvalPrediction(
            question_id=question.id,
            variant=EvalVariant.CLOSED_BOOK,
            supported=False,
            answer=unsupported_answer() if is_unsupported else insufficient_evidence_answer(),
            retrieval_count=0,
            insufficient_evidence_reason=(
                "unsupported_query_type" if is_unsupported else "closed_book_no_filing_context"
            ),
            latency_ms=_elapsed_ms(started_at),
        )

    def _rag_prediction(
        self,
        question: EvalQuestion,
        variant: EvalVariant,
        started_at: float,
    ) -> EvalPrediction:
        use_improved_filters = variant in {
            EvalVariant.IMPROVED_RAG,
            EvalVariant.IMPROVED_RAG_XBRL,
        }
        response = CitedAnswerService(
            session=self.session,
            embed_model=self.embed_model,
            enable_numeric_grounding=variant == EvalVariant.IMPROVED_RAG_XBRL,
        ).answer(
            AskRequest(
                question=question.question,
                accession_number=question.accession_number,
                top_k=question.top_k,
                cik=question.cik if use_improved_filters else None,
                form_type=question.form_type if use_improved_filters else None,
                fiscal_year=question.fiscal_year if use_improved_filters else None,
                fiscal_quarter=question.fiscal_quarter if use_improved_filters else None,
                section_type=question.section_type if use_improved_filters else None,
            )
        )
        return EvalPrediction(
            question_id=question.id,
            variant=variant,
            supported=response.supported,
            answer=response.answer,
            citations=response.citations,
            numeric_grounding=response.numeric_grounding,
            retrieval_count=response.retrieval_count,
            insufficient_evidence_reason=response.insufficient_evidence_reason,
            latency_ms=_elapsed_ms(started_at),
        )


def parse_variants(raw_variants: Optional[list[str]]) -> list[EvalVariant]:
    if not raw_variants:
        return DEFAULT_VARIANTS
    return [EvalVariant(raw_variant) for raw_variant in raw_variants]


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000.0
