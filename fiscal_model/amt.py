"""
Alternative Minimum Tax (AMT) Module

Models federal Alternative Minimum Tax policy changes including:
- Individual AMT exemption level changes
- Phase-out threshold changes
- AMT rate changes (26%/28%)
- Corporate AMT (CAMT - 15% book minimum)

Key data sources:
- CBO: Budget Options, Baseline Projections
- JCT: TCJA scores, revenue estimates
- Tax Policy Center: AMT taxpayer estimates

Current Law (TCJA, through 2025):
- Single exemption: $88,100 (2025), phased out above $626,350
- MFJ exemption: $137,000 (2025), phased out above $1,218,700
- Rates: 26% on first $232,600 (MFJ), 28% above
- Taxpayers affected: ~200,000/year
- Revenue: ~$5B/year

Scheduled 2026 (post-TCJA sunset):
- Single exemption: ~$60,000 (projected)
- MFJ exemption: ~$93,000 (projected)
- Phase-out thresholds drop significantly
- Taxpayers affected: 7.6M in 2026, rising to 10.3M by 2035 (TPC T25-0049)
- Revenue: $71.6B in 2026, rising to $124.2B by 2035 (TPC T25-0049)

Corporate AMT (IRA 2022, permanent):
- 15% on adjusted financial statement income
- Applies to corps with $1B+ avg annual income
- Revenue: ~$22B/year

Scoring modes
-------------
Every policy in this module carries a ``mode``. ``reported`` scores the fitted
``annual_revenue_change_billions`` constant and is what the shipped app uses;
``derived`` ignores it and prices the policy from the published year-indexed
AMT path in ``data_files/amt/tpc_t25_0049_aggregate_amt.csv`` through the
module's own exemption machinery. See the SCORING MODES block below for which
path each caller takes and why.
"""

import csv
from dataclasses import dataclass, field
from enum import Enum
from functools import cache, lru_cache
from pathlib import Path

import numpy as np

from .policies import PolicyType, TaxPolicy


class AMTType(Enum):
    """Type of AMT being modeled."""
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"  # Book minimum tax from IRA


# =============================================================================
# SCORING MODES
# =============================================================================
# Owner Decision 1 (planning/MODELING_IMPROVEMENT.md §6.1, accepted
# 2026-09-01): a calibrated module keeps its fitted annuals as a `reported`
# mode alongside a `derived` mode that scores from structure instead.

#: Score from the fitted ``annual_revenue_change_billions`` constant.
AMT_MODE_REPORTED = "reported"

#: Ignore the fitted constant and score from the published year-indexed AMT
#: path (TPC T25-0049) through this module's own exemption machinery.
AMT_MODE_DERIVED = "derived"

AMT_MODES = (AMT_MODE_REPORTED, AMT_MODE_DERIVED)

#: What the shipped app scores. Decision 1 keeps a module on ``reported``
#: until its derived error beats its fitted error; AMT's does not (see
#: ``planning/lanes/L5_amt.md`` §4), so every preset stays on ``reported``.
AMT_APP_MODE = AMT_MODE_REPORTED

#: What the *held-out* validation path scores. ``validation/loo.py``'s
#: ``run_amt_loo`` builds every individual-AMT case in this mode, so the
#: leave-one-out number now measures the structural path rather than a scalar
#: re-derivation of the fitted constant.
AMT_HELD_OUT_MODE = AMT_MODE_DERIVED

#: What the by-construction scorecard scores. Decision 1 asks for ``derived``
#: here too, and this constant is the single line that would flip it — but it
#: cannot flip yet, and the reason is a gate rather than the model.
#: ``repeal_individual_amt`` is a locked id in ``validation/holdout.py``'s
#: ``revenue-scorecard-post-lock-2026-05-02`` protocol, and
#: ``fiscal_model/readiness.py`` hard-*fails* strict readiness on any holdout
#: entry rated Poor. Derived scores that case at roughly +110% against a $450B
#: target whose own provenance record (``validation/benchmark_sources.py``)
#: puts the published line item at $1,357.1B and calls $450B "a five-year
#: number sitting in a ten-year column". Flipping before the target is
#: corrected would break a release gate for a reason that is not about model
#: quality, and loosening the gate to get green is what
#: ``MODELING_IMPROVEMENT.md`` §4 forbids. The flip is an owner call that
#: belongs with the target correction.
AMT_SCORECARD_MODE = AMT_MODE_REPORTED

#: Growth rate ``ScoringEngine`` applies to an ``AMTPolicy``'s annual static
#: effect (``scoring_engine._growth_tax_policy_handlers``). Derived mode
#: divides it back out year by year so the module's own path is what gets
#: scored; ``tests/test_amt_derived.py`` pins the two together.
AMT_ENGINE_GROWTH_RATE = 0.03


