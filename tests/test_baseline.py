"""
Tests for the baseline budget projection module.

Tests cover:
- EconomicAssumptions default values
- BaselineProjection properties and methods
- CBOBaseline initialization and generation
- Revenue and spending category consistency
- adjust_for_policy immutability
- Array length invariants
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.baseline import BaselineProjection, CBOBaseline, EconomicAssumptions

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def assumptions():
    """Default economic assumptions."""
    return EconomicAssumptions()


@pytest.fixture
def cbo_baseline():
    """CBOBaseline generator using hardcoded fallback data."""
    return CBOBaseline(start_year=2025, use_real_data=False)


@pytest.fixture
def projection(cbo_baseline):
    """Generated baseline projection from hardcoded data."""
    return cbo_baseline.generate()


# =============================================================================
# ECONOMIC ASSUMPTIONS
# =============================================================================

class TestEconomicAssumptions:
    """Test EconomicAssumptions default values."""

    def test_arrays_length_10(self, assumptions):
        """All assumption arrays should have length 10."""
        assert len(assumptions.real_gdp_growth) == 10, "real_gdp_growth should have 10 elements"
        assert len(assumptions.inflation) == 10, "inflation should have 10 elements"
        assert len(assumptions.unemployment) == 10, "unemployment should have 10 elements"
        assert len(assumptions.interest_rate_10yr) == 10, "interest_rate_10yr should have 10 elements"
        assert len(assumptions.labor_force_participation) == 10, "labor_force_participation should have 10 elements"

    def test_gdp_growth_positive(self, assumptions):
        """Real GDP growth rates should all be positive."""
        assert np.all(assumptions.real_gdp_growth > 0), (
            "All real GDP growth rates should be positive"
        )

    def test_inflation_positive(self, assumptions):
        """Inflation rates should all be positive."""
        assert np.all(assumptions.inflation > 0), (
            "All inflation rates should be positive"
        )

    def test_unemployment_reasonable(self, assumptions):
        """Unemployment rates should be between 0% and 15%."""
        assert np.all(assumptions.unemployment > 0), "Unemployment should be positive"
        assert np.all(assumptions.unemployment < 0.15), "Unemployment should be below 15%"

    def test_interest_rates_positive(self, assumptions):
        """Interest rates should be positive."""
        assert np.all(assumptions.interest_rate_10yr > 0), (
            "10-year Treasury rates should be positive"
        )

    def test_labor_force_participation_reasonable(self, assumptions):
        """Labor force participation should be between 50% and 75%."""
        assert np.all(assumptions.labor_force_participation > 0.50), (
            "Labor force participation should be above 50%"
        )
        assert np.all(assumptions.labor_force_participation < 0.75), (
            "Labor force participation should be below 75%"
        )


# =============================================================================
# BASELINE PROJECTION PROPERTIES
# =============================================================================

class TestBaselineProjectionProperties:
    """Test BaselineProjection computed properties."""

    def test_total_revenues(self, projection):
        """total_revenues should equal sum of revenue categories."""
        expected = (
            projection.individual_income_tax
            + projection.corporate_income_tax
            + projection.payroll_taxes
            + projection.other_revenues
        )
        np.testing.assert_allclose(
            projection.total_revenues, expected,
            rtol=1e-10,
            err_msg="total_revenues should equal sum of individual + corporate + payroll + other"
        )

    def test_total_outlays(self, projection):
        """total_outlays should equal sum of spending categories."""
        expected = (
            projection.social_security
            + projection.medicare
            + projection.medicaid
            + projection.other_mandatory
            + projection.defense_discretionary
            + projection.nondefense_discretionary
            + projection.net_interest
        )
        np.testing.assert_allclose(
            projection.total_outlays, expected,
            rtol=1e-10,
            err_msg="total_outlays should equal sum of all spending categories"
        )

    def test_deficit_equals_outlays_minus_revenues(self, projection):
        """Deficit should be outlays minus revenues."""
        expected = projection.total_outlays - projection.total_revenues
        np.testing.assert_allclose(
            projection.deficit, expected,
            rtol=1e-10,
            err_msg="deficit should be total_outlays - total_revenues"
        )

    def test_deficit_positive(self, projection):
        """Baseline projection should show deficits (positive values)."""
        assert np.all(projection.deficit > 0), (
            "Baseline should project deficits (outlays > revenues)"
        )

    def test_debt_to_gdp(self, projection):
        """debt_to_gdp should be debt / GDP * 100."""
        expected = projection.debt_held_by_public / projection.nominal_gdp * 100
        np.testing.assert_allclose(
            projection.debt_to_gdp, expected,
            rtol=1e-10,
            err_msg="debt_to_gdp should equal debt / nominal_gdp * 100"
        )

    def test_debt_to_gdp_reasonable_range(self, projection):
        """Debt-to-GDP should be in a plausible range (50%-200%)."""
        assert np.all(projection.debt_to_gdp > 50), (
            "Debt-to-GDP should be above 50%"
        )
        assert np.all(projection.debt_to_gdp < 200), (
            "Debt-to-GDP should be below 200%"
        )

    def test_primary_deficit(self, projection):
        """Primary deficit should be deficit minus net interest."""
        expected = projection.deficit - projection.net_interest
        np.testing.assert_allclose(
            projection.primary_deficit, expected,
            rtol=1e-10,
            err_msg="primary_deficit should be deficit - net_interest"
        )

    def test_deficit_to_gdp(self, projection):
        """deficit_to_gdp should be deficit / GDP * 100."""
        expected = projection.deficit / projection.nominal_gdp * 100
        np.testing.assert_allclose(
            projection.deficit_to_gdp, expected,
            rtol=1e-10,
            err_msg="deficit_to_gdp should be deficit / nominal_gdp * 100"
        )


# =============================================================================
# BASELINE PROJECTION METHODS
# =============================================================================

class TestBaselineProjectionMethods:
    """Test BaselineProjection methods."""

    def test_get_year_index_start(self, projection):
        """get_year_index for start year should return 0."""
        assert projection.get_year_index(2025) == 0, (
            "Index for start year should be 0"
        )

    def test_get_year_index_middle(self, projection):
        """get_year_index for a middle year should return correct offset."""
        assert projection.get_year_index(2030) == 5, (
            "Index for 2030 should be 5 (2030 - 2025)"
        )

    def test_get_year_index_last(self, projection):
        """get_year_index for last year should return 9."""
        assert projection.get_year_index(2034) == 9, (
            "Index for last year (2034) should be 9"
        )

    def test_get_value_individual_income_tax(self, projection):
        """get_value should return correct value for a category and year."""
        idx = projection.get_year_index(2025)
        expected = projection.individual_income_tax[idx]
        actual = projection.get_value('individual_income_tax', 2025)
        assert actual == pytest.approx(expected), (
            "get_value should match direct array access"
        )

    def test_get_value_different_categories(self, projection):
        """get_value should work for multiple categories."""
        categories = [
            'nominal_gdp', 'individual_income_tax', 'corporate_income_tax',
            'payroll_taxes', 'social_security', 'medicare', 'net_interest',
        ]
        for cat in categories:
            value = projection.get_value(cat, 2028)
            assert isinstance(value, (float, np.floating)), (
                f"get_value('{cat}', 2028) should return a float"
            )

    def test_get_cumulative_deficit_full_window(self, projection):
        """get_cumulative_deficit with no args should sum full 10-year window."""
        expected = np.sum(projection.deficit)
        actual = projection.get_cumulative_deficit()
        assert actual == pytest.approx(expected), (
            "Full window cumulative deficit should equal sum of deficit array"
        )

    def test_get_cumulative_deficit_subrange(self, projection):
        """get_cumulative_deficit for a subrange should sum only those years."""
        expected = np.sum(projection.deficit[2:5])  # Years 2027-2029
        actual = projection.get_cumulative_deficit(start_year=2027, end_year=2029)
        assert actual == pytest.approx(expected), (
            "Subrange cumulative deficit should match array slice sum"
        )

    def test_get_cumulative_deficit_single_year(self, projection):
        """get_cumulative_deficit for a single year should return that year's deficit."""
        expected = projection.deficit[0]
        actual = projection.get_cumulative_deficit(start_year=2025, end_year=2025)
        assert actual == pytest.approx(expected), (
            "Single-year cumulative deficit should equal that year's deficit"
        )


