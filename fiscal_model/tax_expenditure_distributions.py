"""
Distributions of the quantities tax-expenditure reforms actually cap.

Why this module exists
----------------------
A cap is a number with a unit. ``tax_expenditures_core`` used to compare a
$50,000 cap on excludable health **premiums** against ``avg_benefit = 1_600``,
the average **tax benefit**, and conclude that 0.32% of the base was affected
(`docs/VALIDATION_NOTES.md` section 6). Fixing that needs more than a second
constant: it needs, per expenditure, the distribution of the quantity the cap
is denominated in, so that "how much sits above the cap" is a question the
module can answer rather than guess.

Two shapes are enough for every reform the module scores.

``DeductionDistribution``
    Itemized deductions by size of adjusted gross income, from IRS SOI Table
    2.1. Prices a deduction at the margin by pairing each AGI class with the
    statutory ordinary rate that applies there, which is what makes a *rate*
    ceiling (the Obama/Biden 28% limitation, CBO Option 49's 15% alternative)
    scoreable at all: the revenue is the part of the deduction's value that
    sits above the ceiling.

``PremiumDistribution``
    Employment-based health insurance premiums by coverage tier, lognormal,
    with the shape taken from the two percentile values CBO prints in Option
    56 of *Options for Reducing the Deficit: 2025 to 2034*. Prices a dollar
    cap on excludable premiums.

Indexed limits
--------------
A dollar limit and the quantity it limits do not grow at the same rate, and
the gap between the two is a mechanism rather than a detail. Every published
design of the employer-health cap indexes the limit to a **price** series while
premiums grow with health costs, so a widening slice of every premium rises
above the limit each year. :func:`price_index_factor` supplies the price leg
from the repository's own baseline, so a caller can ask what a limit stated in
one year is worth in another.

Both return **shares of the expenditure's own benefit**, never dollar levels.
The level always comes from the published expenditure total in
``JCT_TAX_EXPENDITURES``; this module only supplies shape. That split is
deliberate: the shape is the thing the module was missing, and reconstructing
the level from SOI as well would silently replace published expenditure
figures with a bottom-up estimate that disagrees with them (see the module's
own ``salt`` check in ``tests/test_tax_expenditure_units.py``, where SOI times
the statutory schedule reproduces the *capped* SALT expenditure to 0.1% but
puts the *uncapped* one 25% below the published record).

Marginal rates
--------------
A deduction is worth the taxpayer's top marginal rate. The rate assigned to an
AGI class is the statutory ordinary rate for a married-joint filer whose
taxable income equals the class's **lower bound**, under IRC section 1 as
adjusted for 2025 (Rev. Proc. 2024-40). The rule is mechanical, chosen before
any result was computed, and has two offsetting biases: using AGI in place of
taxable income overstates the rate, and using the married-joint schedule for a
population that includes single filers understates it. It is not fitted, and
``tests/test_tax_expenditure_units.py`` pins the schedule against the one
``fiscal_model.microsim.engine.MicroTaxCalculator`` already carries.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .baseline import BaselineVintage, vintage_assumptions

DATA_DIR = Path(__file__).parent / "data_files" / "tax_expenditures"

SOI_ITEMIZED_FILE = DATA_DIR / "soi_2023_itemized_deductions_by_agi.csv"
PREMIUM_FILE = DATA_DIR / "employer_health_premium_distribution.csv"

#: Tax year of the SOI table transcribed in :data:`SOI_ITEMIZED_FILE`. Amounts
#: are grown from this year to a policy's first year at the expenditure
#: record's own growth rate.
SOI_BASE_YEAR = 2023

#: IRC section 1 ordinary rate schedule for married taxpayers filing jointly,
#: as adjusted for 2025 by Rev. Proc. 2024-40. Bracket floors in dollars of
#: taxable income, paired with the rate that applies above each floor.
STATUTORY_MFJ_BRACKETS_2025: tuple[tuple[float, float], ...] = (
    (0.0, 0.10),
    (23_850.0, 0.12),
    (96_950.0, 0.22),
    (206_700.0, 0.24),
    (394_600.0, 0.32),
    (501_050.0, 0.35),
    (751_600.0, 0.37),
)

#: 75th-percentile z-score, used to invert CBO's two premium percentiles into
#: a lognormal shape parameter.
_Z75 = 0.6744897501960817

#: First projection year of the assumption arrays in :mod:`fiscal_model.baseline`
#: -- ``CBOBaseline``'s own default ``start_year``, so ``inflation[0]`` is the
#: rate in this year.
BASELINE_ASSUMPTION_FIRST_YEAR = 2025

#: Baseline vintage whose price path indexes a statutory dollar limit.
#:
#: CBO's February 2024 baseline, which is the one *Options for Reducing the
#: Deficit: 2025 to 2034* was built on (``preregistered.py``'s
#: ``CBO_OPTIONS_REVENUE_BASELINE``) and the one the out-of-sample battery
#: scores on. The choice is close to immaterial: the three vintages the
#: repository carries put price growth at 2.00%, 1.96% and 2.00% over the years
#: an indexed limit is actually compounded across, and
#: ``tests/test_tax_expenditure_units.py`` pins that they agree.
CAP_INDEXATION_VINTAGE = BaselineVintage.CBO_FEB_2024

#: What the price leg of an indexed limit is, and what it is *not*.
#:
#: CBO indexes Option 56's limits with the chained CPI-U. The repository
#: carries no chained-CPI-U series -- ``baseline.py``'s price variable is the
#: PCE price index and ``data/fred_data.py`` fetches only GDP, unemployment and
#: the 10-year yield -- so the baseline's own inflation path stands in for it.
#: Over 2028-2034 CBO projects both near 2.0% (the CPI-U runs about 0.3pp above
#: each), so the substitution is worth a few basis points a year on the limit.
#: It is recorded here rather than buried because it is the one input in the
#: indexation path that is not the series the source names.
CAP_INDEXATION_SERIES_NOTE = (
    "baseline price inflation (PCE), standing in for the chained CPI-U the "
    "source names; the repository carries no chained-CPI-U series"
)


def statutory_marginal_rate(taxable_income: float) -> float:
    """Ordinary marginal rate under :data:`STATUTORY_MFJ_BRACKETS_2025`."""
    rate = STATUTORY_MFJ_BRACKETS_2025[0][1]
    for floor, bracket_rate in STATUTORY_MFJ_BRACKETS_2025:
        if taxable_income >= floor:
            rate = bracket_rate
    return rate


def _normal_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


@lru_cache(maxsize=8)
def _inflation_path(vintage: BaselineVintage) -> tuple[float, ...]:
    return tuple(float(rate) for rate in vintage_assumptions(vintage)["inflation"])


def price_index_factor(
    from_year: int,
    to_year: int,
    vintage: BaselineVintage = CAP_INDEXATION_VINTAGE,
) -> float:
    """
    Cumulative price growth between two years, from the repository's baseline.

    What a limit stated in ``from_year`` dollars is worth in ``to_year``: the
    product of ``1 + inflation`` over the years in between, taken from
    :func:`fiscal_model.baseline.vintage_assumptions`. Years outside the
    projection are held at the nearest projected rate rather than extrapolated,
    which is what the baseline itself does with its terminal assumption.

    ``to_year < from_year`` returns the reciprocal, so the function is a proper
    index and a limit can be restated backwards as well as forwards. A limit
    stated in its own year is worth exactly itself: ``price_index_factor(y, y)``
    is ``1.0`` for every ``y``, which is why adding indexation to a policy
    scored in its start year changes nothing.
    """
    if to_year == from_year:
        return 1.0
    if to_year < from_year:
        return 1.0 / price_index_factor(to_year, from_year, vintage)

    path = _inflation_path(vintage)
    factor = 1.0
    for year in range(from_year + 1, to_year + 1):
        index = min(max(year - BASELINE_ASSUMPTION_FIRST_YEAR, 0), len(path) - 1)
        factor *= 1.0 + path[index]
    return factor


def _read_rows(path: Path) -> list[dict[str, str]]:
    """Read a ``#``-commented CSV, dropping the provenance header."""
    with path.open("r", encoding="utf-8") as handle:
        lines = [line for line in handle if not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


# ---------------------------------------------------------------------------
# Deductions by AGI class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeductionBracket:
    """One AGI class of an itemized deduction."""

    agi_lower: float
    claimants: float
    """Number of returns claiming the deduction."""
    amount_billions: float
    """Deducted amount, in billions of dollars."""

    @property
    def marginal_rate(self) -> float:
        return statutory_marginal_rate(self.agi_lower)

    @property
    def benefit_billions(self) -> float:
        """Value of the deduction at the class's marginal rate."""
        return self.amount_billions * self.marginal_rate

    @property
    def average_deduction(self) -> float:
        """Deducted amount per claiming return, in dollars."""
        if self.claimants <= 0:
            return 0.0
        return self.amount_billions * 1e9 / self.claimants


@dataclass(frozen=True)
class DeductionDistribution:
    """An itemized deduction distributed across AGI classes."""

    name: str
    brackets: tuple[DeductionBracket, ...]

    @property
    def total_amount_billions(self) -> float:
        return sum(b.amount_billions for b in self.brackets)

    @property
    def implied_benefit_billions(self) -> float:
        """What the deduction is worth at the statutory schedule."""
        return sum(b.benefit_billions for b in self.brackets)

    def benefit_share_above_rate(self, cap_rate: float) -> float:
        """
        Share of the deduction's value denied by a ceiling on its *rate*.

        This is the Obama/Biden 28% limitation and CBO Option 49's 15%
        alternative: the deduction still reduces taxable income, but its value
        is capped at ``cap_rate``, so a filer facing a marginal rate ``m > cap``
        loses ``(m - cap)`` per dollar deducted.
        """
        total = self.implied_benefit_billions
        if total <= 0:
            return 0.0
        denied = sum(
            b.amount_billions * max(0.0, b.marginal_rate - cap_rate)
            for b in self.brackets
        )
        return denied / total

    def benefit_rate_ceiling_offset_share(
        self, cap_rate: float, price_elasticity: float
    ) -> float:
        """
        Behavioural offset of a rate ceiling, as a share of its static effect.

        A benefit-rate ceiling leaves the deduction in place and caps the rate
        at which it may be valued, so for a filer facing marginal rate ``m``
        above ``cap_rate`` the **price** of a deductible dollar rises from
        ``(1 - m)`` to ``(1 - cap_rate)`` -- a proportional increase of
        ``(m - cap_rate) / (1 - m)``. A price elasticity of the deducted item
        turns that into a fall in the quantity deducted, and every dollar no
        longer deducted is a dollar taxed at the filer's own rate instead of
        being subsidised at the capped one, so revenue rises by ``cap_rate``
        per dollar. That is CBO's own channel for this design -- "an effect
        that would increase tax revenues"
        (``cbo.gov/budget-options/58635``, Option 49's third alternative) --
        and it is why the reform is ``MAGNIFY`` in
        :data:`~fiscal_model.tax_expenditures_core.OFFSET_DIRECTIONS`.

        Per AGI class ``b`` with deducted amount ``A_b``::

            static_b = A_b * (m_b - c)
            offset_b = c * A_b * e * (m_b - c) / (1 - m_b)

        and what this returns is ``sum(offset_b) / sum(static_b)`` -- the
        weighted average of ``e * c / (1 - m_b)`` over the classes the ceiling
        bites, which is exactly the ratio
        :meth:`~fiscal_model.tax_expenditures_core.TaxExpenditurePolicy.estimate_behavioral_offset`
        multiplies the static effect by.

        The conversion matters because the two quantities are not the same
        thing: ``price_elasticity`` is ``%change in the item / %change in its
        price``, while the module's offset parameter is ``behavioural revenue /
        static revenue``. Lane W7 recorded the confusion and left it; lane H7
        resolved it here. See ``planning/lanes/HSD_h7_expenditure_magnitudes.md``
        section 1.2.

        ``price_elasticity`` is taken as a magnitude: a source quoting it as
        ``-0.5`` and one quoting it as ``0.5`` mean the same response.
        """
        elasticity = abs(float(price_elasticity))
        static = 0.0
        offset = 0.0
        for bracket in self.brackets:
            excess = max(0.0, bracket.marginal_rate - cap_rate)
            if excess <= 0.0:
                continue
            # A 100% marginal rate would make the price of giving zero and the
            # proportional price change infinite. Not reachable from any
            # statutory schedule, and not worth a ZeroDivisionError if one
            # ever is transcribed.
            net_of_tax = 1.0 - bracket.marginal_rate
            if net_of_tax <= 0.0:
                continue
            static += bracket.amount_billions * excess
            offset += (
                cap_rate * bracket.amount_billions * elasticity * excess / net_of_tax
            )
        if static <= 0.0:
            return 0.0
        return offset / static

    def benefit_share_above_amount(self, cap_amount: float) -> float:
        """
        Share of the deduction's value denied by a per-return **dollar** cap.

        Each AGI class contributes the excess of its *average* claimed
        deduction over the cap. That is an approximation -- SOI publishes class
        aggregates, not the within-class distribution -- and it biases a cap
        set below the top classes' averages downward, because within-class
        dispersion is discarded. It is exact for a cap above every class
        average, and for a cap below every class average.
        """
        total = self.implied_benefit_billions
        if total <= 0:
            return 0.0
        denied = 0.0
        for bracket in self.brackets:
            excess = max(0.0, bracket.average_deduction - cap_amount)
            denied += excess * bracket.claimants / 1e9 * bracket.marginal_rate
        return min(1.0, denied / total)


@lru_cache(maxsize=1)
def _soi_rows() -> tuple[dict[str, str], ...]:
    return tuple(_read_rows(SOI_ITEMIZED_FILE))


@lru_cache(maxsize=8)
def load_deduction_distribution(column: str) -> DeductionDistribution:
    """
    Build a :class:`DeductionDistribution` from one SOI Table 2.1 item.

    ``column`` is the item prefix in
    :data:`SOI_ITEMIZED_FILE` -- ``salt``, ``salt_limited``,
    ``mortgage_interest`` or ``charitable``. SOI publishes returns as counts
    and amounts in thousands of dollars; both are converted here.
    """
    brackets = []
    for row in _soi_rows():
        brackets.append(
            DeductionBracket(
                agi_lower=float(row["agi_lower"]),
                claimants=float(row[f"{column}_returns"]),
                amount_billions=float(row[f"{column}_amount"]) / 1e6,
            )
        )
    return DeductionDistribution(name=column, brackets=tuple(brackets))


# ---------------------------------------------------------------------------
# Employer health premiums
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PremiumTier:
    """One coverage tier's lognormal premium distribution."""

    tier: str
    share_of_policies: float
    mean_premium: float
    mean_premium_year: int
    sigma: float

    def mean_in_year(self, year: int, growth_rate: float) -> float:
        return self.mean_premium * (1.0 + growth_rate) ** (year - self.mean_premium_year)

    def excess_above(self, cap: float, year: int, growth_rate: float) -> float:
        """Expected premium dollars above ``cap`` per policy, ``E[(X-c)+]``."""
        mean = self.mean_in_year(year, growth_rate)
        if cap <= 0:
            return mean
        mu = math.log(mean) - self.sigma * self.sigma / 2.0
        z = (math.log(cap) - mu) / self.sigma
        return mean * _normal_cdf(self.sigma - z) - cap * _normal_cdf(-z)


@dataclass(frozen=True)
class PremiumDistribution:
    """Employment-based premiums across coverage tiers."""

    tiers: tuple[PremiumTier, ...]

    def base_share_above(
        self,
        cap: float,
        year: int,
        growth_rate: float,
        *,
        caps_by_tier: dict[str, float] | None = None,
        cap_index_factor: float = 1.0,
    ) -> float:
        """
        Share of total premium dollars sitting above the cap.

        ``caps_by_tier`` lets a reform set a different limit per coverage tier,
        which is how every published design of this option is written (CBO's
        Option 56 sets both limits at the same *percentile*). Without it the
        single ``cap`` applies to every tier, which is how the repository's
        ``cap_employer_health`` benchmark is written.

        ``cap_index_factor`` restates the limit in ``year`` dollars: it is what
        :func:`price_index_factor` returns between the year the limit is stated
        in and the year being scored. The default of ``1.0`` is a limit fixed
        in nominal terms. Premiums grow at ``growth_rate`` and the limit grows
        at this factor, so the share this returns rises across a window
        whenever health costs outpace prices -- which is the whole reason the
        share has to be asked for year by year rather than once.
        """
        numerator = 0.0
        denominator = 0.0
        for tier in self.tiers:
            tier_cap = (caps_by_tier or {}).get(tier.tier, cap) * cap_index_factor
            weight = tier.share_of_policies
            numerator += weight * tier.excess_above(tier_cap, year, growth_rate)
            denominator += weight * tier.mean_in_year(year, growth_rate)
        if denominator <= 0:
            return 0.0
        return numerator / denominator


@lru_cache(maxsize=1)
def load_premium_distribution() -> PremiumDistribution:
    """Load the employer-health premium distribution from its data file."""
    tiers = []
    for row in _read_rows(PREMIUM_FILE):
        tiers.append(
            PremiumTier(
                tier=row["tier"],
                share_of_policies=float(row["share_of_policies"]),
                mean_premium=float(row["mean_premium"]),
                mean_premium_year=int(row["mean_premium_year"]),
                sigma=float(row["sigma"]),
            )
        )
    return PremiumDistribution(tiers=tuple(tiers))


def implied_sigma(p50: float, p75: float) -> float:
    """Lognormal shape parameter implied by two percentiles."""
    return (math.log(p75) - math.log(p50)) / _Z75


# ---------------------------------------------------------------------------
# A deduction under a cap that is neither zero nor infinite
# ---------------------------------------------------------------------------
#
# Every other reform in this module asks "how much of the base sits above a
# limit" once. SALT has to ask it of a **path** of limits -- P.L. 119-21
# sec. 70120 sets a different cap in every year from 2025 to 2030 and phases it
# down against the filer's own income -- and the class averages
# :meth:`DeductionDistribution.benefit_share_above_amount` compares against
# cannot answer that, because they discard the within-class dispersion a cap
# between the class minimum and the class maximum lives in.
#
# What makes an answer possible without a new assumption is that SOI Table 2.1
# publishes the **same deduction twice**: ``salt`` is state and local taxes
# before IRC 164(b)(6) and ``salt_limited`` is the amount deductible with it in
# force. That is a second moment per AGI class, observed rather than assumed,
# and two moments identify a two-parameter distribution.

#: Number of equal-probability AGI slices each class is cut into when a cap
#: phases down against income. The phase-out range of the published SALT design
#: is narrower than SOI's $500,000-$1,000,000 class, so evaluating the phasedown
#: at the class *mean* would make it a step function at a published class
#: boundary rather than a measurement. Forty slices puts the quadrature error
#: orders of magnitude below the mechanism it measures.
AGI_SLICES_PER_CLASS = 40

#: Where the open-ended top AGI class is truncated for its Pareto fit, as a
#: multiple of its lower bound. Immaterial to every SALT design: the top class
#: begins at $10,000,000, far above any published phase-out range, so every
#: slice of it receives the same cap.
OPEN_CLASS_UPPER_MULTIPLE = 400.0


def _lognormal_mean_min(mean: float, sigma: float | None, cap: float) -> float:
    """``E[min(X, cap)]`` for a lognormal with this mean and shape."""
    if cap <= 0:
        return 0.0
    if math.isinf(cap):
        # No cap at all -- the baseline CBO's own Option 49 is measured on.
        return mean
    if sigma is None or sigma <= 0:
        return min(mean, cap)
    mu = math.log(mean) - sigma * sigma / 2.0
    z = (math.log(cap) - mu) / sigma
    excess = mean * _normal_cdf(sigma - z) - cap * _normal_cdf(-z)
    return mean - excess


def _sigma_from_capped_mean(
    mean: float, capped_mean: float, cap: float
) -> float | None:
    """
    Dispersion of a lognormal with this mean whose ``E[min(X, cap)]`` is
    ``capped_mean``.

    ``None`` when the pair identifies none, which happens only if the published
    capped column is at or above ``min(mean, cap)`` -- the class then shows no
    dispersion across the limit at all, and the caller treats it as a point
    mass at its mean, which is what every other cap rule in this module does
    everywhere.

    ``E[min(X, cap)]`` falls monotonically in sigma at a fixed mean, so a
    bisection is exact to machine precision and needs no derivative.
    """
    ceiling = min(mean, cap)
    if capped_mean >= ceiling - 1e-9 or capped_mean <= 0.0:
        return None
    low, high = 1e-6, 12.0
    for _ in range(200):
        mid = 0.5 * (low + high)
        if _lognormal_mean_min(mean, mid, cap) > capped_mean:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def _bounded_pareto_alpha(
    lower: float, upper: float | None, mean: float
) -> float | None:
    """
    Tail index of a Pareto on ``[lower, upper]`` with this mean.

    ``None`` when the class cannot carry one -- a zero lower bound, or a
    published mean outside the range a bounded Pareto on those bounds can
    produce. The caller then falls back to the class mean.
    """
    if lower <= 0 or mean <= 0:
        return None
    if upper is None:
        if mean <= lower:
            return None
        return mean / (mean - lower)

    ratio = lower / upper

    def class_mean(alpha: float) -> float:
        return (
            (alpha / (alpha - 1.0))
            * lower
            * (1.0 - ratio ** (alpha - 1.0))
            / (1.0 - ratio**alpha)
        )

    low, high = 1.0001, 60.0
    if not class_mean(high) < mean < class_mean(low):
        return None
    for _ in range(200):
        mid = 0.5 * (low + high)
        if class_mean(mid) > mean:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


@dataclass(frozen=True)
class CappedDeductionClass:
    """One AGI class of a deduction whose statutory cap is itself observed."""

    agi_lower: float
    agi_upper: float | None
    agi_mean: float
    """Mean AGI (less deficit) of *all* returns in the class, from SOI."""
    claimants: float
    mean_deduction: float
    """Mean amount claimed before the cap, in dollars per claiming return."""
    mean_deduction_capped: float
    """Mean amount deductible **with the observed cap in force**, in dollars."""
    observed_cap: float
    """The cap the published capped column was measured under, in dollars."""
    marginal_rate: float

    @property
    def sigma(self) -> float | None:
        """Within-class dispersion, identified by the two published columns."""
        return _sigma_from_capped_mean(
            self.mean_deduction, self.mean_deduction_capped, self.observed_cap
        )

    @property
    def agi_alpha(self) -> float | None:
        """Within-class AGI tail index, identified by the published class mean."""
        return _bounded_pareto_alpha(self.agi_lower, self.agi_upper, self.agi_mean)

    def agi_slices(self) -> tuple[tuple[float, float], ...]:
        """``(weight, agi)`` pairs spanning the class, equal probability each."""
        alpha = self.agi_alpha
        if alpha is None:
            return ((1.0, self.agi_mean),)
        lower = self.agi_lower
        upper = (
            self.agi_upper
            if self.agi_upper is not None
            else lower * OPEN_CLASS_UPPER_MULTIPLE
        )
        span = 1.0 - (lower / upper) ** alpha
        weight = 1.0 / AGI_SLICES_PER_CLASS

        def quantile(u: float) -> float:
            return lower * (1.0 - u * span) ** (-1.0 / alpha)

        return tuple(
            (weight, 0.5 * (quantile(i * weight) + quantile((i + 1) * weight)))
            for i in range(AGI_SLICES_PER_CLASS)
        )

    def deductible_benefit_billions(
        self,
        cap_at_agi: Callable[[float], float],
        growth_factor: float = 1.0,
    ) -> float:
        """
        What this class may deduct under ``cap_at_agi``, valued in $B.

        ``growth_factor`` scales the *claimed amounts* and the AGI the cap is
        read at, and never the cap itself. That asymmetry is the mechanism
        rather than a detail: a statutory cap is a nominal figure indexed at
        whatever rate its own statute states (1%/yr for 2027-2029 under IRC
        164(b)(7)(A)) while the taxes it limits grow with incomes, so the same
        cap denies a widening slice of the base every year.
        """
        mean = self.mean_deduction * growth_factor
        sigma = self.sigma
        deductible = 0.0
        for weight, agi in self.agi_slices():
            deductible += weight * _lognormal_mean_min(
                mean, sigma, cap_at_agi(agi * growth_factor)
            )
        return self.claimants * deductible / 1e9 * self.marginal_rate

    def uncapped_benefit_billions(self, growth_factor: float = 1.0) -> float:
        """What this class would deduct with no cap at all, valued in $B."""
        return (
            self.claimants
            * self.mean_deduction
            * growth_factor
            / 1e9
            * self.marginal_rate
        )


@dataclass(frozen=True)
class CappedDeductionDistribution:
    """A deduction whose uncapped and capped columns are both published."""

    name: str
    classes: tuple[CappedDeductionClass, ...]

    def deductible_benefit_billions(
        self,
        cap_at_agi: Callable[[float], float],
        growth_factor: float = 1.0,
    ) -> float:
        """Value of the deduction actually claimable under a cap rule, in $B."""
        return sum(
            c.deductible_benefit_billions(cap_at_agi, growth_factor)
            for c in self.classes
        )

    def uncapped_benefit_billions(self, growth_factor: float = 1.0) -> float:
        """Value of the deduction with no cap at all, in $B."""
        return sum(c.uncapped_benefit_billions(growth_factor) for c in self.classes)


@lru_cache(maxsize=4)
def load_capped_deduction_distribution(
    column: str = "salt",
    capped_column: str = "salt_limited",
    observed_cap: float = 10_000.0,
) -> CappedDeductionDistribution:
    """
    Build a :class:`CappedDeductionDistribution` from two SOI Table 2.1 columns.

    ``column`` is the deduction before its statutory limit, ``capped_column``
    the amount deductible with the limit in force, and ``observed_cap`` the
    limit that capped column was measured under -- $10,000 for tax year 2023,
    under IRC 164(b)(6) as enacted by P.L. 115-97 and before P.L. 119-21
    sec. 70120 replaced it.

    The anchor is what makes the extrapolation checkable rather than invented:
    evaluated *at* ``observed_cap`` this distribution returns the published
    capped column to machine precision, and ``tests/test_salt_cap_path.py``
    pins that against ``JCT_TAX_EXPENDITURES["salt"]["annual_cost"]``, a
    constant with no common ancestor.
    """
    classes = []
    for row in _soi_rows():
        claimants = float(row[f"{column}_returns"])
        if claimants <= 0:
            continue
        upper = row["agi_upper"].strip()
        agi_lower = float(row["agi_lower"])
        classes.append(
            CappedDeductionClass(
                agi_lower=agi_lower,
                agi_upper=float(upper) if upper else None,
                agi_mean=float(row["agi_less_deficit"]) * 1e3 / float(row["returns"]),
                claimants=claimants,
                mean_deduction=float(row[f"{column}_amount"]) * 1e3 / claimants,
                mean_deduction_capped=(
                    float(row[f"{capped_column}_amount"]) * 1e3 / claimants
                ),
                observed_cap=observed_cap,
                marginal_rate=statutory_marginal_rate(agi_lower),
            )
        )
    return CappedDeductionDistribution(name=column, classes=tuple(classes))
