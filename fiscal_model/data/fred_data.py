"""
FRED (Federal Reserve Economic Data) API integration.

This module provides access to economic indicators from the Federal Reserve
Bank of St. Louis's FRED database for use in fiscal policy baseline projections
and economic condition modeling.

API Documentation: https://fred.stlouisfed.org/docs/api/
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

# Try to import fredapi, but handle gracefully if not installed
try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    logger.warning(
        "fredapi library not installed. FRED data integration will not work. "
        "Install with: pip install fredapi"
    )


class FREDData:
    """
    Interface to FRED (Federal Reserve Economic Data) API.

    Provides access to key economic indicators with 24-hour caching to minimize
    API calls. Gracefully handles missing API keys and network issues.

    Common Series:
    - GDP: Nominal Gross Domestic Product
    - GDPC1: Real Gross Domestic Product
    - UNRATE: Unemployment Rate
    - DGS10: 10-Year Treasury Constant Maturity Rate
    - CIVPART: Labor Force Participation Rate
    - CPIAUCSL: Consumer Price Index for All Urban Consumers

    Example:
        >>> fred = FREDData(api_key="your_key_here")
        >>> gdp = fred.get_gdp(nominal=True)
        >>> unemployment = fred.get_latest_value('UNRATE')
    """

    # Default cache duration
    CACHE_HOURS = 24

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize FRED data interface.

        Args:
            api_key: FRED API key. If None, tries to load from environment
                    variable FRED_API_KEY
            cache_dir: Directory for caching data. If None, uses default
                      fiscal_model/data_files/cache/
        """
        if not FRED_AVAILABLE:
            logger.error("fredapi library not available. FRED integration disabled.")
            self.fred = None
            return

        # Get API key
        if api_key is None:
            api_key = os.environ.get('FRED_API_KEY')

        if api_key is None:
            logger.warning(
                "FRED API key not provided. Set FRED_API_KEY environment variable "
                "or pass api_key parameter. Get free key at: "
                "https://fred.stlouisfed.org/docs/api/api_key.html"
            )
            self.fred = None
        else:
            try:
                self.fred = Fred(api_key=api_key)
                logger.info("FRED API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize FRED API: {e}")
                self.fred = None

        # Setup cache directory
        if cache_dir is None:
            module_dir = Path(__file__).parent.parent
            cache_dir = module_dir / "data_files" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "fred_cache.json"

        # Load existing cache
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded FRED cache with {len(cache)} entries")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _is_cache_fresh(self, series_id: str, max_age_hours: int = CACHE_HOURS) -> bool:
        """Check if cached data is still fresh."""
        if series_id not in self._cache:
            return False

        cached_time = datetime.fromisoformat(self._cache[series_id]['timestamp'])
        age = datetime.now() - cached_time
        return age < timedelta(hours=max_age_hours)

    def get_series(self, series_id: str, start_date: Optional[str] = None,
                   use_cache: bool = True) -> pd.Series:
        """
        Get a FRED data series.

        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE')
            start_date: Start date in YYYY-MM-DD format. If None, gets all data.
            use_cache: If True, use cached data if fresh

        Returns:
            pandas Series with dates as index and values

        Raises:
            ValueError: If FRED API not available
            Exception: If API call fails and no cache available
        """
        if self.fred is None:
            if use_cache and series_id in self._cache:
                logger.warning(f"FRED API unavailable, using cached {series_id}")
                return self._series_from_cache(series_id)
            raise ValueError("FRED API not available and no cache found")

        # Check cache first
        if use_cache and self._is_cache_fresh(series_id):
            logger.info(f"Using cached FRED data for {series_id}")
            return self._series_from_cache(series_id)

        # Fetch from API
        try:
            logger.info(f"Fetching {series_id} from FRED API")
            series = self.fred.get_series(series_id, observation_start=start_date)

            # Cache the result
            self._cache[series_id] = {
                'timestamp': datetime.now().isoformat(),
                'data': series.to_json(),
                'start_date': start_date
            }
            self._save_cache()

            return series

        except Exception as e:
            logger.error(f"FRED API call failed for {series_id}: {e}")

            # Try to use stale cache
            if series_id in self._cache:
                logger.warning(f"Using stale cached data for {series_id}")
                return self._series_from_cache(series_id)

            raise

    def _series_from_cache(self, series_id: str) -> pd.Series:
        """Reconstruct pandas Series from cached JSON."""
        cached_json = self._cache[series_id]['data']
        return pd.read_json(cached_json, typ='series')

    def get_latest_value(self, series_id: str) -> float:
        """
        Get the most recent value for a FRED series.

        Args:
            series_id: FRED series ID

        Returns:
            Latest value
        """
        series = self.get_series(series_id)
        return float(series.iloc[-1])

    # Convenience methods for common series

    def get_gdp(self, nominal: bool = True) -> pd.Series:
        """
        Get GDP data.

        Args:
            nominal: If True, returns nominal GDP (billions of dollars).
                    If False, returns real GDP (chained 2017 dollars).

        Returns:
            Quarterly GDP series
        """
        series_id = 'GDP' if nominal else 'GDPC1'
        return self.get_series(series_id)

    def get_unemployment(self) -> pd.Series:
        """
        Get unemployment rate (percent, not seasonally adjusted).

        Returns:
            Monthly unemployment rate series
        """
        return self.get_series('UNRATE')

    def get_interest_rate_10yr(self) -> pd.Series:
        """
        Get 10-Year Treasury Constant Maturity Rate (percent).

        Returns:
            Daily 10-year Treasury rate series
        """
        return self.get_series('DGS10')

    def get_inflation(self, start_date: Optional[str] = None) -> pd.Series:
        """
        Get Consumer Price Index (CPI) for All Urban Consumers.

        Returns:
            Monthly CPI series
        """
        return self.get_series('CPIAUCSL', start_date=start_date)

    def get_labor_force_participation(self) -> pd.Series:
        """
        Get civilian labor force participation rate (percent).

        Returns:
            Monthly labor force participation rate series
        """
        return self.get_series('CIVPART')

    def calculate_growth_rate(self, series: pd.Series, periods: int = 4) -> float:
        """
        Calculate annualized growth rate from a series.

        Args:
            series: Time series data
            periods: Number of periods for growth calculation (4 for quarterly annualized)

        Returns:
            Annualized growth rate (as decimal, e.g., 0.025 for 2.5%)
        """
        if len(series) < periods + 1:
            raise ValueError(f"Series too short for {periods}-period growth rate")

        recent = series.iloc[-1]
        previous = series.iloc[-(periods + 1)]

        return (recent / previous) ** (1 / periods) - 1

    def get_recent_gdp_growth(self, nominal: bool = False) -> float:
        """
        Get recent GDP growth rate (4-quarter annualized).

        Args:
            nominal: If True, nominal GDP growth. If False, real GDP growth.

        Returns:
            Annualized growth rate (decimal)
        """
        gdp = self.get_gdp(nominal=nominal)
        return self.calculate_growth_rate(gdp, periods=4)

    def get_recent_inflation(self) -> float:
        """
        Get recent inflation rate (12-month change in CPI).

        Returns:
            Annual inflation rate (decimal)
        """
        cpi = self.get_inflation()
        if len(cpi) < 13:
            raise ValueError("Insufficient CPI data")

        return (cpi.iloc[-1] / cpi.iloc[-13]) - 1

    def clear_cache(self, older_than_hours: Optional[int] = None):
        """
        Clear cached FRED data.

        Args:
            older_than_hours: If specified, only clear cache older than this.
                            If None, clear all cache.
        """
        if older_than_hours is None:
            self._cache = {}
            logger.info("Cleared all FRED cache")
        else:
            cutoff = datetime.now() - timedelta(hours=older_than_hours)
            original_count = len(self._cache)

            self._cache = {
                k: v for k, v in self._cache.items()
                if datetime.fromisoformat(v['timestamp']) > cutoff
            }

            removed = original_count - len(self._cache)
            logger.info(f"Cleared {removed} stale cache entries older than {older_than_hours} hours")

        self._save_cache()

    def get_cache_status(self) -> Dict[str, Dict]:
        """
        Get status of cached data.

        Returns:
            Dictionary mapping series_id to cache info (timestamp, age_hours)
        """
        status = {}
        now = datetime.now()

        for series_id, cache_entry in self._cache.items():
            cached_time = datetime.fromisoformat(cache_entry['timestamp'])
            age = now - cached_time

            status[series_id] = {
                'timestamp': cache_entry['timestamp'],
                'age_hours': age.total_seconds() / 3600,
                'fresh': age < timedelta(hours=self.CACHE_HOURS)
            }

        return status

    def is_available(self) -> bool:
        """Check if FRED API is available and configured."""
        return self.fred is not None
