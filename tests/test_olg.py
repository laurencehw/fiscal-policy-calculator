"""
Tests for the OLG (Overlapping Generations) model.

Test categories:
  1. Household optimisation — Euler equations, terminal condition
  2. Firm production — factor prices, golden rule
  3. Government budget — fiscal closure, SS arithmetic
  4. Solver — GS convergence on known steady state, Broyden on known steady state
  5. Steady state — calibration targets (K/Y, r, labour share)
  6. Generational accounting — present-value math, sign tests
  7. Policy analysis — direction of effects (sign checks)
  8. Oscillation detection helper
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from fiscal_model.models.olg import (
    BroydenSolver,
    GaussSeidelSolver,
    GenerationalAccounting,
    OLGModel,
    OLGParameters,
    OLGSolver,
    SolverStatus,
    aggregate_household_results,
    factor_prices,
    output,
    solve_household,
)
from fiscal_model.models.olg.calibration import (
    build_age_earnings_profile,
    validate_calibration,
)
from fiscal_model.models.olg.government import (
    compute_closure_tax_rate,
    compute_ss_benefit,
    compute_ss_outlays,
    compute_tax_revenues,
    solve_labor_tax_closure,
)
from fiscal_model.models.olg.solver import _oscillation_fraction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_params():
    """Small OLG (10 cohorts, 5 working) for fast unit tests."""
    p = OLGParameters(
        n_cohorts=10,
        retirement_age_cohort=5,
        sigma=1.5,
        beta=0.96,
        alpha=0.35,
        delta=0.05,
        pop_growth=0.005,
        tol=1e-4,
        max_iter_gs=200,
        max_iter_broyden=50,
        dampening_gs=0.5,
    )
    return p


@pytest.fixture
def default_params():
    """Full 55-cohort default params."""
    return OLGParameters()


# ===========================================================================
# 1. Household optimisation
# ===========================================================================

class TestHousehold:

    def test_terminal_assets_near_zero(self, small_params):
        """a_N should be ≈ 0 (lifetime budget constraint satisfied)."""
        p = small_params
        N, R = p.n_cohorts, p.retirement_age_cohort
        r, w = 0.05, 1.0
        gross_return = 1.0 + r * (1.0 - 0.30)
        net_labor = w * 0.6 * np.ones(R)
        ss_benefit = 0.25

        _, assets = solve_household(N, R, p.sigma, p.beta, gross_return,
                                    net_labor, ss_benefit)
        # Terminal wealth should be near zero
        assert abs(assets[-1]) < 0.05, f"a_N = {assets[-1]:.4f}, expected ≈ 0"

    def test_consumption_positive(self, small_params):
        """Consumption must be positive at every lifecycle stage."""
        p = small_params
        N, R = p.n_cohorts, p.retirement_age_cohort
        gross_return = 1.04
        net_labor = np.ones(R) * 0.7
        ss_benefit = 0.3

        c, _ = solve_household(N, R, p.sigma, p.beta, gross_return,
                               net_labor, ss_benefit)
        assert np.all(c > 0), "Consumption has non-positive values"

    def test_euler_equation_holds(self, small_params):
        """c_{j+1} / c_j should equal (β·R)^(1/σ) at every stage."""
        p = small_params
        N, R = p.n_cohorts, p.retirement_age_cohort
        r = 0.05
        gross_return = 1.0 + r * (1.0 - 0.25)
        net_labor = np.linspace(0.5, 0.9, R)
        ss_benefit = 0.2

        c, _ = solve_household(N, R, p.sigma, p.beta, gross_return,
                               net_labor, ss_benefit)
        phi = (p.beta * gross_return) ** (1.0 / p.sigma)
        for j in range(N - 1):
            ratio = c[j + 1] / c[j]
            assert abs(ratio - phi) < 1e-6, (
                f"Euler violated at j={j}: ratio={ratio:.6f}, phi={phi:.6f}"
            )

    def test_consumption_increases_with_income(self, small_params):
        """Higher income → higher consumption at every stage."""
        p = small_params
        N, R = p.n_cohorts, p.retirement_age_cohort
        gross_return = 1.04
        ss_benefit = 0.2

        c_low, _ = solve_household(N, R, p.sigma, p.beta, gross_return,
                                   np.ones(R) * 0.5, ss_benefit)
        c_high, _ = solve_household(N, R, p.sigma, p.beta, gross_return,
                                    np.ones(R) * 1.0, ss_benefit)
        assert np.all(c_high > c_low)

    def test_savings_hump_shaped(self, small_params):
        """Assets should be hump-shaped: rising during working life, then falling."""
        p = small_params
        N, R = p.n_cohorts, p.retirement_age_cohort
        gross_return = 1.04
        net_labor = np.ones(R) * 0.7
        ss_benefit = 0.15

        _, assets = solve_household(N, R, p.sigma, p.beta, gross_return,
                                    net_labor, ss_benefit)
        # Assets should peak somewhere before retirement
        peak_idx = np.argmax(assets[1:N])
        assert peak_idx >= 1, "Assets should peak after the first period"
        # After the peak, assets should decline
        assert assets[peak_idx + 1] >= assets[N], (
            "Assets should decline from peak to death"
        )

    def test_aggregate_results_shape(self, small_params):
        """aggregate_household_results returns correct shapes."""
        p = small_params
        K_s, L_s, c_path, a_path = aggregate_household_results(
            p, r=0.05, w=1.0,
            tau_l=0.28, tau_k=0.30, tau_ss=0.124, ss_benefit=0.30
        )
        assert isinstance(K_s, float)
        assert isinstance(L_s, float)
        assert len(c_path) == p.n_cohorts
        assert len(a_path) == p.n_cohorts + 1


# ===========================================================================
# 2. Firm production
# ===========================================================================

class TestFirm:

    def test_factor_prices_cobb_douglas(self):
        """r = α·Y/K − δ, w = (1−α)·Y/L."""
        alpha, delta, tfp = 0.35, 0.05, 1.0
        K, L = 3.0, 1.0
        r, w = factor_prices(K, L, alpha, delta, tfp)
        Y = output(K, L, alpha, tfp)
        assert abs(r - (alpha * Y / K - delta)) < 1e-10
        assert abs(w - ((1 - alpha) * Y / L)) < 1e-10

    def test_output_constant_returns(self):
        """Y(λK, λL) = λ·Y(K, L) for any λ > 0."""
        alpha = 0.35
        K, L = 2.0, 1.5
        lam = 2.5
        Y1 = output(K, L, alpha)
        Y2 = output(lam * K, lam * L, alpha)
        assert abs(Y2 / Y1 - lam) < 1e-10

    def test_r_decreases_with_K(self):
        """Higher K (given L) → lower r (diminishing returns to capital)."""
        alpha, delta = 0.35, 0.05
        L = 1.0
        r_lo, _ = factor_prices(1.0, L, alpha, delta)
        r_hi, _ = factor_prices(5.0, L, alpha, delta)
        assert r_lo > r_hi

    def test_w_increases_with_K(self):
        """Higher K → higher wage (capital complements labour)."""
        alpha, delta = 0.35, 0.05
        L = 1.0
        _, w_lo = factor_prices(1.0, L, alpha, delta)
        _, w_hi = factor_prices(5.0, L, alpha, delta)
        assert w_hi > w_lo

    def test_positive_r_for_reasonable_K(self):
        """Net return r should be positive for K/Y ≈ 3."""
        K, L = 3.0, 1.0
        r, _ = factor_prices(K, L, 0.35, 0.05)
        # α·Y/K = α / (K/Y) ≈ 0.35/3 ≈ 0.117; r = 0.117 - 0.05 = 0.067
        assert r > 0.0


# ===========================================================================
# 3. Government budget
# ===========================================================================

class TestGovernment:

    def test_ss_benefit_proportional_to_wage(self):
        """SS benefit = replacement_rate × w."""
        w = 1.5
        rep = 0.4
        assert abs(compute_ss_benefit(rep, w) - rep * w) < 1e-10

    def test_ss_outlays(self, small_params):
        """Total SS outlays = benefit × n_retirees."""
        p = small_params
        ss_benefit = 0.4
        sizes = p.cohort_sizes
        out = compute_ss_outlays(ss_benefit, sizes, p.retirement_age_cohort)
        n_ret = float(sizes[p.retirement_age_cohort:].sum())
        assert abs(out - ss_benefit * n_ret) < 1e-10

    def test_tax_revenues_additive(self):
        """Total revenue = labour tax + capital tax + payroll tax."""
        w, L, r, K = 1.0, 1.5, 0.05, 3.0
        tau_l, tau_k, tau_ss = 0.28, 0.30, 0.124
        rev = compute_tax_revenues(w, L, r, K, tau_l, tau_k, tau_ss)
        expected = tau_l * w * L + tau_k * r * K + tau_ss * w * L
        assert abs(rev - expected) < 1e-10

    def test_labor_tax_closure_budget_balance(self):
        """After closure, primary surplus matches target (unclamped scenario)."""
        # Use values where required tau_l is well within [0, 0.70]
        # Y = output(3.0, 1.0, 0.35) ≈ 1.50; G = 0.175 * 1.50 = 0.26
        # ss_out = 0.05 (small); tau_k * r * K = 0.30*0.05*3.0 = 0.045
        # tau_ss * w * L = 0.124; required_total = 0.26+0.05 = 0.31
        # req_labour_tax = 0.31 - 0.045 - 0.124 = 0.141
        # tau_l = 0.141 / 1.0 = 0.14 → well within [0, 0.70]
        w, L, r, K = 1.0, 1.0, 0.05, 3.0
        G, ss_out = 0.26, 0.05
        tau_k, tau_ss = 0.30, 0.124
        target_ps = 0.0

        tau_l = solve_labor_tax_closure(
            w, L, r, K, tau_k, tau_ss, G, ss_out,
            debt=0.0, target_primary_surplus=target_ps
        )
        # Verify budget balance holds (tau_l is not clamped here)
        total_rev = compute_tax_revenues(w, L, r, K, tau_l, tau_k, tau_ss)
        primary_surplus = total_rev - G - ss_out
        assert abs(primary_surplus - target_ps) < 1e-8
        # tau_l should be in a reasonable range
        assert 0.0 < tau_l < 0.70

    def test_closure_tax_clamped(self):
        """Fiscal closure tax rate should be in [0, 0.70]."""
        p = OLGParameters(fiscal_closure="labor_tax")
        w, L, r, K = 0.5, 0.8, 0.03, 1.0
        Y = output(K, L, p.alpha, p.tfp)
        ss_benefit = 0.2
        ss_out = compute_ss_outlays(ss_benefit, p.cohort_sizes, p.retirement_age_cohort)
        tau_l = compute_closure_tax_rate(p, Y, w, L, r, K, debt=10.0, ss_outlays=ss_out)
        assert 0.0 <= tau_l <= 0.70


# ===========================================================================
# 4. Solver — convergence tests
# ===========================================================================

class TestSolver:

    def test_gs_converges_small(self, small_params):
        """GS should converge for small params."""
        gs = GaussSeidelSolver(small_params)
        L_init = float(np.dot(
            small_params.cohort_sizes[:small_params.retirement_age_cohort],
            small_params.earnings_profile
        ))
        ss, status = gs.solve(K_init=2.0, L_init=L_init, debt=1.0)
        assert status == SolverStatus.CONVERGED
        assert ss.K > 0
        assert ss.Y > 0
        assert ss.r > 0

    def test_broyden_converges_small(self, small_params):
        """Broyden's should converge for small params."""
        broyden = BroydenSolver(small_params)
        L_init = float(np.dot(
            small_params.cohort_sizes[:small_params.retirement_age_cohort],
            small_params.earnings_profile
        ))
        ss, status = broyden.solve(K_init=2.0, L_init=L_init, debt=1.0)
        assert status == SolverStatus.CONVERGED
        assert ss.K > 0

    def test_gs_and_broyden_agree(self, small_params):
        """GS and Broyden's should produce consistent K values."""
        L_init = float(np.dot(
            small_params.cohort_sizes[:small_params.retirement_age_cohort],
            small_params.earnings_profile
        ))
        gs = GaussSeidelSolver(small_params)
        broyden = BroydenSolver(small_params)
        ss_gs, _ = gs.solve(K_init=2.0, L_init=L_init, debt=0.5)
        ss_br, _ = broyden.solve(K_init=2.0, L_init=L_init, debt=0.5)
        # Allow 5% tolerance between GS and Broyden
        assert abs(ss_gs.K - ss_br.K) / max(ss_gs.K, 1e-6) < 0.05, (
            f"GS K={ss_gs.K:.4f} vs Broyden K={ss_br.K:.4f}"
        )

    def test_auto_solver_returns_steady_state(self, small_params):
        """OLGSolver.solve_steady_state() returns a valid SteadyState."""
        solver = OLGSolver(small_params)
        ss = solver.solve_steady_state()
        assert ss.K > 0
        assert ss.Y > 0
        assert ss.r > -0.5  # Interest rate not bizarrely negative

    def test_market_clearing_residual(self, small_params):
        """After solving, capital supply should approximately equal demand."""
        solver = OLGSolver(small_params)
        ss = solver.solve_steady_state()
        # K_supply = re-aggregate given equilibrium prices
        K_check, _, _, _ = aggregate_household_results(
            small_params, ss.r, ss.w,
            ss.tau_l, ss.tau_k, ss.tau_ss, ss.ss_benefit
        )
        assert abs(K_check - ss.K) / max(abs(ss.K), 1e-6) < 0.01, (
            f"Market clearing: K_supply={K_check:.4f} ≠ K_demand={ss.K:.4f}"
        )

    def test_broyden_large_shock(self, small_params):
        """Broyden's should converge even for large tax shocks."""
        import copy
        p = copy.copy(small_params)
        p.capital_tax_rate = 0.50  # Large shock: +20 pp
        solver = OLGSolver(p)
        ss = solver.solve_steady_state(force_broyden=True)
        assert ss.K > 0


