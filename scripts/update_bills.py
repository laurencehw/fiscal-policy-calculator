"""
Daily bill tracker update pipeline.

Usage:
    python scripts/update_bills.py [--full-refresh] [--verbose] [--limit N]

Schedule:
    Daily at 6 AM UTC via cron or Streamlit Cloud scheduled job:
    0 6 * * * cd /path/to/app && python scripts/update_bills.py

Environment variables:
    CONGRESS_API_KEY   — congress.gov API key (required)
    ANTHROPIC_API_KEY  — Anthropic API key for provision extraction (required)

Pipeline:
    1. Fetch new/updated bills from congress.gov (since last run)
    2. Fetch CBO cost estimates and match to bills
    3. Extract provisions via Claude Haiku LLM (skip if manual override exists)
    4. Auto-score each bill using the calculator's scoring pipeline
    5. Store everything to bills.db
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_DB_PATH = Path(__file__).parent.parent / "fiscal_model" / "data_files" / "bills.db"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Update bill tracker database from congress.gov and CBO."
    )
    p.add_argument(
        "--full-refresh",
        action="store_true",
        help="Re-fetch all bills from Jan 1, 2025 (ignores last-update timestamp)",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=250,
        help="Max bills to fetch per run (default: 250)",
    )
    p.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"Path to bills.db (default: {DEFAULT_DB_PATH})",
    )
    p.add_argument(
        "--skip-scoring",
        action="store_true",
        help="Skip auto-scoring (provision mapping + calculator)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and map but do not write to database",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("update_bills")

    # Validate API keys
    congress_key = os.environ.get("CONGRESS_API_KEY", "")
    if not congress_key:
        logger.warning(
            "CONGRESS_API_KEY not set. API calls will be rate-limited. "
            "Register for a free key at https://api.congress.gov/sign-up/"
        )

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key and not args.skip_scoring:
        logger.warning(
            "ANTHROPIC_API_KEY not set. Provision extraction will be skipped. "
            "Set this key to enable LLM-based provision mapping."
        )

    # Ensure DB directory exists
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Import pipeline components
    from bill_tracker.database import BillDatabase
    from bill_tracker.ingestor import BillIngestor
    from bill_tracker.cbo_fetcher import CBOScoreFetcher
    from bill_tracker.provision_mapper import ProvisionMapper
    from bill_tracker.auto_scorer import AutoScorer

    db = BillDatabase(str(db_path) if not args.dry_run else ":memory:")
    ingestor = BillIngestor(api_key=congress_key)
    cbo = CBOScoreFetcher()
    mapper = ProvisionMapper() if (anthropic_key and not args.skip_scoring) else None
    scorer = AutoScorer() if not args.skip_scoring else None

    # Determine fetch window
    if args.full_refresh:
        since = datetime(2025, 1, 1)
        logger.info("Full refresh: fetching bills since Jan 1, 2025")
    else:
        last_update = db.get_last_update()
        since = last_update if last_update else datetime.utcnow() - timedelta(days=7)
        logger.info("Incremental update since %s", since.strftime("%Y-%m-%d"))

    # Step 1: Fetch bills
    logger.info("Fetching bills from congress.gov (limit=%d)...", args.limit)
    bills = ingestor.fetch_recent_bills(congress=119, since_date=since, limit=args.limit)
    logger.info("Fetched %d bills", len(bills))

    # Step 2: Fetch CBO estimates
    logger.info("Fetching recent CBO cost estimates...")
    cbo_estimates = cbo.fetch_recent_estimates(since_date=since, limit=200)
    logger.info("Fetched %d CBO estimates", len(cbo_estimates))

    # Index CBO estimates for quick lookup
    cbo_by_title = {e.title.lower(): e for e in cbo_estimates if e.title}

    # Process each bill
    updated = 0
    scored = 0
    skipped = 0

    for bill in bills:
        logger.debug("Processing %s: %s", bill.bill_id, bill.title[:60])

        # Fetch CRS summary if missing
        if not bill.summary:
            summary = ingestor.fetch_bill_summary(bill.bill_id)
            if summary:
                bill.summary = summary

        if not args.dry_run:
            db.upsert_bill(bill)

        # Match CBO estimate
        cbo_estimate = cbo.match_to_bill(bill.bill_id, bill_title=bill.title)
        if cbo_estimate:
            if not args.dry_run:
                db.upsert_cbo_score(cbo_estimate)
            bill.has_cbo_score = True
            logger.debug("  CBO match: %.1fB", cbo_estimate.ten_year_cost_billions)

        # Provision mapping + scoring
        if args.skip_scoring or mapper is None:
            skipped += 1
            updated += 1
            continue

        if db.has_manual_override(bill.bill_id):
            logger.debug("  Using manual override for %s", bill.bill_id)

        mapping = mapper.map_bill(bill.bill_id, bill.summary)
        logger.debug(
            "  Mapping: %d policies, confidence=%s, method=%s",
            len(mapping.policies),
            mapping.confidence,
            mapping.extraction_method,
        )

        if mapping.confidence == "low" and not mapping.policies:
            logger.debug("  Skipping auto-score (low confidence, no policies)")
            skipped += 1
            updated += 1
            continue

        if scorer:
            auto_score = scorer.score(mapping)
            if auto_score:
                if not args.dry_run:
                    db.upsert_auto_score(auto_score)
                scored += 1
                logger.debug(
                    "  Auto-score: %.1fB (confidence=%s)",
                    auto_score.ten_year_cost_billions,
                    auto_score.confidence,
                )

        updated += 1

    if not args.dry_run:
        db.set_last_update(datetime.utcnow())

    # Summary
    total_in_db = db.count_bills() if not args.dry_run else updated
    logger.info(
        "Done. Updated=%d, Scored=%d, Skipped=%d. DB total=%d bills.",
        updated,
        scored,
        skipped,
        total_in_db,
    )

    if args.verbose:
        _print_sample(db, n=5)

    return 0


def _print_sample(db: Any, n: int = 5) -> None:
    """Print a sample of recently updated bills."""
    bills = db.get_all_bills(limit=n)
    if not bills:
        return
    print(f"\nSample of {n} most recent bills:")
    for b in bills:
        cbo_score = db.get_cbo_score(b["bill_id"])
        auto_score = db.get_auto_score(b["bill_id"])
        cbo_str = f"CBO: ${cbo_score['ten_year_cost_billions']:.1f}B" if cbo_score else "CBO: n/a"
        calc_str = f"Calc: ${auto_score['ten_year_cost_billions']:.1f}B" if auto_score else "Calc: n/a"
        print(f"  {b['bill_id']:25s}  {b['status']:15s}  {cbo_str:18s}  {calc_str}")


if __name__ == "__main__":
    from typing import Any
    sys.exit(main())
