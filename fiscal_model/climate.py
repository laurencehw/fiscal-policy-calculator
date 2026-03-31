"""
Climate & Energy Policy Revenue Module

Models revenue and spending effects from climate/energy policy changes including:
1. IRA clean energy credit repeal or extension
2. Carbon tax (various price levels)
3. EV credit changes
4. Clean energy standards

Key estimates:
- IRA clean energy credits total: ~$783B/10yr (CBO March 2024, revised up from $369B)
- Carbon tax $50/ton: raises ~$1.5-2.0T/10yr (CBO-style estimate)
- EV credit repeal: saves ~$200B/10yr
- IRA extension beyond 2032: costs ~$400B additional

References:
- CBO (2024): Budgetary Effects of IRA Energy-Related Tax Provisions
- EPA (2023): Social Cost of Carbon — $51/ton (Biden administration)
- CBO (2023): Effects of a Carbon Tax on the U.S. Economy
- EIA (2024): Annual Energy Outlook — U.S. CO2 emissions baseline
"""

from dataclasses import dataclass
from enum import Enum

from .policies import Policy, PolicyType


class ClimatePolicyType(Enum):
    IRA_REPEAL = "ira_repeal"
    IRA_EXTENSION = "ira_extension"
    CARBON_TAX = "carbon_tax"
    EV_CREDIT_CHANGE = "ev_credit_change"
    CLEAN_ENERGY_STANDARD = "clean_energy_standard"
    CUSTOM = "custom"


# Baseline data calibrated to CBO/JCT and EPA estimates
CLIMATE_BASELINE = {
    # IRA clean energy credits (CBO March 2024 revised estimate)
    "ira_total_10yr_billions": 783.0,       # Total IRA clean energy credits over 10 years
    "ira_ev_credits_10yr_billions": 200.0,  # EV tax credits (30D, 45W)
    "ira_renewable_10yr_billions": 250.0,   # Renewable energy PTC/ITC (45, 48)
    "ira_manufacturing_10yr_billions": 100.0,  # Clean manufacturing credits (45X, 48C)
    "ira_other_10yr_billions": 233.0,       # Other credits (45Q, 45V, 45Z, etc.)
    "ira_annual_avg_billions": 78.3,        # Average annual IRA credit cost

    # IRA extension beyond 2032
    "ira_extension_5yr_billions": 400.0,    # Cost of 5-year extension beyond 2032

    # U.S. emissions baseline
    "us_co2_emissions_gt_per_year": 5.0,    # U.S. CO2 emissions (gigatons/year)
    "us_co2_emissions_tons_per_year": 5.0e9,  # Same in metric tons

    # Social cost of carbon (EPA 2023, Biden administration)
    "social_cost_of_carbon_per_ton": 51.0,  # $/ton CO2

    # Carbon tax parameters
    "carbon_tax_base_revenue_per_dollar": 5.0,  # $B revenue per $1/ton tax (before behavioral)
    "carbon_tax_emissions_elasticity": -0.3,    # 30% reduction per doubling of price
    "carbon_tax_reference_price": 50.0,         # Reference price for elasticity calibration
    # Behavioral reduction factor: fraction of gross revenue lost to emissions decline
    # Calibrated so $50/ton yields ~$170B/yr avg → ~$1.7T/10yr (CBO-style)
    "carbon_tax_behavioral_factor": 0.50,       # 50% revenue erosion from behavioral response

    # EV credits
    "ev_credit_per_vehicle": 7500.0,        # Current per-vehicle credit ($7,500)
    "ev_sales_millions_per_year": 1.5,      # Current annual EV sales (millions)
    "ev_sales_growth_rate": 0.15,           # 15% annual growth in EV adoption

    # Clean energy standard
    "electricity_sector_emissions_gt": 1.6,   # Electricity sector CO2 (GT/year)
    "ces_compliance_cost_per_ton": 30.0,      # Avg compliance cost under CES
}

CBO_CLIMATE_ESTIMATES = {
    "repeal_ira_credits": {
        "10yr_score": 783.0,
        "source": "CBO (2024)",
        "description": "Repeal all IRA clean energy tax credits (saves $783B/10yr)",
    },
    "carbon_tax_50": {
        "10yr_score": -1700.0,
        "source": "CBO-style estimate",
        "description": "Carbon tax at $50/ton with 5% annual escalator",
    },
    "carbon_tax_25": {
        "10yr_score": -1000.0,
        "source": "CBO-style estimate",
        "description": "Carbon tax at $25/ton with 5% annual escalator",
    },
    "ev_credit_repeal": {
        "10yr_score": 200.0,
        "source": "CBO (2024)",
        "description": "Repeal EV tax credits only (30D, 45W)",
    },
    "extend_ira_credits": {
        "10yr_score": -400.0,
        "source": "CBO-style estimate",
        "description": "Extend IRA clean energy credits 5 years beyond 2032",
    },
}


