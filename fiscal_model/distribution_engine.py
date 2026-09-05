"""
Distributional analysis engine orchestration.
"""

import logging
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
from .distribution_households import (
    HOUSEHOLD,
    SUPPORTED_UNITS,
    TAX_UNIT,
    aggregate_to_households,
    assign_people_weighted_groups,
    build_household_groups,
)
from .policies import Policy

logger = logging.getLogger(__name__)


class DistributionalEngine:
    """
    Engine for computing distributional effects of tax policies.

    ``unit`` selects the universe that is ranked and reported on:

    ``"tax_unit"`` (default)
        CPS tax units ranked by AGI into buckets cut at fixed dollar
        thresholds, averages per return. This is what the TPC and JCT
        return-level tables publish and what every app surface renders.
    ``"household"``
        CBO's universe: households ranked by income before transfers and taxes
        divided by the square root of household size, into groups holding equal
        numbers of people, averages per household. See
        :mod:`fiscal_model.distribution_households` for the published
        definitions this implements.

    The household universe needs the return-level microsimulation — the
    synthetic bracket path aggregates IRS return counts and has no household
    layer — so a household request for a policy the microsim cannot represent
    falls back to the tax-unit path and says so on
    ``DistributionalAnalysis.unit``.
    """

    def __init__(self, data_year: int = 2022, unit: str = TAX_UNIT):
        if unit not in SUPPORTED_UNITS:
            raise ValueError(
                f"Unknown distributional unit {unit!r}; expected one of "
                f"{', '.join(SUPPORTED_UNITS)}."
            )
        self.data_year = data_year
        self.unit = unit
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
        prefer_microsim: bool = True,
        unit: str | None = None,
    ) -> DistributionalAnalysis:
        """Analyze distributional effects of a tax policy.

        When ``prefer_microsim`` is True (default) and the policy can be
        represented as a microsimulation reform, the analysis runs through the
        return-level microsim engine (correct ordinary/preferential rate
        treatment, real SALT modeling, refundable credits). Policies the
        microsim cannot yet represent — or any microsim failure — fall back to
        the synthetic bracket path, which is also used for the offline
        readiness checks.

        ``unit`` overrides the engine's universe for this call; it defaults to
        whatever the engine was constructed with. A ``"household"`` request
        that cannot reach the microsim falls back to the tax-unit synthetic
        path, and the returned analysis records ``unit="tax_unit"`` so the
        caller can tell what it actually got.
        """
        if year is None:
            year = getattr(policy, "start_year", 2025)
        unit = self._resolve_unit(unit)

        if prefer_microsim:
            try:
                from fiscal_model.distribution_effects import policy_to_microsim_reforms

                if policy_to_microsim_reforms(policy, year):
                    return self.analyze_policy_microsim(
                        policy, group_type=group_type, year=year, unit=unit
                    )
            except Exception as exc:
                logger.warning(
                    "Microsim distributional path failed for '%s' (%s); "
                    "falling back to synthetic brackets.",
                    getattr(policy, "name", type(policy).__name__),
                    exc,
                )

        if unit == HOUSEHOLD:
            logger.info(
                "Household universe requested for '%s' but the policy takes the "
                "synthetic bracket path, which ranks IRS return counts and has "
                "no household layer; reporting on tax units.",
                getattr(policy, "name", type(policy).__name__),
            )
        return self._analyze_policy_synthetic(policy, group_type, year)

    def _resolve_unit(self, unit: str | None) -> str:
        """Validate a per-call universe override, defaulting to the engine's."""
        if unit is None:
            return self.unit
        if unit not in SUPPORTED_UNITS:
            raise ValueError(
                f"Unknown distributional unit {unit!r}; expected one of "
                f"{', '.join(SUPPORTED_UNITS)}."
            )
        return unit

    def _analyze_policy_synthetic(
        self,
        policy: Policy,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        year: int | None = None,
    ) -> DistributionalAnalysis:
        """Bracket-aggregate distributional analysis (synthetic population)."""
        if year is None:
            year = getattr(policy, "start_year", 2025)

        logger.info(
            "Distributional analysis: policy='%s' group=%s year=%s",
            getattr(policy, "name", type(policy).__name__),
            group_type.value if hasattr(group_type, "value") else group_type,
            year,
        )

        groups = self.create_income_groups(group_type)
        results = []
        total_tax_change = 0.0
        total_affected = 0

        for group in groups:
            result = dispatch_distributional_effect(
                policy, group, self.total_returns, brackets=self.brackets
            )
            results.append(result)
            total_tax_change += result.tax_change_total
            if result.pct_with_increase > 0 or result.pct_with_decrease > 0:
                total_affected += group.num_returns

        if abs(total_tax_change) > 0.001:
            for result in results:
                result.share_of_total_change = result.tax_change_total / total_tax_change

        logger.info(
            "Distributional analysis complete: total_change=$%.1fB affected=%d",
            total_tax_change,
            total_affected,
        )

        return DistributionalAnalysis(
            policy=policy,
            year=year,
            group_type=group_type,
            results=results,
            total_tax_change=total_tax_change,
            total_affected_returns=total_affected,
            engine="synthetic",
        )

    def analyze_policy_microsim(
        self,
        policy: Policy,
        microdata: pd.DataFrame | None = None,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        year: int | None = None,
        unit: str | None = None,
    ) -> DistributionalAnalysis:
        """Run distributional analysis using microsimulation."""
        from fiscal_model.microsim.engine import MicroTaxCalculator

        if year is None:
            year = getattr(policy, "start_year", 2025)
        unit = self._resolve_unit(unit)

        if microdata is None:
            microdata_path = Path(__file__).parent / "microsim" / "tax_microdata_2024.csv"
            if not microdata_path.exists():
                raise FileNotFoundError(
                    f"Microdata not found at {microdata_path}. "
                    "Please provide microdata or run fiscal_model/microsim/data_builder.py"
                )
            microdata = pd.read_csv(microdata_path)

        # The CPS file lacks deduction detail; impute SALT + itemized so the
        # engine can model SALT-cap policies (no-op if already present).
        from fiscal_model.microsim.salt_imputation import impute_salt_and_itemized

        pop = impute_salt_and_itemized(microdata).copy()
        calc_baseline = MicroTaxCalculator(year=year)
        baseline = calc_baseline.calculate(pop)
        reforms = policy_to_microsim_reforms(policy, year)
        calc_reform = MicroTaxCalculator(year=year)
        reform = calc_reform.apply_reform(pop, reforms)

        merged = baseline.copy()
        merged.loc[:, "reform_tax"] = reform["final_tax"].values
        merged.loc[:, "tax_change"] = merged["reform_tax"] - merged["final_tax"]

        if unit == HOUSEHOLD:
            return self._analyze_households(policy, merged, group_type, year)

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
            engine="microsim",
            unit=TAX_UNIT,
        )

    def _analyze_households(
        self,
        policy: Policy,
        merged: pd.DataFrame,
        group_type: IncomeGroupType,
        year: int,
    ) -> DistributionalAnalysis:
        """Report the microsim result on CBO's household universe.

        Tax units are collapsed to households by ``household_id``, ranked by
        income before transfers and taxes divided by the square root of
        household size, and cut into groups holding equal numbers of people.
        Every dollar reported is unadjusted and per household, and the household
        weight is applied once — at the household — so an average really is an
        average over households.
        """
        households = aggregate_to_households(
            merged,
            sum_columns=("tax_change", "final_tax", "reform_tax"),
        )
        group_index = assign_people_weighted_groups(households, group_type)
        groups = build_household_groups(households, group_index, group_type)

        results: list[DistributionalResult] = []
        total_tax_change = 0.0
        total_affected = 0

        for index, group in enumerate(groups):
            members = households[group_index == index]
            if members.empty:
                results.append(
                    DistributionalResult(
                        income_group=group,
                        pct_unchanged=100.0,
                    )
                )
                continue

            weight = members["household_weight"].values
            weight_sum = weight.sum()
            change = members["tax_change"].values
            weighted_change = float((change * weight).sum())

            # Income before transfers and taxes less the household's baseline
            # federal income tax — the denominator CBO's "percent of income"
            # column is a percent of.
            after_tax = np.maximum(
                members["income_before_transfers_and_taxes"].values
                - members["final_tax"].values,
                1.0,
            )
            after_tax_avg = float((after_tax * weight).sum() / weight_sum)

            increased = float(weight[change > 0.01].sum())
            decreased = float(weight[change < -0.01].sum())
            baseline_income = float(
                (members["income_before_transfers_and_taxes"].values * weight).sum()
            )
            baseline_tax = float((members["final_tax"].values * weight).sum())
            reform_tax = float((members["reform_tax"].values * weight).sum())
            baseline_etr = baseline_tax / baseline_income if baseline_income > 0 else 0.0
            new_etr = reform_tax / baseline_income if baseline_income > 0 else 0.0

            result = DistributionalResult(
                income_group=group,
                tax_change_total=weighted_change / 1e9,
                tax_change_avg=weighted_change / weight_sum,
                tax_change_pct_income=(
                    (weighted_change / weight_sum) / after_tax_avg * 100
                    if after_tax_avg > 0
                    else 0.0
                ),
                share_of_total_change=0.0,
                pct_with_increase=increased / weight_sum * 100,
                pct_with_decrease=decreased / weight_sum * 100,
                pct_unchanged=(weight_sum - increased - decreased) / weight_sum * 100,
                baseline_etr=baseline_etr,
                new_etr=new_etr,
                etr_change=new_etr - baseline_etr,
            )
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
            engine="microsim",
            unit=HOUSEHOLD,
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
            result = dispatch_distributional_effect(
                policy, group, self.total_returns, brackets=self.brackets
            )
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
