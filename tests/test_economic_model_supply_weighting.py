"""R9: EconomicModel's labour-supply channel is weighted by the share it reaches.

See ``planning/lanes/R9_economic_model_supply_weighting.md``.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from fiscal_model import FiscalPolicyScorer, PolicyType, TaxPolicy
from fiscal_model.baseline import APP_DEFAULT_START_YEAR
from fiscal_model.data.irs_soi import IRSSOIData
from fiscal_model.economics import (
    AFFECTED_SHARE_SOI_YEAR,
    EconomicModel,
    labor_supply_affected_share,
)


def _tax(rate: float, threshold: float, policy_type=PolicyType.INCOME_TAX) -> TaxPolicy:
    return TaxPolicy(
        name="t",
        description="t",
        policy_type=policy_type,
        rate_change=rate,
        affected_income_threshold=threshold,
        start_year=APP_DEFAULT_START_YEAR,
    )


def test_the_share_is_soi_agi_above_the_threshold_over_all_agi():
    soi = IRSSOIData()
    total = soi.get_filers_by_bracket(AFFECTED_SHARE_SOI_YEAR, 0)["total_agi_billions"]
    above = soi.get_filers_by_bracket(AFFECTED_SHARE_SOI_YEAR, 400_000)["total_agi_billions"]
    assert labor_supply_affected_share(_tax(0.026, 400_000)) == pytest.approx(above / total)
    assert labor_supply_affected_share(_tax(0.026, 400_000)) == pytest.approx(0.3133, abs=1e-4)


def test_the_share_falls_with_the_threshold_and_is_one_at_zero():
    shares = [labor_supply_affected_share(_tax(0.01, t)) for t in (0, 50_000, 400_000, 1_000_000, 2_000_000)]
    assert shares[0] == 1.0
    assert all(a > b for a, b in pairwise(shares))


@pytest.mark.parametrize(
    "policy_type",
    [PolicyType.CORPORATE_TAX, PolicyType.CAPITAL_GAINS_TAX, PolicyType.ESTATE_TAX],
)
def test_capital_side_rates_have_no_labour_margin(policy_type):
    assert labor_supply_affected_share(_tax(0.07, 0, policy_type)) == 0.0


def test_other_types_keep_the_economy_wide_weight():
    assert labor_supply_affected_share(_tax(0.01, 400_000, PolicyType.EXCISE_TAX)) == 1.0


def test_hours_scale_by_the_share():
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    model = EconomicModel(scorer.baseline)
    policy = _tax(0.026, 400_000)
    effects = model.calculate_effects(policy, np.zeros(len(scorer.baseline.years)))
    expected = -0.026 * model.params["labor_supply_elasticity"] * 0.3133 * 100
    assert effects.hours_worked_change == pytest.approx(np.full(10, expected), abs=1e-3)


def test_the_reference_policy_lands_on_its_preregistered_figures():
    """+2.6pp above $400K: final -$86.1B -> -$206.4B, feedback -$216.1B -> -$95.9B."""
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    result = scorer.score_policy(_tax(0.026, 400_000), dynamic=True)
    assert float(np.sum(result.final_deficit_effect)) == pytest.approx(-206.36, abs=0.1)
    assert float(np.sum(result.dynamic_effects.revenue_feedback)) == pytest.approx(-95.87, abs=0.1)
    assert float(np.sum(result.static_deficit_effect)) == pytest.approx(-345.41, abs=0.1)


def test_a_zero_threshold_rate_change_is_unweighted():
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    model = EconomicModel(scorer.baseline)
    effects = model.calculate_effects(_tax(-0.05, 0), np.zeros(10))
    expected = 0.05 * model.params["labor_supply_elasticity"] * 100
    assert effects.hours_worked_change == pytest.approx(np.full(10, expected))
