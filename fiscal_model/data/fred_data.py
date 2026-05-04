"""
FRED data helper with simple file cache, expiry, timeout, and error tracking.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from fiscal_model.exceptions import FREDUnavailableError
from fiscal_model.time_utils import parse_utc_timestamp, utc_now

logger = logging.getLogger(__name__)

# Retry schedule (seconds) for transient FRED failures. Short by design so
# we fall back to cache quickly rather than blocking UI renders.
_FRED_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (0.5, 1.0)


class FREDData:
    """Fetch selected macro series from FRED when API credentials are available.

    Features:
    - File-based cache with configurable expiry
    - Bundled seed data for deterministic offline smoke/readiness checks
    - Timeout configuration for API calls
    - Error tracking and reporting
    - Fallback to expired cache on network failure
    """

    SERIES = {
        "nominal_gdp": "GDP",   # billions SAAR
        "real_gdp": "GDPC1",    # billions chained 2017$
        "unemployment": "UNRATE",
        "interest_rate": "DGS10",
    }

    def __init__(
        self,
        cache_dir: Path | None = None,
        bundled_seed_path: Path | str | None = None,
        cache_max_age_days: int = 30,
        timeout_seconds: int = 10,
    ):
        default_cache_dir = Path(__file__).resolve().parent.parent / "data_files" / "cache"
        default_seed_path = Path(__file__).resolve().parent.parent / "data_files" / "fred_seed.json"
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if bundled_seed_path is not None:
            self.bundled_seed_path: Path | None = Path(bundled_seed_path)
        elif cache_dir is None:
            self.bundled_seed_path = default_seed_path
        else:
            self.bundled_seed_path = None
        self._api_key = os.getenv("FRED_API_KEY", "").strip()
        self._fred = None
        self.cache_max_age_days = cache_max_age_days
        self.timeout_seconds = timeout_seconds

        # Error tracking
        self._last_error: str | None = None
        self._data_source: str | None = None  # "live", "cache", "bundled", or "fallback"
        self._last_updated: datetime | None = None
        self._cache_age_days: int | None = None
        self._cache_is_expired: bool = False

        if self._api_key:
            try:
                from fredapi import Fred

                self._fred = Fred(api_key=self._api_key)
            except Exception as e:
                self._fred = None
                self._last_error = f"Failed to initialize FRED API: {e!s}"
                logger.warning(self._last_error)

    def is_available(self) -> bool:
        """Check if FRED API is available and initialized."""
        return self._fred is not None

    @property
    def data_status(self) -> dict:
        """Return status information about data sources and last updates.

        Returns:
            dict with keys:
            - source: "live", "cache", "bundled", or "fallback"
            - last_updated: datetime object or None
            - cache_age_days: int or None
            - api_available: bool
            - error: str or None (last error message)
        """
        source = self._data_source
        last_updated = self._last_updated
        cache_age_days = self._cache_age_days
        cache_is_expired = self._cache_is_expired

        if source is None:
            has_cache, cached_updated_at, inferred_expired, inferred_age_days = (
                self._peek_cache_metadata(self.SERIES["nominal_gdp"])
            )
            if has_cache and not inferred_expired:
                source = "cache"
                last_updated = cached_updated_at
                cache_age_days = inferred_age_days
                cache_is_expired = inferred_expired
            else:
                has_seed, seed_updated_at, seed_age_days = (
                    self._peek_bundled_seed_metadata(self.SERIES["nominal_gdp"])
                )
                if has_seed:
                    source = "bundled"
                    last_updated = seed_updated_at
                    cache_age_days = seed_age_days
                    cache_is_expired = False
                elif has_cache:
                    source = "cache"
                    last_updated = cached_updated_at
                    cache_age_days = inferred_age_days
                    cache_is_expired = inferred_expired

        return {
            "source": source,
            "last_updated": last_updated,
            "cache_age_days": cache_age_days,
            "cache_is_expired": cache_is_expired,
            "api_available": self.is_available(),
            "error": self._last_error,
        }

    def get_gdp(self, nominal: bool = True) -> pd.Series:
        series_id = self.SERIES["nominal_gdp"] if nominal else self.SERIES["real_gdp"]
        return self._get_series(series_id)

    def get_unemployment(self) -> pd.Series:
        return self._get_series(self.SERIES["unemployment"])

    def get_interest_rate(self) -> pd.Series:
        return self._get_series(self.SERIES["interest_rate"])

    def _get_series(self, series_id: str) -> pd.Series:
        """Fetch series, trying live API -> fresh cache -> seed -> stale cache."""
        # Try fresh data from live API
        live = self._fetch_live_series(series_id)
        if live is not None and not live.empty:
            self._write_cache(series_id, live)
            self._data_source = "live"
            self._last_error = None
            self._last_updated = utc_now()
            self._cache_age_days = 0
            self._cache_is_expired = False
            return live

        # Try fresh cache first. Stale cache remains useful, but a tracked seed
        # should beat it for deterministic CI/readiness checks.
        cached, is_expired, cache_age, cache_updated_at = self._read_cache(series_id)
        if cached is not None and not cached.empty and not is_expired:
            self._data_source = "cache"
            self._cache_age_days = cache_age
            self._cache_is_expired = is_expired
            self._last_updated = cache_updated_at
            return cached

        # Try a tracked seed snapshot. This keeps CI and offline deployments
        # deterministic without pretending that live FRED is configured.
        bundled, seed_age, seed_updated_at = self._read_bundled_seed(series_id)
        if bundled is not None and not bundled.empty:
            logger.info("Using bundled FRED seed for %s.", series_id)
            self._data_source = "bundled"
            self._last_error = None
            self._cache_age_days = seed_age
            self._cache_is_expired = False
            self._last_updated = seed_updated_at
            return bundled

        if cached is not None and not cached.empty:
            logger.warning(
                f"Cache for {series_id} is {cache_age} days old (max: {self.cache_max_age_days}). "
                "Using stale cache."
            )
            self._data_source = "cache"
            self._cache_age_days = cache_age
            self._cache_is_expired = is_expired
            self._last_updated = cache_updated_at
            return cached

        # Last-resort fallback for offline environments (2026 nominal GDP estimate).
        logger.error(
            f"No live data, cache, or bundled seed available for {series_id}. "
            "Using fallback value."
        )
        self._data_source = "fallback"
        self._last_error = f"No data available for {series_id}"
        self._last_updated = None
        self._cache_age_days = None
        self._cache_is_expired = False
        return pd.Series([30_300.0], index=[pd.Timestamp("2024-01-01")], name=series_id)

    def _fetch_live_series(self, series_id: str) -> pd.Series | None:
        """Fetch a series from FRED API with timeout and short retry/backoff.

        Returns ``None`` on failure so the caller can fall back to cache.
        Transient errors are retried with an exponential-ish backoff before
        giving up; the final error is stored on ``self._last_error``.
        """
        if self._fred is None:
            return None

        attempts = 1 + len(_FRED_RETRY_BACKOFF_SECONDS)
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                series = self._fred.get_series(
                    series_id,
                    observation_start=None,
                    timeout=self.timeout_seconds,
                )
                if isinstance(series, pd.Series):
                    series = series.dropna()
                    series.name = series_id
                    return series
                return None
            except Exception as e:
                # fredapi can raise many underlying types; treat all as transient.
                last_exc = e
                logger.debug(
                    "FRED fetch attempt %d/%d for %s failed: %s",
                    attempt + 1,
                    attempts,
                    series_id,
                    e,
                )
                if attempt < len(_FRED_RETRY_BACKOFF_SECONDS):
                    time.sleep(_FRED_RETRY_BACKOFF_SECONDS[attempt])

        error_msg = f"Failed to fetch {series_id} from FRED: {last_exc!s}"
        logger.info(error_msg)
        self._last_error = error_msg
        return None

    def require_live(self, series_id: str) -> pd.Series:
        """Fetch a series from the live FRED API, raising on failure.

        Useful for callers that must have fresh data (e.g. CLI refresh jobs).
        Raises :class:`FREDUnavailableError` if the API is unreachable or
        returns no usable data.
        """
        if self._fred is None:
            raise FREDUnavailableError(
                "FRED API not configured (set FRED_API_KEY) or fredapi "
                "unavailable"
            )
        series = self._fetch_live_series(series_id)
        if series is None or series.empty:
            raise FREDUnavailableError(
                self._last_error
                or f"No live FRED data available for {series_id}"
            )
        return series

    def refresh(self) -> bool:
        """Force re-fetch all series from FRED API and update cache.

        Returns:
            True if at least one series was successfully fetched, False if all failed.
        """
        if self._fred is None:
            logger.warning("Cannot refresh: FRED API not available")
            self._last_error = "FRED API not available"
            return False

        success_count = 0
        for series_name, series_id in self.SERIES.items():
            try:
                series = self._fetch_live_series(series_id)
                if series is not None and not series.empty:
                    self._write_cache(series_id, series)
                    success_count += 1
                    logger.info(f"Refreshed {series_id} ({series_name})")
                else:
                    logger.warning(f"Failed to refresh {series_id} ({series_name})")
            except Exception as e:
                logger.error(f"Error refreshing {series_id} ({series_name}): {e}")

        if success_count > 0:
            self._data_source = "live"
            self._last_updated = utc_now()
            self._cache_age_days = 0
            self._cache_is_expired = False
            self._last_error = None
            logger.info(f"Successfully refreshed {success_count}/{len(self.SERIES)} series")
            return True
        else:
            self._last_error = "Failed to refresh any series from FRED API"
            logger.error(self._last_error)
            return False

    def _cache_path(self, series_id: str) -> Path:
        return self.cache_dir / f"fred_{series_id}.json"

    def _write_cache(self, series_id: str, series: pd.Series) -> None:
        path = self._cache_path(series_id)
        payload = {
            "series_id": series_id,
            "updated_at": utc_now().isoformat(),
            "values": {str(idx): float(val) for idx, val in series.items()},
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def _series_from_values(series_id: str, values: dict) -> pd.Series | None:
        if not values:
            return None
        index = pd.to_datetime(list(values.keys()))
        data = [float(v) for v in values.values()]
        return pd.Series(data, index=index, name=series_id).sort_index()

    @staticmethod
    def _age_days(updated_at: datetime | None) -> int | None:
        if updated_at is None:
            return None
        age = utc_now() - updated_at
        return int(age.total_seconds() / 86400)

    def _read_bundled_seed_payload(self, series_id: str) -> dict | None:
        path = self.bundled_seed_path
        if path is None or not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug("Error reading bundled FRED seed for %s: %s", series_id, e)
            return None

        series_payload = payload.get("series", {}).get(series_id)
        if not isinstance(series_payload, dict):
            return None
        return {
            **series_payload,
            "_root_updated_at": payload.get("updated_at"),
        }

    def _peek_bundled_seed_metadata(
        self,
        series_id: str,
    ) -> tuple[bool, datetime | None, int | None]:
        """Inspect bundled seed metadata without mutating object state."""
        payload = self._read_bundled_seed_payload(series_id)
        if payload is None or not payload.get("values"):
            return False, None, None

        updated_at = parse_utc_timestamp(
            payload.get("updated_at") or payload.get("_root_updated_at")
        )
        return True, updated_at, self._age_days(updated_at)

    def _read_bundled_seed(
        self,
        series_id: str,
    ) -> tuple[pd.Series | None, int | None, datetime | None]:
        """Read bundled seed data for a series, if the tracked seed provides it."""
        payload = self._read_bundled_seed_payload(series_id)
        if payload is None:
            return None, None, None

        series = self._series_from_values(series_id, payload.get("values", {}))
        if series is None:
            return None, None, None

        updated_at = parse_utc_timestamp(
            payload.get("updated_at") or payload.get("_root_updated_at")
        )
        return series, self._age_days(updated_at), updated_at

    def _peek_cache_metadata(
        self,
        series_id: str,
    ) -> tuple[bool, datetime | None, bool, int | None]:
        """Inspect cache metadata without mutating object state."""
        path = self._cache_path(series_id)
        if not path.exists():
            return False, None, False, None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug(f"Error reading cache metadata for {series_id}: {e}")
            return False, None, False, None

        values = payload.get("values", {})
        if not values:
            return False, None, False, None

        updated_at = parse_utc_timestamp(payload.get("updated_at"))
        if updated_at is None:
            return True, None, False, None

        cache_age = utc_now() - updated_at
        cache_age_days = self._age_days(updated_at)
        is_expired = cache_age > timedelta(days=self.cache_max_age_days)
        return True, updated_at, is_expired, cache_age_days

    def _read_cache(
        self,
        series_id: str,
    ) -> tuple[pd.Series | None, bool, int | None, datetime | None]:
        """Read cache, returning (series, is_expired, cache_age_days).

        Returns:
            Tuple of (series or None, is_expired bool, cache_age_days or None, cache timestamp)
        """
        path = self._cache_path(series_id)
        if not path.exists():
            return None, False, None, None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            values = payload.get("values", {})
            if not values:
                return None, False, None, None

            _, updated_at, is_expired, cache_age_days = self._peek_cache_metadata(series_id)

            series = self._series_from_values(series_id, values)
            return series, is_expired, cache_age_days, updated_at
        except Exception as e:
            logger.debug(f"Error reading cache for {series_id}: {e}")
            return None, False, None, None
