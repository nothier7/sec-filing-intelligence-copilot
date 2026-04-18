import json
from pathlib import Path

import httpx

from sec_copilot.sec import SecClient, SecClientConfig

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_sec_client_uses_user_agent_and_caches_submissions(tmp_path: Path) -> None:
    submissions = (FIXTURE_DIR / "submissions_aapl.json").read_text()
    seen_user_agents: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_user_agents.append(request.headers["User-Agent"])
        assert str(request.url) == "https://data.sec.gov/submissions/CIK0000320193.json"
        return httpx.Response(200, text=submissions)

    client = SecClient(
        SecClientConfig(
            user_agent="sec-copilot-test contact@example.com",
            cache_dir=tmp_path,
            requests_per_second=100,
        ),
        transport=httpx.MockTransport(handler),
    )

    try:
        first_response = client.fetch_submissions("320193")
        second_response = client.fetch_submissions("320193")
    finally:
        client.close()

    assert first_response["name"] == "Apple Inc."
    assert second_response == first_response
    assert seen_user_agents == ["sec-copilot-test contact@example.com"]
    cached = tmp_path / "submissions" / "CIK0000320193.json"
    assert json.loads(cached.read_text())["cik"] == 320193


def test_sec_client_fetches_filing_document_to_cache(tmp_path: Path) -> None:
    html = (FIXTURE_DIR / "aapl-20240928.htm").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/320193/000032019324000123/aapl-20240928.htm")
        return httpx.Response(200, text=html)

    client = SecClient(
        SecClientConfig(
            user_agent="sec-copilot-test contact@example.com",
            cache_dir=tmp_path,
            requests_per_second=100,
        ),
        transport=httpx.MockTransport(handler),
    )

    try:
        text, cache_path = client.fetch_filing_document(
            cik="0000320193",
            accession_number="0000320193-24-000123",
            primary_document="aapl-20240928.htm",
        )
    finally:
        client.close()

    assert "Apple Inc. 2024 Form 10-K" in text
    assert cache_path.exists()
    assert cache_path.read_text() == html

