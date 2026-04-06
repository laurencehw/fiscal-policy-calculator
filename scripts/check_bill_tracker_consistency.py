"""
Run Bill Tracker consistency checks against a SQLite database.

Checks:
- Core table counts
- has_cbo_score flag vs cbo_estimates consistency
- Multiple CBO publications per bill
- Exact duplicate CBO estimate rows
- mapping_overrides integrity and potential staleness
- Optional drift check against fallback JSON IDs

Usage:
    python scripts/check_bill_tracker_consistency.py
    python scripts/check_bill_tracker_consistency.py --db C:/path/to/bills.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "fiscal_model" / "data_files" / "bills.db"
DEFAULT_FALLBACK_PATH = Path(__file__).parent.parent / "bill_tracker" / "cbo_manual_scores.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Bill Tracker DB consistency.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help=f"Path to bills.db (default: {DEFAULT_DB_PATH})")
    parser.add_argument(
        "--fallback-file",
        default=str(DEFAULT_FALLBACK_PATH),
        help=f"Path to fallback CBO JSON (default: {DEFAULT_FALLBACK_PATH})",
    )
    return parser


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def _load_fallback_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    scores = payload.get("scores", payload) if isinstance(payload, dict) else payload
    if not isinstance(scores, list):
        return []
    ids = []
    for row in scores:
        if not isinstance(row, dict):
            continue
        bill_id = str(row.get("bill_id", "")).strip()
        if bill_id:
            ids.append(bill_id)
    return ids


def main() -> int:
    args = build_parser().parse_args()
    db_path = args.db

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        _print_section("Counts")
        bills_total = c.execute("select count(*) from bills").fetchone()[0]
        has_cbo = c.execute("select count(*) from bills where has_cbo_score=1").fetchone()[0]
        cbo_rows = c.execute("select count(*) from cbo_estimates").fetchone()[0]
        print(f"bills total: {bills_total}")
        print(f"bills with has_cbo_score=1: {has_cbo}")
        print(f"cbo_estimates rows: {cbo_rows}")

        _print_section("Flag/Estimate Mismatches")
        has_flag_without_estimate = c.execute(
            """
            select count(*)
            from bills b
            left join cbo_estimates c on b.bill_id=c.bill_id
            where b.has_cbo_score=1 and c.bill_id is null
            """
        ).fetchone()[0]
        estimate_but_flag_zero = c.execute(
            """
            select count(distinct b.bill_id)
            from bills b
            join cbo_estimates c on b.bill_id=c.bill_id
            where b.has_cbo_score=0
            """
        ).fetchone()[0]
        print(f"has_cbo_score=1 but no estimate row: {has_flag_without_estimate}")
        print(f"estimate row exists but has_cbo_score=0: {estimate_but_flag_zero}")

        _print_section("Multiple Publications")
        dup_bills = c.execute(
            """
            select bill_id, count(*) as cnt
            from cbo_estimates
            group by bill_id
            having cnt > 1
            order by cnt desc, bill_id
            """
        ).fetchall()
        print(f"bills with multiple CBO publications: {len(dup_bills)}")
        for bill_id, cnt in dup_bills[:20]:
            print(f"- {bill_id}: {cnt}")

        _print_section("Exact Duplicate Rows")
        exact_dups = c.execute(
            """
            select bill_id, estimate_date, ten_year_cost_billions, coalesce(cbo_url, ''), count(*) as cnt
            from cbo_estimates
            group by bill_id, estimate_date, ten_year_cost_billions, coalesce(cbo_url, '')
            having cnt > 1
            order by cnt desc, bill_id
            """
        ).fetchall()
        print(f"exact duplicate estimate rows: {len(exact_dups)}")
        for row in exact_dups[:20]:
            print(f"- {row}")

        _print_section("Estimate Quality")
        zero_cost_rows = c.execute(
            "select count(*) from cbo_estimates where abs(coalesce(ten_year_cost_billions, 0.0)) < 1e-9"
        ).fetchone()[0]
        blank_date_rows = c.execute(
            "select count(*) from cbo_estimates where estimate_date is null or trim(estimate_date) = ''"
        ).fetchone()[0]
        print(f"zero-cost rows: {zero_cost_rows}")
        print(f"blank estimate_date rows: {blank_date_rows}")

        counts = [r[0] for r in c.execute("select count(*) from cbo_estimates group by bill_id").fetchall()]
        if counts:
            print(
                "publications per scored bill: "
                f"min={min(counts)}, p50={statistics.median(counts)}, max={max(counts)}"
            )

        _print_section("Overrides")
        ov_total = c.execute("select count(*) from mapping_overrides").fetchone()[0]
        print(f"mapping_overrides rows: {ov_total}")
        missing_override_bills = c.execute(
            """
            select m.bill_id
            from mapping_overrides m
            left join bills b on m.bill_id=b.bill_id
            where b.bill_id is null
            """
        ).fetchall()
        print(f"overrides with bill_id missing from bills table: {len(missing_override_bills)}")
        for (bill_id,) in missing_override_bills[:20]:
            print(f"- {bill_id}")

        stale_override_candidates = c.execute(
            """
            select m.bill_id
            from mapping_overrides m
            join bills b on m.bill_id=b.bill_id
            where b.has_cbo_score=1
            """
        ).fetchall()
        print(
            "override bill_ids that now have official CBO score "
            f"(candidate stale overrides): {len(stale_override_candidates)}"
        )
        for (bill_id,) in stale_override_candidates[:20]:
            print(f"- {bill_id}")

        _print_section("Fallback File Drift")
        fallback_ids = _load_fallback_ids(Path(args.fallback_file))
        print(f"fallback score entries: {len(fallback_ids)}")
        if fallback_ids:
            db_ids = {r[0] for r in c.execute("select bill_id from bills").fetchall()}
            missing_in_db = [bill_id for bill_id in fallback_ids if bill_id not in db_ids]
            duplicates = [bill_id for bill_id, count in Counter(fallback_ids).items() if count > 1]
            print(f"fallback bill_ids missing from DB: {len(missing_in_db)}")
            print(f"duplicate bill_ids in fallback file: {len(duplicates)}")
            for bill_id in missing_in_db[:20]:
                print(f"- missing in DB: {bill_id}")
            for bill_id in duplicates[:20]:
                print(f"- duplicate in fallback: {bill_id}")

        conn.close()
        return 0

    except sqlite3.DatabaseError as exc:
        print(f"ERROR: Unable to read SQLite database at {db_path}: {exc}")
        print("If this DB is on VirtioFS/mounted storage, run this checker on the local copy instead.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
