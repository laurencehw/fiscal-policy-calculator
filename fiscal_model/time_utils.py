"""
UTC-aware time helpers used across the fiscal policy calculator.
"""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
ISO_8601_UTC = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalize naive or aware datetimes to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_utc_timestamp(value: datetime | None) -> str:
    """Format a datetime as an ISO 8601 UTC string ending in ``Z``."""
    if value is None:
        return ""
    return ensure_utc(value).strftime(ISO_8601_UTC)


def parse_utc_timestamp(value: str | None) -> datetime | None:
    """Parse common stored timestamp shapes into a timezone-aware UTC datetime."""
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return ensure_utc(datetime.fromisoformat(normalized))
    except ValueError:
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return ensure_utc(datetime.strptime(text[:19], fmt))
        except ValueError:
            continue

    return None


def utc_isoformat(value: datetime | None = None) -> str:
    """Return an ISO 8601 UTC string for the provided or current time."""
    current = ensure_utc(value) if value is not None else utc_now()
    return current.isoformat().replace("+00:00", "Z")
