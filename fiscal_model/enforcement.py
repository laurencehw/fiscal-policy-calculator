"""
IRS Enforcement Revenue Module

Models the revenue return from increased IRS enforcement funding.
CBO and Treasury estimate significant ROI from enforcement spending:
- Audit coverage for high-income returns has dropped from 16% (2010) to 2% (2019)
- IRA 2022 provided $80B in additional IRS funding over 10 years
- CBO estimates: $1 enforcement → $5-10 in revenue (diminishing marginal return)
- Treasury estimates IRA funding raises ~$200B net over 10 years

Key assumptions:
- Revenue yield diminishes with scale (first dollars more productive)
- Takes 2-3 years to hire/train agents and build cases
- Compliance effect: some voluntary compliance improves with visible enforcement
- Revenue concentrated from high-income, corporate, partnership audits

References:
- CBO (2022): "Estimated Budgetary Effects of H.R. 5376" (IRA scoring)
- Treasury (2021): "The Case for a Robust Attack on the Tax Gap"
- IRS (2022): Tax gap estimate ~$600B/year (gross), ~$440B net
- Natasha Sarin & Larry Summers (2019): Enforcement revenue estimates
"""

from dataclasses import dataclass

from .policies import PolicyType, TaxPolicy

# Baseline data
ENFORCEMENT_BASELINE = {
    "current_irs_budget_billions": 14.0,  # FY2024 IRS budget ~$14B
    "ira_additional_billions": 80.0,  # IRA provided $80B over 10 years
    "tax_gap_gross_billions": 600.0,  # Annual gross tax gap
    "tax_gap_net_billions": 440.0,  # After enforcement + late payments
    "current_audit_rate_high_income": 0.02,  # 2% for >$1M (was 16% in 2010)
    "current_audit_rate_corporate": 0.01,  # ~1% for large corps
    "revenue_per_dollar_marginal": 5.0,  # First-dollar ROI (diminishes)
}

CBO_ENFORCEMENT_ESTIMATES = {
    "ira_enforcement": {
        "10yr_score": -200.0,  # Raises ~$200B net
        "source": "CBO (2022)",
        "description": "IRA $80B enforcement funding over 10 years",
    },
    "double_enforcement": {
        "10yr_score": -340.0,  # Diminishing returns
        "source": "Treasury (2021) / Sarin-Summers",
        "description": "Double IRS enforcement budget beyond IRA",
    },
}


