"""The cohort-by-cohort, perfect-foresight OLG transition."""

from __future__ import annotations

import numpy as np
import pytest

from fiscal_model.models.olg import OLGModel, OLGParameters
from fiscal_model.models.olg.household import (
    consumption_equivalent,
    solve_household,
    solve_remaining_life,
)
from fiscal_model.models.olg.solver import OLGSolver


@pytest.fixture(scope="module")
def tax_cut():
    return OLGModel(OLGParameters()).analyze_policy(
        reform_overrides={"tau_k": 0.20}, policy_name="t", compute_gen_accounts=False
    )


def test_remaining_life_plan_is_the_steady_state_plan_at_constant_prices():
    p = OLGParameters()
    R = 1.0 + 0.05 * (1.0 - p.capital_tax_rate)
    labour = 0.6 * p.earnings_profile
    c, a = solve_household(p.n_cohorts, p.retirement_age_cohort, p.sigma, p.beta, R, labour, 0.25)
    income = np.concatenate([labour, np.full(p.n_cohorts - p.retirement_age_cohort, 0.25)])
    for j in (0, 10, 30, 50):
        c_j, a_j = solve_remaining_life(p.sigma, p.beta, np.full(p.n_cohorts - j, R), income[j:], a[j])
        assert np.allclose(c_j, c[j:], rtol=1e-9)
        assert np.allclose(a_j, a[j:], rtol=1e-9, atol=1e-12)


def test_consumption_equivalent_is_the_uniform_scaling():
    c = np.linspace(1.0, 2.0, 40)
    assert consumption_equivalent(1.03 * c, c, 1.5, 0.96) == pytest.approx(0.03, rel=1e-12)
    assert consumption_equivalent(c, c, 1.0, 0.96) == pytest.approx(0.0, abs=1e-12)


def test_unreformed_foresight_path_stays_at_the_baseline():
    solver = OLGSolver(OLGParameters())
    baseline = solver.solve_steady_state()
    path = solver.compute_transition_path_foresight(baseline, lambda t: {}, reform_ss=baseline)
    assert path.converged
    assert np.allclose(path.K_path, baseline.K, rtol=1e-6)
    assert np.allclose(path.debt_path, baseline.debt, rtol=1e-6)
    assert np.allclose(path.tau_l_path, baseline.tau_l, rtol=1e-6)
    assert np.max(np.abs(path.cohort_welfare_pct)) < 1e-3


def test_default_transition_is_perfect_foresight(tax_cut):
    t = tax_cut.transition
    assert t.expectations == "perfect_foresight"
    assert t.converged
    p = OLGParameters()
    # Every generation alive at the start, plus every one entering in the window.
    assert len(t.cohort_birth_years) == p.n_cohorts + p.transition_years - 1
    assert np.all(np.diff(t.cohort_birth_years) == 1)
    assert t.cohort_birth_years[0] == 2026 - 21 - (p.n_cohorts - 1)


def test_capital_builds_up_over_decades_not_years(tax_cut):
    gdp = tax_cut.gdp_transition_pct_change()
    long_run = tax_cut.long_run_gdp_pct_change
    assert long_run > 0
    # Myopic re-planning got most of the way within five years; savers who
    # build capital generation by generation do not.
    assert gdp[5] < 0.5 * long_run
    assert gdp[30] > 0.75 * long_run
    myopic = OLGModel(OLGParameters()).analyze_policy(
        reform_overrides={"tau_k": 0.20}, policy_name="t", compute_gen_accounts=False, expectations="myopic"
    )
    assert myopic.transition.expectations == "myopic"
    assert myopic.gdp_transition_pct_change()[5] > 0.9 * long_run


def test_a_capital_tax_cut_helps_later_generations(tax_cut):
    welfare = tax_cut.transition.cohort_welfare_pct
    assert welfare[-1] > 0
    # The labour tax rises to pay for it, so some generation alive or born
    # early in the window loses.
    assert welfare.min() < 0


def test_unknown_expectations_is_refused():
    with pytest.raises(ValueError):
        OLGModel(OLGParameters()).analyze_policy(
            reform_overrides={"tau_k": 0.2}, compute_gen_accounts=False, expectations="adaptive"
        )


def test_olg_view_reports_welfare_by_birth_year():
    from fiscal_model.result_views import olg_view

    view = olg_view(0.20, 0.124, 0.40)
    assert view["expectations"] == "perfect_foresight"
    assert view["path_converged"] is True
    rows = view["welfare_by_birth_year"]
    assert rows and all(set(r) == {"born", "pct"} for r in rows)
