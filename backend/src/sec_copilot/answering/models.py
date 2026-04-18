from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    TEXT = "text"
    NUMERIC = "numeric"
    COMPARISON = "comparison"
    UNSUPPORTED = "unsupported"


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    accession_number: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    cik: Optional[str] = None
    form_type: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    section_type: Optional[str] = None


class Citation(BaseModel):
    chunk_id: str
    accession_number: Optional[str] = None
    section_name: Optional[str] = None
    section_type: Optional[str] = None
    source_url: Optional[str] = None
    source_start: Optional[int] = None
    source_end: Optional[int] = None
    score: Optional[float] = None
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    query_type: QueryType
    supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    retrieval_count: int = 0
    insufficient_evidence_reason: Optional[str] = None
