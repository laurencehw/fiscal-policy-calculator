"""Tests for fiscal_model.data.freshness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fiscal_model.data.freshness import (
    CBO_VINTAGE_PUBLICATION_DATES,
    FreshnessLevel,
    evaluate_cbo_baseline,
    evaluate_irs_soi,
)

UTC = timezone.utc


def _utc(year, month, day):
    return datetime(year, month, day, tzinfo=UTC)


def test_cbo_fresh_same_day():
    pub = _utc(2026, 2, 4)
    report = evaluate_cbo_baseline(pub, now=pub)
    assert report.level is FreshnessLevel.FRESH
    assert report.age_days == 0


def test_cbo_fresh_within_120_days():
    pub = _utc(2026, 2, 4)
    report = evaluate_cbo_baseline(pub, now=pub + timedelta(days=100))
    assert report.level is FreshnessLevel.FRESH


def test_cbo_aging_past_120_days():
    pub = _utc(2026, 2, 4)
    report = evaluate_cbo_baseline(pub, now=pub + timedelta(days=150))
    assert report.level is FreshnessLevel.AGING
    assert not report.is_stale


def test_cbo_stale_past_180_days():
    pub = _utc(2026, 2, 4)
    report = evaluate_cbo_baseline(pub, now=pub + timedelta(days=200))
    assert report.level is FreshnessLevel.STALE
    assert report.is_stale
    assert "Refresh" in report.message


def test_cbo_unknown_when_vintage_is_none():
    report = evaluate_cbo_baseline(None)
    assert report.level is FreshnessLevel.UNKNOWN
    assert report.age_days is None


def test_cbo_accepts_naive_datetime():
    """Known publication dates live in local tuples in docs; the helper
    should normalize naive datetimes to UTC rather than crashing."""
    naive = datetime(2026, 2, 4)
    report = evaluate_cbo_baseline(naive, now=_utc(2026, 3, 1))
    assert report.level in {FreshnessLevel.FRESH, FreshnessLevel.AGING}


def test_irs_fresh_within_two_years():
    report = evaluate_irs_soi(2024, now=_utc(2026, 4, 13))
    assert report.level is FreshnessLevel.FRESH


def test_irs_aging_three_years():
    report = evaluate_irs_soi(2023, now=_utc(2026, 4, 13))
    assert report.level is FreshnessLevel.AGING


def test_irs_stale_over_three_years():
    report = evaluate_irs_soi(2020, now=_utc(2026, 4, 13))
    assert report.level is FreshnessLevel.STALE
    assert "refresh" in report.message.lower()


def test_irs_unknown_year():
    report = evaluate_irs_soi(None)
    assert report.level is FreshnessLevel.UNKNOWN


def test_cbo_vintage_publication_dates_are_utc():
    """Registered publication dates must be tz-aware to avoid subtraction
    errors against ``utc_now``."""
    for _, dt in CBO_VINTAGE_PUBLICATION_DATES.items():
        assert dt.tzinfo is not None
