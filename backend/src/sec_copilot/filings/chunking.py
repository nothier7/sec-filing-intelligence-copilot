from __future__ import annotations

import re
from dataclasses import dataclass


TOKEN_PATTERN = re.compile(r"\S+")


@dataclass(frozen=True)
class TextChunk:
    sequence: int
    text: str
    token_count: int
    source_start: int
    source_end: int


def chunk_section_text(
    text: str,
    source_offset: int = 0,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[TextChunk]:
    if max_tokens < 1:
        raise ValueError("max_tokens must be at least 1")
    if overlap_tokens < 0:
        raise ValueError("overlap_tokens cannot be negative")
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")

    matches = list(TOKEN_PATTERN.finditer(text))
    if not matches:
        return []

    chunks: list[TextChunk] = []
    start_token = 0
    while start_token < len(matches):
        end_token = min(start_token + max_tokens, len(matches))
        start_char = matches[start_token].start()
        end_char = matches[end_token - 1].end()
        chunk_text = text[start_char:end_char].strip()
        chunks.append(
            TextChunk(
                sequence=len(chunks) + 1,
                text=chunk_text,
                token_count=end_token - start_token,
                source_start=source_offset + start_char,
                source_end=source_offset + end_char,
            )
        )
        if end_token == len(matches):
            break
        start_token = end_token - overlap_tokens
    return chunks


def deterministic_chunk_id(accession_number: str, section_sequence: int, chunk_sequence: int) -> str:
    return f"{accession_number}:s{section_sequence:04d}:c{chunk_sequence:04d}"

