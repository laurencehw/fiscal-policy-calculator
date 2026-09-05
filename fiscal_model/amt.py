"""
Alternative Minimum Tax (AMT) Module

Models federal Alternative Minimum Tax policy changes including:
- Individual AMT exemption level changes
- Phase-out threshold and claw-back-rate changes (IRC 55(d)(2))
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

Scheduled 2026 under the TCJA sunset (the counterfactual both individual-AMT
benchmarks describe, and what TPC T25-0049 projects):
- Single exemption: $72,000; MFJ $111,500 -- pre-TCJA law indexed forward
- Phase-out thresholds drop by an order of magnitude, to ~$212,300 MFJ, and
  the 25% claw-back above them is what makes high-income filers AMT payers
- Taxpayers affected: 7.6M in 2026, rising to 10.3M by 2035 (TPC T25-0049)
- Revenue: $71.6B in 2026, rising to $124.2B by 2035 (TPC T25-0049)

Enacted current law from 2026 (P.L. 119-21 sec. 70107) -- expressible as a
reform via ``create_pl119_21_amt`` but NOT the derived path's baseline, because
no TPC vintage projects a post-OBBBA AMT path:
- TCJA exemption made permanent ($140,200 MFJ in 2026)
- Phase-out thresholds reset DOWN to $500,000 / $1,000,000
- Claw-back rate raised from 25% to 50%

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
#: until its derived error beats its fitted error, and it still does not —
#: re-run against the corrected targets on 2026-09-02
#: (``planning/lanes/PROVENANCE_amt_insulin.md``), derived wins one of the
#: three AMT benchmarks and loses the other two:
#:
#: ===========================  ===========  ==========  =========  ==========
#: Benchmark                    Target       Reported    Derived    Winner
#: ===========================  ===========  ==========  =========  ==========
#: ``extend_tcja_amt``          $1,357.1B    -66.8%      -37.0%     derived
#: ``repeal_individual_amt``    $450B        +0.1%       +110.9%    reported
#: ``repeal_corporate_amt``     $220B        +0.05%      +14.6%     reported
#: ===========================  ===========  ==========  =========  ==========
#:
#: Mean 22.3% reported against 54.2% derived, so every preset stays on
#: ``reported`` and no shipped number changes. Read the two losing rows before
#: treating that as evidence for the fitted path: both targets are reproduced
#: by a constant fitted to them, so their ~0% is bookkeeping. The one row with
#: a target no constant was fitted to is the row derived wins.
AMT_APP_MODE = AMT_MODE_REPORTED

#: What the *held-out* validation path scores. ``validation/loo.py``'s
#: ``run_amt_loo`` builds every individual-AMT case in this mode, so the
#: leave-one-out number now measures the structural path rather than a scalar
#: re-derivation of the fitted constant.
AMT_HELD_OUT_MODE = AMT_MODE_DERIVED

#: What the by-construction scorecard scores. Decision 1 asks for ``derived``
#: here too, and this constant is the single line that would flip it. The
#: 2026-09-02 provenance pass corrected ``extend_tcja_amt``'s target to the
#: published $1,357.1B, which removes half the reason this was blocked — but
#: not the other half, and the remaining half is still a gate rather than the
#: model. ``repeal_individual_amt`` is a locked id in
#: ``validation/holdout.py``'s ``revenue-scorecard-post-lock-2026-05-02``
#: protocol, ``fiscal_model/readiness.py`` hard-*fails* strict readiness on any
#: holdout entry rated Poor, and derived scores that case at +110.9%. Its $450B
#: target could not be corrected: the search recorded in
#: ``validation/benchmark_sources.py`` found no published score of a
#: post-sunset individual-AMT repeal anywhere, and the one published quantity
#: that fits (TPC T25-0049's revenue column, $948.9B) is the file the derived
#: path *reads*, so adopting it would manufacture a 0% row out of leakage.
#: Flipping this constant would therefore fail a release gate on a target no
#: document states, and loosening the gate to get green is what
#: ``MODELING_IMPROVEMENT.md`` §4 forbids. Still an owner call, now blocked on
#: a target that does not exist rather than one nobody had checked.
AMT_SCORECARD_MODE = AMT_MODE_REPORTED

#: Growth rate ``ScoringEngine`` applies to an ``AMTPolicy``'s annual static
#: effect (``scoring_engine._growth_tax_policy_handlers``). Derived mode
#: divides it back out year by year so the module's own path is what gets
#: scored; ``tests/test_amt_derived.py`` pins the two together.
AMT_ENGINE_GROWTH_RATE = 0.03


# =============================================================================
# CURRENT LAW PARAMETERS
# =============================================================================

# Individual AMT exemption and phase-out schedules are built from the
# transcribed statutory table (see the STATUTORY SCHEDULES section below);
# ``AMT_EXEMPTIONS_TCJA`` and ``AMT_EXEMPTIONS_TCJA_EXTENDED`` are assigned
# there, once the loader exists, and are documented at that point.

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


# =============================================================================
# STATUTORY SCHEDULES — EXEMPTION, PHASE-OUT THRESHOLD, CLAW-BACK RATE
# =============================================================================
# Lane L5 stopped here: "it needs a published phase-out path, which T25-0049
# does not carry." T25-0049 does not carry one and does not need to. The
# phase-out is **statutory**, not projected. IRC § 55(d)(2) (§ 55(d)(3) before
# 2018) reduces the exemption "by an amount equal to 25 percent of the amount by
# which the alternative minimum taxable income of the taxpayer exceeds" a
# threshold amount; § 1(f)(3) indexes the exemption and the threshold; and the
# IRS publishes both, for every filing status, in each year's inflation Revenue
# Procedure. P.L. 119-21 § 70107 reset the threshold and raised the claw-back
# rate to 50 percent. All of that is transcribed in
# ``data_files/amt/statutory_amt_parameters.csv``, with the rate confirmed
# arithmetically against the IRS's own printed "Complete Phaseout Amount".
#
# Under the post-sunset schedule this claw-back is what makes high-income filers
# AMT payers: a joint filer whose AMTI exceeds the threshold by four times the
# exemption has no exemption left at all.

STATUTORY_AMT_PARAMETERS_PATH = (
    Path(__file__).parent / "data_files" / "amt" / "statutory_amt_parameters.csv"
)

#: Pre-TCJA law — the schedule the TCJA sunset reverts to.
STATUTE_PRE_TCJA = "pre_tcja"

#: P.L. 115-97 § 12003, taxable years 2018-2025.
STATUTE_TCJA = "tcja"

#: P.L. 119-21 § 70107, taxable years from 2026: the TCJA exemption made
#: permanent, thresholds reset *down* to $500,000/$1,000,000, claw-back rate
#: raised from 25% to 50%.
STATUTE_PL119_21 = "pl119_21"

AMT_STATUTES = (STATUTE_PRE_TCJA, STATUTE_TCJA, STATUTE_PL119_21)

#: Last year of the TCJA exemption schedule under the sunset. From 2026 the
#: derived path's *current law* is pre-TCJA, because that is the counterfactual
#: TPC T25-0049 projects and the one both individual-AMT benchmarks describe.
#: It is deliberately **not** P.L. 119-21: pricing the module against enacted
#: post-2025 law would need a TPC vintage on a post-OBBBA baseline, which does
#: not exist, and inventing one is what ``MODELING_IMPROVEMENT.md`` §4 forbids.
#: ``STATUTE_PL119_21`` is expressible as a *reform* — see
#: :func:`create_pl119_21_amt` — just not as the baseline.
LAST_TCJA_STATUTE_YEAR = 2025

_FILING_STATUS_INDEX = {"single": 0, "mfj": 1, "mfs": 2}


@dataclass(frozen=True)
class AMTStatutoryYear:
    """One year of statutory AMT parameters, by filing status."""

    year: int
    statute: str
    exemption: tuple[float, float, float]  # (single, mfj, mfs)
    phase_out_threshold: tuple[float, float, float]  # (single, mfj, mfs)
    phase_out_rate: float
    source: str
    published: bool

    def exemption_for(self, filing_status: str = "mfj") -> float:
        return float(self.exemption[_FILING_STATUS_INDEX.get(filing_status, 1)])

    def threshold_for(self, filing_status: str = "mfj") -> float:
        return float(
            self.phase_out_threshold[_FILING_STATUS_INDEX.get(filing_status, 1)]
        )

    def complete_phase_out_for(self, filing_status: str = "mfj") -> float:
        """AMTI at which the exemption is fully clawed back, per § 55(d)(2)."""
        if self.phase_out_rate <= 0:
            return float("inf")
        return self.threshold_for(filing_status) + self.exemption_for(
            filing_status
        ) / self.phase_out_rate


@lru_cache(maxsize=1)
def load_statutory_amt_parameters() -> dict[str, dict[int, AMTStatutoryYear]]:
    """Load the transcribed Revenue Procedure rows, keyed by statute and year."""
    table: dict[str, dict[int, AMTStatutoryYear]] = {}
    with open(STATUTORY_AMT_PARAMETERS_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(line for line in handle if not line.startswith("#"))
        for record in reader:
            statute = record["regime"]
            year = int(record["year"])
            table.setdefault(statute, {})[year] = AMTStatutoryYear(
                year=year,
                statute=statute,
                exemption=(
                    float(record["exemption_single"]),
                    float(record["exemption_mfj"]),
                    float(record["exemption_mfs"]),
                ),
                phase_out_threshold=(
                    float(record["threshold_single"]),
                    float(record["threshold_mfj"]),
                    float(record["threshold_mfs"]),
                ),
                phase_out_rate=float(record["phaseout_rate"]),
                source=record["source"],
                published=True,
            )
    missing = [name for name in AMT_STATUTES if name not in table]
    if missing:
        raise ValueError(
            f"Statutory AMT table {STATUTORY_AMT_PARAMETERS_PATH} is missing "
            f"regime(s): {missing}"
        )
    return table


@cache
def statutory_indexation_rate() -> float:
    """
    The single § 1(f)(3) indexation rate the module applies to every schedule.

    It is the compound rate implied by the *published* TCJA MFJ phase-out
    threshold series over its own span ($1,000,000 in 2018 to $1,252,700 in
    2025), so it measures the realised chained-CPI path over exactly the years
    the module has documents for. It is applied identically to every statute and
    every filing status, and is fitted to nothing. The published exemption series
    over the same years implies the same rate to within 0.005pp, which
    ``tests/test_amt_phaseouts.py`` pins.

    Continuing a schedule at the rate its own two-row span implies — the rule
    ``_regime_growth`` uses for the TPC path — is *not* usable here: the
    pre-TCJA statute has published rows only for 2017 and 2018, whose 1.99% is
    one year of low inflation rather than the 2017-2026 path, and would
    under-index the sunset threshold by about 10%.
    """
    tcja = load_statutory_amt_parameters()[STATUTE_TCJA]
    first, last = min(tcja), max(tcja)
    span = last - first
    if span <= 0:
        raise ValueError("TCJA statutory series needs at least two published years")
    return (tcja[last].threshold_for("mfj") / tcja[first].threshold_for("mfj")) ** (
        1.0 / span
    ) - 1.0


def _index_to_hundred(amount: float, years: int) -> float:
    """Index one statutory amount, rounded to $100 as § 1(f)(7) requires."""
    grown = amount * (1.0 + statutory_indexation_rate()) ** years
    return float(round(grown / 100.0) * 100.0)


@lru_cache(maxsize=512)
def amt_statutory_year(statute: str, year: int) -> AMTStatutoryYear:
    """
    Statutory AMT parameters for ``statute`` in ``year``.

    A published Revenue Procedure row is returned as transcribed. Any other year
    is the nearest published row carried by :func:`statutory_indexation_rate`,
    which is what replaces the old tables that simply stopped — the phase-out
    table at 2030, the exemption tables at 2034, both clamping to their last row
    afterwards. Indexing off the *nearest* end rather than the last one matters
    for the reason the clamp it replaces already knew: a 2019 question must not
    be answered from 2025's row.
    """
    if statute not in AMT_STATUTES:
        raise ValueError(f"statute must be one of {AMT_STATUTES}, got {statute!r}")
    rows = load_statutory_amt_parameters()[statute]
    if year in rows:
        return rows[year]
    anchor = rows[max(rows)] if year > max(rows) else rows[min(rows)]
    span = year - anchor.year
    return AMTStatutoryYear(
        year=year,
        statute=statute,
        exemption=tuple(_index_to_hundred(v, span) for v in anchor.exemption),
        phase_out_threshold=tuple(
            _index_to_hundred(v, span) for v in anchor.phase_out_threshold
        ),
        phase_out_rate=anchor.phase_out_rate,
        source=f"{anchor.source}, indexed {span:+d}y at "
        f"{statutory_indexation_rate() * 100:.3f}%/yr",
        published=False,
    )


def current_law_amt_statute(year: int) -> str:
    """
    The statute the derived path treats as current law in ``year``.

    TCJA through 2025, pre-TCJA from 2026 — TPC T25-0049's own baseline, "the
    law in place for each year as of January 1, 2025". See
    :data:`LAST_TCJA_STATUTE_YEAR` for why this is not P.L. 119-21.
    """
    return STATUTE_TCJA if year <= LAST_TCJA_STATUTE_YEAR else STATUTE_PRE_TCJA


def _statute_schedule(
    statute_for_year, first: int = 2018, last: int = 2045
) -> dict[int, tuple[float, float, float]]:
    return {
        year: amt_statutory_year(statute_for_year(year), year).exemption
        for year in range(first, last + 1)
    }


#: Individual AMT exemptions under **current law** as the derived path defines
#: it — the TCJA schedule through 2025 and the pre-TCJA schedule after it.
#: Every row is now either a transcribed Revenue Procedure amount or that
#: amount indexed by the one statutory rule, replacing the hand-estimated
#: post-sunset rows the module used to carry (which put 2026 MFJ at $93,000
#: against the statutory reversion's $112,900).
AMT_EXEMPTIONS_TCJA = _statute_schedule(current_law_amt_statute)

#: Individual AMT exemptions if TCJA's larger amounts are extended. Identical to
#: current law through 2025 — before the sunset there is nothing to extend — and
#: the indexed TCJA schedule afterwards.
AMT_EXEMPTIONS_TCJA_EXTENDED = _statute_schedule(lambda _year: STATUTE_TCJA)

#: Phase-out thresholds ``(single, mfj, mfs)`` under current law. Replaces
#: ``AMT_PHASEOUT_TCJA``, which carried only two statuses, guessed its
#: post-sunset rows and stopped at 2030 — and which nothing read.
AMT_PHASEOUT_CURRENT_LAW = {
    year: amt_statutory_year(current_law_amt_statute(year), year).phase_out_threshold
    for year in range(2018, 2046)
}


# =============================================================================
# THE EXEMPTION-EQUIVALENT — FOLDING A PHASE-OUT INTO ONE SCALAR
# =============================================================================
# The derived path interpolates published aggregates on a single scalar, the MFJ
# exemption. A phase-out is a second and a third parameter (threshold, rate), so
# something has to reduce the triple to one number the interpolation can eat.
#
# The reduction used here is an **exemption-equivalent**: the flat exemption
# that, with no phase-out at all, would leave the same aggregate AMT base as the
# actual (exemption, threshold, rate) schedule does. It is exactly the exemption
# when the phase-out is out of reach, it rises with the exemption and with the
# threshold, and it falls as the claw-back rate rises — the four properties the
# interpolation needs, and each one is a test.
#
# The base is computed on the published IRS SOI Table 1.1 AGI distribution, so
# the only assumption is how filers sit *within* a published bracket, and that is
# pinned by the bracket's own published mean rather than chosen: each bracket
# gets the bounded-Pareto shape that reproduces its printed count and its printed
# mean AGI. The open top bracket gets the unbounded Pareto its own mean implies
# (alpha = 1.50 on 2023 data, which is the standard US top-tail figure).
#
# Two qualifications, stated rather than buried. SOI Table 1.1 pools filing
# statuses while the module's coordinate is MFJ-denominated; and AGI is not
# AMTI. Neither can bias a benchmark, because both regime anchors are computed
# through this same function and both individual-AMT benchmarks sit exactly on an
# anchor — they set only how steeply an *off-anchor* reform is priced.

#: SOI year the income grid is built from, and the rate it is aged at. The
#: growth rate is the module's existing engine constant rather than a new one.
SOI_GRID_YEAR = 2023
SOI_GRID_POINTS_PER_BRACKET = 200


@lru_cache(maxsize=1)
def _soi_income_grid() -> tuple[np.ndarray, np.ndarray]:
    """
    Representative ``(agi, weight)`` filers from IRS SOI Table 1.1.

    Within each published bracket the returns are laid out on a bounded Pareto
    whose shape is solved so the grid reproduces that bracket's own printed mean
    AGI; the count is the bracket's printed count. Nothing here is fitted to an
    AMT quantity. The negative/zero-AGI bracket is dropped: it has no AMT base.
    """
    from .data.irs_soi import IRSSOIData

    quantiles = (np.arange(SOI_GRID_POINTS_PER_BRACKET) + 0.5) / (
        SOI_GRID_POINTS_PER_BRACKET
    )
    incomes: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    for bracket in IRSSOIData().get_bracket_distribution(SOI_GRID_YEAR):
        floor = float(bracket.agi_floor)
        count = float(bracket.num_returns)
        if floor <= 0.0 or count <= 0.0:
            continue
        mean = bracket.total_agi * 1e9 / count
        ceiling = bracket.agi_ceiling
        if ceiling is None:
            # Unbounded Pareto: E[Y] = alpha * floor / (alpha - 1).
            alpha = mean / (mean - floor) if mean > floor else 2.0
            draws = floor * (1.0 - quantiles * 0.99999) ** (-1.0 / alpha)
        elif not floor < mean < ceiling:
            draws = np.full_like(quantiles, min(max(mean, floor), float(ceiling)))
        else:
            draws = _bounded_pareto_matching_mean(
                floor, float(ceiling), mean, quantiles
            )
        incomes.append(draws)
        weights.append(np.full_like(draws, count / SOI_GRID_POINTS_PER_BRACKET))
    return np.concatenate(incomes), np.concatenate(weights)


def _bounded_pareto_matching_mean(
    floor: float,
    ceiling: float,
    mean: float,
    quantiles: np.ndarray,
) -> np.ndarray:
    """Bounded-Pareto draws on ``[floor, ceiling]`` with the published mean."""
    low, high = 0.02, 60.0
    draws = np.full_like(quantiles, mean)
    for _ in range(80):
        alpha = 0.5 * (low + high)
        ratio = (floor / ceiling) ** alpha
        draws = floor / (1.0 - quantiles * (1.0 - ratio)) ** (1.0 / alpha)
        if draws.mean() > mean:
            low = alpha
        else:
            high = alpha
    return draws


def _aged_incomes(year: int) -> np.ndarray:
    incomes, _ = _soi_income_grid()
    return incomes * (1.0 + AMT_ENGINE_GROWTH_RATE) ** (year - SOI_GRID_YEAR)


def amt_clawback_per_filer(
    exemption: float,
    threshold: float,
    phase_out_rate: float,
    year: int,
) -> float:
    """
    Average statutory claw-back per return in ``year``, in dollars.

    ``min(exemption, rate x max(0, AMTI - threshold))`` — IRC § 55(d)(2) — over
    the published SOI distribution. Zero when the phase-out cannot bind, and the
    full exemption once every filer is past the complete-phase-out point.
    """
    if exemption == float("inf") or phase_out_rate <= 0.0:
        return 0.0
    _, weights = _soi_income_grid()
    incomes = _aged_incomes(year)
    clawback = np.minimum(
        exemption, phase_out_rate * np.maximum(0.0, incomes - threshold)
    )
    return float((weights * clawback).sum() / weights.sum())


def _aggregate_amt_base(exempt_amounts: np.ndarray, year: int) -> float:
    _, weights = _soi_income_grid()
    incomes = _aged_incomes(year)
    return float((weights * np.maximum(0.0, incomes - exempt_amounts)).sum())


@lru_cache(maxsize=4096)
def amt_exemption_equivalent(
    exemption: float,
    threshold: float,
    phase_out_rate: float,
    year: int,
) -> float:
    """
    The flat exemption that leaves the same aggregate AMT base as this schedule.

    Returns ``exemption`` exactly when the claw-back cannot bind, and otherwise
    something strictly below it. This is the scalar the published-path
    interpolation is indexed on once a phase-out exists.
    """
    if exemption == float("inf"):
        return float("inf")
    if exemption <= 0:
        raise ValueError(f"AMT exemption must be positive, got {exemption}")
    if phase_out_rate <= 0.0 or threshold == float("inf"):
        return float(exemption)

    incomes = _aged_incomes(year)
    clawback = np.minimum(
        exemption, phase_out_rate * np.maximum(0.0, incomes - threshold)
    )
    target = _aggregate_amt_base(exemption - clawback, year)

    low, high = 0.0, float(incomes.max())
    for _ in range(100):
        middle = 0.5 * (low + high)
        if _aggregate_amt_base(np.float64(middle), year) > target:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


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
    return amt_statutory_year(current_law_amt_statute(year), year).exemption_for("mfj")


def current_law_amt_effective_exemption_mfj(year: int) -> float:
    """
    Current law's MFJ exemption-equivalent — exemption *net of* the claw-back.

    The gap between this and :func:`current_law_amt_exemption_mfj` is the
    structure this lane adds. Post-sunset it is worth about 11% of the
    exemption, because the pre-TCJA threshold sits low in the income
    distribution; under TCJA's own thresholds it is worth under 2%.
    """
    statutory = amt_statutory_year(current_law_amt_statute(year), year)
    return amt_exemption_equivalent(
        statutory.exemption_for("mfj"),
        statutory.threshold_for("mfj"),
        statutory.phase_out_rate,
        year,
    )


def _amt_anchors(year: int) -> tuple[tuple[float, AMTYearRow], tuple[float, AMTYearRow]]:
    """
    The two published regimes as ``(MFJ exemption-equivalent, path row)`` anchors.

    Low = current law for that year (pre-TCJA from 2026); high = the TCJA
    schedule extended. Both anchors are the *same* row while TCJA is still in
    force, which collapses the interpolation to a single point, as it should.

    Each anchor's coordinate is now that anchor's **own** statutory triple —
    exemption, threshold and claw-back rate — put through
    :func:`amt_exemption_equivalent`. That is what keeps the phase-out from
    disturbing anything the module already scored: a benchmark whose policy leg
    *is* an anchor still lands on that anchor exactly, so it returns the
    published row it returned before.
    """
    low_statute = current_law_amt_statute(year)
    low_regime = (
        REGIME_TCJA if year <= _last_tcja_regime_year() else REGIME_POST_SUNSET
    )
    low = (
        current_law_amt_effective_exemption_mfj(year),
        amt_regime_year(low_regime, year),
    )
    tcja_statutory = amt_statutory_year(STATUTE_TCJA, year)
    high = (
        low[0]
        if low_statute == STATUTE_TCJA
        else amt_exemption_equivalent(
            tcja_statutory.exemption_for("mfj"),
            tcja_statutory.threshold_for("mfj"),
            tcja_statutory.phase_out_rate,
            year,
        ),
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

    # Phase-out changes (IRC § 55(d)(2)). Until Wave 4 lane 3c
    # ``phase_out_threshold_change`` was declared and never read, so a threshold
    # reform scored exactly 0.0 — the same class of dead branch L5 found in the
    # exemption leg. All three are live now.
    phase_out_threshold_change: float = 0.0  # Dollar change to the threshold
    new_phase_out_threshold_mfj: float | None = None  # Specific MFJ threshold
    new_phase_out_rate: float | None = None  # e.g. 0.50 under P.L. 119-21

    # Which statutory schedule the reform's phase-out is measured from. ``None``
    # follows the exemption: TCJA's thresholds when TCJA relief is extended,
    # current law's otherwise.
    statute: str | None = None

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

        return (
            self.statutory_year(year).exemption_for(filing_status)
            + self.exemption_change
        )

    def statute_for_year(self, year: int) -> str:
        """
        Which statutory schedule this policy's parameters are measured from.

        TCJA's when TCJA relief is extended past the sunset, current law's
        otherwise. Before the sunset there is nothing to extend, so the
        extension is a no-op and both legs read the same schedule; without that
        guard a 2025 start compared current law's $137,000 against the extended
        schedule and booked a revenue loss in a year the policy cannot touch.
        """
        if self.statute is not None:
            return self.statute
        if self.extend_tcja_relief and year > _last_tcja_regime_year():
            return STATUTE_TCJA
        return current_law_amt_statute(year)

    def statutory_year(self, year: int) -> AMTStatutoryYear:
        """The statutory parameter row this policy starts from in ``year``."""
        return amt_statutory_year(self.statute_for_year(year), year)

    def get_phase_out_threshold_for_year(
        self,
        year: int,
        filing_status: str = "mfj",
    ) -> float:
        """
        Effective § 55(d)(2) phase-out threshold in ``year``, after the reform.

        ``new_phase_out_threshold_mfj`` replaces the MFJ threshold outright and
        scales the other statuses by the statutory ratio; otherwise
        ``phase_out_threshold_change`` shifts every status by the same dollar
        amount. A threshold cannot go below zero — at zero the exemption is
        being clawed back from the first dollar of AMTI.
        """
        statutory = self.statutory_year(year)
        base = statutory.threshold_for(filing_status)
        if self.new_phase_out_threshold_mfj is not None:
            mfj = statutory.threshold_for("mfj")
            scale = self.new_phase_out_threshold_mfj / mfj if mfj else 1.0
            return max(0.0, base * scale)
        return max(0.0, base + self.phase_out_threshold_change)

    def get_phase_out_rate(self, year: int) -> float:
        """Effective claw-back rate: 25% by statute, 50% under P.L. 119-21."""
        if self.new_phase_out_rate is not None:
            return float(self.new_phase_out_rate)
        return self.statutory_year(year).phase_out_rate

    def get_effective_exemption_for_year(
        self,
        year: int,
        filing_status: str = "mfj",
    ) -> float:
        """
        The reform's exemption net of its own statutory claw-back.

        This — not the headline exemption — is what the derived path prices,
        because two schedules with the same exemption and different thresholds
        are not the same policy.
        """
        exemption = self.get_exemption_for_year(year, filing_status)
        if exemption == float("inf"):
            return exemption
        return amt_exemption_equivalent(
            exemption,
            self.get_phase_out_threshold_for_year(year, filing_status),
            self.get_phase_out_rate(year),
            year,
        )

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

        The count is evaluated **through the phase-out**: the exemption passed
        to the published-path interpolation is the reform's exemption net of its
        own statutory claw-back, so moving the threshold moves the affected
        population without touching the headline exemption at all.

        Args:
            year: Tax year.
            exemption: MFJ exemption-equivalent to evaluate. Defaults to the
                policy's own reform schedule. Pass
                ``current_law_amt_effective_exemption_mfj(year)`` to ask the
                counterfactual question — how many filers current law catches —
                which is the leg :meth:`estimate_static_revenue_effect` used to
                be missing.
        """
        if exemption is None:
            if self.repeal_individual_amt:
                return 0
            exemption = self.get_effective_exemption_for_year(year, "mfj")
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
        baseline = amt_revenue_billions(
            current_law_amt_effective_exemption_mfj(year), year
        )
        if self.repeal_individual_amt:
            return -baseline
        policy = amt_revenue_billions(
            self.get_effective_exemption_for_year(year, "mfj"), year
        )
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


