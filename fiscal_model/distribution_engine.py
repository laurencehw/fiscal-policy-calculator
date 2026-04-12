"""
Distributional analysis engine orchestration.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .data.irs_soi import IRSSOIData, TaxBracketData
from .distribution_core import (
    DistributionalAnalysis,
    DistributionalResult,
    IncomeGroupType,
)
from .distribution_effects import (
    dispatch_distributional_effect,
    policy_to_microsim_reforms,
)
from .distribution_grouping import (
    aggregate_brackets_into_groups,
    aggregate_top_income_groups,
    create_groups_from_microdata,
    generate_synthetic_brackets,
    get_group_thresholds,
)
from .policies import Policy


class DistributionalEngine:
    """
    Engine for computing distributional effects of tax policies.
    """

    def __init__(self, data_year: int = 2022):
        self.data_year = data_year
        self._irs_data = None
        self._brackets = None
        self._total_returns = None

    @property
    def irs_data(self) -> IRSSOIData:
        """Lazy load IRS data."""
        if self._irs_data is None:
            self._irs_data = IRSSOIData()
        return self._irs_data

    @property
    def brackets(self) -> list[TaxBracketData]:
        """Lazy load bracket data."""
        if self._brackets is None:
            try:
                self._brackets = self.irs_data.get_bracket_distribution(self.data_year)
            except FileNotFoundError:
                self._brackets = generate_synthetic_brackets(self.data_year)
        return self._brackets

    @property
    def total_returns(self) -> int:
        """Total number of tax returns."""
        if self._total_returns is None:
            self._total_returns = sum(bracket.num_returns for bracket in self.brackets)
        return self._total_returns

    def create_income_groups(
        self,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        custom_brackets: list[tuple[float, float | None]] | None = None,
    ):
        """Create income groups by aggregating IRS brackets."""
        thresholds = get_group_thresholds(group_type, custom_brackets)
        return aggregate_brackets_into_groups(self.brackets, thresholds, self.total_returns)

    def analyze_policy(
        self,
        policy: Policy,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        year: int | None = None,
    ) -> DistributionalAnalysis:
        """Analyze distributional effects of a tax policy."""
        if year is None:
            year = getattr(policy, "start_year", 2025)

        groups = self.create_income_groups(group_type)
        results = []
        total_tax_change = 0.0
        total_affected = 0

        for group in groups:
            result = dispatch_distributional_effect(policy, group, self.total_returns)
            results.append(result)
            total_tax_change += result.tax_change_total
            if result.pct_with_increase > 0 or result.pct_with_decrease > 0:
                total_affected += group.num_returns

        if abs(total_tax_change) > 0.001:
            for result in results:
                result.share_of_total_change = result.tax_change_total / total_tax_change

        return DistributionalAnalysis(
            policy=policy,
            year=year,
            group_type=group_type,
            results=results,
            total_tax_change=total_tax_change,
            total_affected_returns=total_affected,
        )

    def analyze_policy_microsim(
        self,
        policy: Policy,
        microdata: pd.DataFrame | None = None,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        year: int | None = None,
    ) -> DistributionalAnalysis:
        """Run distributional analysis using microsimulation."""
        from fiscal_model.microsim.engine import MicroTaxCalculator

        if year is None:
            year = getattr(policy, "start_year", 2025)

        if microdata is None:
            microdata_path = Path(__file__).parent / "microsim" / "tax_microdata_2024.csv"
            if not microdata_path.exists():
                raise FileNotFoundError(
                    f"Microdata not found at {microdata_path}. "
                    "Please provide microdata or run fiscal_model/microsim/data_builder.py"
                )
            microdata = pd.read_csv(microdata_path)

        pop = microdata.copy()
        calc_baseline = MicroTaxCalculator(year=year)
        baseline = calc_baseline.calculate(pop)
        reforms = policy_to_microsim_reforms(policy, year)
        calc_reform = MicroTaxCalculator(year=year)
        reform = calc_reform.apply_reform(pop, reforms)

        merged = baseline.copy()
        merged.loc[:, "reform_tax"] = reform["final_tax"].values
        merged.loc[:, "tax_change"] = merged["reform_tax"] - merged["final_tax"]

        groups = create_groups_from_microdata(merged, group_type)
        results = []
        total_tax_change = 0.0
        total_affected = 0

        for group in groups:
            in_group = (merged["agi"] >= group.floor) & (
                (merged["agi"] < group.ceiling) if group.ceiling else (merged["agi"] >= group.floor)
            )
            group_data = merged[in_group]

            if len(group_data) == 0:
                result = DistributionalResult(
                    income_group=group,
                    tax_change_total=0.0,
                    tax_change_avg=0.0,
                    tax_change_pct_income=0.0,
                    share_of_total_change=0.0,
                    pct_with_increase=0.0,
                    pct_with_decrease=0.0,
                    pct_unchanged=100.0,
                    baseline_etr=0.0,
                    new_etr=0.0,
                    etr_change=0.0,
                )
            else:
                weights = group_data.get("weight", pd.Series(1.0, index=group_data.index)).values
                total_weight = weights.sum()
                tax_changes = group_data["tax_change"].values
                weighted_tax_change_total = (tax_changes * weights).sum() / 1e9
                weighted_tax_change_avg = (
                    (tax_changes * weights).sum() / total_weight if total_weight > 0 else 0
                )

                aftertax_income = group_data["agi"].values - group_data["final_tax"].values
                aftertax_income = np.maximum(aftertax_income, 1)
                tax_change_pct_income = (
                    (weighted_tax_change_avg / aftertax_income.mean()) * 100
                    if aftertax_income.mean() > 0
                    else 0
                )

                num_increase = (tax_changes > 0.01).sum()
                num_decrease = (tax_changes < -0.01).sum()
                num_unchanged = len(tax_changes) - num_increase - num_decrease
                pct_with_increase = (num_increase / len(tax_changes) * 100) if len(tax_changes) > 0 else 0
                pct_with_decrease = (num_decrease / len(tax_changes) * 100) if len(tax_changes) > 0 else 0
                pct_unchanged = (num_unchanged / len(tax_changes) * 100) if len(tax_changes) > 0 else 100

                baseline_tax = group_data["final_tax"].values
                baseline_agi = group_data["agi"].values
                baseline_etr = (baseline_tax.sum() / baseline_agi.sum()) if baseline_agi.sum() > 0 else 0
                reform_tax = group_data["reform_tax"].values
                new_etr = (reform_tax.sum() / baseline_agi.sum()) if baseline_agi.sum() > 0 else 0

                result = DistributionalResult(
                    income_group=group,
                    tax_change_total=weighted_tax_change_total,
                    tax_change_avg=weighted_tax_change_avg,
                    tax_change_pct_income=tax_change_pct_income,
                    share_of_total_change=0.0,
                    pct_with_increase=pct_with_increase,
                    pct_with_decrease=pct_with_decrease,
                    pct_unchanged=pct_unchanged,
                    baseline_etr=baseline_etr,
                    new_etr=new_etr,
                    etr_change=new_etr - baseline_etr,
                )

            results.append(result)
            total_tax_change += result.tax_change_total
            if result.pct_with_increase > 0 or result.pct_with_decrease > 0:
                total_affected += result.income_group.num_returns

        if abs(total_tax_change) > 0.001:
            for result in results:
                result.share_of_total_change = (
                    result.tax_change_total / total_tax_change if total_tax_change != 0 else 0.0
                )

        return DistributionalAnalysis(
            policy=policy,
            year=year,
            group_type=group_type,
            results=results,
            total_tax_change=total_tax_change,
            total_affected_returns=total_affected,
        )

    def create_top_income_breakout(
        self,
        policy: Policy,
        year: int | None = None,
    ) -> DistributionalAnalysis:
        """Create detailed breakout for top income groups."""
        groups = aggregate_top_income_groups(self.brackets, self.total_returns)

        if year is None:
            year = getattr(policy, "start_year", 2025)

        results = []
        total_tax_change = 0.0

        for group in groups:
            result = dispatch_distributional_effect(policy, group, self.total_returns)
            results.append(result)
            total_tax_change += result.tax_change_total

        if abs(total_tax_change) > 0.001:
            for result in results:
                result.share_of_total_change = result.tax_change_total / total_tax_change

        return DistributionalAnalysis(
            policy=policy,
            year=year,
            group_type=IncomeGroupType.CUSTOM,
            results=results,
            total_tax_change=total_tax_change,
            total_affected_returns=sum(group.num_returns for group in groups),
        )
