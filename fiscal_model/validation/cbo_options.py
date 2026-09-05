"""
Shape classification for the CBO *Options for Reducing the Deficit: 2025-2034*
battery.

Why this file exists
--------------------
The 76 options in `CBO 60557 <https://www.cbo.gov/publication/60557>`_ are the
largest published set of independently scored, single-provision policies that
exists. That makes them the natural out-of-sample battery for the Tier 1
(uncalibrated) validation tier — but only for the subset the *uncalibrated*
path can express **without any tuning**.

This module records that judgement, one line per option, so the battery's
composition is auditable rather than a curated set of flattering shapes.
``tests/test_cbo_options.py`` asserts that every one of the 76 options is
classified and that every runnable one builds a real policy object.

The bar for ``runnable``
------------------------
An option is runnable only if **all** of the following hold.

1. **The shape exists.** ``create_policy_from_score`` can build it from the
   record's own fields: an ordinary-rate change, an AGI-inclusive surtax, an
   LTCG/QDIV rate change, a deemed-realization-at-death reform, a corporate
   rate change, a flat payroll-tax rate on all earnings, or a spending level
   change.
2. **No parameter is fitted to the target.** Behavioural parameters are the
   frozen module defaults (ETI 0.25; capital-gains elasticities 0.8/0.4;
   corporate elasticity 0.25). Where a module constant was *calibrated to
   reproduce this same reform* from another source, the option is excluded as
   **leakage**, not scored — see Options 53 and 62.
3. **Every input is stated by CBO, not derived from the answer.** For spending
   options that means the option's own table must state a *budget authority*
   level path distinct from the outlay total being predicted, and that path
   must be what ``SpendingPolicy`` can express: a level growing at roughly
   inflation. The mechanical test is
   :func:`is_level_budget_authority_path` — the BA path from the first
   effective year must stay within
   :data:`LEVEL_PATH_TOLERANCE` of ``level x 1.02**t``. Ramps (Options 28, 36,
   41), wind-downs (32, 34) and declining caseloads (40) fail it.

   Mandatory options fail (3) categorically: CBO publishes no funding-level
   input distinct from the outlay path, so feeding the first-year outlay back
   in would make the "prediction" an aggregation of the target itself.

   A leakage exclusion is not permanent. Option 56 was excluded on that ground
   until the expenditure module stopped needing a fitted annual to express a
   percentile cap: it now scores the published expenditure level times a share
   read off a premium distribution, so nothing calibrated to a target sits in
   the path and the option is runnable. Options 53 and 62 still are not.

   The budget authority a runnable spending option states is now spent out
   into outlays rather than booked as one (:mod:`fiscal_model.spending_outlays`),
   which is what makes the authority-vs-outlay distinction above load-bearing:
   the model predicts an outlay path from an authority level, instead of
   quietly asserting they are the same number. The spend-out **rates** are
   fitted on the 14 options that publish both rows and are *not* scored here;
   options 37, 38, 39, 42 and 43 never donate to a profile they are then
   scored against.

Sign conventions
----------------
The CSVs carry both. ``savings_*`` columns follow CBO (positive = reduces the
deficit); ``deficit_effect_*`` and everything in this module follow the app
(positive = increases the deficit).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data_files" / "validation"
OPTIONS_CSV = DATA_DIR / "cbo_options_2025_2034.csv"
ALTERNATIVES_CSV = DATA_DIR / "cbo_options_2025_2034_alternatives.csv"

N_OPTIONS = 76

#: Publication metadata, repeated here so callers need not re-read the CSV
#: header comments.
SOURCE_NAME = "Congressional Budget Office"
SOURCE_TITLE = "Options for Reducing the Deficit: 2025 to 2034"
SOURCE_DATE = "2024-12"
SOURCE_URL = "https://www.cbo.gov/publication/60557"

#: Baselines stated on PDF page 2 ("Notes About This Report").
REVENUE_BASELINE = (
    "CBO February 2024 baseline (The Budget and Economic Outlook: 2024 to 2034, "
    "pub. 59710)"
)
SPENDING_BASELINE = (
    "CBO June 2024 baseline (An Update to the Budget and Economic Outlook: "
    "2024 to 2034, pub. 60039)"
)

#: Maximum relative deviation of a budget-authority path from ``level x 1.02**t``
#: for the path to count as a level change ``SpendingPolicy`` can express.
LEVEL_PATH_TOLERANCE = 0.25


@dataclass(frozen=True)
class OptionRecord:
    """One row of Table 1-1 (report pp. 2-3)."""

    option_number: int
    title: str
    category: str
    budget_area: str
    savings_low_billions: float
    savings_high_billions: float
    report_page: int | None
    baseline_vintage: str

    @property
    def deficit_effect_range(self) -> tuple[float, float]:
        """CBO savings restated in the app's convention (+ = increases deficit)."""
        return (-self.savings_high_billions, -self.savings_low_billions)


