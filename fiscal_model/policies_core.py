"""
Core policy parameter definitions.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """Categories of fiscal policies."""

    INCOME_TAX = "income_tax"
    CORPORATE_TAX = "corporate_tax"
    PAYROLL_TAX = "payroll_tax"
    CAPITAL_GAINS_TAX = "capital_gains_tax"
    ESTATE_TAX = "estate_tax"
    EXCISE_TAX = "excise_tax"
    TAX_CREDIT = "tax_credit"
    TAX_DEDUCTION = "tax_deduction"
    DISCRETIONARY_DEFENSE = "discretionary_defense"
    DISCRETIONARY_NONDEFENSE = "discretionary_nondefense"
    MANDATORY_SPENDING = "mandatory_spending"
    INFRASTRUCTURE = "infrastructure"
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"
    UNEMPLOYMENT = "unemployment"
    SNAP = "snap"
    OTHER_TRANSFER = "other_transfer"


@dataclass
class Policy:
    """Base class for fiscal policy proposals."""

    name: str
    description: str
    policy_type: PolicyType
    start_year: int = 2025
    duration_years: int = 10
    phase_in_years: int = 1
    sunset: bool = False

    def __post_init__(self):
        if self.duration_years <= 0:
            raise ValueError(f"duration_years must be positive, got {self.duration_years}")
        if self.phase_in_years < 1:
            raise ValueError(f"phase_in_years must be >= 1, got {self.phase_in_years}")
        if self.start_year < 2000 or self.start_year > 2100:
            raise ValueError(f"start_year must be between 2000 and 2100, got {self.start_year}")

    def get_phase_in_factor(self, year: int) -> float:
        """Calculate the phase-in factor for a given year."""
        if year < self.start_year:
            return 0.0

        years_since_start = year - self.start_year

        if self.sunset and years_since_start >= self.duration_years:
            return 0.0

        if self.phase_in_years <= 1:
            return 1.0

        return min(1.0, (years_since_start + 1) / self.phase_in_years)

    def is_active(self, year: int) -> bool:
        """Check if policy is active in a given year."""
        if year < self.start_year:
            return False
        return not (self.sunset and year >= self.start_year + self.duration_years)


@dataclass
class TaxPolicy(Policy):
    """Tax policy proposal with detailed parameters."""

    rate_change: float = 0.0
    new_rate: float | None = None
    affected_income_threshold: float = 0.0
    affected_income_cap: float | None = None
    credit_amount: float = 0.0
    credit_refundable: bool = False
    deduction_amount: float = 0.0
    affected_taxpayers_millions: float = 0.0
    taxable_income_elasticity: float = 0.25
    labor_supply_elasticity: float = 0.1
    annual_revenue_change_billions: float | None = None
    avg_taxable_income_in_bracket: float = 0.0
    marginal_rate_before: float = 0.0
    data_year: int | None = None

    def __post_init__(self):
        super().__post_init__()
        if not (-1.0 <= self.rate_change <= 1.0):
            raise ValueError(f"rate_change must be between -1.0 and 1.0, got {self.rate_change}")
        if self.new_rate is not None and not (0.0 <= self.new_rate <= 1.0):
            raise ValueError(f"new_rate must be between 0.0 and 1.0, got {self.new_rate}")
        if self.affected_income_threshold < 0:
            raise ValueError(
                f"affected_income_threshold must be >= 0, got {self.affected_income_threshold}"
            )
        if self.taxable_income_elasticity < 0:
            raise ValueError(
                f"taxable_income_elasticity must be >= 0, got {self.taxable_income_elasticity}"
            )
        if self.labor_supply_elasticity < 0:
            raise ValueError(
                f"labor_supply_elasticity must be >= 0, got {self.labor_supply_elasticity}"
            )
        if self.affected_taxpayers_millions < 0:
            raise ValueError(
                f"affected_taxpayers_millions must be >= 0, got {self.affected_taxpayers_millions}"
            )

        if self.affected_income_threshold > 10_000_000:
            logger.warning(
                f"Very high income threshold ${self.affected_income_threshold:,.0f} - few taxpayers affected"
            )

        if self.taxable_income_elasticity > 0.5:
            logger.warning(
                f"ETI of {self.taxable_income_elasticity} exceeds typical range (0.1-0.4)"
            )

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """Estimate static revenue effect before behavioral responses."""
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        if use_real_data and self._should_use_irs_data():
            try:
                return self._estimate_from_irs_data(baseline_revenue)
            except Exception as exc:
                logger.warning(f"Could not use IRS data for auto-population: {exc}")
                logger.warning("Falling back to manual parameters or heuristics")

        if (
            self.rate_change != 0
            and self.affected_taxpayers_millions > 0
            and self.avg_taxable_income_in_bracket > 0
        ):
            marginal_income = max(
                0,
                self.avg_taxable_income_in_bracket - self.affected_income_threshold,
            )

            if self.affected_income_threshold == 0:
                marginal_income = self.avg_taxable_income_in_bracket

            revenue_change = (
                self.rate_change
                * marginal_income
                * self.affected_taxpayers_millions
                * 1e6
            ) / 1e9
            return revenue_change

        if self.rate_change != 0:
            if self.affected_income_threshold > 0:
                if self.affected_income_threshold >= 500000:
                    affected_share = 0.20
                elif self.affected_income_threshold >= 200000:
                    affected_share = 0.40
                elif self.affected_income_threshold >= 100000:
                    affected_share = 0.55
                elif self.affected_income_threshold >= 50000:
                    affected_share = 0.75
                else:
                    affected_share = 0.90
            else:
                affected_share = 1.0

            avg_effective_rate = 0.18
            return baseline_revenue * affected_share * (self.rate_change / avg_effective_rate)

        if self.credit_amount != 0 and self.affected_taxpayers_millions > 0:
            return -self.credit_amount * self.affected_taxpayers_millions / 1e3

        if self.deduction_amount != 0 and self.affected_taxpayers_millions > 0:
            marginal_rate = self.marginal_rate_before if self.marginal_rate_before > 0 else 0.25
            return -self.deduction_amount * marginal_rate * self.affected_taxpayers_millions / 1e3

        return 0.0

    def _should_use_irs_data(self) -> bool:
        """Check if we should attempt to auto-populate from IRS SOI data."""
        return (
            self.rate_change != 0
            and self.affected_income_threshold > 0
            and self.affected_taxpayers_millions == 0
        )

    def _estimate_from_irs_data(self, baseline_revenue: float) -> float:
        """Auto-populate parameters from IRS SOI data and estimate revenue effect."""
        _ = baseline_revenue
        from fiscal_model.data import IRSSOIData

        irs_data = IRSSOIData()
        available_years = irs_data.get_data_years_available()
        if not available_years:
            raise FileNotFoundError(
                "No IRS SOI data files found. "
                "See fiscal_model/data_files/irs_soi/README.md for download instructions."
            )

        year = self.data_year if self.data_year else max(available_years)
        logger.info(f"Auto-populating tax policy parameters from {year} IRS SOI data")
        bracket_info = irs_data.get_filers_by_bracket(
            year=year,
            threshold=self.affected_income_threshold,
        )

        logger.info(
            f"  Affected filers: {bracket_info['num_filers']/1e6:.2f}M "
            f"(threshold: ${self.affected_income_threshold:,.0f})"
        )
        logger.info(f"  Avg taxable income: ${bracket_info['avg_taxable_income']:,.0f}")

        self.affected_taxpayers_millions = bracket_info["num_filers"] / 1e6
        self.avg_taxable_income_in_bracket = bracket_info["avg_taxable_income"]

        marginal_income = max(
            0,
            bracket_info["avg_taxable_income"] - self.affected_income_threshold,
        )

        if self.affected_income_threshold == 0:
            marginal_income = bracket_info["avg_taxable_income"]

        logger.info(f"  Avg total income: ${bracket_info['avg_taxable_income']:,.0f}")
        logger.info(
            f"  Marginal income above ${self.affected_income_threshold:,.0f}: ${marginal_income:,.0f}"
        )

        revenue_change = (
            self.rate_change * marginal_income * bracket_info["num_filers"]
        ) / 1e9

        logger.info(
            f"  Estimated revenue change: ${revenue_change:,.1f}B "
            f"({self.rate_change*100:+.1f}pp rate change)"
        )

        return revenue_change

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Estimate behavioral response offset to static revenue estimate."""
        return abs(static_effect) * self.taxable_income_elasticity * 0.5

    def validate_inputs(self) -> list[str]:
        """Validate inputs and return warning strings for unusual parameters."""
        warnings = []

        if self.affected_income_threshold > 10_000_000:
            warnings.append(
                f"Very high income threshold (${self.affected_income_threshold:,.0f}): "
                "only a small fraction of taxpayers affected"
            )

        if self.taxable_income_elasticity > 0.5:
            warnings.append(
                f"High ETI ({self.taxable_income_elasticity:.2f}): "
                "typical range is 0.1-0.4; consider if this is intentional"
            )

        if self.rate_change > 0.2:
            warnings.append(
                f"Large rate increase ({self.rate_change*100:+.1f}pp): "
                "verify this policy is intended to be highly restrictive"
            )

        if self.rate_change < -0.2:
            warnings.append(
                f"Large rate decrease ({self.rate_change*100:+.1f}pp): "
                "verify this policy is intended to be highly stimulative"
            )

        if (
            self.rate_change != 0
            and self.affected_income_threshold == 0
            and self.affected_taxpayers_millions == 0
            and self.avg_taxable_income_in_bracket == 0
        ):
            warnings.append(
                "Rate change specified but no population data provided: "
                "cannot estimate revenue impact accurately. "
                "Consider providing affected_taxpayers_millions or avg_taxable_income_in_bracket"
            )

        return warnings


