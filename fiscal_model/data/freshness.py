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
# - CBO baseline: updated ~quarterly; warn if > 1.5 quarters (~135d).
# - IRS SOI: ~2-year publication lag, annual update; warn at > 2.25y.
_CBO_FRESH_DAYS = 120
_CBO_STALE_DAYS = 180
_IRS_FRESH_YEARS = 2
_IRS_STALE_YEARS = 3


def evaluate_cbo_baseline(
    vintage_date: datetime | None,
    *,
    now: datetime | None = None,
) -> FreshnessReport:
    """Evaluate the CBO baseline vintage.

    Args:
        vintage_date: Datetime the baseline was published. ``None`` means
            unknown.
        now: Injection point for tests.
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

    if age_days <= _CBO_FRESH_DAYS:
        level = FreshnessLevel.FRESH
        message = f"Fresh ({age_days}d since publication)"
    elif age_days <= _CBO_STALE_DAYS:
        level = FreshnessLevel.AGING
        message = f"Aging ({age_days}d since publication — next CBO update due)"
    else:
        level = FreshnessLevel.STALE
        message = (
            f"Stale ({age_days}d since publication). "
            "Refresh from latest CBO Budget & Economic Outlook."
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


# Known CBO baseline publication dates, keyed by the vintage enum value
# (see :mod:`fiscal_model.baseline`). Update as new baselines ship.
CBO_VINTAGE_PUBLICATION_DATES: dict[str, datetime] = {
    "cbo_feb_2024": ensure_utc(datetime(2024, 2, 7)),
    "cbo_jan_2025": ensure_utc(datetime(2025, 1, 17)),
    "cbo_feb_2026": ensure_utc(datetime(2026, 2, 4)),
}


__all__ = [
    "CBO_VINTAGE_PUBLICATION_DATES",
    "FreshnessLevel",
    "FreshnessReport",
    "evaluate_cbo_baseline",
    "evaluate_irs_soi",
]