# =============================================================================
# CBO BASELINE INITIALIZATION
# =============================================================================

class TestCBOBaselineInit:
    """Test CBOBaseline initialization."""

    def test_init_hardcoded_fallback(self):
        """CBOBaseline with use_real_data=False should use hardcoded values."""
        # Default vintage is CBO Feb 2026 with updated GDP
        gen = CBOBaseline(start_year=2026, use_real_data=False)
        assert gen.base_gdp == 30300, "Hardcoded GDP should be 30300 (Feb 2026 baseline)"
        assert gen.base_individual_income_tax == 2700, "Hardcoded income tax should be 2700"

    def test_init_hardcoded_fallback_legacy_vintage(self):
        """CBOBaseline with Feb 2024 vintage should use legacy hardcoded values."""
        from fiscal_model.baseline import BaselineVintage
        gen = CBOBaseline(start_year=2025, use_real_data=False, vintage=BaselineVintage.CBO_FEB_2024)
        assert gen.base_gdp == 28500, "Legacy GDP should be 28500"
        assert gen.base_individual_income_tax == 2500, "Legacy income tax should be 2500"

    def test_init_custom_start_year(self):
        """CBOBaseline respects custom start year."""
        gen = CBOBaseline(start_year=2030, use_real_data=False)
        assert gen.start_year == 2030
        assert gen.years[0] == 2030
        assert gen.years[-1] == 2039

    def test_init_years_array_length(self, cbo_baseline):
        """Years array should have 10 elements."""
        assert len(cbo_baseline.years) == 10, "Should have 10-year window"

    def test_init_assumptions_created(self, cbo_baseline):
        """CBOBaseline should create EconomicAssumptions."""
        assert cbo_baseline.assumptions is not None
        assert isinstance(cbo_baseline.assumptions, EconomicAssumptions)

    def test_init_tracks_fallback_metadata(self):
        """Hardcoded fallback mode should expose explicit source metadata."""
        gen = CBOBaseline(start_year=2026, use_real_data=False)

        assert gen.metadata["source"] == "hardcoded_fallback"
        assert gen.metadata["gdp_source"] == "hardcoded"
        assert gen.metadata["requested_real_data"] is False

    def test_real_data_baseline_uses_cached_fred_without_live_api(self, monkeypatch):
        """Cached FRED GDP should be usable even when no live API key is configured."""
        import fiscal_model.data as data_module

        class DummyIRSData:
            def get_data_years_available(self):
                return [2022]

            def get_total_revenue(self, year):
                assert year == 2022
                return 2700.0

        class DummyFREDData:
            def get_gdp(self, nominal=True):
                assert nominal is True
                return pd.Series([31_000.0], index=pd.to_datetime(["2025-01-01"]), name="GDP")

            @property
            def data_status(self):
                return {
                    "source": "cache",
                    "last_updated": pd.Timestamp("2025-01-01T00:00:00Z").to_pydatetime(),
                    "cache_age_days": 5,
                    "cache_is_expired": False,
                    "api_available": False,
                    "error": None,
                }

        monkeypatch.setattr(data_module, "IRSSOIData", DummyIRSData)
        monkeypatch.setattr(data_module, "FREDData", DummyFREDData)

        gen = CBOBaseline(start_year=2026, use_real_data=True)

        assert gen.base_gdp == 31_000.0
        assert gen.metadata["source"] == "real_data"
        assert gen.metadata["gdp_source"] == "fred_cache"
        assert gen.metadata["irs_data_year"] == 2022