@dataclass
class CapitalGainsPolicy(TaxPolicy):
    """Capital gains tax policy with realizations behavioral response."""

    baseline_capital_gains_rate: float = 0.20
    baseline_realizations_billions: float = 0.0
    short_run_elasticity: float = 0.8
    long_run_elasticity: float = 0.4
    transition_years: int = 3
    realization_elasticity: float = 0.5
    use_time_varying_elasticity: bool = True
    step_up_at_death: bool = True
    eliminate_step_up: bool = False
    step_up_exemption: float = 1_000_000
    gains_at_death_billions: float = 54.0
    step_up_lock_in_multiplier: float = 2.0

    def __post_init__(self):
        super().__post_init__()
        if not (0 <= self.baseline_capital_gains_rate <= 1):
            raise ValueError(
                "baseline_capital_gains_rate must be between 0 and 1, "
                f"got {self.baseline_capital_gains_rate}"
            )
        if self.short_run_elasticity < 0:
            raise ValueError(
                f"short_run_elasticity must be >= 0, got {self.short_run_elasticity}"
            )
        if self.long_run_elasticity < 0:
            raise ValueError(
                f"long_run_elasticity must be >= 0, got {self.long_run_elasticity}"
            )
        if self.transition_years < 0:
            raise ValueError(f"transition_years must be >= 0, got {self.transition_years}")
        if self.step_up_lock_in_multiplier < 0:
            raise ValueError(
                "step_up_lock_in_multiplier must be >= 0, "
                f"got {self.step_up_lock_in_multiplier}"
            )

    def get_elasticity_for_year(self, years_since_start: int) -> float:
        """Get the appropriate realization elasticity for a given year."""
        if not self.use_time_varying_elasticity:
            base_elasticity = float(self.realization_elasticity)
        elif years_since_start <= 0:
            base_elasticity = float(self.short_run_elasticity)
        elif years_since_start >= self.transition_years:
            base_elasticity = float(self.long_run_elasticity)
        else:
            weight = years_since_start / self.transition_years
            base_elasticity = float(
                self.short_run_elasticity * (1 - weight)
                + self.long_run_elasticity * weight
            )

        if self.step_up_at_death and not self.eliminate_step_up:
            return base_elasticity * self.step_up_lock_in_multiplier
        return base_elasticity

    def _reform_capital_gains_rate(self) -> float:
        """Determine the reform capital gains rate."""
        if self.new_rate is not None:
            return float(self.new_rate)
        return float(self.baseline_capital_gains_rate + self.rate_change)

    def estimate_step_up_elimination_revenue(self) -> float:
        """Estimate annual revenue from eliminating step-up basis at death."""
        if not self.eliminate_step_up:
            return 0.0

        tau1 = float(self._reform_capital_gains_rate())
        gains_at_death = float(self.gains_at_death_billions)

        if self.step_up_exemption > 0:
            exemption_millions = self.step_up_exemption / 1_000_000
            exemption_share = min(0.9, 0.4 * exemption_millions)
        else:
            exemption_share = 0.0

        taxable_gains = gains_at_death * (1 - exemption_share)
        return tau1 * taxable_gains

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """Static effect holding realizations fixed."""
        _ = baseline_revenue
        if use_real_data and float(self.baseline_realizations_billions) <= 0:
            from fiscal_model.data import CapitalGainsBaseline

            year = int(self.data_year) if self.data_year else 2022
            baseline = CapitalGainsBaseline().get_baseline_above_threshold_with_rate_method(
                year=year,
                threshold=float(self.affected_income_threshold),
                rate_method="statutory_by_agi",
            )
            self.baseline_realizations_billions = float(baseline["net_capital_gain_billions"])
            self.baseline_capital_gains_rate = float(baseline["average_effective_tax_rate"])

        tau0 = float(self.baseline_capital_gains_rate)
        tau1 = float(self._reform_capital_gains_rate())
        r0 = float(self.baseline_realizations_billions)

        if r0 <= 0:
            raise ValueError(
                "baseline_realizations_billions must be > 0 for CapitalGainsPolicy "
                "(set it manually or enable real-data auto-population)."
            )
        if not (0 <= tau0 < 1) or not (0 <= tau1 < 1):
            raise ValueError("Capital gains rates must be in [0, 1) for CapitalGainsPolicy")

        return (tau1 - tau0) * r0

    def estimate_behavioral_offset(
        self,
        static_effect: float,
        years_since_start: int = 0,
    ) -> float:
        """Behavioral offset from realizations response."""
        _ = static_effect
        tau0 = float(self.baseline_capital_gains_rate)
        tau1 = float(self._reform_capital_gains_rate())
        r0 = float(self.baseline_realizations_billions)
        eps = self.get_elasticity_for_year(years_since_start)

        if r0 <= 0:
            raise ValueError("baseline_realizations_billions must be > 0 for CapitalGainsPolicy")
        if eps < 0:
            raise ValueError("realization_elasticity must be >= 0 for CapitalGainsPolicy")
        if not (0 <= tau0 < 1) or not (0 <= tau1 < 1):
            raise ValueError("Capital gains rates must be in [0, 1) for CapitalGainsPolicy")

        net0 = 1 - tau0
        net1 = 1 - tau1
        r1 = r0 * (net1 / net0) ** eps
        delta_rev_static = (tau1 - tau0) * r0
        delta_rev_total = (tau1 * r1) - (tau0 * r0)
        return delta_rev_static - delta_rev_total