@dataclass
class ClimateEnergyPolicy(Policy):
    """
    Climate and energy policy.

    Models fiscal effects from carbon pricing, clean energy credits,
    and EV subsidies. Includes environmental metrics (emissions reduction,
    social cost of carbon).
    """
    reform_type: ClimatePolicyType = ClimatePolicyType.CUSTOM

    # Carbon tax parameters
    carbon_tax_per_ton: float = 0.0          # $/ton CO2
    carbon_tax_growth_rate: float = 0.05     # 5% annual price increase

    # EV credit change
    ev_credit_change: float = 0.0            # Change in per-vehicle credit (current $7,500)

    # IRA credit controls
    repeal_ira_credits: bool = False          # Repeal all IRA clean energy credits
    extend_ira_credits: bool = False          # Extend IRA credits beyond 2032
    ira_extension_years: int = 5             # How many years to extend

    # Behavioral parameters
    emissions_elasticity: float = -0.3       # Emissions response to price (negative)

    # Environmental output toggle
    include_emissions_impact: bool = True    # Include CO2/environmental metrics

    def __post_init__(self):
        # Set policy_type based on reform_type before calling super
        if self.reform_type in (
            ClimatePolicyType.CARBON_TAX,
            ClimatePolicyType.CLEAN_ENERGY_STANDARD,
        ):
            self.policy_type = PolicyType.EXCISE_TAX
        elif self.reform_type in (
            ClimatePolicyType.IRA_REPEAL,
            ClimatePolicyType.IRA_EXTENSION,
            ClimatePolicyType.EV_CREDIT_CHANGE,
        ):
            self.policy_type = PolicyType.MANDATORY_SPENDING
        # For CUSTOM, infer from fields
        elif self.reform_type == ClimatePolicyType.CUSTOM:
            if self.carbon_tax_per_ton > 0:
                self.policy_type = PolicyType.EXCISE_TAX
            else:
                self.policy_type = PolicyType.MANDATORY_SPENDING
        super().__post_init__()

    def estimate_cost_effect(self, baseline_cost: float = 0.0) -> float:
        """
        Estimate annual budgetary impact.

        Returns:
            Billions per year. Negative = increases revenue / reduces deficit.
            Positive = increases spending / increases deficit.
        """
        total = 0.0

        # IRA repeal saves money (positive = deficit reduction in spending terms)
        if self.repeal_ira_credits:
            total -= CLIMATE_BASELINE["ira_annual_avg_billions"]

        # IRA extension costs money (only during extension years, not full window)
        if self.extend_ira_credits:
            # Extension cost is spread over extension years, then averaged over budget window
            annual_extension_cost = (
                CLIMATE_BASELINE["ira_extension_5yr_billions"]
                / max(1, self.duration_years)
            )
            total += annual_extension_cost

        # EV credit change (reduction saves, increase costs)
        if self.ev_credit_change != 0:
            total += self._estimate_ev_credit_impact()

        # Carbon tax raises revenue (returned as negative = deficit reduction)
        if self.carbon_tax_per_ton > 0:
            # Use average across budget window for annual estimate
            total -= self._estimate_carbon_tax_revenue_avg()

        return total

    def estimate_carbon_tax_revenue(self, year_offset: int = 0) -> float:
        """
        Estimate carbon tax revenue for a specific year.

        The tax price escalates annually, but emissions decline in response,
        so revenue eventually peaks and falls.

        Uses a calibrated model:
        - Gross revenue = price * baseline_emissions
        - Behavioral reduction grows over time as emissions respond
        - Net revenue = gross * (1 - behavioral_factor * cumulative_price_pressure)

        Calibrated so $50/ton yields ~$170B/yr average (~$1.7T/10yr).

        Args:
            year_offset: Years since policy start (0 = first year)

        Returns:
            Revenue in billions (positive = revenue raised)
        """
        if self.carbon_tax_per_ton <= 0:
            return 0.0

        base = CLIMATE_BASELINE

        # Tax price escalates over time
        price = self.carbon_tax_per_ton * (1 + self.carbon_tax_growth_rate) ** year_offset

        # Gross revenue before behavioral response
        gross_revenue = price * base["us_co2_emissions_tons_per_year"] / 1e9

        # Behavioral reduction: emissions decline over time in response to price
        # The reduction factor grows as cumulative price exposure increases
        # Year 0: small reduction; Year 9: larger reduction
        behavioral_factor = base["carbon_tax_behavioral_factor"]
        # Scale behavioral response: sqrt of price ratio gives diminishing returns
        # at high prices but still meaningful reduction at low prices
        price_ratio = price / base["carbon_tax_reference_price"]
        import math
        price_scale = math.sqrt(min(price_ratio, 4.0))
        # Cumulative behavioral response grows with time and price
        year_factor = min(1.0, (year_offset + 1) / self.duration_years)
        effective_reduction = behavioral_factor * (0.5 + 0.5 * year_factor) * price_scale

        # Net revenue after behavioral offset
        net_revenue = gross_revenue * max(0.2, 1.0 - effective_reduction)

        return net_revenue

    def _estimate_carbon_tax_revenue_avg(self) -> float:
        """Average annual carbon tax revenue over the budget window."""
        total = 0.0
        for yr in range(self.duration_years):
            total += self.estimate_carbon_tax_revenue(year_offset=yr)
        return total / self.duration_years

    def _estimate_ev_credit_impact(self) -> float:
        """
        Estimate annual budgetary impact of EV credit changes.

        Returns:
            Billions per year. Positive = costs money. Negative = saves money.
        """
        base = CLIMATE_BASELINE
        current_credit = base["ev_credit_per_vehicle"]
        new_credit = current_credit + self.ev_credit_change

        if new_credit < 0:
            new_credit = 0.0

        # Average EV sales over budget window (growing market)
        avg_sales = base["ev_sales_millions_per_year"]
        growth = base["ev_sales_growth_rate"]
        total_sales = 0.0
        for yr in range(self.duration_years):
            total_sales += avg_sales * (1 + growth) ** yr
        avg_annual_sales = total_sales / self.duration_years

        # Change in credit cost
        credit_change_per_vehicle = new_credit - current_credit
        annual_cost_change = credit_change_per_vehicle * avg_annual_sales * 1e6 / 1e9

        return annual_cost_change

    def estimate_emissions_reduction(self) -> float:
        """
        Estimate total CO2 emissions reduction over the budget window.

        Returns:
            Gigatons of CO2 reduced over the full budget window.
        """
        if not self.include_emissions_impact:
            return 0.0

        base = CLIMATE_BASELINE
        total_reduction_gt = 0.0

        # Carbon tax emissions reduction
        if self.carbon_tax_per_ton > 0:
            reference_price = base["carbon_tax_reference_price"]
            baseline_emissions = base["us_co2_emissions_gt_per_year"]
            behavioral_factor = base["carbon_tax_behavioral_factor"]

            import math
            for yr in range(self.duration_years):
                price = self.carbon_tax_per_ton * (1 + self.carbon_tax_growth_rate) ** yr
                price_ratio = price / reference_price
                price_scale = math.sqrt(min(price_ratio, 4.0))
                year_factor = min(1.0, (yr + 1) / self.duration_years)
                # Emissions reduction mirrors the behavioral factor used in revenue
                reduction_pct = behavioral_factor * (0.5 + 0.5 * year_factor) * price_scale
                reduction_pct = min(reduction_pct, 0.8)  # Cap at 80% reduction
                total_reduction_gt += baseline_emissions * reduction_pct

        # IRA repeal increases emissions (less clean energy investment)
        if self.repeal_ira_credits:
            # IRA estimated to reduce emissions by ~1 GT over 10 years
            total_reduction_gt -= 1.0

        # IRA extension further reduces emissions
        if self.extend_ira_credits:
            # Proportional to extension length relative to original 10-year window
            total_reduction_gt += 1.0 * (self.ira_extension_years / 10.0)

        return total_reduction_gt

    def get_environmental_metrics(self) -> dict:
        """
        Get environmental impact metrics.

        Returns:
            Dict with CO2 reduction, revenue, consumer cost, and social benefit.
        """
        base = CLIMATE_BASELINE

        co2_reduction_gt = self.estimate_emissions_reduction()
        co2_reduction_tons = co2_reduction_gt * 1e9

        # Social benefit of emissions reduction
        social_benefit_billions = (
            co2_reduction_tons * base["social_cost_of_carbon_per_ton"] / 1e9
        )

        # Carbon tax revenue (total over window)
        total_revenue = 0.0
        if self.carbon_tax_per_ton > 0:
            for yr in range(self.duration_years):
                total_revenue += self.estimate_carbon_tax_revenue(year_offset=yr)

        # Consumer cost (higher energy prices from carbon tax)
        # Rough estimate: ~60% of carbon tax cost passed to consumers
        consumer_cost_billions = total_revenue * 0.6

        return {
            "co2_reduction_gt": round(co2_reduction_gt, 2),
            "co2_reduction_pct": round(
                co2_reduction_gt / (base["us_co2_emissions_gt_per_year"] * self.duration_years) * 100,
                1,
            ) if co2_reduction_gt != 0 else 0.0,
            "total_revenue_billions": round(total_revenue, 1),
            "social_benefit_billions": round(social_benefit_billions, 1),
            "consumer_cost_billions": round(consumer_cost_billions, 1),
            "net_social_benefit_billions": round(
                social_benefit_billions - consumer_cost_billions, 1
            ),
            "social_cost_of_carbon_per_ton": base["social_cost_of_carbon_per_ton"],
        }


