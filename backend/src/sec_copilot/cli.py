from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from sec_copilot.db.session import session_scope
from sec_copilot.filings import FilingParseService
from sec_copilot.ingestion import SecIngestionService
from sec_copilot.sec import SecClient


def build_parser() -> argparse.ArgumentParser:
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


if __name__ == "__main__":
    main()