# =============================================================================
# CBO BASELINE GENERATION
# =============================================================================

class TestCBOBaselineGeneration:
    """Test CBOBaseline.generate() output."""

    def test_generate_returns_projection(self, cbo_baseline):
        """generate() should return a BaselineProjection."""
        proj = cbo_baseline.generate()
        assert isinstance(proj, BaselineProjection)

    def test_gdp_increasing(self, projection):
        """Nominal GDP should increase over the 10-year window."""
        for i in range(1, 10):
            assert projection.nominal_gdp[i] > projection.nominal_gdp[i - 1], (
                f"Nominal GDP in year {i + 1} should exceed year {i}"
            )

    def test_real_gdp_increasing(self, projection):
        """Real GDP should increase over the 10-year window."""
        for i in range(1, 10):
            assert projection.real_gdp[i] > projection.real_gdp[i - 1], (
                f"Real GDP in year {i + 1} should exceed year {i}"
            )

    def test_nominal_gdp_exceeds_real(self, projection):
        """Nominal GDP should exceed real GDP (positive inflation)."""
        assert np.all(projection.nominal_gdp > projection.real_gdp), (
            "Nominal GDP should be greater than real GDP with positive inflation"
        )

    def test_revenues_positive(self, projection):
        """All revenue categories should be positive."""
        assert np.all(projection.individual_income_tax > 0), "Individual income tax should be positive"
        assert np.all(projection.corporate_income_tax > 0), "Corporate income tax should be positive"
        assert np.all(projection.payroll_taxes > 0), "Payroll taxes should be positive"
        assert np.all(projection.other_revenues > 0), "Other revenues should be positive"

    def test_spending_positive(self, projection):
        """All spending categories should be positive."""
        assert np.all(projection.social_security > 0), "Social Security should be positive"
        assert np.all(projection.medicare > 0), "Medicare should be positive"
        assert np.all(projection.medicaid > 0), "Medicaid should be positive"
        assert np.all(projection.defense_discretionary > 0), "Defense should be positive"
        assert np.all(projection.nondefense_discretionary > 0), "Nondefense should be positive"
        assert np.all(projection.net_interest > 0), "Net interest should be positive"

    def test_revenue_categories_sum_to_total(self, projection):
        """Revenue categories should sum to total_revenues."""
        category_sum = (
            projection.individual_income_tax
            + projection.corporate_income_tax
            + projection.payroll_taxes
            + projection.other_revenues
        )
        np.testing.assert_allclose(
            category_sum, projection.total_revenues,
            rtol=1e-10,
            err_msg="Revenue categories should sum to total_revenues"
        )

    def test_spending_categories_sum_to_total(self, projection):
        """Spending categories (including interest) should sum to total_outlays."""
        category_sum = (
            projection.social_security
            + projection.medicare
            + projection.medicaid
            + projection.other_mandatory
            + projection.defense_discretionary
            + projection.nondefense_discretionary
            + projection.net_interest
        )
        np.testing.assert_allclose(
            category_sum, projection.total_outlays,
            rtol=1e-10,
            err_msg="Spending categories should sum to total_outlays"
        )

    def test_deficit_is_reasonable(self, projection):
        """Deficit should be positive and reasonable relative to GDP."""
        deficit_to_gdp = projection.deficit / projection.nominal_gdp * 100
        assert np.all(deficit_to_gdp > 0), "Should project deficits"
        assert np.all(deficit_to_gdp < 20), (
            "Deficit-to-GDP should be below 20% in baseline"
        )

    def test_debt_grows_with_deficits(self, projection):
        """Debt should grow over time given persistent deficits."""
        for i in range(1, 10):
            assert projection.debt_held_by_public[i] > projection.debt_held_by_public[i - 1], (
                f"Debt in year {i + 1} should exceed year {i} with persistent deficits"
            )

    def test_social_security_grows_faster_than_defense(self, projection):
        """Social Security (5% growth) should outpace defense (2% growth)."""
        ss_growth = projection.social_security[-1] / projection.social_security[0]
        defense_growth = projection.defense_discretionary[-1] / projection.defense_discretionary[0]
        assert ss_growth > defense_growth, (
            "Social Security growth should exceed defense growth"
        )