# =============================================================================
# CURRENT LAW PARAMETERS
# =============================================================================

# Individual AMT exemption levels under TCJA (inflation-indexed)
AMT_EXEMPTIONS_TCJA = {
    # (single, mfj, mfs)
    2024: (85_700, 133_300, 66_650),
    2025: (88_100, 137_000, 68_500),
    # Post-TCJA sunset (estimated)
    2026: (60_000, 93_000, 46_500),
    2027: (62_000, 96_000, 48_000),
    2028: (64_000, 99_000, 49_500),
    2029: (66_000, 102_000, 51_000),
    2030: (68_000, 105_000, 52_500),
    2031: (70_000, 108_000, 54_000),
    2032: (72_000, 111_000, 55_500),
    2033: (74_000, 114_000, 57_000),
    2034: (76_000, 117_000, 58_500),
}

# If TCJA is extended (keep higher exemptions)
AMT_EXEMPTIONS_TCJA_EXTENDED = {
    2026: (91_000, 141_000, 70_500),
    2027: (94_000, 145_000, 72_500),
    2028: (97_000, 150_000, 75_000),
    2029: (100_000, 155_000, 77_500),
    2030: (103_000, 160_000, 80_000),
    2031: (106_000, 165_000, 82_500),
    2032: (109_000, 170_000, 85_000),
    2033: (112_000, 175_000, 87_500),
    2034: (115_000, 180_000, 90_000),
}

# Phase-out thresholds under TCJA
AMT_PHASEOUT_TCJA = {
    # (single, mfj) - exemption phases out at 25 cents per dollar above these
    2024: (609_350, 1_218_700),
    2025: (626_350, 1_252_700),
    # Post-TCJA (reverts to lower thresholds)
    2026: (150_000, 200_000),  # Pre-TCJA levels (estimated with inflation)
    2027: (155_000, 206_000),
    2028: (160_000, 212_000),
    2029: (165_000, 218_000),
    2030: (170_000, 225_000),
}

# AMT rates (unchanged by TCJA)
AMT_RATES = {
    "first_tier": 0.26,  # 26% on AMTI up to threshold
    "second_tier": 0.28,  # 28% above threshold
    "tier_threshold_mfj": 232_600,  # 2025 MFJ
    "tier_threshold_single": 116_300,  # 2025 single
}

# Corporate AMT (CAMT) from Inflation Reduction Act 2022
CORPORATE_AMT = {
    "rate": 0.15,  # 15% book minimum tax
    "threshold": 1_000_000_000,  # $1B average annual income
    "revenue_per_year": 22.0,  # ~$22B/year (CBO)
}

# Baseline data
#
# These are the module's legacy *single-point* summary of the two AMT regimes,
# rounded from the Oct-2018 vintage of TPC's aggregate AMT table. They are kept
# because they are exported and read elsewhere, but nothing in the derived path
# uses them: the year-indexed path below (TPC T25-0049, April 2025) supersedes
# them, and the two disagree by about 15% on the post-sunset level, which is the
# vintage uncertainty around this projection.
BASELINE_AMT_DATA = {
    # Taxpayers affected
    "taxpayers_tcja": 200_000,  # Under high TCJA exemptions
    "taxpayers_post_tcja": 7_300_000,  # After exemptions drop (TPC)

    # Revenue (billions per year)
    "revenue_tcja": 5.0,  # Under TCJA (~$5B/year)
    "revenue_post_tcja_2030": 75.0,  # Projected after sunset (~$75B by 2030)

    # Average AMT liability
    "avg_amt_tcja": 25_000,  # Higher-income taxpayers under TCJA
    "avg_amt_post_tcja": 10_000,  # More taxpayers, lower average

    # Behavioral parameters
    "timing_elasticity": 0.15,  # Income timing response
    "avoidance_elasticity": 0.10,  # Tax planning response
}

# CBO/JCT official estimates.
#
# Reference only since lane L5: the two individual-AMT annuals here are
# window-average calibrations fitted to the $450B benchmarks, and neither the
# reported nor the derived scoring path reads them any more. Reported mode
# reads the policy's own ``annual_revenue_change_billions``; derived mode reads
# nothing but the published path and the exemption schedules.
CBO_AMT_ESTIMATES = {
    # Cost of extending TCJA AMT relief
    "extend_tcja_10yr": 450.0,  # ~$450B over 10 years (from TCJA component)
    "extend_tcja_annual": 39.3,  # Average annual (calibrated with 3% growth)

    # Revenue from letting TCJA expire (baseline)
    "tcja_expiration_10yr": 450.0,  # Revenue GAIN if TCJA expires

    # Current individual AMT revenue
    "current_individual_annual": 5.0,  # ~$5B/year under TCJA

    # Corporate AMT (permanent, not affected by TCJA sunset)
    "camt_annual": 22.0,  # ~$22B/year from IRA 2022
    "camt_10yr": 220.0,

    # Repeal individual AMT entirely
    "repeal_individual_10yr": 450.0,  # Cost if repealed (loses $450B revenue)
}


