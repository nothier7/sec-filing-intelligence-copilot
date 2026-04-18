from sec_copilot.answering.synthesis import best_evidence_snippet
from sec_copilot.retrieval import RetrievalResult


def test_best_evidence_snippet_prefers_fact_table_row_over_page_marker() -> None:
    result = RetrievalResult(
        chunk_id="chunk-1",
        score=0.5,
        text="""
Apple Inc. | 2025 Form 10-K | 22

The following table shows net sales by category for 2025, 2024 and 2023
(dollars in millions):

2025
Change
2024
Change
2023
Services
$
109,158
14
%
$
96,169
13
%
$
85,200
Total net sales
$
416,161
6
%
$
391,035
2
%
$
383,285
""",
        metadata={},
    )

    snippet = best_evidence_snippet(
        "How much revenue did Apple report in 2025? revenue 416,161",
        result,
    )

    assert "Total net sales" in snippet
    assert "416,161" in snippet
    assert snippet != "Apple Inc. | 2025 Form 10-K | 22"


def test_best_evidence_snippet_penalizes_short_boilerplate() -> None:
    result = RetrievalResult(
        chunk_id="chunk-1",
        score=0.5,
        text="""
Apple Inc.

Operating expenses for 2025, 2024 and 2023 were as follows
(dollars in millions):
""",
        metadata={},
    )

    snippet = best_evidence_snippet("What were Apple operating expenses in 2025?", result)

    assert snippet.startswith("Operating expenses")


def test_best_evidence_snippet_prefers_label_over_numeric_leading_fragment() -> None:
    result = RetrievalResult(
        chunk_id="chunk-1",
        score=0.5,
        text="""
Total net sales
$
416,161
6
%
$
391,035
2
%
$
383,285

(1)Services net sales include amortization of the deferred value of services bundled in the sales price of certain products.

iPhone

iPhone net sales increased during 2025 compared to 2024 due to higher net sales of Pro models.
""",
        metadata={},
    )

    snippet = best_evidence_snippet(
        "How much revenue did Apple report in 2025? revenue 416,161,000,000",
        result,
    )

    assert snippet.startswith("Total net sales")
    assert "416,161" in snippet


def test_best_evidence_snippet_prefers_target_value_over_table_header() -> None:
    result = RetrievalResult(
        chunk_id="chunk-1",
        score=0.5,
        text="""
Operating Expenses

Operating expenses for 2025, 2024 and 2023 were as follows (dollars in millions):

2025
Change
2024
Change
2023
Research and development
$
34,550
10
%
$
31,370
5
%
$
29,915
Total operating expenses
$
62,151
8
%
$
57,467
5
%
$
54,847
""",
        metadata={},
    )

    snippet = best_evidence_snippet(
        "What were Apple's operating expenses in 2025? operating expenses 62,151,000,000",
        result,
    )

    assert snippet.startswith("Total operating expenses")
    assert "62,151" in snippet
    assert "34,550" not in snippet