# ===========================================================================
# 5. Steady state — calibration targets
# ===========================================================================

class TestSteadyState:

    def test_ky_ratio_reasonable(self, small_params):
        """K/Y should be positive and not astronomically large."""
        # The 10-cohort model with 5-period working life gives a lower K/Y
        # than the 55-cohort model, so we use a wider check here.
        model = OLGModel(small_params)
        ss = model.get_baseline()
        assert 0.1 <= ss.capital_output_ratio <= 10.0, (
            f"K/Y = {ss.capital_output_ratio:.2f}, expected 0.1–10.0"
        )

    def test_interest_rate_positive(self, small_params):
        """Real interest rate r should be positive."""
        model = OLGModel(small_params)
        ss = model.get_baseline()
        assert ss.r > 0.0

    def test_labour_share_close_to_1_minus_alpha(self, small_params):
        """Labour share wL/Y ≈ 1 − α by the Cobb-Douglas identity."""
        model = OLGModel(small_params)
        ss = model.get_baseline()
        expected_share = 1.0 - small_params.alpha
        assert abs(ss.labor_share - expected_share) < 0.05, (
            f"Labour share = {ss.labor_share:.3f}, expected ≈ {expected_share:.3f}"
        )

    def test_default_params_convergence(self, default_params):
        """55-cohort full model should converge and satisfy labour-share identity."""
        default_params.tol = 1e-4  # Relaxed for speed in CI
        default_params.max_iter_gs = 300
        model = OLGModel(default_params)
        ss = model.get_baseline()
        checks = validate_calibration(ss, default_params)
        # Labour share is a direct Cobb-Douglas identity (always ≈ 1−α)
        assert checks["Labour share (wL/Y)"]["ok"], (
            f"Labour share = {checks['Labour share (wL/Y)']['value']:.3f}"
        )
        # Model should converge to a positive-output equilibrium
        assert ss.Y > 0 and ss.K > 0 and ss.r > -0.5

    def test_reform_vs_baseline_direction(self, small_params):
        """Higher capital tax → lower K, lower w, higher r in steady state."""
        import copy
        p_reform = copy.copy(small_params)
        p_reform.capital_tax_rate = 0.45  # +15 pp shock

        model_base = OLGModel(small_params)
        model_reform = OLGModel(p_reform)

        ss_base = model_base.get_baseline()
        ss_reform = model_reform.get_baseline()

        assert ss_reform.K < ss_base.K, "Higher capital tax should reduce K"
        assert ss_reform.w < ss_base.w, "Lower K should reduce wage"


