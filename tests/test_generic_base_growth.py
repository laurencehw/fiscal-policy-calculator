"""The generic income-tax base is priced in the years being scored.

Lane ``planning/lanes/HSB_h2_base_growth.md``. Until 2026-09-09 the generic
``TaxPolicy`` path read IRS SOI Table 1.1 for its tax year and stamped that one
annual on all ten scored years, so ``yr1 == yr10`` to the cent on every shape.
These tests pin the replacement and, more importantly, pin the three things it
must **not** do: read anything fitted, reach a base the caller supplied, or
disturb the filing-status split PR #127 built.
"""

from __future__ import annotations

import numpy as np
import pytest

from fiscal_model.baseline import (
    APP_DEFAULT_START_YEAR,
    BaselineProjection,
    BaselineVintage,
    CBOBaseline,
    vintage_assumptions,
)
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer

SOI_TAX_YEAR = 2023


def _scorer(start_year: int = 2025, vintage: BaselineVintage | None = None):
    if vintage is None:
        return FiscalPolicyScorer(start_year=start_year, use_real_data=True)
    baseline = CBOBaseline(
        start_year=start_year, use_real_data=True, vintage=vintage
    ).generate()
    return FiscalPolicyScorer(
        baseline=baseline, start_year=start_year, use_real_data=True
    )


def _policy(**kwargs) -> TaxPolicy:
    params = dict(
        name="generic",
        description="generic rate change",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=0.0,
        start_year=2025,
        duration_years=10,
        taxable_income_elasticity=0.25,
    )
    params.update(kwargs)
    return TaxPolicy(**params)


# --------------------------------------------------------------------------
# The index itself
# --------------------------------------------------------------------------


def test_index_inside_the_window_is_the_vintages_own_path():
    proj = CBOBaseline(
        start_year=2025, use_real_data=True, vintage=BaselineVintage.CBO_FEB_2024
    ).generate()
    for offset, level in enumerate(proj.nominal_gdp):
        assert proj.nominal_income_index(2025 + offset) == pytest.approx(float(level))


def test_index_at_the_year_before_the_window_is_the_published_base_level():
    proj = CBOBaseline(
        start_year=2026, use_real_data=True, vintage=BaselineVintage.CBO_FEB_2026
    ).generate()
    assert proj.base_nominal_gdp > 0
    assert proj.nominal_income_index(2025) == pytest.approx(proj.base_nominal_gdp)


def test_index_ratios_are_the_vintages_growth_assumptions_and_nothing_else():
    """The level cancels, so the index carries no FRED anchor into a score."""
    for vintage in BaselineVintage:
        assumptions = vintage_assumptions(vintage)
        nominal = np.asarray(assumptions["real_gdp_growth"]) + np.asarray(
            assumptions["inflation"]
        )
        proj = CBOBaseline(
            start_year=2025, use_real_data=True, vintage=vintage
        ).generate()
        for offset in range(1, 10):
            ratio = proj.nominal_income_index(2025 + offset) / proj.nominal_income_index(
                2024 + offset
            )
            assert ratio == pytest.approx(1.0 + nominal[offset], rel=1e-12)


def test_index_extrapolates_at_both_ends_at_the_nearest_observed_rate():
    proj = CBOBaseline(
        start_year=2025, use_real_data=True, vintage=BaselineVintage.CBO_FEB_2024
    ).generate()
    first_growth = proj.nominal_gdp[0] / proj.base_nominal_gdp - 1.0
    assert proj.nominal_income_index(2023) == pytest.approx(
        proj.base_nominal_gdp / (1.0 + first_growth)
    )
    last_growth = proj.nominal_gdp[-1] / proj.nominal_gdp[-2] - 1.0
    assert proj.nominal_income_index(2035) == pytest.approx(
        proj.nominal_gdp[-1] * (1.0 + last_growth)
    )


def test_index_returns_zero_on_a_hand_built_projection():
    """A projection with no GDP path says so rather than guessing one."""
    assert BaselineProjection().nominal_income_index(2030) == 0.0


# --------------------------------------------------------------------------
# What the engine does with it
# --------------------------------------------------------------------------


def test_the_generic_path_is_no_longer_flat():
    result = _scorer().score_policy(_policy(), dynamic=False)
    path = result.final_deficit_effect
    assert path[0] != path[-1]
    assert abs(path[-1]) > abs(path[0])


def test_each_year_carries_its_own_factor_off_the_scored_baseline():
    scorer = _scorer(vintage=BaselineVintage.CBO_FEB_2024)
    policy = _policy()
    result = scorer.score_policy(policy, dynamic=False)
    assert policy.soi_base_tax_year == SOI_TAX_YEAR

    baseline = scorer.baseline
    anchor = baseline.nominal_income_index(SOI_TAX_YEAR)
    factors = np.array(
        [baseline.nominal_income_index(int(year)) / anchor for year in result.years]
    )
    # Dividing each year's factor back out leaves ten identical annuals - the
    # flat path the lane replaced, reconstructed from the run itself.
    unprojected = np.asarray(result.final_deficit_effect, dtype=float) / factors
    assert unprojected == pytest.approx(np.full(len(unprojected), unprojected[0]))


def test_the_vintage_decides_the_factor():
    """Two vintages over the same window give two different projections."""
    totals = {}
    for vintage in (BaselineVintage.CBO_FEB_2024, BaselineVintage.CBO_JAN_2025):
        result = _scorer(vintage=vintage).score_policy(_policy(), dynamic=False)
        totals[vintage] = result.total_10_year_cost
    assert totals[BaselineVintage.CBO_FEB_2024] != pytest.approx(
        totals[BaselineVintage.CBO_JAN_2025]
    )


