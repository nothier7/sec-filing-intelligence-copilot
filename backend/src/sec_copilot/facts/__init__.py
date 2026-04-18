"""Structured XBRL fact lookup helpers."""

from sec_copilot.facts.metrics import MetricDefinition, match_metric
from sec_copilot.facts.service import FactLookupRequest, FactLookupResult, FactLookupService

__all__ = [
    "FactLookupRequest",
    "FactLookupResult",
    "FactLookupService",
    "MetricDefinition",
    "match_metric",
]
