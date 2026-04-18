from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sec_copilot.db.models import Company, Filing, XbrlFact
from sec_copilot.ingestion import SecIngestionService
from sec_copilot.sec import SecClient, SecClientConfig

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_sec_ingestion_upserts_company_filings_and_facts(
    session: Session,
    tmp_path: Path,
) -> None:
    submissions = (FIXTURE_DIR / "submissions_aapl.json").read_text()
    company_facts = (FIXTURE_DIR / "companyfacts_aapl.json").read_text()
    ten_k = (FIXTURE_DIR / "aapl-20240928.htm").read_text()
    ten_q = (FIXTURE_DIR / "aapl-20240629.htm").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/submissions/CIK0000320193.json"):
            return httpx.Response(200, text=submissions)
        if url.endswith("/api/xbrl/companyfacts/CIK0000320193.json"):
            return httpx.Response(200, text=company_facts)
        if url.endswith("/320193/000032019324000123/aapl-20240928.htm"):
            return httpx.Response(200, text=ten_k)
        if url.endswith("/320193/000032019324000083/aapl-20240629.htm"):
            return httpx.Response(200, text=ten_q)
        return httpx.Response(404, text="not found")

    client = SecClient(
        SecClientConfig(
            user_agent="sec-copilot-test contact@example.com",
            cache_dir=tmp_path,
            requests_per_second=100,
        ),
        transport=httpx.MockTransport(handler),
    )

    try:
        service = SecIngestionService(session=session, client=client)
        first_result = service.ingest_company("320193", filing_limit=2)
        session.commit()
        second_result = service.ingest_company("0000320193", filing_limit=2)
        session.commit()
    finally:
        client.close()

    assert first_result.company_created is True
    assert first_result.filings_created == 2
    assert first_result.xbrl_facts_created == 3
    assert second_result.company_created is False
    assert second_result.filings_updated == 2
    assert second_result.xbrl_facts_updated == 3

    assert session.scalar(select(func.count()).select_from(Company)) == 1
    assert session.scalar(select(func.count()).select_from(Filing)) == 2
    assert session.scalar(select(func.count()).select_from(XbrlFact)) == 3

    company = session.execute(select(Company)).scalar_one()
    assert company.cik == "0000320193"
    assert company.ticker == "AAPL"

    ten_k_filing = session.execute(
        select(Filing).where(Filing.accession_number == "0000320193-24-000123")
    ).scalar_one()
    assert ten_k_filing.raw_artifact_path is not None
    assert Path(ten_k_filing.raw_artifact_path).exists()

    revenue_fact = session.execute(
        select(XbrlFact).where(
            XbrlFact.concept == "Revenues",
            XbrlFact.fiscal_period == "FY",
        )
    ).scalar_one()
    assert revenue_fact.filing_id == ten_k_filing.id

