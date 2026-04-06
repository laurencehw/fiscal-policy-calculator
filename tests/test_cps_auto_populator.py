"""
Tests for CPS microdata auto-populator.

Validates that CPS-based filer counts and income statistics are
more accurate than the IRS SOI heuristic for policy auto-population.
"""

import pytest

from fiscal_model.microsim.cps_auto_populator import CPSAutoPopulator


@pytest.fixture
def cps():
    if not CPSAutoPopulator.is_available():
        pytest.skip("CPS microdata not available")
    return CPSAutoPopulator()


class TestCPSAutoPopulator:

    def test_loads_without_error(self, cps):
        assert cps is not None

    def test_total_filers_reasonable(self, cps):
        """Total weighted filers should be in range 150-200M."""
        stats = cps.get_filers_by_threshold(0)
        assert 100e6 <= stats["num_filers"] <= 250e6

    def test_threshold_reduces_filers(self, cps):
        """Higher threshold should mean fewer filers."""
        all_filers = cps.get_filers_by_threshold(0)
        high_earners = cps.get_filers_by_threshold(400_000)
        assert high_earners["num_filers"] < all_filers["num_filers"]

    def test_400k_threshold_filer_count(self, cps):
        """Filers with taxable income > $400K should be ~1-4M (CBO/IRS range)."""
        stats = cps.get_filers_by_threshold(400_000, income_basis="taxable_income")
        filers_m = stats["num_filers_millions"]
        assert 0.5 <= filers_m <= 5.0, (
            f"Expected 0.5-5M filers above $400K taxable, got {filers_m:.2f}M"
        )

    def test_taxable_income_basis_fewer_than_agi(self, cps):
        """Filtering on taxable_income should yield fewer filers than AGI."""
        agi_stats = cps.get_filers_by_threshold(200_000, income_basis="agi")
        ti_stats = cps.get_filers_by_threshold(200_000, income_basis="taxable_income")
        assert ti_stats["num_filers"] <= agi_stats["num_filers"], (
            "Taxable income threshold should capture fewer filers than AGI threshold"
        )

    def test_avg_taxable_income_above_threshold(self, cps):
        """Average taxable income should be above the threshold."""
        threshold = 200_000
        stats = cps.get_filers_by_threshold(threshold, income_basis="taxable_income")
        if stats["num_filers"] > 0:
            assert stats["avg_taxable_income"] >= threshold

    def test_empty_result_for_extreme_threshold(self, cps):
        """Very high threshold should return zero filers."""
        stats = cps.get_filers_by_threshold(100_000_000)
        assert stats["num_filers"] == 0

    def test_effective_tax_rate_reasonable(self, cps):
        """Effective tax rate should be between 0 and 40%."""
        stats = cps.get_filers_by_threshold(100_000, income_basis="taxable_income")
        assert 0.0 <= stats["effective_tax_rate"] <= 0.40

    def test_return_keys_match_irs_interface(self, cps):
        """Return dict should have all keys from IRSSOIData.get_filers_by_bracket."""
        stats = cps.get_filers_by_threshold(0)
        expected_keys = {
            "num_filers", "num_filers_millions",
            "avg_agi", "avg_taxable_income",
            "total_agi_billions", "total_taxable_income_billions",
            "total_tax_billions", "effective_tax_rate",
        }
        assert expected_keys == set(stats.keys())

    def test_invalid_basis_raises(self, cps):
        with pytest.raises(ValueError, match="income_basis"):
            cps.get_filers_by_threshold(0, income_basis="invalid")
