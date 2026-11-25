"""Lane SUPPLY: the corporate capital channel in the dynamic view.

``planning/lanes/SUPPLY_corporate_capital_channel.md`` section 4.
"""

from __future__ import annotations

import ast
import inspect

import numpy as np
import pytest

from fiscal_model import cbo_tax_parameters as ctp
from fiscal_model import supply_channel
from fiscal_model.corporate import CorporateTaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer


@pytest.fixture(scope="module")
def baseline():
    from fiscal_model.baseline import APP_DEFAULT_START_YEAR

    return FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR).baseline


def _corp(rate_change: float, **kwargs) -> CorporateTaxPolicy:
    from fiscal_model.baseline import APP_DEFAULT_START_YEAR
    from fiscal_model.policies import PolicyType

    return CorporateTaxPolicy(
        name="c",
        description="c",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=rate_change,
        start_year=APP_DEFAULT_START_YEAR,
        **kwargs,
    )


def test_a_rise_lowers_output_a_cut_raises_it_and_zero_is_zero(baseline):
    rise = supply_channel.corporate_supply_path(_corp(0.07), baseline)
    cut = supply_channel.corporate_supply_path(_corp(-0.06), baseline)
    assert rise is not None and cut is not None
    assert np.all(rise < 0) and np.all(cut > 0)
    assert supply_channel.corporate_supply_path(_corp(0.0), baseline) is None


def test_the_preregistered_long_run_figure(baseline):
    """Section 3: the 28% preset reaches -0.29% of GDP by FY2035."""
    path = supply_channel.corporate_supply_path(_corp(0.07), baseline)
    assert path[-1] * 100 == pytest.approx(-0.288, abs=0.001)


#: The two earlier editions publish no ``tp_emtr_capital_housing`` row (only
#: its debt, equity and land-inclusive variants), so ``s`` cannot be read back
#: on the same definitions and the channel stays off there. Recorded in the
#: lane's outturn as not predicted.
VINTAGES_WITHOUT_HOUSING_EMTR = {"cbo_feb_2024", "cbo_jan_2025"}


@pytest.mark.parametrize("vintage", ctp.schedule_vintages())
def test_the_c_corp_share_is_a_share_in_every_year(vintage):
    years = supply_channel.emtr_years(vintage)
    if vintage in VINTAGES_WITHOUT_HOUSING_EMTR:
        assert years == ()
        return
    assert len(years) >= 10, years
    for year in years:
        share = supply_channel.c_corp_capital_share(vintage, year)
        assert share is not None and 0.0 < share < 1.0, (vintage, year, share)


def test_a_sunset_lets_output_decay_back(baseline):
    path = supply_channel.corporate_supply_path(_corp(0.07, duration_years=3), baseline)
    assert path[2] < 0
    assert abs(path[-1]) < abs(path[2])


def test_the_module_types_no_level_and_reads_no_target():
    source = inspect.getsource(supply_channel)
    body = source.split('"""', 2)[-1]
    for forbidden in ("cbo_scores", "preregistered", "CBO_SCORE_MAP", "official_10yr"):
        assert forbidden not in body, forbidden
    floats = {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    }
    assert floats <= {0.0, 1.0, 100.0}, floats


def test_only_a_corporate_rate_change_gets_a_supply_path(baseline):
    from fiscal_model.policies import PolicyType, TaxPolicy

    income = TaxPolicy(
        name="t",
        description="t",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )
    assert supply_channel.corporate_supply_path(income, baseline) is None


#: Section 3 predictions: (conventional, feedback, dynamic total), $B.
PREDICTED = {
    "Biden Corporate 28%": (-968.8, -248.8, -923.7),
    "Trump Corporate 15%": (1230.2, 235.5, 1251.3),
}


@pytest.mark.parametrize(("stem", "figures"), sorted(PREDICTED.items()))
def test_the_presets_land_on_their_preregistration(stem, figures):
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for
    from fiscal_model.dynamic_view import run_dynamic_view

    label = next(name for name in PRESET_POLICIES if stem in name)
    policy, use_real = _build_preset_policy(label, PRESET_POLICIES[label])
    result = _scorer_for(policy, use_real).score_policy(policy, dynamic=False)
    view, _ = run_dynamic_view(policy, result)
    conventional, feedback, total = figures
    assert view.conventional == pytest.approx(conventional, abs=1.0)
    assert view.feedback == pytest.approx(feedback, abs=1.0)
    assert view.dynamic_total == pytest.approx(total, abs=1.0)


def test_the_simple_multiplier_stays_demand_only(baseline):
    from fiscal_model.models.macro_adapter import MacroScenario, SimpleMultiplierAdapter

    plain = MacroScenario(name="p", description="p", receipts_change=np.full(10, 100.0))
    with_supply = MacroScenario(
        name="p",
        description="p",
        receipts_change=np.full(10, 100.0),
        supply_gdp_fraction=np.full(10, -0.01),
        baseline_nominal_gdp=np.full(10, 30_000.0),
    )
    adapter = SimpleMultiplierAdapter()
    np.testing.assert_allclose(
        adapter.run(plain).revenue_feedback_billions,
        adapter.run(with_supply).revenue_feedback_billions,
    )


def test_frbus_lite_adds_supply_feedback_at_its_marginal_rate():
    from fiscal_model.models.macro_adapter import FRBUSAdapterLite, MacroScenario

    adapter = FRBUSAdapterLite()
    plain = MacroScenario(name="p", description="p", receipts_change=np.full(10, 100.0))
    with_supply = MacroScenario(
        name="p",
        description="p",
        receipts_change=np.full(10, 100.0),
        supply_gdp_fraction=np.full(10, -0.01),
        baseline_nominal_gdp=np.full(10, 30_000.0),
    )
    gap = adapter.run(with_supply).revenue_feedback_billions - adapter.run(plain).revenue_feedback_billions
    np.testing.assert_allclose(gap, np.full(10, -300.0 * adapter.marginal_tax_rate))
    # Employment stays demand-only.
    np.testing.assert_allclose(
        adapter.run(with_supply).employment_change_millions,
        adapter.run(plain).employment_change_millions,
    )


def test_the_caption_computes_the_old_feedback_from_the_run():
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for
    from fiscal_model.dynamic_view import run_dynamic_view

    label = next(name for name in PRESET_POLICIES if "Biden Corporate 28%" in name)
    policy, use_real = _build_preset_policy(label, PRESET_POLICIES[label])
    result = _scorer_for(policy, use_real).score_policy(policy, dynamic=False)
    _, macro = run_dynamic_view(policy, result)
    caption = supply_channel.supply_feedback_caption(macro)
    assert caption is not None
    # Supply part, demand-only feedback and the total, as pre-registered.
    assert "-$162.2B" in caption
    assert "-$86.6B" in caption
    assert "-$248.8B" in caption


def test_no_caption_without_a_supply_channel():
    from fiscal_model.models.macro_adapter import FRBUSAdapterLite, MacroScenario

    plain = MacroScenario(name="p", description="p", receipts_change=np.full(10, 100.0))
    assert supply_channel.supply_feedback_caption(FRBUSAdapterLite().run(plain)) is None