# Factory functions

def create_repeal_ira_credits() -> ClimateEnergyPolicy:
    """Full repeal of IRA clean energy credits (saves ~$783B/10yr)."""
    return ClimateEnergyPolicy(
        name="Repeal IRA Clean Energy Credits",
        description=(
            "Repeal all IRA clean energy tax credits including EV, renewable, "
            "and manufacturing credits. Estimated: +\\$783B/10yr savings."
        ),
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=ClimatePolicyType.IRA_REPEAL,
        repeal_ira_credits=True,
    )


def create_carbon_tax_50() -> ClimateEnergyPolicy:
    """Carbon tax at $50/ton with 5% annual escalator (raises ~$1.7T/10yr)."""
    return ClimateEnergyPolicy(
        name="Carbon Tax (\\$50/ton)",
        description=(
            "Economy-wide carbon tax starting at \\$50/ton CO2 with 5% annual escalator. "
            "Estimated: -\\$1.7T/10yr revenue."
        ),
        policy_type=PolicyType.EXCISE_TAX,
        reform_type=ClimatePolicyType.CARBON_TAX,
        carbon_tax_per_ton=50.0,
        carbon_tax_growth_rate=0.05,
    )


def create_carbon_tax_25() -> ClimateEnergyPolicy:
    """Carbon tax at $25/ton with 5% annual escalator (raises ~$1.0T/10yr)."""
    return ClimateEnergyPolicy(
        name="Carbon Tax (\\$25/ton)",
        description=(
            "Economy-wide carbon tax starting at \\$25/ton CO2 with 5% annual escalator. "
            "Estimated: -\\$1.0T/10yr revenue."
        ),
        policy_type=PolicyType.EXCISE_TAX,
        reform_type=ClimatePolicyType.CARBON_TAX,
        carbon_tax_per_ton=25.0,
        carbon_tax_growth_rate=0.05,
    )


