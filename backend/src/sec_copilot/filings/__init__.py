"""Filing parsing, section detection, and chunking."""

from sec_copilot.filings.chunking import TextChunk, chunk_section_text
from sec_copilot.filings.parser import FilingParseResult, FilingParseService
from sec_copilot.filings.sections import ExtractedSection, detect_filing_sections
from sec_copilot.filings.text import extract_text

__all__ = [
    "ExtractedSection",
    "FilingParseResult",
    "FilingParseService",
    "TextChunk",
    "chunk_section_text",
    "detect_filing_sections",
    "extract_text",
]

