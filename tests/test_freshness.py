"""Tests for fiscal_model.data.freshness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fiscal_model.data.freshness import (
    CBO_VINTAGE_PUBLICATION_DATES,
    FreshnessLevel,
    evaluate_cbo_baseline,
    evaluate_irs_soi,
    known_cbo_releases,
)

UTC = timezone.utc


def _utc(year, month, day):
    return datetime(year, month, day, tzinfo=UTC)


# ---------------------------------------------------------------------------
# CBO baseline — release-calendar alarm
# ---------------------------------------------------------------------------
#
# The rule is "stale iff a known CBO release is newer than the bundled
# vintage", not "stale after N days". CBO publishes its Budget and Economic
# Outlook roughly once a year, so a February baseline read the following
# August is current, not aging. Raw age only drives the alarm as an offline
# fallback past one full annual cycle.

FEB_2026 = CBO_VINTAGE_PUBLICATION_DATES["cbo_feb_2026"]
JAN_2025 = CBO_VINTAGE_PUBLICATION_DATES["cbo_jan_2025"]


def test_cbo_fresh_same_day():
    report = evaluate_cbo_baseline(FEB_2026, now=FEB_2026)
    assert report.level is FreshnessLevel.FRESH
    assert report.age_days == 0


def test_cbo_feb_baseline_read_in_august_is_fresh():
    """The bug this rule replaces: 209 days into CBO's ordinary annual cycle
    the old 120d/180d thresholds flagged the current baseline STALE, which
    lit the amber pill and the degraded-data banner all summer."""
    report = evaluate_cbo_baseline(FEB_2026, now=_utc(2026, 8, 31))
    assert report.level is FreshnessLevel.FRESH
    assert not report.is_stale
    assert report.age_days > 200


def test_cbo_fresh_across_the_old_stale_thresholds():
    for days in (100, 150, 200, 300, 390):
        report = evaluate_cbo_baseline(FEB_2026, now=FEB_2026 + timedelta(days=days))
        assert report.level is FreshnessLevel.FRESH, days


def test_cbo_stale_when_a_newer_known_release_exists():
    report = evaluate_cbo_baseline(
        FEB_2026,
        now=_utc(2027, 3, 1),
        known_releases=(FEB_2026, _utc(2027, 2, 3)),
    )
    assert report.level is FreshnessLevel.STALE
    assert report.is_stale
    assert "Feb 3, 2027" in report.message
    assert "Refresh" in report.message


def test_cbo_stale_as_soon_as_a_newer_release_lands():
    """Age is irrelevant once CBO publishes: a two-week-old vintage that has
    already been superseded is stale."""
    report = evaluate_cbo_baseline(
        _utc(2027, 1, 20),
        now=_utc(2027, 2, 17),
        known_releases=(_utc(2027, 1, 20), _utc(2027, 2, 3)),
    )
    assert report.level is FreshnessLevel.STALE
    assert report.age_days < 30


def test_cbo_ignores_a_release_that_has_not_happened_yet():
    """A date registered ahead of publication must not backdate the alarm."""
    report = evaluate_cbo_baseline(
        FEB_2026,
        now=_utc(2026, 8, 31),
        known_releases=(FEB_2026, _utc(2027, 2, 3)),
    )
    assert report.level is FreshnessLevel.FRESH


def test_cbo_aging_past_one_annual_cycle_with_no_known_release():
    report = evaluate_cbo_baseline(
        FEB_2026,
        now=FEB_2026 + timedelta(days=400),
        known_releases=(FEB_2026,),
    )
    assert report.level is FreshnessLevel.AGING
    assert not report.is_stale


def test_cbo_stale_past_fourteen_months_with_no_known_release():
    """Offline fallback: we cannot see a release nobody registered, so a
    vintage older than any plausible cycle is flagged on age alone."""
    report = evaluate_cbo_baseline(
        FEB_2026,
        now=FEB_2026 + timedelta(days=430),
        known_releases=(FEB_2026,),
    )
    assert report.level is FreshnessLevel.STALE
    assert report.is_stale
    assert "Refresh" in report.message


def test_cbo_superseded_bundled_vintage_is_stale_against_the_shipped_calendar():
    """Jan 2025 is stale today without any override: Feb 2026 is in the
    shipped calendar."""
    report = evaluate_cbo_baseline(JAN_2025, now=_utc(2026, 8, 31))
    assert report.level is FreshnessLevel.STALE


def test_cbo_unknown_when_vintage_is_none():
    report = evaluate_cbo_baseline(None)
    assert report.level is FreshnessLevel.UNKNOWN
    assert report.age_days is None


def test_cbo_accepts_naive_datetime():
    """Known publication dates live in local tuples in docs; the helper
    should normalize naive datetimes to UTC rather than crashing."""
    naive = datetime(2026, 2, 4)
    report = evaluate_cbo_baseline(naive, now=_utc(2026, 3, 1))
    assert report.level is FreshnessLevel.FRESH


def test_shipped_calendar_marks_the_current_bundled_vintage_fresh_today():
    """Guards the whole point of the change: whatever vintage the app ships,
    it must read green until CBO publishes a successor."""
    newest = max(known_cbo_releases())
    report = evaluate_cbo_baseline(newest)
    assert report.level is FreshnessLevel.FRESH


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


def test_known_cbo_releases_is_sorted_tz_aware_and_covers_the_bundled_vintages():
    releases = known_cbo_releases()
    assert list(releases) == sorted(releases)
    assert all(dt.tzinfo is not None for dt in releases)
    for dt in CBO_VINTAGE_PUBLICATION_DATES.values():
        assert dt in releases
