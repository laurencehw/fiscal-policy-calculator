"""
Estate Tax Module

Models federal estate and gift tax policy changes including:
- Exemption level changes
- Rate changes
- Portability provisions
- Behavioral responses (estate planning, gifts)

Key data sources:
- IRS SOI, *Estate Tax Statistics*, Table 1 (returns, taxable estate, adjusted
  taxable gifts and net estate tax by size of gross estate), filing years 2010,
  2013 and 2024, transcribed to
  ``data_files/estate/soi_estate_table1_by_size_of_gross_estate.csv``
- CBO: Understanding Federal Estate and Gift Taxes (2021)
- JCT: Revenue estimates for TCJA estate provisions

Current Law (TCJA, through 2025):
- Exemption: $13.99M per person (2025), indexed to inflation
- Top rate: 40%
- Revenue: ~$32B/year

Scheduled 2026 (post-TCJA sunset):
- Exemption: ~$6.4M per person (inflation-adjusted)
- Revenue projected to increase to ~$50B/year

How the exemption is priced
---------------------------
The estate tax base is modelled as a **size distribution**, not as two
hand-set reference points. Before 2026-09 this module interpolated between a
"7,000 estates averaging $8M under TCJA" anchor and a "19,000 averaging $4M
after the sunset" anchor, and for any exemption at or below $6.4M it set
``estates = 19,000 * (6.4M / E)`` against ``avg = 4M * (E / 6.4M)``. That
product is **exactly invariant in E**, so lowering the exemption derived
precisely zero revenue and ``create_estate_exemption_change`` returned $0.0B
for every exemption at or below the post-sunset level.

The replacement is a Pareto survival function for the **estate tax base**
``B = taxable estate + adjusted taxable gifts`` -- the quantity the exemption
is actually subtracted from -- fitted to SOI's own size classes:

    N(B > E)                 proportional to  E ** -alpha
    E[B - E | B > E]         proportional to  E
    base(E)  = N(B > E) * E[B - E | B > E]   proportional to  E ** (1 - alpha)

so a lower exemption raises revenue through both the count and the amount.

Scoring modes
-------------
Every policy in this module carries a ``mode``. ``reported`` scores the fitted
``annual_revenue_change_billions`` when one is set; ``derived`` ignores it and
scores the year-indexed structural path. See the SCORING MODES block below.
"""

from __future__ import annotations

import csv
import itertools
from dataclasses import dataclass
from enum import Enum
from functools import cache, lru_cache
from pathlib import Path

import numpy as np

from .policies import PolicyType, TaxPolicy


class EstateTaxScenario(Enum):
    """Common estate tax policy scenarios."""
    CURRENT_LAW = "current_law"  # TCJA expires 2026
    EXTEND_TCJA = "extend_tcja"  # Keep $14M+ exemption
    LOWER_EXEMPTION = "lower_exemption"  # e.g., $3.5M
    INCREASE_RATE = "increase_rate"
    ELIMINATE = "eliminate"


# =============================================================================
# SCORING MODES
# =============================================================================
# Owner Decision 1 (planning/MODELING_IMPROVEMENT.md §6.1, accepted
# 2026-09-01): the calibrated modules keep their fitted annuals as a `reported`
# mode alongside a `derived` mode that scores from structure instead. L5
# implemented the switch module-locally in `amt.py`; this is the same shape.

#: Score the fitted ``annual_revenue_change_billions`` when one is set.
ESTATE_MODE_REPORTED = "reported"

#: Ignore the fitted annual and score the structural year path.
ESTATE_MODE_DERIVED = "derived"

ESTATE_MODES = (ESTATE_MODE_REPORTED, ESTATE_MODE_DERIVED)

#: What the app and every shipped preset use. Decision 1's rule is that a
#: module flips to ``derived`` only once derived beats fitted on that module's
#: own carried benchmarks. It does not: derived scores +19% / +2% against
#: +0.0% / +0.0% fitted, so nothing a user sees changes.
ESTATE_APP_MODE = ESTATE_MODE_REPORTED

#: What ``validation/loo.run_estate_loo`` uses. Derived is the default in the
#: held-out path, which is where the honesty claim lives.
ESTATE_HELD_OUT_MODE = ESTATE_MODE_DERIVED

#: What the by-construction scorecard uses. Kept on ``reported`` so the
#: calibrated tier keeps measuring what it says it measures -- bookkeeping --
#: rather than silently becoming a second copy of the LOO column.
ESTATE_SCORECARD_MODE = ESTATE_MODE_REPORTED