@dataclass(frozen=True)
class AlternativeRecord:
    """One reported line inside an option's own table."""

    option_number: int
    alternative_id: str
    label: str
    measure: str
    savings_10yr_billions: float
    annual_savings_billions: tuple[float, ...]
    report_page: int | None

    @property
    def deficit_effect_10yr_billions(self) -> float:
        return -self.savings_10yr_billions


@dataclass(frozen=True)
class RunnableOption:
    """An option (or one of its alternatives) the uncalibrated path can score.

    Attributes:
        alternative_id: The row of the alternatives CSV the model's *input*
            comes from. For tax shapes that row also carries the target; for
            spending shapes it carries the budget-authority level.
        target_alternative_id: For spending shapes, the row that carries the
            **target** - CBO's 10-year outlay total. Kept separate from
            ``alternative_id`` because input and target are different series,
            which is exactly what makes the spending cases a real test.
    """

    option_number: int
    alternative_id: str
    score_id: str
    shape: str
    note: str
    target_alternative_id: str | None = None

    @property
    def target_row_id(self) -> str:
        """The alternatives-CSV row the pre-registered target was read from."""
        return self.target_alternative_id or self.alternative_id


@dataclass(frozen=True)
class OptionClassification:
    """The verdict for one option, plus per-alternative verdicts."""

    option_number: int
    title: str
    category: str
    runnable: bool
    reason: str
    runnable_alternatives: tuple[RunnableOption, ...] = ()


# ---------------------------------------------------------------------------
# Runnable set
# ---------------------------------------------------------------------------