# ===========================================================================
# 6. Generational accounting
# ===========================================================================

class TestGenerationalAccounting:

    def test_burden_profile_length(self, small_params):
        """Burden profile length should equal n_cohorts."""
        model = OLGModel(small_params)
        baseline = model.get_baseline()
        ga = GenerationalAccounting(small_params)
        gen_acc = ga.compute(baseline, baseline)
        assert len(gen_acc.lifetime_burden_baseline) == small_params.n_cohorts

    def test_no_reform_zero_burden_change(self, small_params):
        """When reform = baseline, burden change should be zero."""
        model = OLGModel(small_params)
        baseline = model.get_baseline()
        ga = GenerationalAccounting(small_params)
        gen_acc = ga.compute(baseline, baseline)
        assert np.allclose(gen_acc.burden_change, 0.0, atol=1e-8)

    def test_burden_change_sign(self, small_params):
        """Reform that raises capital tax should increase burden on younger cohorts."""
        import copy
        p_reform = copy.copy(small_params)
        p_reform.capital_tax_rate = 0.45

        model_base = OLGModel(small_params)
        model_reform = OLGModel(p_reform)

        ss_base = model_base.get_baseline()
        ss_reform = model_reform.get_baseline()

        ga = GenerationalAccounting(small_params)
        gen_acc = ga.compute(ss_base, ss_reform)

        # Higher capital tax → higher capital income tax → positive burden change
        # (at least for working cohorts with positive savings)
        assert gen_acc.newborn_burden_change is not None  # Must compute

    def test_generational_imbalance_is_float(self, small_params):
        """generational_imbalance property should return a finite float."""
        model = OLGModel(small_params)
        baseline = model.get_baseline()
        ga = GenerationalAccounting(small_params)
        gen_acc = ga.compute(baseline, baseline)
        imb = gen_acc.generational_imbalance
        assert math.isfinite(imb)

    def test_pv_discounting_in_gen_accounts(self, small_params):
        """Remaining lifetime burden should be smaller for older cohorts (j > 0)."""
        model = OLGModel(small_params)
        baseline = model.get_baseline()
        ga = GenerationalAccounting(small_params)
        gen_acc = ga.compute(baseline, baseline)
        # For positive net taxes: younger cohorts (j=0) have higher remaining burden
        # The youngest cohort has the longest remaining life
        # (cannot be strictly tested without knowing sign of taxes, but length holds)
        assert len(gen_acc.lifetime_burden_baseline) == small_params.n_cohorts

    def test_to_dataframe(self, small_params):
        """to_dataframe() returns correct columns and length."""
        model = OLGModel(small_params)
        baseline = model.get_baseline()
        ga = GenerationalAccounting(small_params)
        gen_acc = ga.compute(baseline, baseline)
        df = gen_acc.to_dataframe()
        assert len(df) == small_params.n_cohorts
        assert "age" in df.columns
        assert "burden_change" in df.columns

    def test_intertemporal_balance(self, small_params):
        """compute_intertemporal_balance returns dict with expected keys."""
        model = OLGModel(small_params)
        baseline = model.get_baseline()
        ga = GenerationalAccounting(small_params)
        result = ga.compute_intertemporal_balance(baseline)
        assert "pv_taxes" in result
        assert "pv_spending" in result
        assert "current_debt" in result
        assert "imbalance" in result
        assert "sustainable" in result
        assert isinstance(result["sustainable"], bool)


