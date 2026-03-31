"""
Tests for fiscal_model/uncertainty.py — UncertaintyAnalysis.

Covers:
- Initialization
- calculate_ranges (policy uncertainty) returns correct-length arrays
- Uncertainty grows over time
- Tax vs spending uncertainty factors
- Dynamic scoring increases uncertainty
- Low < central, high > central for positive values
- Asymmetric ranges
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy, TransferPolicy
from fiscal_model.uncertainty import UncertaintyAnalysis, UncertaintyFactors

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def analyzer():
    return UncertaintyAnalysis()


@pytest.fixture
def custom_analyzer():
    return UncertaintyAnalysis(factors=UncertaintyFactors(behavioral_response_cv=0.60))


@pytest.fixture
def tax_policy():
    return TaxPolicy(
        name="Test Tax",
        description="Test tax increase",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=200_000,
    )


@pytest.fixture
def spending_policy():
    return SpendingPolicy(
        name="Test Spending",
        description="Test spending program",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=50.0,
    )


@pytest.fixture
def transfer_policy():
    return TransferPolicy(
        name="Test Transfer",
        description="Test transfer program",
        policy_type=PolicyType.OTHER_TRANSFER,
        benefit_change_dollars=500.0,
        new_beneficiaries_millions=10.0,
    )


@pytest.fixture
def positive_estimate():
    """A 10-year central estimate with positive values (deficit increase)."""
    return np.array([50.0, 52.0, 54.0, 56.0, 58.0, 60.0, 62.0, 64.0, 66.0, 68.0])


@pytest.fixture
def negative_estimate():
    """A 10-year central estimate with negative values (revenue gain)."""
    return np.array([-25.0] * 10)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestUncertaintyAnalysisInit:

    def test_default_init(self, analyzer):
        assert analyzer.factors is not None
        assert analyzer.factors.gdp_growth_std == 0.015

    def test_custom_factors(self, custom_analyzer):
        assert custom_analyzer.factors.behavioral_response_cv == 0.60

    def test_correlation_matrix_shape(self, analyzer):
        assert analyzer.econ_correlation.shape == (4, 4)

    def test_correlation_matrix_symmetric(self, analyzer):
        np.testing.assert_array_almost_equal(
            analyzer.econ_correlation, analyzer.econ_correlation.T
        )


# =============================================================================
# CALCULATE POLICY UNCERTAINTY
# =============================================================================

class TestCalculatePolicyUncertainty:

    def test_returns_correct_length(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        assert len(result["central"]) == 10
        assert len(result["low"]) == 10
        assert len(result["high"]) == 10

    def test_uncertainty_grows_over_time(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        spread = result["high"] - result["low"]
        # Later years should have wider spread than earlier years
        assert spread[-1] > spread[0], "Uncertainty should grow over time"

    def test_tax_higher_uncertainty_than_spending(
        self, analyzer, tax_policy, spending_policy, positive_estimate
    ):
        tax_result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        spend_result = analyzer.calculate_policy_uncertainty(spending_policy, positive_estimate)

        tax_spread = np.mean(tax_result["high"] - tax_result["low"])
        spend_spread = np.mean(spend_result["high"] - spend_result["low"])

        assert tax_spread > spend_spread, (
            "Tax policy should have wider uncertainty than spending"
        )

    def test_low_less_than_central_positive(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        assert np.all(result["low"] < result["central"])

    def test_high_greater_than_central_positive(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        assert np.all(result["high"] > result["central"])

    def test_central_unchanged(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        np.testing.assert_array_equal(result["central"], positive_estimate)

    def test_percentile_keys_present(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        for key in ("10th", "25th", "75th", "90th", "low", "high", "central"):
            assert key in result

    def test_percentile_ordering(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        # For positive central: 10th < 25th < central < 75th < 90th
        assert np.all(result["10th"] < result["25th"])
        assert np.all(result["25th"] < result["central"])
        assert np.all(result["central"] < result["75th"])
        assert np.all(result["75th"] < result["90th"])

    def test_transfer_policy_uncertainty(self, analyzer, transfer_policy, positive_estimate):
        result = analyzer.calculate_policy_uncertainty(transfer_policy, positive_estimate)
        assert len(result["central"]) == 10
        spread = result["high"] - result["low"]
        assert spread[-1] > spread[0]

    def test_negative_estimate_uncertainty(self, analyzer, tax_policy, negative_estimate):
        result = analyzer.calculate_policy_uncertainty(tax_policy, negative_estimate)
        # For negative central values, low should be more negative (further from zero)
        assert np.all(result["low"] < result["central"])
        assert np.all(result["high"] > result["central"])


# =============================================================================
# ASYMMETRIC RANGES
# =============================================================================

class TestAsymmetricRanges:

    def test_high_side_vs_low_side_magnitude(self, analyzer, tax_policy, positive_estimate):
        """
        For positive estimates the absolute distance from central to high
        should equal the distance from central to low (symmetric in this
        implementation), but both should be > 0.
        """
        result = analyzer.calculate_policy_uncertainty(tax_policy, positive_estimate)
        high_dist = np.abs(result["high"] - result["central"])
        low_dist = np.abs(result["central"] - result["low"])
        # Both distances should be positive
        assert np.all(high_dist > 0)
        assert np.all(low_dist > 0)


# =============================================================================
# MONTE CARLO
# =============================================================================

class TestMonteCarlo:

    def test_monte_carlo_returns_expected_keys(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.monte_carlo_simulation(
            tax_policy, positive_estimate, n_simulations=100
        )
        for key in ("mean", "median", "std", "p10", "p25", "p75", "p90", "simulations"):
            assert key in result

    def test_simulations_shape(self, analyzer, tax_policy, positive_estimate):
        n_sims = 200
        result = analyzer.monte_carlo_simulation(
            tax_policy, positive_estimate, n_simulations=n_sims
        )
        assert result["simulations"].shape == (n_sims, 10)

    def test_std_positive(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.monte_carlo_simulation(
            tax_policy, positive_estimate, n_simulations=200
        )
        assert np.all(result["std"] > 0)


# =============================================================================
# SENSITIVITY ANALYSIS
# =============================================================================

class TestSensitivityAnalysis:

    def test_sensitivity_returns_result(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.sensitivity_analysis(
            tax_policy, positive_estimate, parameter="gdp_growth"
        )
        assert result.parameter_name == "gdp_growth"
        assert len(result.parameter_values) == 11
        assert len(result.deficit_effects) == 11

    def test_sensitivity_elasticity_finite(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.sensitivity_analysis(
            tax_policy, positive_estimate, parameter="behavioral_elasticity"
        )
        assert np.isfinite(result.elasticity)

    def test_sensitivity_range_property(self, analyzer, tax_policy, positive_estimate):
        result = analyzer.sensitivity_analysis(
            tax_policy, positive_estimate, parameter="interest_rate"
        )
        lo, hi = result.range
        assert lo <= hi


# =============================================================================
# FORMAT SUMMARY
# =============================================================================

class TestFormatSummary:

    def test_format_uncertainty_summary(self, analyzer):
        mock_dict = {
            "total_deficit": {
                "central": np.array([100.0] * 10),
                "low": np.array([90.0] * 10),
                "high": np.array([110.0] * 10),
            }
        }
        text = analyzer.format_uncertainty_summary(mock_dict)
        assert "Uncertainty Analysis Summary" in text
        assert "Central estimate" in text
