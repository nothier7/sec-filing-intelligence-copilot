from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from sec_copilot.answering import Citation, NumericGrounding


class EvalVariant(str, Enum):
    CLOSED_BOOK = "closed_book"
    NAIVE_RAG = "naive_rag"
    IMPROVED_RAG = "improved_rag"
    IMPROVED_RAG_XBRL = "improved_rag_xbrl"


class EvalExpected(BaseModel):
    supported: bool = True
    answer_keywords: list[str] = Field(default_factory=list)
    citation_chunk_ids: list[str] = Field(default_factory=list)
    section_types: list[str] = Field(default_factory=list)
    xbrl_concepts: list[str] = Field(default_factory=list)
    numeric_value: Optional[str] = None
    numeric_unit: Optional[str] = None
    insufficient_reason: Optional[str] = None


class EvalQuestion(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    accession_number: str = Field(min_length=1)
    question_type: str = Field(default="text", min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    cik: Optional[str] = None
    form_type: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    section_type: Optional[str] = None
    expected: EvalExpected
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalPrediction(BaseModel):
    question_id: str
    variant: EvalVariant
    supported: bool
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    numeric_grounding: list[NumericGrounding] = Field(default_factory=list)
    retrieval_count: int = 0
    insufficient_evidence_reason: Optional[str] = None
    latency_ms: float = Field(ge=0.0)
    error: Optional[str] = None


class EvalQuestionResult(BaseModel):
    question: EvalQuestion
    predictions: dict[EvalVariant, EvalPrediction]
    metrics: dict[EvalVariant, dict[str, float]]


class EvalRunResult(BaseModel):
    generated_at: datetime
    dataset_path: str
    variants: list[EvalVariant]
    question_count: int
    metrics: dict[EvalVariant, dict[str, float]]
    results: list[EvalQuestionResult]