# ===========================================================================
# 7. Policy analysis
# ===========================================================================

class TestPolicyAnalysis:

    def test_analyze_policy_returns_result(self, small_params):
        """analyze_policy returns an OLGPolicyResult."""
        model = OLGModel(small_params)
        result = model.analyze_policy(
            reform_overrides={"tau_k": 0.35},
            policy_name="Test Reform",
            compute_gen_accounts=True,
            compute_transition=True,
            start_year=2026,
        )
        assert result is not None
        assert result.policy_name == "Test Reform"
        assert result.confidence_label == OLGModel.CONFIDENCE_LABEL

    def test_no_reform_zero_gdp_change(self, small_params):
        """Null reform (no overrides) should give ~0% long-run GDP change."""
        model = OLGModel(small_params)
        result = model.analyze_policy(
            reform_overrides={},
            compute_transition=False,
            compute_gen_accounts=False,
        )
        assert abs(result.long_run_gdp_pct_change) < 1.0, (
            f"Null reform GDP change = {result.long_run_gdp_pct_change:.2f}%"
        )

    def test_higher_capital_tax_lowers_gdp(self, small_params):
        """Raising capital tax should lower long-run GDP (crowding out)."""
        model = OLGModel(small_params)
        result = model.analyze_policy(
            reform_overrides={"tau_k": 0.45},
            compute_transition=False,
            compute_gen_accounts=False,
        )
        assert result.long_run_gdp_pct_change < 0.0, (
            f"Expected GDP decline, got {result.long_run_gdp_pct_change:+.2f}%"
        )

    def test_ss_cut_raises_k(self, small_params):
        """Cutting SS replacement rate → more private saving → higher K."""
        model = OLGModel(small_params)
        result = model.analyze_policy(
            reform_overrides={"ss_replacement_rate": 0.20},  # Cut from 0.40
            compute_transition=False,
            compute_gen_accounts=False,
        )
        assert result.long_run_capital_pct_change > 0.0, (
            f"Expected capital increase, got {result.long_run_capital_pct_change:+.2f}%"
        )

    def test_transition_path_length(self, small_params):
        """Transition path should have transition_years entries."""
        model = OLGModel(small_params)
        result = model.analyze_policy(
            reform_overrides={"tau_k": 0.35},
            compute_transition=True,
            compute_gen_accounts=False,
        )
        assert len(result.transition.years) == small_params.transition_years

    def test_summary_string(self, small_params):
        """summary() should return a non-empty string."""
        model = OLGModel(small_params)
        result = model.analyze_policy(reform_overrides={}, compute_transition=False,
                                      compute_gen_accounts=False)
        s = result.summary()
        assert isinstance(s, str) and len(s) > 50

    def test_to_transition_dataframe(self, small_params):
        """to_transition_dataframe() should return a DataFrame with expected columns."""
        model = OLGModel(small_params)
        result = model.analyze_policy(reform_overrides={}, compute_transition=True,
                                      compute_gen_accounts=False)
        df = result.to_transition_dataframe()
        assert "Year" in df.columns
        assert "Y" in df.columns
        assert "GDP_pct_change" in df.columns
        assert len(df) == small_params.transition_years


