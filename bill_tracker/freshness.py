"""
Freshness and staleness logic for tracked bills.

Thresholds:
  fresh    — updated today (< 1 day)
  stale    — updated within a week (1–7 days)
  outdated — updated within a month (8–30 days)
  expired  — not updated in > 30 days (flag prominently)
  enacted  — bill became law (stable, no auto-update needed)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class FreshnessStatus:
    """Freshness status for a single bill."""

    bill_id: str
    status: str               # "fresh" | "stale" | "outdated" | "expired" | "enacted"
    last_updated: datetime
    days_since_update: int
    warning: str | None       # Human-readable warning for stale/outdated bills
    badge_color: str          # "green" | "yellow" | "red" | "blue"
    badge_label: str          # Short label for UI display


FRESHNESS_THRESHOLDS = {
    "fresh": 1,       # < 1 day old
    "stale": 7,       # 1–7 days old
    "outdated": 30,   # 8–30 days old
    # > 30 days → "expired"
}


def check_freshness(
    bill_id: str,
    last_fetched: datetime,
    status: str = "introduced",
    now: datetime | None = None,
) -> FreshnessStatus:
    """
    Compute freshness status for a bill.

    Args:
        bill_id: Bill identifier.
        last_fetched: UTC datetime of last successful data fetch.
        status: Bill legislative status (e.g. "enacted").
        now: Override current time (useful for testing). Defaults to UTC now.
    """
    if now is None:
        now = datetime.utcnow()

    # Normalise timezone (strip tz info for comparison)
    if last_fetched.tzinfo is not None:
        last_fetched = last_fetched.replace(tzinfo=None)

    delta = now - last_fetched
    days = max(0, delta.days)

    if status == "enacted":
        return FreshnessStatus(
            bill_id=bill_id,
            status="enacted",
            last_updated=last_fetched,
            days_since_update=days,
            warning=None,
            badge_color="blue",
            badge_label="Enacted",
        )

    if days < FRESHNESS_THRESHOLDS["fresh"]:
        return FreshnessStatus(
            bill_id=bill_id,
            status="fresh",
            last_updated=last_fetched,
            days_since_update=days,
            warning=None,
            badge_color="green",
            badge_label="Fresh",
        )

    if days <= FRESHNESS_THRESHOLDS["stale"]:
        return FreshnessStatus(
            bill_id=bill_id,
            status="stale",
            last_updated=last_fetched,
            days_since_update=days,
            warning=(
                f"Last updated {days} day{'s' if days != 1 else ''} ago. "
                "Check congress.gov for status changes."
            ),
            badge_color="yellow",
            badge_label=f"Stale ({days}d)",
        )

    if days <= FRESHNESS_THRESHOLDS["outdated"]:
        return FreshnessStatus(
            bill_id=bill_id,
            status="outdated",
            last_updated=last_fetched,
            days_since_update=days,
            warning=(
                f"Data is {days} days old. "
                "This bill's status or CBO score may have changed significantly."
            ),
            badge_color="red",
            badge_label=f"Outdated ({days}d)",
        )

    # > 30 days
    return FreshnessStatus(
        bill_id=bill_id,
        status="expired",
        last_updated=last_fetched,
        days_since_update=days,
        warning=(
            f"⚠ Data is {days} days old. "
            "Scores may be unreliable. Run update pipeline to refresh."
        ),
        badge_color="red",
        badge_label=f"Expired ({days}d)",
    )


def freshness_from_db_row(row: dict) -> FreshnessStatus:
    """
    Construct FreshnessStatus from a database row dict (bills table).
    """
    from .database import _parse_dt

    last_fetched_str = row.get("last_fetched", "")
    last_fetched = _parse_dt(last_fetched_str) or datetime(1970, 1, 1)
    status = row.get("status", "introduced")
    bill_id = row.get("bill_id", "")

    return check_freshness(
        bill_id=bill_id,
        last_fetched=last_fetched,
        status=status,
    )