#: ``ScoringEngine._growth_tax_policy_handlers`` books an ``EstateTaxPolicy``
#: at this rate, except that an explicit ``annual_revenue_change_billions`` is
#: treated as a window average and grown at 0. :meth:`get_phase_in_factor`
#: has to divide by whichever the engine will apply, or the derived path would
#: arrive grown twice.
ESTATE_ENGINE_GROWTH_RATE = 0.03

#: Fiscal-year receipts lag. The estate tax on a year-*t* decedent is paid with
#: a Form 706 due nine months after death (IRC 6075(a)), extendable six months
#: (IRC 6081), so it lands in fiscal year *t+1*. SOI states the same thing in
#: its own footnote to every Table 1: "Generally, an estate files a federal
#: estate tax return (Form 706) in the year after a decedent's death."
ESTATE_RECEIPTS_LAG_YEARS = 1


# =============================================================================
# CURRENT LAW PARAMETERS
# =============================================================================

# Current law exemption levels (indexed to inflation)
ESTATE_TAX_EXEMPTIONS = {
    2024: 13_610_000,  # Per person
    2025: 13_990_000,  # Per person (estimated)
    2026: 6_400_000,   # Post-TCJA sunset (estimated, inflation-adjusted)
    2027: 6_600_000,   # Projected
    2028: 6_800_000,
    2029: 7_000_000,
    2030: 7_200_000,
    2031: 7_400_000,
    2032: 7_600_000,
    2033: 7_800_000,
    2034: 8_000_000,
}

# TCJA-extended exemption levels (if made permanent). The 2024 and 2025 rows
# are current law either way -- TCJA's doubled exemption is in force for those
# decedents -- and they are carried explicitly so an extension scores zero in
# the years it changes nothing instead of falling through to the 2034 row.
TCJA_EXTENDED_EXEMPTIONS = {
    2024: 13_610_000,
    2025: 13_990_000,
    2026: 14_400_000,
    2027: 14_800_000,
    2028: 15_200_000,
    2029: 15_600_000,
    2030: 16_000_000,
    2031: 16_400_000,
    2032: 16_800_000,
    2033: 17_200_000,
    2034: 17_600_000,
}

# Estate tax rate (unchanged by TCJA)
CURRENT_ESTATE_TAX_RATE = 0.40

#: Reported-estate elasticity with respect to the net-of-tax share, from
#: Kopczuk & Slemrod (2003), "Dying to Save Taxes: Evidence from Estate-Tax
#: Returns on the Death Elasticity", *Review of Economics and Statistics*
#: 85(2), 256-265. Their reported-estate elasticities cluster around 0.16 and
#: they read them as an avoidance/reporting response rather than a real one.
#: One frozen value, used for every rate change; it replaces the previous
#: ``planning_elasticity = 0.15``, which was not an elasticity at all but a
#: flat 15% haircut on the static effect regardless of what the policy did.
KOPCZUK_SLEMROD_PLANNING_ELASTICITY = 0.16

# Baseline data
BASELINE_ESTATE_DATA = {
    # Annual revenue (billions)
    "revenue_2024": 32.0,  # FY2024 actual
    # CBO projection once the exemption drops. No longer an input to any
    # score: the level now comes from SOI's own anchor row, and this is the
    # external check on it. The SOI-anchored model puts 2026 revenue at the
    # $6.4M exemption at ~$47.6B, 5% below this figure.
    "revenue_baseline_2026": 50.0,

    # Total deaths per year
    "annual_deaths": 2_800_000,

    # Behavioral parameters
    "planning_elasticity": KOPCZUK_SLEMROD_PLANNING_ELASTICITY,
    "gift_shifting_rate": 0.10,  # Fraction shifted to gifts
}

# CBO/JCT official estimates
CBO_ESTATE_ESTIMATES = {
    # Cost of extending TCJA exemption
    "extend_tcja_10yr": 167.0,  # Billions over 10 years (CBO)
    "extend_tcja_annual": 16.7,  # Average annual cost

    # JCT estimate for permanent extension
    "permanent_extension_10yr": 201.0,  # FY2025-2034

    # Revenue projections (2021-2031)
    "total_revenue_10yr": 372.0,  # Combined estate + gift
}


# =============================================================================
# SOI TAXABLE-ESTATE SIZE DISTRIBUTION
# =============================================================================

SOI_ESTATE_TABLE1_PATH = (
    Path(__file__).resolve().parent
    / "data_files"
    / "estate"
    / "soi_estate_table1_by_size_of_gross_estate.csv"
)

#: Filing year whose taxable-return panel anchors the *level* of the
#: distribution. The most recent transcribed year, so the level is the most
#: recent thing SOI has actually observed rather than a projection.
SOI_ANCHOR_FILING_YEAR = 2024

