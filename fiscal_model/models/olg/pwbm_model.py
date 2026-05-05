"""
PWBMModel — Penn Wharton-style OLG adapter for the existing MacroModelAdapter framework.

Bridges the 55-cohort AK OLG model to the MacroModelAdapter ABC so that OLG
results can be used anywhere FRBUSAdapterLite is accepted.

Usage
-----
    from fiscal_model.models.olg import PWBMModel
    from fiscal_model.models import MacroScenario
    import numpy as np

    pwbm = PWBMModel()

    scenario = MacroScenario(
        name="Corporate Tax Hike",
        description="21% → 28% corporate rate",
        receipts_change=np.array([-135.0] * 10),  # CBO estimate
    )
    result = pwbm.run(scenario)
    print(f"Long-run GDP effect: {result.olg_result.long_run_gdp_pct_change:+.2f}%")
    print(f"10-year GDP effect:  {result.cumulative_gdp_effect:+.2f}%-years")

Confidence label
----------------
All OLG-derived outputs display:
    "Model estimate — wide uncertainty band"
to distinguish them from CBO-calibrated static scores.

Streamlit caching
-----------------
For use in the Streamlit app, wrap calls in ``@st.cache_data``.
The steady-state computation (~0.5 s per call) is the expensive step;
the baseline is cached as a class attribute.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..macro_adapter import (
    MacroModelAdapter,
    MacroResult,
    MacroScenario,
)
from .model import OLGModel, OLGPolicyResult
from .parameters import OLGParameters

logger = logging.getLogger(__name__)

CONFIDENCE_LABEL = "Model estimate — wide uncertainty band"


def _pad_to_horizon(values: np.ndarray, horizon: int) -> np.ndarray:
    """Return a fixed-horizon array by trimming or extending the final value."""
    array = np.asarray(values, dtype=float)
    if len(array) == horizon:
        return array
    if len(array) == 0:
        return np.zeros(horizon, dtype=float)
    if len(array) > horizon:
        return array[:horizon]
    return np.concatenate([array, np.full(horizon - len(array), array[-1])])


# ---------------------------------------------------------------------------
# Extended result that carries both MacroResult and OLG-specific data
# ---------------------------------------------------------------------------

@dataclass
class OLGMacroResult(MacroResult):
    """
    MacroResult extended with OLG-specific long-run outputs.

    Inherits all standard MacroResult fields (GDP path, employment, rates,
    revenue feedback) plus:
      olg_result       — full OLGPolicyResult with steady states and gen accounts
      confidence_label — always "Model estimate — wide uncertainty band"
    """
    olg_result: OLGPolicyResult | None = None
    confidence_label: str = CONFIDENCE_LABEL
    olg_overrides: dict | None = None


# ---------------------------------------------------------------------------
# PWBMModel
# ---------------------------------------------------------------------------

class PWBMModel(MacroModelAdapter):
    """
    Penn Wharton-style OLG model implementing the MacroModelAdapter interface.

    Translates a MacroScenario (receipts/outlays changes) into OLG fiscal
    parameter overrides and runs the AK 55-cohort model.

    The mapping from scenario revenue changes to OLG overrides uses a
    simple heuristic:
      - Large revenue increase (< −$500B/yr) → capital tax rate increase
      - Large revenue decrease (> +$200B/yr) → capital tax rate decrease
      - SS-related changes → SS replacement rate adjustment
      - Default → labour tax rate adjustment (fiscal closure backstop)

    For most use cases, callers should use ``analyze_policy_olg()`` directly
    with explicit parameter overrides rather than relying on this heuristic.

    Parameters
    ----------
    params : OLGParameters | None
        OLG model parameters. Default: US calibration circa 2025.
    baseline_gdp_billions : float
        Nominal GDP level for unit conversions (default $30T CBO 2026).
    """

    CONFIDENCE_LABEL = CONFIDENCE_LABEL

    def __init__(
        self,
        params: OLGParameters | None = None,
        baseline_gdp_billions: float = 30_000.0,
    ):
        self._params = params or OLGParameters()
        self._baseline_gdp = baseline_gdp_billions
        self._model = OLGModel(self._params)
        # Cache baseline at class level so repeated calls are fast
        self._baseline_ss = None

    @property
    def name(self) -> str:
        return "PWBM-OLG"

    @property
    def description(self) -> str:
        return (
            "55-cohort Auerbach-Kotlikoff OLG model (Penn Wharton style). "
            f"{self.CONFIDENCE_LABEL}."
        )

    # ------------------------------------------------------------------
    # MacroModelAdapter interface
    # ------------------------------------------------------------------

    def run(self, scenario: MacroScenario) -> OLGMacroResult:
        """
        Run OLG model for the given fiscal scenario.

        Converts receipts_change / outlays_change into OLG parameter overrides,
        solves for the reform steady state, and packages results as MacroResult.

        Returns OLGMacroResult (a MacroResult subclass with .olg_result attached).
        """
        n = scenario.horizon_years
        years = np.arange(scenario.start_year, scenario.start_year + n)

        # Derive OLG overrides from scenario
        overrides = self._scenario_to_olg_overrides(scenario)
        policy_name = scenario.name

        if not overrides:
            olg_result = self.analyze_policy_olg(
                reform_overrides={},
                policy_name=policy_name,
                compute_gen_accounts=False,
                compute_transition=False,
                start_year=scenario.start_year,
            )
            zeros = np.zeros(n, dtype=float)
            return OLGMacroResult(
                scenario_name=scenario.name,
                model_name=self.name,
                years=years,
                gdp_level_pct=zeros.copy(),
                gdp_growth_ppts=zeros.copy(),
                employment_change_millions=zeros.copy(),
                unemployment_rate_ppts=zeros.copy(),
                short_rate_ppts=zeros.copy(),
                long_rate_ppts=zeros.copy(),
                revenue_feedback_billions=zeros.copy(),
                interest_cost_billions=zeros.copy(),
                olg_result=olg_result,
                confidence_label=self.CONFIDENCE_LABEL,
                olg_overrides={},
            )

        # Run OLG analysis
        olg_result = self.analyze_policy_olg(
            reform_overrides=overrides,
            policy_name=policy_name,
            compute_transition=True,
            start_year=scenario.start_year,
        )
        baseline_transition = self.analyze_policy_olg(
            reform_overrides={},
            policy_name=f"{policy_name} — no-reform reference",
            compute_gen_accounts=False,
            compute_transition=True,
            start_year=scenario.start_year,
        ).transition

        # Map OLG transition path to MacroResult arrays (10-year window),
        # netting out the model's no-reform transition drift.
        path = olg_result.transition
        y_reform = _pad_to_horizon(path.Y_path, n)
        y_reference = _pad_to_horizon(baseline_transition.Y_path, n)
        gdp_pct = (y_reform - y_reference) / np.maximum(np.abs(y_reference), 1e-10) * 100.0

        # GDP growth rate (first difference of level)
        gdp_growth = np.zeros(n)
        gdp_growth[0] = gdp_pct[0]
        gdp_growth[1:] = np.diff(gdp_pct)

        # Employment: Okun coefficient ~0.5
        employment_change = gdp_pct / 100.0 * 0.5 * 160.0  # millions

        # Unemployment (inverse Okun)
        unemp_ppts = -gdp_pct * 0.5

        # Interest rates: capital deepening changes r
        r_path = _pad_to_horizon(path.r_path, n)
        reference_r_path = _pad_to_horizon(baseline_transition.r_path, n)
        short_rate_ppts = (r_path - reference_r_path) * 100.0
        long_rate_ppts = short_rate_ppts * 0.8  # Long rate moves ~80% as much

        # Revenue feedback: OLG GDP change × marginal tax rate
        marginal_rate = self._params.labor_tax_rate
        gdp_change_bn = (y_reform - y_reference) * self._baseline_gdp
        revenue_feedback = gdp_change_bn * marginal_rate

        # Interest cost: change in debt × avg rate
        debt_path = _pad_to_horizon(path.debt_path, n)
        reference_debt_path = _pad_to_horizon(baseline_transition.debt_path, n)
        debt_change = (debt_path - reference_debt_path) * self._baseline_gdp
        interest_cost = debt_change * 0.04

        return OLGMacroResult(
            scenario_name=scenario.name,
            model_name=self.name,
            years=years,
            gdp_level_pct=gdp_pct,
            gdp_growth_ppts=gdp_growth,
            employment_change_millions=employment_change,
            unemployment_rate_ppts=unemp_ppts,
            short_rate_ppts=short_rate_ppts,
            long_rate_ppts=long_rate_ppts,
            revenue_feedback_billions=revenue_feedback,
            interest_cost_billions=interest_cost,
            olg_result=olg_result,
            confidence_label=self.CONFIDENCE_LABEL,
            olg_overrides=dict(overrides),
        )

    def get_baseline(self) -> pd.DataFrame:
        """Get baseline steady-state projection as a DataFrame."""
        if self._baseline_ss is None:
            self._baseline_ss = self._model.get_baseline()
        ss = self._baseline_ss
        years = np.arange(2025, 2035)
        Y_bn = ss.Y * self._baseline_gdp
        r_pct = ss.r * 100.0
        return pd.DataFrame({
            "Year": years,
            "GDP ($T)": np.full(10, Y_bn / 1000.0),
            "Real GDP ($T)": np.full(10, Y_bn / 1000.0),
            "Unemployment (%)": np.full(10, 4.2),
            "Fed Funds (%)": np.full(10, r_pct),
            "10Y Rate (%)": np.full(10, r_pct + 0.5),
            "Core PCE (%)": np.full(10, 2.5),
        })

    # ------------------------------------------------------------------
    # OLG-specific public methods
    # ------------------------------------------------------------------

    def analyze_policy_olg(
        self,
        reform_overrides: dict | None = None,
        policy_name: str = "OLG Reform",
        compute_gen_accounts: bool = True,
        compute_transition: bool = True,
        start_year: int = 2026,
    ) -> OLGPolicyResult:
        """
        Full OLG policy analysis with explicit parameter overrides.

        This is the preferred entry point when you know the exact fiscal
        parameter changes (e.g. tau_k = 0.35 for a +5 pp corporate hike).

        Parameters
        ----------
        reform_overrides : dict | None
            OLG parameter overrides: {'tau_l', 'tau_k', 'tau_ss',
            'ss_replacement_rate'}.
        policy_name : str
        compute_gen_accounts : bool
        compute_transition : bool
        start_year : int

        Returns
        -------
        OLGPolicyResult with summary(), to_transition_dataframe(), etc.
        """
        return self._model.analyze_policy(
            reform_overrides=reform_overrides or {},
            policy_name=policy_name,
            compute_gen_accounts=compute_gen_accounts,
            compute_transition=compute_transition,
            start_year=start_year,
        )

    def get_olg_baseline(self):
        """Return cached OLG baseline steady state."""
        return self._model.get_baseline()

    # ------------------------------------------------------------------
    # Scenario → OLG overrides (heuristic mapping)
    # ------------------------------------------------------------------

    def _scenario_to_olg_overrides(self, scenario: MacroScenario) -> dict:
        """
        Map a MacroScenario to OLG fiscal parameter overrides.

        Heuristic rules (approximate; for precise analysis use
        analyze_policy_olg() with explicit overrides):

        1. Net annual revenue change → implied labour tax rate change
        2. If SS-related policy, adjust ss_replacement_rate
        3. Very large capital changes → capital tax rate
        """
        p = self._params
        overrides: dict = {}

        # Average annual revenue change (positive = more revenue = contractionary)
        avg_receipts = float(np.mean(scenario.receipts_change))
        avg_outlays = float(np.mean(scenario.outlays_change))

        # Convert from billions to fraction of model GDP
        # (model is normalised; rough conversion: $30T GDP → 1 model unit)
        rev_fraction = avg_receipts / max(self._baseline_gdp, 1.0)

        # Capital tax proxy: if large revenue change, use capital tax
        if abs(rev_fraction) > 0.003:  # >$90B/yr threshold
            # Map to capital tax rate change
            # Each 1pp of capital tax ≈ $60–80B revenue (rough)
            delta_tau_k = rev_fraction / 0.003 * 0.01
            overrides["tau_k"] = float(
                np.clip(p.capital_tax_rate + delta_tau_k, 0.05, 0.60)
            )

        # Outlays proxy: SS expansion
        if abs(avg_outlays) > 0:
            ss_fraction = avg_outlays / max(self._baseline_gdp, 1.0)
            if abs(ss_fraction) > 0.001:
                # Roughly: SS outlays / GDP ≈ 5%; rep rate ≈ 40%
                delta_rep = ss_fraction / 0.05 * p.ss_replacement_rate
                overrides["ss_replacement_rate"] = float(
                    np.clip(p.ss_replacement_rate + delta_rep, 0.0, 0.80)
                )

        return overrides
