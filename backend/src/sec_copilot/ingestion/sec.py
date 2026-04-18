from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from sec_copilot.repositories import CompanyRepository, FilingRepository, XbrlFactRepository
from sec_copilot.sec.client import SecClient
from sec_copilot.sec.normalizers import (
    normalize_company,
    normalize_company_facts,
    normalize_recent_filings,
)


@dataclass(frozen=True)
class SecIngestionResult:
    cik: str
    company_id: int
    company_created: bool
    filings_created: int
    filings_updated: int
    filing_documents_cached: int
    xbrl_facts_created: int
    xbrl_facts_updated: int


class SecIngestionService:
    def __init__(self, session: Session, client: SecClient) -> None:
        self.session = session
        self.client = client
        self.companies = CompanyRepository(session)
        self.filings = FilingRepository(session)
        self.xbrl_facts = XbrlFactRepository(session)

    def ingest_company(
        self,
        cik: str,
        form_types: Sequence[str] = ("10-K", "10-Q"),
        filing_limit: int = 10,
        fact_concepts: Optional[Sequence[str]] = None,
        download_documents: bool = True,
        use_cache: bool = True,
    ) -> SecIngestionResult:
        submissions = self.client.fetch_submissions(cik, use_cache=use_cache)
        normalized_company = normalize_company(submissions)
        company_created = self.companies.get_by_cik(normalized_company.cik) is None
        company = self.companies.upsert_by_cik(
            cik=normalized_company.cik,
            ticker=normalized_company.ticker,
            name=normalized_company.name,
            exchange=normalized_company.exchange,
            sic=normalized_company.sic,
            fiscal_year_end=normalized_company.fiscal_year_end,
        )

        filings_created = 0
        filings_updated = 0
        filing_documents_cached = 0
        normalized_filings = normalize_recent_filings(
            submissions,
            form_types=form_types,
            limit=filing_limit,
            archives_base_url=self.client.config.archives_base_url,
        )

        for normalized_filing in normalized_filings:
            raw_artifact_path: Optional[str] = None
            if download_documents:
                _, cache_path = self.client.fetch_filing_document(
                    cik=normalized_filing.cik,
                    accession_number=normalized_filing.accession_number,
                    primary_document=normalized_filing.primary_document,
                    use_cache=use_cache,
                )
                raw_artifact_path = _path_to_string(cache_path)
                filing_documents_cached += 1

            existing_filing = self.filings.get_by_accession_number(
                normalized_filing.accession_number
            )
            if existing_filing is None:
                filings_created += 1
            else:
                filings_updated += 1

            self.filings.upsert_by_accession_number(
                company_id=company.id,
                accession_number=normalized_filing.accession_number,
                cik=normalized_filing.cik,
                form_type=normalized_filing.form_type,
                filing_date=normalized_filing.filing_date,
                report_date=normalized_filing.report_date,
                fiscal_year=normalized_filing.fiscal_year,
                fiscal_quarter=normalized_filing.fiscal_quarter,
                source_url=normalized_filing.source_url,
                raw_artifact_path=raw_artifact_path,
            )

        company_facts = self.client.fetch_company_facts(cik, use_cache=use_cache)
        xbrl_facts_created = 0
        xbrl_facts_updated = 0
        for normalized_fact in normalize_company_facts(company_facts, concepts=fact_concepts):
            existing_fact = self.xbrl_facts.get_by_source_key(normalized_fact.source_key)
            if existing_fact is None:
                xbrl_facts_created += 1
            else:
                xbrl_facts_updated += 1

            linked_filing = (
                self.filings.get_by_accession_number(normalized_fact.accession_number)
                if normalized_fact.accession_number
                else None
            )
            self.xbrl_facts.upsert_by_source_key(
                source_key=normalized_fact.source_key,
                company_id=company.id,
                filing_id=linked_filing.id if linked_filing else None,
                cik=normalized_fact.cik,
                accession_number=normalized_fact.accession_number,
                concept=normalized_fact.concept,
                label=normalized_fact.label,
                unit=normalized_fact.unit,
                value=normalized_fact.value,
                fiscal_period=normalized_fact.fiscal_period,
                fiscal_year=normalized_fact.fiscal_year,
                fiscal_quarter=normalized_fact.fiscal_quarter,
                form_type=normalized_fact.form_type,
                filed_date=normalized_fact.filed_date,
                frame=normalized_fact.frame,
            )

        return SecIngestionResult(
            cik=company.cik,
            company_id=company.id,
            company_created=company_created,
            filings_created=filings_created,
            filings_updated=filings_updated,
            filing_documents_cached=filing_documents_cached,
            xbrl_facts_created=xbrl_facts_created,
            xbrl_facts_updated=xbrl_facts_updated,
        )


def _path_to_string(path: Path) -> str:
    return path.as_posix()

