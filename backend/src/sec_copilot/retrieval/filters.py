from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sec_copilot.retrieval.llamaindex_compat import suppress_llamaindex_import_noise

with suppress_llamaindex_import_noise():
    from llama_index.core.vector_stores import FilterCondition, MetadataFilter, MetadataFilters


@dataclass(frozen=True)
class RetrievalFilters:
    cik: Optional[str] = None
    accession_number: Optional[str] = None
    form_type: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    section_type: Optional[str] = None


def to_metadata_filters(filters: Optional[RetrievalFilters]) -> Optional[MetadataFilters]:
    if filters is None:
        return None

    metadata_filters: list[MetadataFilter] = []
    _append_filter(metadata_filters, "cik", filters.cik)
    _append_filter(metadata_filters, "accession_number", filters.accession_number)
    _append_filter(metadata_filters, "form_type", filters.form_type)
    _append_filter(metadata_filters, "fiscal_year", filters.fiscal_year)
    _append_filter(metadata_filters, "fiscal_quarter", filters.fiscal_quarter)
    _append_filter(metadata_filters, "section_type", filters.section_type)

    if not metadata_filters:
        return None
    return MetadataFilters(filters=metadata_filters, condition=FilterCondition.AND)


def _append_filter(filters: list[MetadataFilter], key: str, value: object) -> None:
    if value is None:
        return
    filters.append(MetadataFilter(key=key, value=value))