@dataclass
class SpendingPolicy(Policy):
    """Spending policy proposal."""

    annual_spending_change_billions: float = 0.0
    annual_growth_rate: float = 0.02
    gdp_multiplier: float = 1.0
    employment_per_billion: float = 10000
    is_one_time: bool = False
    category: Literal["defense", "nondefense", "mandatory"] = "nondefense"

    def __post_init__(self):
        super().__post_init__()
        category_to_type = {
            "defense": PolicyType.DISCRETIONARY_DEFENSE,
            "nondefense": PolicyType.DISCRETIONARY_NONDEFENSE,
            "mandatory": PolicyType.MANDATORY_SPENDING,
        }
        expected_type = category_to_type.get(self.category)
        if expected_type and self.policy_type != expected_type:
            self.policy_type = expected_type

    def get_spending_in_year(self, year: int, start_amount: float | None = None) -> float:
        """Calculate spending amount for a given year, including growth."""
        if not self.is_active(year):
            return 0.0

        base = start_amount if start_amount else self.annual_spending_change_billions
        years_since_start = year - self.start_year
        phase_factor = self.get_phase_in_factor(year)

        if self.is_one_time and years_since_start > 0:
            return 0.0

        growth_factor = (1 + self.annual_growth_rate) ** years_since_start
        return base * growth_factor * phase_factor