# =============================================================================
# PUBLISHED YEAR-INDEXED AMT PATH
# =============================================================================
# Urban-Brookings Tax Policy Center, Table T25-0049, "Aggregate Alternative
# Minimum Tax (AMT) Projections, 2024-2035" (3 April 2025). Its baseline is
# "the law in place for each year as of January 1, 2025", which still carries
# the TCJA sunset — so 2024-2025 sit under TCJA's larger exemption and
# 2026-2035 after it lapses. That is the counterfactual both individual-AMT
# benchmarks describe. Provenance, footnotes and the cross-check against the
# Oct-2018 vintage are in the CSV's own header.
#
# The table settles a question the plan left open. §3 L5 supposed the module
# over-predicted because the window "ramps from the 2026 sunset" and the module
# has no ramp. TPC shows no ramp: AMT payers go 0.2M in 2025 to 7.6M in 2026,
# a cliff, and the post-sunset path then *grows*, $71.6B to $124.2B. The flat
# ~$73B/yr steady state was therefore the window's early-year level, not its
# average, and indexing the path by year raises the score rather than lowering
# it.

TPC_AMT_PROJECTIONS_PATH = (
    Path(__file__).parent / "data_files" / "amt" / "tpc_t25_0049_aggregate_amt.csv"
)

#: Years under TCJA's larger AMT exemption.
REGIME_TCJA = "tcja"

#: Years after the TCJA exemption lapses.
REGIME_POST_SUNSET = "post_sunset"


@dataclass(frozen=True)
class AMTYearRow:
    """
    One published year of the aggregate AMT path.

    ``payers`` is reconstructed as ``revenue / avg_liability`` rather than read
    from TPC's "Number (millions)" column, which is rounded to one decimal of a
    million and so carries a single significant figure at 0.2M, while revenue
    and revenue-per-payer are printed to three or four. The reconstruction
    agrees with the printed count to within TPC's own rounding, which
    ``tests/test_amt_derived.py`` pins.
    """

    year: int
    regime: str
    revenue_billions: float
    avg_liability: float
    payers: float
    printed_payers_millions: float


