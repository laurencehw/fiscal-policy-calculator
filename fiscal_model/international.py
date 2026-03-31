"""
International Tax Policy Module

Models international corporate tax provisions including:
1. GILTI reform (Global Intangible Low-Taxed Income)
2. FDII repeal/reform (Foreign-Derived Intangible Income)
3. Pillar Two global minimum tax (15% minimum)
4. Country-by-country minimum tax (UTPR)
5. Profit shifting / base erosion provisions

Key parameters calibrated to CBO/JCT estimates:
- GILTI reform (Biden): raises ~$280B/10yr (Treasury FY2025)
- FDII repeal: raises ~$200B/10yr
- Pillar Two adoption: raises ~$50-120B/10yr (JCT estimates vary)
- Combined Biden international package: ~$700-900B/10yr

References:
- Treasury Green Book FY2025
- JCT (2023): Pillar Two revenue estimates
- OECD (2024): Pillar Two implementation guidance
- Clausing (2020): Profit shifting estimates
"""

from dataclasses import dataclass
from enum import Enum

from .policies import PolicyType, TaxPolicy


class InternationalReformType(Enum):
    GILTI_REFORM = "gilti_reform"
    FDII_REPEAL = "fdii_repeal"
    PILLAR_TWO = "pillar_two"
    UTPR = "utpr"  # Undertaxed Profits Rule
    CUSTOM = "custom"


# Baseline data (2024)
INTERNATIONAL_BASELINE = {
    # GILTI (current law post-TCJA)
    "gilti_rate": 0.105,  # 10.5% effective rate (50% deduction on 21%)
    "gilti_base_billions": 250.0,  # Taxable GILTI ~$250B/year
    "gilti_revenue_billions": 25.0,  # Current GILTI revenue ~$25B/yr
    "gilti_qbai_exemption_rate": 0.10,  # 10% return on QBAI exempt
    "gilti_high_tax_exclusion_rate": 0.90,  # 90% of US rate threshold
    "gilti_qbai_exempt_income_billions": 100.0,  # ~$100B currently exempt
    "gilti_cbc_revenue_multiplier": 1.35,  # ~35% revenue increase from per-country
    "current_corporate_rate": 0.21,  # US statutory corporate rate

    # FDII (current law)
    "fdii_deduction_rate": 0.375,  # 37.5% deduction -> 13.125% effective
    "fdii_base_billions": 160.0,  # FDII-eligible income ~$160B
    "fdii_cost_billions": 20.0,  # Tax expenditure ~$20B/year

    # Profit shifting
    "shifted_profits_billions": 300.0,  # Estimated shifted profits (Clausing 2020)
    "tax_haven_rate": 0.05,  # Average effective rate in havens

    # Pillar Two
    "pillar_two_rate": 0.15,  # Global minimum 15%
    "undertaxed_profits_billions": 120.0,  # US MNE profits taxed below 15%
    "foreign_undertaxed_in_us_billions": 30.0,  # Foreign MNE profits in US below 15%
    "pillar_two_carveout_fraction": 0.6,  # ~60% subject after substance carve-outs (OECD)
    "utpr_capture_rate": 0.5,  # ~50% of undertaxed profits captured by UTPR
    "behavioral_offset_factor": 0.3,  # Lower than domestic (anti-avoidance rules)
}

# CBO/JCT/Treasury estimates for validation
CBO_INTERNATIONAL_ESTIMATES = {
    "biden_gilti_reform": {
        "10yr_score": -280.0,  # Raises $280B
        "source": "Treasury FY2025 Green Book",
        "description": "Country-by-country GILTI at 21%, eliminate QBAI exemption",
    },
    "fdii_repeal": {
        "10yr_score": -200.0,
        "source": "Treasury FY2025",
        "description": "Repeal FDII deduction entirely",
    },
    "pillar_two_adoption": {
        "10yr_score": -80.0,  # Range: $50-120B
        "source": "JCT (2023)",
        "description": "Adopt OECD Pillar Two qualified domestic minimum top-up tax",
    },
    "biden_full_international": {
        "10yr_score": -700.0,
        "source": "Treasury FY2025",
        "description": "Full Biden international package (GILTI + FDII + UTPR)",
    },
}


