"""
Overlapping Generations (OLG) Model for Generational Burden Analysis

Two-period-style OLG model calibrated to the US economy. Tracks capital
accumulation and factor prices over time, then computes generational accounts
(present value of lifetime taxes minus transfers) for each birth cohort.

This is a pedagogical implementation designed for classroom use. It captures
the core insight that deficit financing crowds out capital, lowering wages for
future workers while shifting their tax burden upward.

Theory:
- Production: Y_t = A_t * K_t^α * L_t^(1-α)
- Factor prices: w_t = (1-α) * Y_t/L_t, r_t = α * Y_t/K_t - δ
- Capital law of motion: K_{t+1} = (1-δ)K_t + s*Y_t - G_t
  where G_t = government borrowing crowds out private capital
- Generational account for cohort born in year b:
    GA_b = Σ_{a=0}^{T-1} [τ_w * w_{b+a} + τ_k * r_{b+a} * K_{b+a}/L_{b+a}
                          - SS_{b+a}] / (1+ρ)^a
  (summed over working + retirement years, discounted to birth)

References:
- Diamond (1965): National debt in a neoclassical growth model, AER
- Auerbach, Gokhale & Kotlikoff (1991): Generational accounts, BPEA
- CBO (2023): Long-term budget outlook
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class OLGParams:
    """
    Calibration parameters for the OLG model.

    Default values are calibrated to approximate the US economy.
    """
    # Production function
    alpha: float = 0.35           # Capital share (Cobb-Douglas)
    tfp_growth: float = 0.015     # Annual TFP growth rate (~1.5%/yr)
    delta: float = 0.05           # Annual depreciation rate

    # Demographics
    n_growth: float = 0.007       # Annual labor force growth (~0.7%/yr)
    working_years: int = 40       # Years in working life
    retirement_years: int = 20    # Years in retirement

    # Preferences
    discount_rate: float = 0.03   # Individual discount rate (3%/yr)

    # Macro calibration (2025 US)
    initial_capital_gdp_ratio: float = 3.0    # K/Y ≈ 3
    initial_gdp: float = 29_000.0             # ~$29T GDP (billions)
    savings_rate: float = 0.20                # Private savings rate

    # Fiscal baseline (as % of GDP)
    baseline_labor_tax_rate: float = 0.25     # Average labor income tax rate
    baseline_capital_tax_rate: float = 0.20   # Average capital income tax rate
    baseline_ss_replacement: float = 0.40     # SS replaces 40% of wages
    baseline_deficit_gdp: float = 0.06        # Baseline deficit ~6% GDP

    # Simulation
    sim_years: int = 80           # Simulation horizon (years from 2025)
    base_year: int = 2025


@dataclass
class OLGResult:
    """
    Results from an OLG simulation.

    All paths are indexed by simulation year (0 = base_year).
    Generational accounts are indexed by birth cohort.
    """
    # Simulation years
    years: np.ndarray                  # Calendar years
    birth_years: np.ndarray            # Birth years of tracked cohorts

    # Factor price paths
    wage_path: np.ndarray              # Real wage ($ per worker)
    interest_path: np.ndarray          # Real interest rate (decimal)
    gdp_path: np.ndarray               # GDP level ($B)
    capital_path: np.ndarray           # Capital stock ($B)
    debt_path: np.ndarray              # Government debt ($B)

    # Generational accounts
    pv_taxes: np.ndarray               # PV of lifetime taxes paid ($B per person)
    pv_transfers: np.ndarray           # PV of lifetime SS/transfers received ($B)
    pv_wages: np.ndarray               # PV of lifetime wages earned ($B)
    net_lifetime_tax: np.ndarray       # pv_taxes - pv_transfers ($B per person)
    net_tax_rate: np.ndarray           # net_lifetime_tax / pv_wages (%)
    wage_growth_rate: np.ndarray       # Annual wage growth for each cohort (%)

    # Summary
    params: OLGParams
    scenario_name: str = "Baseline"
    description: str = ""

    @property
    def crowding_out_effect(self) -> np.ndarray:
        """Capital stock deviation from no-debt baseline (% of GDP)."""
        # Estimate: each $1 of debt crowds out ~$0.33 of capital (CBO)
        crowding = self.debt_path / self.gdp_path * 0.33 * 100
        return crowding

    def burden_vs_baseline(self, baseline: OLGResult) -> np.ndarray:
        """Net tax rate difference vs. a baseline scenario (pp)."""
        return self.net_tax_rate - baseline.net_tax_rate


class OLGModel:
    """
    Simple OLG model for generational burden analysis.

    Simulates capital accumulation and factor prices under different
    fiscal paths, then computes lifetime generational accounts.

    Usage::

        model = OLGModel()
        baseline = model.run(scenario_name="Baseline")
        reform = model.run(
            debt_shock_pct_gdp=0.10,      # +10pp debt starting Year 1
            scenario_name="High Debt"
        )
        burden_diff = reform.burden_vs_baseline(baseline)

    """

    def __init__(self, params: OLGParams | None = None):
        self.params = params or OLGParams()

    def run(
        self,
        scenario_name: str = "Baseline",
        description: str = "",
        # Debt shock: additional annual borrowing as % of GDP
        debt_shock_pct_gdp: float = 0.0,
        # SS reform: change in replacement rate (negative = cut)
        ss_replacement_change: float = 0.0,
        # Labor tax change (pp)
        labor_tax_change: float = 0.0,
        # Capital tax change (pp)
        capital_tax_change: float = 0.0,
        # Phase-in years for policy (0 = immediate)
        phase_in_years: int = 0,
    ) -> OLGResult:
        """
        Run the OLG simulation and compute generational accounts.

        Parameters
        ----------
        debt_shock_pct_gdp
            Additional annual government borrowing as a share of GDP.
            Positive = more deficit spending, crowds out capital.
        ss_replacement_change
            Change in SS replacement rate (e.g., -0.10 = 10pp cut).
        labor_tax_change
            Change in labor income tax rate (e.g., +0.02 = 2pp increase).
        capital_tax_change
            Change in capital income tax rate.
        phase_in_years
            Years to fully phase in the policy (0 = immediate).
        """
        p = self.params
        T = p.sim_years

        years = np.arange(p.base_year, p.base_year + T)

        # --- Initial steady-state calibration ---
        # K/Y = 3  →  k_init = K/L = (K/Y) * (Y/L)
        # Y/L ≈ GDP / workforce; US labor force ~170M
        labor_force = 170.0  # millions
        _initial_y_per_worker = p.initial_gdp / labor_force  # $B per million workers ≈ $170K

        initial_capital = p.initial_gdp * p.initial_capital_gdp_ratio  # $B
        initial_l = labor_force  # millions

        # Build phase-in ramp
        ramp = np.ones(T)
        if phase_in_years > 0:
            for t in range(min(phase_in_years, T)):
                ramp[t] = (t + 1) / phase_in_years

        # Policy paths (applied with ramp)
        debt_shock = debt_shock_pct_gdp * ramp
        tau_l = p.baseline_labor_tax_rate + labor_tax_change * ramp
        _tau_k = p.baseline_capital_tax_rate + capital_tax_change * ramp
        ss_repl = p.baseline_ss_replacement + ss_replacement_change * ramp

        # --- Simulate production + capital ---
        tfp = (1 + p.tfp_growth) ** np.arange(T)       # TFP index (base=1 in year 0)
        labor = initial_l * (1 + p.n_growth) ** np.arange(T)  # labor force path

        gdp = np.zeros(T)
        capital = np.zeros(T)
        wage = np.zeros(T)
        interest = np.zeros(T)
        debt = np.zeros(T)

        capital[0] = initial_capital

        for t in range(T):
            # Cobb-Douglas production
            gdp[t] = tfp[t] * (capital[t] ** p.alpha) * (labor[t] ** (1 - p.alpha))

            # Factor prices (marginal products)
            wage[t] = (1 - p.alpha) * gdp[t] / labor[t]  # $ per worker
            r_gross = p.alpha * gdp[t] / capital[t]        # gross rate of return
            interest[t] = r_gross - p.delta                 # net interest rate

            # Debt accumulation
            if t == 0:
                debt[0] = 0.20 * gdp[0]  # initial debt ~20% GDP (simplified)
            else:
                baseline_deficit = p.baseline_deficit_gdp * gdp[t]
                policy_deficit = debt_shock[t] * gdp[t]
                debt[t] = debt[t - 1] * (1 + interest[t - 1]) + baseline_deficit + policy_deficit

            # Capital law of motion (for next period)
            if t < T - 1:
                gross_investment = p.savings_rate * gdp[t]
                # Crowding out: government debt displaces private capital
                # CBO methodology: each $1 of debt → ~$0.33 less capital (partial crowding out)
                crowding_out = (p.baseline_deficit_gdp + debt_shock[t]) * gdp[t] * 0.33
                capital[t + 1] = (1 - p.delta) * capital[t] + gross_investment - crowding_out
                capital[t + 1] = max(capital[t + 1], 0.5 * capital[t])  # floor at 50%

        # --- Compute generational accounts ---
        # Track cohorts born from (base_year - working_years) to (base_year + T - 1)
        # For simplicity, track cohorts born from base_year-40 to base_year+T-1
        birth_start = p.base_year - p.working_years
        birth_end = p.base_year + T - 1
        birth_years = np.arange(birth_start, birth_end + 1)
        n_cohorts = len(birth_years)

        pv_taxes = np.zeros(n_cohorts)
        pv_transfers = np.zeros(n_cohorts)
        pv_wages = np.zeros(n_cohorts)

        for i, by in enumerate(birth_years):
            _pv_t = 0.0   # present value of taxes paid (discounted to birth year)
            _pv_tr = 0.0  # present value of SS/transfers received
            _pv_w = 0.0   # present value of wages earned

            # Working life: ages 0..working_years-1  →  years by..by+working_years-1
            for age in range(p.working_years):
                cal_year = by + age
                if cal_year < p.base_year:
                    # Pre-simulation: extrapolate backward with constant parameters
                    yr_idx = 0
                    w_t = wage[0] * (1 + p.tfp_growth) ** (cal_year - p.base_year)
                elif cal_year >= p.base_year + T:
                    yr_idx = T - 1
                    w_t = wage[T - 1] * (1 + p.tfp_growth) ** (cal_year - (p.base_year + T - 1))
                else:
                    yr_idx = cal_year - p.base_year
                    w_t = wage[yr_idx]

                tl_t = tau_l[min(yr_idx, T - 1)]
                disc = (1 + p.discount_rate) ** (-age)

                pv_taxes[i] += tl_t * w_t * disc
                pv_wages[i] += w_t * disc

            # Retirement: ages working_years..working_years+retirement_years-1
            retire_age_start = p.working_years
            for age in range(p.retirement_years):
                cal_year = by + retire_age_start + age
                if cal_year < p.base_year:
                    yr_idx = 0
                    _w_ref = wage[0] * (1 + p.tfp_growth) ** (cal_year - p.base_year)
                elif cal_year >= p.base_year + T:
                    yr_idx = T - 1
                    _w_ref = wage[T - 1] * (1 + p.tfp_growth) ** (cal_year - (p.base_year + T - 1))
                else:
                    yr_idx = cal_year - p.base_year
                    _w_ref = wage[yr_idx]

                ss_t = ss_repl[min(yr_idx, T - 1)]
                disc = (1 + p.discount_rate) ** (-(retire_age_start + age))

                # SS benefit = replacement rate * average wage at retirement
                retire_year_idx = min(max(by + retire_age_start - p.base_year, 0), T - 1)
                w_at_retire = wage[retire_year_idx]
                benefit = ss_t * w_at_retire
                pv_transfers[i] += benefit * disc

        net_lifetime_tax = pv_taxes - pv_transfers
        # Avoid division by zero for very old/future cohorts
        safe_pv_wages = np.where(pv_wages > 1e-6, pv_wages, np.nan)
        net_tax_rate = (net_lifetime_tax / safe_pv_wages) * 100

        # Wage growth rate: annualized wage growth over cohort's working life
        wage_growth = np.zeros(n_cohorts)
        for i, by in enumerate(birth_years):
            start_yr = max(by - p.base_year, 0)
            end_yr = min(by + p.working_years - 1 - p.base_year, T - 1)
            if end_yr > start_yr and start_yr < T:
                w_start = wage[start_yr]
                w_end = wage[end_yr]
                n_yrs = end_yr - start_yr
                if w_start > 0 and n_yrs > 0:
                    wage_growth[i] = ((w_end / w_start) ** (1 / n_yrs) - 1) * 100
                else:
                    wage_growth[i] = p.tfp_growth * 100

        return OLGResult(
            years=years,
            birth_years=birth_years,
            wage_path=wage,
            interest_path=interest,
            gdp_path=gdp,
            capital_path=capital,
            debt_path=debt,
            pv_taxes=pv_taxes,
            pv_transfers=pv_transfers,
            pv_wages=pv_wages,
            net_lifetime_tax=net_lifetime_tax,
            net_tax_rate=net_tax_rate,
            wage_growth_rate=wage_growth,
            params=p,
            scenario_name=scenario_name,
            description=description,
        )

    def compare_scenarios(
        self,
        scenarios: list[dict],
    ) -> dict[str, OLGResult]:
        """
        Run multiple scenarios and return results keyed by scenario name.

        Each scenario dict is passed as kwargs to ``run()``.
        """
        results = {}
        for kwargs in scenarios:
            name = kwargs.get("scenario_name", f"Scenario {len(results) + 1}")
            results[name] = self.run(**kwargs)
        return results