def create_repeal_ev_credits() -> ClimateEnergyPolicy:
    """Repeal EV tax credits only (saves ~$200B/10yr)."""
    return ClimateEnergyPolicy(
        name="Repeal EV Tax Credits",
        description=(
            "Repeal EV purchase credits (Section 30D, 45W) while keeping other "
            "IRA clean energy provisions. Estimated: +\\$200B/10yr savings."
        ),
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=ClimatePolicyType.EV_CREDIT_CHANGE,
        ev_credit_change=-7500.0,  # Eliminate the full $7,500 credit
    )


def create_extend_ira() -> ClimateEnergyPolicy:
    """Extend IRA clean energy credits 5 years beyond 2032 (costs ~$400B)."""
    return ClimateEnergyPolicy(
        name="Extend IRA Credits (5 years)",
        description=(
            "Extend all IRA clean energy tax credits 5 years beyond their 2032 "
            "expiration. Estimated: +\\$400B/5yr additional cost."
        ),
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=ClimatePolicyType.IRA_EXTENSION,
        extend_ira_credits=True,
        ira_extension_years=5,
    )


# Validation scenarios
CLIMATE_VALIDATION_SCENARIOS = {
    "repeal_ira_credits": {
        "description": "Full repeal of IRA clean energy credits",
        "expected_10yr": 783.0,
        "source": "CBO (2024)",
    },
    "carbon_tax_50": {
        "description": "Carbon tax at $50/ton with 5% escalator",
        "expected_10yr": -1700.0,
        "source": "CBO-style estimate",
    },
    "carbon_tax_25": {
        "description": "Carbon tax at $25/ton with 5% escalator",
        "expected_10yr": -1000.0,
        "source": "CBO-style estimate",
    },
    "ev_credit_repeal": {
        "description": "Repeal EV credits only",
        "expected_10yr": 200.0,
        "source": "CBO (2024)",
    },
    "extend_ira_5yr": {
        "description": "Extend IRA credits 5 years beyond 2032",
        "expected_10yr": -400.0,
        "source": "CBO-style estimate",
    },
}
