from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from sec_copilot.answering.classifier import classify_query
from sec_copilot.answering.models import AskRequest, AskResponse, Citation, QueryType
from sec_copilot.answering.synthesis import (
    best_evidence_snippet,
    has_numeric_evidence,
    insufficient_evidence_answer,
    synthesize_extractive_answer,
    unsupported_answer,
)
from sec_copilot.retrieval import HashEmbedding, RetrievalFilters, RetrievalIndexService, RetrievalResult


class CitedAnswerService:
    def __init__(
        self,
        session: Session,
        embed_model: Optional[HashEmbedding] = None,
        min_similarity_score: float = 0.05,
    ) -> None:
        self.retrieval = RetrievalIndexService(session=session, embed_model=embed_model)
        self.min_similarity_score = min_similarity_score

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

        insufficient_reason = self._insufficient_reason(query_type, strong_results, snippets)
        if insufficient_reason is not None:
            return AskResponse(
                question=request.question,
                answer=insufficient_evidence_answer(),
                query_type=query_type,
                supported=False,
                confidence=0.0,
                citations=citations,
                retrieval_count=len(results),
                insufficient_evidence_reason=insufficient_reason,
            )

        confidence = min(max((result.score or 0.0) for result in strong_results), 1.0)
        return AskResponse(
            question=request.question,
            answer=synthesize_extractive_answer(request.question, snippets),
            query_type=query_type,
            supported=True,
            confidence=confidence,
            citations=citations,
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
    ) -> Optional[str]:
        if not results:
            return "no_retrieved_evidence"
        if query_type == QueryType.NUMERIC and not has_numeric_evidence(snippets):
            return "no_numeric_evidence"
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
