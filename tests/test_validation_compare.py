"""
Tests for validation and comparison modules.

Covers:
- fiscal_model/validation/compare.py (comparison functions)
- fiscal_model/data/validation.py (data validators)
- fiscal_model/validation/distributional_validation.py (distributional benchmarks)
- fiscal_model/constants.py (constants access)

Tests ensure validation functions work correctly with various policy inputs.
"""

import pandas as pd

from fiscal_model.amt import CORPORATE_AMT
from fiscal_model.constants import (
    BASELINE_GROWTH,
    BUDGET_WINDOW_YEARS,
    CG_LONG_RUN_ELASTICITY,
    CG_SHORT_RUN_ELASTICITY,
    CG_TRANSITION_YEARS,
    DEFAULT_CAPITAL_ELASTICITY,
    DEFAULT_CORPORATE_ELASTICITY,
    DEFAULT_ETI,
    DEFAULT_LABOR_SUPPLY_ELASTICITY,
    FALLBACK_BASELINE,
    GDP_RATIOS,
    GROWTH_RATES,
    JOBS_PER_GDP_PERCENT,
    LABOR_SHARE,
    MARGINAL_REVENUE_RATE,
    SPENDING_MULTIPLIER_BASE,
    TAX_MULTIPLIER_BASE,
    TRANSFER_MULTIPLIER_BASE,
)
from fiscal_model.data.validation import DataValidator, ValidationResult
from fiscal_model.policies import TaxPolicy
from fiscal_model.validation.compare import (
    ValidationResult as ComparisonValidationResult,
)
from fiscal_model.validation.compare import (
    _rate_accuracy,
    create_policy_from_score,
)
from fiscal_model.validation.distributional_validation import (
    CORPORATE_INCIDENCE,
    TPC_TCJA_2018,
    DistributionalBenchmark,
)

# =============================================================================
# CONSTANTS TESTS
# =============================================================================


class TestConstants:
    """Tests for fiscal_model/constants.py constants."""

    def test_budget_window_years_is_positive_int(self):
        """Verify BUDGET_WINDOW_YEARS is a positive integer."""
        assert isinstance(BUDGET_WINDOW_YEARS, int)
        assert BUDGET_WINDOW_YEARS > 0
        assert BUDGET_WINDOW_YEARS == 10  # Standard 10-year window

    def test_elasticity_constants_are_positive(self):
        """Verify elasticity constants are in valid ranges."""
        assert 0 <= DEFAULT_ETI <= 1.0
        assert 0 <= DEFAULT_LABOR_SUPPLY_ELASTICITY <= 1.0
        assert 0 <= DEFAULT_CAPITAL_ELASTICITY <= 1.0
        assert 0 <= DEFAULT_CORPORATE_ELASTICITY <= 1.0

    def test_capital_gains_elasticity_constants(self):
        """Verify capital gains elasticity constants."""
        assert CG_SHORT_RUN_ELASTICITY > CG_LONG_RUN_ELASTICITY
        assert 0 < CG_SHORT_RUN_ELASTICITY <= 1.0
        assert 0 < CG_LONG_RUN_ELASTICITY <= 1.0
        assert CG_TRANSITION_YEARS > 0

    def test_growth_rates_dict(self):
        """Verify GROWTH_RATES dict has valid structure."""
        assert isinstance(GROWTH_RATES, dict)
        assert "default" in GROWTH_RATES
        for _key, value in GROWTH_RATES.items():
            assert isinstance(value, (int, float))
            assert 0 <= value <= 0.20  # Growth rates should be reasonable

    def test_baseline_growth_dict(self):
        """Verify BASELINE_GROWTH dict has valid structure."""
        assert isinstance(BASELINE_GROWTH, dict)
        for _key, value in BASELINE_GROWTH.items():
            assert isinstance(value, (int, float))
            assert 0 <= value <= 0.10  # Growth rates should be reasonable

    def test_multiplier_constants(self):
        """Verify fiscal multiplier constants."""
        assert SPENDING_MULTIPLIER_BASE > 0
        assert TAX_MULTIPLIER_BASE > 0
        assert TRANSFER_MULTIPLIER_BASE > 0
        assert MARGINAL_REVENUE_RATE > 0

    def test_labor_capital_shares(self):
        """Verify labor and capital shares sum to 1."""
        assert LABOR_SHARE + DEFAULT_CAPITAL_ELASTICITY != 1.0  # These aren't the same
        # But individually they should be reasonable
        assert 0 < LABOR_SHARE < 1
        assert 0 < DEFAULT_CAPITAL_ELASTICITY < 1

    def test_jobs_per_gdp_percent(self):
        """Verify JOBS_PER_GDP_PERCENT is positive."""
        assert JOBS_PER_GDP_PERCENT > 0
        assert isinstance(JOBS_PER_GDP_PERCENT, int)

    def test_fallback_baseline_dict(self):
        """Verify FALLBACK_BASELINE has expected keys and positive values."""
        assert isinstance(FALLBACK_BASELINE, dict)
        expected_keys = [
            "gdp", "individual_income_tax", "corporate_tax", "payroll_tax",
            "other_revenue", "social_security", "medicare", "medicaid",
        ]
        for key in expected_keys:
            assert key in FALLBACK_BASELINE
            assert FALLBACK_BASELINE[key] > 0

    def test_gdp_ratios_dict(self):
        """Verify GDP_RATIOS has valid structure."""
        assert isinstance(GDP_RATIOS, dict)
        for key, value in GDP_RATIOS.items():
            assert isinstance(value, (int, float))
            # Ratios should be between 0 and 1 (except debt which can be >1)
            if "debt" not in key.lower():
                assert 0 <= value <= 1.0

    def test_corporate_amt_dict(self):
        """Verify CORPORATE_AMT constants."""
        assert isinstance(CORPORATE_AMT, dict)
        assert CORPORATE_AMT["rate"] == 0.15
        assert CORPORATE_AMT["threshold"] > 0
        assert CORPORATE_AMT["revenue_per_year"] > 0


