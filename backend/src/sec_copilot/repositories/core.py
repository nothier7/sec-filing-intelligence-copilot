from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from sec_copilot.db.models import (
    BenchmarkQuestion,
    Chunk,
    Company,
    EvalRun,
    Filing,
    FilingSection,
    XbrlFact,
)


class CompanyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company

    def get_by_cik(self, cik: str) -> Optional[Company]:
        return self.session.execute(select(Company).where(Company.cik == cik)).scalar_one_or_none()

    def get_by_ticker(self, ticker: str) -> Optional[Company]:
        return self.session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        ).scalar_one_or_none()

    def list_all(self) -> Sequence[Company]:
        return self.session.execute(select(Company).order_by(Company.name)).scalars().all()


class FilingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, filing: Filing) -> Filing:
        self.session.add(filing)
        self.session.flush()
        return filing

    def add_section(self, section: FilingSection) -> FilingSection:
        self.session.add(section)
        self.session.flush()
        return section

    def get_by_accession_number(self, accession_number: str) -> Optional[Filing]:
        return self.session.execute(
            select(Filing).where(Filing.accession_number == accession_number)
        ).scalar_one_or_none()

    def list_for_company(
        self,
        company_id: int,
        form_types: Optional[Sequence[str]] = None,
    ) -> Sequence[Filing]:
        statement: Select[tuple[Filing]] = select(Filing).where(Filing.company_id == company_id)
        if form_types:
            statement = statement.where(Filing.form_type.in_(form_types))
        statement = statement.order_by(Filing.filing_date.desc(), Filing.accession_number)
        return self.session.execute(statement).scalars().all()

    def list_sections(self, filing_id: int) -> Sequence[FilingSection]:
        return self.session.execute(
            select(FilingSection)
            .where(FilingSection.filing_id == filing_id)
            .order_by(FilingSection.sequence)
        ).scalars().all()


class ChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, chunk: Chunk) -> Chunk:
        self.session.add(chunk)
        self.session.flush()
        return chunk

    def get(self, chunk_id: str) -> Optional[Chunk]:
        return self.session.get(Chunk, chunk_id)

    def list_for_filing(self, filing_id: int) -> Sequence[Chunk]:
        return self.session.execute(
            select(Chunk).where(Chunk.filing_id == filing_id).order_by(Chunk.id)
        ).scalars().all()

    def list_for_section(self, section_id: int) -> Sequence[Chunk]:
        return self.session.execute(
            select(Chunk).where(Chunk.section_id == section_id).order_by(Chunk.id)
        ).scalars().all()


class XbrlFactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: XbrlFact) -> XbrlFact:
        self.session.add(fact)
        self.session.flush()
        return fact

    def find_by_concept(
        self,
        company_id: int,
        concept: str,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
    ) -> Sequence[XbrlFact]:
        statement: Select[tuple[XbrlFact]] = select(XbrlFact).where(
            XbrlFact.company_id == company_id,
            XbrlFact.concept == concept,
        )
        if fiscal_year is not None:
            statement = statement.where(XbrlFact.fiscal_year == fiscal_year)
        if fiscal_quarter is not None:
            statement = statement.where(XbrlFact.fiscal_quarter == fiscal_quarter)
        statement = statement.order_by(XbrlFact.filed_date.desc(), XbrlFact.id.desc())
        return self.session.execute(statement).scalars().all()


class BenchmarkQuestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, question: BenchmarkQuestion) -> BenchmarkQuestion:
        self.session.add(question)
        self.session.flush()
        return question

    def list_by_type(self, question_type: str) -> Sequence[BenchmarkQuestion]:
        return self.session.execute(
            select(BenchmarkQuestion)
            .where(BenchmarkQuestion.question_type == question_type)
            .order_by(BenchmarkQuestion.id)
        ).scalars().all()


class EvalRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, eval_run: EvalRun) -> EvalRun:
        self.session.add(eval_run)
        self.session.flush()
        return eval_run

    def get(self, eval_run_id: str) -> Optional[EvalRun]:
        return self.session.get(EvalRun, eval_run_id)

    def list_by_variant(self, system_variant: str) -> Sequence[EvalRun]:
        return self.session.execute(
            select(EvalRun)
            .where(EvalRun.system_variant == system_variant)
            .order_by(EvalRun.started_at.desc())
        ).scalars().all()

