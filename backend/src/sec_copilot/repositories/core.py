from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Select, delete, select
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

    def upsert_by_cik(
        self,
        cik: str,
        name: str,
        ticker: Optional[str] = None,
        exchange: Optional[str] = None,
        sic: Optional[str] = None,
        fiscal_year_end: Optional[str] = None,
    ) -> Company:
        company = self.get_by_cik(cik)
        if company is None:
            company = Company(
                cik=cik,
                ticker=ticker,
                name=name,
                exchange=exchange,
                sic=sic,
                fiscal_year_end=fiscal_year_end,
            )
            return self.add(company)

        company.name = name
        company.ticker = ticker
        company.exchange = exchange
        company.sic = sic
        company.fiscal_year_end = fiscal_year_end
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

    def upsert_by_accession_number(
        self,
        company_id: int,
        accession_number: str,
        cik: str,
        form_type: str,
        filing_date: date,
        source_url: str,
        report_date: Optional[date] = None,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
        raw_artifact_path: Optional[str] = None,
    ) -> Filing:
        filing = self.get_by_accession_number(accession_number)
        if filing is None:
            filing = Filing(
                company_id=company_id,
                accession_number=accession_number,
                cik=cik,
                form_type=form_type,
                filing_date=filing_date,
                report_date=report_date,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                source_url=source_url,
                raw_artifact_path=raw_artifact_path,
            )
            return self.add(filing)

        filing.company_id = company_id
        filing.cik = cik
        filing.form_type = form_type
        filing.filing_date = filing_date
        filing.report_date = report_date
        filing.fiscal_year = fiscal_year
        filing.fiscal_quarter = fiscal_quarter
        filing.source_url = source_url
        filing.raw_artifact_path = raw_artifact_path
        self.session.flush()
        return filing

    def add_section(
        self,
        filing_id: int,
        section_name: str,
        normalized_section_type: str,
        sequence: int,
        text_hash: str,
    ) -> FilingSection:
        section = FilingSection(
            filing_id=filing_id,
            section_name=section_name,
            normalized_section_type=normalized_section_type,
            sequence=sequence,
            text_hash=text_hash,
        )
        self.session.add(section)
        self.session.flush()
        return section

    def get(self, filing_id: int) -> Optional[Filing]:
        return self.session.get(Filing, filing_id)

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

    def delete_sections_for_filing(self, filing_id: int) -> int:
        result = self.session.execute(
            delete(FilingSection).where(FilingSection.filing_id == filing_id)
        )
        self.session.flush()
        return result.rowcount or 0


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

    def delete_for_filing(self, filing_id: int) -> int:
        result = self.session.execute(delete(Chunk).where(Chunk.filing_id == filing_id))
        self.session.flush()
        return result.rowcount or 0


class XbrlFactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fact: XbrlFact) -> XbrlFact:
        self.session.add(fact)
        self.session.flush()
        return fact

    def get_by_source_key(self, source_key: str) -> Optional[XbrlFact]:
        return self.session.execute(
            select(XbrlFact).where(XbrlFact.source_key == source_key)
        ).scalar_one_or_none()

    def upsert_by_source_key(
        self,
        source_key: str,
        company_id: int,
        cik: str,
        concept: str,
        unit: str,
        value: Decimal,
        filing_id: Optional[int] = None,
        accession_number: Optional[str] = None,
        label: Optional[str] = None,
        fiscal_period: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
        form_type: Optional[str] = None,
        filed_date: Optional[date] = None,
        frame: Optional[str] = None,
    ) -> XbrlFact:
        fact = self.get_by_source_key(source_key)
        if fact is None:
            fact = XbrlFact(
                source_key=source_key,
                company_id=company_id,
                filing_id=filing_id,
                cik=cik,
                accession_number=accession_number,
                concept=concept,
                label=label,
                unit=unit,
                value=value,
                fiscal_period=fiscal_period,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                form_type=form_type,
                filed_date=filed_date,
                frame=frame,
            )
            return self.add(fact)

        fact.company_id = company_id
        fact.filing_id = filing_id
        fact.cik = cik
        fact.accession_number = accession_number
        fact.concept = concept
        fact.label = label
        fact.unit = unit
        fact.value = value
        fact.fiscal_period = fiscal_period
        fact.fiscal_year = fiscal_year
        fact.fiscal_quarter = fiscal_quarter
        fact.form_type = form_type
        fact.filed_date = filed_date
        fact.frame = frame
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

    def find_by_concepts(
        self,
        company_id: int,
        concepts: Sequence[str],
        fiscal_year: Optional[int] = None,
        fiscal_quarter: Optional[int] = None,
        fiscal_period: Optional[str] = None,
        form_type: Optional[str] = None,
        accession_number: Optional[str] = None,
    ) -> Sequence[XbrlFact]:
        statement: Select[tuple[XbrlFact]] = select(XbrlFact).where(
            XbrlFact.company_id == company_id,
            XbrlFact.concept.in_(concepts),
        )
        if fiscal_year is not None:
            statement = statement.where(XbrlFact.fiscal_year == fiscal_year)
        if fiscal_quarter is not None:
            statement = statement.where(XbrlFact.fiscal_quarter == fiscal_quarter)
        if fiscal_period is not None:
            statement = statement.where(XbrlFact.fiscal_period == fiscal_period)
        if form_type is not None:
            statement = statement.where(XbrlFact.form_type == form_type)
        if accession_number is not None:
            statement = statement.where(XbrlFact.accession_number == accession_number)
        statement = statement.order_by(
            XbrlFact.filed_date.desc(),
            XbrlFact.fiscal_year.desc(),
            XbrlFact.id.desc(),
        )
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
