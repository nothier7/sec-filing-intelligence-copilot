from __future__ import annotations

import warnings
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid5

from sec_copilot.retrieval.embeddings import HashEmbedding
from sec_copilot.retrieval.llamaindex_compat import suppress_llamaindex_import_noise
from sec_copilot.retrieval.sparse import hash_sparse_vectors

with suppress_llamaindex_import_noise():
    from qdrant_client import QdrantClient
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.core.schema import TextNode
    from llama_index.vector_stores.qdrant import QdrantVectorStore

QDRANT_POINT_NAMESPACE = UUID("a1293f11-2bd0-45c4-a1cb-d7eba4c13fa7")


@dataclass(frozen=True)
class QdrantIndexConfig:
    collection_name: str = "sec_filings"
    url: Optional[str] = None
    path: Optional[Path] = None
    enable_hybrid: bool = False
    batch_size: int = 64
    fastembed_sparse_model: Optional[str] = None


def build_qdrant_vector_store(config: QdrantIndexConfig) -> QdrantVectorStore:
    sparse_doc_fn = None
    sparse_query_fn = None
    if config.enable_hybrid and config.fastembed_sparse_model is None:
        sparse_doc_fn = hash_sparse_vectors
        sparse_query_fn = hash_sparse_vectors

    if config.path is not None:
        client = QdrantClient(path=config.path.as_posix())
        return QdrantVectorStore(
            collection_name=config.collection_name,
            client=client,
            enable_hybrid=config.enable_hybrid,
            batch_size=config.batch_size,
            fastembed_sparse_model=config.fastembed_sparse_model,
            sparse_doc_fn=sparse_doc_fn,
            sparse_query_fn=sparse_query_fn,
        )

    return QdrantVectorStore(
        collection_name=config.collection_name,
        url=config.url,
        enable_hybrid=config.enable_hybrid,
        batch_size=config.batch_size,
        fastembed_sparse_model=config.fastembed_sparse_model,
        sparse_doc_fn=sparse_doc_fn,
        sparse_query_fn=sparse_query_fn,
    )


def build_qdrant_index(
    nodes: list[TextNode],
    config: QdrantIndexConfig,
    embed_model: Optional[HashEmbedding] = None,
) -> VectorStoreIndex:
    vector_store = build_qdrant_vector_store(config)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    warning_context = warnings.catch_warnings() if config.path is not None else nullcontext()
    with warning_context:
        if config.path is not None:
            warnings.filterwarnings("ignore", message="Payload indexes have no effect.*")
        return VectorStoreIndex(
            qdrant_compatible_nodes(nodes),
            storage_context=storage_context,
            embed_model=embed_model or HashEmbedding(),
        )


def qdrant_point_id(node_id: str) -> str:
    return str(uuid5(QDRANT_POINT_NAMESPACE, node_id))


def qdrant_compatible_nodes(nodes: list[TextNode]) -> list[TextNode]:
    compatible_nodes: list[TextNode] = []
    for node in nodes:
        metadata = dict(node.metadata or {})
        metadata.setdefault("chunk_id", node.node_id)
        compatible_nodes.append(
            node.copy(
                update={
                    "id_": qdrant_point_id(node.node_id),
                    "metadata": metadata,
                }
            )
        )
    return compatible_nodes