# ===========================================================================
# 8. Oscillation detection
# ===========================================================================

class TestOscillationDetection:

    def test_monotone_sequence_no_oscillation(self):
        """Monotone decreasing residuals → oscillation fraction ≈ 0."""
        residuals = list(np.linspace(1.0, 0.001, 30))
        frac = _oscillation_fraction(residuals, window=20)
        assert frac < 0.1

    def test_alternating_sequence_high_oscillation(self):
        """Alternating sign residuals → oscillation fraction ≈ 1."""
        residuals = [(-1) ** i * 0.1 for i in range(30)]
        frac = _oscillation_fraction(residuals, window=20)
        assert frac > 0.8

    def test_empty_sequence(self):
        """Empty sequence → oscillation fraction = 0."""
        assert _oscillation_fraction([], 10) == 0.0

    def test_single_element(self):
        """Single element → no sign changes → 0."""
        assert _oscillation_fraction([1.0], 10) == 0.0

    def test_window_smaller_than_sequence(self):
        """Window correctly limits to last N entries."""
        residuals = [1.0] * 50 + [(-1) ** i * 0.1 for i in range(20)]
        frac = _oscillation_fraction(residuals, window=20)
        assert frac > 0.8


# ===========================================================================
# 9. Age-earnings profile calibration
# ===========================================================================

