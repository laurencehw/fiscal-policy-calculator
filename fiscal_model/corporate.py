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

Two scoring modes
-----------------
Owner Decision 1 (``planning/MODELING_IMPROVEMENT.md`` §6.1) gives a calibrated
module a ``reported`` mode that keeps its fitted constants and a ``derived``
mode that scores from published structure instead. Here the fitted constant is
:data:`BASELINE_TAXABLE_PROFITS_BILLIONS`, whose own comment calls it
calibrated, and the structure is IRS SOI Table 11's *income subject to tax* —
the base a statutory rate change actually reaches, published rather than tuned.

``planning/lanes/W5_corporate_margin.md`` carries the arithmetic. The short
version is that the module's yield is **$199.6B per percentage point at any
step**, while CBO 60557's Option 64 says 135.7 and Treasury's FY2025 Green Book
says 192.8 — the two documents disagree by 42% per point, with the *larger*
rate change carrying the *larger* per-point yield, which no concave-in-rate
behavioural model can produce. Correcting the base moves this module toward
Treasury and away from CBO. That is a fact about the documents, not a repair.
"""

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .policies import PolicyType, TaxPolicy

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


# =============================================================================
# SCORING MODES
# =============================================================================

#: Score the rate channel off :data:`BASELINE_TAXABLE_PROFITS_BILLIONS`, the
#: fitted profits aggregate, with the flat ``|static| x elasticity x 0.5``
#: offset. This is what the app has always done and what it still does.
CORPORATE_MODE_REPORTED = "reported"

#: Ignore the fitted aggregate and score the rate channel from IRS SOI's
#: published statutory base, its published credit-realization ratio, a
#: literature-frozen profit-shifting semi-elasticity and IRC section 6655's
#: estimated-payment timing.
CORPORATE_MODE_DERIVED = "derived"

CORPORATE_MODES = (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED)

#: What the shipped app scores. Decision 1 keeps a module on ``reported`` until
#: its derived error beats its fitted error across the benchmarks it carries,
#: and here it does not:
#:
#: =========================  ===========  ==========  =========  ==========
#: Benchmark                  Target       Reported    Derived    Winner
#: =========================  ===========  ==========  =========  ==========
#: ``biden_corporate_28``     -$1,347.0B   +3.7%       +7.8%      reported
#: ``trump_corporate_15``     +$1,920.0B   -0.1%       -11.5%     reported
#: =========================  ===========  ==========  =========  ==========
#:
#: Read the second row before treating that as evidence for the fitted path:
#: ``trump_corporate_15``'s target has provenance ``model_estimate`` — it is
#: this model's own output, recorded as an expectation — so derived loses it by
#: construction. The first row is the one with a document behind it (Treasury
#: Green Book FY2025, report p. 239) and reported still wins it, which is an
#: honest loss for the structural path and is recorded as one.
CORPORATE_APP_MODE = CORPORATE_MODE_REPORTED

#: What the *uncalibrated* validation path scores.
#: ``validation/core.py``'s ``create_policy_from_score`` pins the
#: ``corporate_rate`` shape to this mode for the same reason it pins the
#: ``tax_expenditure`` shape to derived: an out-of-sample prediction must not
#: read a base fitted to a different benchmark, and
#: :data:`BASELINE_TAXABLE_PROFITS_BILLIONS` is fitted to
#: ``biden_corporate_28``.
CORPORATE_VALIDATION_MODE = CORPORATE_MODE_DERIVED


# =============================================================================
# DERIVED-MODE INPUTS
# =============================================================================

SOI_TABLE11_PATH = (
    Path(__file__).parent
    / "data_files"
    / "corporate"
    / "soi_table11_corporate_tax_items.csv"
)

#: Growth rate ``ScoringEngine`` applies to a :class:`CorporateTaxPolicy`'s
#: annual static effect (``scoring_engine._growth_tax_policy_handlers``). The
#: derived path ages SOI's base from its tax year to ``start_year`` at the same
#: rate, so exactly one growth assumption exists in the module rather than two;
#: ``tests/test_corporate_derived.py`` pins this constant to the engine's.
CORPORATE_BASE_GROWTH = 0.04

#: Semi-elasticity of reported pre-tax corporate profits with respect to the
#: statutory tax rate: a 1 percentage point higher rate reduces the reported
#: base by 0.8%. Heckemeyer & Overesch, "Multinationals' profit response to tax
#: differentials: effect size and shifting channels" (ZEW Discussion Paper
#: 13-045, 2013; *Canadian Journal of Economics* 50(4), 2017), consensus
#: estimate across 27 studies. One value, one mechanism, applied identically to
#: every case — never per benchmark (``MODELING_IMPROVEMENT.md`` §4).
#:
#: The offset it produces is ``beta x (tau_0 + delta)``, a function of the rate
#: *level*, which is what makes the derived identity concave in the rate step.
#: The module's ``reported`` offset is a flat 12.5% of the static effect, whose
#: implied semi-elasticity therefore *falls* as the rate rises (0.568 at a 1pp
#: step, 0.446 at 7pp). The literature says the opposite.
PROFIT_SHIFTING_SEMI_ELASTICITY = 0.8

#: IRC section 6655(c)(2): a calendar-year corporation pays estimated tax in
#: four instalments, due on the 15th day of the 4th, 6th, 9th and 12th months
#: of its tax year. Three of those — April, June, September — fall inside the
#: federal fiscal year that shares the tax year's number; the December
#: instalment and the settlement with the return fall in the next one. So a
#: fiscal year collects three quarters of its own tax year's liability change
#: and one quarter of the previous year's.
ESTIMATED_PAYMENT_SAME_FY_SHARE = 0.75


@lru_cache(maxsize=1)
def load_soi_table11() -> tuple[dict[str, str], ...]:
    """Read the transcribed SOI Table 11 rows, comments stripped."""
    with SOI_TABLE11_PATH.open(encoding="utf-8") as handle:
        body = (line for line in handle if not line.startswith("#"))
        return tuple(csv.DictReader(body))


@lru_cache(maxsize=1)
def latest_soi_tax_year() -> int:
    """The most recent tax year on the transcribed file."""
    return max(int(row["tax_year"]) for row in load_soi_table11())


def soi_row(tax_year: int | None = None) -> dict[str, str]:
    """One SOI Table 11 row, defaulting to the latest published tax year."""
    year = latest_soi_tax_year() if tax_year is None else tax_year
    for row in load_soi_table11():
        if int(row["tax_year"]) == year:
            return row
    raise KeyError(f"No SOI Table 11 row transcribed for tax year {year}")


def statutory_base_billions(tax_year: int | None = None) -> float:
    """
    SOI's "income subject to tax" — the base a statutory rate change reaches.

    Not "profits", and not a calibrated aggregate: SOI's own "income tax" line
    is 21.0% of this quantity to within a tenth of a percentage point in every
    post-TCJA year on the file, which is the identity that identifies it.
    """
    return float(soi_row(tax_year)["income_subject_to_tax_thousands"]) / 1e6


def credit_realization_ratio(tax_year: int | None = None) -> float:
    """
    Share of a pre-credit dollar of corporate tax that reaches receipts.

    SOI's total income tax after credits over total income tax before credits:
    0.7085 in TY2022, and between 0.67 and 0.71 in every year on the file. The
    derived path applies this *average* share to the *marginal* pre-credit
    dollar; :func:`section_904_realization_ratio` is the cross-check that the
    substitution is not wild, and the module's docstring says where it is
    weakest (section 38(c) carryforwards, which a rate rise unlocks and which
    Table 11 does not publish).
    """
    row = soi_row(tax_year)
    before = float(row["total_income_tax_before_credits_thousands"])
    after = float(row["total_income_tax_after_credits_thousands"])
    return after / before


def section_904_realization_ratio(tax_year: int | None = None) -> float:
    """
    The same share, built the other way, as a check on the average.

    The section 904 limitation scales with the statutory rate, so for a
    taxpayer in an excess-credit position the marginal US tax on foreign-source
    income is fully absorbed by the foreign tax credit. Treat the FTC as
    exactly the tax on the foreign-source share of the base at the statutory
    rate, and the remaining credits as absorbing the domestic remainder at
    their own average share. Returns 0.7012 for TY2022 against
    :func:`credit_realization_ratio`'s 0.7085 — 1.0% apart.
    """
    row = soi_row(tax_year)
    before = float(row["total_income_tax_before_credits_thousands"])
    after = float(row["total_income_tax_after_credits_thousands"])
    ftc = float(row["foreign_tax_credit_thousands"])
    base = float(row["income_subject_to_tax_thousands"])

    foreign_share = (ftc / CURRENT_CORPORATE_RATE) / base
    non_ftc_credits = (before - after) - ftc
    domestic_before = before - ftc
    return (1.0 - foreign_share) * (1.0 - non_ftc_credits / domestic_before)


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
    new_rate: float | None = None  # Alternative: specify new rate directly

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

    # Scoring mode: "reported" (fitted profits aggregate, flat offset) or
    # "derived" (SOI statutory base, published credit ratio, semi-elastic
    # offset, IRC 6655 timing). Decision 1 keeps the app on ``reported``.
    mode: str = CORPORATE_APP_MODE

    # Derived-mode behavioural parameter. Frozen at the module constant; a
    # per-case value here would be exactly what MODELING_IMPROVEMENT.md §4
    # forbids, and no factory or validation shape sets it.
    profit_shifting_semi_elasticity: float = PROFIT_SHIFTING_SEMI_ELASTICITY

    def __post_init__(self):
        """Set policy type to corporate."""
        self.policy_type = PolicyType.CORPORATE_TAX
        if self.mode not in CORPORATE_MODES:
            raise ValueError(
                f"Unknown corporate scoring mode {self.mode!r}; "
                f"expected one of {CORPORATE_MODES}"
            )
        super().__post_init__()

    def get_phase_in_factor(self, year: int) -> float:
        """
        Phase-in factor, carrying IRC section 6655 settlement timing in derived mode.

        A tax-year liability change is not a fiscal-year receipt change. Three
        of the four estimated instalments fall inside the tax year's own fiscal
        year and one falls in the next, so
        ``FY_t = 0.75 L_t + 0.25 L_(t-1)``. The engine grows ``L`` at
        :data:`CORPORATE_BASE_GROWTH`, which makes that convolution a constant
        multiple of ``L_t`` — ``0.75`` in the first year, when there is no
        previous year to collect from, and
        ``0.75 + 0.25 / (1 + g) = 0.99038`` thereafter. Expressing it as a
        phase factor keeps it out of the engine, and means the behavioural
        offset (computed on the phased revenue) is timed with it.

        ``reported`` mode returns the base class's factor unchanged.
        """
        base = super().get_phase_in_factor(year)
        if self.mode != CORPORATE_MODE_DERIVED or base == 0.0:
            return base
        if year <= self.start_year:
            return base * ESTIMATED_PAYMENT_SAME_FY_SHARE
        carry = 1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
        return base * (
            ESTIMATED_PAYMENT_SAME_FY_SHARE + carry / (1.0 + CORPORATE_BASE_GROWTH)
        )

    def _derived_rate_effect(self) -> float:
        """
        Rate-channel revenue change in ``start_year``, from published inputs.

        ``delta x (income subject to tax) x (credit realization)``, with the
        base aged from SOI's tax year to ``start_year`` at the engine's own
        corporate growth rate. Nothing here reads the baseline, so the derived
        score is independent of the vintage it is run on — the property
        ``validation/cbo_options.py`` claims for every uncalibrated shape.
        """
        delta = self._get_reform_rate() - self.baseline_rate
        if delta == 0.0:
            return 0.0
        years = self.start_year - latest_soi_tax_year()
        base = statutory_base_billions() * (1.0 + CORPORATE_BASE_GROWTH) ** years
        return delta * base * credit_realization_ratio()

    def _get_reform_rate(self) -> float:
        """Get the reform corporate tax rate."""
        if self.new_rate is not None:
            return float(self.new_rate)
        return float(self.baseline_rate + self.rate_change)

    def estimate_static_revenue_effect(self, baseline_revenue: float,
                                       use_real_data: bool = True) -> float:
        """
        Estimate static revenue effect from corporate rate change.

        In ``reported`` mode the formula is
            ΔRevenue = ΔRate × Taxable_Profits
        against the fitted profits aggregate. In ``derived`` mode it is
            ΔRevenue = ΔRate × (income subject to tax) × (credit realization)
        against IRS SOI's published statutory base — see
        :meth:`_derived_rate_effect`.

        Either way this is the mechanical change before behavioral responses.
        The international, R&D, depreciation and book-minimum channels below
        are the same in both modes: this lane re-derived the rate identity and
        left those constants where it found them.

        Args:
            baseline_revenue: Baseline corporate revenue (can use or override)
            use_real_data: Whether to use empirical baseline data

        Returns:
            Static revenue change in billions (positive = revenue gain)
        """
        if self.mode == CORPORATE_MODE_DERIVED:
            static_effect = self._derived_rate_effect()
        else:
            # Use stored profits base or estimate from revenue
            profits = self.baseline_profits_billions
            if profits <= 0:
                # Estimate from baseline revenue and current rate
                profits = (
                    baseline_revenue / self.baseline_rate if self.baseline_rate > 0 else 0
                )

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

        ``reported`` mode returns ``|static| × elasticity × 0.5``, a flat
        12.5% of the static effect whatever the rate step and whatever its
        sign. **That is unsigned, and the sign matters.** ``policies_core``'s
        contract is that the offset carries the static effect's sign, so the
        engine's ``deficit = -static + behavioral`` erodes a gain *and* recovers
        part of a cut; returning an absolute value instead makes a corporate
        rate cut cost *more* than its static effect, which is backwards. The
        ``abs()`` is kept in ``reported`` because ``trump_corporate_15``'s
        fitted number is scored through it.

        ``derived`` mode returns ``static × β × (τ₀ + Δτ)``, signed as the
        parent documents. The base falls by ``β`` per unit of statutory rate
        (:data:`PROFIT_SHIFTING_SEMI_ELASTICITY`), so the revenue lost is that
        contraction valued at the *new* rate — which makes the offset a
        function of the rate level rather than of the step, and the whole
        identity concave in the step.

        Returns:
            Behavioral offset in billions (reported: positive = revenue lost;
            derived: signed with ``static_effect``)
        """
        if self.mode == CORPORATE_MODE_DERIVED:
            base_offset = (
                static_effect
                * self.profit_shifting_semi_elasticity
                * self._get_reform_rate()
            )
            if self.include_passthrough_effects and self.rate_change != 0:
                shift = self._estimate_passthrough_shift()
                base_offset += math.copysign(shift, static_effect or 1.0)
            return base_offset

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

        The ``rate_change_effect`` follows the policy's mode, so a breakdown
        printed beside a score always adds up to that score.
        """
        if self.mode == CORPORATE_MODE_DERIVED:
            rate_effect = self._derived_rate_effect()
        else:
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
    mode: str = CORPORATE_APP_MODE,
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
        mode=mode,
    )


def create_biden_corporate_rate_only(
    mode: str = CORPORATE_APP_MODE,
) -> CorporateTaxPolicy:
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
        mode=mode,
    )


def create_biden_corporate_proposal(
    mode: str = CORPORATE_APP_MODE,
) -> CorporateTaxPolicy:
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
        mode=mode,
    )


def create_tcja_corporate_repeal(
    mode: str = CORPORATE_APP_MODE,
) -> CorporateTaxPolicy:
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
        mode=mode,
    )


def create_republican_corporate_cut(
    mode: str = CORPORATE_APP_MODE,
) -> CorporateTaxPolicy:
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
        mode=mode,
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