#: The 15 alternatives the uncalibrated path can express. ``score_id`` is the
#: ``KNOWN_SCORES`` key; ``alternative_id`` indexes the alternatives CSV.
RUNNABLE_OPTIONS: tuple[RunnableOption, ...] = (
    # -- Individual income tax rates ---------------------------------------
    RunnableOption(
        45, "45.1", "cbo_opt45_all_rates_1pp", "ordinary_rate",
        "Uniform +1pp on every ordinary bracket; threshold 0, ordinary-income base.",
    ),
    RunnableOption(
        45, "45.2", "cbo_opt45_top4_brackets_2pp", "ordinary_rate",
        "+2pp on the four highest brackets. The generic path takes a single "
        "threshold, so the 2025 single-filer 24%-bracket floor ($103,350, IRS "
        "Rev. Proc. 2024-40) stands in for a filing-status-specific boundary.",
    ),
    RunnableOption(
        46, "46.1", "cbo_opt46_agi_surtax_1pp_20k", "ordinary_rate",
        "AGI surtax: AGI-inclusive base, single-filer threshold.",
    ),
    RunnableOption(
        46, "46.2", "cbo_opt46_agi_surtax_2pp_100k", "ordinary_rate",
        "AGI surtax: AGI-inclusive base, single-filer threshold.",
    ),
    # -- Capital gains ------------------------------------------------------
    RunnableOption(
        47, "47.1", "cbo_opt47_ltcg_qdiv_2pp", "capital_gains",
        "+2pp on all long-term gains and qualified dividends, frozen 0.8/0.4 "
        "realization elasticities, SOI-populated baseline realizations and rate.",
    ),
    RunnableOption(
        51, "51.2", "cbo_opt51_gains_at_death", "capital_gains",
        "Constructive realization at death with no exemption: the module's "
        "step-up-elimination channel with step_up_exemption=0 and no rate change.",
    ),
    # -- Payroll ------------------------------------------------------------
    RunnableOption(
        61, "61.1", "cbo_opt61_new_payroll_tax_1pct", "payroll_rate",
        "A new flat tax on all earnings shares the Medicare base (all covered "
        "earnings, no taxable maximum), so it is scored as a Medicare-base rate "
        "change; the module constant is the $400B/2.9% revenue identity.",
    ),
    RunnableOption(
        61, "61.2", "cbo_opt61_new_payroll_tax_2pct", "payroll_rate",
        "As 61.1 at 2 percentage points.",
    ),
    # -- Corporate ----------------------------------------------------------
    RunnableOption(
        64, "64.1", "cbo_opt64_corporate_rate_1pp", "corporate_rate",
        "21% -> 22%, scored in the corporate module's derived mode: IRS SOI "
        "Table 11's published income subject to tax, realized at SOI's own "
        "after-credits/before-credits ratio, offset by one frozen "
        "profit-shifting semi-elasticity and settled on IRC section 6655's "
        "estimated-payment calendar. Not the module's fitted profits "
        "aggregate, whose own comment calls it calibrated to reproduce the "
        "21% -> 28% benchmark - a different reform, so not a leakage "
        "exclusion under (2) above, but not a bottom-up input either. Nothing "
        "in the derived path reads a level off the baseline, so this shape "
        "keeps the vintage-independence every other one has.",
    ),
    # -- Tax expenditures ---------------------------------------------------
    RunnableOption(
        56, "56.9", "cbo_opt56_employer_health_income_only", "tax_expenditure",
        "Limit only the income-tax exclusion for employment-based health "
        "insurance to the 50th percentile of premiums. Scored in the "
        "expenditure module's derived mode: the published expenditure level "
        "times the share of premium dollars above CBO's own stated 2028 "
        "limits ($10,000 individual, $24,400 family). No fitted annual is "
        "read. The option's other two alternatives limit the payroll-tax "
        "exclusion as well and are out of scope per alternative.",
    ),
    # -- Discretionary spending --------------------------------------------
    RunnableOption(
        37, "37.1", "cbo_opt37_international_affairs", "spending",
        "25% cut to the international affairs budget; CBO's own first-year "
        "budget-authority level (-$23B in 2026) grown at the module default.",
        target_alternative_id="37.2",
    ),
    RunnableOption(
        38, "38.1", "cbo_opt38_national_service", "spending",
        "Eliminate CNCS funding except the National Service Trust; first-year "
        "budget authority -$1.3B.",
        target_alternative_id="38.2",
    ),
    RunnableOption(
        39, "39.1", "cbo_opt39_pell_eligibility", "spending",
        "Restrict Pell eligibility to maximum-award students; first-year "
        "discretionary budget authority -$2.5B. Target is the discretionary "
        "outlay total only (the mandatory piece is reported separately).",
        target_alternative_id="39.2",
    ),
    RunnableOption(
        42, "42.1", "cbo_opt42_nondefense_discretionary", "spending",
        "One-third cut to transportation and education grant funding; first-year "
        "spending authority -$41B.",
        target_alternative_id="42.2",
    ),
    RunnableOption(
        43, "43.11", "cbo_opt43_state_local_grants", "spending",
        "25%/50% cut to five grant programs; first-year total budget authority "
        "-$12.0B (front-loaded by IIJA advance funding).",
        target_alternative_id="43.12",
    ),
)


# ---------------------------------------------------------------------------
# Out-of-scope set
# ---------------------------------------------------------------------------

