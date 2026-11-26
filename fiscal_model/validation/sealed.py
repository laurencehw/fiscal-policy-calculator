"""
The sealed battery: published scores the model has never been run against.

Why this exists
---------------
The 44-row out-of-sample tier (``preregistered.py``) was frozen before it was
first scored, but it has since been read through a dozen engineering waves, so
it is a development set as much as a test (outside review, 23 Nov 2026,
finding 2.1). It also holds no tax cut, because CBO's *Options* volumes list
only ways to reduce the deficit. This module is a second battery that answers
both points, and its rules are stricter than the first's.

The rules
---------
1. **Locked.** :data:`LOCK_DATE` is the day the battery opened. Every row is
   entered in a commit of its own with scoring switched off
   (``scoring_enabled=False``), and switched on in a *later* commit. That is the
   same two-commit protocol Phases B and D used, so "the target was fixed
   before the model was run against it" can be read off the git history.
2. **Never pooled.** The rows are not in ``KNOWN_SCORES``, so no scorecard
   tier, CI gate, band or headline counts them. They are reported in their own
   block (``scripts/sealed_battery.py``), beside the 44 rows and never added
   to them.
3. **Never debugged against.** A miss here is recorded, not fixed. A change
   whose stated reason is a sealed row's error is out of bounds. A model change
   made for another reason that moves a sealed row is reported with the change.
   Once a row has been read for a fix it leaves the battery: it is moved to
   ``RETIRED`` with the reason, and its result is still shown.
4. **Tax cuts as well as rises.** Each design enters in both directions when
   the source publishes both, so the battery tests the sign the 44 rows cannot.
5. **Eligible sources.** Rows are ten-year conventional scores published by
   CBO, JCT, Treasury or a house whose model the repository has not been
   calibrated to *for that policy class*. Tax Foundation sets the corporate
   credit factor (``BET2_corporate_credit_factor.md``), so no Tax Foundation
   corporate row is eligible. Rows must also be expressible by the generic
   path with no new code.
6. **Future rows.** Scores published after :data:`LOCK_DATE` for bills the
   generic path can express enter in the same two steps. That is the part of
   the battery that is prospective in the strict sense.

Honest boundary
---------------
The first four rows were published in July 2026, before the lock, so they are
*sealed* rather than *prospective*: nobody had run this model against them, but
the numbers existed. The window and baseline differences are stated row by
row, not adjusted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cbo_scores import CBOScore, ScoreSource

#: The day the battery opened.
LOCK_DATE = "2026-11-26"

#: The vintage every row here is scored on: the post-P.L. 119-21 baseline,
#: which is the baseline Tax Foundation's *Options 3.0* priced against.
SEALED_VINTAGE = "cbo_feb_2026"

#: Tax Foundation's *Options 3.0* window is calendar 2027-2036. The generic path
#: is scored on the fiscal years 2027-2036, which is the nearest window it can
#: run; the one-quarter offset is stated, not adjusted.
TF_OPTIONS_3_WINDOW_FIRST_YEAR = 2027

#: Top ordinary bracket in 2027 under the February 2026 statutory schedule
#: (``cbo_tax_parameters``, bracket 7, which CBO publishes): single $657,025,
#: joint $788,400. Read by the generic path through
#: ``statutory_bracket_index``; the single figure is the anchor.
TOP_BRACKET_INDEX = 7
TOP_BRACKET_SINGLE_2027 = 657_025.0
TOP_BRACKET_JOINT_2027 = 788_400.0

#: The 20% capital-gains rate threshold for 2026, joint returns: $613,700 of
#: taxable income (Rev. Proc. 2025-32, section 4.03). The capital-gains module
#: reads its threshold on its own SOI income grid, so this is the nearest input
#: it takes. Recorded as a limitation, not adjusted.
CG_TOP_THRESHOLD_JOINT_2026 = 613_700.0

TF_OPTIONS_3 = (
    "Tax Foundation, Options for Reforming America's Tax Code 3.0 (July 2026)"
)


@dataclass(frozen=True)
class SealedCase:
    """One sealed row: the published target, frozen at entry."""

    case_id: str
    score: CBOScore
    #: The page the target was read from, and the day it was read.
    read_from: str
    read_on: str
    entered_date: str
    #: Off at entry; switched on in a later commit (rule 1).
    scoring_enabled: bool = False
    limitations: tuple[str, ...] = field(default_factory=tuple)


def _tf_row(
    *,
    case_id: str,
    option: int,
    title: str,
    ten_year_cost: float,
    url: str,
    policy_type: str,
    rate_change: float,
    income_threshold: float,
    income_threshold_by_filing_status: dict[str, float] | None = None,
    statutory_bracket_index: int | None = None,
    limitations: tuple[str, ...] = (),
) -> SealedCase:
    score = CBOScore(
        policy_id=case_id,
        name=f"Tax Foundation Option {option}: {title}",
        description=title,
        ten_year_cost=ten_year_cost,
        source=ScoreSource.TAX_FOUNDATION,
        source_date="2026-07",
        source_url=url,
        rate_change=rate_change,
        income_threshold=income_threshold,
        income_threshold_by_filing_status=income_threshold_by_filing_status,
        statutory_bracket_index=statutory_bracket_index,
        policy_type=policy_type,  # type: ignore[arg-type]
        baseline_year=2026,
        budget_window="CY2027-2036",
        effective_start_year=TF_OPTIONS_3_WINDOW_FIRST_YEAR,
        scoring_vintage=SEALED_VINTAGE,
        scoring_window_first_year=TF_OPTIONS_3_WINDOW_FIRST_YEAR,
        notes=(
            f"{TF_OPTIONS_3}, Option {option}, topline table: conventional "
            f"primary deficit change over 2027-2036."
        ),
    )
    return SealedCase(
        case_id=case_id,
        score=score,
        read_from=url,
        read_on="2026-11-26",
        entered_date=LOCK_DATE,
        # Switched on in dfc2b9b, the commit after 68a6bfb, which entered the rows.
        scoring_enabled=True,
        limitations=(
            "Tax Foundation's window is calendar 2027-2036; the model scores "
            "fiscal 2027-2036.",
            "Tax Foundation's figure is a primary deficit change: it excludes "
            "interest, as the model's conventional score does.",
            *limitations,
        ),
    )


_TOP_RATE_THRESHOLDS = {"single": TOP_BRACKET_SINGLE_2027, "joint": TOP_BRACKET_JOINT_2027}
_CG_LIMITATION = (
    "The capital-gains module reads its threshold on its SOI income grid, not "
    "on taxable income, so the 20% bracket's $613,700 (joint, 2026) is an "
    "approximation of where the top rate starts."
)

#: The sealed rows, in entry order. Do not edit a target: supersede it.
SEALED_CASES: tuple[SealedCase, ...] = (
    _tf_row(
        case_id="tf3_opt1_top_rate_35",
        option=1,
        title="Lower the Top Marginal Individual Income Tax Rate to 35 Percent",
        ten_year_cost=625.3,
        url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "lower-the-top-marginal-individual-income-tax-rate-to-35/"
        ),
        policy_type="income_tax",
        rate_change=-0.02,
        income_threshold=TOP_BRACKET_SINGLE_2027,
        income_threshold_by_filing_status=_TOP_RATE_THRESHOLDS,
        statutory_bracket_index=TOP_BRACKET_INDEX,
    ),
    _tf_row(
        case_id="tf3_opt4_top_rate_50",
        option=4,
        title="Raise the Top Marginal Individual Income Tax Rate to 50 Percent",
        ten_year_cost=-1_603.8,
        url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "raise-the-top-marginal-individual-income-tax-rate-to-50/"
        ),
        policy_type="income_tax",
        rate_change=0.13,
        income_threshold=TOP_BRACKET_SINGLE_2027,
        income_threshold_by_filing_status=_TOP_RATE_THRESHOLDS,
        statutory_bracket_index=TOP_BRACKET_INDEX,
    ),
    _tf_row(
        case_id="tf3_opt7_cg_top_rate_15",
        option=7,
        title="Lower the Top Tax Rate on Capital Gains and Dividends to 15 Percent",
        ten_year_cost=170.7,
        url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "lower-the-top-tax-rate-on-capital-gains-and-dividends-to-15/"
        ),
        policy_type="capital_gains_tax",
        rate_change=-0.05,
        income_threshold=CG_TOP_THRESHOLD_JOINT_2026,
        limitations=(_CG_LIMITATION,),
    ),
    _tf_row(
        case_id="tf3_opt8_cg_top_rate_30",
        option=8,
        title="Raise the Top Tax Rate on Capital Gains and Dividends to 30 Percent",
        ten_year_cost=-362.5,
        url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "raise-the-top-tax-rate-on-capital-gains-and-dividends-to-30/"
        ),
        policy_type="capital_gains_tax",
        rate_change=0.10,
        income_threshold=CG_TOP_THRESHOLD_JOINT_2026,
        limitations=(_CG_LIMITATION,),
    ),
)

#: Rows that left the battery under rule 3, with the reason. Empty at lock.
RETIRED: dict[str, str] = {}


def sealed_cases(*, enabled_only: bool = False) -> tuple[SealedCase, ...]:
    """The live sealed rows, optionally only those whose scoring is on."""
    rows = tuple(c for c in SEALED_CASES if c.case_id not in RETIRED)
    if enabled_only:
        rows = tuple(c for c in rows if c.scoring_enabled)
    return rows


__all__ = [
    "LOCK_DATE",
    "RETIRED",
    "SEALED_CASES",
    "SEALED_VINTAGE",
    "SealedCase",
    "sealed_cases",
]
