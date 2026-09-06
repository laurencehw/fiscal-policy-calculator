#!/usr/bin/env python3
"""
Reconcile the published per-point revenue yields of a corporate rate change.

Reads ``fiscal_model/data_files/validation/corporate_rate_scores.csv`` and
prints the three tables behind ``planning/memos/CORPORATE_PER_POINT_YIELD.md``.
Nothing here scores a policy or touches a target; it is arithmetic on published
figures, kept in a script so the memo's numbers can be re-derived rather than
believed.

The quantity everything turns on is the **implied marginal base**::

    B_marginal = published_10yr_total / rate_change_decimal / window_years

A published score divided by the rate step is the base that step reached, in
dollars per year. It is invariant to the statutory rate level, which per-point
dollars are not: a point off 35% is 1/35 of the base and a point off 21% is
1/21, so per-point yields from the pre- and post-TCJA eras are not comparable
and implied marginal bases are.

Against it sits the **average credit-realized base**, read off each vintage's
own published corporate receipts::

    B_average = baseline_corporate_receipts / statutory_rate

That is the base which, taxed at the statutory rate, reproduces the receipts
the baseline projects - so it already nets credits, NOLs, shifting and every
other reason receipts fall short of profits times the rate. Their ratio,

    marginal_share = B_marginal / B_average

is the share of the average base a statutory point actually reaches, and it is
the one number on which the estimators visibly and stably disagree.

Usage
-----
    python scripts/corporate_yield_reconciliation.py
    python scripts/corporate_yield_reconciliation.py --json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORES_CSV = (
    PROJECT_ROOT
    / "fiscal_model"
    / "data_files"
    / "validation"
    / "corporate_rate_scores.csv"
)

# ---------------------------------------------------------------------------
# Baseline corporate receipts, by vintage
# ---------------------------------------------------------------------------
# Every figure below is CBO's own projected *corporate income tax receipts*,
# fiscal years, in billions, read from that vintage's recurring supplemental
# budget-projections workbook (``51118-<yyyy>-<mm>-budgetprojections.xlsx``).
# cbo.gov returns HTTP 403 to this environment, so the workbooks were fetched
# through Wayback mirrors of cbo.gov's own files; they are the primary
# documents, delivered by a mirror.
#
# ``receipts_10yr`` is the total over ``window``; where the workbook prints its
# own ten-year total column that column is used, otherwise the annual row is
# summed. ``annual`` carries the year-by-year path where it was transcribed.
#
# ``statutory_rate`` is the top statutory corporate rate in force over the
# window on that vintage's own current law - 35% before the TCJA, 21% after.
BASELINES: dict[str, dict] = {
    "cbo_mar_2016": {
        "document": "CBO, Updated Budget Projections: 2016 to 2026 (March 2016), pub. 51384, Table 1",
        "window": "FY2017-2026",
        "start_year": 2017,
        "statutory_rate": 0.35,
        "receipts_10yr": 3987.7,
        "annual": [356.9, 365.9, 372.4, 399.7, 395.5, 401.2, 407.3, 416.7, 428.6, 443.6],
        "note": (
            "Pre-TCJA, and richer than the June 2017 vintage on the overlapping "
            "years: CBO projected FY2017 at $356.9B in March 2016, $310.0B in "
            "June 2017, against an actual of $297.0B. It was revising corporate "
            "receipts down materially before the TCJA."
        ),
    },
    "cbo_jun_2017": {
        "document": "CBO, An Update to the Budget and Economic Outlook: 2017 to 2027 (June 2017), pub. 52801, Table 1",
        "window": "FY2018-2027",
        "start_year": 2018,
        "statutory_rate": 0.35,
        "receipts_10yr": 3907.2,
        "annual": [324.3, 343.9, 380.4, 382.7, 389.5, 395.1, 405.1, 415.6, 428.0, 442.7],
        "note": "Pre-TCJA. The baseline JCX-67-17's rate line was priced against.",
    },
    "cbo_apr_2018": {
        "document": "CBO, The Budget and Economic Outlook: 2018 to 2028 (April 2018), pub. 53651, Table 4-1",
        "window": "FY2019-2028",
        "start_year": 2019,
        "statutory_rate": 0.21,
        "receipts_10yr": 3846.6,
        "annual": [276.3, 307.4, 326.7, 352.8, 388.1, 420.6, 446.5, 449.0, 431.4, 447.8],
        "note": "First post-TCJA vintage; the revenue baseline for CBO's Dec 2018 Options volume.",
    },
    "cbo_sep_2020": {
        "document": "CBO, An Update to the Budget Outlook: 2020 to 2030 (September 2020), pub. 56517, Table 1",
        "window": "FY2021-2030",
        "start_year": 2021,
        "statutory_rate": 0.21,
        "receipts_10yr": 3152.4,
        "annual": [122.8, 234.1, 289.3, 318.9, 347.3, 352.3, 355.6, 368.1, 377.6, 386.6],
        "note": (
            "A COVID outlier: FY2021 was projected at $122.8B against an actual "
            "of $371.8B. Its denominator is far too small, so any marginal share "
            "computed against it is far too large. Read it as an outlier, not a "
            "measurement."
        ),
    },
    "cbo_jul_2021": {
        "document": "CBO, An Update to the Budget and Economic Outlook: 2021 to 2031 (July 2021), pub. 57218, Table 1",
        "window": "FY2022-2031",
        "start_year": 2022,
        "statutory_rate": 0.21,
        "receipts_10yr": 3856.5,
        "annual": None,
        "note": (
            "A PROXY. The FY2022 Green Book states no baseline at all and "
            "Treasury does not publish one; this is the nearest CBO vintage on "
            "the same window, used so that Treasury's rows can be normalised at "
            "all. Any Treasury marginal share below inherits that substitution."
        ),
    },
    "cbo_may_2022": {
        "document": "CBO, The Budget and Economic Outlook: 2022 to 2032 (May 2022), pub. 57950, Table 1-1",
        "window": "FY2023-2032",
        "start_year": 2023,
        "statutory_rate": 0.21,
        "receipts_10yr": 4754.9,
        "annual": [456.1, 478.0, 483.2, 473.0, 456.9, 461.0, 470.4, 480.1, 491.0, 505.2],
        "note": "Revenue baseline for CBO's Dec 2022 Options volume; proxy baseline for the FY2023 Green Book.",
    },
    "cbo_feb_2023": {
        "document": "CBO, The Budget and Economic Outlook: 2023 to 2033 (February 2023), pub. 58848",
        "window": "FY2024-2033",
        "start_year": 2024,
        "statutory_rate": 0.21,
        "receipts_10yr": 5089.4,
        "annual": None,
        "note": "Proxy baseline for the FY2024 Green Book.",
    },
    "cbo_feb_2024": {
        "document": "CBO, The Budget and Economic Outlook: 2024 to 2034 (February 2024), pub. 59710, Table 1-1",
        "window": "FY2025-2034",
        "start_year": 2025,
        "statutory_rate": 0.21,
        "receipts_10yr": 5094.0,
        "annual": [494.1, 491.4, 484.1, 490.7, 500.9, 510.6, 518.7, 519.2, 533.4, 550.8],
        "note": (
            "The revenue baseline CBO's December 2024 Options volume names for "
            "its revenue options, and the repository's BaselineVintage.CBO_FEB_2024. "
            "Proxy baseline for the FY2025 Green Book."
        ),
    },
    "cbo_jan_2025": {
        "document": "CBO, The Budget and Economic Outlook: 2025 to 2035 (January 2025), pub. 60870",
        "window": "FY2026-2035",
        "start_year": 2026,
        "statutory_rate": 0.21,
        "receipts_10yr": 4766.7,
        "annual": None,
        "note": (
            "Proxy baseline for CRFB's per-point row. The repository's "
            "BaselineVintage.CBO_JAN_2025 cites pub. 61172; the workbook itself "
            "says 60870, which is the data release behind that report."
        ),
    },
    "cbo_feb_2026": {
        "document": "CBO, The Budget and Economic Outlook: 2027 to 2036 (February 2026), pub. 61882",
        "window": "FY2027-2036",
        "start_year": 2027,
        "statutory_rate": 0.21,
        "receipts_10yr": 4976.7,
        "annual": None,
        "note": (
            "Proxy baseline for Tax Foundation's Options 3.0, which runs on its "
            "own post-OBBBA projection rather than CBO's. A weak proxy: the two "
            "baselines are not the same law and not the same forecaster."
        ),
    },
}

#: Which baseline each published score is normalised against. Where the source
#: names its own baseline this is that baseline; where it does not - every
#: Treasury Green Book - it is the nearest CBO vintage on the same window, and
#: the row is flagged ``proxy``.
SCORE_BASELINE = {
    "JCX-67-17": ("cbo_jun_2017", "named"),
    "JCX-42-21": ("cbo_jul_2021", "proxy"),
    "Options 2024 Option 64": ("cbo_feb_2024", "named"),
    "Options 2022 Option 50": ("cbo_may_2022", "named"),
    "Options 2020 Option 19": ("cbo_sep_2020", "named"),
    "Options 2018 Option 24": ("cbo_apr_2018", "named"),
    "Budget Options 2016 Option 25": ("cbo_mar_2016", "named"),
    "Green Book FY2022": ("cbo_jul_2021", "proxy"),
    "Green Book FY2023": ("cbo_may_2022", "proxy"),
    "Green Book FY2024": ("cbo_feb_2023", "proxy"),
    "Green Book FY2025": ("cbo_feb_2024", "proxy"),
    "TPC 2020": ("cbo_sep_2020", "proxy"),
    "Tax Foundation 2021": ("cbo_jul_2021", "proxy"),
    "PWBM AJP 2021": ("cbo_jul_2021", "proxy"),
    "PWBM FY2025 Budget": ("cbo_feb_2024", "proxy"),
    "Tax Foundation 2024": ("cbo_feb_2024", "proxy"),
    "CRFB Offsets Bank": ("cbo_jan_2025", "proxy"),
    "Tax Foundation Options 3.0": ("cbo_feb_2026", "proxy"),
}

#: Short label per CSV row, keyed on a distinctive fragment of ``document``.
LABELS = (
    ("JCX-67-17", "JCX-67-17"),
    ("JCX-42-21", "JCX-42-21"),
    ("Option 64", "Options 2024 Option 64"),
    ("Option 50", "Options 2022 Option 50"),
    ("Option 19", "Options 2020 Option 19"),
    ("Option 24", "Options 2018 Option 24"),
    ("Option 25", "Budget Options 2016 Option 25"),
    ("FY2022 Revenue Proposals", "Green Book FY2022"),
    ("FY2023 Revenue Proposals", "Green Book FY2023"),
    ("FY2024 Revenue Proposals", "Green Book FY2024"),
    ("FY2025 Revenue Proposals", "Green Book FY2025"),
    ("Mermin", "TPC 2020"),
    ("Evaluating Proposals", "Tax Foundation 2021"),
    ("American Jobs Plan", "PWBM AJP 2021"),
    ("FY2025 Budget Proposal", "PWBM FY2025 Budget"),
    ("Biden Budget Tax Proposals", "Tax Foundation 2024"),
    ("Budget Offsets Bank", "CRFB Offsets Bank"),
    ("Tax Code 3.0", "Tax Foundation Options 3.0"),
)

# ---------------------------------------------------------------------------
# The model, on the same metric
# ---------------------------------------------------------------------------
#: What ``fiscal_model/corporate.py`` scores today, FY2025-2034, from
#: ``scripts/cold_holdout.py`` and ``validate_all_corporate``. ``reported`` is
#: exactly linear in the base; ``derived`` is mildly concave in the step.
#:
#: The ``derived`` rows moved in lane W6
#: (``planning/lanes/W6_corporate_base_projection.md``), which built §5's
#: counterfactual: the base is now projected off CBO's own corporate receipts
#: path instead of aged at a flat 4%/yr. The pre-W6 figures are kept below,
#: labelled, because §4's table and most of this memo's prose were written
#: against them.
MODEL_ROWS = (
    ("model reported +1pp", 1.0, -199.60, "rate_only"),
    ("model reported +7pp", 7.0, -1397.21, "rate_only"),
    ("model derived +1pp", 1.0, -196.08, "rate_only"),
    ("model derived +7pp", 7.0, -1292.62, "rate_only"),
    ("model derived +1pp (pre-W6)", 1.0, -220.28, "rate_only"),
    ("model derived +7pp (pre-W6)", 7.0, -1452.14, "rate_only"),
)

#: The derived path's own annual path at +1pp, FY2025-2034 ($B, deficit sign),
#: for the year-by-year marginal-share check.
MODEL_DERIVED_1PP_ANNUAL = [
    -14.66, -19.47, -19.23, -19.35, -19.72, -20.11, -20.44, -20.54, -20.96, -21.62
]

#: The same path before W6, when the base was aged at a flat 4%/yr. Kept so the
#: year-by-year table can print the drift the lane removed rather than assert it.
MODEL_DERIVED_1PP_ANNUAL_PRE_W6 = [
    -14.18, -19.47, -20.25, -21.06, -21.91, -22.78, -23.69, -24.64, -25.63, -26.65
]

#: CBO Option 64's own annual path, and the FY2025 Green Book's, both $B and
#: both transcribed in the CSV's ``notes``. Repeated here as floats so the
#: year-by-year table can be printed without re-parsing prose.
OPT64_ANNUAL = [7.5, 12.7, 13.6, 13.7, 14.1, 14.4, 14.5, 14.6, 14.9, 15.7]
GB2025_ANNUAL = [
    122.474, 125.105, 128.114, 128.624, 128.353,
    129.396, 137.888, 144.919, 150.028, 155.040,
]


def load_scores() -> list[dict]:
    """Read the CSV, stripping the ``#`` provenance header."""
    with SCORES_CSV.open(encoding="utf-8") as handle:
        body = (line for line in handle if not line.startswith("#"))
        rows = list(csv.DictReader(body))
    for row in rows:
        row["label"] = next(
            (label for frag, label in LABELS if frag in row["document"]),
            row["document"][:40],
        )
        for key in ("rate_change_pp", "ten_year_billions", "per_point_billions"):
            row[key] = float(row[key])
    return rows


