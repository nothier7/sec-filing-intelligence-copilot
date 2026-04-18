from __future__ import annotations

from typing import Union


def normalize_cik(cik: Union[int, str]) -> str:
    digits = "".join(character for character in str(cik).strip() if character.isdigit())
    if not digits:
        raise ValueError("CIK must contain digits")
    if len(digits) > 10:
        raise ValueError("CIK cannot be longer than 10 digits")
    return digits.zfill(10)


def accession_without_dashes(accession_number: str) -> str:
    normalized = accession_number.strip()
    if not normalized:
        raise ValueError("Accession number cannot be empty")
    return normalized.replace("-", "")


def filing_document_url(
    cik: Union[int, str],
    accession_number: str,
    primary_document: str,
    archives_base_url: str = "https://www.sec.gov/Archives",
) -> str:
    normalized_cik = str(int(normalize_cik(cik)))
    accession = accession_without_dashes(accession_number)
    document = primary_document.strip().lstrip("/")
    if not document:
        raise ValueError("Primary document cannot be empty")
    return f"{archives_base_url.rstrip('/')}/edgar/data/{normalized_cik}/{accession}/{document}"