@dataclass
class InternationalTaxPolicy(TaxPolicy):
    """
    International tax reform policy.

    Models structural changes to how US taxes multinational profits,
    not just rate changes.
    """
    # Provide default for policy_type so factories don't need to pass it explicitly
    policy_type: PolicyType = PolicyType.CORPORATE_TAX

    reform_type: InternationalReformType = InternationalReformType.CUSTOM

    # GILTI reform parameters
    gilti_country_by_country: bool = False  # Switch from blended to per-country
    gilti_new_rate: float | None = None  # New effective GILTI rate (e.g., 0.21)
    gilti_eliminate_qbai: bool = False  # Remove 10% QBAI exemption
    gilti_eliminate_high_tax_exclusion: bool = False

    # FDII parameters
    fdii_repeal: bool = False
    fdii_new_rate: float | None = None  # Modified FDII effective rate

    # Pillar Two parameters
    pillar_two_adopt: bool = False  # Adopt qualified domestic minimum top-up
    pillar_two_rate: float = 0.15  # Minimum rate (OECD standard)
    adopt_utpr: bool = False  # Undertaxed Profits Rule

    # Profit shifting parameters
    profit_shifting_elasticity: float = 0.5  # How responsive is shifting to rate gaps

    def __post_init__(self):
        self.policy_type = PolicyType.CORPORATE_TAX
        super().__post_init__()

    def estimate_static_revenue_effect(self, baseline_revenue: float,
                                       use_real_data: bool = True) -> float:
        """Estimate revenue from international tax reform."""
        total = 0.0
        total += self._estimate_gilti_reform()
        total += self._estimate_fdii_reform()
        total += self._estimate_pillar_two()
        total += self._estimate_utpr()
        return total

    def _estimate_gilti_reform(self) -> float:
        """Revenue from GILTI reform."""
        if not self.gilti_country_by_country and self.gilti_new_rate is None and not self.gilti_eliminate_qbai:
            return 0.0

        base = INTERNATIONAL_BASELINE
        current_revenue = base["gilti_revenue_billions"]
        gilti_base = base["gilti_base_billions"]

        # New effective rate
        new_rate = self.gilti_new_rate if self.gilti_new_rate is not None else base["gilti_rate"]

        # Country-by-country increases effective rate by eliminating cross-crediting
        # CBO estimates ~30-40% revenue increase from per-country
        cbc_multiplier = base["gilti_cbc_revenue_multiplier"] if self.gilti_country_by_country else 1.0

        # QBAI exemption elimination adds to the base
        qbai_addition = 0.0
        if self.gilti_eliminate_qbai:
            qbai_addition = base["gilti_qbai_exempt_income_billions"] * new_rate

        new_revenue = (gilti_base * new_rate * cbc_multiplier) + qbai_addition
        return new_revenue - current_revenue

    def _estimate_fdii_reform(self) -> float:
        """Revenue from FDII reform/repeal."""
        if not self.fdii_repeal and self.fdii_new_rate is None:
            return 0.0

        base = INTERNATIONAL_BASELINE
        if self.fdii_repeal:
            return base["fdii_cost_billions"]  # Full repeal recovers the expenditure

        # Modified FDII rate
        if self.fdii_new_rate is not None:
            current_effective = base["current_corporate_rate"] * (1 - base["fdii_deduction_rate"])
            new_effective = self.fdii_new_rate
            fdii_base = base["fdii_base_billions"]
            return (new_effective - current_effective) * fdii_base

        return 0.0

    def _estimate_pillar_two(self) -> float:
        """Revenue from Pillar Two adoption."""
        if not self.pillar_two_adopt:
            return 0.0

        base = INTERNATIONAL_BASELINE
        # Qualified Domestic Minimum Top-up Tax (QDMTT)
        # Captures US MNE profits currently taxed below 15% in foreign jurisdictions
        undertaxed = base["undertaxed_profits_billions"]
        rate_gap = max(0, self.pillar_two_rate - base["tax_haven_rate"])

        return undertaxed * rate_gap * base["pillar_two_carveout_fraction"]

    def _estimate_utpr(self) -> float:
        """Revenue from Undertaxed Profits Rule."""
        if not self.adopt_utpr:
            return 0.0

        base = INTERNATIONAL_BASELINE
        # UTPR allows taxing foreign MNE profits allocated to US
        foreign_undertaxed = base["foreign_undertaxed_in_us_billions"]
        rate_gap = max(0, self.pillar_two_rate - base["tax_haven_rate"])

        return foreign_undertaxed * rate_gap * base["utpr_capture_rate"]

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Behavioral response to international tax changes."""
        # International provisions have lower behavioral offset than domestic
        # because they're harder to avoid (anti-avoidance rules)
        # But profit shifting elasticity still matters
        base_offset = abs(static_effect) * self.profit_shifting_elasticity * INTERNATIONAL_BASELINE["behavioral_offset_factor"]
        return base_offset

    def get_component_breakdown(self) -> dict:
        """Detailed breakdown of international tax effects."""
        gilti = self._estimate_gilti_reform()
        fdii = self._estimate_fdii_reform()
        p2 = self._estimate_pillar_two()
        utpr = self._estimate_utpr()
        static_total = gilti + fdii + p2 + utpr
        behavioral = self.estimate_behavioral_offset(static_total)

        return {
            "gilti_reform": gilti,
            "fdii_reform": fdii,
            "pillar_two": p2,
            "utpr": utpr,
            "static_total": static_total,
            "behavioral_offset": behavioral,
            "net_effect": static_total - behavioral,
        }


# Factory functions

def create_biden_gilti_reform() -> InternationalTaxPolicy:
    """Biden GILTI reform: country-by-country at 21%, eliminate QBAI."""
    return InternationalTaxPolicy(
        name="Biden GILTI Reform",
        description="Country-by-country GILTI at 21% rate, eliminate QBAI exemption. Treasury estimate: -$280B/10yr.",
        reform_type=InternationalReformType.GILTI_REFORM,
        gilti_country_by_country=True,
        gilti_new_rate=0.21,
        gilti_eliminate_qbai=True,
    )


def create_fdii_repeal() -> InternationalTaxPolicy:
    """Repeal FDII deduction."""
    return InternationalTaxPolicy(
        name="Repeal FDII",
        description="Repeal Foreign-Derived Intangible Income deduction. Treasury estimate: -$200B/10yr.",
        reform_type=InternationalReformType.FDII_REPEAL,
        fdii_repeal=True,
    )


def create_pillar_two_adoption() -> InternationalTaxPolicy:
    """Adopt OECD Pillar Two 15% global minimum."""
    return InternationalTaxPolicy(
        name="Pillar Two Adoption",
        description="Adopt OECD Pillar Two qualified domestic minimum top-up tax at 15%. JCT estimate: -$80B/10yr.",
        reform_type=InternationalReformType.PILLAR_TWO,
        pillar_two_adopt=True,
        pillar_two_rate=0.15,
    )


def create_biden_full_international() -> InternationalTaxPolicy:
    """Biden full international package."""
    return InternationalTaxPolicy(
        name="Biden International Package",
        description="Full Biden international reform: GILTI at 21% per-country + FDII repeal + UTPR. Treasury estimate: -$700B/10yr.",
        reform_type=InternationalReformType.CUSTOM,
        gilti_country_by_country=True,
        gilti_new_rate=0.21,
        gilti_eliminate_qbai=True,
        fdii_repeal=True,
        adopt_utpr=True,
    )


def create_pillar_two_with_utpr() -> InternationalTaxPolicy:
    """Pillar Two with UTPR."""
    return InternationalTaxPolicy(
        name="Pillar Two + UTPR",
        description="Adopt Pillar Two minimum tax with Undertaxed Profits Rule.",
        reform_type=InternationalReformType.PILLAR_TWO,
        pillar_two_adopt=True,
        adopt_utpr=True,
        pillar_two_rate=0.15,
    )


INTERNATIONAL_VALIDATION_SCENARIOS = {
    "biden_gilti_reform": {
        "factory": "create_biden_gilti_reform",
        "expected_10yr": -280.0,
        "source": "Treasury FY2025",
    },
    "fdii_repeal": {
        "factory": "create_fdii_repeal",
        "expected_10yr": -200.0,
        "source": "Treasury FY2025",
    },
    "pillar_two": {
        "factory": "create_pillar_two_adoption",
        "expected_10yr": -80.0,
        "source": "JCT (2023)",
    },
}