def enrich(rows: list[dict]) -> list[dict]:
    """Attach the implied marginal base, the average base and their ratio."""
    for row in rows:
        step = abs(row["rate_change_pp"]) / 100.0
        row["per_point_check"] = row["ten_year_billions"] / row["rate_change_pp"]
        # |total| / step / 10 years -> dollars of base per year
        row["marginal_base"] = abs(row["ten_year_billions"]) / step / 10.0

        key, kind = SCORE_BASELINE.get(row["label"], (None, "none"))
        row["baseline_key"] = key
        row["baseline_kind"] = kind
        if key is None:
            row["average_base"] = None
            row["marginal_share"] = None
            row["implied_offset"] = None
            continue
        base = BASELINES[key]
        row["average_base"] = base["receipts_10yr"] / base["statutory_rate"] / 10.0
        row["marginal_share"] = row["marginal_base"] / row["average_base"]
        row["implied_offset"] = 1.0 - row["marginal_share"]
    return rows


def _rule(width: int = 108) -> str:
    return "-" * width


def print_published(rows: list[dict]) -> None:
    print("\n1. THE PUBLISHED RECORD")
    print(_rule())
    print(
        f"{'source':30s} {'date':8s} {'window':12s} {'scope':16s} "
        f"{'step':>6s} {'10yr $B':>10s} {'per pp $B':>10s}"
    )
    print(_rule())
    for row in rows:
        step = f"{row['rate_change_pp']:+.1f}pp"
        print(
            f"{row['label']:30s} {row['date']:8s} {row['window']:12s} "
            f"{row['scope']:16s} {step:>6s} "
            f"{row['ten_year_billions']:10.1f} {row['per_point_check']:10.2f}"
        )
    print(_rule())
    print(
        "Per-point dollars are NOT comparable across `scope`, across statutory\n"
        "rate levels, or across windows. Table 3 is the comparable metric."
    )


