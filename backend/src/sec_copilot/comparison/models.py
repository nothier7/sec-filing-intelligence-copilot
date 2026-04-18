from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"


class CompareRequest(BaseModel):
    accession_number: str = Field(min_length=1)
    section_type: str = Field(default="risk_factors", min_length=1)
    previous_accession_number: Optional[str] = None
    max_claims: int = Field(default=5, ge=1, le=20)


class ChangeCitation(BaseModel):
    filing_role: str
    accession_number: str
    chunk_id: str
    section_name: Optional[str] = None
    section_type: Optional[str] = None
    source_url: Optional[str] = None
    source_start: Optional[int] = None
    source_end: Optional[int] = None
    snippet: str


class ChangeClaim(BaseModel):
    change_type: ChangeType
    text: str
    citations: list[ChangeCitation] = Field(default_factory=list)


class CompareResponse(BaseModel):
    current_accession_number: str
    prior_accession_number: Optional[str] = None
    section_type: str
    supported: bool
    summary: str
    added_claims: list[ChangeClaim] = Field(default_factory=list)
    removed_claims: list[ChangeClaim] = Field(default_factory=list)
    unchanged_claim_count: int = 0
    citations: list[ChangeCitation] = Field(default_factory=list)
    insufficient_evidence_reason: Optional[str] = None
