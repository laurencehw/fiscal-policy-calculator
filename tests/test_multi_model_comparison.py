"""
Tests for multi-model comparison system.

Validates that:
- All scoring models implement the BaseScoringModel interface
- compare_models produces consistent, comparable results
- ModelComparison provides useful divergence analysis
"""

import numpy as np
import pytest

from fiscal_model.models.base import ModelComparison, ModelResult
from fiscal_model.models.scoring_models import (
    CBOConventionalModel,
    DynamicScoringModel,
    compare_models,
)
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.tcja import create_tcja_extension


@pytest.fixture
def tax_increase():
    return TaxPolicy(
        name="Test Tax Increase",
        description="2.6pp on $400K+",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.026,
        affected_income_threshold=400_000,
        affected_taxpayers_millions=1.8,
        avg_taxable_income_in_bracket=1_200_000,
    )


@pytest.fixture
def cbo_model():
    return CBOConventionalModel(use_real_data=False)


@pytest.fixture
def dynamic_model():
    return DynamicScoringModel(use_real_data=False)


# =============================================================================
# BaseScoringModel interface
# =============================================================================

class TestBaseScoringModelInterface:

    def test_cbo_model_has_name(self, cbo_model):
        assert isinstance(cbo_model.name, str)
        assert len(cbo_model.name) > 0

    def test_cbo_model_has_methodology(self, cbo_model):
        assert isinstance(cbo_model.methodology, str)

    def test_cbo_model_has_assumptions(self, cbo_model):
        assumptions = cbo_model.get_assumptions()
        assert isinstance(assumptions, dict)
        assert "eti" in assumptions

    def test_dynamic_model_has_name(self, dynamic_model):
        assert isinstance(dynamic_model.name, str)

    def test_dynamic_model_assumptions_include_multipliers(self, dynamic_model):
        assumptions = dynamic_model.get_assumptions()
        assert "spending_multiplier" in assumptions
        assert "tax_multiplier" in assumptions


# =============================================================================
# ModelResult
# =============================================================================

class TestModelResult:

    def test_cbo_score_returns_model_result(self, cbo_model, tax_increase):
        result = cbo_model.score(tax_increase)
        assert isinstance(result, ModelResult)

    def test_result_has_ten_year_cost(self, cbo_model, tax_increase):
        result = cbo_model.score(tax_increase)
        assert isinstance(result.ten_year_cost, (int, float, np.floating))

    def test_result_has_annual_effects(self, cbo_model, tax_increase):
        result = cbo_model.score(tax_increase)
        assert len(result.annual_effects) == 10

    def test_tax_increase_reduces_deficit(self, cbo_model, tax_increase):
        result = cbo_model.score(tax_increase)
        assert result.ten_year_cost < 0, "Tax increase should reduce deficit"

    def test_dynamic_includes_gdp_effect(self, dynamic_model, tax_increase):
        result = dynamic_model.score(tax_increase)
        # Dynamic should have non-zero GDP effect
        assert result.gdp_effect_pct != 0.0

    def test_uncertainty_range(self, cbo_model, tax_increase):
        result = cbo_model.score(tax_increase)
        assert result.low_estimate <= result.ten_year_cost <= result.high_estimate or \
               result.high_estimate <= result.ten_year_cost <= result.low_estimate


# =============================================================================
# compare_models
# =============================================================================

class TestCompareModels:

    def test_compare_returns_model_comparison(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        assert isinstance(comparison, ModelComparison)

    def test_compare_has_two_models_by_default(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        assert len(comparison.results) == 2

    def test_compare_models_agree_on_direction(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        signs = [r.ten_year_cost > 0 for r in comparison.results]
        assert len(set(signs)) == 1, "All models should agree on direction"

    def test_dynamic_costs_less_than_conventional_for_tax_increase(self, tax_increase):
        """Dynamic scoring should show less deficit reduction (GDP growth offsets revenue)."""
        comparison = compare_models(tax_increase, use_real_data=False)
        cbo = next(r for r in comparison.results if "Conventional" in r.model_name)
        dyn = next(r for r in comparison.results if "Dynamic" in r.model_name)
        # For a tax increase: conventional shows larger deficit reduction
        # Dynamic shows less reduction (GDP drag reduces revenue feedback)
        # Both are negative; dynamic should be closer to zero
        assert abs(dyn.ten_year_cost) < abs(cbo.ten_year_cost), (
            f"Dynamic ({dyn.ten_year_cost:.0f}B) should show less deficit "
            f"reduction than conventional ({cbo.ten_year_cost:.0f}B)"
        )

    def test_compare_with_custom_models(self, tax_increase):
        models = [CBOConventionalModel(use_real_data=False)]
        comparison = compare_models(tax_increase, models=models, use_real_data=False)
        assert len(comparison.results) == 1


# =============================================================================
# ModelComparison
# =============================================================================

class TestModelComparison:

    def test_spread_is_positive(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        assert comparison.spread >= 0

    def test_consensus_estimate(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        avg = sum(r.ten_year_cost for r in comparison.results) / len(comparison.results)
        assert comparison.consensus_estimate == pytest.approx(avg)

    def test_to_dataframe(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        df = comparison.to_dataframe()
        assert len(df) == 2
        assert "Model" in df.columns
        assert "10-Year Cost ($B)" in df.columns

    def test_explain_divergence(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        explanation = comparison.explain_divergence()
        assert "diverge" in explanation.lower()

    def test_model_names(self, tax_increase):
        comparison = compare_models(tax_increase, use_real_data=False)
        names = comparison.model_names
        assert len(names) == 2
        assert all(isinstance(n, str) for n in names)


# =============================================================================
# TCJA integration test
# =============================================================================

class TestTCJAComparison:
    """Verify multi-model comparison works for a real policy."""

    def test_tcja_comparison_runs(self):
        policy = create_tcja_extension(extend_all=True)
        comparison = compare_models(policy, use_real_data=False)
        assert len(comparison.results) == 2
        # Both should show TCJA costs money
        for r in comparison.results:
            assert r.ten_year_cost > 0, f"{r.model_name} should show positive cost"
