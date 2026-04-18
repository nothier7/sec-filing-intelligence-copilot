from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from sec_copilot.db.models import Chunk
from sec_copilot.filings.chunking import chunk_section_text, deterministic_chunk_id
from sec_copilot.filings.sections import detect_filing_sections
from sec_copilot.filings.text import extract_text
from sec_copilot.repositories import ChunkRepository, FilingRepository


@dataclass(frozen=True)
class FilingParseResult:
    filing_id: int
    accession_number: str
    sections_created: int
    chunks_created: int


class FilingParseService:
    def __init__(
        self,
        session: Session,
        max_tokens: int = 800,
        overlap_tokens: int = 100,
    ) -> None:
        self.session = session
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.filings = FilingRepository(session)
        self.chunks = ChunkRepository(session)

    def parse_by_accession_number(self, accession_number: str) -> FilingParseResult:
        filing = self.filings.get_by_accession_number(accession_number)
        if filing is None:
            raise ValueError(f"Filing not found for accession number: {accession_number}")
        return self.parse_filing(filing.id)

    def parse_filing(self, filing_id: int) -> FilingParseResult:
        filing = self.filings.get(filing_id)
        if filing is None:
            raise ValueError(f"Filing not found: {filing_id}")
        if filing.raw_artifact_path is None:
            raise ValueError(f"Filing has no raw artifact path: {filing.accession_number}")

        raw_path = Path(filing.raw_artifact_path)
        if not raw_path.exists():
            raise FileNotFoundError(raw_path)

        document = raw_path.read_text(encoding="utf-8")
        text = extract_text(document)
        extracted_sections = detect_filing_sections(text, form_type=filing.form_type)

        self.chunks.delete_for_filing(filing.id)
        self.filings.delete_sections_for_filing(filing.id)

        chunks_created = 0
        for extracted_section in extracted_sections:
            section = self.filings.add_section(
                filing_id=filing.id,
                section_name=extracted_section.section_name,
                normalized_section_type=extracted_section.normalized_section_type,
                sequence=extracted_section.sequence,
                text_hash=extracted_section.text_hash,
            )
            text_chunks = chunk_section_text(
                text=extracted_section.text,
                source_offset=extracted_section.start_offset,
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )
            for text_chunk in text_chunks:
                self.chunks.add(
                    Chunk(
                        id=deterministic_chunk_id(
                            filing.accession_number,
                            extracted_section.sequence,
                            text_chunk.sequence,
                        ),
                        filing_id=filing.id,
                        section_id=section.id,
                        text=text_chunk.text,
                        token_count=text_chunk.token_count,
                        metadata_json={
                            "accession_number": filing.accession_number,
                            "cik": filing.cik,
                            "filing_date": filing.filing_date.isoformat(),
                            "fiscal_quarter": filing.fiscal_quarter,
                            "fiscal_year": filing.fiscal_year,
                            "form_type": filing.form_type,
                            "report_date": filing.report_date.isoformat()
                            if filing.report_date
                            else None,
                            "section_name": extracted_section.section_name,
                            "section_sequence": extracted_section.sequence,
                            "section_type": extracted_section.normalized_section_type,
                            "source_url": filing.source_url,
                        },
                        source_start=text_chunk.source_start,
                        source_end=text_chunk.source_end,
                    )
                )
                chunks_created += 1

        return FilingParseResult(
            filing_id=filing.id,
            accession_number=filing.accession_number,
            sections_created=len(extracted_sections),
            chunks_created=chunks_created,
        )

