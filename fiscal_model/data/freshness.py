"""
Data freshness evaluation.

Centralizes the logic for deciding whether the CBO baseline and IRS SOI
tables are "fresh enough" for production use. Used by the Streamlit app's
sidebar status panel and by CI to fail loudly when data lags the policy
year.

Kept in ``fiscal_model.data`` (not ``ui``) so non-UI callers — CLI scripts,
tests, the API — can consult the same rules without importing Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from fiscal_model.time_utils import ensure_utc, utc_now


class FreshnessLevel(str, Enum):
    """Ordered freshness tiers used for sidebar colouring and alerts."""

    FRESH = "fresh"          # within expected cadence
    AGING = "aging"          # approaching next expected update
    STALE = "stale"          # past the next update — warn loudly
    UNKNOWN = "unknown"      # can't determine — treat as aging


@dataclass(frozen=True)
class FreshnessReport:
    """Result of a freshness check for a single data source."""

    source: str
    level: FreshnessLevel
    age_days: int | None
    message: str

    @property
    def is_stale(self) -> bool:
        return self.level is FreshnessLevel.STALE

    @property
    def emoji(self) -> str:
        return {
            FreshnessLevel.FRESH: "🟢",
            FreshnessLevel.AGING: "🟡",
            FreshnessLevel.STALE: "🟠",
            FreshnessLevel.UNKNOWN: "⚪",
        }[self.level]


# Expected update cadence in days. Sources:
# - IRS SOI: ~2-year publication lag, annual update; warn at > 2.25y.
_IRS_FRESH_YEARS = 2
_IRS_STALE_YEARS = 3


# ---------------------------------------------------------------------------
# CBO baseline release calendar
# ---------------------------------------------------------------------------
#
# CBO publishes its *Budget and Economic Outlook* baseline roughly once a year
# (January/February), so elapsed age is a bad alarm on its own: the February
# 2026 baseline read at the end of August 2026 is ~209 days old and completely
# current. The previous 120d/180d thresholds turned CBO's ordinary annual
# cycle into an amber "past its expected refresh window" warning every summer.
#
# The rule is now driven by a release calendar rather than a stopwatch:
#
#   **stale iff a known CBO baseline release is dated later than the bundled
#   vintage** (and has actually happened as of ``now``).
#
# Offline fallback: the app cannot learn about a release nobody has registered
# here, so a vintage older than a full annual cycle is flagged anyway — that is
# the only case where raw age still drives the alarm.
_CBO_CYCLE_DAYS = 395     # ~13 months: one annual cycle plus a month of slack
_CBO_OVERDUE_DAYS = 425   # ~14 months: past any plausible CBO cycle

# Known CBO baseline publication dates, keyed by the vintage enum value
# (see :mod:`fiscal_model.baseline`). These are the vintages this app bundles.
CBO_VINTAGE_PUBLICATION_DATES: dict[str, datetime] = {
    "cbo_feb_2024": ensure_utc(datetime(2024, 2, 7)),
    "cbo_jan_2025": ensure_utc(datetime(2025, 1, 17)),
    "cbo_feb_2026": ensure_utc(datetime(2026, 2, 4)),
}

# CBO baselines that have been *published* but are not bundled here yet.
# Add a date the day CBO publishes, before the data is wired in: the gap
# between "CBO released it" and "we ingested it" is precisely the window the
# amber alarm exists to flag. Empty means every known release is bundled.
_UNBUNDLED_CBO_RELEASES: tuple[datetime, ...] = ()


def known_cbo_releases() -> tuple[datetime, ...]:
    """Return every known CBO baseline publication date, oldest first.

    The union of the bundled vintages and any published-but-not-yet-ingested
    releases. This is the calendar :func:`evaluate_cbo_baseline` compares the
    bundled vintage against.
    """
    return tuple(
        sorted({*CBO_VINTAGE_PUBLICATION_DATES.values(), *_UNBUNDLED_CBO_RELEASES})
    )


def _newest_release_after(
    vintage_date: datetime,
    now: datetime,
    releases: tuple[datetime, ...],
) -> datetime | None:
    """Latest calendar entry newer than ``vintage_date`` and already published."""
    candidates = [
        ensure_utc(release)
        for release in releases
        if ensure_utc(release) > vintage_date and ensure_utc(release) <= now
    ]
    return max(candidates) if candidates else None


def _format_release(moment: datetime) -> str:
    """``2027-02-03`` -> ``Feb 3, 2027`` (no platform-specific strftime flags)."""
    return f"{moment:%b} {moment.day}, {moment.year}"


def evaluate_cbo_baseline(
    vintage_date: datetime | None,
    *,
    now: datetime | None = None,
    known_releases: tuple[datetime, ...] | None = None,
) -> FreshnessReport:
    """Evaluate the CBO baseline vintage against the known release calendar.

    A baseline inside CBO's normal annual cycle reads FRESH regardless of how
    many days old it is. It only goes STALE when a newer release is known to
    exist, or — as an offline fallback — when it is older than one full cycle.

    Args:
        vintage_date: Datetime the bundled baseline was published. ``None``
            means unknown.
        now: Injection point for tests.
        known_releases: Override the release calendar (tests; also lets a
            caller supply a live-fetched list).
    """
    current = now or utc_now()
    if vintage_date is None:
        return FreshnessReport(
            source="CBO baseline",
            level=FreshnessLevel.UNKNOWN,
            age_days=None,
            message="Unknown baseline vintage",
        )

    # Normalize both sides to tz-aware UTC so subtraction always works.
    vintage_date = ensure_utc(vintage_date)
    current = ensure_utc(current)

    age_days = int((current - vintage_date).total_seconds() // 86400)
    if age_days < 0:
        age_days = 0

    releases = known_cbo_releases() if known_releases is None else tuple(known_releases)
    superseded_by = _newest_release_after(vintage_date, current, releases)

    if superseded_by is not None:
        level = FreshnessLevel.STALE
        message = (
            f"Superseded — CBO published a newer baseline on "
            f"{_format_release(superseded_by)}. "
            "Refresh from latest CBO Budget & Economic Outlook."
        )
    elif age_days > _CBO_OVERDUE_DAYS:
        level = FreshnessLevel.STALE
        message = (
            f"Stale ({age_days}d since publication — more than one CBO annual "
            "cycle with no newer release on record). "
            "Refresh from latest CBO Budget & Economic Outlook."
        )
    elif age_days > _CBO_CYCLE_DAYS:
        level = FreshnessLevel.AGING
        message = (
            f"Aging ({age_days}d since publication — next CBO baseline is due)"
        )
    else:
        level = FreshnessLevel.FRESH
        message = (
            f"Current CBO baseline ({age_days}d since publication; "
            "no newer release)"
        )

    return FreshnessReport(
        source="CBO baseline",
        level=level,
        age_days=age_days,
        message=message,
    )


def evaluate_irs_soi(
    data_year: int | None,
    *,
    now: datetime | None = None,
) -> FreshnessReport:
    """Evaluate IRS Statistics of Income freshness.

    Args:
        data_year: Tax year represented by the SOI tables the app is using.
        now: Injection point for tests.
    """
    current = now or utc_now()
    if data_year is None:
        return FreshnessReport(
            source="IRS SOI",
            level=FreshnessLevel.UNKNOWN,
            age_days=None,
            message="Unknown IRS SOI year",
        )

    lag_years = current.year - data_year
    age_days = int(lag_years * 365.25)

    if lag_years <= _IRS_FRESH_YEARS:
        level = FreshnessLevel.FRESH
        message = f"IRS SOI {data_year} (lag {lag_years}y — within expected window)"
    elif lag_years <= _IRS_STALE_YEARS:
        level = FreshnessLevel.AGING
        message = (
            f"IRS SOI {data_year} (lag {lag_years}y — new release likely available)"
        )
    else:
        level = FreshnessLevel.STALE
        message = (
            f"IRS SOI {data_year} (lag {lag_years}y — refresh data_files/irs_soi/)"
        )

    return FreshnessReport(
        source="IRS SOI",
        level=level,
        age_days=age_days,
        message=message,
    )


__all__ = [
    "CBO_VINTAGE_PUBLICATION_DATES",
    "FreshnessLevel",
    "FreshnessReport",
    "evaluate_cbo_baseline",
    "evaluate_irs_soi",
    "known_cbo_releases",
]