#: Every option the uncalibrated path cannot express, with a one-line reason.
#: Options that appear in :data:`RUNNABLE_OPTIONS` are absent from this map.
OUT_OF_SCOPE_REASONS: dict[int, str] = {
    # ---- Mandatory spending (Options 1-27) --------------------------------
    # These fail the "input distinct from the target" test categorically: CBO
    # publishes an outlay path that is the *result* of a program-rule change,
    # with no funding level to feed in.
    1: "Crop-insurance subsidy rates: mandatory program-rule change with no stated funding level.",
    2: "GSE guarantee fees and loan limits: mandatory receipt change driven by mortgage-market modelling.",
    3: "Pell add-on: mandatory program-rule change with no stated funding level.",
    4: "Medicaid per-capita caps: mandatory program-rule change; no Medicaid module.",
    5: "Provider-tax limits: Medicaid financing rule; no Medicaid module.",
    6: "Federal Medicaid matching rates: mandatory matching-formula change; no Medicaid module.",
    7: "Medicare Part B premiums: mandatory premium-formula change; no Medicare module.",
    8: "Medicare Advantage benchmarks: Medicare payment rule; no Medicare module.",
    9: "FEHB voucher: federal-employee benefit formula change; no such module.",
    10: "TRICARE for Life enrollment fees: military health benefit rule; no such module.",
    11: "TRICARE for Life out-of-pocket minimums: military health benefit rule; no such module.",
    12: "Medicare cost sharing and Medigap: Medicare benefit-design change; no Medicare module.",
    13: "Medicare bad-debt coverage: Medicare payment rule; no Medicare module.",
    14: "Graduate medical education payments: Medicare payment rule; no Medicare module.",
    15: "Medicare Advantage risk adjustment: Medicare payment rule; no Medicare module.",
    16: "Hospital outpatient payment rates: Medicare payment rule; no Medicare module.",
    17: "340B drug payments: Medicare payment rule; no Medicare module.",
    18: "School meal subsidies: means-tested program eligibility rule; no such module.",
    19: "Social Security benefits for high earners: benefit-formula (PIA bend point) change; the payroll module models revenue, not benefits.",
    20: "Uniform Social Security benefit: benefit-formula change; the payroll module models revenue, not benefits.",
    21: "Full retirement age: benefit-formula change; the payroll module models revenue, not benefits.",
    22: "SSDI recent-work requirement: disability eligibility rule; no such module.",
    23: "Means-testing VA disability compensation: veterans benefit eligibility rule; no such module.",
    24: "VA individual unemployability payments: veterans benefit eligibility rule; no such module.",
    25: "VA disability benefits after the FRA: veterans benefit eligibility rule; no such module.",
    26: "VA disability ratings: veterans benefit eligibility rule; no such module.",
    27: "Chained CPI indexing: an indexation change across many programs and the tax code; no indexation module.",

    # ---- Discretionary spending (Options 28-44) ---------------------------
    # These have a stated budget-authority path, but it is not a level path
    # SpendingPolicy can express (see is_level_budget_authority_path).
    28: "DoD budget: a 10-year funding ramp (BA -$28B to -$175B), not a level; expressing it needs a plateau and ramp length read off the target's own path.",
    29: "Military basic-pay cap: a compounding pay-raise differential, so the BA path ramps rather than holding a level.",
    30: "Military-to-civilian substitution: phased conversion, ramping BA path.",
    31: "Ford class carriers: lumpy shipbuilding appropriations (BA -$0.6B to -$5.5B and back); no level.",
    32: "Long-Range Standoff Weapon: a program wind-down, BA falls to zero by 2034.",
    33: "Future Long-Range Assault Aircraft: development ramp, rising BA path.",
    34: "B-1B retirement: wind-down, BA falls to zero by 2032.",
    35: "F-22 retirement: BA path declines ~2%/yr in nominal terms, outside the level-path tolerance.",
    36: "Basic Allowance for Housing: nine successive 1.7pp reductions, so the BA path ramps.",
    40: "VA priority groups 7 and 8: savings track a declining enrolled caseload, not a level.",
    41: "Federal civilian pay adjustment: a compounding pay differential, so BA ramps from -$1.2B to -$17.0B.",
    44: "Davis-Bacon repeal: savings accrue as contracts turn over, so the first year is a partial-year level.",

    # ---- Revenues (Options 45-76) -----------------------------------------
    48: "Head-of-household filing status: a filing-status rule change; the generic path has no filing-status dimension.",
    49: "Itemized deductions: routed to the calibrated TaxExpenditurePolicy module, which carries a per-benchmark annual constant.",
    50: "Charitable deduction limits: deduction base change; the tax-expenditure module is calibrated, not predictive here.",
    52: "Private activity bonds: municipal-bond issuance and yield modelling; no such module.",
    53: "NIIT base expansion to active S-corp and partnership income: the payroll module's NIIT constant ($25B/yr) is calibrated to JCT's estimate of this same reform - leakage, not prediction.",
    54: "Carried interest: partnership character-conversion rule; no such module.",
    55: "Taxing VA disability payments: needs a benefit-recipient income distribution the model does not carry.",
    57: "Retirement contribution limits: needs contribution-level microdata; no such module.",
    58: "Education tax preferences: credit-module territory, and its annuals are calibrated per benchmark.",
    59: "EITC/CTC investment income limit: credit eligibility rule inside the calibrated credits module.",
    60: "EITC/CTC Social Security number requirement: eligibility rule requiring return-level immigration status.",
    62: "Social Security taxable maximum: the payroll module's covered-wage bands are anchored to reproduce the Trustees/CBO annuals for exactly these two reforms (90% coverage and the $250K donut) - leakage, not prediction.",
    63: "Newly hired state and local employees: needs non-covered-employment data the model does not carry.",
    65: "Taxing all foreign income at the statutory rate: the corporate module's GILTI base and rate step are set to reproduce the Biden GILTI package - leakage, not prediction.",
    66: "LIFO and inventory valuation: an accounting-method timing change; no inventory module.",
    67: "Advertising amortization: an accounting-method timing change; no such module.",
    68: "Low-Income Housing Tax Credit: a project-allocation credit; no such module.",
    69: "Alcohol excise taxes: no excise module.",
    70: "Tobacco excise taxes: no excise module.",
    71: "Motor fuel excise taxes: no excise module.",
    72: "5% value-added tax: no consumption-tax module.",
    73: "Greenhouse gas emissions tax: routed to the climate module, which is calibrated to published carbon-price scores.",
    74: "Financial transactions tax: no transaction-volume base in the model.",
    75: "USCIS and CBP fees: a fee schedule, not a tax base the model carries.",
    76: "FERS employee contributions: a federal-retirement contribution rule; no such module.",
}

