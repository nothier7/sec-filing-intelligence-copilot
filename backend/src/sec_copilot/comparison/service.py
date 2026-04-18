from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from sec_copilot.comparison.diff import SectionClaim, diff_claims, extract_claims
from sec_copilot.comparison.models import (
    ChangeCitation,
    ChangeClaim,
    ChangeType,
    CompareRequest,
    CompareResponse,
)
from sec_copilot.db.models import Filing, FilingSection
from sec_copilot.repositories import ChunkRepository, FilingRepository


class FilingComparisonService:
    def __init__(self, session: Session) -> None:
        self.filings = FilingRepository(session)
        self.chunks = ChunkRepository(session)

    def compare(self, request: CompareRequest) -> CompareResponse:
        current_filing = self.filings.get_by_accession_number(request.accession_number)
        if current_filing is None:
            raise ValueError(f"Filing not found: {request.accession_number}")

        current_section = self.filings.get_section_by_type(
            current_filing.id,
            request.section_type,
        )
        if current_section is None:
            return self._unsupported(
                request=request,
                current_filing=current_filing,
                prior_filing=None,
                reason="current_section_missing",
            )

        prior_filing = self._prior_filing(current_filing, request.previous_accession_number)
        if prior_filing is None:
            return self._unsupported(
                request=request,
                current_filing=current_filing,
                prior_filing=None,
                reason="previous_filing_missing",
            )

        prior_section = self.filings.get_section_by_type(prior_filing.id, request.section_type)
        if prior_section is None:
            return self._unsupported(
                request=request,
                current_filing=current_filing,
                prior_filing=prior_filing,
                reason="prior_section_missing",
            )

        current_claims = self._claims_for_section(
            filing=current_filing,
            section=current_section,
            filing_role="current",
        )
        prior_claims = self._claims_for_section(
            filing=prior_filing,
            section=prior_section,
            filing_role="prior",
        )
        if not current_claims or not prior_claims:
            return self._unsupported(
                request=request,
                current_filing=current_filing,
                prior_filing=prior_filing,
                reason="section_chunks_missing",
            )

        section_diff = diff_claims(current_claims=current_claims, prior_claims=prior_claims)
        added = [
            self._change_claim(ChangeType.ADDED, claim)
            for claim in section_diff.added[: request.max_claims]
        ]
        removed = [
            self._change_claim(ChangeType.REMOVED, claim)
            for claim in section_diff.removed[: request.max_claims]
        ]
        citations = self._comparison_citations(
            current_claims=current_claims,
            prior_claims=prior_claims,
            added=added,
            removed=removed,
        )
        summary = self._summary(
            section_type=request.section_type,
            current_accession=current_filing.accession_number,
            prior_accession=prior_filing.accession_number,
            added_count=len(section_diff.added),
            removed_count=len(section_diff.removed),
            unchanged_count=section_diff.unchanged_count,
        )

        return CompareResponse(
            current_accession_number=current_filing.accession_number,
            prior_accession_number=prior_filing.accession_number,
            section_type=request.section_type,
            supported=True,
            summary=summary,
            added_claims=added,
            removed_claims=removed,
            unchanged_claim_count=section_diff.unchanged_count,
            citations=citations,
        )

    def _prior_filing(
        self,
        current_filing: Filing,
        previous_accession_number: Optional[str],
    ) -> Optional[Filing]:
        if previous_accession_number:
            return self.filings.get_by_accession_number(previous_accession_number)
        return self.filings.get_previous_filing(current_filing)

    def _claims_for_section(
        self,
        filing: Filing,
        section: FilingSection,
        filing_role: str,
    ) -> list[SectionClaim]:
        return extract_claims(
            filing=filing,
            section=section,
            chunks=list(self.chunks.list_for_section(section.id)),
            filing_role=filing_role,
        )

    def _unsupported(
        self,
        request: CompareRequest,
        current_filing: Filing,
        prior_filing: Optional[Filing],
        reason: str,
    ) -> CompareResponse:
        return CompareResponse(
            current_accession_number=current_filing.accession_number,
            prior_accession_number=prior_filing.accession_number if prior_filing else None,
            section_type=request.section_type,
            supported=False,
            summary="I do not have enough comparable filing evidence to summarize changes.",
            insufficient_evidence_reason=reason,
        )

    def _change_claim(self, change_type: ChangeType, claim: SectionClaim) -> ChangeClaim:
        return ChangeClaim(
            change_type=change_type,
            text=claim.text,
            citations=[claim.citation],
        )

    def _comparison_citations(
        self,
        current_claims: list[SectionClaim],
        prior_claims: list[SectionClaim],
        added: list[ChangeClaim],
        removed: list[ChangeClaim],
    ) -> list[ChangeCitation]:
        citations = [citation for claim in added + removed for citation in claim.citations]
        if not any(citation.filing_role == "current" for citation in citations) and current_claims:
            citations.append(current_claims[0].citation)
        if not any(citation.filing_role == "prior" for citation in citations) and prior_claims:
            citations.append(prior_claims[0].citation)
        return citations

    def _summary(
        self,
        section_type: str,
        current_accession: str,
        prior_accession: str,
        added_count: int,
        removed_count: int,
        unchanged_count: int,
    ) -> str:
        return (
            f"Compared {section_type} in {current_accession} against {prior_accession}: "
            f"{added_count} added claim(s), {removed_count} removed claim(s), "
            f"and {unchanged_count} unchanged claim(s)."
        )