def print_baselines() -> None:
    print("\n2. THE BASELINE EACH SCORE WAS PRICED AGAINST")
    print(_rule())
    print(
        f"{'vintage':16s} {'window':12s} {'rate':>6s} {'receipts 10yr':>14s} "
        f"{'avg/yr':>9s} {'avg base/yr':>12s}"
    )
    print(_rule())
    for key, base in BASELINES.items():
        avg = base["receipts_10yr"] / 10.0
        avg_base = avg / base["statutory_rate"]
        print(
            f"{key:16s} {base['window']:12s} {base['statutory_rate']:6.0%} "
            f"{base['receipts_10yr']:14.1f} {avg:9.1f} {avg_base:12.1f}"
        )
    print(_rule())
    print(
        "avg base/yr = corporate receipts / statutory rate: the base which,\n"
        "taxed at the statutory rate, reproduces the receipts the vintage\n"
        "projects. It already nets credits, NOLs and shifting."
    )


def print_implied(rows: list[dict]) -> None:
    print("\n3. IMPLIED MARGINAL BASE AND IMPLIED OFFSET")
    print(_rule())
    print(
        f"{'source':30s} {'scope':16s} {'B_marg/yr':>10s} {'B_avg/yr':>10s} "
        f"{'share':>8s} {'offset':>8s}  baseline"
    )
    print(_rule())
    for row in rows:
        share = row["marginal_share"]
        if share is None:
            print(
                f"{row['label']:30s} {row['scope']:16s} "
                f"{row['marginal_base']:10.1f} {'-':>10s} {'-':>8s} {'-':>8s}  "
                "no baseline transcribed"
            )
            continue
        flag = "" if row["baseline_kind"] == "named" else " (proxy)"
        print(
            f"{row['label']:30s} {row['scope']:16s} "
            f"{row['marginal_base']:10.1f} {row['average_base']:10.1f} "
            f"{share:8.1%} {row['implied_offset']:8.1%}  "
            f"{row['baseline_key']}{flag}"
        )
    print(_rule())
    base = BASELINES["cbo_feb_2024"]
    avg_2024 = base["receipts_10yr"] / base["statutory_rate"] / 10.0
    for label, step_pp, total, scope in MODEL_ROWS:
        marg = abs(total) / (step_pp / 100.0) / 10.0
        print(
            f"{label:30s} {scope:16s} {marg:10.1f} {avg_2024:10.1f} "
            f"{marg / avg_2024:8.1%} {1 - marg / avg_2024:8.1%}  cbo_feb_2024"
        )
    print(_rule())


