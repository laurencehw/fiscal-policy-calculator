"""
Corporate Tax Scoring Module

Models corporate income tax rate changes, pass-through income, international
provisions (GILTI/FDII), and corporate tax reform proposals.

Key Corporate Tax Components:
1. Corporate rate (currently 21%, was 35% pre-TCJA)
2. Pass-through income (S-corps, partnerships taxed at individual rates)
3. GILTI/FDII international provisions
4. R&D expensing and amortization
5. Bonus depreciation (phasing out 2023-2027)
6. Book minimum tax (15% from IRA 2022)

References:
- CBO (2024): $450B corporate revenue baseline
- Biden FY2025: 21%→28% raises ~$1.35T/10yr
- JCT (2017): TCJA corporate cut ~$329B net
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

from .policies import TaxPolicy, PolicyType


# =============================================================================
# CORPORATE TAX BASELINE DATA
# =============================================================================

# Current law parameters (2024)
CURRENT_CORPORATE_RATE = 0.21  # 21% (TCJA permanent)
PRE_TCJA_CORPORATE_RATE = 0.35  # 35% (pre-2018)

# Revenue estimates (2024 baseline)
# CBO Feb 2024: Corporate income tax ~$450-500B/year
BASELINE_CORPORATE_REVENUE_BILLIONS = 475.0

# Taxable corporate profits (2024 estimate)
# Calibrated to match CBO estimate: Biden 21%→28% raises ~$1.35T
# At 7pp increase and ~$1.35T/10yr = $135B/year average
# With ~20% behavioral offset, static = ~$168B
# Profits = $168B / 0.07 = ~$2,400B
# But CBO has other factors, so we use lower effective base
# Calibrated: $1,900B gives closer match to CBO
BASELINE_TAXABLE_PROFITS_BILLIONS = 1900.0

# Pass-through income (S-corps, partnerships)
# ~$1.4T in pass-through income (taxed at individual rates)
BASELINE_PASSTHROUGH_INCOME_BILLIONS = 1400.0

# International (GILTI/FDII)
GILTI_REVENUE_BILLIONS = 25.0  # Current GILTI revenue ~$25B/year
FDII_COST_BILLIONS = 20.0  # FDII deduction costs ~$20B/year


@dataclass
class CorporateTaxPolicy(TaxPolicy):
    """
    Corporate tax policy with detailed corporate-specific parameters.

    Supports:
    - Corporate rate changes
    - Pass-through business income effects
    - International provisions (GILTI/FDII)
    - R&D and depreciation changes
    - Book minimum tax

    Behavioral response:
    - Corporate investment responds to after-tax returns
    - Elasticity of corporate tax revenue: ~0.3-0.5
    - Pass-through allocation responds to rate differentials
    """

    # Rate change (additive, e.g., +0.07 for 21%→28%)
    rate_change: float = 0.0
    baseline_rate: float = CURRENT_CORPORATE_RATE
    new_rate: Optional[float] = None  # Alternative: specify new rate directly

    # Behavioral response
    # Corporate income elasticity is lower than individual ETI
    # CBO/JCT use ~0.2-0.3 for corporate
    corporate_elasticity: float = 0.25

    # Revenue base
    # If not provided, uses default baseline
    baseline_revenue_billions: float = BASELINE_CORPORATE_REVENUE_BILLIONS
    baseline_profits_billions: float = BASELINE_TAXABLE_PROFITS_BILLIONS

    # Pass-through income effects
    # When corporate rate changes, some income shifts to/from pass-through
    include_passthrough_effects: bool = True
    passthrough_shift_elasticity: float = 0.15  # Share of pass-through that shifts

    # International provisions
    # GILTI: Global Intangible Low-Taxed Income (anti-offshoring)
    # FDII: Foreign-Derived Intangible Income (export incentive)
    gilti_rate_change: float = 0.0  # Change in GILTI rate (currently 10.5%)
    fdii_rate_change: float = 0.0  # Change in FDII rate (currently 13.125%)
    eliminate_fdii: bool = False  # Biden proposal to repeal FDII

    # R&D expensing
    # TCJA requires R&D amortization over 5 years starting 2022
    restore_rd_expensing: bool = False  # Bipartisan proposal to restore immediate expensing

    # Bonus depreciation
    # TCJA 100% bonus depreciation phasing down: 80% (2023), 60% (2024), 40% (2025), 20% (2026), 0% (2027)
    extend_bonus_depreciation: bool = False  # Extend 100% bonus depreciation

    # Book minimum tax (IRA 2022)
    # 15% minimum on adjusted financial statement income for >$1B corps
    adjust_book_minimum: bool = False
    book_minimum_rate_change: float = 0.0  # Change in 15% rate

    def __post_init__(self):
        """Set policy type to corporate."""
        self.policy_type = PolicyType.CORPORATE_TAX

    def _get_reform_rate(self) -> float:
        """Get the reform corporate tax rate."""
        if self.new_rate is not None:
            return float(self.new_rate)
        return float(self.baseline_rate + self.rate_change)

    def estimate_static_revenue_effect(self, baseline_revenue: float,
                                       use_real_data: bool = True) -> float:
        """
        Estimate static revenue effect from corporate rate change.

        For corporate tax, the static formula is simpler:
            ΔRevenue = ΔRate × Taxable_Profits

        This gives the mechanical revenue change before behavioral responses.

        Args:
            baseline_revenue: Baseline corporate revenue (can use or override)
            use_real_data: Whether to use empirical baseline data

        Returns:
            Static revenue change in billions (positive = revenue gain)
        """
        # Use stored profits base or estimate from revenue
        profits = self.baseline_profits_billions
        if profits <= 0:
            # Estimate from baseline revenue and current rate
            profits = baseline_revenue / self.baseline_rate if self.baseline_rate > 0 else 0

        # Core rate change effect
        rate_change = self._get_reform_rate() - self.baseline_rate
        static_effect = rate_change * profits

        # Add international provision effects
        static_effect += self._estimate_international_effects()

        # Add R&D expensing effect
        static_effect += self._estimate_rd_effect()

        # Add bonus depreciation effect
        static_effect += self._estimate_bonus_depreciation_effect()

        # Add book minimum effect
        static_effect += self._estimate_book_minimum_effect()

        return static_effect

    def _estimate_international_effects(self) -> float:
        """Estimate revenue from GILTI/FDII changes."""
        effect = 0.0

        # GILTI rate change (higher rate = more revenue)
        if self.gilti_rate_change != 0:
            # GILTI base ~$250B, taxed at 10.5%
            gilti_base = 250.0
            effect += self.gilti_rate_change * gilti_base

        # FDII repeal (eliminating deduction = revenue gain)
        if self.eliminate_fdii:
            # FDII costs ~$20B/year in revenue
            effect += FDII_COST_BILLIONS

        return effect

    def _estimate_rd_effect(self) -> float:
        """Estimate revenue from R&D expensing changes."""
        if not self.restore_rd_expensing:
            return 0.0

        # Restoring R&D expensing costs ~$10-15B/year
        # This is a timing difference that grows over time
        return -12.0  # Costs $12B/year on average

    def _estimate_bonus_depreciation_effect(self) -> float:
        """Estimate revenue from bonus depreciation changes."""
        if not self.extend_bonus_depreciation:
            return 0.0

        # Extending 100% bonus depreciation costs ~$25-30B/year
        # Phaseout schedule: current law raises revenue as bonus % drops
        return -28.0  # Costs $28B/year on average to extend

    def _estimate_book_minimum_effect(self) -> float:
        """Estimate revenue from book minimum tax changes."""
        if not self.adjust_book_minimum or self.book_minimum_rate_change == 0:
            return 0.0

        # Book minimum affects ~150 corporations with >$1B AFSI
        # Base: ~$100B in AFSI subject to minimum
        book_minimum_base = 100.0
        return self.book_minimum_rate_change * book_minimum_base

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to corporate tax change.

        Corporate behavioral responses include:
        1. Investment reduction (lowers profits and future revenue)
        2. Profit shifting (international tax planning)
        3. Pass-through conversion (shift to/from S-corp/partnership form)

        The offset is smaller than individual ETI because:
        - Corporate profits are less elastic than taxable income
        - Less ability to shift timing (vs individual cap gains)

        Returns:
            Behavioral offset in billions (positive = revenue lost)
        """
        # Base behavioral offset
        base_offset = abs(static_effect) * self.corporate_elasticity * 0.5

        # Pass-through shift effect
        if self.include_passthrough_effects and self.rate_change != 0:
            # When corporate rate rises, some businesses convert to pass-through
            # When corporate rate falls, some pass-through converts to C-corp
            passthrough_shift = self._estimate_passthrough_shift()
            base_offset += passthrough_shift

        return base_offset

    def _estimate_passthrough_shift(self) -> float:
        """
        Estimate revenue effect from pass-through/C-corp shifting.

        When corporate rate rises relative to individual rates:
        - Some C-corps convert to S-corps/partnerships
        - Revenue shifts from corporate to individual tax

        When corporate rate falls:
        - Some pass-throughs convert to C-corps
        - Revenue shifts from individual to corporate

        The NET revenue effect depends on rate differential.
        """
        # Current individual top rate: 37% (or 29.6% with 199A deduction)
        individual_effective_rate = 0.296  # With 199A deduction
        new_corporate_rate = self._get_reform_rate()

        # Rate differential drives shifting
        rate_differential = new_corporate_rate - individual_effective_rate

        # If corporate rate exceeds individual, income shifts OUT of C-corps
        # Passthrough income is ~$1.4T; assume 5-10% is marginal
        marginal_passthrough = BASELINE_PASSTHROUGH_INCOME_BILLIONS * 0.07

        # Shift reduces corporate revenue (lost to individual side)
        # But we only count the NET effect (some is recaptured at individual rates)
        if rate_differential > 0:
            # Corporate rate > individual: income shifts to pass-through
            shift_amount = marginal_passthrough * self.passthrough_shift_elasticity
            # Net revenue loss: lose corporate tax, but gain some at individual rate
            net_loss = shift_amount * (new_corporate_rate - individual_effective_rate)
            return abs(net_loss)  # Return as positive offset (revenue lost)
        else:
            # Corporate rate < individual: income shifts TO C-corp
            # This is a revenue GAIN (offset reduces the loss)
            return 0.0  # Captured in base elasticity

    def get_component_breakdown(self) -> dict:
        """
        Get detailed breakdown of corporate tax effects.

        Returns dict with:
        - rate_change_effect: From core rate change
        - international_effect: From GILTI/FDII changes
        - rd_effect: From R&D expensing
        - depreciation_effect: From bonus depreciation
        - book_minimum_effect: From 15% minimum tax
        - behavioral_offset: From behavioral responses
        """
        profits = self.baseline_profits_billions
        rate_change = self._get_reform_rate() - self.baseline_rate

        rate_effect = rate_change * profits
        intl_effect = self._estimate_international_effects()
        rd_effect = self._estimate_rd_effect()
        depreciation_effect = self._estimate_bonus_depreciation_effect()
        book_min_effect = self._estimate_book_minimum_effect()

        static_total = rate_effect + intl_effect + rd_effect + depreciation_effect + book_min_effect
        behavioral = self.estimate_behavioral_offset(static_total)

        return {
            "rate_change_effect": rate_effect,
            "international_effect": intl_effect,
            "rd_effect": rd_effect,
            "depreciation_effect": depreciation_effect,
            "book_minimum_effect": book_min_effect,
            "static_total": static_total,
            "behavioral_offset": behavioral,
            "net_effect": static_total - behavioral,  # Behavioral offset reduces revenue
        }


