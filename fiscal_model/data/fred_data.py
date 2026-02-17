"""
FRED data helper with simple file cache.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd


class FREDData:
    """Fetch selected macro series from FRED when API credentials are available."""

    SERIES = {
        "nominal_gdp": "GDP",   # billions SAAR
        "real_gdp": "GDPC1",    # billions chained 2017$
        "unemployment": "UNRATE",
        "interest_rate": "DGS10",
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        default_cache_dir = Path(__file__).resolve().parent.parent / "data_files" / "cache"
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._api_key = os.getenv("FRED_API_KEY", "").strip()
        self._fred = None

        if self._api_key:
            try:
                from fredapi import Fred

                self._fred = Fred(api_key=self._api_key)
            except Exception:
                self._fred = None

    def is_available(self) -> bool:
        return self._fred is not None

    def get_gdp(self, nominal: bool = True) -> pd.Series:
        series_id = self.SERIES["nominal_gdp"] if nominal else self.SERIES["real_gdp"]
        return self._get_series(series_id)

    def get_unemployment(self) -> pd.Series:
        return self._get_series(self.SERIES["unemployment"])

    def get_interest_rate(self) -> pd.Series:
        return self._get_series(self.SERIES["interest_rate"])

    def _get_series(self, series_id: str) -> pd.Series:
        live = self._fetch_live_series(series_id)
        if live is not None and not live.empty:
            self._write_cache(series_id, live)
            return live

        cached = self._read_cache(series_id)
        if cached is not None and not cached.empty:
            return cached

        # Last-resort fallback for offline environments.
        return pd.Series([28_500.0], index=[pd.Timestamp("2024-01-01")], name=series_id)

    def _fetch_live_series(self, series_id: str) -> Optional[pd.Series]:
        if self._fred is None:
            return None
        try:
            series = self._fred.get_series(series_id)
            if isinstance(series, pd.Series):
                series = series.dropna()
                series.name = series_id
                return series
            return None
        except Exception:
            return None

    def _cache_path(self, series_id: str) -> Path:
        return self.cache_dir / f"fred_{series_id}.json"

    def _write_cache(self, series_id: str, series: pd.Series) -> None:
        path = self._cache_path(series_id)
        payload = {
            "series_id": series_id,
            "updated_at": datetime.utcnow().isoformat(),
            "values": {str(idx): float(val) for idx, val in series.items()},
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _read_cache(self, series_id: str) -> Optional[pd.Series]:
        path = self._cache_path(series_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            values = payload.get("values", {})
            if not values:
                return None
            index = pd.to_datetime(list(values.keys()))
            data = [float(v) for v in values.values()]
            return pd.Series(data, index=index, name=series_id).sort_index()
        except Exception:
            return None
