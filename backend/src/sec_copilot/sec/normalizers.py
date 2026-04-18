from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional, Sequence

from sec_copilot.sec.identifiers import filing_document_url, normalize_cik


@dataclass(frozen=True)
class NormalizedCompany:
    cik: str
    ticker: Optional[str]
    name: str
    exchange: Optional[str]
    sic: Optional[str]
    fiscal_year_end: Optional[str]


@dataclass(frozen=True)
class NormalizedFiling:
    accession_number: str
    cik: str
    form_type: str
    filing_date: date
    report_date: Optional[date]
    fiscal_year: Optional[int]
    fiscal_quarter: Optional[int]
    primary_document: str
    source_url: str


@dataclass(frozen=True)
class NormalizedXbrlFact:
    source_key: str
    cik: str
    accession_number: Optional[str]
    concept: str
    label: Optional[str]
    unit: str
    value: Decimal
    fiscal_period: Optional[str]
    fiscal_year: Optional[int]
    fiscal_quarter: Optional[int]
    form_type: Optional[str]
    filed_date: Optional[date]
    frame: Optional[str]


def normalize_company(submissions: dict[str, Any]) -> NormalizedCompany:
    cik = normalize_cik(submissions.get("cik", ""))
    tickers = submissions.get("tickers") or []
    exchanges = submissions.get("exchanges") or []
    return NormalizedCompany(
        cik=cik,
        ticker=_first_non_empty(tickers),
        name=str(submissions.get("name") or submissions.get("entityName") or f"CIK {cik}"),
        exchange=_first_non_empty(exchanges),
        sic=_optional_string(submissions.get("sic")),
        fiscal_year_end=_optional_string(submissions.get("fiscalYearEnd")),
    )


def normalize_recent_filings(
    submissions: dict[str, Any],
    form_types: Sequence[str] = ("10-K", "10-Q"),
    limit: Optional[int] = None,
    archives_base_url: str = "https://www.sec.gov/Archives",
) -> list[NormalizedFiling]:
    cik = normalize_cik(submissions.get("cik", ""))
    allowed_forms = set(form_types)
    recent = submissions.get("filings", {}).get("recent", {})
    rows = _transpose_recent_filings(recent)
    filings: list[NormalizedFiling] = []

    for row in rows:
        form_type = _optional_string(row.get("form"))
        if form_type not in allowed_forms:
            continue

        accession_number = _optional_string(row.get("accessionNumber"))
        primary_document = _optional_string(row.get("primaryDocument"))
        filing_date = _parse_date(row.get("filingDate"))
        if accession_number is None or primary_document is None or filing_date is None:
            continue

        report_date = _parse_date(row.get("reportDate"))
        filings.append(
            NormalizedFiling(
                accession_number=accession_number,
                cik=cik,
                form_type=form_type,
                filing_date=filing_date,
                report_date=report_date,
                fiscal_year=report_date.year if report_date else None,
                fiscal_quarter=_infer_fiscal_quarter(form_type, report_date),
                primary_document=primary_document,
                source_url=filing_document_url(
                    cik=cik,
                    accession_number=accession_number,
                    primary_document=primary_document,
                    archives_base_url=archives_base_url,
                ),
            )
        )
        if limit is not None and len(filings) >= limit:
            break

    return filings


def normalize_company_facts(
    company_facts: dict[str, Any],
    concepts: Optional[Iterable[str]] = None,
) -> list[NormalizedXbrlFact]:
    cik = normalize_cik(company_facts.get("cik", ""))
    concept_filter = set(concepts or [])
    facts: list[NormalizedXbrlFact] = []

    for taxonomy_facts in company_facts.get("facts", {}).values():
        for concept, concept_payload in taxonomy_facts.items():
            if concept_filter and concept not in concept_filter:
                continue
            label = _optional_string(concept_payload.get("label"))
            units = concept_payload.get("units", {})
            for unit, unit_facts in units.items():
                for fact_payload in unit_facts:
                    normalized = _normalize_fact_payload(
                        cik=cik,
                        concept=concept,
                        label=label,
                        unit=unit,
                        payload=fact_payload,
                    )
                    if normalized is not None:
                        facts.append(normalized)

    return facts


def _normalize_fact_payload(
    cik: str,
    concept: str,
    label: Optional[str],
    unit: str,
    payload: dict[str, Any],
) -> Optional[NormalizedXbrlFact]:
    value = _parse_decimal(payload.get("val"))
    if value is None:
        return None

    accession_number = _optional_string(payload.get("accn"))
    fiscal_period = _optional_string(payload.get("fp"))
    fiscal_year = _optional_int(payload.get("fy"))
    form_type = _optional_string(payload.get("form"))
    filed_date = _parse_date(payload.get("filed"))
    frame = _optional_string(payload.get("frame"))

    fact = NormalizedXbrlFact(
        source_key=_xbrl_source_key(
            cik=cik,
            accession_number=accession_number,
            concept=concept,
            unit=unit,
            value=value,
            fiscal_period=fiscal_period,
            fiscal_year=fiscal_year,
            form_type=form_type,
            filed_date=filed_date,
            frame=frame,
        ),
        cik=cik,
        accession_number=accession_number,
        concept=concept,
        label=label,
        unit=unit,
        value=value,
        fiscal_period=fiscal_period,
        fiscal_year=fiscal_year,
        fiscal_quarter=_fiscal_quarter_from_period(fiscal_period),
        form_type=form_type,
        filed_date=filed_date,
        frame=frame,
    )
    return fact


def _transpose_recent_filings(recent: dict[str, Any]) -> list[dict[str, Any]]:
    if not recent:
        return []
    row_count = max((len(values) for values in recent.values() if isinstance(values, list)), default=0)
    rows: list[dict[str, Any]] = []
    for index in range(row_count):
        row: dict[str, Any] = {}
        for key, values in recent.items():
            if isinstance(values, list) and index < len(values):
                row[key] = values[index]
        rows.append(row)
    return rows


def _parse_date(value: Any) -> Optional[date]:
    text = _optional_string(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_non_empty(values: Sequence[Any]) -> Optional[str]:
    for value in values:
        text = _optional_string(value)
        if text is not None:
            return text
    return None


def _infer_fiscal_quarter(form_type: str, report_date: Optional[date]) -> Optional[int]:
    if form_type == "10-K":
        return None
    if form_type != "10-Q" or report_date is None:
        return None
    return ((report_date.month - 1) // 3) + 1


def _fiscal_quarter_from_period(fiscal_period: Optional[str]) -> Optional[int]:
    if fiscal_period is None:
        return None
    if len(fiscal_period) == 2 and fiscal_period.startswith("Q") and fiscal_period[1].isdigit():
        quarter = int(fiscal_period[1])
        if 1 <= quarter <= 4:
            return quarter
    return None


def _xbrl_source_key(
    cik: str,
    accession_number: Optional[str],
    concept: str,
    unit: str,
    value: Decimal,
    fiscal_period: Optional[str],
    fiscal_year: Optional[int],
    form_type: Optional[str],
    filed_date: Optional[date],
    frame: Optional[str],
) -> str:
    payload = {
        "accession_number": accession_number,
        "cik": cik,
        "concept": concept,
        "filed_date": filed_date.isoformat() if filed_date else None,
        "fiscal_period": fiscal_period,
        "fiscal_year": fiscal_year,
        "form_type": form_type,
        "frame": frame,
        "unit": unit,
        "value": str(value),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