def create_corporate_rate_change(
    rate_change: float,
    name: str = "Corporate Rate Change",
    include_behavioral: bool = True,
    include_passthrough: bool = True,
    start_year: int = 2025,
    duration_years: int = 10,
) -> CorporateTaxPolicy:
    """
    Create a simple corporate rate change policy.

    Args:
        rate_change: Change in corporate rate (e.g., +0.07 for 21%→28%)
        name: Policy name
        include_behavioral: Include behavioral response
        include_passthrough: Include pass-through shifting
        start_year: Year policy takes effect
        duration_years: Duration of policy

    Returns:
        CorporateTaxPolicy configured for rate change
    """
    new_rate = CURRENT_CORPORATE_RATE + rate_change
    return CorporateTaxPolicy(
        name=name,
        description=f"Change corporate rate from {CURRENT_CORPORATE_RATE*100:.0f}% to {new_rate*100:.0f}%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=rate_change,
        baseline_rate=CURRENT_CORPORATE_RATE,
        corporate_elasticity=0.25 if include_behavioral else 0.0,
        include_passthrough_effects=include_passthrough,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_corporate_rate_only() -> CorporateTaxPolicy:
    """
    Create Biden's corporate rate increase (21%→28%) without international changes.

    This matches the CBO/Treasury estimate of ~$1.35T over 10 years for just
    the rate increase component.
    """
    return CorporateTaxPolicy(
        name="Biden Corporate Rate to 28%",
        description="Biden proposal: raise corporate rate from 21% to 28%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=0.07,  # 21% → 28%
        baseline_rate=CURRENT_CORPORATE_RATE,
        corporate_elasticity=0.25,
        include_passthrough_effects=True,
        # No international changes - just rate
        gilti_rate_change=0.0,
        eliminate_fdii=False,
        start_year=2025,
        duration_years=10,
    )


def create_biden_corporate_proposal() -> CorporateTaxPolicy:
    """
    Create Biden's full FY2025 corporate tax proposal.

    Key components:
    - Raise corporate rate from 21% to 28% (~$1.35T)
    - Increase GILTI rate from 10.5% to 21% (~$300B)
    - Eliminate FDII deduction (~$200B)
    - Other international changes

    Full package estimate: ~$1.8-2.0T over 10 years
    """
    return CorporateTaxPolicy(
        name="Biden Corporate Package (FY2025)",
        description="Biden FY2025 corporate proposals: 28% rate + GILTI increase + FDII repeal",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=0.07,  # 21% → 28%
        baseline_rate=CURRENT_CORPORATE_RATE,
        corporate_elasticity=0.25,
        include_passthrough_effects=True,
        # International provisions
        gilti_rate_change=0.105,  # 10.5% → 21% (double the rate)
        eliminate_fdii=True,
        start_year=2025,
        duration_years=10,
    )


def create_tcja_corporate_repeal() -> CorporateTaxPolicy:
    """
    Create policy to repeal TCJA corporate rate cut (restore 35%).

    This would raise corporate rate from 21% back to 35%.
    Revenue estimate: ~$1.7-2.0T over 10 years (larger than Biden due to higher rate)
    """
    return CorporateTaxPolicy(
        name="Repeal TCJA Corporate Cut",
        description="Restore corporate rate to pre-TCJA 35%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=0.14,  # 21% → 35%
        baseline_rate=CURRENT_CORPORATE_RATE,
        corporate_elasticity=0.30,  # Higher elasticity for larger change
        include_passthrough_effects=True,
        start_year=2025,
        duration_years=10,
    )


def create_republican_corporate_cut() -> CorporateTaxPolicy:
    """
    Create policy for further corporate rate reduction (Trump 2024 proposal).

    Lower corporate rate from 21% to 15%.
    Revenue estimate: ~-$600-700B over 10 years
    """
    return CorporateTaxPolicy(
        name="Trump Corporate Rate Cut",
        description="Reduce corporate rate from 21% to 15%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=-0.06,  # 21% → 15%
        baseline_rate=CURRENT_CORPORATE_RATE,
        corporate_elasticity=0.25,
        include_passthrough_effects=True,
        extend_bonus_depreciation=True,  # Usually paired with depreciation extension
        start_year=2025,
        duration_years=10,
    )


def estimate_corporate_rate_revenue(
    rate_change: float,
    include_behavioral: bool = True,
) -> dict:
    """
    Quick estimate of corporate rate change revenue.

    Args:
        rate_change: Change in rate (e.g., +0.07)
        include_behavioral: Include behavioral response

    Returns:
        Dict with 10-year estimate and component breakdown
    """
    policy = create_corporate_rate_change(
        rate_change=rate_change,
        include_behavioral=include_behavioral,
    )

    # Get annual effects
    static = policy.estimate_static_revenue_effect(BASELINE_CORPORATE_REVENUE_BILLIONS)
    behavioral = policy.estimate_behavioral_offset(static) if include_behavioral else 0.0

    # 10-year projection with growth
    annual_net = static - behavioral  # Behavioral reduces revenue
    growth_rate = 0.04  # ~4% annual growth in corporate profits

    ten_year_total = 0.0
    annual_effects = []
    for year in range(10):
        year_effect = annual_net * ((1 + growth_rate) ** year)
        annual_effects.append(year_effect)
        ten_year_total += year_effect

    return {
        "rate_change": rate_change,
        "new_rate": CURRENT_CORPORATE_RATE + rate_change,
        "static_annual": static,
        "behavioral_annual": behavioral,
        "net_annual": annual_net,
        "ten_year_total": ten_year_total,
        "annual_effects": annual_effects,
        "breakdown": policy.get_component_breakdown(),
    }
