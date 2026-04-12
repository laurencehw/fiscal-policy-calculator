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

        result = ScoringResult(
            policy=policy,
            baseline=self.baseline,
            years=years,
            static_revenue_effect=static_revenue,
            static_spending_effect=static_spending,
            static_deficit_effect=static_deficit,
            behavioral_offset=behavioral,
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

        for result in results:
            total_static_revenue += result.static_revenue_effect
            total_static_spending += result.static_spending_effect
            total_behavioral += result.behavioral_offset

        total_static_revenue *= package.interaction_factor
        total_static_spending *= package.interaction_factor
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
            static_annual = policy.estimate_static_revenue_effect(
                base_rev,
                use_real_data=self.use_real_data,
            )
            revenue[idx] = static_annual * phase

            if isinstance(policy, CapitalGainsPolicy) and policy.eliminate_step_up:
                step_up_revenue = policy.estimate_step_up_elimination_revenue()
                revenue[idx] += step_up_revenue * phase

            if isinstance(policy, CapitalGainsPolicy):
                years_since_start = year - policy.start_year
                behavioral[idx] = policy.estimate_behavioral_offset(revenue[idx], years_since_start)
            else:
                behavioral[idx] = policy.estimate_behavioral_offset(revenue[idx])

        return revenue, behavioral

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
            static_annual = policy.estimate_static_revenue_effect(
                base_rev,
                use_real_data=self.use_real_data,
            )

            if isinstance(policy, TaxExpenditurePolicy):
                growth_rate = policy.get_expenditure_data().get("growth_rate", 0.03)

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
        """Calculate static spending effect for spending policy."""
        n_years = len(self.baseline.years)
        spending = np.zeros(n_years)

        for idx, year in enumerate(self.baseline.years):
            spending[idx] = policy.get_spending_in_year(year)

        return spending

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