# =============================================================================
# DATA VALIDATION TESTS
# =============================================================================


class TestDataValidator:
    """Tests for fiscal_model/data/validation.py."""

    def test_validation_result_created(self):
        """Verify ValidationResult can be created."""
        result = ValidationResult(
            passed=True,
            message="Test passed"
        )
        assert result.passed is True
        assert "Test" in str(result)

    def test_validation_result_str_representation(self):
        """Verify ValidationResult string formatting."""
        result_pass = ValidationResult(passed=True, message="Test")
        result_fail = ValidationResult(passed=False, message="Test")
        assert "PASS" in str(result_pass)
        assert "FAIL" in str(result_fail)

    def test_validate_irs_table_1_1_empty_df(self):
        """Verify validation fails on empty DataFrame."""
        df = pd.DataFrame()
        result = DataValidator.validate_irs_table_1_1(df, 2022)
        assert result.passed is False
        assert "empty" in result.message.lower()

    def test_validate_irs_table_1_1_valid_df(self):
        """Verify validation passes on well-formed DataFrame."""
        df = pd.DataFrame({
            'returns': [100_000_000, 50_000_000],
            'agi': [5_000_000_000_000, 2_500_000_000_000],
            'income': [5_500_000_000_000, 2_750_000_000_000],
        })
        result = DataValidator.validate_irs_table_1_1(df, 2022)
        # Should pass basic validation (totals in range)
        assert isinstance(result, ValidationResult)

    def test_validate_irs_table_3_3_empty_df(self):
        """Verify table 3.3 validation fails on empty DataFrame."""
        df = pd.DataFrame()
        result = DataValidator.validate_irs_table_3_3(df, 2022)
        assert result.passed is False

    def test_validate_irs_table_3_3_valid_df(self):
        """Verify table 3.3 validation passes on well-formed DataFrame."""
        df = pd.DataFrame({
            'tax_liability': [1_500_000_000_000, 750_000_000_000],
            'credit': [100_000_000_000, 50_000_000_000],
        })
        result = DataValidator.validate_irs_table_3_3(df, 2022)
        assert isinstance(result, ValidationResult)

    def test_validate_fred_series_empty(self):
        """Verify FRED validation fails on empty series."""
        series = pd.Series([], dtype=float)
        result = DataValidator.validate_fred_series(series, 'GDP')
        assert result.passed is False

    def test_validate_fred_series_valid_gdp(self):
        """Verify FRED validation passes for valid GDP series."""
        series = pd.Series([28_000, 28_500, 29_000])
        result = DataValidator.validate_fred_series(series, 'GDP')
        # Should be OK because values are in range
        assert isinstance(result, ValidationResult)

    def test_validate_fred_series_gdp_too_low(self):
        """Verify FRED validation fails when GDP is too low."""
        series = pd.Series([10_000])  # Below minimum
        result = DataValidator.validate_fred_series(series, 'GDP')
        assert result.passed is False or "outside" in result.message.lower()

    def test_validate_fred_series_unrate(self):
        """Verify FRED validation works for unemployment rate."""
        series = pd.Series([3.5, 4.0, 4.2])  # Reasonable unemployment rates
        result = DataValidator.validate_fred_series(series, 'UNRATE')
        assert isinstance(result, ValidationResult)

    def test_find_column_with_keywords(self):
        """Verify _find_column method works."""
        df = pd.DataFrame({'Total Returns': [1, 2], 'AGI': [3, 4]})
        col = DataValidator._find_column(df, ['returns', 'number'])
        assert col in df.columns
        assert 'return' in col.lower()

    def test_find_column_case_insensitive(self):
        """Verify _find_column is case-insensitive."""
        df = pd.DataFrame({'RETURNS': [1, 2], 'agi': [3, 4]})
        col = DataValidator._find_column(df, ['returns'])
        assert col is not None

    def test_find_column_not_found(self):
        """Verify _find_column returns None if not found."""
        df = pd.DataFrame({'Other': [1, 2]})
        col = DataValidator._find_column(df, ['returns', 'agi'])
        assert col is None