#: Alternatives inside an otherwise-runnable option that are themselves out of
#: scope.
OUT_OF_SCOPE_ALTERNATIVES: dict[str, str] = {
    "51.1": (
        "Carryover basis defers the tax until the heir sells; the capital-gains "
        "module only implements deemed realization at death, so it has no "
        "carryover path."
    ),
    "56.3": (
        "Limits the income *and payroll* tax exclusion. The expenditure module "
        "carries the income-tax expenditure only and has no payroll base, so "
        "scoring this alternative would be a known base mismatch rather than a "
        "prediction. CBO's third alternative is the same cap on the income-tax "
        "exclusion alone, and that is the one this battery scores."
    ),
    "56.6": (
        "As 56.3 at the 75th percentile of premiums: income and payroll "
        "exclusion together, and CBO publishes no income-tax-only counterpart "
        "at that percentile."
    ),
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


def _maybe_float(value: str) -> float:
    return float(value) if value not in ("", "None") else 0.0


def _maybe_int(value: str) -> int | None:
    return int(value) if value not in ("", "None") else None


@lru_cache(maxsize=1)
def load_options() -> tuple[OptionRecord, ...]:
    """All 76 options, from Table 1-1."""
    return tuple(
        OptionRecord(
            option_number=int(row["option_number"]),
            title=row["title"],
            category=row["category"],
            budget_area=row["budget_area"],
            savings_low_billions=_maybe_float(row["savings_low_billions"]),
            savings_high_billions=_maybe_float(row["savings_high_billions"]),
            report_page=_maybe_int(row["report_page"]),
            baseline_vintage=row["baseline_vintage"],
        )
        for row in sorted(_rows(OPTIONS_CSV), key=lambda r: int(r["option_number"]))
    )


@lru_cache(maxsize=1)
def load_alternatives() -> tuple[AlternativeRecord, ...]:
    """Every reported line from the individual option tables."""
    return tuple(
        AlternativeRecord(
            option_number=int(row["option_number"]),
            alternative_id=row["alternative_id"],
            label=row["label"],
            measure=row["measure"],
            savings_10yr_billions=_maybe_float(row["savings_10yr_billions"]),
            annual_savings_billions=tuple(
                _maybe_float(row[f"savings_{year}_billions"])
                for year in range(2025, 2035)
            ),
            report_page=_maybe_int(row["report_page"]),
        )
        for row in _rows(ALTERNATIVES_CSV)
    )


def get_alternative(alternative_id: str) -> AlternativeRecord | None:
    """One alternative row by its ``option.sequence`` id."""
    return next(
        (a for a in load_alternatives() if a.alternative_id == alternative_id), None
    )


def get_option(option_number: int) -> OptionRecord | None:
    """One Table 1-1 row."""
    return next((o for o in load_options() if o.option_number == option_number), None)


# ---------------------------------------------------------------------------
# The level-path test for spending shapes
# ---------------------------------------------------------------------------

def is_level_budget_authority_path(
    annual: tuple[float, ...] | list[float],
    *,
    growth: float = 0.02,
    tolerance: float = LEVEL_PATH_TOLERANCE,
) -> bool:
    """
    Is this budget-authority path a level change ``SpendingPolicy`` can express?

    ``SpendingPolicy`` produces ``level x (1 + growth) ** t``. A CBO option is
    only scoreable by that shape when its own published path is close to it, so
    the test is applied to CBO's numbers, never to the model's.

    Args:
        annual: Savings by year (CBO sign: positive = reduces the deficit).
        growth: The module's default annual growth rate.
        tolerance: Maximum relative deviation from the fitted level path.

    Returns:
        True when every effective year is within ``tolerance`` of the level path.
    """
    non_zero = [index for index, value in enumerate(annual) if abs(value) > 1e-9]
    if not non_zero:
        return False
    path = list(annual)[non_zero[0]:]
    level = path[0]
    if level == 0:
        return False
    return all(
        abs(value - level * (1 + growth) ** offset) / abs(level * (1 + growth) ** offset)
        <= tolerance
        for offset, value in enumerate(path)
    )


def first_effective_year(
    annual: tuple[float, ...] | list[float], *, window_start: int = 2025
) -> int | None:
    """Calendar year of the first non-zero entry in an option's annual path."""
    for offset, value in enumerate(annual):
        if abs(value) > 1e-9:
            return window_start + offset
    return None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def classify_all() -> tuple[OptionClassification, ...]:
    """Classify every one of the 76 options as runnable or out of scope."""
    by_option: dict[int, list[RunnableOption]] = {}
    for entry in RUNNABLE_OPTIONS:
        by_option.setdefault(entry.option_number, []).append(entry)

    out: list[OptionClassification] = []
    for option in load_options():
        runnable = by_option.get(option.option_number, [])
        if runnable:
            reason = "; ".join(entry.note for entry in runnable)
        else:
            reason = OUT_OF_SCOPE_REASONS.get(option.option_number, "")
        out.append(
            OptionClassification(
                option_number=option.option_number,
                title=option.title,
                category=option.category,
                runnable=bool(runnable),
                reason=reason,
                runnable_alternatives=tuple(runnable),
            )
        )
    return tuple(out)


def runnable_score_ids() -> dict[str, RunnableOption]:
    """``KNOWN_SCORES`` policy id -> the option alternative it came from."""
    return {entry.score_id: entry for entry in RUNNABLE_OPTIONS}


def describe_option_coverage() -> dict[str, object]:
    """
    Account for all 76 options.

    ``total`` always equals ``runnable_options + out_of_scope``; anything in
    ``unclassified`` is an option with neither a runnable alternative nor a
    stated reason, i.e. a silently dropped benchmark.
    """
    classifications = classify_all()
    runnable = [c for c in classifications if c.runnable]
    out_of_scope = [c for c in classifications if not c.runnable and c.reason]
    unclassified = [c for c in classifications if not c.runnable and not c.reason]

    by_category: dict[str, dict[str, int]] = {}
    for entry in classifications:
        bucket = by_category.setdefault(
            entry.category, {"runnable": 0, "out_of_scope": 0}
        )
        bucket["runnable" if entry.runnable else "out_of_scope"] += 1

    return {
        "total": len(classifications),
        "runnable_options": len(runnable),
        "runnable_alternatives": len(RUNNABLE_OPTIONS),
        "out_of_scope": len(out_of_scope),
        "unclassified": sorted(c.option_number for c in unclassified),
        "by_category": by_category,
        "runnable_score_ids": sorted(entry.score_id for entry in RUNNABLE_OPTIONS),
    }


__all__ = [
    "ALTERNATIVES_CSV",
    "LEVEL_PATH_TOLERANCE",
    "OPTIONS_CSV",
    "OUT_OF_SCOPE_ALTERNATIVES",
    "OUT_OF_SCOPE_REASONS",
    "REVENUE_BASELINE",
    "RUNNABLE_OPTIONS",
    "SOURCE_DATE",
    "SOURCE_NAME",
    "SOURCE_TITLE",
    "SOURCE_URL",
    "SPENDING_BASELINE",
    "AlternativeRecord",
    "OptionClassification",
    "OptionRecord",
    "RunnableOption",
    "classify_all",
    "describe_option_coverage",
    "first_effective_year",
    "get_alternative",
    "get_option",
    "is_level_budget_authority_path",
    "load_alternatives",
    "load_options",
    "runnable_score_ids",
]
