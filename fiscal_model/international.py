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
- FDII repeal: Treasury OTA prices the deduction at $130.2B/10yr
- Pillar Two adoption: raises ~$50-120B/10yr (JCT estimates vary)
- Combined Biden international package: ~$700-900B/10yr

Two things are modelled structurally rather than as constants, both added by
lane L9 of ``planning/MODELING_IMPROVEMENT.md``:

**The base overlap.** A reformed per-country GILTI and a Pillar Two top-up
reach the same profits — a US group's foreign earnings in jurisdictions whose
effective rate is below the minimum — so summing their claims books that income
twice. JCT states the fix as an ordering rule (JCX-22-23 p. 6: local corporate
income taxes, then QDMTTs, then CFC rules including GILTI, then IIRs, and
finally UTPRs) and its Equation 1 subtracts the top-up another provision has
already taken. :func:`shared_claim_share` computes how much of the smaller
claim the larger one absorbs, jurisdiction by jurisdiction, on the IRS
Country-by-Country distribution vendored in ``data_files/international/``;
:meth:`InternationalTaxPolicy._estimate_base_overlap` subtracts it.

At a 21% per-country GILTI the share is exactly 1: with an 80% foreign tax
credit, ``0.21*Y - 0.8*T`` exceeds ``0.15*Y - T`` for every positive ``Y`` and
``T``, so a 21% GILTI subsumes a 15% top-up in every jurisdiction. That is
algebra, not a property of the data. Below about 15% the two provisions
interleave and the share falls under 1, which is why it is computed rather than
asserted.

**The FDII identity.** Repeal used to return a flat $20B/yr while the
rate-change branch of the same function used ``base x rate`` on a $160B base —
$12.6B/yr, a 59% disagreement inside one function. Both branches now run the
identity, on an FDII income implied by Treasury OTA's own published tax
expenditure for the deduction. That figure ($130,230M over FY2025-2034) is 35%
below the module's old constant, so the modelled repeal falls with it.

References:
- Treasury Green Book FY2025 (Table of Revenue Estimates, report pp. 239-240)
- Treasury OTA, Tax Expenditures FY2026 (27 Nov 2024), Table 1 lines 4 and 5
- JCT, JCX-22-23, "Possible Effects of Adopting the OECD's Pillar Two"
- IRS SOI, Country-by-Country Report (Form 8975) Table 4, TY2023
- OECD (2024): Pillar Two implementation guidance
- Clausing (2020): Profit shifting estimates
"""

import csv
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from .policies import PolicyType, TaxPolicy


class InternationalReformType(Enum):
    GILTI_REFORM = "gilti_reform"
    FDII_REPEAL = "fdii_repeal"
    PILLAR_TWO = "pillar_two"
    UTPR = "utpr"  # Undertaxed Profits Rule
    CUSTOM = "custom"


# Baseline data (2024)
# Note: GILTI/FDII bases are NET of foreign tax credits and exclusions.
# Gross GILTI is ~$250B but FTCs reduce the effective taxable base significantly.
# These values are calibrated to match Treasury FY2025 Green Book estimates.
INTERNATIONAL_BASELINE = {
    # GILTI (current law post-TCJA)
    "gilti_rate": 0.105,  # 10.5% effective rate (50% deduction on 21%)
    "gilti_base_billions": 250.0,  # Gross taxable GILTI ~$250B/year
    "gilti_revenue_billions": 25.0,  # Current GILTI revenue ~$25B/yr (after FTCs)
    # Net QBAI exempt income after FTCs — Treasury estimates smaller effective base
    "gilti_qbai_exempt_income_billions": 40.0,  # ~$40B net (many MNEs already above threshold)
    # CBC multiplier — per-country eliminates cross-crediting but many jurisdictions
    # already exceed 10.5%; net effect is smaller than gross estimate
    "gilti_cbc_revenue_multiplier": 1.20,  # ~20% net revenue increase (Treasury calibrated)
    "current_corporate_rate": 0.21,  # US statutory corporate rate
    # Calibration factor: Treasury estimates net GILTI reform at $28B/yr
    # Model: (250 * 0.21 * 1.20) + (40 * 0.21) - 25 = 63.0 + 8.4 - 25 = 46.4 (static)
    # After behavioral: 46.4 * (1 - 0.5 * 0.3) = 39.4 → still too high
    # Apply FTC offset: many MNEs get credits that reduce incremental revenue
    "gilti_ftc_offset_rate": 0.40,  # ~40% of incremental revenue offset by FTCs

    # FDII (current law)
    "fdii_deduction_rate": 0.375,  # IRC 250(a)(1)(A): 37.5% -> 13.125% effective
    # Treasury OTA, Tax Expenditures FY2026, Table 1 line 5: the FDII deduction
    # costs $130,230M over FY2025-2034, i.e. $13.023B/yr. That path already
    # embeds the 250(a)(3) step-down to 21.875% from TY2026 (FY2025 $16.42B
    # falls to FY2026 $11.20B), so the window average is the right scalar for a
    # module whose interface carries no year. Dividing it by the deduction rate
    # and the statutory rate gives the FDII income the identity runs on —
    # $165.4B, within 3.4% of the $160B this module already carried, which is
    # why the old flat $20B/yr repeal figure was the outlier, not the base.
    "fdii_deduction_tax_expenditure_billions": 13.023,

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

    # Base-overlap inputs. Both are statutory/OECD parameters read only by
    # `shared_claim_share`, which uses them to decide how much of one
    # provision's claim on the low-taxed foreign-profit pool the other has
    # already taken. Neither sets a revenue level.
    "gilti_ftc_limit": 0.80,  # IRC 960(d): GILTI FTC capped at 80% of foreign tax
    # Substance-based income exclusion, tangible-asset half only. JCT JCX-22-23
    # p. 3 gives 5% of payroll *and* 5% of tangible assets; Form 8975 reports
    # employee counts rather than payroll, so the payroll half is omitted. That
    # raises the modelled top-up by about 3% and leaves the overlap share — a
    # ratio of two claims on the same base — unchanged.
    "pillar_two_sbie_tangible_rate": 0.05,
}


#: IRS SOI Country-by-Country distribution of US multinationals' foreign profit
#: that sits below a 15% effective rate. See the file's own header for the
#: provenance and for why only the *shape* of this distribution is used.
FOREIGN_PROFIT_BY_ETR_FILE = (
    Path(__file__).parent
    / "data_files"
    / "international"
    / "us_mne_foreign_profit_by_etr_2023.csv"
)


@dataclass(frozen=True)
class ForeignProfitRow:
    """One jurisdiction's low-taxed foreign profit, as filed on Form 8975."""

    jurisdiction: str
    etr_band: str
    profit_billions: float
    tax_accrued_billions: float
    tangible_assets_billions: float
    employees_thousands: float

    @property
    def effective_rate(self) -> float:
        """Income tax accrued over profit before income tax. May be negative."""
        return self.tax_accrued_billions / self.profit_billions


