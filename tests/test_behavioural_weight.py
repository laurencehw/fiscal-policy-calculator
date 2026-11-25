"""Lane SSG: the bracket-specific behavioural offset.

``planning/lanes/SSG_bracket_behavioural_offset.md`` section 4 registers what
these tests check: the weight reads no scorecard target and types in no rate,
a $0 floor gives ``a = 1``, the weight rises from the all-brackets case to the
$400K case, and every policy outside a plain income-tax rate change keeps 0.5.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from fiscal_model import behavioral_weight
from fiscal_model.behavioral_weight import LEGACY_WEIGHT, ssg_terms, ssg_weight
from fiscal_model.data.irs_soi import FILING_STATUSES
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.ui.formatting import format_money

SOI_YEAR = 2023


def _uniform(floor: float) -> dict[str, float]:
    return {status: floor for status in FILING_STATUSES}


def _key(floors: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted(floors.items()))


def test_a_zero_floor_gives_a_equal_to_one():
    terms = ssg_terms(_key(_uniform(0.0)), "taxable_income", SOI_YEAR)
    assert terms is not None
    tau, a = terms
    assert a == pytest.approx(1.0)
    assert 0.0 < tau < 0.5


def test_the_weight_rises_from_all_brackets_to_the_top():
    broad = ssg_weight(_uniform(0.0), "taxable_income", SOI_YEAR)
    top = ssg_weight(_uniform(400_000.0), "taxable_income", SOI_YEAR)
    assert broad is not None and top is not None
    assert broad < LEGACY_WEIGHT < top
    # The pre-registered figures (lane doc section 3).
    assert broad == pytest.approx(0.345, abs=0.001)
    assert top == pytest.approx(1.385, abs=0.001)


def test_the_module_reads_no_target_and_types_no_rate():
    source = inspect.getsource(behavioral_weight)
    for forbidden in ("cbo_scores", "preregistered", "CBO_SCORE_MAP", "official_10yr", "target"):
        assert forbidden not in source.split('"""', 2)[-1], forbidden
    tree = ast.parse(source)
    floats = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    }
    # 0.5 is the legacy weight it falls back to; 0.0, 1.0 and 1e9 are units.
    assert floats <= {0.0, 0.5, 1.0, 1e9}, floats


def _tax(**kwargs) -> TaxPolicy:
    base = dict(
        name="t",
        description="t",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=400_000,
    )
    base.update(kwargs)
    return TaxPolicy(**base)


def test_a_plain_income_tax_rate_change_uses_the_ssg_weight():
    assert _tax().behavioral_erosion_weight() == pytest.approx(1.385, abs=0.001)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rate_change": 0.0},
        {"policy_type": PolicyType.PAYROLL_TAX},
    ],
)
def test_everything_else_keeps_the_legacy_weight(kwargs):
    assert _tax(**kwargs).behavioral_erosion_weight() == LEGACY_WEIGHT


def test_a_subclass_keeps_the_legacy_weight():
    from fiscal_model.policies import CapitalGainsPolicy

    policy = CapitalGainsPolicy(
        name="cg",
        description="cg",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=0.05,
        affected_income_threshold=1_000_000,
    )
    assert TaxPolicy.behavioral_erosion_weight(policy) == LEGACY_WEIGHT


def test_the_offset_is_linear_in_the_weight():
    policy = _tax()
    w = policy.behavioral_erosion_weight()
    assert policy.estimate_behavioral_offset(-100.0) == pytest.approx(-100.0 * 0.25 * w)


#: Decision 6: each moved preset names the figure it printed with 0.5.
MOVED = {
    "Top Rate to 39.6% (Biden FY2025)": -309.8,
    "Middle Class Tax Cut": 1473.2,
}


@pytest.mark.parametrize(("label", "before"), sorted(MOVED.items()))
def test_a_moved_preset_carries_the_caption(label, before):
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for
    from fiscal_model.ui.tabs.results_summary import behavioural_weight_caption

    matches = [name for name in PRESET_POLICIES if name.startswith(label.split(" (")[0])]
    assert matches, label
    name = matches[0]
    policy, use_real = _build_preset_policy(name, PRESET_POLICIES[name])
    result = _scorer_for(policy, use_real).score_policy(policy, dynamic=False)
    caption = behavioural_weight_caption(policy, result)
    assert "Saez, Slemrod and Giertz" in caption
    assert format_money(before, escape=True) in caption
    assert format_money(float(result.total_10_year_cost), escape=True) in caption


def test_the_caption_is_silent_on_the_legacy_weight():
    from fiscal_model.ui.tabs.results_summary import behavioural_weight_caption

    policy = _tax(policy_type=PolicyType.PAYROLL_TAX)
    assert behavioural_weight_caption(policy, object()) == ""
