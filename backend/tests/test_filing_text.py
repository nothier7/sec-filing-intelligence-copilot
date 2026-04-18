from pathlib import Path

from sec_copilot.filings import extract_text

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_extract_text_from_html_preserves_block_boundaries() -> None:
    html = (FIXTURE_DIR / "aapl-20240928.htm").read_text()

    text = extract_text(html)

    assert "Apple Inc. 2024 Form 10-K" in text
    assert "Item 1A. Risk Factors" in text
    assert "Item 7. Management's Discussion" in text
    assert "<p>" not in text

