from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sec_copilot.config import get_settings
from sec_copilot.db.session import session_scope
from sec_copilot.filings import FilingParseService
from sec_copilot.ingestion import SecIngestionService
from sec_copilot.sec import SecClient


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="sec-copilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest-sec-company", help="Ingest one company from SEC EDGAR")
    ingest.add_argument("cik", help="Company CIK, with or without leading zeros")
    ingest.add_argument("--limit", type=int, default=10, help="Maximum filings to ingest")
    ingest.add_argument(
        "--forms",
        nargs="+",
        default=["10-K", "10-Q"],
        help="SEC form types to ingest",
    )
    ingest.add_argument(
        "--skip-documents",
        action="store_true",
        help="Skip filing document downloads and only store metadata plus company facts",
    )
    ingest.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cached SEC JSON/documents and refetch from SEC",
    )

    parse = subparsers.add_parser(
        "parse-sec-filing",
        help="Parse one cached SEC filing into sections and chunks",
    )
    parse.add_argument("accession_number", help="SEC accession number with dashes")
    parse.add_argument("--max-tokens", type=int, default=800, help="Maximum tokens per chunk")
    parse.add_argument("--overlap-tokens", type=int, default=100, help="Overlapping tokens per chunk")

    retrieve = subparsers.add_parser(
        "retrieve-sec-filing",
        help="Run local retrieval over parsed chunks for one SEC filing",
    )
    retrieve.add_argument("accession_number", help="SEC accession number with dashes")
    retrieve.add_argument("query", help="Retrieval query")
    retrieve.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    retrieve.add_argument("--section-type", help="Optional normalized section type filter")

    ask = subparsers.add_parser(
        "ask-sec-filing",
        help="Answer one question over a parsed SEC filing with citations",
    )
    ask.add_argument("accession_number", help="SEC accession number with dashes")
    ask.add_argument("question", help="Question to answer")
    ask.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    ask.add_argument("--section-type", help="Optional normalized section type filter")

    compare = subparsers.add_parser(
        "compare-sec-filing",
        help="Compare one filing section against a previous filing",
    )
    compare.add_argument("accession_number", help="Current SEC accession number with dashes")
    compare.add_argument(
        "--section-type",
        default="risk_factors",
        help="Normalized section type to compare",
    )
    compare.add_argument("--previous-accession-number", help="Optional prior filing accession")
    compare.add_argument("--max-claims", type=int, default=5, help="Maximum added/removed claims")

    run_eval = subparsers.add_parser(
        "run-eval",
        help="Run the local SEC RAG benchmark and generate eval artifacts",
    )
    run_eval.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/questions/sec_seed.jsonl"),
        help="JSONL benchmark question file",
    )
    run_eval.add_argument(
        "--variant",
        dest="variants",
        action="append",
        choices=["closed_book", "naive_rag", "improved_rag", "improved_rag_xbrl"],
        help="Variant to run. Repeat to run multiple variants. Defaults to all variants.",
    )
    run_eval.add_argument(
        "--output",
        type=Path,
        default=Path("evals/results/sec_seed_eval.json"),
        help="JSON result output path",
    )
    run_eval.add_argument(
        "--report",
        type=Path,
        default=Path("evals/results/sec_seed_eval.md"),
        help="Markdown report output path",
    )

    index = subparsers.add_parser(
        "index-sec-filing",
        help="Index one parsed SEC filing into Qdrant",
    )
    index.add_argument("accession_number", help="SEC accession number with dashes")
    index.add_argument(
        "--collection",
        default=settings.qdrant_collection,
        help="Qdrant collection name",
    )
    index.add_argument("--qdrant-url", default=settings.qdrant_url, help="Remote Qdrant URL")
    index.add_argument("--qdrant-path", help="Local Qdrant storage path")
    index.add_argument("--hybrid", action="store_true", help="Enable Qdrant hybrid search")
    index.add_argument(
        "--fastembed-sparse-model",
        help="Optional FastEmbed sparse model name for hybrid search",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ingest-sec-company":
        client = SecClient.from_settings()
        try:
            with session_scope() as session:
                result = SecIngestionService(session=session, client=client).ingest_company(
                    cik=args.cik,
                    form_types=args.forms,
                    filing_limit=args.limit,
                    download_documents=not args.skip_documents,
                    use_cache=not args.refresh,
                )
            print(json.dumps(asdict(result), indent=2, sort_keys=True))
        finally:
            client.close()
    elif args.command == "parse-sec-filing":
        with session_scope() as session:
            result = FilingParseService(
                session=session,
                max_tokens=args.max_tokens,
                overlap_tokens=args.overlap_tokens,
            ).parse_by_accession_number(args.accession_number)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    elif args.command == "retrieve-sec-filing":
        from sec_copilot.retrieval import RetrievalFilters, RetrievalIndexService

        with session_scope() as session:
            service = RetrievalIndexService(session=session)
            filing = service.filings.get_by_accession_number(args.accession_number)
            if filing is None:
                raise ValueError(f"Filing not found: {args.accession_number}")
            filters = RetrievalFilters(
                accession_number=args.accession_number,
                section_type=args.section_type,
            )
            results = service.retrieve_for_filing(
                filing_id=filing.id,
                query=args.query,
                top_k=args.top_k,
                filters=filters,
            )
        print(json.dumps([asdict(result) for result in results], indent=2, sort_keys=True))
    elif args.command == "ask-sec-filing":
        from sec_copilot.answering import AskRequest, CitedAnswerService

        with session_scope() as session:
            response = CitedAnswerService(session=session).answer(
                AskRequest(
                    accession_number=args.accession_number,
                    question=args.question,
                    top_k=args.top_k,
                    section_type=args.section_type,
                )
            )
        print(response.model_dump_json(indent=2))
    elif args.command == "compare-sec-filing":
        from sec_copilot.comparison import CompareRequest, FilingComparisonService

        with session_scope() as session:
            response = FilingComparisonService(session=session).compare(
                CompareRequest(
                    accession_number=args.accession_number,
                    section_type=args.section_type,
                    previous_accession_number=args.previous_accession_number,
                    max_claims=args.max_claims,
                )
            )
        print(response.model_dump_json(indent=2))
    elif args.command == "run-eval":
        from sec_copilot.evals import EvaluationRunner, format_eval_report, parse_variants

        variants = parse_variants(args.variants)
        with session_scope() as session:
            result = EvaluationRunner(session=session).run(
                dataset_path=args.dataset,
                variants=variants,
            )
        report = format_eval_report(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        args.report.write_text(report, encoding="utf-8")
        print(
            json.dumps(
                {
                    "dataset": result.dataset_path,
                    "question_count": result.question_count,
                    "variants": [variant.value for variant in variants],
                    "output": args.output.as_posix(),
                    "report": args.report.as_posix(),
                    "metrics": result.model_dump(mode="json")["metrics"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif args.command == "index-sec-filing":
        from sec_copilot.retrieval import RetrievalIndexService
        from sec_copilot.retrieval.qdrant import QdrantIndexConfig

        qdrant_path = Path(args.qdrant_path) if args.qdrant_path else None
        qdrant_url = None if qdrant_path else args.qdrant_url
        with session_scope() as session:
            service = RetrievalIndexService(session=session)
            filing = service.filings.get_by_accession_number(args.accession_number)
            if filing is None:
                raise ValueError(f"Filing not found: {args.accession_number}")
            service.build_qdrant_index_for_filing(
                filing_id=filing.id,
                config=QdrantIndexConfig(
                    collection_name=args.collection,
                    url=qdrant_url,
                    path=qdrant_path,
                    enable_hybrid=args.hybrid,
                    fastembed_sparse_model=args.fastembed_sparse_model if args.hybrid else None,
                ),
            )
        print(
            json.dumps(
                {
                    "accession_number": args.accession_number,
                    "collection": args.collection,
                    "indexed": True,
                    "qdrant_path": qdrant_path.as_posix() if qdrant_path else None,
                    "qdrant_url": qdrant_url,
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
