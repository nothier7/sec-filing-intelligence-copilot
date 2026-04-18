from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sec_copilot.db.models import Chunk, Company, Filing, FilingSection
from sec_copilot.filings import FilingParseService
from sec_copilot.repositories import CompanyRepository, FilingRepository

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_filing_parse_service_persists_sections_and_chunks(session: Session) -> None:
    company = CompanyRepository(session).add(
        Company(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    filing = FilingRepository(session).add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-24-000123",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2024, 11, 1),
            report_date=date(2024, 9, 28),
            fiscal_year=2024,
            source_url="https://www.sec.gov/Archives/example.htm",
            raw_artifact_path=(FIXTURE_DIR / "aapl-20240928.htm").as_posix(),
        )
    )
    session.commit()

    service = FilingParseService(session=session, max_tokens=12, overlap_tokens=2)
    first_result = service.parse_filing(filing.id)
    session.commit()
    second_result = service.parse_by_accession_number("0000320193-24-000123")
    session.commit()

    assert first_result.sections_created == 4
    assert first_result.chunks_created >= 4
    assert second_result.sections_created == first_result.sections_created
    assert second_result.chunks_created == first_result.chunks_created
    assert session.scalar(select(func.count()).select_from(FilingSection)) == 4
    assert session.scalar(select(func.count()).select_from(Chunk)) == first_result.chunks_created

    risk_section = session.execute(
        select(FilingSection).where(FilingSection.normalized_section_type == "risk_factors")
    ).scalar_one()
    risk_chunks = session.execute(
        select(Chunk).where(Chunk.section_id == risk_section.id).order_by(Chunk.id)
    ).scalars().all()

    assert risk_chunks
    assert risk_chunks[0].id.startswith("0000320193-24-000123:s0002:c")
    assert risk_chunks[0].metadata_json["section_type"] == "risk_factors"
    assert risk_chunks[0].metadata_json["source_url"] == "https://www.sec.gov/Archives/example.htm"

