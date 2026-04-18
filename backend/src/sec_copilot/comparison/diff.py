from __future__ import annotations

import re
from dataclasses import dataclass

from sec_copilot.comparison.models import ChangeCitation
from sec_copilot.db.models import Chunk, Filing, FilingSection

SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SectionClaim:
    text: str
    normalized_text: str
    citation: ChangeCitation


@dataclass(frozen=True)
class SectionDiff:
    added: list[SectionClaim]
    removed: list[SectionClaim]
    unchanged_count: int


def extract_claims(
    filing: Filing,
    section: FilingSection,
    chunks: list[Chunk],
    filing_role: str,
) -> list[SectionClaim]:
    claims: list[SectionClaim] = []
    seen: set[str] = set()
    for chunk in chunks:
        for fragment in _sentence_fragments(chunk.text):
            normalized = normalize_claim(fragment)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            claims.append(
                SectionClaim(
                    text=fragment,
                    normalized_text=normalized,
                    citation=ChangeCitation(
                        filing_role=filing_role,
                        accession_number=filing.accession_number,
                        chunk_id=chunk.id,
                        section_name=section.section_name,
                        section_type=section.normalized_section_type,
                        source_url=filing.source_url,
                        source_start=chunk.source_start,
                        source_end=chunk.source_end,
                        snippet=fragment,
                    ),
                )
            )
    return claims


def diff_claims(current_claims: list[SectionClaim], prior_claims: list[SectionClaim]) -> SectionDiff:
    prior_by_normalized = {claim.normalized_text: claim for claim in prior_claims}
    current_by_normalized = {claim.normalized_text: claim for claim in current_claims}

    added = [
        claim
        for claim in current_claims
        if claim.normalized_text not in prior_by_normalized
    ]
    removed = [
        claim
        for claim in prior_claims
        if claim.normalized_text not in current_by_normalized
    ]
    unchanged_count = len(set(current_by_normalized) & set(prior_by_normalized))
    return SectionDiff(added=added, removed=removed, unchanged_count=unchanged_count)


def normalize_claim(text: str) -> str:
    return NORMALIZE_PATTERN.sub(" ", text.lower()).strip()


def _sentence_fragments(text: str) -> list[str]:
    fragments = []
    for fragment in SENTENCE_BOUNDARY_PATTERN.split(text):
        cleaned = " ".join(fragment.split())
        if len(cleaned) < 8:
            continue
        fragments.append(cleaned)
    return fragments
