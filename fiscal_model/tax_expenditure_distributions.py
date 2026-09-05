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