@lru_cache(maxsize=1)
def load_foreign_profit_by_etr() -> tuple[ForeignProfitRow, ...]:
    """Load the vendored CbCR effective-rate distribution.

    Cached: the file is a couple of dozen rows and never changes at runtime.
    """
    rows: list[ForeignProfitRow] = []
    with open(FOREIGN_PROFIT_BY_ETR_FILE, encoding="utf-8") as handle:
        reader = csv.DictReader(
            line for line in handle if not line.lstrip().startswith("#")
        )
        for record in reader:
            profit = float(record["profit_before_income_tax_billions"])
            if profit <= 0:
                # Pillar Two tops up positive excess profit only, and a
                # negative-profit row has no meaningful effective rate.
                continue
            rows.append(
                ForeignProfitRow(
                    jurisdiction=record["jurisdiction"],
                    etr_band=record["etr_band"],
                    profit_billions=profit,
                    tax_accrued_billions=float(record["income_tax_accrued_billions"]),
                    tangible_assets_billions=float(record["tangible_assets_billions"]),
                    employees_thousands=float(record["employees_thousands"]),
                )
            )
    if not rows:
        raise ValueError(
            f"No usable rows in {FOREIGN_PROFIT_BY_ETR_FILE}; the base-overlap "
            "term cannot be computed without the CbCR distribution."
        )
    return tuple(rows)


def fdii_income_billions() -> float:
    """FDII-eligible income implied by Treasury's own tax expenditure.

    The deduction is worth ``deduction_rate x statutory_rate`` per dollar of
    foreign-derived intangible income, so inverting Treasury OTA's published
    cost for the provision gives the income the identity in
    :meth:`InternationalTaxPolicy._estimate_fdii_reform` runs on:
    ``13.023 / (0.375 x 0.21) = $165.4B``.

    It is a *window-average* income over FY2025-2034 rather than a tax-year
    level, because the tax-expenditure path it inverts spans the IRC 250(a)(3)
    step-down. Deriving it rather than carrying it keeps one published number in
    the module instead of two constants that can drift apart — which is how the
    old ``fdii_cost_billions`` came to contradict ``fdii_base_billions`` by 59%.
    """
    base = INTERNATIONAL_BASELINE
    return base["fdii_deduction_tax_expenditure_billions"] / (
        base["fdii_deduction_rate"] * base["current_corporate_rate"]
    )