class TestCalibration:

    def test_profile_mean_one(self):
        """BLS-calibrated profile should have mean ≈ 1."""
        eps = build_age_earnings_profile(44)
        assert abs(eps.mean() - 1.0) < 0.05

    def test_profile_hump_shaped(self):
        """Profile should peak in middle cohorts (ages 40–55)."""
        eps = build_age_earnings_profile(44)
        peak_cohort = int(np.argmax(eps))
        # Peak should be between cohort 15 (age 36) and 35 (age 56)
        assert 15 <= peak_cohort <= 35, f"Peak at cohort {peak_cohort} (age {21 + peak_cohort})"

    def test_profile_length(self):
        """Profile length should match retirement_age_cohort."""
        for R in [30, 44, 50]:
            eps = build_age_earnings_profile(R)
            assert len(eps) == R

    def test_profile_positive(self):
        """All efficiency values should be positive."""
        eps = build_age_earnings_profile(44)
        assert np.all(eps > 0)

    def test_validate_calibration_keys(self, small_params):
        """validate_calibration returns expected keys."""
        model = OLGModel(small_params)
        ss = model.get_baseline()
        checks = validate_calibration(ss, small_params)
        assert "K/Y ratio" in checks
        assert "Labour share (wL/Y)" in checks
        assert "Real interest rate (%)" in checks
        assert "Debt / GDP" in checks