def print_same_window(rows: list[dict]) -> None:
    """The apples-to-apples set: everything priced on FY2025-2034."""
    print("\n3b. FOUR ESTIMATORS, ONE WINDOW (FY2025-2034)")
    print(_rule())
    subset = [r for r in rows if r["window"] == "FY2025-2034"]
    subset.sort(key=lambda r: r["marginal_share"])
    base = BASELINES["cbo_feb_2024"]
    avg = base["receipts_10yr"] / base["statutory_rate"] / 10.0
    print(f"{'source':30s} {'estimator':28s} {'scope':16s} {'B_marg/yr':>10s} {'share':>8s}")
    print(_rule())
    for row in subset:
        print(
            f"{row['label']:30s} {row['estimator']:28s} {row['scope']:16s} "
            f"{row['marginal_base']:10.1f} {row['marginal_share']:8.1%}"
        )
    for label, step_pp, total, scope in MODEL_ROWS:
        marg = abs(total) / (step_pp / 100.0) / 10.0
        print(
            f"{label:30s} {'fiscal-policy-calculator':28s} {scope:16s} "
            f"{marg:10.1f} {marg / avg:8.1%}"
        )
    print(_rule())
    shares = [r["marginal_share"] for r in subset if r["source"] != "Treasury"]
    print(
        f"Excluding Treasury, the published shares on this window span "
        f"{min(shares):.1%} to {max(shares):.1%}. Treasury's is 79.5% and it is\n"
        "the only one of the four whose scope is not rate-only. The model's "
        "derived path is 80.8% since lane\nW6 projected its base off CBO's own "
        "receipts path - Treasury's neighbourhood, and above every other "
        "estimator\non the record. It was 90.8% before, higher than all four, "
        "and the benchmark it is fitted to is the second highest."
    )
    print(
        "\nRead the shares with the denominator in mind. Only the JCT/CBO rows "
        "put numerator and\ndenominator in the same house: JCT's estimate "
        "against CBO's own baseline. Tax Foundation,\nPWBM and Treasury run "
        "their own baselines, so their shares are cross-house ratios and carry "
        "a\nforecast difference as well as a modelling one."
    )