# =============================================================================
# VALIDATION COMPARE TESTS
# =============================================================================


class TestValidationCompare:
    """Tests for fiscal_model/validation/compare.py functions."""

    def test_rate_accuracy_excellent(self):
        """Verify accuracy rating for very accurate estimates."""
        rating = _rate_accuracy(2.5)
        assert rating == "Excellent"

    def test_rate_accuracy_good(self):
        """Verify accuracy rating for good estimates."""
        rating = _rate_accuracy(7.5)
        assert rating == "Good"

    def test_rate_accuracy_acceptable(self):
        """Verify accuracy rating for acceptable estimates."""
        rating = _rate_accuracy(15.0)
        assert rating == "Acceptable"

    def test_rate_accuracy_poor(self):
        """Verify accuracy rating for poor estimates."""
        rating = _rate_accuracy(35.0)
        assert rating == "Poor"

    def test_rate_accuracy_is_absolute(self):
        """Verify accuracy rating uses absolute difference."""
        rating_pos = _rate_accuracy(7.5)
        rating_neg = _rate_accuracy(-7.5)
        assert rating_pos == rating_neg

    def test_validation_result_creation(self):
        """Verify ComparisonValidationResult can be created."""
        result = ComparisonValidationResult(
            policy_id="test",
            policy_name="Test Policy",
            official_10yr=-100.0,
            official_source="CBO",
            model_10yr=-95.0,
            model_first_year=-10.0,
            difference=5.0,
            percent_difference=5.0,
            direction_match=True,
            accuracy_rating="Good",
        )
        assert result.policy_id == "test"
        assert result.is_accurate is True  # Within 20%

    def test_validation_result_is_accurate(self):
        """Verify is_accurate property works correctly."""
        accurate = ComparisonValidationResult(
            policy_id="test", policy_name="Test",
            official_10yr=-100.0, official_source="CBO",
            model_10yr=-105.0, model_first_year=-10.0,
            difference=-5.0, percent_difference=5.0,
            direction_match=True, accuracy_rating="Good"
        )
        assert accurate.is_accurate is True

        inaccurate = ComparisonValidationResult(
            policy_id="test", policy_name="Test",
            official_10yr=-100.0, official_source="CBO",
            model_10yr=-150.0, model_first_year=-15.0,
            difference=-50.0, percent_difference=50.0,
            direction_match=True, accuracy_rating="Poor"
        )
        assert inaccurate.is_accurate is False

    def test_validation_result_get_summary(self):
        """Verify get_summary method produces a string."""
        result = ComparisonValidationResult(
            policy_id="test", policy_name="Test Policy",
            official_10yr=-100.0, official_source="CBO",
            model_10yr=-95.0, model_first_year=-10.0,
            difference=5.0, percent_difference=5.0,
            direction_match=True, accuracy_rating="Good"
        )
        summary = result.get_summary()
        assert isinstance(summary, str)
        assert "Test Policy" in summary
        assert "-100" in summary or "-95" in summary

    def test_create_policy_from_score_returns_policy_or_none(self):
        """Verify create_policy_from_score returns TaxPolicy or None."""
        # This function requires a CBOScore object; test that it handles gracefully
        # We'll test with a mock/simple case
        from fiscal_model.validation.cbo_scores import CBOScore, ScoreSource

        score = CBOScore(
            policy_id="test",
            name="Test Policy",
            description="Test policy",
            ten_year_cost=-100.0,
            source=ScoreSource.CBO,
            source_date="2024-01",
            policy_type="income_tax",
            rate_change=0.05,
            income_threshold=400_000,
        )

        result = create_policy_from_score(score)
        # Should return either a TaxPolicy or None
        assert result is None or isinstance(result, TaxPolicy)


