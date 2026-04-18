import warnings
from datetime import date
from pathlib import Path
from uuid import UUID

from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilters
from sqlalchemy.orm import Session

from sec_copilot.db.models import Company, Filing
from sec_copilot.filings import FilingParseService
from sec_copilot.repositories import CompanyRepository, FilingRepository
from sec_copilot.retrieval import (
    HashEmbedding,
    RetrievalFilters,
    RetrievalIndexService,
    chunk_to_node,
    hash_sparse_vectors,
    to_metadata_filters,
)
from sec_copilot.retrieval.qdrant import (
    QdrantIndexConfig,
    build_qdrant_index,
    build_qdrant_vector_store,
    qdrant_compatible_nodes,
    qdrant_point_id,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sec"


def test_hash_embedding_is_deterministic_and_normalized() -> None:
    embedder = HashEmbedding(dimensions=16)

    first = embedder.get_text_embedding("supply chain regulatory risks")
    second = embedder.get_text_embedding("supply chain regulatory risks")

    assert first == second
    assert len(first) == 16
    assert any(value > 0 for value in first)


def test_hash_sparse_vectors_are_deterministic_and_normalized() -> None:
    first_indices, first_values = hash_sparse_vectors(["supply chain regulatory risks"])
    second_indices, second_values = hash_sparse_vectors(["supply chain regulatory risks"])

    assert first_indices == second_indices
    assert first_values == second_values
    assert first_indices[0]
    assert round(sum(value * value for value in first_values[0]), 6) == 1.0


def test_chunk_to_node_preserves_citation_metadata(session: Session) -> None:
    filing_id = _create_parsed_fixture_filing(session)
    chunk = RetrievalIndexService(session=session).chunks.list_for_filing(filing_id)[0]

    node = chunk_to_node(chunk)

    assert node.node_id == chunk.id
    assert node.metadata["chunk_id"] == chunk.id
    assert node.metadata["accession_number"] == "0000320193-24-000123"
    assert node.metadata["source_url"] == "https://www.sec.gov/Archives/example.htm"


def test_to_metadata_filters_maps_retrieval_filters() -> None:
    filters = to_metadata_filters(
        RetrievalFilters(
            cik="0000320193",
            accession_number="0000320193-24-000123",
            form_type="10-K",
            fiscal_year=2024,
            section_type="risk_factors",
        )
    )

    assert isinstance(filters, MetadataFilters)
    assert {metadata_filter.key: metadata_filter.value for metadata_filter in filters.filters} == {
        "accession_number": "0000320193-24-000123",
        "cik": "0000320193",
        "fiscal_year": 2024,
        "form_type": "10-K",
        "section_type": "risk_factors",
    }


def test_retrieval_service_retrieves_filtered_chunks(session: Session) -> None:
    filing_id = _create_parsed_fixture_filing(session)
    service = RetrievalIndexService(session=session, embed_model=HashEmbedding(dimensions=32))

    results = service.retrieve_for_filing(
        filing_id=filing_id,
        query="competitive supply chain regulatory risks",
        top_k=2,
        filters=RetrievalFilters(section_type="risk_factors"),
    )

    assert results
    assert all(result.metadata["section_type"] == "risk_factors" for result in results)
    assert "supply chain" in results[0].text
    assert results[0].score is not None


def test_build_qdrant_vector_store_supports_local_path(tmp_path: Path) -> None:
    vector_store = build_qdrant_vector_store(
        QdrantIndexConfig(collection_name="test_sec_filings", path=tmp_path / "qdrant")
    )

    assert vector_store.collection_name == "test_sec_filings"


def test_build_qdrant_vector_store_supports_local_hybrid_hashing(tmp_path: Path) -> None:
    vector_store = build_qdrant_vector_store(
        QdrantIndexConfig(
            collection_name="test_sec_filings",
            path=tmp_path / "qdrant",
            enable_hybrid=True,
        )
    )

    assert vector_store.enable_hybrid is True
    assert vector_store._sparse_doc_fn is hash_sparse_vectors
    assert vector_store._sparse_query_fn is hash_sparse_vectors


def test_qdrant_compatible_nodes_use_stable_uuid_point_ids() -> None:
    source_node = TextNode(
        id_="0000320193-24-000123:s0002:c0003",
        text="Supply chain regulatory risks.",
        extra_info={"section_type": "risk_factors"},
    )

    qdrant_node = qdrant_compatible_nodes([source_node])[0]

    UUID(qdrant_node.node_id)
    assert qdrant_node.node_id == qdrant_point_id(source_node.node_id)
    assert qdrant_node.metadata["chunk_id"] == source_node.node_id
    assert qdrant_node.metadata["section_type"] == "risk_factors"


def test_build_qdrant_index_supports_local_hybrid_indexing(tmp_path: Path) -> None:
    nodes = [
        TextNode(
            id_="0000320193-24-000123:s0002:c0001",
            text="Supply chain regulatory risks may affect margins.",
            extra_info={"section_type": "risk_factors"},
        ),
        TextNode(
            id_="0000320193-24-000123:s0003:c0001",
            text="Revenue increased due to services growth.",
            extra_info={"section_type": "mda"},
        ),
    ]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Payload indexes have no effect.*")
        warnings.filterwarnings("ignore", message="`search_batch` method is deprecated.*")
        index = build_qdrant_index(
            nodes,
            config=QdrantIndexConfig(
                collection_name="test_sec_filings",
                path=tmp_path / "qdrant-index",
                enable_hybrid=True,
            ),
            embed_model=HashEmbedding(dimensions=32),
        )
        results = index.as_retriever(similarity_top_k=1).retrieve("supply chain risks")

    assert results[0].node.metadata["chunk_id"] == "0000320193-24-000123:s0002:c0001"


def _create_parsed_fixture_filing(session: Session) -> int:
    company = CompanyRepository(session).add(
        Company(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    filing = FilingRepository(session).add(
        Filing(
            company_id=company.id,
            accession_number="0000320193-24-000123",
            cik=company.cik,
            form_type="10-K",
            filing_date=date(2024, 11, 1),
            report_date=date(2024, 9, 28),
            fiscal_year=2024,
            source_url="https://www.sec.gov/Archives/example.htm",
            raw_artifact_path=(FIXTURE_DIR / "aapl-20240928.htm").as_posix(),
        )
    )
    session.commit()

    FilingParseService(session=session, max_tokens=12, overlap_tokens=2).parse_filing(filing.id)
    session.commit()
    return filing.id
