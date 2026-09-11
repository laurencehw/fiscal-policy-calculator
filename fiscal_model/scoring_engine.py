"""
Fiscal policy scoring engine.
"""

import logging
from collections.abc import Callable

import numpy as np

from .amt import AMTPolicy
from .baseline import BaselineProjection, CBOBaseline
from .constants import (
    ASYMMETRY_HIGH,
    ASYMMETRY_LOW,
    BASE_UNCERTAINTY,
    DYNAMIC_UNCERTAINTY_FACTOR,
    SPENDING_UNCERTAINTY_FACTOR,
    TAX_UNCERTAINTY_FACTOR,
    UNCERTAINTY_GROWTH_PER_YEAR,
)
from .corporate import CorporateTaxPolicy
from .credits import TaxCreditPolicy
from .economics import DynamicEffects, EconomicModel
from .estate import EstateTaxPolicy
from .payroll import PayrollTaxPolicy
from .policies import (
    CapitalGainsPolicy,
    Policy,
    PolicyPackage,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
)
from .ptc import PremiumTaxCreditPolicy
from .scoring_result import ScoringResult
from .tax_expenditures import TaxExpenditurePolicy
from .tcja import TCJAExtensionPolicy

logger = logging.getLogger(__name__)


class FiscalPolicyScorer:
    """
    Main scoring engine for fiscal policy analysis.
    """

    def __init__(
        self,
        baseline: BaselineProjection | None = None,
        start_year: int = 2025,
        use_real_data: bool = True,
    ):
        self.start_year = start_year
        self.use_real_data = use_real_data

        if baseline is None:
            generator = CBOBaseline(start_year=start_year, use_real_data=use_real_data)
            self.baseline = generator.generate()
        else:
            self.baseline = baseline

        self.economic_model = EconomicModel(self.baseline)
        self._policy_handlers: tuple[
            tuple[type[Policy], Callable[[Policy, int], tuple[np.ndarray, np.ndarray, np.ndarray]]],
            ...,
        ] = (
            (TaxPolicy, self._score_tax_policy_branch),
            (SpendingPolicy, self._score_spending_policy_branch),
            (TransferPolicy, self._score_transfer_policy_branch),
        )
        self._growth_tax_policy_handlers: tuple[tuple[type[TaxPolicy], float, bool], ...] = (
            (CorporateTaxPolicy, 0.04, True),
            (TaxCreditPolicy, 0.03, False),
            (EstateTaxPolicy, 0.03, False),
            (PayrollTaxPolicy, 0.04, False),
            (AMTPolicy, 0.03, False),
            (PremiumTaxCreditPolicy, 0.04, False),
            (TaxExpenditurePolicy, -1.0, False),
        )

    def _score_tax_policy_branch(
        self,
        policy: Policy,
        n_years: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        tax_policy = policy
        if not isinstance(tax_policy, TaxPolicy):
            raise TypeError(f"Expected TaxPolicy, got {type(policy).__name__}")
        static_revenue, behavioral = self._score_tax_policy(tax_policy)
        return static_revenue, np.zeros(n_years), behavioral

    def _score_spending_policy_branch(
        self,
        policy: Policy,
        n_years: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        spending_policy = policy
        if not isinstance(spending_policy, SpendingPolicy):
            raise TypeError(f"Expected SpendingPolicy, got {type(policy).__name__}")
        return np.zeros(n_years), self._score_spending_policy(spending_policy), np.zeros(n_years)

    def _score_transfer_policy_branch(
        self,
        policy: Policy,
        n_years: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        transfer_policy = policy
        if not isinstance(transfer_policy, TransferPolicy):
            raise TypeError(f"Expected TransferPolicy, got {type(policy).__name__}")
        return np.zeros(n_years), self._score_transfer_policy(transfer_policy), np.zeros(n_years)

    def _score_cost_estimate_policy_branch(
        self,
        policy: Policy,
        n_years: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not hasattr(policy, "estimate_cost_effect"):
            raise TypeError(
                f"Unsupported policy type '{type(policy).__name__}'. "
                "Expected TaxPolicy, SpendingPolicy, TransferPolicy, or a policy "
                "implementing estimate_cost_effect()."
            )

        spending = np.zeros(n_years)
        for idx, year in enumerate(self.baseline.years):
            if hasattr(policy, "is_active") and not policy.is_active(year):
                continue

            phase = 1.0
            if hasattr(policy, "get_phase_in_factor"):
                phase = policy.get_phase_in_factor(year)
            spending[idx] = policy.estimate_cost_effect(0.0) * phase

        return np.zeros(n_years), spending, np.zeros(n_years)

    def score_policy(
        self,
        policy: Policy,
        dynamic: bool = False,
        include_uncertainty: bool = True,
    ) -> ScoringResult:
        """Score a fiscal policy proposal."""
        logger.info("Scoring policy '%s' (dynamic=%s)", policy.name, dynamic)

        years = self.baseline.years
        n_years = len(years)
        static_revenue = np.zeros(n_years)
        static_spending = np.zeros(n_years)
        behavioral = np.zeros(n_years)

        handler_used = False
        for policy_cls, handler in self._policy_handlers:
            if isinstance(policy, policy_cls):
                static_revenue, static_spending, behavioral = handler(policy, n_years)
                handler_used = True
                break

        if not handler_used:
            static_revenue, static_spending, behavioral = self._score_cost_estimate_policy_branch(
                policy,
                n_years,
            )

        static_deficit = static_spending - static_revenue
        deficit_after_behavioral = static_deficit + behavioral

        dynamic_effects = None
        if dynamic:
            dynamic_effects = self.economic_model.calculate_effects(
                policy,
                deficit_after_behavioral,
            )
            final_deficit = deficit_after_behavioral - dynamic_effects.revenue_feedback
        else:
            final_deficit = deficit_after_behavioral

        if include_uncertainty:
            low, high = self._calculate_uncertainty(policy, final_deficit, dynamic_effects)
        else:
            low = final_deficit.copy()
            high = final_deficit.copy()

        if isinstance(policy, SpendingPolicy):
            budget_authority = self._score_spending_authority(policy)
        else:
            budget_authority = static_spending.copy()

        result = ScoringResult(
            policy=policy,
            baseline=self.baseline,
            years=years,
            static_revenue_effect=static_revenue,
            static_spending_effect=static_spending,
            static_deficit_effect=static_deficit,
            behavioral_offset=behavioral,
            budget_authority_effect=budget_authority,
            dynamic_effects=dynamic_effects,
            final_deficit_effect=final_deficit,
            low_estimate=low,
            high_estimate=high,
        )

        if np.allclose(result.total_10_year_cost, 0.0, atol=0.1):
            logger.warning(
                "Policy '%s' scored with near-zero 10-year cost (%.1fB). "
                "Check that income threshold includes affected taxpayers.",
                policy.name,
                result.total_10_year_cost,
            )

        logger.info("Policy '%s': 10yr cost $%.1fB", policy.name, result.total_10_year_cost)
        return result

    def score_package(self, package: PolicyPackage, dynamic: bool = False) -> ScoringResult:
        """Score a package of policies together."""
        logger.info("Scoring package with %d policies", len(package.policies))
        results = [self.score_policy(policy, dynamic=dynamic) for policy in package.policies]
        n_years = len(self.baseline.years)
        total_static_revenue = np.zeros(n_years)
        total_static_spending = np.zeros(n_years)
        total_behavioral = np.zeros(n_years)
        total_budget_authority = np.zeros(n_years)

        for result in results:
            total_static_revenue += result.static_revenue_effect
            total_static_spending += result.static_spending_effect
            total_behavioral += result.behavioral_offset
            total_budget_authority += result.budget_authority_effect

        total_static_revenue *= package.interaction_factor
        total_static_spending *= package.interaction_factor
        total_budget_authority *= package.interaction_factor
        static_deficit = total_static_spending - total_static_revenue
        deficit_after_behavioral = static_deficit + total_behavioral

        if dynamic:
            combined_dynamic = self._aggregate_dynamic_effects(results)
            final_deficit = deficit_after_behavioral - combined_dynamic.revenue_feedback
        else:
            combined_dynamic = None
            final_deficit = deficit_after_behavioral

        low, high = self._calculate_uncertainty(
            package.policies[0],
            final_deficit,
            combined_dynamic,
        )

        synthetic = Policy(
            name=package.name,
            description=package.description,
            policy_type=PolicyType.MANDATORY_SPENDING,
            start_year=min(policy.start_year for policy in package.policies),
        )

        return ScoringResult(
            policy=synthetic,
            baseline=self.baseline,
            years=self.baseline.years,
            static_revenue_effect=total_static_revenue,
            static_spending_effect=total_static_spending,
            static_deficit_effect=static_deficit,
            behavioral_offset=total_behavioral,
            budget_authority_effect=total_budget_authority,
            dynamic_effects=combined_dynamic,
            final_deficit_effect=final_deficit,
            low_estimate=low,
            high_estimate=high,
        )

    def _score_tax_policy(self, policy: TaxPolicy) -> tuple[np.ndarray, np.ndarray]:
        """Calculate static revenue effect and behavioral offset for tax policy."""
        n_years = len(self.baseline.years)
        revenue = np.zeros(n_years)
        behavioral = np.zeros(n_years)

        for idx, year in enumerate(self.baseline.years):
            if not policy.is_active(year):
                continue

            phase = policy.get_phase_in_factor(year)

            if isinstance(policy, TCJAExtensionPolicy):
                years_since_start = year - policy.start_year
                annual_cost = policy._get_annual_cost(years_since_start)
                revenue[idx] = -annual_cost * phase
                behavioral[idx] = 0.0
                continue

            growth_scored = self._score_growth_tax_policy_year(
                policy=policy,
                year=year,
                baseline_index=idx,
                phase=phase,
            )
            if growth_scored is not None:
                revenue[idx], behavioral[idx] = growth_scored
                continue

            base_rev = self._get_baseline_revenue_for_tax_policy(policy=policy, baseline_index=idx)
            if policy.scores_by_year():
                # The answer genuinely differs by year: a realizations base that
                # is a flow off a projected stock (CapitalGainsPolicy), or a
                # threshold the law re-indexes against the base it is measured
                # above (a TaxPolicy with threshold_indexation != "income").
                # Asked of the policy rather than of its type since the schedule
                # lane needed a second case here - see Policy.scores_by_year()
                # and MODELING_IMPROVEMENT.md section 6.2 item 27.
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                    year=year,
                    threshold_deflator=self._threshold_deflator(policy, year),
                )
            else:
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                )
            # The generic base is a dated SOI aggregate and the window prices
            # ten later years, so it is projected onto the year being scored -
            # the same reason the branches above ask for a year. 1.0 for every
            # base this policy did not read from SOI, which includes every
            # capital-gains policy: that class projects its own base and never
            # sets ``soi_base_tax_year``.
            static_annual *= self._income_base_projection_factor(policy, year)
            revenue[idx] = static_annual * phase

            if isinstance(policy, CapitalGainsPolicy):
                years_since_start = year - policy.start_year
                if policy.eliminate_step_up:
                    # Gains transferred at death are indexed to the asset
                    # stock, so this grows across the window rather than
                    # repeating one constant.
                    step_up_revenue = policy.estimate_step_up_elimination_revenue(
                        years_since_start
                    )
                    revenue[idx] += step_up_revenue * phase
                behavioral[idx] = policy.estimate_behavioral_offset(
                    revenue[idx],
                    years_since_start,
                    use_real_data=self.use_real_data,
                    phase=phase,
                )
            else:
                behavioral[idx] = policy.estimate_behavioral_offset(revenue[idx])

        return revenue, behavioral

    def _income_base_projection_factor(self, policy: TaxPolicy, year: int) -> float:
        """Growth of the generic income-tax base from its SOI year to ``year``.

        IRS SOI Table 1.1 reports filer counts and average taxable income for a
        **tax year**; a ten-year score prices ten later years. Held flat, the
        generic path returned one annual ten times - ``yr1 == yr10`` to the cent
        on every shape - which answers a FY2026-2035 question with a TY2023
        base, 35.6% below what this vintage's own nominal path projects across
        that window on average.

        The factor is the ratio of the **scored baseline's own** nominal income
        index between the two years
        (:meth:`fiscal_model.baseline.BaselineProjection.nominal_income_index`),
        so it is the vintage's, not a constant: the CBO Options battery scores
        on February 2024 and takes 1.3118 on FY2025-2034, the app scores on
        February 2026 and takes 1.3560 on FY2026-2035. Nothing fitted is read
        and no new figure enters - the index is each vintage's own transcribed
        ``real_gdp_growth + inflation``, and only ratios of it are used, so its
        level cancels.

        Nominal GDP rather than CBO's wages-and-salaries path for two reasons,
        both in ``planning/lanes/HSB_h2_base_growth.md`` section 1.3: only GDP
        is transcribed for all three vintages, and the base being projected is
        taxable income, of which wages are a shrinking share as the threshold
        rises. Measured on the one vintage where both exist the choice is worth
        **0.35%** on the window mean, so the mechanism does not turn on it.

        Returns ``1.0`` - no projection - for every base this policy did not
        read from SOI, and for a baseline carrying no GDP path at all.
        """
        soi_year = getattr(policy, "soi_base_tax_year", None)
        if soi_year is None:
            return 1.0
        return self._nominal_income_ratio(int(soi_year), year)

    def _nominal_income_ratio(self, from_year: int, to_year: int) -> float:
        """This baseline's own nominal-income index between two years, or 1.0.

        The one place the ratio is formed, so the base projection and the
        threshold deflator cannot drift apart - they are the two halves of one
        unit conversion and a discrepancy between them would be silent.
        """
        anchor = self.baseline.nominal_income_index(int(from_year))
        if anchor <= 0:
            return 1.0
        scored = self.baseline.nominal_income_index(int(to_year))
        if scored <= 0:
            return 1.0
        return float(scored / anchor)

    def _threshold_deflator(self, policy: TaxPolicy, year: int) -> float:
        """Converts a threshold stated in ``year``'s dollars into SOI-year dollars.

        The *same* ratio :meth:`_income_base_projection_factor` multiplies the
        annual by, which is what makes the pair a unit conversion rather than
        two growth terms. A threshold ``T`` in year-``t`` dollars against a base
        measured in SOI-year dollars and then grown by ``g`` is
        ``g · Σ max(0, y − T/g)``, and dropping the ``/g`` compares a 2031
        boundary to a 2023 income.

        Returns ``1.0`` - no deflation - for every policy whose threshold is not
        re-indexed, which is every policy by default, and for a baseline
        carrying no GDP path at all. Resolved **before** the first SOI read
        rather than after it, because the first scored year needs the ratio too.
        """
        if not policy.reindexes_threshold():
            return 1.0
        soi_year = policy.resolve_soi_base_tax_year()
        if soi_year is None:
            return 1.0
        return self._nominal_income_ratio(int(soi_year), year)

    def _score_growth_tax_policy_year(
        self,
        policy: TaxPolicy,
        year: int,
        baseline_index: int,
        phase: float,
    ) -> tuple[float, float] | None:
        years_since_start = year - policy.start_year

        for policy_cls, growth_rate, use_corporate_base in self._growth_tax_policy_handlers:
            if not isinstance(policy, policy_cls):
                continue

            base_rev = self.baseline.corporate_income_tax[baseline_index] if use_corporate_base else 0.0

            if isinstance(policy, TaxExpenditurePolicy):
                # A cap's bite is a function of the year: the limit and the
                # quantity it limits grow at different rates, so the share of
                # the base above the limit has to be asked for in the year
                # being scored rather than once at start_year. The level still
                # grows at the expenditure's own rate below; only the share is
                # year-indexed here.
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                    year=year,
                )
                growth_rate = policy.get_expenditure_data().get("growth_rate", 0.03)
            elif isinstance(policy, PayrollTaxPolicy) and policy.uses_covered_earnings_base():
                # A new flat tax on covered earnings is priced off CBO's own
                # baseline wage path, which already grows, and its first year
                # carries the share of the fiscal year the stated effective
                # month covers. So the year is asked for and the module-default
                # 4%/yr is switched off rather than compounded on top.
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                    year=year,
                )
                growth_rate = 0.0
            elif (
                isinstance(policy, PremiumTaxCreditPolicy)
                and policy.uses_baseline_credit_path()
            ):
                # Repealing section 36B removes CBO's own projection of the
                # credit, which is an annual path rather than a level, and it is
                # not a smooth one: the ARPA/IRA enhancement lapsed at the end of
                # calendar 2025, so the February 2026 vintage falls from $105B in
                # FY2026 to $74B in FY2028. So the year is asked for and the
                # module-default 4%/yr is switched off rather than compounded on
                # top of a path that already carries CBO's own growth.
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                    year=year,
                )
                growth_rate = 0.0
            elif isinstance(policy, CorporateTaxPolicy) and policy.uses_projected_base():
                # The derived rate channel is priced off CBO's own projected
                # corporate receipts path, which already grows — at 1.4%/yr on
                # the February 2024 vintage, against the 4%/yr the module used
                # to age SOI's base at. So the year is asked for and the
                # module-default growth is switched off rather than compounded
                # on top. The policy grows its four non-rate constants itself,
                # since they are annual levels rather than a path.
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                    year=year,
                )
                growth_rate = 0.0
            else:
                static_annual = policy.estimate_static_revenue_effect(
                    base_rev,
                    use_real_data=self.use_real_data,
                )

            if isinstance(policy, TaxCreditPolicy) and policy.uses_window_average_annual():
                # Covers both a fitted annual and the derived CPS path, which
                # averages over the window itself.
                growth_rate = 0.0
            elif (
                isinstance(policy, (EstateTaxPolicy, PayrollTaxPolicy))
                and getattr(policy, "annual_revenue_change_billions", None) is not None
            ):
                # Explicit annual figures are window-average calibrations
                # (e.g. Treasury $450B / 10yr → $45B/yr for Biden estate reform;
                # Trustees $2.7T / 10yr → $270B/yr for the SS donut).
                # Growing them again was the main estate (~10%) and payroll
                # (12.2%) residual.
                growth_rate = 0.0

            growth_factor = (1 + growth_rate) ** years_since_start
            annual_revenue = static_annual * growth_factor * phase
            annual_behavioral = policy.estimate_behavioral_offset(annual_revenue)
            return annual_revenue, annual_behavioral

        return None

    def _get_baseline_revenue_for_tax_policy(self, policy: TaxPolicy, baseline_index: int) -> float:
        if policy.policy_type == PolicyType.INCOME_TAX:
            return self.baseline.individual_income_tax[baseline_index]
        if policy.policy_type == PolicyType.CORPORATE_TAX:
            return self.baseline.corporate_income_tax[baseline_index]
        if policy.policy_type == PolicyType.PAYROLL_TAX:
            return self.baseline.payroll_taxes[baseline_index]
        if policy.policy_type == PolicyType.CAPITAL_GAINS_TAX:
            return 0.0
        return self.baseline.individual_income_tax[baseline_index]

    def _score_spending_policy(self, policy: SpendingPolicy) -> np.ndarray:
        """Outlays for a spending policy - the quantity that hits the deficit.

        Budget authority is spent out over the years the account's profile
        implies (:mod:`fiscal_model.spending_outlays`); under the default
        ``immediate`` class the two coincide.

        The window truncates the *tail*, not the head: authority whose outlays
        fall past the end of the projection is dropped (the within-window
        truncation official 10-year totals embed), but a policy that began
        before the window still spends its earlier authority out into it,
        because that authority is a fact about the policy and not about where
        the projection happens to start.
        """
        n_years = len(self.baseline.years)
        spending = np.zeros(n_years)

        for idx, year in enumerate(self.baseline.years):
            spending[idx] = policy.get_outlays_in_year(year)

        return spending

    def _score_spending_authority(self, policy: SpendingPolicy) -> np.ndarray:
        """Budget authority a spending policy provides or withdraws, by year."""
        n_years = len(self.baseline.years)
        authority = np.zeros(n_years)

        for idx, year in enumerate(self.baseline.years):
            authority[idx] = policy.get_budget_authority_in_year(year)

        return authority

    def _score_transfer_policy(self, policy: TransferPolicy) -> np.ndarray:
        """Calculate static cost effect for transfer policy."""
        n_years = len(self.baseline.years)
        cost = np.zeros(n_years)

        for idx, year in enumerate(self.baseline.years):
            if not policy.is_active(year):
                continue

            phase = policy.get_phase_in_factor(year)
            if policy.policy_type == PolicyType.SOCIAL_SECURITY:
                base_cost = self.baseline.social_security[idx]
            elif policy.policy_type == PolicyType.MEDICARE:
                base_cost = self.baseline.medicare[idx]
            elif policy.policy_type == PolicyType.MEDICAID:
                base_cost = self.baseline.medicaid[idx]
            else:
                base_cost = self.baseline.other_mandatory[idx]

            cost[idx] = policy.estimate_cost_effect(base_cost) * phase

        return cost

    def _aggregate_dynamic_effects(self, results: list[ScoringResult]) -> DynamicEffects:
        """Aggregate dynamic effects from multiple policies."""
        n_years = len(self.baseline.years)
        gdp_level = np.zeros(n_years)
        gdp_pct = np.zeros(n_years)
        employment = np.zeros(n_years)
        revenue_fb = np.zeros(n_years)

        for result in results:
            if result.dynamic_effects:
                gdp_level += result.dynamic_effects.gdp_level_change
                gdp_pct += result.dynamic_effects.gdp_percent_change
                employment += result.dynamic_effects.employment_change
                revenue_fb += result.dynamic_effects.revenue_feedback

        return DynamicEffects(
            years=self.baseline.years.copy(),
            gdp_level_change=gdp_level,
            gdp_percent_change=gdp_pct,
            employment_change=employment,
            hours_worked_change=np.zeros(n_years),
            labor_force_change=np.zeros(n_years),
            capital_stock_change=np.zeros(n_years),
            investment_change=np.zeros(n_years),
            interest_rate_change=np.zeros(n_years),
            revenue_feedback=revenue_fb,
        )

    def _calculate_uncertainty(
        self,
        policy: Policy,
        central: np.ndarray,
        dynamic: DynamicEffects | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Calculate uncertainty ranges."""
        n_years = len(central)
        base_uncertainty = np.array(
            [BASE_UNCERTAINTY + UNCERTAINTY_GROWTH_PER_YEAR * idx for idx in range(n_years)]
        )

        if isinstance(policy, TaxPolicy):
            policy_factor = TAX_UNCERTAINTY_FACTOR
        elif isinstance(policy, SpendingPolicy):
            policy_factor = SPENDING_UNCERTAINTY_FACTOR
        else:
            policy_factor = 1.0

        dynamic_factor = DYNAMIC_UNCERTAINTY_FACTOR if dynamic is not None else 1.0
        total_uncertainty = base_uncertainty * policy_factor * dynamic_factor
        low = central * (1 - total_uncertainty * ASYMMETRY_LOW)
        high = central * (1 + total_uncertainty * ASYMMETRY_HIGH)
        return low, high


def quick_score(policy: Policy, dynamic: bool = False) -> ScoringResult:
    """Convenience function for quick policy scoring."""
    scorer = FiscalPolicyScorer()
    return scorer.score_policy(policy, dynamic=dynamic)
