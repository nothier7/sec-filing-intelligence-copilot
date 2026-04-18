from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sec_copilot.db.models import Chunk
from sec_copilot.retrieval.llamaindex_compat import suppress_llamaindex_import_noise

with suppress_llamaindex_import_noise():
    from llama_index.core.schema import TextNode


def chunk_to_node(chunk: Chunk) -> TextNode:
    metadata = _metadata_for_chunk(chunk)
    return TextNode(
        id_=chunk.id,
        text=chunk.text,
        extra_info=metadata,
        start_char_idx=chunk.source_start,
        end_char_idx=chunk.source_end,
    )


def chunks_to_nodes(chunks: Iterable[Chunk]) -> list[TextNode]:
    return [chunk_to_node(chunk) for chunk in chunks]


def _metadata_for_chunk(chunk: Chunk) -> dict[str, Any]:
    metadata = dict(chunk.metadata_json or {})
    metadata.update(
        {
            "chunk_id": chunk.id,
            "filing_id": chunk.filing_id,
            "section_id": chunk.section_id,
            "source_end": chunk.source_end,
            "source_start": chunk.source_start,
            "token_count": chunk.token_count,
        }
    )
    return metadata