def print_year_by_year() -> None:
    print("\n4. MARGINAL SHARE, YEAR BY YEAR, AGAINST CBO'S OWN FEB 2024 PATH")
    print(_rule())
    base = BASELINES["cbo_feb_2024"]
    print(
        f"{'FY':>5s} {'receipts':>9s} {'B_avg':>9s} "
        f"{'Opt64 B_m':>10s} {'share':>7s} "
        f"{'GB25 B_m':>10s} {'share':>7s} "
        f"{'model B_m':>10s} {'share':>7s} {'pre-W6':>7s}"
    )
    print(_rule())
    for i, fy in enumerate(range(2025, 2035)):
        receipts = base["annual"][i]
        b_avg = receipts / base["statutory_rate"]
        b_opt = OPT64_ANNUAL[i] / 0.01
        b_gb = GB2025_ANNUAL[i] / 0.07
        b_mod = abs(MODEL_DERIVED_1PP_ANNUAL[i]) / 0.01
        b_old = abs(MODEL_DERIVED_1PP_ANNUAL_PRE_W6[i]) / 0.01
        print(
            f"{fy:5d} {receipts:9.1f} {b_avg:9.1f} "
            f"{b_opt:10.1f} {b_opt / b_avg:7.1%} "
            f"{b_gb:10.1f} {b_gb / b_avg:7.1%} "
            f"{b_mod:10.1f} {b_mod / b_avg:7.1%} {b_old / b_avg:7.1%}"
        )
    print(_rule())
    shares = [OPT64_ANNUAL[i] / 0.01 / (base["annual"][i] / 0.21) for i in range(2, 10)]
    print(
        f"CBO Option 64's share over FY2027-2034: {min(shares):.3f} to "
        f"{max(shares):.3f} - flat to {100 * (max(shares) / min(shares) - 1):.1f}%."
    )
    old = [
        abs(MODEL_DERIVED_1PP_ANNUAL_PRE_W6[i]) / 0.01 / (base["annual"][i] / 0.21)
        for i in range(10)
    ]
    mod = [
        abs(MODEL_DERIVED_1PP_ANNUAL[i]) / 0.01 / (base["annual"][i] / 0.21)
        for i in range(10)
    ]
    print(
        f"The model's share ran {old[0]:.3f} rising to {old[-1]:.3f} before lane "
        "W6 - it priced more than 100% of the vintage's own\naverage base in the "
        "last two years, which no marginal base can be. W6 projected the base "
        "off this same\nreceipts path, and the column now reads "
        f"{mod[0]:.3f} then flat at about {sum(mod[1:]) / 9:.3f}: the drift is "
        "gone because the\nnumerator and the denominator are the same series. "
        "The LEVEL is unchanged in kind - about 0.83 of the\naverage base "
        "against Treasury's 0.795, JCT's 0.559 and Tax Foundation's 0.551 - "
        "and section 5's diagnosis holds:\nthe residual is a disagreement between "
        "estimators, not a vintage problem."
    )