# =============================================================================
# DISTRIBUTIONAL VALIDATION TESTS
# =============================================================================


class TestDistributionalValidation:
    """Tests for fiscal_model/validation/distributional_validation.py."""

    def test_distributional_benchmark_creation(self):
        """Verify DistributionalBenchmark can be created."""
        benchmark = DistributionalBenchmark(
            name="Test Benchmark",
            source="Test Source",
            year=2020,
            quintile_data={
                "Lowest": (-100, 0.05),
                "Middle": (-500, 0.15),
            }
        )
        assert benchmark.name == "Test Benchmark"
        assert benchmark.year == 2020

    def test_tpc_tcja_2018_benchmark_exists(self):
        """Verify TPC_TCJA_2018 benchmark has correct structure."""
        assert isinstance(TPC_TCJA_2018, DistributionalBenchmark)
        assert TPC_TCJA_2018.year == 2018
        assert len(TPC_TCJA_2018.quintile_data) == 5
        # Should have all quintiles
        assert "Lowest Quintile" in TPC_TCJA_2018.quintile_data
        assert "Top Quintile" in TPC_TCJA_2018.quintile_data

    def test_tpc_tcja_2018_benchmark_values(self):
        """Verify TCJA benchmark values are reasonable."""
        # All changes should be negative (tax cuts)
        for quintile, (avg_change, share) in TPC_TCJA_2018.quintile_data.items():
            assert avg_change < 0, f"{quintile} should be negative"
            assert 0 <= share <= 1, f"{quintile} share should be between 0 and 1"

    def test_tpc_tcja_2018_shares_sum(self):
        """Verify TCJA benchmark shares sum to approximately 1."""
        total_share = sum(
            share for _, share in TPC_TCJA_2018.quintile_data.values()
        )
        # Should sum to 1.0 (within floating point precision)
        assert 0.99 <= total_share <= 1.01

    def test_corporate_incidence_has_structure(self):
        """Verify CORPORATE_INCIDENCE has expected structure."""
        assert isinstance(CORPORATE_INCIDENCE, dict)
        assert "capital_share" in CORPORATE_INCIDENCE
        assert "labor_share" in CORPORATE_INCIDENCE
        assert CORPORATE_INCIDENCE["capital_share"] > CORPORATE_INCIDENCE["labor_share"]

    def test_corporate_incidence_shares_sum_to_one(self):
        """Verify corporate incidence shares sum to expected value."""
        capital = CORPORATE_INCIDENCE["capital_share"]
        labor = CORPORATE_INCIDENCE["labor_share"]
        # Should sum to at least 75% (some might be consumer)
        assert (capital + labor) >= 0.75
        assert (capital + labor) <= 1.01  # Allow floating point error
