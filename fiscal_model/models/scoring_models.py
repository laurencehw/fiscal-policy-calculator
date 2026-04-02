"""
Concrete scoring model implementations for multi-model comparison.

Wraps the existing FiscalPolicyScorer and MacroModelAdapter infrastructure
into the BaseScoringModel interface for side-by-side comparison.
"""

from __future__ import annotations

import numpy as np

from fiscal_model.policies import Policy
from fiscal_model.scoring import FiscalPolicyScorer

from .base import BaseScoringModel, ModelComparison, ModelResult


class CBOConventionalModel(BaseScoringModel):
    """
    CBO-style conventional scoring (static + behavioral ETI offset).

    This is the standard scoring methodology: compute the static revenue
    effect, then apply the elasticity of taxable income (ETI) to estimate
    behavioral response. No macroeconomic feedback.
    """

    def __init__(self, use_real_data: bool = True):
        self._scorer = FiscalPolicyScorer(use_real_data=use_real_data)

    @property
    def name(self) -> str:
        return "CBO Conventional"

    @property
    def methodology(self) -> str:
        return "Static revenue + behavioral offset (ETI=0.25). No macro feedback."

    def score(self, policy: Policy) -> ModelResult:
        result = self._scorer.score_policy(policy, dynamic=False)
        return ModelResult(
            model_name=self.name,
            methodology=self.methodology,
            ten_year_cost=result.total_10_year_cost,
            annual_effects=result.final_deficit_effect.copy(),
            low_estimate=np.sum(result.low_estimate),
            high_estimate=np.sum(result.high_estimate),
        )

    def get_assumptions(self) -> dict:
        return {
            "scoring_type": "conventional",
            "eti": 0.25,
            "dynamic": False,
            "baseline_vintage": "CBO Feb 2026",
        }


class DynamicScoringModel(BaseScoringModel):
    """
    Dynamic scoring with macroeconomic feedback.

    Extends conventional scoring with GDP, employment, and interest rate
    effects via EconomicModel (condition-adjusted multipliers). Revenue
    feedback from GDP growth partially offsets the static cost.
    """

    def __init__(self, use_real_data: bool = True):
        self._scorer = FiscalPolicyScorer(use_real_data=use_real_data)

    @property
    def name(self) -> str:
        return "CBO Dynamic"

    @property
    def methodology(self) -> str:
        return (
            "Static + behavioral + macro feedback. "
            "EconomicModel with condition-adjusted multipliers "
            "(spending=1.0, tax=0.5 in normal times)."
        )

    def score(self, policy: Policy) -> ModelResult:
        result = self._scorer.score_policy(policy, dynamic=True)
        gdp_pct = 0.0
        employment = 0.0
        if result.dynamic_effects is not None:
            gdp_pct = float(np.mean(result.dynamic_effects.gdp_percent_change))
            employment = float(np.mean(result.dynamic_effects.employment_change))

        return ModelResult(
            model_name=self.name,
            methodology=self.methodology,
            ten_year_cost=result.total_10_year_cost,
            annual_effects=result.final_deficit_effect.copy(),
            low_estimate=np.sum(result.low_estimate),
            high_estimate=np.sum(result.high_estimate),
            gdp_effect_pct=gdp_pct,
            employment_effect_thousands=employment,
            extras={
                "revenue_feedback_10yr": result.revenue_feedback_10yr,
            },
        )

    def get_assumptions(self) -> dict:
        # Pull actual parameters from the scorer's economic model
        params = self._scorer.economic_model.params
        return {
            "scoring_type": "dynamic",
            "eti": params.get("eti", 0.25),
            "dynamic": True,
            "spending_multiplier": params.get("spending_multiplier_peak", 1.0),
            "tax_multiplier": params.get("tax_multiplier", 0.5),
            "multiplier_decay": params.get("spending_multiplier_decay", 0.7),
            "crowding_out": params.get("crowding_out", 0.03),
            "marginal_revenue_rate": params.get("marginal_revenue_rate", 0.25),
        }