@lru_cache(maxsize=1)
def load_tpc_amt_projections() -> dict[int, AMTYearRow]:
    """Load the transcribed TPC T25-0049 aggregate AMT path, keyed by year."""
    rows: dict[int, AMTYearRow] = {}
    with open(TPC_AMT_PROJECTIONS_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(line for line in handle if not line.startswith("#"))
        for record in reader:
            year = int(record["year"])
            revenue = float(record["amt_revenue_billions"])
            avg_liability = float(record["amt_revenue_per_payer_dollars"])
            rows[year] = AMTYearRow(
                year=year,
                regime=record["regime"],
                revenue_billions=revenue,
                avg_liability=avg_liability,
                payers=revenue * 1e9 / avg_liability,
                printed_payers_millions=float(record["amt_payers_millions"]),
            )
    if not rows:
        raise ValueError(f"No AMT projection rows found in {TPC_AMT_PROJECTIONS_PATH}")
    return rows


@cache
def _regime_series(regime: str) -> tuple[AMTYearRow, ...]:
    """Published rows for one regime, in year order."""
    rows = [row for row in load_tpc_amt_projections().values() if row.regime == regime]
    if not rows:
        raise ValueError(f"Unknown AMT regime {regime!r}")
    return tuple(sorted(rows, key=lambda row: row.year))


def _compound_growth(first: float, last: float, years: int) -> float:
    if years <= 0 or first <= 0 or last <= 0:
        return 0.0
    return (last / first) ** (1.0 / years) - 1.0


@cache
def _regime_growth(regime: str) -> tuple[float, float]:
    """
    ``(payer growth, per-payer liability growth)`` implied by a regime's own
    published years. This is the single extrapolation rule the module applies
    on top of the table, it is the same rule for both regimes, and it is fitted
    to nothing: each regime is continued at the compound rate its own printed
    rows imply.
    """
    series = _regime_series(regime)
    if len(series) < 2:
        return 0.0, 0.0
    span = series[-1].year - series[0].year
    return (
        _compound_growth(series[0].payers, series[-1].payers, span),
        _compound_growth(series[0].avg_liability, series[-1].avg_liability, span),
    )


def amt_regime_year(regime: str, year: int) -> AMTYearRow:
    """The regime's row for ``year``, extrapolated beyond the published table."""
    series = _regime_series(regime)
    for row in series:
        if row.year == year:
            return row
    anchor = series[-1] if year > series[-1].year else series[0]
    span = year - anchor.year
    payer_growth, liability_growth = _regime_growth(regime)
    payers = anchor.payers * (1.0 + payer_growth) ** span
    avg_liability = anchor.avg_liability * (1.0 + liability_growth) ** span
    return AMTYearRow(
        year=year,
        regime=regime,
        revenue_billions=payers * avg_liability / 1e9,
        avg_liability=avg_liability,
        payers=payers,
        printed_payers_millions=payers / 1e6,
    )


def _schedule_row(
    schedule: dict[int, tuple[float, float, float]],
    year: int,
) -> tuple[float, float, float]:
    """
    One year's ``(single, mfj, mfs)`` exemptions, clamped to the nearest
    published year. Clamping to the *nearest* end matters: falling back to the
    last row for a year that precedes the schedule would price a 2025 policy on
    2034's exemptions.
    """
    if year in schedule:
        return schedule[year]
    return schedule[max(schedule)] if year > max(schedule) else schedule[min(schedule)]


def _schedule_mfj(schedule: dict[int, tuple[float, float, float]], year: int) -> float:
    """MFJ exemption from one of the module's exemption schedules."""
    return float(_schedule_row(schedule, year)[1])


@cache
def _last_tcja_regime_year() -> int:
    """Last published year in which TCJA's larger AMT exemption still applies."""
    return _regime_series(REGIME_TCJA)[-1].year


def current_law_amt_exemption_mfj(year: int) -> float:
    """
    MFJ AMT exemption under **current law**, ignoring any policy change.

    This is the counterfactual leg the exemption-change branch was missing:
    it used to compare the reform schedule against itself.
    """
    return _schedule_mfj(AMT_EXEMPTIONS_TCJA, year)


def _amt_anchors(year: int) -> tuple[tuple[float, AMTYearRow], tuple[float, AMTYearRow]]:
    """
    The two published regimes as ``(MFJ exemption, path row)`` anchors.

    Low exemption = current law for that year (post-sunset from 2026); high
    exemption = the TCJA schedule extended. Both anchors are the *same* row
    while TCJA is still in force, which collapses the interpolation to a
    single point, as it should.
    """
    low_regime = (
        REGIME_TCJA if year <= _last_tcja_regime_year() else REGIME_POST_SUNSET
    )
    low = (_schedule_mfj(AMT_EXEMPTIONS_TCJA, year), amt_regime_year(low_regime, year))
    high = (
        _schedule_mfj(AMT_EXEMPTIONS_TCJA_EXTENDED, year),
        amt_regime_year(REGIME_TCJA, year),
    )
    if high[0] <= low[0]:
        return low, low
    return low, high


def _interpolate_on_exemption(
    exemption_mfj: float,
    year: int,
    attribute: str,
) -> float:
    """
    One published quantity, evaluated at an arbitrary MFJ exemption.

    Between the two anchors the quantity moves linearly in the exemption — the
    functional form the module already used, kept deliberately rather than
    replaced, because no published evidence in scope pins a better one.
    Outside them it scales hyperbolically off the nearer anchor: halving the
    exempt amount roughly doubles the caught population, and the same factor
    carries the revenue. Both branches are monotone decreasing in the
    exemption, and continuous at each anchor.
    """
    (low_e, low_row), (high_e, high_row) = _amt_anchors(year)
    low = float(getattr(low_row, attribute))
    high = float(getattr(high_row, attribute))

    if high_e <= low_e or exemption_mfj <= low_e:
        return low * (low_e / exemption_mfj)
    if exemption_mfj >= high_e:
        return high * (high_e / exemption_mfj)
    frac = (exemption_mfj - low_e) / (high_e - low_e)
    return low + frac * (high - low)


def amt_revenue_billions(exemption_mfj: float, year: int) -> float:
    """Individual-AMT revenue in ``year`` at an MFJ exemption, in billions."""
    if exemption_mfj == float("inf"):
        return 0.0
    if exemption_mfj <= 0:
        raise ValueError(f"AMT exemption must be positive, got {exemption_mfj}")
    return _interpolate_on_exemption(exemption_mfj, year, "revenue_billions")


def amt_payers_and_liability(exemption_mfj: float, year: int) -> tuple[float, float]:
    """
    Affected-payer count and average liability in ``year`` at an MFJ exemption.

    Revenue and the payer count are each interpolated on their own; the average
    liability is their ratio rather than a third interpolation. Interpolating
    the average separately would break monotonicity — a rising exemption drops
    payers but raises the average of those left, and the *product* of two
    linear paths can turn upward, which would have priced an exemption
    *increase* as a revenue *gain*.
    """
    if exemption_mfj == float("inf"):
        return 0.0, 0.0
    if exemption_mfj <= 0:
        raise ValueError(f"AMT exemption must be positive, got {exemption_mfj}")

    payers = _interpolate_on_exemption(exemption_mfj, year, "payers")
    revenue = _interpolate_on_exemption(exemption_mfj, year, "revenue_billions")
    avg_liability = revenue * 1e9 / payers if payers else 0.0
    return payers, avg_liability


@dataclass
class AMTPolicy(TaxPolicy):
    """
    Alternative Minimum Tax policy modeling exemption, rate, and threshold changes.

    Models both individual AMT and corporate AMT (book minimum tax).

    Key parameters:
        amt_type: Whether modeling individual or corporate AMT
        extend_tcja_relief: Extend TCJA's higher exemptions past 2025
        exemption_change: Change in exemption levels (dollars)
        new_exemption_single: Specific new exemption (single)
        new_exemption_mfj: Specific new exemption (MFJ)
        repeal_individual_amt: Fully repeal individual AMT
        rate_change: Change in AMT rates

    Behavioral responses:
        - Income timing (defer income to avoid AMT)
        - Tax planning (restructure to minimize AMTI)

    Scoring modes
    -------------
    ``reported`` (the app default) returns ``annual_revenue_change_billions``
    when it is set, which is what every shipped preset does today.

    ``derived`` ignores that constant and prices each year as
    ``payers(exemption, year) x average liability(exemption, year)``, netted
    against the same identity evaluated at the **current-law** exemption, with
    both legs anchored on TPC T25-0049. The result is a year path rather than a
    level, and it reaches the scoring engine through
    :meth:`get_phase_in_factor` — see that method for why.
    """

    # AMT type
    amt_type: AMTType = field(default=AMTType.INDIVIDUAL)

    # Scoring mode: "reported" (fitted annual) or "derived" (structural path)
    mode: str = AMT_APP_MODE

    # TCJA extension
    extend_tcja_relief: bool = False  # Keep TCJA's high exemptions post-2025

    # Exemption changes (individual AMT)
    exemption_change: float = 0.0  # Dollar change in exemption
    new_exemption_single: float | None = None
    new_exemption_mfj: float | None = None

    # Full repeal options
    repeal_individual_amt: bool = False
    repeal_corporate_amt: bool = False

    # Rate changes
    rate_change: float = 0.0  # Change to both tiers
    new_first_tier_rate: float | None = None  # 26% default
    new_second_tier_rate: float | None = None  # 28% default

    # Phase-out changes
    phase_out_threshold_change: float = 0.0  # Change to phase-out start

    # Behavioral parameters
    timing_elasticity: float = 0.15
    avoidance_elasticity: float = 0.10

    # Base year for calculations
    base_year: int = 2024

    # Calibration
    annual_revenue_change_billions: float | None = None

    def __post_init__(self):
        """Set default policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.INCOME_TAX  # AMT is part of income tax
        if self.mode not in AMT_MODES:
            raise ValueError(
                f"mode must be one of {AMT_MODES}, got {self.mode!r}"
            )
        super().__post_init__()

    def get_exemption_for_year(
        self,
        year: int,
        filing_status: str = "mfj"
    ) -> float:
        """
        Get the effective AMT exemption for a given year.

        Args:
            year: Tax year
            filing_status: 'single', 'mfj', or 'mfs'

        Returns:
            Exemption amount in dollars
        """
        if self.repeal_individual_amt:
            return float('inf')  # No AMT = infinite exemption

        # Specific exemption overrides
        if filing_status == "single" and self.new_exemption_single is not None:
            return self.new_exemption_single
        if filing_status == "mfj" and self.new_exemption_mfj is not None:
            return self.new_exemption_mfj
        if filing_status == "mfs" and self.new_exemption_mfj is not None:
            return self.new_exemption_mfj / 2  # MFS is half of MFJ

        # TCJA extension. Before the sunset there is nothing to extend, so the
        # extension is a no-op and both legs read the same schedule; without
        # that guard a 2025 start compared current law's $137,000 against the
        # extended schedule's out-of-range fallback and booked a revenue loss
        # in a year the policy cannot touch.
        if self.extend_tcja_relief and year > _last_tcja_regime_year():
            exemptions = _schedule_row(AMT_EXEMPTIONS_TCJA_EXTENDED, year)
        else:
            # Current law baseline
            exemptions = _schedule_row(AMT_EXEMPTIONS_TCJA, year)

        # Extract by filing status
        idx = {"single": 0, "mfj": 1, "mfs": 2}.get(filing_status, 1)
        base = exemptions[idx]

        return base + self.exemption_change

    def get_rate_for_tier(self, tier: int = 1) -> float:
        """
        Get AMT rate for a tier (1 = 26%, 2 = 28%).

        Args:
            tier: 1 for first tier, 2 for second tier

        Returns:
            Tax rate as decimal
        """
        if tier == 1:
            if self.new_first_tier_rate is not None:
                return self.new_first_tier_rate
            return AMT_RATES["first_tier"] + self.rate_change
        else:
            if self.new_second_tier_rate is not None:
                return self.new_second_tier_rate
            return AMT_RATES["second_tier"] + self.rate_change

    def estimate_affected_taxpayers(
        self,
        year: int = 2026,
        exemption: float | None = None,
    ) -> int:
        """
        Estimate the number of taxpayers affected by the AMT in ``year``.

        Under TCJA's high exemptions the published anchor is ~0.2M; after the
        sunset it is ~7.6M (TPC T25-0049), and the count now moves with the
        year as well as with the exemption.

        Args:
            year: Tax year.
            exemption: MFJ exemption to evaluate. Defaults to the policy's own
                reform schedule. Pass ``current_law_amt_exemption_mfj(year)``
                to ask the counterfactual question — how many filers current
                law catches — which is the leg
                :meth:`estimate_static_revenue_effect` used to be missing.
        """
        if exemption is None:
            if self.repeal_individual_amt:
                return 0
            exemption = self.get_exemption_for_year(year, "mfj")
        payers, _ = amt_payers_and_liability(exemption, year)
        return int(payers)

    def _rate_scale(self) -> float:
        """Liability scale implied by a change to the 26%/28% AMT rates."""
        baseline = AMT_RATES["first_tier"] + AMT_RATES["second_tier"]
        reform = self.get_rate_for_tier(1) + self.get_rate_for_tier(2)
        return reform / baseline if baseline else 1.0

    def _corporate_static_effect(self) -> float:
        """Corporate AMT (CAMT) annual effect, in billions."""
        if self.repeal_corporate_amt:
            return -CORPORATE_AMT["revenue_per_year"]
        if self.rate_change != 0:
            return CORPORATE_AMT["revenue_per_year"] * (
                self.rate_change / CORPORATE_AMT["rate"]
            )
        return 0.0

    def derived_annual_effect(self, year: int) -> float:
        """
        Structural individual-AMT revenue effect in ``year``, in billions.

        Negative means a revenue loss. The baseline leg is evaluated at the
        **current-law** exemption and the policy leg at the reform exemption,
        which is the fix for the dead branch this replaced: it built both legs
        from the same call, so every exemption change scored exactly zero.

        Repeal, TCJA extension and a plain exemption change are all the same
        identity here rather than three separate constants.
        """
        baseline = amt_revenue_billions(current_law_amt_exemption_mfj(year), year)
        if self.repeal_individual_amt:
            return -baseline
        policy = amt_revenue_billions(self.get_exemption_for_year(year, "mfj"), year)
        return policy * self._rate_scale() - baseline

    def derived_revenue_path(self) -> list[tuple[int, float]]:
        """The derived annual effects across the policy's own window."""
        return [
            (self.start_year + offset, self.derived_annual_effect(self.start_year + offset))
            for offset in range(self.duration_years)
        ]

    def derived_anchor_effect(self) -> float:
        """
        The level the engine multiplies, in derived mode.

        The **first non-zero** year of the path, not the first year. A policy
        can be a no-op in its opening years and bite later — extending TCJA
        relief from 2025 does nothing until the 2026 sunset — and anchoring on
        a zero would make ``estimate_static_revenue_effect`` return 0.0, which
        the engine then multiplies through the whole window and books the
        entire path as zero.
        """
        for _, effect in self.derived_revenue_path():
            if effect != 0.0:
                return effect
        return 0.0

    def get_phase_in_factor(self, year: int) -> float:
        """
        Phase factor, carrying the derived year path when ``mode`` is derived.

        ``ScoringEngine`` books an ``AMTPolicy`` as
        ``estimate_static_revenue_effect() * (1 + AMT_ENGINE_GROWTH_RATE)**t *
        get_phase_in_factor(year)`` and passes no year into the first term, so
        a year-indexed path can only reach the engine through this factor. In
        derived mode it therefore returns the ratio of the module's own path in
        ``year`` to the flat-and-grown level the engine would otherwise book
        from :meth:`derived_anchor_effect`, which leaves the scored annual
        exactly equal to :meth:`derived_annual_effect`. Reported mode is
        untouched.
        """
        base = super().get_phase_in_factor(year)
        if (
            base == 0.0
            or self.mode != AMT_MODE_DERIVED
            or self.amt_type == AMTType.CORPORATE
        ):
            return base
        anchor = self.derived_anchor_effect()
        if anchor == 0.0:
            return base
        engine_level = anchor * (1 + AMT_ENGINE_GROWTH_RATE) ** (year - self.start_year)
        return base * self.derived_annual_effect(year) / engine_level

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of an AMT policy change.

        In ``reported`` mode this is the fitted annual constant when one is
        set. In ``derived`` mode the constant is ignored and the answer is
        :meth:`derived_anchor_effect` -- the first non-zero year of the
        structural path; every year, including the anchor's own, then arrives
        through :meth:`get_phase_in_factor`.

        Args:
            baseline_revenue: Baseline revenue (unused; AMT is scored from its
                own base rather than off the aggregate income-tax line)
            use_real_data: Accepted for interface compatibility

        Returns:
            Revenue change in billions (negative = revenue loss)
        """
        if self.mode == AMT_MODE_REPORTED and self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        if self.amt_type == AMTType.CORPORATE:
            return self._corporate_static_effect()

        return self.derived_anchor_effect()

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to AMT changes.

        Behavioral responses include:
        - Income timing (accelerate/defer income)
        - Tax planning (restructure to minimize AMTI)
        - Charitable giving timing

        Returns:
            Behavioral offset in billions
        """
        # Timing response
        timing_offset = abs(static_effect) * self.timing_elasticity

        # Avoidance response
        avoidance_offset = abs(static_effect) * self.avoidance_elasticity

        total_offset = timing_offset + avoidance_offset

        # Offset reduces revenue gain or loss
        if static_effect > 0:
            return -total_offset  # Reduces revenue gain
        else:
            return total_offset  # Reduces revenue loss


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_extend_tcja_amt_relief(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = AMT_APP_MODE,
) -> AMTPolicy:
    """
    Create policy to extend TCJA AMT relief beyond 2025.

    Keeps the higher exemptions ($88K single, $137K MFJ) instead of
    reverting to pre-TCJA levels (~$60K single, ~$93K MFJ).

    CBO/JCT estimate: ~$450B cost over 10 years
    """
    return AMTPolicy(
        name="Extend TCJA AMT Relief",
        description="Extend higher AMT exemptions beyond 2025 sunset",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        extend_tcja_relief=True,
        timing_elasticity=0.0,  # Behavioral already in calibration
        avoidance_elasticity=0.0,
        # Calibrated to ~$450B over 10 years (with 3% annual growth)
        annual_revenue_change_billions=-39.3,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_repeal_individual_amt(
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = AMT_APP_MODE,
) -> AMTPolicy:
    """
    Create policy to fully repeal the individual AMT.

    This eliminates all individual AMT revenue.
    Under TCJA, this is ~$5B/year, growing to ~$75B/year after sunset.

    If starting post-2025 (after sunset), the 10-year cost is ~$450B.
    If starting in 2025 (before sunset), cost is lower (~$50B over 10 years).
    """
    # Cost depends on whether TCJA is still in effect
    if start_year <= 2025:
        # TCJA still in effect - lower revenue to lose
        annual_cost = -5.0  # ~$5B/year under TCJA
    else:
        # Post-TCJA - more revenue at stake
        annual_cost = -39.3  # Growing to ~$75B by 2030

    return AMTPolicy(
        name="Repeal Individual AMT",
        description="Fully repeal the individual Alternative Minimum Tax",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        repeal_individual_amt=True,
        timing_elasticity=0.0,
        avoidance_elasticity=0.0,
        annual_revenue_change_billions=annual_cost,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_repeal_corporate_amt(
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = AMT_APP_MODE,
) -> AMTPolicy:
    """
    Create policy to repeal the corporate AMT (book minimum tax).

    The 15% corporate AMT was enacted in IRA 2022 and is permanent.
    Repealing would cost ~$22B/year in lost revenue.
    """
    return AMTPolicy(
        name="Repeal Corporate AMT",
        description="Repeal the 15% book minimum tax (CAMT) from IRA 2022",
        policy_type=PolicyType.CORPORATE_TAX,
        amt_type=AMTType.CORPORATE,
        repeal_corporate_amt=True,
        timing_elasticity=0.0,
        avoidance_elasticity=0.0,
        # Calibrated: ~$220B over 10 years
        annual_revenue_change_billions=-19.2,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_increase_amt_exemption(
    exemption_increase: float = 25_000,
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = AMT_APP_MODE,
) -> AMTPolicy:
    """
    Create policy to increase AMT exemption levels.

    Args:
        exemption_increase: Dollar increase in exemption (e.g., $25,000)
        start_year: First year of policy
        duration_years: Duration

    Returns:
        AMTPolicy for exemption increase
    """
    # Rough estimate: each $25K exemption increase reduces affected taxpayers
    # and revenue by roughly 15%
    reduction_pct = 0.15 * (exemption_increase / 25_000)

    # Baseline post-TCJA revenue ~$39B/year (average)
    annual_cost = -39.3 * reduction_pct

    return AMTPolicy(
        name=f"AMT Exemption +${exemption_increase/1000:.0f}K",
        description=f"Increase AMT exemption by ${exemption_increase:,.0f}",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        exemption_change=exemption_increase,
        annual_revenue_change_billions=annual_cost,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_amt_rate_change(
    rate_change: float,
    start_year: int = 2025,
    duration_years: int = 10,
    mode: str = AMT_APP_MODE,
) -> AMTPolicy:
    """
    Create AMT rate change policy.

    Args:
        rate_change: Change in rate (e.g., -0.02 for 2pp cut)
        start_year: First year
        duration_years: Duration

    Returns:
        AMTPolicy for rate change
    """
    # Revenue effect proportional to rate change
    # Current combined rate ~27% average, baseline ~$40B/year post-TCJA
    avg_rate = (AMT_RATES["first_tier"] + AMT_RATES["second_tier"]) / 2
    baseline_revenue = 39.3  # Average annual post-TCJA
    pct_change = rate_change / avg_rate
    annual_change = baseline_revenue * pct_change

    direction = "increase" if rate_change > 0 else "decrease"
    new_first = AMT_RATES["first_tier"] + rate_change
    new_second = AMT_RATES["second_tier"] + rate_change

    return AMTPolicy(
        name=f"AMT Rate {direction.title()} {abs(rate_change)*100:.0f}pp",
        description=f"Change AMT rates to {new_first*100:.0f}%/{new_second*100:.0f}%",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        rate_change=rate_change,
        annual_revenue_change_billions=annual_change,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

AMT_VALIDATION_SCENARIOS = {
    "extend_tcja_amt": {
        "description": "Extend TCJA AMT relief",
        "policy_factory": "create_extend_tcja_amt_relief",
        "expected_10yr": 450.0,  # Cost (increases deficit)
        "source": "JCT/CBO",
        "notes": "Keep higher exemptions instead of sunset to pre-TCJA levels",
    },
    "repeal_individual_amt": {
        "description": "Repeal individual AMT (post-2025)",
        "policy_factory": "create_repeal_individual_amt",
        "kwargs": {"start_year": 2026},
        "expected_10yr": 450.0,  # Cost (lost revenue)
        "source": "CBO baseline",
        "notes": "Eliminate all individual AMT after TCJA expires",
    },
    "repeal_corporate_amt": {
        "description": "Repeal corporate AMT (CAMT)",
        "policy_factory": "create_repeal_corporate_amt",
        "expected_10yr": 220.0,  # Cost
        "source": "CBO",
        "notes": "Repeal 15% book minimum tax from IRA 2022",
    },
}


def estimate_amt_revenue(policy: AMTPolicy) -> dict:
    """
    Estimate total revenue effect of an AMT policy.

    Returns dict with:
        - annual_static: Average annual static effect
        - ten_year_static: Total 10-year static effect
        - behavioral_offset: Total behavioral offset
        - net_effect: Final effect after behavioral response
    """
    annual_static = policy.estimate_static_revenue_effect(0)

    if policy.mode == AMT_MODE_DERIVED and policy.amt_type == AMTType.INDIVIDUAL:
        # Derived mode already knows every year; do not re-grow it.
        annual_effects = np.array(
            [effect for _, effect in policy.derived_revenue_path()],
            dtype=float,
        )
    else:
        # Apply growth (~3%/year for income growth), matching the scoring engine
        years = np.arange(policy.duration_years)
        annual_effects = annual_static * (AMT_ENGINE_GROWTH_RATE + 1.0) ** years

    behavioral_effects = np.array(
        [policy.estimate_behavioral_offset(effect) for effect in annual_effects],
        dtype=float,
    )

    ten_year_static = np.sum(annual_effects)
    ten_year_behavioral = np.sum(behavioral_effects)

    return {
        "annual_static": annual_static,
        "ten_year_static": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_effect": ten_year_static + ten_year_behavioral,
    }
