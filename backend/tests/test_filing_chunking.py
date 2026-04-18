import pytest

from sec_copilot.filings.chunking import chunk_section_text, deterministic_chunk_id


def test_chunk_section_text_uses_token_windows_and_offsets() -> None:
    text = "one two three four five six seven"

    chunks = chunk_section_text(text, source_offset=10, max_tokens=3, overlap_tokens=1)

    assert [chunk.text for chunk in chunks] == [
        "one two three",
        "three four five",
        "five six seven",
    ]
    assert [chunk.token_count for chunk in chunks] == [3, 3, 3]
    assert chunks[0].source_start == 10
    assert chunks[0].source_end == 23


def test_chunk_section_text_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_section_text("one two", max_tokens=2, overlap_tokens=2)


def test_deterministic_chunk_id_is_stable() -> None:
    assert (
        deterministic_chunk_id("0000320193-24-000123", section_sequence=2, chunk_sequence=3)
        == "0000320193-24-000123:s0002:c0003"
    )