def shared_claim_share(gilti_rate: float, minimum_rate: float) -> float:
    """How much of the smaller provision's claim the other one already takes.

    A per-country GILTI at ``gilti_rate`` and a Pillar Two top-up to
    ``minimum_rate`` both reach a US group's foreign profit in jurisdictions
    taxed below the minimum. JCT's ordering rule (JCX-22-23 p. 6) says the two
    do not add: whichever provision reaches a jurisdiction first, the other
    collects only the increment above it. Per jurisdiction *j*, with profit
    ``Y``, accrued foreign tax ``T`` and tangible assets ``A``::

        g_j = max(0, gilti_rate * Y - ftc_limit * T)          # CFC rules
        p_j = max(0, minimum_rate - T / Y) * (Y - sbie * A)   # IIR / QDMTT
        share = sum_j min(g_j, p_j) / min(sum_j g_j, sum_j p_j)

    ``T`` is floored at zero. A jurisdiction can accrue negative current-year
    tax on positive book profit — 58 rows of Table 4 do — and letting that run
    through unclamped would credit GILTI with more than its own rate on the
    profit and top a jurisdiction up by more than the minimum rate, neither of
    which either regime does.

    The share is a ratio of two claims on one base, so it is scale-free: it
    says nothing about how much either provision raises, only how much of the
    smaller one is already inside the larger. Returns 0.0 when either provision
    claims nothing, so a caller can multiply it by ``min(gilti, pillar_two)``
    unconditionally.

    At ``gilti_rate=0.21`` and ``minimum_rate=0.15`` the share is exactly 1,
    and that is algebra rather than data: ``0.21*Y - 0.8*T`` minus
    ``0.15*Y - T`` is ``0.06*Y + 0.2*T``, positive for every positive profit
    and non-negative tax, so the 21% claim dominates everywhere.
    """
    ftc_limit = INTERNATIONAL_BASELINE["gilti_ftc_limit"]
    sbie_rate = INTERNATIONAL_BASELINE["pillar_two_sbie_tangible_rate"]

    gilti_total = 0.0
    pillar_two_total = 0.0
    shared_total = 0.0

    for row in load_foreign_profit_by_etr():
        creditable_tax = max(0.0, row.tax_accrued_billions)
        effective_rate = creditable_tax / row.profit_billions
        gilti_claim = max(
            0.0, gilti_rate * row.profit_billions - ftc_limit * creditable_tax
        )
        excess_profit = max(
            0.0,
            row.profit_billions - sbie_rate * row.tangible_assets_billions,
        )
        top_up_claim = max(0.0, minimum_rate - effective_rate) * excess_profit

        gilti_total += gilti_claim
        pillar_two_total += top_up_claim
        shared_total += min(gilti_claim, top_up_claim)

    smaller = min(gilti_total, pillar_two_total)
    if smaller <= 0.0:
        return 0.0
    return shared_total / smaller

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
        """Estimate revenue from international tax reform.

        The four provisions are summed and the revenue two of them would book
        twice is then netted out — see :meth:`_estimate_base_overlap`.
        """
        total = 0.0
        total += self._estimate_gilti_reform()
        total += self._estimate_fdii_reform()
        total += self._estimate_pillar_two()
        total += self._estimate_utpr()
        return total - self._estimate_base_overlap()

    def _estimate_gilti_reform(self) -> float:
        """Revenue from GILTI reform."""
        if not self.gilti_country_by_country and self.gilti_new_rate is None and not self.gilti_eliminate_qbai:
            return 0.0

        base = INTERNATIONAL_BASELINE
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

        # Compare reform parameters against baseline to avoid baseline mismatch
        # (theoretical baseline 250*0.105 ≈ $26.25B ≠ calibrated $25B)
        gross_delta = (gilti_base * (new_rate * cbc_multiplier - base["gilti_rate"])) + qbai_addition

        # Apply FTC offset — many MNEs get foreign tax credits that reduce
        # the incremental US tax from GILTI reform.
        # Only applies to positive delta (tax increases); tax cuts aren't offset by FTCs.
        ftc_offset = base.get("gilti_ftc_offset_rate", 0.0)
        return gross_delta * (1 - ftc_offset) if gross_delta > 0 else gross_delta

    def _estimate_fdii_reform(self) -> float:
        """Revenue from FDII reform or repeal.

        One identity for both branches. Repeal is the limiting case of a rate
        change — the deduction goes, so foreign-derived intangible income faces
        the full statutory rate — and both come out as

            (new effective rate - current effective rate) x FDII income

        with FDII income implied by Treasury OTA's own published tax expenditure
        for the deduction (see :func:`fdii_income_billions`). Repeal therefore
        returns that tax expenditure exactly, $13.0B/yr, where this branch used
        to return a flat $20B/yr that the module's own $160B base contradicted.

        Not modelled: the IRC 250(a)(3) step-down from a 37.5% to a 21.875%
        deduction in TY2026. It is inside the published path the income base is
        inverted from, so the window average reflects it, but the scalar
        interface cannot say which years are which. Nor is the interaction
        Treasury's own repeal row carries: their $157,993M is this deduction
        repealed on a baseline that already has the same volume's 28% corporate
        rate, and 13.023 x 10 x (28/21) = $173.6B before behaviour, which is
        where that row's 21% premium over the tax expenditure comes from.
        """
        if not self.fdii_repeal and self.fdii_new_rate is None:
            return 0.0

        base = INTERNATIONAL_BASELINE
        statutory_rate = base["current_corporate_rate"]
        current_effective = statutory_rate * (1 - base["fdii_deduction_rate"])
        new_effective = statutory_rate if self.fdii_repeal else self.fdii_new_rate

        return (new_effective - current_effective) * fdii_income_billions()

    def _estimate_base_overlap(self) -> float:
        """Revenue two provisions would book twice on the same profits.

        A reformed per-country GILTI and a Pillar Two top-up both reach a US
        group's foreign earnings in jurisdictions taxed below the minimum rate.
        JCT's ordering rule puts CFC rules ahead of the IIR and the UTPR
        (JCX-22-23 p. 6) and its Equation 1 subtracts what the other provision
        has already taken, so the combined take on a shared jurisdiction is the
        larger claim, not the sum. This returns the non-negative amount to
        subtract; :func:`shared_claim_share` says how much of the smaller claim
        the larger absorbs.

        Two pairs are deliberately *not* netted, because as this module defines
        them their bases are disjoint:

        * **GILTI against the UTPR.** ``_estimate_utpr`` scores
          ``foreign_undertaxed_in_us_billions`` — profits of *foreign*-parented
          groups — while ``_estimate_gilti_reform`` scores US-parented CFC
          income. ``create_biden_full_international`` combines exactly these
          two, so its overlap is zero and the package's residual against
          Treasury's subtotal is a level, not an interaction.
        * **Pillar Two against the UTPR.** Same disjoint bases, US-parented
          against foreign-parented, even though the ordering rule would net
          them if they shared one.
        """
        gilti = self._estimate_gilti_reform()
        pillar_two = self._estimate_pillar_two()
        if gilti <= 0.0 or pillar_two <= 0.0:
            return 0.0

        gilti_rate = (
            self.gilti_new_rate
            if self.gilti_new_rate is not None
            else INTERNATIONAL_BASELINE["gilti_rate"]
        )
        share = shared_claim_share(gilti_rate, self.pillar_two_rate)
        return share * min(gilti, pillar_two)

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
        overlap = self._estimate_base_overlap()
        static_total = gilti + fdii + p2 + utpr - overlap
        behavioral = self.estimate_behavioral_offset(static_total)

        return {
            "gilti_reform": gilti,
            "fdii_reform": fdii,
            "pillar_two": p2,
            "utpr": utpr,
            # Non-negative; already subtracted from static_total. Zero unless a
            # policy pulls both the GILTI and the Pillar Two levers.
            "base_overlap": overlap,
            "static_total": static_total,
            "behavioral_offset": behavioral,
            "net_effect": static_total - behavioral,
        }


