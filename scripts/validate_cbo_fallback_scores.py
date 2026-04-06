"""
Validate fallback CBO score JSON before importing.

Checks:
- JSON structure and required fields
- Duplicate bill IDs
- bill_id format
- bill_id presence in bills.db

Usage:
    python scripts/validate_cbo_fallback_scores.py
    python scripts/validate_cbo_fallback_scores.py --file bill_tracker/cbo_manual_scores.json --db fiscal_model/data_files/bills.db
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bill_tracker.database import BillDatabase

DEFAULT_DB_PATH = Path(__file__).parent.parent / "fiscal_model" / "data_files" / "bills.db"
DEFAULT_FALLBACK_PATH = Path(__file__).parent.parent / "bill_tracker" / "cbo_manual_scores.json"

BILL_ID_RE = re.compile(r"^[a-z]+-\d+-\d+$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate fallback CBO score JSON.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help=f"Path to bills.db (default: {DEFAULT_DB_PATH})")
    parser.add_argument(
        "--file",
        default=str(DEFAULT_FALLBACK_PATH),
        help=f"Path to fallback CBO JSON file (default: {DEFAULT_FALLBACK_PATH})",
    )
    return parser


def _load_raw_scores(file_path: Path) -> list[dict]:
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return []
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: Failed to parse JSON: {exc}")
        return []

    scores = payload.get("scores", payload) if isinstance(payload, dict) else payload
    if not isinstance(scores, list):
        print("ERROR: Expected root list or {'scores': [...]}.")
        return []

    return [row for row in scores if isinstance(row, dict)]


def main() -> int:
    args = build_parser().parse_args()
    file_path = Path(args.file)
    db = BillDatabase(args.db)

    rows = _load_raw_scores(file_path)
    if not rows:
        print("No fallback CBO entries found.")
        return 0

    bill_ids = [str(row.get("bill_id", "")).strip() for row in rows]
    duplicate_ids = [bill_id for bill_id, count in Counter(bill_ids).items() if bill_id and count > 1]

    missing_required = []
    bad_bill_id_format = []
    invalid_cost = []
    unknown_bill_ids = []

    for idx, row in enumerate(rows, start=1):
        bill_id = str(row.get("bill_id", "")).strip()
        cost_raw = row.get("ten_year_cost_billions")

        if not bill_id or cost_raw is None:
            missing_required.append((idx, bill_id))
            continue

        if not BILL_ID_RE.match(bill_id):
            bad_bill_id_format.append((idx, bill_id))

        try:
            float(cost_raw)
        except (TypeError, ValueError):
            invalid_cost.append((idx, bill_id, cost_raw))

        if db.get_bill(bill_id) is None:
            unknown_bill_ids.append((idx, bill_id))

    print(f"Validated {len(rows)} fallback entries from {file_path}")
    print(f"- Duplicate bill_id entries: {len(duplicate_ids)}")
    print(f"- Missing required fields: {len(missing_required)}")
    print(f"- Invalid bill_id format: {len(bad_bill_id_format)}")
    print(f"- Invalid ten_year_cost_billions: {len(invalid_cost)}")
    print(f"- bill_id not found in DB: {len(unknown_bill_ids)}")

    if duplicate_ids:
        print("\nDuplicate bill_id values:")
        for bill_id in duplicate_ids:
            print(f"  - {bill_id}")

    if missing_required:
        print("\nMissing required fields (line index, bill_id):")
        for idx, bill_id in missing_required[:20]:
            print(f"  - #{idx}: {bill_id or '<missing>'}")

    if bad_bill_id_format:
        print("\nInvalid bill_id format:")
        for idx, bill_id in bad_bill_id_format[:20]:
            print(f"  - #{idx}: {bill_id}")

    if invalid_cost:
        print("\nInvalid ten_year_cost_billions values:")
        for idx, bill_id, raw in invalid_cost[:20]:
            print(f"  - #{idx}: {bill_id} -> {raw!r}")

    if unknown_bill_ids:
        print("\nEntries with bill_id not present in DB:")
        for idx, bill_id in unknown_bill_ids[:20]:
            print(f"  - #{idx}: {bill_id}")

    has_errors = bool(duplicate_ids or missing_required or bad_bill_id_format or invalid_cost)
    if has_errors:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
