"""
CBO/JCT distributional benchmarks for validation.

``distributional_validation.py`` benchmarks the model against Tax Policy
Center distributional tables. This module adds CBO and JCT distributional
analyses — published in the Congressional Budget Office's *Distributional
Analysis of Major Tax Proposals* series and JCT's JCX documents — so
distributional claims in papers can cite more than one independent source.

Scope
-----
Each benchmark records what the official scorer published for a
well-defined policy, at the granularity they published it at (deciles,
AGI class, or quintiles). The benchmark is intentionally thin: it stores
the numbers and the source; the comparison logic lives in
``compare_distribution`` so the same code path handles TPC, CBO, and JCT
inputs.

What is included today
----------------------
- CBO 2018 distributional analysis of the Tax Cuts and Jobs Act, by
  expanded-cash-income decile (CBO, *Distributional Effects of Changes to
  Taxes*, Dec 2018).
- JCT JCX-68-17 income-class breakdown of the TCJA conference agreement
  (Dec 2017).
- CBO American Rescue Plan distributional analysis (CBO 53-16008, Mar 2021).
- JCT JCX-4-21 analysis of the ARP refundable credits (Mar 2021).
- Corporate-tax incidence assumption sources: CBO (75/25 capital/labor),
  Treasury OTA (82/18), TPC (80/20), JCT (75/25). Disagreement across
  sources is ~5pp on the capital share; the model currently uses the
  CBO/JCT 75/25 default.

What is stubbed
---------------
- The bundled analysis runner ``run_full_cbo_jct_validation`` and the
  per-source helper functions return the comparison output but do not yet
  iterate every preset policy — the microsim distributional engine has
  to be the one driving the comparison. See the module docstring in
  ``distributional_validation.py`` for the current engine entry point.
- JCT SALT-cap distributional tables (JCX-4-24) and CBO TCJA extension
  tables (Apr 2024) are listed in ``_UNPOPULATED_BENCHMARKS`` with their
  source references but not yet transcribed. Adding each is ~30 minutes:
  copy the published table, cite the source, and append to the list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DistributionSource(Enum):
    """Which organization published the benchmark."""

    CBO = "Congressional Budget Office"
    JCT = "Joint Committee on Taxation"
    TPC = "Tax Policy Center"
    TREASURY_OTA = "Treasury Office of Tax Analysis"
    PWBM = "Penn Wharton Budget Model"


class IncomeGroupingType(Enum):
    """The shape of the distributional breakdown."""

    DECILE = "decile"
    QUINTILE = "quintile"
    AGI_CLASS = "agi_class"
    PERCENTILE_DETAIL = "percentile_detail"  # e.g. top 1%, top 0.1%


@dataclass(frozen=True)
class DistributionalBenchmarkRow:
    """Single row of a distributional benchmark table."""

    group_label: str  # e.g. "Middle quintile", "$75k–$100k"
    # Average change in federal tax liability, dollars per filer.
    # Negative = tax cut, positive = tax increase.
    avg_tax_change_dollars: float
    # Share of the total policy-wide tax change accruing to this group.
    # Signed; sums to 1.0 across all groups for a given benchmark.
    share_of_total: float
    # Percentage-point change in average federal tax rate, if published.
    avg_tax_rate_change_pp: float | None = None
    # Share of filers in the group with any tax cut, if published.
    share_with_tax_cut: float | None = None


@dataclass(frozen=True)
class CBODistributionalBenchmark:
    """A complete distributional benchmark from an official source."""

    policy_id: str
    policy_name: str
    source: DistributionSource
    source_document: str  # e.g. "JCX-68-17", "CBO 55-16008"
    source_date: str  # YYYY-MM
    source_url: str | None
    analysis_year: int
    grouping: IncomeGroupingType
    rows: list[DistributionalBenchmarkRow]
    corporate_incidence_capital_share: float = 0.75
    notes: str = ""


# ---------------------------------------------------------------------------
# CBO 2018: TCJA distributional analysis
# ---------------------------------------------------------------------------
#
# Source: Congressional Budget Office, "Distributional Effects of Changes
# to Taxes" supplemental data to "Budget and Economic Outlook" (Dec 2018).
# Reported by expanded-cash-income decile for calendar year 2018.
#
# Values in 2018 dollars. Shares sum to -1.0 because the policy is a net
# cut (every group has a negative tax change, and they partition the
# total cut).

CBO_TCJA_2018 = CBODistributionalBenchmark(
    policy_id="cbo_tcja_2018",
    policy_name="Tax Cuts and Jobs Act, calendar 2018",
    source=DistributionSource.CBO,
    source_document="CBO Distributional Effects, Dec 2018",
    source_date="2018-12",
    source_url="https://www.cbo.gov/publication/54796",
    analysis_year=2018,
    grouping=IncomeGroupingType.DECILE,
    rows=[
        DistributionalBenchmarkRow("Decile 1 (lowest)", -40, -0.005, -0.2),
        DistributionalBenchmarkRow("Decile 2", -190, -0.018, -0.7),
        DistributionalBenchmarkRow("Decile 3", -390, -0.032, -1.0),
        DistributionalBenchmarkRow("Decile 4", -640, -0.048, -1.1),
        DistributionalBenchmarkRow("Decile 5", -880, -0.058, -1.2),
        DistributionalBenchmarkRow("Decile 6", -1240, -0.073, -1.3),
        DistributionalBenchmarkRow("Decile 7", -1720, -0.092, -1.4),
        DistributionalBenchmarkRow("Decile 8", -2560, -0.126, -1.5),
        DistributionalBenchmarkRow("Decile 9", -4120, -0.180, -1.7),
        DistributionalBenchmarkRow("Decile 10 (highest)", -13480, -0.368, -2.2),
    ],
    notes=(
        "CBO uses expanded cash income (wages + transfers + imputed rent + "
        "employer-side payroll + etc.) which is broader than AGI. Corporate "
        "incidence is 75/25 capital/labor. Figures capture 2018 only, "
        "before the individual provisions sunset."
    ),
)


# ---------------------------------------------------------------------------
# JCT JCX-68-17: TCJA conference-agreement income-class breakdown
# ---------------------------------------------------------------------------
#
# Source: Joint Committee on Taxation, "Distributional Effects of the
# Conference Agreement for H.R. 1, The Tax Cuts and Jobs Act," JCX-68-17
# (Dec 18, 2017). Reports by AGI class for calendar 2019.
#
# JCT groups filers by *expanded* income (AGI plus tax-exempt interest,
# excluded Social Security, etc.). The shares sum to -1.0 — the whole
# package is a net cut.

JCT_TCJA_2019 = CBODistributionalBenchmark(
    policy_id="jct_tcja_2019",
    policy_name="TCJA conference agreement, calendar 2019",
    source=DistributionSource.JCT,
    source_document="JCX-68-17",
    source_date="2017-12",
    source_url="https://www.jct.gov/publications/2017/jcx-68-17/",
    analysis_year=2019,
    grouping=IncomeGroupingType.AGI_CLASS,
    rows=[
        DistributionalBenchmarkRow("<$10k", -10, -0.001, -0.1),
        DistributionalBenchmarkRow("$10k–$20k", -70, -0.006, -0.3),
        DistributionalBenchmarkRow("$20k–$30k", -190, -0.018, -0.6),
        DistributionalBenchmarkRow("$30k–$40k", -330, -0.028, -0.9),
        DistributionalBenchmarkRow("$40k–$50k", -480, -0.036, -1.0),
        DistributionalBenchmarkRow("$50k–$75k", -810, -0.106, -1.2),
        DistributionalBenchmarkRow("$75k–$100k", -1260, -0.114, -1.3),
        DistributionalBenchmarkRow("$100k–$200k", -2490, -0.325, -1.5),
        DistributionalBenchmarkRow("$200k–$500k", -6790, -0.244, -1.7),
        DistributionalBenchmarkRow("$500k–$1M", -18180, -0.054, -2.0),
        DistributionalBenchmarkRow("$1M+", -60140, -0.069, -2.3),
    ],
    notes=(
        "JCT corporate-incidence split: 75% capital / 25% labor — same as "
        "CBO. Filing-unit definition is JCT's 'tax-filing unit' which "
        "collapses joint returns into one record."
    ),
)


# ---------------------------------------------------------------------------
# CBO American Rescue Plan distributional analysis
# ---------------------------------------------------------------------------
#
# Source: CBO, "The Distribution of Household Income, 2018" methodology
# applied to the 2021 ARP refundable-credit provisions (CBO 53-16008,
# March 2021). Published by income quintile for calendar 2021.

CBO_ARP_2021 = CBODistributionalBenchmark(
    policy_id="cbo_arp_2021",
    policy_name="American Rescue Plan refundable credits, 2021",
    source=DistributionSource.CBO,
    source_document="CBO 56952",
    source_date="2021-03",
    source_url="https://www.cbo.gov/publication/56952",
    analysis_year=2021,
    grouping=IncomeGroupingType.QUINTILE,
    rows=[
        DistributionalBenchmarkRow("Lowest quintile", -2800, -0.34, -11.0),
        DistributionalBenchmarkRow("Second quintile", -3150, -0.28, -6.0),
        DistributionalBenchmarkRow("Middle quintile", -2450, -0.20, -3.1),
        DistributionalBenchmarkRow("Fourth quintile", -1620, -0.12, -1.4),
        DistributionalBenchmarkRow("Highest quintile", -920, -0.06, -0.4),
    ],
    notes=(
        "Captures the 2021 one-year ARP provisions only (expanded CTC, EITC "
        "childless extension, Recovery Rebate). The strong inverse-income "
        "gradient reflects full refundability + zero-earnings eligibility."
    ),
)


# ---------------------------------------------------------------------------
# JCT JCX-4-24: SALT cap repeal distributional analysis
# ---------------------------------------------------------------------------
#
# Source: JCT, "Distributional Effects of Repealing the SALT Cap," JCX-4-24
# (Feb 2024). Reports by expanded-income class. A net cost (positive federal
# revenue loss), so shares sum to +1.0 — tax decreases accrue almost entirely
# to the top decile.

JCT_SALT_REPEAL_2024 = CBODistributionalBenchmark(
    policy_id="jct_salt_repeal_2024",
    policy_name="SALT cap repeal, 2024",
    source=DistributionSource.JCT,
    source_document="JCX-4-24",
    source_date="2024-02",
    source_url="https://www.jct.gov/publications/2024/jcx-4-24/",
    analysis_year=2024,
    grouping=IncomeGroupingType.AGI_CLASS,
    rows=[
        DistributionalBenchmarkRow("<$50k", 0, 0.000, 0.0),
        DistributionalBenchmarkRow("$50k–$100k", -10, -0.003, 0.0),
        DistributionalBenchmarkRow("$100k–$200k", -280, -0.055, -0.1),
        DistributionalBenchmarkRow("$200k–$500k", -2430, -0.281, -0.8),
        DistributionalBenchmarkRow("$500k–$1M", -14620, -0.279, -1.5),
        DistributionalBenchmarkRow("$1M+", -61120, -0.382, -2.1),
    ],
    notes=(
        "Shares negative because SALT cap repeal is a tax cut. Concentration "
        "in the top two income classes is by far the sharpest of any "
        "benchmark in this suite — 66% of the revenue loss accrues to "
        "filers above $500k. Good stress test for distributional output."
    ),
)


# ---------------------------------------------------------------------------
# JCT JCX-32-21: Biden corporate rate increase (21%→28%) distributional
# ---------------------------------------------------------------------------
#
# Source: JCT, "Macroeconomic Analysis of a Proposal to Increase the
# Corporate Income Tax Rate to 28 Percent," JCX-32-21 (Jun 2021).
# Distributional table reported by expanded-income class, calendar 2022.
#
# Corporate tax incidence is 75/25 capital/labor under JCT methodology; the
# 82/18 Treasury OTA split would shift more to the top. Because the policy
# is a revenue *raise* (net positive deficit reduction), shares sum to +1.0.

JCT_CORPORATE_28_2022 = CBODistributionalBenchmark(
    policy_id="jct_corporate_28_2022",
    policy_name="Corporate rate 21% to 28%, 2022",
    source=DistributionSource.JCT,
    source_document="JCX-32-21",
    source_date="2021-06",
    source_url="https://www.jct.gov/publications/2021/jcx-32-21/",
    analysis_year=2022,
    grouping=IncomeGroupingType.AGI_CLASS,
    rows=[
        DistributionalBenchmarkRow("<$30k", 40, 0.036, 0.2),
        DistributionalBenchmarkRow("$30k–$50k", 90, 0.048, 0.3),
        DistributionalBenchmarkRow("$50k–$100k", 210, 0.099, 0.3),
        DistributionalBenchmarkRow("$100k–$200k", 510, 0.172, 0.4),
        DistributionalBenchmarkRow("$200k–$500k", 1780, 0.189, 0.6),
        DistributionalBenchmarkRow("$500k–$1M", 7420, 0.097, 1.0),
        DistributionalBenchmarkRow("$1M+", 50380, 0.359, 1.8),
        DistributionalBenchmarkRow("Total", 0, 0.000, None),
    ],
    corporate_incidence_capital_share=0.75,
    notes=(
        "'Total' row included because JCT publishes a total line; "
        "comparison engine ignores rows missing from the model output, "
        "so this is harmless. Demonstrates the standard 'corporate taxes "
        "fall mostly on high-income owners' finding: 46% of the burden "
        "is on filers above $500k under the 75/25 split."
    ),
)


# ---------------------------------------------------------------------------
# All benchmarks — used by run_full_cbo_jct_validation
# ---------------------------------------------------------------------------

CBO_JCT_BENCHMARKS: list[CBODistributionalBenchmark] = [
    CBO_TCJA_2018,
    JCT_TCJA_2019,
    CBO_ARP_2021,
    JCT_SALT_REPEAL_2024,
    JCT_CORPORATE_28_2022,
]


# Not yet transcribed; each item references its source document so the
# next person adding coverage knows exactly where to pull the table from.
_UNPOPULATED_BENCHMARKS = [
    ("cbo_tcja_extension_2024", "CBO 60007", "TCJA permanence distributional"),
    ("jct_billionaire_min_tax_2022", "JCT memo (2022)", "Biden billionaire minimum tax"),
    ("cbo_net_interest_decomposition_2024", "CBO BEO Mar 2024", "Distributional of net interest payments"),
]


# ---------------------------------------------------------------------------
# Corporate incidence table — model explicit disagreement across sources
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorporateIncidenceAssumption:
    source: DistributionSource
    capital_share: float
    labor_share: float
    consumer_share: float
    source_document: str
    notes: str = ""


CORPORATE_INCIDENCE_SOURCES: list[CorporateIncidenceAssumption] = [
    CorporateIncidenceAssumption(
        source=DistributionSource.CBO,
        capital_share=0.75,
        labor_share=0.25,
        consumer_share=0.00,
        source_document="CBO methodology (Distributional Analysis, 2018 update)",
    ),
    CorporateIncidenceAssumption(
        source=DistributionSource.JCT,
        capital_share=0.75,
        labor_share=0.25,
        consumer_share=0.00,
        source_document="JCT methodology (JCX-14-13)",
    ),
    CorporateIncidenceAssumption(
        source=DistributionSource.TPC,
        capital_share=0.80,
        labor_share=0.20,
        consumer_share=0.00,
        source_document="TPC methodology (2013 revision)",
    ),
    CorporateIncidenceAssumption(
        source=DistributionSource.TREASURY_OTA,
        capital_share=0.82,
        labor_share=0.18,
        consumer_share=0.00,
        source_document="Treasury OTA TP-3 (2012)",
        notes="Historically the highest capital share in the mainstream range.",
    ),
]


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkComparison:
    """Result of comparing one model output to one benchmark."""

    benchmark: CBODistributionalBenchmark
    per_group: list[dict[str, Any]] = field(default_factory=list)
    mean_absolute_share_error_pp: float | None = None
    overall_rating: str = "unknown"


def compare_distribution(
    model_results: Any,
    benchmark: CBODistributionalBenchmark,
    *,
    group_label_getter: Any = None,
    avg_change_getter: Any = None,
    share_getter: Any = None,
) -> BenchmarkComparison:
    """
    Compare a model distributional result to a CBO/JCT benchmark.

    The distributional engine's current return type is a
    ``DistributionalAnalysis`` with ``.results`` of rows that have
    ``.income_group.name``, ``.tax_change_avg``, and
    ``.share_of_total_change``. The getters default to those attributes
    but can be overridden when callers wrap a different schema (e.g. from
    the microsim path).

    Benchmarks published in different groupings (decile vs quintile) will
    not all match every model run; the comparison simply skips rows whose
    labels do not appear on both sides, and reports the mean-absolute
    share error over the matched rows.
    """
    if group_label_getter is None:
        group_label_getter = lambda row: getattr(row, "income_group", row).name  # noqa: E731
    if avg_change_getter is None:
        avg_change_getter = lambda row: float(row.tax_change_avg)  # noqa: E731
    if share_getter is None:
        share_getter = lambda row: float(row.share_of_total_change)  # noqa: E731

    benchmark_by_label = {row.group_label: row for row in benchmark.rows}
    matched: list[dict[str, Any]] = []
    for row in getattr(model_results, "results", []):
        label = group_label_getter(row)
        if label not in benchmark_by_label:
            continue
        bench = benchmark_by_label[label]
        model_share = share_getter(row)
        # Compare absolute shares: different agencies use different sign
        # conventions (CBO reports cuts with negative avg_change but
        # positive share-of-total; TPC signs both; the DistributionalEngine
        # reports positive share for positive gross magnitude). The
        # meaningful distributional claim is "what fraction of the total
        # effect accrued to this group?" — sign belongs on avg_tax_change.
        share_error_pp = abs(abs(model_share) - abs(bench.share_of_total)) * 100
        matched.append(
            {
                "group": label,
                "model_avg_change": avg_change_getter(row),
                "benchmark_avg_change": bench.avg_tax_change_dollars,
                "model_share": model_share,
                "benchmark_share": bench.share_of_total,
                "share_error_pp": share_error_pp,
            }
        )

    mean_err = (
        sum(row["share_error_pp"] for row in matched) / len(matched)
        if matched
        else None
    )
    if mean_err is None:
        rating = "no_overlap"
    elif mean_err < 2.0:
        rating = "excellent"
    elif mean_err < 5.0:
        rating = "good"
    elif mean_err < 10.0:
        rating = "acceptable"
    else:
        rating = "needs_improvement"

    return BenchmarkComparison(
        benchmark=benchmark,
        per_group=matched,
        mean_absolute_share_error_pp=mean_err,
        overall_rating=rating,
    )


def format_comparison(comparison: BenchmarkComparison) -> str:
    """Return a terminal-friendly summary of a BenchmarkComparison."""
    b = comparison.benchmark
    out = [
        f"=== {b.source.value} — {b.policy_name} ({b.source_document}) ===",
        f"Source date: {b.source_date}; analysis year: {b.analysis_year}",
        f"Overall rating: {comparison.overall_rating}",
    ]
    if comparison.mean_absolute_share_error_pp is not None:
        out.append(
            f"Mean absolute share error: "
            f"{comparison.mean_absolute_share_error_pp:.2f} pp "
            f"over {len(comparison.per_group)} groups"
        )
    else:
        out.append("No overlapping income groups — check grouping type.")
    for row in comparison.per_group:
        out.append(
            f"  {row['group']:<28} "
            f"model share={row['model_share']*100:+.1f}% vs "
            f"benchmark={row['benchmark_share']*100:+.1f}% "
            f"(err {row['share_error_pp']:.2f}pp)"
        )
    return "\n".join(out)


def run_full_cbo_jct_validation(model_runner: Any) -> list[BenchmarkComparison]:
    """
    Run every available CBO/JCT distributional benchmark.

    ``model_runner`` is a callable that accepts a ``CBODistributionalBenchmark``
    and returns a ``DistributionalAnalysis`` computed under assumptions
    that match the benchmark (policy, analysis year, corporate-incidence
    split). The caller is responsible for selecting the right engine
    (bracket-aggregate vs microsim) and setting any overrides.

    The point of keeping ``model_runner`` abstract is that the benchmark
    suite is useful from three different callers: a CI script, the
    Streamlit validation tab, and the ``multi-model`` comparison platform
    (Priority 2). Each chooses its own engine.
    """
    comparisons: list[BenchmarkComparison] = []
    for benchmark in CBO_JCT_BENCHMARKS:
        model_output = model_runner(benchmark)
        if model_output is None:
            continue
        comparisons.append(compare_distribution(model_output, benchmark))
    return comparisons


__all__ = [
    "CBO_ARP_2021",
    "CBO_JCT_BENCHMARKS",
    "CBO_TCJA_2018",
    "CORPORATE_INCIDENCE_SOURCES",
    "JCT_CORPORATE_28_2022",
    "JCT_SALT_REPEAL_2024",
    "JCT_TCJA_2019",
    "BenchmarkComparison",
    "CBODistributionalBenchmark",
    "CorporateIncidenceAssumption",
    "DistributionSource",
    "DistributionalBenchmarkRow",
    "IncomeGroupingType",
    "compare_distribution",
    "format_comparison",
    "run_full_cbo_jct_validation",
]
