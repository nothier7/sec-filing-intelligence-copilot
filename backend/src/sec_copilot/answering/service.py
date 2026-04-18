from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from sec_copilot.answering.classifier import classify_query
from sec_copilot.answering.models import (
    AskRequest,
    AskResponse,
    Citation,
    NumericGrounding,
    NumericGroundingStatus,
    QueryType,
)
from sec_copilot.answering.synthesis import (
    best_evidence_snippet,
    has_numeric_evidence,
    insufficient_evidence_answer,
    metric_clarification_answer,
    synthesize_extractive_answer,
    synthesize_numeric_fact_answer,
    unsupported_answer,
)
from sec_copilot.db.models import XbrlFact
from sec_copilot.facts import FactLookupRequest, FactLookupResult, FactLookupService
from sec_copilot.facts.service import format_fact_value
from sec_copilot.retrieval import HashEmbedding, RetrievalFilters, RetrievalIndexService, RetrievalResult


class CitedAnswerService:
    def __init__(
        self,
        session: Session,
        embed_model: Optional[HashEmbedding] = None,
        min_similarity_score: float = 0.05,
        enable_numeric_grounding: bool = True,
    ) -> None:
        self.retrieval = RetrievalIndexService(session=session, embed_model=embed_model)
        self.fact_lookup = FactLookupService(session=session)
        self.min_similarity_score = min_similarity_score
        self.enable_numeric_grounding = enable_numeric_grounding

    def answer(self, request: AskRequest) -> AskResponse:
        query_type = classify_query(request.question)
        if query_type == QueryType.UNSUPPORTED:
            return AskResponse(
                question=request.question,
                answer=unsupported_answer(),
                query_type=query_type,
                supported=False,
                confidence=0.0,
                citations=[],
                retrieval_count=0,
                insufficient_evidence_reason="unsupported_query_type",
            )

        filing = self.retrieval.filings.get_by_accession_number(request.accession_number)
        if filing is None:
            raise ValueError(f"Filing not found: {request.accession_number}")

        fact_lookup = None
        if query_type == QueryType.NUMERIC and self.enable_numeric_grounding:
            fact_lookup = self.fact_lookup.lookup(
                FactLookupRequest(
                    question=request.question,
                    filing=filing,
                    fiscal_year=request.fiscal_year,
                    fiscal_quarter=request.fiscal_quarter,
                    form_type=request.form_type,
                )
            )

        results = self.retrieval.retrieve_for_filing(
            filing_id=filing.id,
            query=request.question,
            top_k=request.top_k,
            filters=RetrievalFilters(
                accession_number=request.accession_number,
                cik=request.cik,
                form_type=request.form_type,
                fiscal_year=request.fiscal_year,
                fiscal_quarter=request.fiscal_quarter,
                section_type=request.section_type,
            ),
        )
        strong_results = self._strong_results(results)
        citations = [self._citation_for_result(request.question, result) for result in strong_results]
        snippets = [citation.snippet for citation in citations]
        numeric_grounding = self._numeric_grounding(fact_lookup, snippets)

        insufficient_reason = self._insufficient_reason(
            query_type=query_type,
            results=strong_results,
            snippets=snippets,
            numeric_grounding=numeric_grounding,
        )
        if insufficient_reason is not None:
            return AskResponse(
                question=request.question,
                answer=(
                    metric_clarification_answer()
                    if insufficient_reason == "no_metric_match"
                    else insufficient_evidence_answer()
                ),
                query_type=query_type,
                supported=False,
                confidence=0.0,
                citations=citations,
                numeric_grounding=numeric_grounding,
                retrieval_count=len(results),
                insufficient_evidence_reason=insufficient_reason,
            )

        if query_type == QueryType.NUMERIC and fact_lookup is not None and fact_lookup.fact:
            fact = fact_lookup.fact
            value = format_fact_value(fact.value)
            return AskResponse(
                question=request.question,
                answer=synthesize_numeric_fact_answer(
                    metric_label=fact_lookup.metric.label if fact_lookup.metric else fact.concept,
                    value=value,
                    unit=fact.unit,
                    period=self._period_label(fact),
                    concept=fact.concept,
                ),
                query_type=query_type,
                supported=True,
                confidence=1.0,
                citations=citations,
                numeric_grounding=numeric_grounding,
                retrieval_count=len(results),
                insufficient_evidence_reason=None,
            )

        confidence = min(max((result.score or 0.0) for result in strong_results), 1.0)
        return AskResponse(
            question=request.question,
            answer=synthesize_extractive_answer(request.question, snippets),
            query_type=query_type,
            supported=True,
            confidence=confidence,
            citations=citations,
            numeric_grounding=numeric_grounding,
            retrieval_count=len(results),
            insufficient_evidence_reason=None,
        )

    def _strong_results(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        return [
            result
            for result in results
            if result.score is None or result.score >= self.min_similarity_score
        ]

    def _insufficient_reason(
        self,
        query_type: QueryType,
        results: list[RetrievalResult],
        snippets: list[str],
        numeric_grounding: list[NumericGrounding],
    ) -> Optional[str]:
        if not results:
            return "no_retrieved_evidence"
        if query_type == QueryType.NUMERIC:
            if not self.enable_numeric_grounding:
                if not has_numeric_evidence(snippets):
                    return "no_numeric_evidence"
                return None
            if not numeric_grounding:
                return "no_metric_match"
            status = numeric_grounding[0].status
            if status == NumericGroundingStatus.UNAVAILABLE:
                return numeric_grounding[0].reason or "structured_fact_unavailable"
            if status == NumericGroundingStatus.MISMATCHED:
                return "numeric_fact_mismatch"
        if query_type == QueryType.COMPARISON and len(results) < 2:
            return "not_enough_comparison_evidence"
        return None

    def _citation_for_result(self, question: str, result: RetrievalResult) -> Citation:
        metadata = result.metadata
        return Citation(
            chunk_id=result.chunk_id,
            accession_number=metadata.get("accession_number"),
            section_name=metadata.get("section_name"),
            section_type=metadata.get("section_type"),
            source_url=metadata.get("source_url"),
            source_start=metadata.get("source_start"),
            source_end=metadata.get("source_end"),
            score=result.score,
            snippet=best_evidence_snippet(question, result),
        )

    def _numeric_grounding(
        self,
        fact_lookup: Optional[FactLookupResult],
        snippets: list[str],
    ) -> list[NumericGrounding]:
        if fact_lookup is None:
            return []
        if fact_lookup.fact is None:
            return [
                NumericGrounding(
                    status=NumericGroundingStatus.UNAVAILABLE,
                    metric=fact_lookup.metric.key if fact_lookup.metric else None,
                    metric_label=fact_lookup.metric.label if fact_lookup.metric else None,
                    reason=fact_lookup.reason,
                )
            ]

        fact = fact_lookup.fact
        status = NumericGroundingStatus.VALIDATED
        reason = None
        if self._has_conflicting_numeric_snippet(fact, snippets):
            status = NumericGroundingStatus.MISMATCHED
            reason = "retrieved_numeric_text_does_not_match_structured_fact"

        return [
            NumericGrounding(
                status=status,
                metric=fact_lookup.metric.key if fact_lookup.metric else fact.concept,
                metric_label=fact_lookup.metric.label if fact_lookup.metric else fact.concept,
                concept=fact.concept,
                label=fact.label,
                value=format_fact_value(fact.value),
                unit=fact.unit,
                fiscal_year=fact.fiscal_year,
                fiscal_quarter=fact.fiscal_quarter,
                fiscal_period=fact.fiscal_period,
                form_type=fact.form_type,
                filed_date=fact.filed_date,
                accession_number=fact.accession_number,
                source_key=fact.source_key,
                reason=reason,
            )
        ]

    def _has_conflicting_numeric_snippet(self, fact: XbrlFact, snippets: list[str]) -> bool:
        observed_numbers = _large_numeric_tokens(snippets)
        if not observed_numbers:
            return False
        fact_digits = "".join(character for character in format_fact_value(fact.value) if character.isdigit())
        return fact_digits not in observed_numbers

    def _period_label(self, fact: XbrlFact) -> str:
        if fact.fiscal_period:
            if fact.fiscal_year is not None:
                return f"{fact.fiscal_period} {fact.fiscal_year}"
            return fact.fiscal_period
        if fact.fiscal_quarter is not None and fact.fiscal_year is not None:
            return f"Q{fact.fiscal_quarter} {fact.fiscal_year}"
        if fact.fiscal_year is not None:
            return f"FY {fact.fiscal_year}"
        return "the matched period"


def _large_numeric_tokens(snippets: list[str]) -> set[str]:
    tokens: set[str] = set()
    for snippet in snippets:
        for raw_token in snippet.replace(",", "").split():
            digits = "".join(character for character in raw_token if character.isdigit())
            if len(digits) < 5:
                continue
            tokens.add(digits)
    return tokens
