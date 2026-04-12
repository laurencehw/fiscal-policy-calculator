"""
FRED data helper with simple file cache, expiry, timeout, and error tracking.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from fiscal_model.time_utils import ensure_utc, utc_now

logger = logging.getLogger(__name__)


class FREDData:
    """Fetch selected macro series from FRED when API credentials are available.

    Features:
    - File-based cache with configurable expiry
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
        cache_dir: Optional[Path] = None,
        cache_max_age_days: int = 30,
        timeout_seconds: int = 10,
    ):
        default_cache_dir = Path(__file__).resolve().parent.parent / "data_files" / "cache"
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._api_key = os.getenv("FRED_API_KEY", "").strip()
        self._fred = None
        self.cache_max_age_days = cache_max_age_days
        self.timeout_seconds = timeout_seconds

        # Error tracking
        self._last_error: Optional[str] = None
        self._data_source: Optional[str] = None  # "live", "cache", or "fallback"
        self._last_updated: Optional[datetime] = None
        self._cache_age_days: Optional[int] = None

        if self._api_key:
            try:
                from fredapi import Fred

                self._fred = Fred(api_key=self._api_key)
            except Exception as e:
                self._fred = None
                self._last_error = f"Failed to initialize FRED API: {str(e)}"
                logger.warning(self._last_error)

    def is_available(self) -> bool:
        """Check if FRED API is available and initialized."""
        return self._fred is not None

    @property
    def data_status(self) -> dict:
        """Return status information about data sources and last updates.

        Returns:
            dict with keys:
            - source: "live", "cache", or "fallback"
            - last_updated: datetime object or None
            - cache_age_days: int or None
            - api_available: bool
            - error: str or None (last error message)
        """
        return {
            "source": self._data_source,
            "last_updated": self._last_updated,
            "cache_age_days": self._cache_age_days,
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
        """Fetch series, trying live API -> valid cache -> expired cache -> fallback."""
        # Try fresh data from live API
        live = self._fetch_live_series(series_id)
        if live is not None and not live.empty:
            self._write_cache(series_id, live)
            self._data_source = "live"
            self._last_error = None
            self._last_updated = utc_now()
            self._cache_age_days = 0
            return live

        # Try cache (valid or expired)
        cached, is_expired, cache_age = self._read_cache(series_id)
        if cached is not None and not cached.empty:
            if is_expired:
                logger.warning(
                    f"Cache for {series_id} is {cache_age} days old (max: {self.cache_max_age_days}). "
                    "Using stale cache."
                )
                self._data_source = "cache (expired)"
                self._cache_age_days = cache_age
            else:
                self._data_source = "cache"
                self._cache_age_days = cache_age
            self._last_updated = utc_now()
            return cached

        # Last-resort fallback for offline environments (2026 nominal GDP estimate).
        logger.error(
            f"No live data or cache available for {series_id}. Using fallback value."
        )
        self._data_source = "fallback"
        self._last_error = f"No data available for {series_id}"
        self._last_updated = None
        self._cache_age_days = None
        return pd.Series([30_300.0], index=[pd.Timestamp("2024-01-01")], name=series_id)

    def _fetch_live_series(self, series_id: str) -> Optional[pd.Series]:
        """Fetch a series from FRED API with timeout."""
        if self._fred is None:
            return None
        try:
            series = self._fred.get_series(series_id, observation_start=None, timeout=self.timeout_seconds)
            if isinstance(series, pd.Series):
                series = series.dropna()
                series.name = series_id
                return series
            return None
        except Exception as e:
            error_msg = f"Failed to fetch {series_id} from FRED: {str(e)}"
            logger.debug(error_msg)
            self._last_error = error_msg
            return None

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

    def _read_cache(self, series_id: str) -> tuple[Optional[pd.Series], bool, Optional[int]]:
        """Read cache, returning (series, is_expired, cache_age_days).

        Returns:
            Tuple of (series or None, is_expired bool, cache_age_days or None)
        """
        path = self._cache_path(series_id)
        if not path.exists():
            return None, False, None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            values = payload.get("values", {})
            if not values:
                return None, False, None

            # Check cache age
            updated_at_str = payload.get("updated_at")
            is_expired = False
            cache_age_days = None

            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    cache_age = utc_now() - ensure_utc(updated_at)
                    cache_age_days = int(cache_age.total_seconds() / 86400)
                    is_expired = cache_age > timedelta(days=self.cache_max_age_days)
                except Exception as e:
                    logger.debug(f"Error parsing cache timestamp for {series_id}: {e}")

            index = pd.to_datetime(list(values.keys()))
            data = [float(v) for v in values.values()]
            series = pd.Series(data, index=index, name=series_id).sort_index()
            return series, is_expired, cache_age_days
        except Exception as e:
            logger.debug(f"Error reading cache for {series_id}: {e}")
            return None, False, None
