import pytest

from sec_copilot.sec import accession_without_dashes, filing_document_url, normalize_cik


def test_normalize_cik_zero_pads_to_ten_digits() -> None:
    assert normalize_cik("320193") == "0000320193"
    assert normalize_cik(320193) == "0000320193"


def test_normalize_cik_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        normalize_cik("not-a-cik")


def test_filing_document_url_uses_archive_path_shape() -> None:
    assert accession_without_dashes("0000320193-24-000123") == "000032019324000123"
    assert filing_document_url(
        cik="0000320193",
        accession_number="0000320193-24-000123",
        primary_document="aapl-20240928.htm",
    ) == (
        "https://www.sec.gov/Archives/edgar/data/"
        "320193/000032019324000123/aapl-20240928.htm"
    )

