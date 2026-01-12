"""
Policy Parameter Definitions

Defines the structure for various fiscal policy proposals including
tax policies, spending policies, and transfer programs.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import numpy as np


class PolicyType(Enum):
    """Categories of fiscal policies."""
    # Tax policies
    INCOME_TAX = "income_tax"
    CORPORATE_TAX = "corporate_tax"
    PAYROLL_TAX = "payroll_tax"
    CAPITAL_GAINS_TAX = "capital_gains_tax"
    ESTATE_TAX = "estate_tax"
    EXCISE_TAX = "excise_tax"
    TAX_CREDIT = "tax_credit"
    TAX_DEDUCTION = "tax_deduction"
    
    # Spending policies
    DISCRETIONARY_DEFENSE = "discretionary_defense"
    DISCRETIONARY_NONDEFENSE = "discretionary_nondefense"
    MANDATORY_SPENDING = "mandatory_spending"
    INFRASTRUCTURE = "infrastructure"
    
    # Transfer programs
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"
    UNEMPLOYMENT = "unemployment"
    SNAP = "snap"
    OTHER_TRANSFER = "other_transfer"


@dataclass
class Policy:
    """
    Base class for fiscal policy proposals.
    
    Attributes:
        name: Short descriptive name
        description: Detailed description of the policy
        policy_type: Category of fiscal policy
        start_year: First year the policy takes effect
        duration_years: Number of years the policy is in effect (default 10 for CBO window)
        phase_in_years: Years to fully phase in the policy (default 1 = immediate)
        sunset: Whether the policy expires after duration_years
    """
    name: str
    description: str
    policy_type: PolicyType
    start_year: int = 2025
    duration_years: int = 10
    phase_in_years: int = 1
    sunset: bool = False
    
    def get_phase_in_factor(self, year: int) -> float:
        """
        Calculate the phase-in factor for a given year.
        Returns 0 if before start, 1 if fully phased in, fractional during phase-in.
        """
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
        if self.sunset and year >= self.start_year + self.duration_years:
            return False
        return True


@dataclass
class TaxPolicy(Policy):
    """
    Tax policy proposal with detailed parameters.
    
    Supports various tax changes including rate changes, threshold changes,
    new credits/deductions, and base broadening.
    """
    # Rate changes
    rate_change: float = 0.0  # Change in tax rate (e.g., -0.02 for 2pp reduction)
    new_rate: Optional[float] = None  # Alternative: specify new rate directly
    
    # Who is affected
    affected_income_threshold: float = 0.0  # Income threshold for applicability
    affected_income_cap: Optional[float] = None  # Upper bound if applicable
    
    # For credits/deductions
    credit_amount: float = 0.0  # Per-taxpayer credit amount
    credit_refundable: bool = False  # Is the credit refundable?
    deduction_amount: float = 0.0  # Deduction amount
    
    # Affected population
    affected_taxpayers_millions: float = 0.0  # Estimated affected population
    
    # Behavioral parameters (CBO-style elasticities)
    taxable_income_elasticity: float = 0.25  # ETI - key behavioral parameter
    labor_supply_elasticity: float = 0.1  # Compensated labor supply elasticity
    
    # Revenue estimate override (if known from external source)
    annual_revenue_change_billions: Optional[float] = None
    
    # More granular inputs for accurate static estimation
    avg_taxable_income_in_bracket: float = 0.0  # Average taxable income of affected filers
    marginal_rate_before: float = 0.0  # Current marginal rate in affected bracket

    # Data integration
    data_year: Optional[int] = None  # IRS data year to use (None = most recent available)

    def estimate_static_revenue_effect(self, baseline_revenue: float,
                                       use_real_data: bool = True) -> float:
        """
        Estimate static revenue effect before behavioral responses.

        Uses the more accurate formula when bracket-level data is provided:
            Revenue Change = Rate Change × Taxable Income × Affected Taxpayers

        NEW: Can auto-populate parameters from IRS SOI data when available!

        Falls back to proportional estimation if granular data unavailable.

        Args:
            baseline_revenue: Baseline revenue in billions for affected tax
            use_real_data: If True, try to auto-populate from IRS SOI data

        Returns:
            Change in revenue in billions (negative = revenue loss)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        # NEW: Try to auto-populate from IRS SOI data
        if use_real_data and self._should_use_irs_data():
            try:
                return self._estimate_from_irs_data(baseline_revenue)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not use IRS data for auto-population: {e}")
                logger.warning("Falling back to manual parameters or heuristics")
                # Fall through to existing logic

        # PREFERRED: Use bracket-level calculation if data provided
        if (self.rate_change != 0 and 
            self.affected_taxpayers_millions > 0 and 
            self.avg_taxable_income_in_bracket > 0):
            # Key insight: Rate changes apply only to MARGINAL income above threshold,
            # not the entire income of affected filers.
            # 
            # Example: For a $400K threshold, someone earning $500K only has $100K
            # subject to the rate change, not the full $500K.
            #
            # Formula: ΔRevenue = ΔRate × Marginal_Income × # Taxpayers
            # where Marginal_Income = Avg_Income - Threshold
            
            marginal_income = max(0, self.avg_taxable_income_in_bracket - self.affected_income_threshold)
            
            # If threshold is 0 (affects all income), use full average income
            if self.affected_income_threshold == 0:
                marginal_income = self.avg_taxable_income_in_bracket
            
            revenue_change = (
                self.rate_change *  # e.g., -0.02 for 2pp cut
                marginal_income *   # income ABOVE threshold subject to rate change
                self.affected_taxpayers_millions * 1e6  # convert to actual count
            ) / 1e9  # convert to billions
            return revenue_change
        
        # FALLBACK: Simple proportional estimation (less accurate)
        if self.rate_change != 0:
            # Estimate affected share of total revenue
            if self.affected_income_threshold > 0:
                # Higher thresholds affect smaller share of revenue
                # Rough heuristic: income above $500K is ~20% of income tax base
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
                affected_share = 1.0  # Affects all brackets
            
            # Revenue change = baseline × affected share × (rate change / avg rate)
            avg_effective_rate = 0.18  # Average effective income tax rate
            return baseline_revenue * affected_share * (self.rate_change / avg_effective_rate)
            
        # Credit/deduction effects
        if self.credit_amount != 0 and self.affected_taxpayers_millions > 0:
            return -self.credit_amount * self.affected_taxpayers_millions / 1e3
            
        if self.deduction_amount != 0 and self.affected_taxpayers_millions > 0:
            # Deduction value depends on marginal rate
            marginal_rate = self.marginal_rate_before if self.marginal_rate_before > 0 else 0.25
            return -self.deduction_amount * marginal_rate * self.affected_taxpayers_millions / 1e3
            
        return 0.0

    def _should_use_irs_data(self) -> bool:
        """
        Check if we should attempt to auto-populate from IRS SOI data.

        Returns True if:
        - Rate change is specified (non-zero)
        - Income threshold is specified
        - Manual parameters NOT already provided
        """
        return (
            self.rate_change != 0 and
            self.affected_income_threshold > 0 and
            self.affected_taxpayers_millions == 0  # Not manually specified
        )

    def _estimate_from_irs_data(self, baseline_revenue: float) -> float:
        """
        Auto-populate parameters from IRS SOI data and estimate revenue effect.

        This method automatically looks up:
        - Number of filers above the income threshold
        - Average taxable income in affected brackets
        - Total tax liability

        Args:
            baseline_revenue: Baseline revenue (not used in this method)

        Returns:
            Revenue change in billions

        Raises:
            FileNotFoundError: If IRS SOI data files not available
            ValueError: If data lookup fails
        """
        import logging
        logger = logging.getLogger(__name__)

        # Import here to avoid circular dependency
        from fiscal_model.data import IRSSOIData

        # Initialize data loader
        irs_data = IRSSOIData()

        # Get most recent available data year (or use specified year)
        available_years = irs_data.get_data_years_available()
        if not available_years:
            raise FileNotFoundError(
                "No IRS SOI data files found. "
                "See fiscal_model/data_files/irs_soi/README.md for download instructions."
            )

        year = self.data_year if self.data_year else max(available_years)
        logger.info(f"Auto-populating tax policy parameters from {year} IRS SOI data")

        # Get filer statistics for income above threshold
        bracket_info = irs_data.get_filers_by_bracket(
            year=year,
            threshold=self.affected_income_threshold
        )

        logger.info(
            f"  Affected filers: {bracket_info['num_filers']/1e6:.2f}M "
            f"(threshold: ${self.affected_income_threshold:,.0f})"
        )
        logger.info(
            f"  Avg taxable income: ${bracket_info['avg_taxable_income']:,.0f}"
        )

        # Update policy object with auto-populated values (so UI can display them)
        self.affected_taxpayers_millions = bracket_info['num_filers'] / 1e6
        self.avg_taxable_income_in_bracket = bracket_info['avg_taxable_income']

        # Calculate MARGINAL income (income above threshold)
        marginal_income = max(0, bracket_info['avg_taxable_income'] - self.affected_income_threshold)

        # If threshold is 0 (affects all income), use full average income
        if self.affected_income_threshold == 0:
            marginal_income = bracket_info['avg_taxable_income']

        logger.info(
            f"  Avg total income: ${bracket_info['avg_taxable_income']:,.0f}"
        )
        logger.info(
            f"  Marginal income above ${self.affected_income_threshold:,.0f}: ${marginal_income:,.0f}"
        )

        # Calculate revenue change using MARGINAL income
        revenue_change = (
            self.rate_change *
            marginal_income *
            bracket_info['num_filers']
        ) / 1e9  # Convert to billions

        logger.info(
            f"  Estimated revenue change: ${revenue_change:,.1f}B "
            f"({self.rate_change*100:+.1f}pp rate change)"
        )

        return revenue_change

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response offset to static revenue estimate.
        Uses elasticity of taxable income (ETI) approach.

        The behavioral offset represents REVENUE LOST due to behavioral response:
        - Tax INCREASE: People reduce taxable income → positive offset (lost revenue)
        - Tax CUT: People increase taxable income → negative offset (recovered revenue)

        This offset is ADDED to static deficit to get final deficit effect.

        Returns:
            Behavioral offset in billions (positive = revenue lost, increases deficit)
        """
        # Behavioral response reduces revenue from tax increases (positive offset)
        # and recovers some revenue from tax cuts (negative offset)
        return abs(static_effect) * self.taxable_income_elasticity * 0.5


@dataclass
class CapitalGainsPolicy(TaxPolicy):
    """
    Capital gains tax policy with realizations behavioral response.

    Unlike wage income, capital gains realizations respond strongly to the tax rate
    due to timing/lock-in effects. This policy models that channel explicitly.

    Required inputs (currently user-provided):
    - baseline_capital_gains_rate: baseline effective marginal rate (0-1) for the affected group
    - baseline_realizations_billions: taxable realizations base ($B/year) for the affected group

    Elasticity parameters (time-varying):
    - short_run_elasticity: elasticity in years 1-3 (higher due to timing effects), default 0.8
    - long_run_elasticity: elasticity in years 4+ (timing effects exhausted), default 0.4
    - transition_years: years to transition from short-run to long-run, default 3

    The realization_elasticity parameter is kept for backward compatibility; if
    short_run_elasticity and long_run_elasticity are both left at defaults,
    realization_elasticity is used as a single constant instead.

    References:
    - CBO (2012): "How Capital Gains Tax Rates Affect Revenues" — short-run ε ≈ 0.7-1.0
    - Dowd, McClelland, Muthitacharoen (2015): long-run ε ≈ 0.3-0.5
    - Yale Budget Lab: distinguishes transitory vs permanent behavioral response
    """

    baseline_capital_gains_rate: float = 0.20
    baseline_realizations_billions: float = 0.0

    # Time-varying elasticity parameters
    short_run_elasticity: float = 0.8   # Years 1-3: timing/anticipation effects dominate
    long_run_elasticity: float = 0.4    # Years 4+: permanent behavioral response only
    transition_years: int = 3           # Years over which elasticity transitions

    # Backward-compatible single elasticity (used if short/long are at defaults)
    realization_elasticity: float = 0.5

    # Whether to use time-varying elasticity (auto-detected, can override)
    use_time_varying_elasticity: bool = True

    # Step-up basis at death parameters
    # Current law: unrealized gains are forgiven at death (step-up basis)
    # This creates strong lock-in incentive to hold until death
    step_up_at_death: bool = True       # Current law default
    eliminate_step_up: bool = False     # Policy change: tax gains at death
    step_up_exemption: float = 1_000_000 # Exemption per decedent (Biden: $1M)

    # Unrealized gains at death (for step-up elimination revenue)
    # JCT estimates ~$40-60B/year in forgone revenue from step-up
    # CBO estimates ~$54B/year taxable if step-up eliminated
    gains_at_death_billions: float = 54.0  # Annual unrealized gains at death

    # Step-up elasticity multiplier: how much step-up increases lock-in
    # With step-up, taxpayers can avoid tax entirely by holding until death
    # This creates much stronger deferral incentive than just timing
    # Calibrated from PWBM: need ~2x elasticity multiplier to match their results
    step_up_lock_in_multiplier: float = 2.0

    def get_elasticity_for_year(self, years_since_start: int) -> float:
        """
        Get the appropriate realization elasticity based on years since policy start.

        The elasticity transitions from short_run_elasticity to long_run_elasticity
        over the transition_years period using linear interpolation.

        If step-up basis at death is in effect (current law), the elasticity is
        multiplied by step_up_lock_in_multiplier to capture the stronger deferral
        incentive from being able to avoid tax entirely by holding until death.

        Args:
            years_since_start: Number of years since policy took effect (0 = first year)

        Returns:
            Elasticity value for that year (may be multiplied by step-up factor)

        Example with defaults (short=0.8, long=0.4, transition=3):
            Year 0: 0.8 (full short-run)
            Year 1: 0.67
            Year 2: 0.53
            Year 3+: 0.4 (full long-run)

        With step_up_at_death=True and multiplier=2.0:
            Year 0: 1.6, Year 3+: 0.8
        """
        if not self.use_time_varying_elasticity:
            base_elasticity = float(self.realization_elasticity)
        elif years_since_start <= 0:
            base_elasticity = float(self.short_run_elasticity)
        elif years_since_start >= self.transition_years:
            base_elasticity = float(self.long_run_elasticity)
        else:
            # Interpolate
            weight = years_since_start / self.transition_years
            base_elasticity = float(
                self.short_run_elasticity * (1 - weight) +
                self.long_run_elasticity * weight
            )

        # Apply step-up lock-in multiplier if step-up is in effect
        # When step-up is eliminated, the lock-in incentive is reduced
        if self.step_up_at_death and not self.eliminate_step_up:
            return base_elasticity * self.step_up_lock_in_multiplier
        else:
            return base_elasticity

    def _reform_capital_gains_rate(self) -> float:
        """
        Determine the reform capital gains rate.

        Precedence:
        1) new_rate if provided
        2) baseline_capital_gains_rate + rate_change
        """
        if self.new_rate is not None:
            return float(self.new_rate)
        return float(self.baseline_capital_gains_rate + self.rate_change)

    def estimate_step_up_elimination_revenue(self) -> float:
        """
        Estimate annual revenue from eliminating step-up basis at death.

        When step-up is eliminated, unrealized capital gains become taxable at death.
        This creates a NEW revenue stream separate from lifetime realizations.

        Formula:
            Revenue = τ × Gains_at_death × (1 - exemption_share)

        Where:
        - τ = reform capital gains rate
        - Gains_at_death = annual unrealized gains transferred at death (~$54B baseline)
        - exemption_share = fraction of gains below exemption threshold

        Returns:
            Annual revenue in billions from taxing gains at death (0 if step-up not eliminated)

        References:
        - JCT: Step-up tax expenditure ~$40-60B/year
        - CBO: Taxing at death would raise ~$54B/year (no exemption)
        - Biden proposal: $1M exemption reduces revenue to ~$32B/year
        """
        if not self.eliminate_step_up:
            return 0.0

        tau1 = float(self._reform_capital_gains_rate())
        gains_at_death = float(self.gains_at_death_billions)

        # Calculate exemption share
        # Biden proposal: $1M per person exemption
        # Rough estimate: ~40% of gains at death are below $1M threshold
        # Higher exemptions reduce taxable share further
        if self.step_up_exemption > 0:
            # Rough heuristic: each $1M of exemption shields ~40% of gains
            # This is a simplification; actual distribution is complex
            exemption_millions = self.step_up_exemption / 1_000_000
            exemption_share = min(0.9, 0.4 * exemption_millions)
        else:
            exemption_share = 0.0

        taxable_gains = gains_at_death * (1 - exemption_share)
        return tau1 * taxable_gains

    def estimate_static_revenue_effect(self, baseline_revenue: float, use_real_data: bool = True) -> float:
        """
        Static effect holding realizations fixed:

            ΔRev_static = (τ1 - τ0) * R0

        where:
        - τ0 baseline rate
        - τ1 reform rate
        - R0 baseline realizations base ($B/year)
        """
        _ = baseline_revenue  # Not used for capital gains; base is provided directly.
        # Auto-populate baseline realizations/rate when requested and not provided.
        if use_real_data and float(self.baseline_realizations_billions) <= 0:
            from fiscal_model.data import CapitalGainsBaseline

            year = int(self.data_year) if self.data_year else 2022
            # Use a by-AGI statutory proxy for τ0 by default (more consistent with threshold targeting).
            baseline = CapitalGainsBaseline().get_baseline_above_threshold_with_rate_method(
                year=year,
                threshold=float(self.affected_income_threshold),
                rate_method="statutory_by_agi",
            )
            # Mutate for downstream display / reuse.
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

    def estimate_behavioral_offset(self, static_effect: float,
                                      years_since_start: int = 0) -> float:
        """
        Behavioral offset from realizations response (timing/lock-in).

        Uses time-varying elasticity: higher in short-run (timing effects),
        lower in long-run (permanent behavioral response only).

        Realizations response:
            R1 = R0 * ((1 - τ1) / (1 - τ0)) ** ε(t)

        where ε(t) transitions from short_run_elasticity to long_run_elasticity.

        Total revenue change:
            ΔRev_total = τ1*R1 - τ0*R0

        Offset returned here is:
            behavioral_offset = ΔRev_static - ΔRev_total

        This is POSITIVE when behavioral response reduces revenue (rate increase
        causes deferral, so actual revenue < static estimate).

        Args:
            static_effect: The static revenue effect (used for compatibility, not in calculation)
            years_since_start: Years since policy took effect (0 = first year)

        Returns:
            Behavioral offset in billions (positive = revenue lost, increases deficit)
        """
        _ = static_effect  # We recompute consistently from stored parameters.
        tau0 = float(self.baseline_capital_gains_rate)
        tau1 = float(self._reform_capital_gains_rate())
        r0 = float(self.baseline_realizations_billions)

        # Get time-varying elasticity
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

        # Return positive offset when revenue is lost (static > total)
        return delta_rev_static - delta_rev_total


@dataclass
class SpendingPolicy(Policy):
    """
    Spending policy proposal.
    
    Covers discretionary and mandatory spending changes.
    """
    # Annual spending change
    annual_spending_change_billions: float = 0.0
    
    # Growth rate for spending (real, after start year)
    annual_growth_rate: float = 0.02  # Default 2% real growth
    
    # Economic impact parameters
    gdp_multiplier: float = 1.0  # Fiscal multiplier for GDP impact
    employment_per_billion: float = 10000  # Jobs per billion dollars
    
    # Spending characteristics
    is_one_time: bool = False  # One-time vs recurring spending
    category: Literal["defense", "nondefense", "mandatory"] = "nondefense"
    
    def get_spending_in_year(self, year: int, start_amount: Optional[float] = None) -> float:
        """
        Calculate spending amount for a given year, including growth.
        """
        if not self.is_active(year):
            return 0.0
            
        base = start_amount if start_amount else self.annual_spending_change_billions
        years_since_start = year - self.start_year
        
        phase_factor = self.get_phase_in_factor(year)
        
        if self.is_one_time and years_since_start > 0:
            return 0.0
            
        # Apply growth rate
        growth_factor = (1 + self.annual_growth_rate) ** years_since_start
        
        return base * growth_factor * phase_factor


@dataclass
class TransferPolicy(Policy):
    """
    Transfer program policy (Social Security, Medicare, etc.)
    """
    # Benefit changes
    benefit_change_percent: float = 0.0  # Percentage change in benefits
    benefit_change_dollars: float = 0.0  # Dollar change per beneficiary
    
    # Eligibility changes
    eligibility_age_change: float = 0.0  # Change in eligibility age (years)
    new_beneficiaries_millions: float = 0.0  # Net new beneficiaries
    
    # Cost estimates
    annual_cost_change_billions: float = 0.0
    
    # Behavioral responses
    labor_force_participation_effect: float = 0.0  # Effect on labor force participation
    
    def estimate_cost_effect(self, baseline_cost: float) -> float:
        """
        Estimate change in program costs.
        """
        if self.annual_cost_change_billions != 0:
            return self.annual_cost_change_billions
            
        # Benefit change effect
        cost_change = baseline_cost * self.benefit_change_percent
        
        # New beneficiaries (assume average benefit)
        if self.new_beneficiaries_millions != 0:
            avg_benefit = baseline_cost / 60  # Rough estimate per million beneficiaries
            cost_change += avg_benefit * self.new_beneficiaries_millions
            
        return cost_change


@dataclass
class PolicyPackage:
    """
    A package of multiple policies analyzed together.
    
    Allows for interaction effects between policies.
    """
    name: str
    description: str
    policies: list[Policy] = field(default_factory=list)
    
    # Interaction parameters
    interaction_factor: float = 1.0  # Adjustment for policy interactions
    
    def add_policy(self, policy: Policy):
        """Add a policy to the package."""
        self.policies.append(policy)
        
    def get_all_years(self) -> tuple[int, int]:
        """Get the range of years covered by all policies."""
        if not self.policies:
            return (2025, 2034)
            
        start = min(p.start_year for p in self.policies)
        end = max(p.start_year + p.duration_years for p in self.policies)
        return (start, end)
    
    def get_active_policies(self, year: int) -> list[Policy]:
        """Get all policies active in a given year."""
        return [p for p in self.policies if p.is_active(year)]


# Convenience functions for creating common policy types

def create_income_tax_cut(
    name: str,
    rate_reduction: float,
    income_threshold: float = 0,
    start_year: int = 2025,
    duration: int = 10,
    affected_millions: float = 0
) -> TaxPolicy:
    """
    Create a standard income tax cut policy.

    Args:
        name: Policy name for identification
        rate_reduction: Reduction in tax rate as decimal (e.g., 0.02 for 2pp cut)
        income_threshold: Income threshold for applicability (dollars)
        start_year: First year policy takes effect
        duration: Number of years policy is active
        affected_millions: Estimated affected taxpayers in millions

    Returns:
        TaxPolicy configured as an income tax cut

    Example:
        >>> policy = create_income_tax_cut("Top Rate Cut", 0.03, income_threshold=500000)
    """
    return TaxPolicy(
        name=name,
        description=f"Reduce income tax rate by {rate_reduction*100:.1f} percentage points",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-abs(rate_reduction),
        affected_income_threshold=income_threshold,
        affected_taxpayers_millions=affected_millions,
        start_year=start_year,
        duration_years=duration,
    )


def create_new_tax_credit(
    name: str,
    amount: float,
    refundable: bool,
    affected_millions: float,
    start_year: int = 2025,
    duration: int = 10
) -> TaxPolicy:
    """
    Create a new tax credit policy.

    Args:
        name: Policy name for identification
        amount: Credit amount per taxpayer in dollars
        refundable: Whether the credit is refundable (paid even if no tax liability)
        affected_millions: Estimated eligible taxpayers in millions
        start_year: First year policy takes effect
        duration: Number of years policy is active

    Returns:
        TaxPolicy configured as a tax credit

    Example:
        >>> policy = create_new_tax_credit("New Family Credit", 1000, refundable=True, affected_millions=30)
    """
    return TaxPolicy(
        name=name,
        description=f"New {'refundable' if refundable else 'non-refundable'} tax credit of ${amount:,.0f}",
        policy_type=PolicyType.TAX_CREDIT,
        credit_amount=amount,
        credit_refundable=refundable,
        affected_taxpayers_millions=affected_millions,
        start_year=start_year,
        duration_years=duration,
    )


def create_spending_increase(
    name: str,
    annual_billions: float,
    category: Literal["defense", "nondefense", "mandatory"] = "nondefense",
    start_year: int = 2025,
    duration: int = 10,
    multiplier: float = 1.0
) -> SpendingPolicy:
    """
    Create a spending increase policy.

    Args:
        name: Policy name for identification
        annual_billions: Annual spending increase in billions of dollars
        category: Spending category ('defense', 'nondefense', or 'mandatory')
        start_year: First year policy takes effect
        duration: Number of years policy is active
        multiplier: GDP multiplier for economic effects (default 1.0)

    Returns:
        SpendingPolicy configured for the spending increase

    Example:
        >>> policy = create_spending_increase("Infrastructure", 50, category="nondefense", multiplier=1.5)
    """
    return SpendingPolicy(
        name=name,
        description=f"Increase {category} spending by ${annual_billions:.1f}B annually",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE if category == "nondefense" 
                   else PolicyType.DISCRETIONARY_DEFENSE if category == "defense"
                   else PolicyType.MANDATORY_SPENDING,
        annual_spending_change_billions=annual_billions,
        category=category,
        gdp_multiplier=multiplier,
        start_year=start_year,
        duration_years=duration,
    )