#: A class boundary is read only if it sits at or above this fraction of its
#: year's filing threshold. Below the threshold SOI's classes are a mixture of
#: earlier-year deaths (lower thresholds), portability filers and estates whose
#: gross estate excludes lifetime gift tax paid, so their counts do not lie on
#: the same survival curve. 0.95 keeps FY2013's $5.0M boundary against its
#: $5.12M threshold (a 2.3% overlap) and drops FY2024's $10M against $12.92M.
SOI_BOUNDARY_THRESHOLD_TOLERANCE = 0.95

#: Nominal growth of the estate size distribution, per year: the whole
#: distribution -- decedents and the values they leave -- scales at this rate,
#: so revenue at a *fixed* exemption grows at ``alpha`` times it, and the
#: baseline path, whose exemption is indexed at about 2.8%/yr, grows at about
#: 3%/yr. That is what the module's old "~3%/year for wealth growth" comment
#: was describing.
#:
#: The value is the app's own CBO-baseline nominal GDP growth
#: (``CBOBaseline.generate().nominal_gdp``, 3.82%/yr compound over FY2025-2034),
#: i.e. wealth held at a constant ratio to GDP. It is deliberately *not* the
#: rate SOI's own history implies: fitting the level and the growth jointly to
#: the three transcribed filing years returns 6.8%/yr, because household net
#: worth grew far faster than GDP over 2009-2023. Projecting 6.8% forward would
#: roughly double every ten-year estate score, and no published CBO or JCT
#: estate estimate is consistent with that. See planning/lanes/L4_estate.md.
ESTATE_BASE_GROWTH_RATE = 0.0382


@dataclass(frozen=True)
class SOIEstateAnchor:
    """One filing year's taxable-return panel, reduced to what pricing needs."""

    filing_year: int
    decedent_year: int
    exemption: float
    statutory_top_rate: float
    taxable_returns: int
    tax_base_billions: float          # taxable estate + adjusted taxable gifts
    net_estate_tax_billions: float

    @property
    def base_above_exemption_billions(self) -> float:
        """Aggregate ``B - exemption`` over the taxable returns, $B."""
        return self.tax_base_billions - self.exemption * self.taxable_returns / 1e9

    @property
    def mean_excess_ratio(self) -> float:
        """``E[B - E | B > E] / E`` -- 1.83 at the FY2024 anchor."""
        return (
            self.base_above_exemption_billions * 1e9
            / self.taxable_returns
            / self.exemption
        )

    @property
    def effective_rate_factor(self) -> float:
        """
        Net estate tax as a share of ``statutory rate x base above exemption``.

        0.93 at the FY2024 anchor: the graduated brackets below the top rate,
        the state death tax deduction and the remaining credits all sit between
        the statutory rate and what is actually collected. Applying it keeps
        the module's revenue equal to SOI's own printed total at the anchor.
        """
        denominator = self.statutory_top_rate * self.base_above_exemption_billions
        if denominator == 0:
            return 1.0
        return self.net_estate_tax_billions / denominator


@lru_cache(maxsize=1)
def load_soi_estate_table1() -> tuple[dict[str, str], ...]:
    """Read the transcribed SOI Table 1 rows, comments stripped."""
    with SOI_ESTATE_TABLE1_PATH.open(encoding="utf-8") as handle:
        body = (line for line in handle if not line.startswith("#"))
        return tuple(csv.DictReader(body))


def _taxable_class_rows(filing_year: int) -> list[dict[str, str]]:
    """Part II size-class rows for one filing year, panel total excluded."""
    return [
        row
        for row in load_soi_estate_table1()
        if int(row["filing_year"]) == filing_year
        and row["tax_status"] == "taxable"
        and not (row["size_class_lower_usd"] == "0" and not row["size_class_upper_usd"])
    ]


def _survival_above_boundaries(filing_year: int) -> list[tuple[float, int, float]]:
    """
    ``(boundary, returns above it, tax base above it)`` for readable boundaries.

    Boundaries below :data:`SOI_BOUNDARY_THRESHOLD_TOLERANCE` times the year's
    filing threshold are dropped, for the reason that constant documents.
    """
    rows = sorted(
        _taxable_class_rows(filing_year),
        key=lambda row: float(row["size_class_lower_usd"]),
        reverse=True,
    )
    threshold = float(rows[0]["filing_threshold_usd"])
    floor = SOI_BOUNDARY_THRESHOLD_TOLERANCE * threshold
    out: list[tuple[float, int, float]] = []
    returns = 0
    base = 0.0
    for row in rows:
        returns += int(row["returns"])
        base += (
            float(row["taxable_estate_thou"]) + float(row["adjusted_taxable_gifts_thou"])
        ) / 1e6  # thousands -> billions
        lower = float(row["size_class_lower_usd"])
        if lower >= floor:
            out.append((lower, returns, base))
    out.reverse()
    return out


