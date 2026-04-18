from pathlib import Path

from sec_copilot.filings import detect_filing_sections, extract_text

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_detect_filing_sections_identifies_major_10k_sections() -> None:
    html = (FIXTURE_DIR / "aapl-20240928.htm").read_text()
    text = extract_text(html)

    sections = detect_filing_sections(text, form_type="10-K")

    assert [section.normalized_section_type for section in sections] == [
        "business",
        "risk_factors",
        "mda",
        "controls",
    ]
    assert sections[1].section_name == "Item 1A. Risk Factors"
    assert "competitive, supply chain" in sections[1].text
    assert sections[1].text_hash


def test_detect_filing_sections_falls_back_to_document_section() -> None:
    sections = detect_filing_sections("No item headings here.", form_type="10-Q")

    assert len(sections) == 1
    assert sections[0].normalized_section_type == "document"
    assert sections[0].section_name == "Document"