@dataclass
class IRSEnforcementPolicy(TaxPolicy):
    """
    IRS enforcement funding policy.

    Models the revenue return from investing in IRS enforcement capacity.
    Unlike tax rate changes, enforcement spending has a multiplied return
    because it closes the tax gap rather than changing tax law.
    """
    # Spending parameters
    annual_enforcement_spending_billions: float = 0.0  # Additional annual spending
    total_10yr_spending_billions: float = 0.0  # Alternative: total over window

    # ROI parameters
    base_roi_multiplier: float = 5.0  # Revenue per dollar (high-income audits)
    diminishing_returns_factor: float = 0.85  # Each additional $1B yields 85% of prior

    # Phase-in (hiring/training delay)
    ramp_up_years: int = 3  # Years to reach full capacity

    # Compliance multiplier (deterrence effect)
    voluntary_compliance_boost: float = 0.15  # 15% additional from deterrence

    # Focus areas
    focus_high_income: bool = True  # Priority: >$400K returns
    focus_partnerships: bool = True  # Large partnership audits
    focus_corporate: bool = True  # Large corporate audits
    focus_crypto: bool = False  # Cryptocurrency compliance

    def __post_init__(self):
        self.policy_type = PolicyType.INCOME_TAX
        # Skip rate_change validation since this isn't a rate-based policy
        if self.start_year < 2000 or self.start_year > 2100:
            raise ValueError(f"start_year must be between 2000 and 2100, got {self.start_year}")
        if self.duration_years <= 0:
            raise ValueError(f"duration_years must be positive, got {self.duration_years}")
        if self.phase_in_years < 1:
            raise ValueError(f"phase_in_years must be >= 1, got {self.phase_in_years}")

        # Calculate annual from total if only total provided
        if self.annual_enforcement_spending_billions == 0 and self.total_10yr_spending_billions > 0:
            self.annual_enforcement_spending_billions = self.total_10yr_spending_billions / self.duration_years

    def estimate_static_revenue_effect(self, baseline_revenue: float,
                                       use_real_data: bool = True) -> float:
        """
        Estimate revenue from enforcement spending.

        Revenue = Spending × ROI × Ramp-up × (1 + compliance_boost)

        ROI diminishes with scale: each additional $1B yields diminishing_returns_factor
        of the prior billion's return.
        """
        annual_spending = self.annual_enforcement_spending_billions
        if annual_spending <= 0:
            return 0.0

        # Calculate diminishing ROI
        # First $1B at base ROI, each subsequent billion at factor^n of base
        total_revenue = 0.0
        remaining = annual_spending
        increment = 1.0  # Process in $1B chunks
        chunk_idx = 0

        while remaining > 0:
            chunk = min(increment, remaining)
            roi = self.base_roi_multiplier * (self.diminishing_returns_factor ** chunk_idx)
            total_revenue += chunk * roi
            remaining -= chunk
            chunk_idx += 1

        # Add voluntary compliance boost (deterrence effect)
        total_revenue *= (1 + self.voluntary_compliance_boost)

        # Average over ramp-up period
        # Year 1: 30%, Year 2: 60%, Year 3: 90%, Year 4+: 100%
        ramp_factor = sum(
            min(1.0, (y + 1) / self.ramp_up_years)
            for y in range(self.duration_years)
        ) / self.duration_years

        # Return as negative (reduces deficit)
        # But subtract the cost of enforcement spending itself
        net_revenue = (total_revenue * ramp_factor) - annual_spending
        return net_revenue  # Positive = net revenue gain

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Enforcement has minimal behavioral offset — it's not changing rates."""
        # Small offset for increased avoidance in response to higher audit rates
        return abs(static_effect) * 0.05

    def get_roi_summary(self) -> dict:
        """Summary of enforcement ROI."""
        gross_revenue = self.estimate_static_revenue_effect(0) + self.annual_enforcement_spending_billions
        return {
            "annual_spending": self.annual_enforcement_spending_billions,
            "gross_annual_revenue": gross_revenue,
            "net_annual_revenue": gross_revenue - self.annual_enforcement_spending_billions,
            "effective_roi": gross_revenue / self.annual_enforcement_spending_billions if self.annual_enforcement_spending_billions > 0 else 0,
        }


# Factory functions

def create_ira_enforcement() -> IRSEnforcementPolicy:
    """IRA enforcement funding ($80B/10yr)."""
    return IRSEnforcementPolicy(
        name="IRA Enforcement Funding",
        description="$80B additional IRS enforcement over 10 years (IRA 2022). CBO estimate: raises ~$200B net.",
        policy_type=PolicyType.INCOME_TAX,
        total_10yr_spending_billions=80.0,
        base_roi_multiplier=5.0,
        ramp_up_years=3,
    )

def create_double_enforcement() -> IRSEnforcementPolicy:
    """Double IRS enforcement beyond IRA."""
    return IRSEnforcementPolicy(
        name="Double IRS Enforcement",
        description="Double enforcement funding beyond IRA levels (~$16B/year additional). Higher diminishing returns.",
        policy_type=PolicyType.INCOME_TAX,
        annual_enforcement_spending_billions=16.0,
        base_roi_multiplier=4.0,  # Lower base ROI at scale
        diminishing_returns_factor=0.80,  # Faster diminishing
        ramp_up_years=4,
    )

def create_high_income_enforcement() -> IRSEnforcementPolicy:
    """Targeted high-income and partnership enforcement."""
    return IRSEnforcementPolicy(
        name="High-Income Enforcement",
        description="Targeted enforcement for >$400K returns and large partnerships. $5B/year additional.",
        policy_type=PolicyType.INCOME_TAX,
        annual_enforcement_spending_billions=5.0,
        base_roi_multiplier=7.0,  # Higher ROI for targeted high-income
        focus_high_income=True,
        focus_partnerships=True,
        focus_corporate=False,
        focus_crypto=False,
    )


ENFORCEMENT_VALIDATION_SCENARIOS = {
    "ira_enforcement": {
        "factory": "create_ira_enforcement",
        "expected_10yr": -200.0,
        "source": "CBO (2022)",
    },
}