# Factory functions

def create_biden_gilti_reform() -> InternationalTaxPolicy:
    """Biden GILTI reform: country-by-country at 21%, eliminate QBAI."""
    return InternationalTaxPolicy(
        name="Biden GILTI Reform",
        description="Country-by-country GILTI at 21% rate, eliminate QBAI exemption. Treasury estimate: -\\$280B/10yr.",
        reform_type=InternationalReformType.GILTI_REFORM,
        gilti_country_by_country=True,
        gilti_new_rate=0.21,
        gilti_eliminate_qbai=True,
    )


def create_fdii_repeal() -> InternationalTaxPolicy:
    """Repeal FDII deduction."""
    return InternationalTaxPolicy(
        name="Repeal FDII",
        description="Repeal Foreign-Derived Intangible Income deduction. Treasury estimate: -\\$200B/10yr.",
        reform_type=InternationalReformType.FDII_REPEAL,
        fdii_repeal=True,
    )


def create_pillar_two_adoption() -> InternationalTaxPolicy:
    """Adopt OECD Pillar Two 15% global minimum."""
    return InternationalTaxPolicy(
        name="Pillar Two Adoption",
        description="Adopt OECD Pillar Two qualified domestic minimum top-up tax at 15%. JCT estimate: -\\$80B/10yr.",
        reform_type=InternationalReformType.PILLAR_TWO,
        pillar_two_adopt=True,
        pillar_two_rate=0.15,
    )


def create_biden_full_international() -> InternationalTaxPolicy:
    """Biden full international package."""
    return InternationalTaxPolicy(
        name="Biden International Package",
        description="Biden international reform: GILTI at 21% per-country + FDII repeal + UTPR. Treasury full package: -\\$700B/10yr (model covers core provisions).",
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
