"""
Tests for the IRS enforcement revenue module (``fiscal_model/enforcement.py``).

Covers the diminishing-returns ROI model, the total-vs-annual spending
conversion, the deterrence (voluntary compliance) boost, the behavioral offset,
the ROI summary, and end-to-end scoring through ``FiscalPolicyScorer``.

Scoring uses ``use_real_data=False`` for reproducibility. The IRA preset is a
calibrated reconstruction of CBO's ~-$200B/10yr score; the end-to-end band is
kept modestly wide because the scorer adds phase-in on top of the static model.
"""

import pytest

from fiscal_model.enforcement import (
    ENFORCEMENT_BASELINE,
    ENFORCEMENT_VALIDATION_SCENARIOS,
    IRSEnforcementPolicy,
    create_double_enforcement,
    create_high_income_enforcement,
    create_ira_enforcement,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer


@pytest.fixture
def scorer():
    return FiscalPolicyScorer(use_real_data=False)


def _policy(**kwargs) -> IRSEnforcementPolicy:
    """Helper to build an enforcement policy with the required base fields."""
    kwargs.setdefault("name", "Test Enforcement")
    kwargs.setdefault("description", "test")
    kwargs.setdefault("policy_type", PolicyType.INCOME_TAX)
    return IRSEnforcementPolicy(**kwargs)


class TestFactories:
    def test_factory_types(self):
        for factory in (
            create_ira_enforcement,
            create_double_enforcement,
            create_high_income_enforcement,
        ):
            p = factory()
            assert isinstance(p, IRSEnforcementPolicy)
            assert p.policy_type is PolicyType.INCOME_TAX

    def test_ira_uses_total_spending(self):
        p = create_ira_enforcement()
        assert p.total_10yr_spending_billions == 80.0


class TestSpendingConversion:
    def test_total_converts_to_annual(self):
        # $80B over the default 10-year window -> $8B/year.
        p = _policy(total_10yr_spending_billions=80.0, duration_years=10)
        assert p.annual_enforcement_spending_billions == pytest.approx(8.0)

    def test_explicit_annual_is_preserved(self):
        p = _policy(annual_enforcement_spending_billions=5.0)
        assert p.annual_enforcement_spending_billions == 5.0

    def test_zero_spending_yields_zero_revenue(self):
        p = _policy(annual_enforcement_spending_billions=0.0)
        assert p.estimate_static_revenue_effect(0) == 0.0


class TestROIModel:
    def test_net_revenue_positive_for_ira(self):
        p = create_ira_enforcement()
        assert p.estimate_static_revenue_effect(0) > 0

    def test_diminishing_returns_lower_marginal_roi(self):
        # Effective ROI per dollar should fall as the program scales, because
        # each additional $1B chunk earns diminishing_returns_factor of the prior.
        small = _policy(annual_enforcement_spending_billions=2.0)
        large = _policy(annual_enforcement_spending_billions=20.0)
        assert small.get_roi_summary()["effective_roi"] > large.get_roi_summary()["effective_roi"]

    def test_compliance_boost_increases_revenue(self):
        without = _policy(
            annual_enforcement_spending_billions=8.0, voluntary_compliance_boost=0.0,
        )
        with_boost = _policy(
            annual_enforcement_spending_billions=8.0, voluntary_compliance_boost=0.15,
        )
        assert with_boost.estimate_static_revenue_effect(0) > without.estimate_static_revenue_effect(0)

    def test_higher_base_roi_raises_revenue(self):
        low = _policy(annual_enforcement_spending_billions=5.0, base_roi_multiplier=4.0)
        high = _policy(annual_enforcement_spending_billions=5.0, base_roi_multiplier=7.0)
        assert high.estimate_static_revenue_effect(0) > low.estimate_static_revenue_effect(0)


class TestBehavioralOffset:
    def test_offset_uses_avoidance_rate(self):
        p = create_ira_enforcement()
        static = p.estimate_static_revenue_effect(0)
        offset = p.estimate_behavioral_offset(static)
        assert offset == pytest.approx(
            abs(static) * ENFORCEMENT_BASELINE["avoidance_response_rate"]
        )

    def test_offset_is_small(self):
        # Enforcement doesn't change rates, so the behavioral offset is minimal.
        p = create_ira_enforcement()
        static = p.estimate_static_revenue_effect(0)
        assert p.estimate_behavioral_offset(static) < 0.1 * abs(static)


class TestROISummary:
    def test_summary_keys_and_consistency(self):
        p = create_ira_enforcement()
        s = p.get_roi_summary()
        assert set(s) >= {
            "annual_spending", "gross_annual_revenue",
            "net_annual_revenue", "effective_roi",
        }
        # net = gross - spending, and effective_roi = gross / spending.
        assert s["net_annual_revenue"] == pytest.approx(
            s["gross_annual_revenue"] - s["annual_spending"]
        )
        assert s["effective_roi"] == pytest.approx(
            s["gross_annual_revenue"] / s["annual_spending"]
        )


class TestScorerIntegration:
    def test_ira_reduces_deficit(self, scorer):
        r = scorer.score_policy(create_ira_enforcement())
        assert r.total_10_year_cost < 0

    def test_ira_near_cbo_score(self, scorer):
        # CBO scores IRA enforcement at ~-$200B/10yr; the reconstruction lands
        # near -$190B. Keep a modest band around the calibration target.
        r = scorer.score_policy(create_ira_enforcement())
        assert -240 <= r.total_10_year_cost <= -150


class TestValidationScenarios:
    def test_scenarios_resolve_to_real_factories(self):
        import fiscal_model.enforcement as enf
        for key, spec in ENFORCEMENT_VALIDATION_SCENARIOS.items():
            factory = getattr(enf, spec["factory"], None)
            assert callable(factory), f"{key}: missing factory {spec['factory']}"
            assert isinstance(factory(), IRSEnforcementPolicy)
            assert spec["expected_10yr"] < 0