def print_counterfactual() -> None:
    """What a vintage-projected base reads. Hand arithmetic, now also built.

    Lane W6 (``planning/lanes/W6_corporate_base_projection.md``) shipped this
    mechanism. The figures below are still the memo's own hand arithmetic,
    unchanged, so the prediction stays legible beside what was built; the two
    differ by 1.4% for two stated reasons, printed at the end.
    """
    print("\n5. COUNTERFACTUAL: THE BASE PROJECTED OFF THE SCORED VINTAGE")
    print(_rule())
    base = BASELINES["cbo_feb_2024"]
    # Static per point per year = receipts_t x (0.01 / 0.21); receipts/rate is
    # already credit-realized, so no further credit ratio is applied.
    static = [r * 0.01 / base["statutory_rate"] for r in base["annual"]]
    # IRC 6655 phase as the module implements it.
    phased = [static[0] * 0.75] + [s * 0.99038 for s in static[1:]]
    gross = sum(phased)
    print(f"  static, credit-realized, before behaviour : {gross:8.2f}")
    for step_pp in (1.0, 7.0):
        new_rate = 0.21 + step_pp / 100.0
        offset = 1.0 - 0.8 * new_rate
        total = gross * step_pp * offset
        target = -135.7 if step_pp == 1.0 else -1347.0
        print(
            f"  +{step_pp:.0f}pp with beta=0.8 offset ({offset:.3f})       : "
            f"{-total:9.2f}   vs {target:9.1f}   "
            f"err {100 * abs(total / abs(target) - 1):5.1f}%"
        )
    print(_rule())
    # What the row would need, and why no lane may take it.
    needed = 135.7 / gross
    print(
        f"  The total factor that reproduces Option 64 is {needed:.4f}. JCT's own\n"
        f"  window-average marginal share against this same baseline is 0.559 and\n"
        f"  its steady-state share is 0.590 - so a 'marginal realization ratio' of\n"
        f"  about 0.59 with NO behavioural offset reproduces the row to about 2%."
    )
    print(
        f"  {gross:.2f} x 0.59 = {gross * 0.59:.2f} against -135.7, "
        f"{100 * abs(gross * 0.59 / 135.7 - 1):.1f}%."
    )
    print(
        "  That number is JCT's answer read backwards, and section 4 of the plan\n"
        "  forbids picking it. It is printed here so a later lane that arrives at\n"
        "  0.59 by another route knows where it is standing. Note also that it is\n"
        "  NOT separable from beta: JCT's 0.59 already contains whatever behaviour\n"
        "  JCT applies, so a lane that keeps beta AND adds a share double-counts."
    )
    print(_rule())
    print(
        "Hand arithmetic on published inputs. Lane W6 built it, and the shipped\n"
        "identity returns -196.08 at +1pp (44.50% vs Option 64) and -1,292.62 at\n"
        "+7pp (4.04% vs the Green Book row) - 1.4% above the figures printed\n"
        "above, for two stated reasons. The lane keeps the section 6655\n"
        "convolution `0.75 + 0.25 B(t-1)/B(t)` rather than the closed form\n"
        "0.99038 above, which assumes the constant growth the lane removes; and\n"
        "it anchors the level on SOI's own credit-realized TY2022 base over\n"
        "Treasury's actual FY2022 receipts (4.80133 per receipts dollar) rather\n"
        "than on 1/tau (4.76190) - 0.83% apart, which is the check that the two\n"
        "series measure the same thing."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the enriched rows as JSON")
    args = parser.parse_args(argv)

    rows = enrich(load_scores())

    if args.json:
        payload = [
            {
                k: v
                for k, v in row.items()
                if k
                in {
                    "label", "source", "estimator", "date", "window", "scope",
                    "rate_change_pp", "ten_year_billions", "per_point_check",
                    "marginal_base", "average_base", "marginal_share",
                    "implied_offset", "baseline_key", "baseline_kind", "verified",
                }
            }
            for row in rows
        ]
        json.dump(payload, sys.stdout, indent=2)
        print()
        return 0

    print("Corporate rate: reconciling the published per-point yields")
    print(f"Source file: {SCORES_CSV.relative_to(PROJECT_ROOT)}")
    print_published(rows)
    print_baselines()
    print_implied(rows)
    print_same_window(rows)
    print_year_by_year()
    print_counterfactual()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
