from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import httpx

from sec_copilot.config import get_settings
from sec_copilot.sec.identifiers import filing_document_url, normalize_cik


@dataclass(frozen=True)
class SecClientConfig:
    user_agent: str
    requests_per_second: int = 5
    cache_dir: Path = Path("data/raw/sec")
    data_base_url: str = "https://data.sec.gov"
    archives_base_url: str = "https://www.sec.gov/Archives"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5


class SecClient:
    def __init__(
        self,
        config: SecClientConfig,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if config.requests_per_second < 1:
            raise ValueError("requests_per_second must be at least 1")
        self.config = config
        self._client = httpx.Client(
            headers={
                "User-Agent": config.user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=config.timeout_seconds,
            follow_redirects=True,
            transport=transport,
        )
        self._lock = Lock()
        self._last_request_at = 0.0

    @classmethod
    def from_settings(cls) -> "SecClient":
        settings = get_settings()
        return cls(
            SecClientConfig(
                user_agent=settings.sec_user_agent,
                requests_per_second=settings.sec_requests_per_second,
                cache_dir=Path(settings.sec_raw_data_dir),
            )
        )

    def close(self) -> None:
        self._client.close()

    def fetch_submissions(self, cik: int | str, use_cache: bool = True) -> dict[str, Any]:
        normalized_cik = normalize_cik(cik)
        url = f"{self.config.data_base_url.rstrip('/')}/submissions/CIK{normalized_cik}.json"
        cache_path = self.config.cache_dir / "submissions" / f"CIK{normalized_cik}.json"
        return self._get_json(url, cache_path, use_cache=use_cache)

    def fetch_company_facts(self, cik: int | str, use_cache: bool = True) -> dict[str, Any]:
        normalized_cik = normalize_cik(cik)
        url = f"{self.config.data_base_url.rstrip('/')}/api/xbrl/companyfacts/CIK{normalized_cik}.json"
        cache_path = self.config.cache_dir / "companyfacts" / f"CIK{normalized_cik}.json"
        return self._get_json(url, cache_path, use_cache=use_cache)

    def fetch_filing_document(
        self,
        cik: int | str,
        accession_number: str,
        primary_document: str,
        use_cache: bool = True,
    ) -> tuple[str, Path]:
        normalized_cik = normalize_cik(cik)
        url = filing_document_url(
            cik=normalized_cik,
            accession_number=accession_number,
            primary_document=primary_document,
            archives_base_url=self.config.archives_base_url,
        )
        cache_path = (
            self.config.cache_dir
            / "filings"
            / normalized_cik
            / accession_number.replace("-", "")
            / primary_document
        )
        return self._get_text(url, cache_path, use_cache=use_cache), cache_path

    def _get_json(self, url: str, cache_path: Path, use_cache: bool) -> dict[str, Any]:
        if use_cache and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        text = self._request_text(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        return json.loads(text)

    def _get_text(self, url: str, cache_path: Path, use_cache: bool) -> str:
        if use_cache and cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

        text = self._request_text(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        return text

    def _request_text(self, url: str) -> str:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            self._throttle()
            try:
                response = self._client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as error:
                last_error = error
                if attempt == self.config.max_retries:
                    break
                time.sleep(self.config.retry_backoff_seconds * attempt)
        if last_error is None:
            raise RuntimeError(f"SEC request failed without an exception: {url}")
        raise last_error

    def _throttle(self) -> None:
        min_interval = 1.0 / self.config.requests_per_second
        with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_at = time.monotonic()