class MicrosimScoringModel(BaseScoringModel):
    """
    Microsimulation-based scoring using CPS microdata.

    Runs the MicroTaxCalculator on all 56K CPS ASEC tax units under
    baseline and reform scenarios, computing the weighted tax change
    at the individual level. This captures phase-outs, cliffs, AMT,
    SALT cap, and EITC/CTC interactions that aggregate models miss.

    Requires a TaxPolicy with rate_change and affected_income_threshold.
    """

    def __init__(self):
        from fiscal_model.microsim.cps_auto_populator import CPSAutoPopulator
        from fiscal_model.microsim.engine import MicroTaxCalculator

        self._calc = MicroTaxCalculator(year=2025)
        self._cps = CPSAutoPopulator()
        self._pop_df = self._cps._df.copy()  # Reuse already-loaded CPS data

    @property
    def name(self) -> str:
        return "Microsimulation (CPS)"

    @property
    def methodology(self) -> str:
        return (
            "Individual-level tax calculation on 56K CPS ASEC units. "
            "Captures phase-outs, AMT, SALT cap, EITC/CTC interactions."
        )

    def score(self, policy: Policy) -> ModelResult:
        from fiscal_model.microsim.engine import MicroTaxCalculator

        # Validate required policy attributes
        if not hasattr(policy, "rate_change") or not hasattr(policy, "affected_income_threshold"):
            raise ValueError(
                f"MicrosimScoringModel requires a TaxPolicy with rate_change and "
                f"affected_income_threshold, got {type(policy).__name__}"
            )

        rate_change = float(policy.rate_change)
        threshold = float(policy.affected_income_threshold)

        # 1. Baseline tax: compute tax for all records under current law
        baseline_df = self._calc.calculate(self._pop_df)

        # 2. Reform tax: apply rate change to affected brackets
        if rate_change != 0:
            reform_calc = MicroTaxCalculator(year=2025)

            # Shift bracket rates for income above threshold
            for i, bracket_floor in enumerate(reform_calc.brackets_mfj):
                if bracket_floor >= threshold:
                    reform_calc.rates_mfj[i] = min(1.0, max(0.0, reform_calc.rates_mfj[i] + rate_change))
            for i, bracket_floor in enumerate(reform_calc.brackets_single):
                if bracket_floor >= threshold:
                    reform_calc.rates_single[i] = min(1.0, max(0.0, reform_calc.rates_single[i] + rate_change))

            reform_df = reform_calc.calculate(self._pop_df)
        else:
            reform_df = baseline_df

        # 3. Compute weighted tax change per individual
        weights = baseline_df["weight"].values
        tax_change = reform_df["final_tax"].values - baseline_df["final_tax"].values

        # Weighted annual revenue change (positive = more revenue)
        annual_revenue_change = (tax_change * weights).sum() / 1e9

        # Apply growth (~4% nominal) over 10-year window
        annual_effects_revenue = np.array([annual_revenue_change * (1.04 ** i) for i in range(10)])
        deficit_effects = -annual_effects_revenue  # Negative revenue = positive deficit

        ten_year = float(np.sum(deficit_effects))

        # Count affected filers
        n_affected = int(((baseline_df["taxable_income"] >= threshold) * weights).sum()) if threshold > 0 else int(weights.sum())

        return ModelResult(
            model_name=self.name,
            methodology=self.methodology,
            ten_year_cost=ten_year,
            annual_effects=deficit_effects,
            low_estimate=ten_year * 0.85,
            high_estimate=ten_year * 1.15,
            extras={
                "affected_filers": n_affected,
                "affected_filers_millions": n_affected / 1e6,
                "avg_tax_change": float((tax_change * weights).sum() / weights.sum()),
                "data_source": "CPS ASEC 2024",
                "tax_units": len(baseline_df),
            },
        )

    def get_assumptions(self) -> dict:
        return {
            "scoring_type": "microsimulation",
            "data_source": "CPS ASEC 2024",
            "tax_units": len(self._pop_df),
            "captures": ["phase-outs", "AMT", "SALT cap", "EITC/CTC"],
            "growth_rate": 0.04,
        }


def compare_models(
    policy: Policy,
    models: list[BaseScoringModel] | None = None,
    use_real_data: bool = True,
) -> ModelComparison:
    """
    Run the same policy through multiple scoring models and compare.

    Args:
        policy: Policy to score
        models: List of models to use (default: CBO conventional + dynamic)
        use_real_data: Whether to use real IRS/CPS data

    Returns:
        ModelComparison with side-by-side results

    Example:
        >>> from fiscal_model.tcja import create_tcja_extension
        >>> comparison = compare_models(create_tcja_extension())
        >>> print(comparison.to_dataframe())
        >>> print(comparison.explain_divergence())
    """
    if models is None:
        models = [
            CBOConventionalModel(use_real_data=use_real_data),
            DynamicScoringModel(use_real_data=use_real_data),
        ]

    comparison = ModelComparison(policy_name=policy.name)
    for model in models:
        result = model.score(policy)
        comparison.results.append(result)

    return comparison