# =============================================================================
# PROJECTION ARRAY LENGTHS
# =============================================================================

class TestProjectionArrayLengths:
    """All projection arrays should have exactly 10 elements."""

    def test_years_length(self, projection):
        assert len(projection.years) == 10, "years should have 10 elements"

    def test_gdp_arrays_length(self, projection):
        assert len(projection.nominal_gdp) == 10, "nominal_gdp should have 10 elements"
        assert len(projection.real_gdp) == 10, "real_gdp should have 10 elements"

    def test_revenue_arrays_length(self, projection):
        assert len(projection.individual_income_tax) == 10
        assert len(projection.corporate_income_tax) == 10
        assert len(projection.payroll_taxes) == 10
        assert len(projection.other_revenues) == 10

    def test_spending_arrays_length(self, projection):
        assert len(projection.social_security) == 10
        assert len(projection.medicare) == 10
        assert len(projection.medicaid) == 10
        assert len(projection.other_mandatory) == 10
        assert len(projection.defense_discretionary) == 10
        assert len(projection.nondefense_discretionary) == 10
        assert len(projection.net_interest) == 10

    def test_debt_array_length(self, projection):
        assert len(projection.debt_held_by_public) == 10

    def test_derived_arrays_length(self, projection):
        """Derived properties should also have 10 elements."""
        assert len(projection.total_revenues) == 10
        assert len(projection.total_outlays) == 10
        assert len(projection.deficit) == 10
        assert len(projection.primary_deficit) == 10
        assert len(projection.deficit_to_gdp) == 10
        assert len(projection.debt_to_gdp) == 10


