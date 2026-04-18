from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from sec_copilot.retrieval.embeddings import HashEmbedding
from sec_copilot.retrieval.filters import RetrievalFilters, to_metadata_filters
from sec_copilot.retrieval.llamaindex_compat import suppress_llamaindex_import_noise
from sec_copilot.retrieval.nodes import chunks_to_nodes
from sec_copilot.retrieval.qdrant import QdrantIndexConfig, build_qdrant_index
from sec_copilot.repositories import ChunkRepository, FilingRepository

with suppress_llamaindex_import_noise():
    from llama_index.core import VectorStoreIndex


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    score: Optional[float]
    text: str
    metadata: dict[str, Any]


class RetrievalIndexService:
    def __init__(self, session: Session, embed_model: Optional[HashEmbedding] = None) -> None:
        self.session = session
        self.embed_model = embed_model or HashEmbedding()
        self.filings = FilingRepository(session)
        self.chunks = ChunkRepository(session)

    def nodes_for_filing(self, filing_id: int) -> list:
        chunks = self.chunks.list_for_filing(filing_id)
        return chunks_to_nodes(chunks)

    def nodes_for_accession_number(self, accession_number: str) -> list:
        filing = self.filings.get_by_accession_number(accession_number)
        if filing is None:
            raise ValueError(f"Filing not found for accession number: {accession_number}")
        return self.nodes_for_filing(filing.id)

    def build_in_memory_index_for_filing(self, filing_id: int) -> VectorStoreIndex:
        nodes = self.nodes_for_filing(filing_id)
        if not nodes:
            raise ValueError(f"No chunks found for filing: {filing_id}")
        return VectorStoreIndex(nodes, embed_model=self.embed_model)

    def build_qdrant_index_for_filing(
        self,
        filing_id: int,
        config: QdrantIndexConfig,
    ) -> VectorStoreIndex:
        nodes = self.nodes_for_filing(filing_id)
        if not nodes:
            raise ValueError(f"No chunks found for filing: {filing_id}")
        return build_qdrant_index(nodes, config=config, embed_model=self.embed_model)

    def retrieve_for_filing(
        self,
        filing_id: int,
        query: str,
        top_k: int = 5,
        filters: Optional[RetrievalFilters] = None,
    ) -> list[RetrievalResult]:
        index = self.build_in_memory_index_for_filing(filing_id)
        retriever_kwargs: dict[str, Any] = {"similarity_top_k": top_k}
        metadata_filters = to_metadata_filters(filters)
        if metadata_filters is not None:
            retriever_kwargs["filters"] = metadata_filters

        source_nodes = index.as_retriever(**retriever_kwargs).retrieve(query)
        return [
            RetrievalResult(
                chunk_id=str(node.node.metadata.get("chunk_id", node.node.node_id)),
                score=node.score,
                text=node.node.get_text(),
                metadata=dict(node.node.metadata),
            )
            for node in source_nodes
        ]
