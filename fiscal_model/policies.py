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
    
    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response offset to static revenue estimate.
        Uses elasticity of taxable income (ETI) approach.

        Returns:
            Offset factor (e.g., 0.25 means 25% of static effect is offset)
        """
        # Revenue offset from behavioral response
        # Higher ETI = more revenue offset from tax cuts, less gain from tax increases
        return static_effect * self.taxable_income_elasticity * 0.5

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
        # This is crucial: rate changes only apply to income ABOVE the threshold,
        # not the entire income of affected filers.
        #
        # Example: For $400K threshold, someone earning $600K has only $200K
        # subject to the new rate, not the full $600K.
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
    """Create a standard income tax cut policy."""
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
    """Create a new tax credit policy."""
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
    """Create a spending increase policy."""
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