@lru_cache(maxsize=1)
def soi_tax_base_pareto_alpha() -> float:
    """
    Pareto shape of the estate tax base, pooled over the transcribed years.

    For a Pareto tail, the returns above boundary *j* and the mean base above
    it satisfy ``N_j / N_{j+1} = (m_{j+1} / m_j) ** alpha``, so each adjacent
    pair of readable class boundaries yields one local estimate. Estimating it
    inside a filing year makes it scale-free: no wealth index is needed to
    compare 2009 dollars with 2023 dollars, because no comparison is made.

    Seven local estimates -- three from filing year 2010, three from 2013 and
    one from 2024, the count of *adjacent pairs* of readable boundaries in each
    year rather than of boundaries -- across decedents fourteen years apart and
    filing thresholds a factor of 3.7 apart, returning 1.66 to 1.87. That the
    same number comes back from three regimes is the evidence this is structure
    and not a fit.
    """
    estimates: list[float] = []
    for filing_year in sorted({int(row["filing_year"]) for row in load_soi_estate_table1()}):
        points = _survival_above_boundaries(filing_year)
        for (_g1, n1, b1), (_g2, n2, b2) in itertools.pairwise(points):
            mean1, mean2 = b1 / n1, b2 / n2
            estimates.append(np.log(n1 / n2) / np.log(mean2 / mean1))
    return float(np.mean(estimates))


@cache
def soi_estate_anchor(filing_year: int = SOI_ANCHOR_FILING_YEAR) -> SOIEstateAnchor:
    """The taxable-return panel total for one transcribed filing year."""
    for row in load_soi_estate_table1():
        if (
            int(row["filing_year"]) == filing_year
            and row["tax_status"] == "taxable"
            and row["size_class_lower_usd"] == "0"
            and not row["size_class_upper_usd"]
        ):
            return SOIEstateAnchor(
                filing_year=filing_year,
                decedent_year=int(row["decedent_year"]),
                exemption=float(row["filing_threshold_usd"]),
                statutory_top_rate=float(row["statutory_top_rate"]),
                taxable_returns=int(row["returns"]),
                tax_base_billions=(
                    float(row["taxable_estate_thou"])
                    + float(row["adjusted_taxable_gifts_thou"])
                ) / 1e6,
                net_estate_tax_billions=float(row["net_estate_tax_thou"]) / 1e6,
            )
    raise KeyError(f"No taxable-return panel total for SOI filing year {filing_year}")


def taxable_base_above_exemption(exemption: float, year: int) -> float:
    """
    Aggregate ``estate tax base - exemption`` over taxable estates, $B.

    ``base(E) = base_anchor * (E / E_anchor) ** (1 - alpha)`` times the
    distribution's growth between the anchor's decedent year and ``year``,
    which enters with exponent ``alpha`` because scaling every estate by *s*
    multiplies the count above a fixed exemption by ``s ** alpha`` and leaves
    the Pareto mean excess at a fixed exemption unchanged.
    """
    if exemption <= 0 or not np.isfinite(exemption):
        return 0.0
    anchor = soi_estate_anchor()
    alpha = soi_tax_base_pareto_alpha()
    shape = (exemption / anchor.exemption) ** (1.0 - alpha)
    growth = (1.0 + ESTATE_BASE_GROWTH_RATE) ** (alpha * (year - anchor.decedent_year))
    return anchor.base_above_exemption_billions * shape * growth


def annual_estate_tax(exemption: float, rate: float, year: int) -> float:
    """
    Estate tax collected on ``year`` decedents at this exemption and rate, $B.

    Reproduces SOI's own printed net estate tax exactly at the anchor row, and
    prices any other exemption off the fitted size distribution. The effective
    rate factor is held fixed as the rate moves, so a 40% -> 45% change scales
    revenue by 45/40 for the estates that remain taxable.
    """
    if not np.isfinite(exemption) or rate <= 0.0:
        return 0.0
    anchor = soi_estate_anchor()
    return (
        taxable_base_above_exemption(exemption, year)
        * rate
        * anchor.effective_rate_factor
    )


def _lookup_exemption(schedule: dict[int, int], year: int) -> float:
    """Read a year off an exemption schedule, clamping at both ends."""
    if year in schedule:
        return float(schedule[year])
    years = sorted(schedule)
    if year < years[0]:
        return float(schedule[years[0]])
    return float(schedule[years[-1]])