# =============================================================================
# ADJUST FOR POLICY
# =============================================================================

class TestAdjustForPolicy:
    """Test CBOBaseline.adjust_for_policy."""

    def test_returns_new_projection(self, cbo_baseline, projection):
        """adjust_for_policy should return a new BaselineProjection."""
        changes = np.full(10, 50.0)  # $50B increase per year
        new_proj = cbo_baseline.adjust_for_policy(
            projection, 'individual_income_tax', changes
        )
        assert isinstance(new_proj, BaselineProjection)
        assert new_proj is not projection, "Should return a new object, not mutate original"

    def test_original_unchanged(self, cbo_baseline, projection):
        """Original projection should not be modified."""
        original_tax = projection.individual_income_tax.copy()
        changes = np.full(10, 100.0)
        cbo_baseline.adjust_for_policy(projection, 'individual_income_tax', changes)
        np.testing.assert_array_equal(
            projection.individual_income_tax, original_tax,
            err_msg="Original projection should not be modified"
        )

    def test_changes_applied_correctly(self, cbo_baseline, projection):
        """Changes should be added to the specified category."""
        changes = np.full(10, 25.0)
        new_proj = cbo_baseline.adjust_for_policy(
            projection, 'individual_income_tax', changes
        )
        expected = projection.individual_income_tax + changes
        np.testing.assert_allclose(
            new_proj.individual_income_tax, expected,
            rtol=1e-10,
            err_msg="Adjusted category should equal original + changes"
        )

    def test_other_categories_unchanged(self, cbo_baseline, projection):
        """Categories not targeted should remain unchanged."""
        changes = np.full(10, 50.0)
        new_proj = cbo_baseline.adjust_for_policy(
            projection, 'individual_income_tax', changes
        )
        np.testing.assert_array_equal(
            new_proj.corporate_income_tax, projection.corporate_income_tax,
            err_msg="Corporate tax should be unchanged when adjusting income tax"
        )
        np.testing.assert_array_equal(
            new_proj.social_security, projection.social_security,
            err_msg="Social Security should be unchanged when adjusting income tax"
        )

    def test_adjust_spending_category(self, cbo_baseline, projection):
        """adjust_for_policy should also work for spending categories."""
        changes = np.full(10, -30.0)  # $30B cut
        new_proj = cbo_baseline.adjust_for_policy(
            projection, 'defense_discretionary', changes
        )
        expected = projection.defense_discretionary + changes
        np.testing.assert_allclose(
            new_proj.defense_discretionary, expected,
            rtol=1e-10,
            err_msg="Defense spending should be reduced by the change amount"
        )

    def test_adjusted_revenues_differ(self, cbo_baseline, projection):
        """Adjusting a revenue category should change total_revenues in the new projection."""
        changes = np.full(10, 50.0)
        new_proj = cbo_baseline.adjust_for_policy(
            projection, 'individual_income_tax', changes
        )
        assert np.all(new_proj.total_revenues > projection.total_revenues), (
            "Adding revenue should increase total_revenues"
        )