def create_amt_phase_out_threshold_change(
    threshold_change: float,
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = AMT_MODE_DERIVED,
) -> AMTPolicy:
    """
    Move the § 55(d)(2) phase-out threshold, leaving the exemption alone.

    A *cut* to the threshold claws the exemption back from more filers and
    therefore **raises** revenue; an increase loses it. This is the reform the
    module could not express at all before Wave 4 lane 3c —
    ``phase_out_threshold_change`` was declared and never read, so every value
    of it scored 0.0.

    The default mode is ``derived`` because there is no fitted annual for this
    policy and there should not be one: the whole point is that the answer comes
    out of the statutory claw-back rather than out of a constant.
    """
    direction = "Raise" if threshold_change > 0 else "Cut"
    return AMTPolicy(
        name=f"AMT Phase-Out Threshold {direction} ${abs(threshold_change)/1000:.0f}K",
        description=(
            f"{direction} the AMT exemption phase-out threshold by "
            f"${abs(threshold_change):,.0f}"
        ),
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        phase_out_threshold_change=threshold_change,
        timing_elasticity=0.0,
        avoidance_elasticity=0.0,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_pl119_21_amt(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = AMT_MODE_DERIVED,
) -> AMTPolicy:
    """
    Enacted current law: P.L. 119-21 § 70107's AMT provision, as a reform.

    Three moves at once, and until this lane the module could express only the
    first: the TCJA exemption made permanent, the phase-out thresholds reset
    **down** to $500,000/$1,000,000, and the claw-back rate raised from 25% to
    50%. The last two are why JCT's line item for this provision
    (JCX-35-25, +$1,362.810B over FY2025-2034) is not the same quantity as a
    naive TCJA extension.

    **Not a benchmark, and deliberately not wired into one.** The repository's
    ``pl119_21_amt_exemption`` row is scored by ``tcja.py``; this factory exists
    so the mechanism can be *measured* against a published figure rather than
    only asserted. See ``planning/lanes/W4_amt_phaseouts.md`` §4.
    """
    return AMTPolicy(
        name="P.L. 119-21 AMT Provision",
        description=(
            "Make the TCJA AMT exemption permanent, reset the phase-out "
            "thresholds to $500K/$1M and raise the claw-back rate to 50%"
        ),
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        extend_tcja_relief=True,
        statute=STATUTE_PL119_21,
        timing_elasticity=0.0,
        avoidance_elasticity=0.0,
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