def test_a_later_window_projects_further():
    early = _scorer(start_year=2025).score_policy(
        _policy(start_year=2025), dynamic=False
    )
    late = _scorer(start_year=APP_DEFAULT_START_YEAR).score_policy(
        _policy(start_year=APP_DEFAULT_START_YEAR), dynamic=False
    )
    assert abs(late.total_10_year_cost) > abs(early.total_10_year_cost)


# --------------------------------------------------------------------------
# What it must not reach
# --------------------------------------------------------------------------


def test_a_caller_supplied_annual_is_used_exactly_as_given():
    policy = _policy(annual_revenue_change_billions=-100.0)
    result = _scorer().score_policy(policy, dynamic=False)
    assert policy.soi_base_tax_year is None
    static = np.asarray(result.static_revenue_effect, dtype=float)
    assert static == pytest.approx(np.full(len(static), static[0]))


def test_a_caller_supplied_population_is_used_exactly_as_given():
    """A hand-set base carries a vintage this class has no field for."""
    policy = _policy(
        affected_taxpayers_millions=5.0,
        avg_taxable_income_in_bracket=1_000_000.0,
        affected_income_threshold=400_000.0,
    )
    result = _scorer().score_policy(policy, dynamic=False)
    assert policy.soi_base_tax_year is None
    static = np.asarray(result.static_revenue_effect, dtype=float)
    assert static == pytest.approx(np.full(len(static), static[0]))


def test_soi_base_tax_year_is_none_before_the_policy_is_scored():
    assert _policy().soi_base_tax_year is None


def test_the_data_year_a_caller_names_is_the_anchor():
    scorer = _scorer(vintage=BaselineVintage.CBO_FEB_2024)
    older = _policy(data_year=2021)
    newer = _policy(data_year=SOI_TAX_YEAR)
    a = scorer.score_policy(older, dynamic=False)
    b = scorer.score_policy(newer, dynamic=False)
    assert older.soi_base_tax_year == 2021
    assert newer.soi_base_tax_year == SOI_TAX_YEAR
    # A 2021 base is projected across two more years, so its factor is larger.
    baseline = scorer.baseline
    ratio = baseline.nominal_income_index(SOI_TAX_YEAR) / baseline.nominal_income_index(
        2021
    )
    assert ratio > 1.0
    # Same SOI level would give exactly that ratio; the levels differ, so only
    # the direction is asserted here and the ratio is pinned above.
    assert a.total_10_year_cost != pytest.approx(b.total_10_year_cost)


def test_module_policies_are_untouched_by_the_generic_factor():
    """Every module class returns before the generic branch is reached."""
    from fiscal_model.payroll import PayrollTaxPolicy, PayrollTaxType

    payroll = PayrollTaxPolicy(
        name="new payroll tax",
        description="1pp on covered earnings",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.NEW_EARNINGS_TAX,
        new_payroll_tax_rate=0.01,
        employer_share=0.0,
        effective_month=1,
        start_year=2025,
        duration_years=10,
    )
    _scorer().score_policy(payroll, dynamic=False)
    assert payroll.soi_base_tax_year is None


# --------------------------------------------------------------------------
# The filing-status split, held still
# --------------------------------------------------------------------------


def test_a_uniform_per_status_threshold_is_byte_identical_to_the_pooled_path():
    """PR #127's own invariant, re-asserted with the base growing."""
    from fiscal_model.data.irs_soi import FILING_STATUSES

    scorer = _scorer(vintage=BaselineVintage.CBO_FEB_2024)
    pooled = scorer.score_policy(
        _policy(rate_change=0.02, affected_income_threshold=100_000.0), dynamic=False
    )
    split = scorer.score_policy(
        _policy(
            rate_change=0.02,
            affected_income_threshold=100_000.0,
            threshold_by_filing_status=dict.fromkeys(FILING_STATUSES, 100_000.0),
        ),
        dynamic=False,
    )
    assert np.asarray(split.final_deficit_effect) == pytest.approx(
        np.asarray(pooled.final_deficit_effect)
    )


def test_the_split_path_grows_year_by_year_too():
    split = _scorer(vintage=BaselineVintage.CBO_FEB_2024).score_policy(
        _policy(
            rate_change=0.01,
            affected_income_threshold=20_000.0,
            threshold_by_filing_status={"joint": 40_000.0},
        ),
        dynamic=False,
    )
    path = np.asarray(split.final_deficit_effect, dtype=float)
    assert abs(path[-1]) > abs(path[0])


# --------------------------------------------------------------------------
# The Decision 6 caption
# --------------------------------------------------------------------------


def test_the_caption_reconstructs_the_figure_the_app_used_to_print():
    from fiscal_model.ui.tabs.results_summary import income_base_projection_caption

    scorer = _scorer(start_year=APP_DEFAULT_START_YEAR)
    policy = _policy(start_year=APP_DEFAULT_START_YEAR)
    result = scorer.score_policy(policy, dynamic=False)
    caption = income_base_projection_caption(policy, result)

    assert caption
    assert f"tax year {SOI_TAX_YEAR}" in caption
    baseline = scorer.baseline
    anchor = baseline.nominal_income_index(SOI_TAX_YEAR)
    factors = np.array(
        [baseline.nominal_income_index(int(year)) / anchor for year in result.years]
    )
    previous = float(
        np.sum(np.asarray(result.final_deficit_effect, dtype=float) / factors)
    )
    assert f"{previous:+,.1f}B" in caption
    assert f"{result.total_10_year_cost:+,.1f}B" in caption


def test_the_caption_is_silent_where_no_number_moved():
    from fiscal_model.ui.tabs.results_summary import income_base_projection_caption

    policy = _policy(annual_revenue_change_billions=-100.0)
    result = _scorer().score_policy(policy, dynamic=False)
    assert income_base_projection_caption(policy, result) == ""
