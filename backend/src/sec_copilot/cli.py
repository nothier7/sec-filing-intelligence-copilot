from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from sec_copilot.db.session import session_scope
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


if __name__ == "__main__":
    main()

