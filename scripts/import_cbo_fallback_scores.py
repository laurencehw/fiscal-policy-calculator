"""
Import fallback CBO scores from JSON into bills.db.

Usage:
    python scripts/import_cbo_fallback_scores.py
    python scripts/import_cbo_fallback_scores.py --file bill_tracker/cbo_manual_scores.json --db fiscal_model/data_files/bills.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bill_tracker.cbo_fetcher import load_fallback_estimates
from bill_tracker.database import BillDatabase

DEFAULT_DB_PATH = Path(__file__).parent.parent / "fiscal_model" / "data_files" / "bills.db"
DEFAULT_FALLBACK_PATH = Path(__file__).parent.parent / "bill_tracker" / "cbo_manual_scores.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import fallback CBO scores into bills.db.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help=f"Path to bills.db (default: {DEFAULT_DB_PATH})")
    parser.add_argument(
        "--file",
        default=str(DEFAULT_FALLBACK_PATH),
        help=f"Path to fallback CBO JSON file (default: {DEFAULT_FALLBACK_PATH})",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db = BillDatabase(args.db)
    estimates = load_fallback_estimates(args.file)

    if not estimates:
        print(f"No fallback CBO scores found in {args.file}")
        return 0

    imported = 0
    skipped = 0
    for estimate in estimates:
        if not db.get_bill(estimate.bill_id):
            skipped += 1
            continue
        db.upsert_cbo_score(estimate)
        imported += 1

    print(f"Imported {imported} CBO fallback scores. Skipped {skipped} (bill_id not in DB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
