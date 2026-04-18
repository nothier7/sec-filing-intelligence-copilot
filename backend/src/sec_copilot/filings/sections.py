from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExtractedSection:
    section_name: str
    normalized_section_type: str
    sequence: int
    text: str
    text_hash: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class SectionPattern:
    normalized_section_type: str
    pattern: re.Pattern[str]


SECTION_PATTERNS = [
    SectionPattern("business", re.compile(r"^item\s+1\.?\s+business\b", re.IGNORECASE)),
    SectionPattern("risk_factors", re.compile(r"^item\s+1a\.?\s+risk\s+factors\b", re.IGNORECASE)),
    SectionPattern(
        "mda",
        re.compile(
            r"^item\s+(?:2|7)\.?\s+management.?s\s+discussion\s+and\s+analysis\b",
            re.IGNORECASE,
        ),
    ),
    SectionPattern(
        "legal_proceedings",
        re.compile(r"^item\s+(?:1|3)\.?\s+legal\s+proceedings\b", re.IGNORECASE),
    ),
    SectionPattern(
        "controls",
        re.compile(r"^item\s+(?:4|9a)\.?\s+controls\s+and\s+procedures\b", re.IGNORECASE),
    ),
    SectionPattern("financial_statements", re.compile(r"^item\s+8\.?\s+financial\s+statements\b", re.IGNORECASE)),
]


@dataclass(frozen=True)
class _Marker:
    section_name: str
    normalized_section_type: str
    offset: int


def detect_filing_sections(text: str, form_type: str) -> list[ExtractedSection]:
    del form_type
    markers = _find_markers(text)
    if not markers:
        return [
            ExtractedSection(
                section_name="Document",
                normalized_section_type="document",
                sequence=1,
                text=text,
                text_hash=_hash_text(text),
                start_offset=0,
                end_offset=len(text),
            )
        ]

    sections: list[ExtractedSection] = []
    for index, marker in enumerate(markers):
        next_offset = markers[index + 1].offset if index + 1 < len(markers) else len(text)
        section_text = text[marker.offset:next_offset].strip()
        if not section_text:
            continue
        sections.append(
            ExtractedSection(
                section_name=marker.section_name,
                normalized_section_type=marker.normalized_section_type,
                sequence=len(sections) + 1,
                text=section_text,
                text_hash=_hash_text(section_text),
                start_offset=marker.offset,
                end_offset=next_offset,
            )
        )
    return sections


def _find_markers(text: str) -> list[_Marker]:
    markers: list[_Marker] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        normalized = _normalize_heading(stripped)
        section_type = _classify_heading(normalized)
        if section_type is not None:
            markers.append(
                _Marker(
                    section_name=stripped,
                    normalized_section_type=section_type,
                    offset=offset + line.find(stripped),
                )
            )
        offset += len(line)
    return _dedupe_nearby_markers(markers)


def _classify_heading(heading: str) -> Optional[str]:
    if not heading or len(heading) > 180:
        return None
    for section_pattern in SECTION_PATTERNS:
        if section_pattern.pattern.search(heading):
            return section_pattern.normalized_section_type
    return None


def _normalize_heading(heading: str) -> str:
    heading = heading.replace("\xa0", " ")
    heading = re.sub(r"\s+", " ", heading)
    heading = heading.strip(" .:-\t")
    return heading


def _dedupe_nearby_markers(markers: list[_Marker]) -> list[_Marker]:
    if not markers:
        return []
    deduped = [markers[0]]
    for marker in markers[1:]:
        previous = deduped[-1]
        if (
            marker.normalized_section_type == previous.normalized_section_type
            and marker.offset - previous.offset < 200
        ):
            continue
        deduped.append(marker)
    return deduped


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

