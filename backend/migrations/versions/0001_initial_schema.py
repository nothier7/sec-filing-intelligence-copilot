"""Create initial persistence schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-18
"""

from collections.abc import Sequence
from typing import Optional

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Optional[str] = None
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cik", sa.String(length=10), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("sic", sa.String(length=16), nullable=True),
        sa.Column("fiscal_year_end", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_cik"), "companies", ["cik"], unique=True)
    op.create_index(op.f("ix_companies_ticker"), "companies", ["ticker"], unique=False)

    op.create_table(
        "benchmark_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=64), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("expected_evidence", sa.JSON(), nullable=False),
        sa.Column("expected_facts", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_benchmark_questions_type",
        "benchmark_questions",
        ["question_type"],
        unique=False,
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("system_variant", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model_config", sa.JSON(), nullable=False),
        sa.Column("retriever_config", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eval_runs_variant_started",
        "eval_runs",
        ["system_variant", "started_at"],
        unique=False,
    )

    op.create_table(
        "filings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.String(length=32), nullable=False),
        sa.Column("cik", sa.String(length=10), nullable=False),
        sa.Column("form_type", sa.String(length=16), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("raw_artifact_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "accession_number", name="uq_filings_company_accession"),
    )
    op.create_index(op.f("ix_filings_accession_number"), "filings", ["accession_number"], unique=True)
    op.create_index(op.f("ix_filings_cik"), "filings", ["cik"], unique=False)
    op.create_index("ix_filings_company_form_date", "filings", ["company_id", "form_type", "filing_date"], unique=False)
    op.create_index(op.f("ix_filings_filing_date"), "filings", ["filing_date"], unique=False)
    op.create_index(op.f("ix_filings_form_type"), "filings", ["form_type"], unique=False)

    op.create_table(
        "filing_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filing_id", sa.Integer(), nullable=False),
        sa.Column("section_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_section_type", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["filing_id"], ["filings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filing_id", "sequence", name="uq_filing_sections_filing_sequence"),
    )
    op.create_index("ix_filing_sections_type", "filing_sections", ["normalized_section_type"], unique=False)
    op.create_index(
        op.f("ix_filing_sections_normalized_section_type"),
        "filing_sections",
        ["normalized_section_type"],
        unique=False,
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("filing_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("source_start", sa.Integer(), nullable=True),
        sa.Column("source_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["filing_id"], ["filings.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["filing_sections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunks_filing_section", "chunks", ["filing_id", "section_id"], unique=False)
    op.create_index("ix_chunks_token_count", "chunks", ["token_count"], unique=False)

    op.create_table(
        "xbrl_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("filing_id", sa.Integer(), nullable=True),
        sa.Column("cik", sa.String(length=10), nullable=False),
        sa.Column("accession_number", sa.String(length=32), nullable=True),
        sa.Column("concept", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(38, 6), nullable=False),
        sa.Column("fiscal_period", sa.String(length=16), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=True),
        sa.Column("form_type", sa.String(length=16), nullable=True),
        sa.Column("filed_date", sa.Date(), nullable=True),
        sa.Column("frame", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["filing_id"], ["filings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_xbrl_facts_source_key"), "xbrl_facts", ["source_key"], unique=True)
    op.create_index(op.f("ix_xbrl_facts_accession_number"), "xbrl_facts", ["accession_number"], unique=False)
    op.create_index("ix_xbrl_facts_accession_concept", "xbrl_facts", ["accession_number", "concept"], unique=False)
    op.create_index(op.f("ix_xbrl_facts_cik"), "xbrl_facts", ["cik"], unique=False)
    op.create_index("ix_xbrl_facts_company_concept_period", "xbrl_facts", ["company_id", "concept", "fiscal_year", "fiscal_quarter"], unique=False)
    op.create_index(op.f("ix_xbrl_facts_concept"), "xbrl_facts", ["concept"], unique=False)
    op.create_index(op.f("ix_xbrl_facts_fiscal_year"), "xbrl_facts", ["fiscal_year"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_xbrl_facts_source_key"), table_name="xbrl_facts")
    op.drop_index(op.f("ix_xbrl_facts_fiscal_year"), table_name="xbrl_facts")
    op.drop_index(op.f("ix_xbrl_facts_concept"), table_name="xbrl_facts")
    op.drop_index("ix_xbrl_facts_company_concept_period", table_name="xbrl_facts")
    op.drop_index(op.f("ix_xbrl_facts_cik"), table_name="xbrl_facts")
    op.drop_index("ix_xbrl_facts_accession_concept", table_name="xbrl_facts")
    op.drop_index(op.f("ix_xbrl_facts_accession_number"), table_name="xbrl_facts")
    op.drop_table("xbrl_facts")
    op.drop_index("ix_chunks_token_count", table_name="chunks")
    op.drop_index("ix_chunks_filing_section", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index(op.f("ix_filing_sections_normalized_section_type"), table_name="filing_sections")
    op.drop_index("ix_filing_sections_type", table_name="filing_sections")
    op.drop_table("filing_sections")
    op.drop_index(op.f("ix_filings_form_type"), table_name="filings")
    op.drop_index(op.f("ix_filings_filing_date"), table_name="filings")
    op.drop_index("ix_filings_company_form_date", table_name="filings")
    op.drop_index(op.f("ix_filings_cik"), table_name="filings")
    op.drop_index(op.f("ix_filings_accession_number"), table_name="filings")
    op.drop_table("filings")
    op.drop_index("ix_eval_runs_variant_started", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index("ix_benchmark_questions_type", table_name="benchmark_questions")
    op.drop_table("benchmark_questions")
    op.drop_index(op.f("ix_companies_ticker"), table_name="companies")
    op.drop_index(op.f("ix_companies_cik"), table_name="companies")
    op.drop_table("companies")
