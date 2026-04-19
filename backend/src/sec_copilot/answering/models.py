from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    TEXT = "text"
    NUMERIC = "numeric"
    COMPARISON = "comparison"
    UNSUPPORTED = "unsupported"


class NumericGroundingStatus(str, Enum):
    VALIDATED = "validated"
    MISMATCHED = "mismatched"
    UNAVAILABLE = "unavailable"


class AnswerMode(str, Enum):
    EXTRACTIVE = "extractive"
    LLM = "llm"


class SynthesisStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    SUCCEEDED = "succeeded"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    accession_number: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    answer_mode: AnswerMode = AnswerMode.EXTRACTIVE
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


class NumericGrounding(BaseModel):
    status: NumericGroundingStatus
    metric: Optional[str] = None
    metric_label: Optional[str] = None
    concept: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    fiscal_period: Optional[str] = None
    form_type: Optional[str] = None
    filed_date: Optional[date] = None
    accession_number: Optional[str] = None
    source_key: Optional[str] = None
    reason: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    answer: str
    query_type: QueryType
    supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    numeric_grounding: list[NumericGrounding] = Field(default_factory=list)
    retrieval_count: int = 0
    insufficient_evidence_reason: Optional[str] = None
    answer_mode: AnswerMode = AnswerMode.EXTRACTIVE
    fallback_answer: Optional[str] = None
    synthesis_model: Optional[str] = None
    synthesis_status: SynthesisStatus = SynthesisStatus.NOT_REQUESTED
    synthesis_reason: Optional[str] = None