@dataclass
class TransferPolicy(Policy):
    """Transfer program policy."""

    benefit_change_percent: float = 0.0
    benefit_change_dollars: float = 0.0
    eligibility_age_change: float = 0.0
    new_beneficiaries_millions: float = 0.0
    annual_cost_change_billions: float = 0.0
    labor_force_participation_effect: float = 0.0

    def estimate_cost_effect(self, baseline_cost: float) -> float:
        """Estimate change in program costs."""
        if self.annual_cost_change_billions != 0:
            return self.annual_cost_change_billions

        cost_change = baseline_cost * self.benefit_change_percent

        if self.new_beneficiaries_millions != 0:
            avg_benefit = baseline_cost / 60
            cost_change += avg_benefit * self.new_beneficiaries_millions

        return cost_change


@dataclass
class PolicyPackage:
    """A package of multiple policies analyzed together."""

    name: str
    description: str
    policies: list[Policy] = field(default_factory=list)
    interaction_factor: float = 1.0

    def add_policy(self, policy: Policy):
        """Add a policy to the package."""
        self.policies.append(policy)

    def get_all_years(self) -> tuple[int, int]:
        """Get the range of years covered by all policies."""
        if not self.policies:
            return (2025, 2034)

        start = min(policy.start_year for policy in self.policies)
        end = max(policy.start_year + policy.duration_years for policy in self.policies)
        return (start, end)

    def get_active_policies(self, year: int) -> list[Policy]:
        """Get all policies active in a given year."""
        return [policy for policy in self.policies if policy.is_active(year)]
