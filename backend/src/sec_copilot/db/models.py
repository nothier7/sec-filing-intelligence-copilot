from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    ticker: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[Optional[str]] = mapped_column(String(64))
    sic: Mapped[Optional[str]] = mapped_column(String(16))
    fiscal_year_end: Mapped[Optional[str]] = mapped_column(String(8))

    filings: Mapped[list[Filing]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    xbrl_facts: Mapped[list[XbrlFact]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )


class Filing(TimestampMixin, Base):
    __tablename__ = "filings"
    __table_args__ = (
        UniqueConstraint("company_id", "accession_number", name="uq_filings_company_accession"),
        Index("ix_filings_company_form_date", "company_id", "form_type", "filing_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    accession_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    cik: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    form_type: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    filing_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    report_date: Mapped[Optional[date]] = mapped_column(Date)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_artifact_path: Mapped[Optional[str]] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="filings")
    sections: Mapped[list[FilingSection]] = relationship(
        back_populates="filing",
        cascade="all, delete-orphan",
    )
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="filing",
        cascade="all, delete-orphan",
    )
    xbrl_facts: Mapped[list[XbrlFact]] = relationship(back_populates="filing")


class FilingSection(TimestampMixin, Base):
    __tablename__ = "filing_sections"
    __table_args__ = (
        UniqueConstraint("filing_id", "sequence", name="uq_filing_sections_filing_sequence"),
        Index("ix_filing_sections_type", "normalized_section_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.id"), nullable=False)
    section_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_section_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    filing: Mapped[Filing] = relationship(back_populates="sections")
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
    )


class Chunk(TimestampMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_filing_section", "filing_id", "section_id"),
        Index("ix_chunks_token_count", "token_count"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.id"), nullable=False)
    section_id: Mapped[Optional[int]] = mapped_column(ForeignKey("filing_sections.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    source_start: Mapped[Optional[int]] = mapped_column(Integer)
    source_end: Mapped[Optional[int]] = mapped_column(Integer)

    filing: Mapped[Filing] = relationship(back_populates="chunks")
    section: Mapped[Optional[FilingSection]] = relationship(back_populates="chunks")


class XbrlFact(TimestampMixin, Base):
    __tablename__ = "xbrl_facts"
    __table_args__ = (
        Index("ix_xbrl_facts_company_concept_period", "company_id", "concept", "fiscal_year", "fiscal_quarter"),
        Index("ix_xbrl_facts_accession_concept", "accession_number", "concept"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    filing_id: Mapped[Optional[int]] = mapped_column(ForeignKey("filings.id"))
    cik: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    accession_number: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    concept: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(38, 6), nullable=False)
    fiscal_period: Mapped[Optional[str]] = mapped_column(String(16))
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer)
    form_type: Mapped[Optional[str]] = mapped_column(String(16))
    filed_date: Mapped[Optional[date]] = mapped_column(Date)
    frame: Mapped[Optional[str]] = mapped_column(String(32))

    company: Mapped[Company] = relationship(back_populates="xbrl_facts")
    filing: Mapped[Optional[Filing]] = relationship(back_populates="xbrl_facts")


class BenchmarkQuestion(TimestampMixin, Base):
    __tablename__ = "benchmark_questions"
    __table_args__ = (Index("ix_benchmark_questions_type", "question_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text)
    expected_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expected_facts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class EvalRun(TimestampMixin, Base):
    __tablename__ = "eval_runs"
    __table_args__ = (Index("ix_eval_runs_variant_started", "system_variant", "started_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    system_variant: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    model_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    retriever_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_path: Mapped[Optional[str]] = mapped_column(Text)