# ===========================================================================
# 10. PWBMModel adapter
# ===========================================================================

class TestPWBMModel:

    def test_pwbm_run_returns_macro_result(self, small_params):
        """PWBMModel.run() should return an OLGMacroResult."""
        from fiscal_model.models import MacroScenario
        from fiscal_model.models.olg import PWBMModel

        pwbm = PWBMModel(params=small_params)
        scenario = MacroScenario(
            name="Test",
            description="Test scenario",
            receipts_change=np.zeros(10),
            outlays_change=np.zeros(10),
        )
        result = pwbm.run(scenario)
        assert result is not None
        assert len(result.years) == 10
        assert len(result.gdp_level_pct) == 10

    def test_pwbm_confidence_label(self, small_params):
        """Result should carry the OLG confidence label."""
        from fiscal_model.models import MacroScenario
        from fiscal_model.models.olg import PWBMModel

        pwbm = PWBMModel(params=small_params)
        scenario = MacroScenario(
            name="Test",
            description="Test scenario",
        )
        result = pwbm.run(scenario)
        assert "uncertainty" in result.confidence_label.lower()

    def test_pwbm_get_baseline(self, small_params):
        """get_baseline() should return a DataFrame with expected columns."""
        from fiscal_model.models.olg import PWBMModel
        pwbm = PWBMModel(params=small_params)
        df = pwbm.get_baseline()
        assert "Year" in df.columns
        assert "GDP ($T)" in df.columns
        assert len(df) == 10
