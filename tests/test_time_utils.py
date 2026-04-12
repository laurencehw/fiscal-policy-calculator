"""
Tests for fiscal_model.time_utils.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fiscal_model.time_utils import (
    UTC,
    ensure_utc,
    format_utc_timestamp,
    parse_utc_timestamp,
    utc_isoformat,
    utc_now,
)


def test_utc_now_returns_timezone_aware_value():
    current = utc_now()
    assert current.tzinfo == UTC


def test_ensure_utc_normalizes_naive_and_aware_datetimes():
    naive = datetime(2026, 4, 11, 12, 0, 0)
    aware = datetime(2026, 4, 11, 8, 0, 0, tzinfo=timezone(timedelta(hours=-4)))

    assert ensure_utc(naive).tzinfo == UTC
    assert ensure_utc(aware) == datetime(2026, 4, 11, 12, 0, 0, tzinfo=UTC)


def test_format_utc_timestamp_handles_none_and_datetime_values():
    assert format_utc_timestamp(None) == ""
    assert format_utc_timestamp(datetime(2026, 4, 11, 12, 0, 0)) == "2026-04-11T12:00:00Z"


def test_parse_utc_timestamp_supports_common_formats_and_invalid_values():
    assert parse_utc_timestamp(None) is None
    assert parse_utc_timestamp("   ") is None
    assert parse_utc_timestamp("2026-04-11T12:00:00Z") == datetime(2026, 4, 11, 12, 0, 0, tzinfo=UTC)
    assert parse_utc_timestamp("2026-04-11T12:00:00") == datetime(2026, 4, 11, 12, 0, 0, tzinfo=UTC)
    assert parse_utc_timestamp("2026-04-11T12:00:00 junk") == datetime(2026, 4, 11, 12, 0, 0, tzinfo=UTC)
    assert parse_utc_timestamp("2026-04-11") == datetime(2026, 4, 11, 0, 0, 0, tzinfo=UTC)
    assert parse_utc_timestamp("not-a-date") is None


def test_utc_isoformat_uses_provided_value_and_current_time():
    value = datetime(2026, 4, 11, 12, 0, 0, tzinfo=UTC)
    assert utc_isoformat(value) == "2026-04-11T12:00:00Z"
    assert utc_isoformat().endswith("Z")
