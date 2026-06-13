"""
Tests for the international corporate tax module (``fiscal_model/international.py``).

Covers the four structural provisions (GILTI reform, FDII repeal, Pillar Two,
UTPR), the component breakdown, behavioral offset, the preset factories, and
end-to-end scoring through ``FiscalPolicyScorer``.

Scoring uses ``use_real_data=False`` so the numbers are reproducible across
environments without external data files. The end-to-end ranges are deliberately
wider than the standalone-component checks because the scorer layers phase-in and
its generic behavioral offset on top of the module's static estimate — these are
reconstructions of published Treasury/JCT scores, not calibrated reference models.
"""

import pytest

from fiscal_model.international import (
    INTERNATIONAL_BASELINE,
    INTERNATIONAL_VALIDATION_SCENARIOS,
    InternationalReformType,
    InternationalTaxPolicy,
    create_biden_full_international,
    create_biden_gilti_reform,
    create_fdii_repeal,
    create_pillar_two_adoption,
    create_pillar_two_with_utpr,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer


@pytest.fixture
def scorer():
    return FiscalPolicyScorer(use_real_data=False)


class TestFactoryTypes:
    """Each preset factory returns a correctly-typed, correctly-flagged policy."""

    def test_gilti_factory(self):
        p = create_biden_gilti_reform()
        assert isinstance(p, InternationalTaxPolicy)
        assert p.reform_type is InternationalReformType.GILTI_REFORM
        assert p.policy_type is PolicyType.CORPORATE_TAX
        assert p.gilti_country_by_country is True
        assert p.gilti_eliminate_qbai is True
        assert p.gilti_new_rate == 0.21

    def test_fdii_factory(self):
        p = create_fdii_repeal()
        assert p.reform_type is InternationalReformType.FDII_REPEAL
        assert p.fdii_repeal is True

    def test_pillar_two_factory(self):
        p = create_pillar_two_adoption()
        assert p.pillar_two_adopt is True
        assert p.pillar_two_rate == 0.15
        assert p.adopt_utpr is False

    def test_full_package_factory(self):
        p = create_biden_full_international()
        assert p.gilti_country_by_country is True
        assert p.fdii_repeal is True
        assert p.adopt_utpr is True

    def test_post_init_forces_corporate_type(self):
        # Even a bare CUSTOM policy is coerced to CORPORATE_TAX in __post_init__.
        p = InternationalTaxPolicy(name="x", description="x")
        assert p.policy_type is PolicyType.CORPORATE_TAX


class TestGILTIReform:
    def test_no_change_is_zero(self):
        # No GILTI levers pulled -> no GILTI revenue.
        p = InternationalTaxPolicy(name="noop", description="noop")
        assert p._estimate_gilti_reform() == 0.0

    def test_country_by_country_raises_revenue(self):
        p = create_biden_gilti_reform()
        assert p._estimate_gilti_reform() > 0

    def test_eliminating_qbai_adds_revenue(self):
        without_qbai = InternationalTaxPolicy(
            name="a", description="a",
            gilti_country_by_country=True, gilti_new_rate=0.21,
            gilti_eliminate_qbai=False,
        )
        with_qbai = InternationalTaxPolicy(
            name="b", description="b",
            gilti_country_by_country=True, gilti_new_rate=0.21,
            gilti_eliminate_qbai=True,
        )
        assert with_qbai._estimate_gilti_reform() > without_qbai._estimate_gilti_reform()

    def test_ftc_offset_only_applies_to_increases(self):
        # A GILTI rate *cut* (negative delta) is not damped by the FTC offset.
        cut = InternationalTaxPolicy(
            name="cut", description="cut", gilti_new_rate=0.05,
        )
        # new_rate 0.05 < baseline 0.105 -> negative (revenue loss)
        assert cut._estimate_gilti_reform() < 0


class TestFDIIReform:
    def test_repeal_recovers_full_expenditure(self):
        p = create_fdii_repeal()
        assert p._estimate_fdii_reform() == INTERNATIONAL_BASELINE["fdii_cost_billions"]

    def test_no_fdii_change_is_zero(self):
        p = InternationalTaxPolicy(name="noop", description="noop")
        assert p._estimate_fdii_reform() == 0.0

    def test_higher_fdii_rate_raises_revenue(self):
        # Raising the effective FDII rate above current law raises revenue.
        p = InternationalTaxPolicy(name="r", description="r", fdii_new_rate=0.18)
        assert p._estimate_fdii_reform() > 0


class TestPillarTwoAndUTPR:
    def test_pillar_two_requires_adopt_flag(self):
        off = InternationalTaxPolicy(name="off", description="off")
        on = create_pillar_two_adoption()
        assert off._estimate_pillar_two() == 0.0
        assert on._estimate_pillar_two() > 0

    def test_utpr_requires_adopt_flag(self):
        off = create_pillar_two_adoption()  # adopt_utpr defaults False
        on = create_pillar_two_with_utpr()
        assert off._estimate_utpr() == 0.0
        assert on._estimate_utpr() > 0


class TestBehavioralAndBreakdown:
    def test_offset_is_positive_and_smaller_than_static(self):
        p = create_biden_full_international()
        static = p.estimate_static_revenue_effect(0)
        offset = p.estimate_behavioral_offset(static)
        assert 0 < offset < abs(static)

    def test_breakdown_keys_and_sum(self):
        p = create_biden_full_international()
        bd = p.get_component_breakdown()
        assert set(bd) >= {
            "gilti_reform", "fdii_reform", "pillar_two", "utpr",
            "static_total", "behavioral_offset", "net_effect",
        }
        # static_total is the sum of the four provisions.
        assert bd["static_total"] == pytest.approx(
            bd["gilti_reform"] + bd["fdii_reform"] + bd["pillar_two"] + bd["utpr"]
        )
        # net_effect = static minus behavioral offset.
        assert bd["net_effect"] == pytest.approx(
            bd["static_total"] - bd["behavioral_offset"]
        )

    def test_full_package_exceeds_single_provision(self):
        full = create_biden_full_international().estimate_static_revenue_effect(0)
        gilti_only = create_biden_gilti_reform().estimate_static_revenue_effect(0)
        assert full > gilti_only


class TestScorerIntegration:
    """End-to-end through FiscalPolicyScorer (reconstruction of Treasury scores)."""

    def test_gilti_reduces_deficit(self, scorer):
        r = scorer.score_policy(create_biden_gilti_reform())
        # Revenue raiser -> reduces the deficit (negative cost).
        assert r.total_10_year_cost < 0

    def test_gilti_in_treasury_ballpark(self, scorer):
        # Treasury FY2025 scores Biden GILTI reform at ~-$280B/10yr. The generic
        # scorer reconstruction lands near -$230B; assert a directional ballpark
        # rather than a tight calibration band.
        r = scorer.score_policy(create_biden_gilti_reform())
        assert -360 <= r.total_10_year_cost <= -150

    def test_full_package_raises_more_than_gilti(self, scorer):
        full = scorer.score_policy(create_biden_full_international()).total_10_year_cost
        gilti = scorer.score_policy(create_biden_gilti_reform()).total_10_year_cost
        assert full < gilti  # more negative = more revenue


class TestValidationScenarios:
    def test_scenarios_resolve_to_real_factories(self):
        import fiscal_model.international as intl
        for key, spec in INTERNATIONAL_VALIDATION_SCENARIOS.items():
            factory = getattr(intl, spec["factory"], None)
            assert callable(factory), f"{key}: missing factory {spec['factory']}"
            policy = factory()
            assert isinstance(policy, InternationalTaxPolicy)
            assert spec["expected_10yr"] < 0  # all are revenue raisers
