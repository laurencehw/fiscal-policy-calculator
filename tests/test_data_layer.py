"""
Tests for fiscal_model/data — IRS SOI, Capital Gains, FRED data layers.

Covers:
- IRSSOIData initializes without error
- get_data_years_available returns a list of ints
- get_filers_by_bracket returns dict with expected keys
- CapitalGainsBaseline initializes without error
- FREDData.is_available returns bool
- FREDData fallback works when API unavailable
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.data.capital_gains import CapitalGainsBaseline
from fiscal_model.data.fred_data import FREDData
from fiscal_model.data.irs_soi import IRSSOIData

# =============================================================================
# IRS SOI DATA
# =============================================================================

class TestIRSSOIData:

    def test_initializes_without_error(self):
        irs = IRSSOIData()
        assert irs is not None

    def test_get_data_years_available_returns_ints(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        assert isinstance(years, list)
        assert len(years) > 0
        for y in years:
            assert isinstance(y, int)

    def test_get_data_years_sorted(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        assert years == sorted(years)

    def test_get_filers_by_bracket_returns_expected_keys(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        result = irs.get_filers_by_bracket(year=years[-1], threshold=400_000)
        expected_keys = {
            "num_filers",
            "num_filers_millions",
            "avg_agi",
            "avg_taxable_income",
            "total_agi_billions",
            "total_taxable_income_billions",
            "total_tax_billions",
            "effective_tax_rate",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_filers_above_400k_reasonable(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        result = irs.get_filers_by_bracket(year=years[-1], threshold=400_000)
        # Should be at least some filers above $400K
        assert result["num_filers"] > 0
        assert result["avg_agi"] > 400_000

    def test_filers_above_zero_threshold(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        result = irs.get_filers_by_bracket(year=years[-1], threshold=0)
        # All filers
        assert result["num_filers"] > 1_000_000

    def test_get_total_revenue(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        revenue = irs.get_total_revenue(year=years[-1])
        # Total income tax revenue should be positive and in hundreds of billions
        assert revenue > 100  # > $100B
        assert revenue < 10_000  # < $10T (sanity)

    def test_get_bracket_distribution(self):
        irs = IRSSOIData()
        years = irs.get_data_years_available()
        brackets = irs.get_bracket_distribution(year=years[-1])
        assert isinstance(brackets, list)
        assert len(brackets) > 5  # Should have multiple brackets

    def test_nonexistent_year_raises(self):
        irs = IRSSOIData()
        with pytest.raises(FileNotFoundError):
            irs.get_filers_by_bracket(year=1900, threshold=0)


# =============================================================================
# CAPITAL GAINS BASELINE
# =============================================================================

class TestCapitalGainsBaseline:

    def test_initializes_without_error(self):
        cg = CapitalGainsBaseline()
        assert cg is not None

    def test_share_above_threshold_zero(self):
        cg = CapitalGainsBaseline()
        share = cg._share_above_threshold(0)
        assert share == 1.0

    def test_share_above_threshold_high(self):
        cg = CapitalGainsBaseline()
        share = cg._share_above_threshold(10_000_000)
        assert 0 < share <= 0.10

    def test_share_monotonically_decreasing(self):
        cg = CapitalGainsBaseline()
        thresholds = [0, 50_000, 200_000, 500_000, 1_000_000, 5_000_000]
        shares = [cg._share_above_threshold(t) for t in thresholds]
        for i in range(len(shares) - 1):
            assert shares[i] >= shares[i + 1]

    def test_baseline_with_rate_method(self):
        cg = CapitalGainsBaseline()
        result = cg.get_baseline_above_threshold_with_rate_method(
            year=2022, threshold=400_000
        )
        assert "net_capital_gain_billions" in result
        assert "average_effective_tax_rate" in result
        assert result["net_capital_gain_billions"] > 0

    def test_statutory_proxy_rate(self):
        rate_low = CapitalGainsBaseline._statutory_proxy_rate(50_000)
        rate_high = CapitalGainsBaseline._statutory_proxy_rate(1_000_000)
        assert rate_high > rate_low

    def test_taxfoundation_rate_method(self):
        cg = CapitalGainsBaseline()
        result = cg.get_baseline_above_threshold_with_rate_method(
            year=2022, threshold=0, rate_method="taxfoundation_aggregate"
        )
        assert result["rate_source"] == "taxfoundation_aggregate"


# =============================================================================
# FRED DATA
# =============================================================================

class TestFREDData:

    def test_initializes_without_error(self):
        fred = FREDData()
        assert fred is not None

    def test_is_available_returns_bool(self):
        fred = FREDData()
        assert isinstance(fred.is_available(), bool)

    def test_fallback_when_api_unavailable(self, tmp_path):
        """Without FRED_API_KEY, _get_series should return fallback data."""
        fred = FREDData(cache_dir=tmp_path)
        # Even without API key, get_gdp should not raise
        gdp = fred.get_gdp(nominal=True)
        assert isinstance(gdp, pd.Series)
        assert len(gdp) > 0
        assert fred.data_status["source"] == "fallback"
        assert fred.data_status["last_updated"] is None
        assert "GDP" in fred.data_status["error"]

    def test_get_unemployment_fallback(self, tmp_path):
        fred = FREDData(cache_dir=tmp_path)
        series = fred.get_unemployment()
        assert isinstance(series, pd.Series)
        assert len(series) > 0

    def test_get_interest_rate_fallback(self, tmp_path):
        fred = FREDData(cache_dir=tmp_path)
        series = fred.get_interest_rate()
        assert isinstance(series, pd.Series)
        assert len(series) > 0

    def test_cache_dir_created(self, tmp_path):
        cache_dir = tmp_path / "fred_cache"
        FREDData(cache_dir=cache_dir)
        assert cache_dir.exists()

    def test_reads_fresh_cache_with_status_metadata(self, tmp_path, monkeypatch):
        fred = FREDData(cache_dir=tmp_path)
        monkeypatch.setattr(
            "fiscal_model.data.fred_data.utc_now",
            lambda: pd.Timestamp("2024-04-01T00:00:00Z").to_pydatetime(),
        )
        fred._write_cache("GDP", pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-01", "2024-04-01"])))
        monkeypatch.setattr(fred, "_fetch_live_series", lambda series_id: None)

        series = fred.get_gdp()

        assert isinstance(series, pd.Series)
        assert fred.data_status["source"] == "cache"
        assert fred.data_status["cache_is_expired"] is False
        assert fred.data_status["cache_age_days"] == 0
        assert fred.data_status["last_updated"] == pd.Timestamp("2024-04-01T00:00:00Z").to_pydatetime()

    def test_reads_stale_cache_with_expired_flag(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "cache"
        fred = FREDData(cache_dir=cache_dir, cache_max_age_days=30)
        cache_file = cache_dir / "fred_GDP.json"
        cache_file.write_text(
            """
            {
              "series_id": "GDP",
              "updated_at": "2024-01-01T00:00:00+00:00",
              "values": {
                "2024-01-01 00:00:00": 30300.0
              }
            }
            """.strip(),
            encoding="utf-8",
        )
        monkeypatch.setattr(fred, "_fetch_live_series", lambda series_id: None)
        monkeypatch.setattr("fiscal_model.data.fred_data.utc_now", lambda: pd.Timestamp("2024-03-15T00:00:00Z").to_pydatetime())

        series = fred.get_gdp()

        assert isinstance(series, pd.Series)
        assert fred.data_status["source"] == "cache"
        assert fred.data_status["cache_is_expired"] is True
        assert fred.data_status["cache_age_days"] == 74
        assert fred.data_status["last_updated"] == pd.Timestamp("2024-01-01T00:00:00Z").to_pydatetime()

    def test_data_status_infers_cache_before_first_fetch(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "cache"
        fred = FREDData(cache_dir=cache_dir, cache_max_age_days=30)
        (cache_dir / "fred_GDP.json").write_text(
            """
            {
              "series_id": "GDP",
              "updated_at": "2024-01-01T00:00:00Z",
              "values": {
                "2024-01-01 00:00:00": 30300.0
              }
            }
            """.strip(),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "fiscal_model.data.fred_data.utc_now",
            lambda: pd.Timestamp("2024-01-31T00:00:00Z").to_pydatetime(),
        )

        status = fred.data_status

        assert status["source"] == "cache"
        assert status["cache_age_days"] == 30
        assert status["cache_is_expired"] is False
        assert status["last_updated"] == pd.Timestamp("2024-01-01T00:00:00Z").to_pydatetime()

    def test_refresh_returns_false_without_api(self, tmp_path):
        fred = FREDData(cache_dir=tmp_path)

        assert fred.refresh() is False
        assert fred.data_status["error"] == "FRED API not available"

    def test_refresh_updates_live_status_when_any_series_succeeds(self, tmp_path, monkeypatch):
        fred = FREDData(cache_dir=tmp_path)
        fred._fred = object()
        written_series: list[str] = []

        monkeypatch.setattr(
            fred,
            "_fetch_live_series",
            lambda series_id: pd.Series([1.0], index=pd.to_datetime(["2024-01-01"]), name=series_id)
            if series_id == "GDP"
            else None,
        )
        monkeypatch.setattr(
            fred,
            "_write_cache",
            lambda series_id, series: written_series.append(series_id),
        )

        assert fred.refresh() is True
        assert written_series == ["GDP"]
        assert fred.data_status["source"] == "live"
        assert fred.data_status["cache_age_days"] == 0
        assert fred.data_status["cache_is_expired"] is False
        assert fred.data_status["error"] is None