@dataclass
class EstateTaxPolicy(TaxPolicy):
    """
    Estate tax policy modeling exemption and rate changes.

    Models the federal estate (and gift) tax which applies to transfers
    of wealth at death above the exemption amount.

    Key parameters:
        exemption_change: Change in exemption level (dollars)
        new_exemption: New exemption level (overrides exemption_change)
        rate_change: Change in estate tax rate (e.g., 0.05 for 5pp increase)
        new_rate: New estate tax rate (overrides rate_change)

    Behavioral responses:
        - Higher exemptions reduce taxable estates
        - Lower rates reduce planning/avoidance
        - Lock-in effects similar to capital gains

    Scoring modes
        ``reported`` (the app default) scores the fitted
        ``annual_revenue_change_billions`` when one is set. ``derived``
        ignores it and scores the year-indexed structural path built from the
        SOI size distribution; :meth:`get_phase_in_factor` carries that path
        into the engine.
    """

    # Exemption changes
    exemption_change: float = 0.0  # Dollar change in exemption
    new_exemption: float | None = None  # Set specific exemption level
    extend_tcja_exemption: bool = False  # Keep ~$14M exemption beyond 2025

    # Rate changes
    rate_change: float = 0.0  # Change in estate tax rate
    new_rate: float | None = None  # Set specific rate

    # Portability (unused exemption transfers to surviving spouse)
    modify_portability: bool = False
    portability_cap: float | None = None  # Cap on portable amount

    # Behavioral parameters
    planning_elasticity: float = KOPCZUK_SLEMROD_PLANNING_ELASTICITY
    gift_shifting_elasticity: float = 0.10  # Shifting to inter vivos gifts

    # Valuation discounts (family-owned businesses, etc.)
    limit_valuation_discounts: bool = False
    discount_limit_pct: float = 0.0  # Cap discounts at this percent

    # Base year for calculations
    base_year: int = 2024

    # Calibration
    annual_revenue_change_billions: float | None = None

    # Scoring mode: "reported" (fitted annual) or "derived" (structural path)
    mode: str = ESTATE_APP_MODE

    def __post_init__(self):
        """Set default policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.ESTATE_TAX
        if self.mode not in ESTATE_MODES:
            raise ValueError(f"mode must be one of {ESTATE_MODES}, got {self.mode!r}")
        super().__post_init__()

    def get_exemption_for_year(self, year: int, policy_active: bool = True) -> float:
        """
        Get the effective exemption for a given year.

        Args:
            year: Tax year (year of death, not the fiscal year of receipts)
            policy_active: Whether policy is in effect

        Returns:
            Exemption amount in dollars
        """
        if not policy_active:
            # Return baseline (current law)
            return _lookup_exemption(ESTATE_TAX_EXEMPTIONS, year)

        if self.new_exemption is not None:
            # Specific exemption set
            return self.new_exemption

        if self.extend_tcja_exemption:
            # Keep TCJA-level exemptions
            return _lookup_exemption(TCJA_EXTENDED_EXEMPTIONS, year)

        # Apply exemption change to baseline
        return _lookup_exemption(ESTATE_TAX_EXEMPTIONS, year) + self.exemption_change

    def get_rate_for_year(self, year: int) -> float:
        """Get the effective estate tax rate."""
        del year
        if self.new_rate is not None:
            return self.new_rate
        return CURRENT_ESTATE_TAX_RATE + self.rate_change

    def estimate_taxable_estates(
        self,
        exemption: float,
        year: int = 2026,
    ) -> tuple[int, float]:
        """
        Estimate number of taxable estates and average taxable amount.

        Both come from the SOI-fitted size distribution
        (:func:`taxable_base_above_exemption`), so the pair is no longer
        invariant in the exemption the way the old two-point blend was.

        The average is ``exemption * anchor.mean_excess_ratio`` -- the ratio
        SOI's own anchor row shows, 1.83 -- and the count is the aggregate base
        divided by it, so count x average reproduces the aggregate exactly and
        the count reproduces SOI's 2,663 taxable returns at the anchor.

        Note that ``count * average * rate`` is the *statutory* yield;
        :func:`annual_estate_tax` additionally applies SOI's realized ratio of
        net estate tax to that product (:attr:`SOIEstateAnchor
        .effective_rate_factor`, 0.93).

        Args:
            exemption: Effective exemption level
            year: Year of death

        Returns:
            Tuple of (number of taxable estates, average taxable amount)
        """
        base_billions = taxable_base_above_exemption(exemption, year)
        if base_billions <= 0:
            return 0, 0.0
        average = exemption * soi_estate_anchor().mean_excess_ratio
        return int(round(base_billions * 1e9 / average)), float(average)

    # -- derived (structural) path -------------------------------------------

    def derived_annual_effect(self, fiscal_year: int) -> float:
        """
        Structural revenue change in one fiscal year, $B (negative = loss).

        Receipts in fiscal year *y* come from year *y-1* decedents
        (:data:`ESTATE_RECEIPTS_LAG_YEARS`), and a policy that first applies to
        deaths in ``start_year`` therefore changes nothing until the fiscal
        year after that. Extending TCJA relief is additionally a no-op for
        2025 decedents, because TCJA's exemption is current law for them.
        """
        decedent_year = fiscal_year - ESTATE_RECEIPTS_LAG_YEARS
        if decedent_year < self.start_year:
            return 0.0
        baseline = annual_estate_tax(
            _lookup_exemption(ESTATE_TAX_EXEMPTIONS, decedent_year),
            CURRENT_ESTATE_TAX_RATE,
            decedent_year,
        )
        policy = annual_estate_tax(
            self.get_exemption_for_year(decedent_year),
            self.get_rate_for_year(decedent_year),
            decedent_year,
        )
        return policy - baseline

    def derived_revenue_path(self) -> list[tuple[int, float]]:
        """The derived annual effects across the policy's own window."""
        return [
            (self.start_year + offset, self.derived_annual_effect(self.start_year + offset))
            for offset in range(self.duration_years)
        ]

    def derived_window_average(self) -> float:
        """Window-average annual effect of the derived path, $B."""
        path = self.derived_revenue_path()
        if not path:
            return 0.0
        return sum(effect for _year, effect in path) / len(path)

    def derived_anchor_effect(self) -> float:
        """
        The level the engine multiplies, in derived mode.

        The **first non-zero** year of the path, not the first year: an estate
        policy is a no-op in its opening years by construction (the receipts
        lag alone guarantees one), and anchoring on a zero would make
        :meth:`estimate_static_revenue_effect` return 0.0, which the engine
        then books through the whole window.
        """
        for _year, effect in self.derived_revenue_path():
            if effect != 0.0:
                return effect
        return 0.0

    def _engine_growth_rate(self) -> float:
        """The growth rate ``ScoringEngine`` will apply to this policy."""
        if self.annual_revenue_change_billions is not None:
            return 0.0
        return ESTATE_ENGINE_GROWTH_RATE

    def get_phase_in_factor(self, year: int) -> float:
        """
        Phase factor, carrying the derived year path when ``mode`` is derived.

        ``ScoringEngine`` books an ``EstateTaxPolicy`` as
        ``estimate_static_revenue_effect() * (1 + g)**t * get_phase_in_factor(year)``
        and passes no year into the first term, so a year-indexed path can only
        reach the engine through this factor. In derived mode it returns the
        ratio of the module's own path in ``year`` to the flat-and-grown level
        the engine would otherwise book from :meth:`derived_anchor_effect`,
        which leaves the scored annual exactly equal to
        :meth:`derived_annual_effect`. Reported mode is untouched.
        """
        base = super().get_phase_in_factor(year)
        if base == 0.0 or self.mode != ESTATE_MODE_DERIVED:
            return base
        anchor = self.derived_anchor_effect()
        if anchor == 0.0:
            return base
        engine_level = anchor * (1 + self._engine_growth_rate()) ** (year - self.start_year)
        if engine_level == 0.0:
            return base
        return base * self.derived_annual_effect(year) / engine_level

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of estate tax policy change.

        In ``reported`` mode this is the fitted annual constant when one is
        set. Otherwise the constant is ignored and the answer is
        :meth:`derived_anchor_effect` -- the first non-zero year of the
        structural path; every year, including the anchor's own, then arrives
        through :meth:`get_phase_in_factor`.

        Args:
            baseline_revenue: Baseline estate tax revenue (unused; the estate
                tax is scored from its own base, not off an aggregate line)
            use_real_data: Accepted for interface compatibility

        Returns:
            Revenue change in billions (negative = revenue loss)
        """
        del baseline_revenue, use_real_data
        if self.mode == ESTATE_MODE_REPORTED and self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions
        return self.derived_anchor_effect()

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to estate tax changes.

        Two channels, and only the first responds to the policy:

        - **Planning** (trusts, family partnerships, valuation discounts,
          charitable bequests). Reported estates respond to the *net-of-tax
          share*, so a rate change from ``t0`` to ``t1`` moves the reported
          base by ``((1-t1)/(1-t0)) ** planning_elasticity - 1`` with the
          elasticity frozen at Kopczuk & Slemrod (2003)'s 0.16. An exemption
          change leaves the marginal rate alone and so produces no planning
          response, which the previous flat 15%-of-static rule could not say.
        - **Gift shifting** to inter vivos transfers, still a flat share.

        Returns:
            Behavioral offset in billions
        """
        baseline_rate = CURRENT_ESTATE_TAX_RATE
        policy_rate = self.get_rate_for_year(self.start_year)
        planning_offset = 0.0
        if policy_rate != baseline_rate and max(policy_rate, baseline_rate) < 1.0:
            net_of_tax_ratio = (1.0 - policy_rate) / (1.0 - baseline_rate)
            response = net_of_tax_ratio ** self.planning_elasticity - 1.0
            planning_offset = abs(static_effect) * abs(response)

        gift_offset = abs(static_effect) * self.gift_shifting_elasticity

        total_offset = planning_offset + gift_offset

        # Offset reduces revenue gain or loss
        if static_effect > 0:
            return -total_offset  # Reduces revenue gain
        else:
            return total_offset  # Reduces revenue loss


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_tcja_estate_extension(
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = ESTATE_APP_MODE,
) -> EstateTaxPolicy:
    """
    Create policy to extend TCJA estate tax exemption.

    Keeps the ~$14M exemption (indexed) instead of reverting
    to ~$6.4M in 2026.

    CBO estimate: $167B cost over 10 years
    """
    return EstateTaxPolicy(
        name="Extend TCJA Estate Exemption",
        description="Extend doubled estate tax exemption (~$14M vs ~$6.4M) beyond 2025",
        policy_type=PolicyType.ESTATE_TAX,
        extend_tcja_exemption=True,
        planning_elasticity=0.0,  # Behavioral response already in calibration
        gift_shifting_elasticity=0.0,
        # Window-average of CBO $167B / 10yr (do not grow again in the scorer)
        annual_revenue_change_billions=-16.7,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_biden_estate_proposal(
    exemption: float = 3_500_000,
    rate: float = 0.45,
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = ESTATE_APP_MODE,
) -> EstateTaxPolicy:
    """
    Create Biden-style estate tax reform.

    Key features:
    - Lower exemption to $3.5M (from $14M)
    - Increase rate to 45% (from 40%)

    This would dramatically increase taxable estates and revenue.
    Carried benchmark: $450B over 10 years. ``benchmark_sources.py`` records
    the published line item as JCT's $429.6B score of "For the 99.5 Percent
    Act", which covers ten sections this module does not implement, so the
    target is an upper bound on the exemption-and-rate change alone.
    """
    return EstateTaxPolicy(
        name="Biden Estate Tax Reform",
        description=f"Lower exemption to ${exemption/1e6:.1f}M, raise rate to {rate*100:.0f}%",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=exemption,
        new_rate=rate,
        planning_elasticity=0.0,  # Behavioral response in calibration
        gift_shifting_elasticity=0.0,
        # Window-average of the $450B / 10yr target (do not grow again)
        annual_revenue_change_billions=45.0,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_warren_estate_proposal(
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = ESTATE_APP_MODE,
) -> EstateTaxPolicy:
    """
    Create Warren-style progressive estate tax.

    Key features:
    - $3.5M exemption
    - Progressive rates: 45% up to $10M, 55% up to $50M, 65% over $1B
    - Limit valuation discounts

    For simplicity, we use the effective average rate.
    """
    return EstateTaxPolicy(
        name="Warren Progressive Estate Tax",
        description="$3.5M exemption, progressive rates up to 65% on billionaires",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=3_500_000,
        new_rate=0.55,  # Effective average rate
        limit_valuation_discounts=True,
        discount_limit_pct=0.10,
        planning_elasticity=0.0,  # Behavioral already in PWBM-style calibration
        gift_shifting_elasticity=0.0,
        # Window-average of PWBM ~$2.6T / 10yr (do not grow again in the scorer)
        annual_revenue_change_billions=260.0,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_estate_rate_change(
    rate_change: float,
    start_year: int = 2025,
    duration_years: int = 10,
    name: str | None = None,
) -> EstateTaxPolicy:
    """
    Create a simple estate tax rate change.

    Args:
        rate_change: Change in rate (e.g., 0.05 for 5pp increase)
        start_year: First year of policy
        duration_years: Duration
        name: Optional custom name

    Returns:
        EstateTaxPolicy for rate change
    """
    direction = "increase" if rate_change > 0 else "decrease"
    new_rate = CURRENT_ESTATE_TAX_RATE + rate_change

    # Estimate revenue effect
    # ~$32B baseline revenue, rate change proportional
    baseline_revenue = BASELINE_ESTATE_DATA["revenue_2024"]
    static_pct_change = rate_change / CURRENT_ESTATE_TAX_RATE
    annual_change = baseline_revenue * static_pct_change

    return EstateTaxPolicy(
        name=name or f"Estate Tax Rate {direction.title()} to {new_rate*100:.0f}%",
        description=f"Change estate tax rate from 40% to {new_rate*100:.0f}%",
        policy_type=PolicyType.ESTATE_TAX,
        rate_change=rate_change,
        planning_elasticity=KOPCZUK_SLEMROD_PLANNING_ELASTICITY,
        annual_revenue_change_billions=annual_change,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_estate_exemption_change(
    new_exemption: float,
    start_year: int = 2025,
    duration_years: int = 10,
    name: str | None = None,
) -> EstateTaxPolicy:
    """
    Create an estate tax exemption change policy.

    The annual is the window average of the structural path, so this factory
    now returns a real number for an exemption cut. Under the pre-2026-09
    two-point blend it returned exactly $0.0B for every exemption at or below
    the post-sunset level, because the blend's count-times-average product was
    invariant in the exemption.

    Args:
        new_exemption: New exemption level in dollars
        start_year: First year of policy
        duration_years: Duration
        name: Optional custom name

    Returns:
        EstateTaxPolicy for exemption change
    """
    policy = EstateTaxPolicy(
        name=name or f"Estate Exemption to ${new_exemption/1e6:.1f}M",
        description=f"Set estate tax exemption to ${new_exemption:,.0f}",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=new_exemption,
        planning_elasticity=KOPCZUK_SLEMROD_PLANNING_ELASTICITY,
        start_year=start_year,
        duration_years=duration_years,
    )

    # Calculate annual revenue change (window average of the derived path)
    policy.annual_revenue_change_billions = policy.derived_window_average()

    return policy


def create_eliminate_estate_tax(
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = ESTATE_APP_MODE,
) -> EstateTaxPolicy:
    """
    Create policy to eliminate the estate tax entirely.

    Estimated cost: ~$350B over 10 years (foregone revenue)
    """
    return EstateTaxPolicy(
        name="Eliminate Estate Tax",
        description="Repeal the federal estate tax entirely",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=float('inf'),  # Effectively no tax
        new_rate=0.0,
        planning_elasticity=0.0,  # No behavioral offset needed
        gift_shifting_elasticity=0.0,
        # Window-average of ~$350B / 10yr foregone revenue
        annual_revenue_change_billions=-35.0,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

ESTATE_VALIDATION_SCENARIOS = {
    "extend_tcja_exemption": {
        "description": "Extend TCJA estate exemption",
        "policy_factory": "create_tcja_estate_extension",
        "expected_10yr": 167.0,  # CBO estimate (cost = positive)
        "source": "CBO",
        "notes": "Keep $14M+ exemption instead of reversion to $6.4M",
    },
    "biden_estate_reform": {
        "description": "Biden estate tax reform ($3.5M, 45%)",
        "policy_factory": "create_biden_estate_proposal",
        "expected_10yr": -450.0,  # Revenue gain (negative = deficit reduction)
        "source": "Treasury estimate",
        "notes": "Lower exemption + higher rate raises significant revenue",
    },
}


def estimate_estate_revenue(policy: EstateTaxPolicy) -> dict:
    """
    Estimate total revenue effect of an estate tax policy.

    In ``derived`` mode the year path is the module's own, so it is summed
    directly rather than grown off a single annual -- growing it again would
    apply the base's growth twice.

    Returns dict with:
        - annual_static: Average annual static effect
        - ten_year_static: Total 10-year static effect
        - behavioral_offset: Total behavioral offset
        - net_effect: Final effect after behavioral response
    """
    if policy.mode == ESTATE_MODE_DERIVED:
        path = np.array([effect for _year, effect in policy.derived_revenue_path()])
        annual_static = float(path.mean()) if path.size else 0.0
        behavioral = policy.estimate_behavioral_offset(annual_static)
        share = behavioral / annual_static if annual_static else 0.0
        return {
            "annual_static": annual_static,
            "ten_year_static": float(path.sum()),
            "behavioral_offset": float(path.sum()) * share,
            "net_effect": float(path.sum()) * (1.0 + share),
        }

    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)

    # Apply growth (~3%/year for wealth growth)
    years = np.arange(10)
    annual_effects = annual_static * (1.03 ** years)
    behavioral_effects = behavioral * (1.03 ** years)

    ten_year_static = np.sum(annual_effects)
    ten_year_behavioral = np.sum(behavioral_effects)

    return {
        "annual_static": annual_static,
        "ten_year_static": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_effect": ten_year_static + ten_year_behavioral,
    }
