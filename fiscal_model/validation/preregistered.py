"""
Pre-registration manifest for the out-of-sample (Tier 1) validation battery.

Why this file exists
--------------------
Tier 2 of the scorecard is *calibrated*: module parameters are tuned so the
components reproduce a published decomposition, so its low error is expected by
construction. Tier 1 — the "Generic" runner — is the only tier that claims
predictive skill, and a predictive claim is worth nothing unless the target was
fixed **before** the model was allowed to move. This module is the ledger that
makes that auditable.

The discipline
--------------
1. **One row per out-of-sample case**, carrying the official 10-year target, the
   source that published it, the budget baseline *that source* was scored
   against, the commit and date at which the record entered this repository,
   and the commit of the first scoring run.
2. **Targets are immutable.** A manifest target may never be edited to match a
   later model run. If the official number genuinely changes (a re-estimate, a
   corrected transcription), the old row is marked ``superseded_by`` and a new
   row with a **new** ``case_id`` is added. The history stays in the file.
3. **The manifest and the database must agree.** ``assert_preregistered`` fails
   if any live row disagrees with ``KNOWN_SCORES``, or if any Generic scorecard
   entry has no row at all — so a new out-of-sample case cannot be scored
   without first being registered here.
4. **Misses are kept.** A row is never removed because the model scores it
   badly; large errors are documented in ``known_limitations`` and reported.

Honest boundary
---------------
Like ``holdout.py``, this is a *forward* protocol, not a retroactive claim. The
targets below are all previously published numbers, and the rows entered in
Phase A record targets that already existed in the repository or in
``CBO_SCORE_MAP`` before they were ever scored. What the manifest guarantees is
that **from its entry commit onward** the target is frozen and any change is
visible in the diff — not that nobody had ever seen the number.

``entered_commit`` note: a file cannot contain its own commit hash, so rows
added in a change are stamped with that change's hash in the immediately
following commit. ``PHASE_A_COMMIT`` below is the Phase A commit that
introduced this module and the widened battery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cbo_scores import KNOWN_SCORES

#: Commit that introduced this manifest and the widened out-of-sample battery.
PHASE_A_COMMIT = "6c9bfa2b80f8376ef33643e5771e14ebc639b765"
PHASE_A_DATE = "2026-09-01"

#: Commit that first added the validation module and its four original
#: out-of-sample targets (``git log -S 'policy_id="biden_high_income_tax"'``).
VALIDATION_MODULE_COMMIT = "be7e9470e654c20e3b3a8f8aafd8357b175c488a"
VALIDATION_MODULE_DATE = "2025-12-08"

#: Commit that added the Treasury 39.6% + step-up-elimination target.
TREASURY_CAPGAINS_COMMIT = "d11bf2cadd01a2933168af947cc70e0b6180a36e"
TREASURY_CAPGAINS_DATE = "2025-12-31"

#: Commit that entered the CBO *Options for Reducing the Deficit: 2025-2034*
#: battery into this manifest. The rows below were added in that commit and
#: scored for the first time in :data:`PHASE_B_FIRST_SCORED_COMMIT`, which is a
#: *later* commit — the two-commit protocol is what makes "the target was fixed
#: before the model was allowed to move" checkable from the git history rather
#: than asserted in prose.
PHASE_B_ENTERED_COMMIT = "752f0f1b204a2ee9f8b7b987c52b0e19b88e6995"
PHASE_B_ENTERED_DATE = "2026-09-01"

#: Commit in which the Phase B battery was first scored (the commit that flips
#: the 14 records to ``runnable=True`` and adds the vintage/effective-year/
#: payroll plumbing they need).
PHASE_B_FIRST_SCORED_COMMIT = "36d683f9a24f7609d0a179de5f8f36b0ec44a9fc"

#: Commit that entered the Phase D enacted-law component targets (IIJA
#: discretionary, the Fiscal Responsibility Act's discretionary caps, and the
#: Social Security Fairness Act's WEP/GPO repeal) into this manifest. As in
#: Phase B, the rows were added in this commit and first scored in a *later*
#: one, so "the target was fixed before the model was allowed to move" is
#: checkable from the git history rather than asserted in prose.
# Note: the Phase D branch was rebased onto origin/main before review, which
# rewrote these two hashes. They are re-stamped here to the commits that
# actually carry the entry and the first scoring run on the merged history; the
# two-commit ordering they record is unchanged.
PHASE_D_ENTERED_COMMIT = "aed531816f597601a26810ae80fbe5c76fc14a38"
PHASE_D_ENTERED_DATE = "2026-09-01"

#: Commit in which the Phase D enacted-law battery was first scored (the commit
#: that flips those three records to ``runnable=True``).
PHASE_D_FIRST_SCORED_COMMIT = "dca3a50053d0b6727fef116f6a1020efccaad823"

#: The rule that set ``annual_amount_billions`` for every Phase D spending
#: case, fixed before any of them was scored. Written here rather than only in
#: each record's notes because a per-case choice of level would be a knob.
PHASE_D_SPENDING_LEVEL_RULE = (
    "annual_amount_billions = the source's own stated funding or benefit change "
    "for the first fiscal year in which the provision is fully in effect, "
    "excluding any year the source itself describes as carrying retroactive or "
    "transition amounts; grown at the module default 2%/yr. "
    "effective_start_year = the first fiscal year the source's table shows a "
    "non-zero effect, so the model window matches the source's own non-zero "
    "window."
)

#: Commit that entered the IIJA authorization-path row
#: (``iija_2021_discretionary.v2``) into this manifest. As in Phase B and
#: Phase D, the row was added in this commit and first scored in a *later*
#: one: the shape input is frozen in the git history before the mechanism is
#: allowed to read it.
IIJA_AUTHORIZATION_PATH_ENTERED_COMMIT = (
    "1a681183e5b77cc23770f253ee3b7320239f6ced"
)
IIJA_AUTHORIZATION_PATH_ENTERED_DATE = "2026-09-01"

#: Commit in which the authorization-path shape was first scored (the commit
#: that lets ``validation/core.py`` read ``annual_authority_path_billions``).
IIJA_AUTHORIZATION_PATH_FIRST_SCORED_COMMIT = (
    "327a69b61c0424bfb9708e0623787c8fb7641b20"
)

#: The rule that sets every year of IIJA's budget-authority path, fixed before
#: the model was allowed to read it. Written here rather than only in the
#: record's notes because a per-year choice of authority would be a knob.
IIJA_AUTHORIZATION_PATH_RULE = (
    "budget_authority_path = the discretionary budget authority CBO's own cost "
    "estimate states for each fiscal year it names ($162,996M in FY2022, then "
    "$70.1B, $68.5B, $68.1B and $66.2B), with the remainder of the estimate's "
    "stated $446,306M budget-authority total spread evenly over the fiscal "
    "years it describes only as 'about $2B/yr' (FY2027-2031, $2.082B each). "
    "No year is grown, discounted or otherwise adjusted, and the path sums to "
    "the source's own total by construction."
)

#: Commit that entered CBO Option 56's third alternative — the income-tax-only
#: limit on the employer-health exclusion — into this manifest. Option 56 was
#: excluded from the Phase B battery as *leakage*: the only path that could
#: score it was ``cap_employer_health``'s annual, a constant fitted to a
#: published benchmark. Lane L6 replaced that path with a premium distribution
#: and a published expenditure level, so the option became expressible without
#: reading any fitted constant, and this row promotes it. Same two-commit
#: protocol as Phases B and D: the row is entered here and first scored in
#: :data:`OPTION_56_FIRST_SCORED_COMMIT`, a *later* commit.
OPTION_56_ENTERED_COMMIT = "3738ffceba2afb876d3af2e29e2c809693a0112a"
OPTION_56_ENTERED_DATE = "2026-09-02"

#: Commit in which Option 56 was first scored — the commit that adds the
#: ``tax_expenditure`` validation shape and flips the record to
#: ``runnable=True``.
OPTION_56_FIRST_SCORED_COMMIT = "d189a269f4430765ca085cb9d8fa70de0166016b"

#: The rule that fixed Option 56's shape inputs, written down before the
#: option was scored, because a per-case choice of cap would be a knob.
OPTION_56_SHAPE_RULE = (
    "expenditure_caps_by_tier = the dollar limits CBO's own text states for "
    "the alternative being scored, in the year the option takes effect "
    "($10,000 individual and $24,400 family in 2028, the 50th percentile of "
    "2026 premiums indexed with the chained CPI-U). effective_start_year = "
    "the first fiscal year CBO's own table shows a non-zero effect (2028). "
    "The expenditure level the cap is applied to is the published "
    "JCT_TAX_EXPENDITURES annual for the employer-health exclusion, and the "
    "premium distribution's shape is identified from the two percentile "
    "values the same option prints. No parameter is read from, or chosen "
    "against, the -$697B the option is scored on."
)

#: Commit of the Phase E provenance pass (plan §5.1-§5.2): the pass that opened
#: the primary documents and transcribed the rows behind the benchmark targets.
#: It supersedes one out-of-sample row — ``biden_capital_gains_39`` — because
#: its -$456B target turned out to appear in no Treasury volume. A *re-sourced*
#: target is exactly the case the "new row, never an edit" rule exists for: the
#: old row and the reason it went are both still in this file.
PHASE_E_PROVENANCE_COMMIT = "0bcfbc3b4ba1e4a73864369d8f50f3bb6528efe5"
PHASE_E_PROVENANCE_DATE = "2026-09-01"

#: Commit of the Wave 4 provenance pass, which supersedes one out-of-sample
#: row: ``biden_high_income_tax``. Phase E transcribed the Green Book row this
#: target is credited to and found it prints $245,924 million against the
#: -$252B the manifest froze, then deliberately left it, because a Tier 1
#: target may only move through a new manifest row and that is an owner
#: decision rather than a bookkeeping one. This is that decision. As in
#: Phase B and Phase D the row is entered here and first scored in a *later*
#: commit, so "the target was fixed before the model was scored against it"
#: is checkable from the git history rather than asserted in prose.
WAVE4_PROVENANCE_ENTERED_COMMIT = (
    "318be6bea12f92ae02300e0a5da6b84b98a6bff0"
)
WAVE4_PROVENANCE_ENTERED_DATE = "2026-09-02"

#: Commit in which the Wave 4 out-of-sample target was first actually scored
#: (the commit that writes $245.9B into ``KNOWN_SCORES``).
WAVE4_PROVENANCE_FIRST_SCORED_COMMIT = (
    "22ccdd24182f5e319eebb16caf7128ed8e6537b2"
)

#: Commit that entered the FY2022 Green Book window row
#: (``treasury_capgains_39_plus_stepup_elim.v2``) into this manifest. Same
#: two-commit protocol as Phases B and D and as the IIJA authorization path,
#: and the same *kind* of change as that one: the shape input moves and the
#: published target does not. The row is added here and first scored in
#: :data:`FY2022_WINDOW_FIRST_SCORED_COMMIT`, a *later* commit.
FY2022_WINDOW_ENTERED_COMMIT = "2353f83206a25f9ef5df524c2b476fcc0823bb95"
FY2022_WINDOW_ENTERED_DATE = "2026-09-06"

#: Commit in which the FY2022 window was first scored (the commit that lets
#: ``validation/core.py`` read ``scoring_window_first_year``).
FY2022_WINDOW_FIRST_SCORED_COMMIT = (
    "804e5521bd8d69128f78204a047b47cb07dae16b"
)

#: The rule that sets the scoring window for every case that carries one,
#: fixed before the model was allowed to read it. Written here rather than only
#: in the record's notes because a per-case choice of decade would be a knob.
FY2022_TARGET_WINDOW_RULE = (
    "scoring_window_first_year = the first fiscal year of the window the "
    "source's own published total covers, as already transcribed into the "
    "record's ``budget_window``. It is read for one purpose - to open the "
    "model's ten-year window in that year, so the ten fiscal years scored are "
    "the ten the target covers - and it moves the policy's start year with it, "
    "because moving the window alone truncates the head of the path instead of "
    "shifting it. A record that states an ``effective_start_year`` keeps it: "
    "that is the year the source says the policy takes effect, which is a "
    "different fact. No year is chosen against an error, and no target moves."
)

#: Commit that entered the IIJA window row (``iija_2021_discretionary.v3``)
#: into this manifest. Owner decision (3) of
#: ``planning/HIGH_STAKES_ACCURACY.md`` section 4, applying
#: :data:`FY2022_TARGET_WINDOW_RULE` to the second row that carries a window
#: its own source published and the model does not score on. Same two-commit
#: protocol as every shape-input change before it, and the same *kind* of
#: change as ``.v2`` was: the shape input moves and the published target does
#: not. The row is added here and first scored in
#: :data:`IIJA_WINDOW_FIRST_SCORED_COMMIT`, a *later* commit.
IIJA_WINDOW_ENTERED_COMMIT = "97cc6a6f41148b3c887f0660c8e67ebf6fa85063"
IIJA_WINDOW_ENTERED_DATE = "2026-09-11"

#: Commit in which the IIJA window was first scored (the commit that writes
#: ``scoring_window_first_year=2022`` onto the ``KNOWN_SCORES`` record).
IIJA_WINDOW_FIRST_SCORED_COMMIT = "2cde296698702e0361b13661d152a150aa922c19"

#: Commit that entered lane R2's provenance decisions — the five Tier 1 rows
#: whose targets carried no source URL (``planning/ROUTE_TO_8_5.md`` §1 R2,
#: ``planning/lanes/R2_tier1_secondhand_targets.md``). One target moves onto a
#: published line item (``illustrative_1pp_all``) and four are withdrawn, each
#: with its search recorded. Same two-commit protocol as every target change
#: before it: the rows are written here and first scored in
#: :data:`R2_SECONDHAND_FIRST_SCORED_COMMIT`, a *later* commit, so "the target
#: was fixed before the model was scored against it" is checkable from the git
#: history rather than asserted in prose.
R2_SECONDHAND_ENTERED_COMMIT = "1ada9021a5f8690c5cc385a6ee977833509abbc4"
R2_SECONDHAND_ENTERED_DATE = "2026-09-11"

#: Commit in which R2's decisions were first scored — the commit that writes
#: -$1,081.3B into ``KNOWN_SCORES`` and flips the four withdrawn records to
#: ``runnable=False``.
R2_SECONDHAND_FIRST_SCORED_COMMIT = "7d5d751de384a50940d4c348dc311bc9b022b9b6"

#: The rule R2 bound itself to before it opened a document, written here rather
#: than only in each record's ``retired_reason`` because "which rows did we
#: withdraw?" is the question a reader of a shrinking battery asks first.
R2_RETIREMENT_RULE = (
    "A Tier 1 row is withdrawn if and only if its target cannot be traced to "
    "any published document - never because of the size of its error. The two "
    "are independent, and medicare_surcharge_2pp is the proof: its 2pp model "
    "output sits 4.6% from the 1.2pp figure Treasury actually prints, so the "
    "row would have looked accurate on the document it is withdrawn for "
    "missing. A row whose target exists is kept however badly it scores "
    "(cbo_opt64_corporate_rate_1pp at 44.5% is the tier's worst and is not at "
    "risk), and a row whose target does not exist is withdrawn however well it "
    "scores. Where a document argues for a different *shape*, R2 publishes the "
    "restated figure and leaves the new row to the owner: a provenance lane "
    "may not move a model output by implication."
)

#: Commit that entered lane R3's battery — the 22 rows from the three CBO
#: *Options for Reducing the Deficit* volumes the battery did not contain
#: (``planning/ROUTE_TO_8_5.md`` §1 R3, ``planning/lanes/R3_tier1_battery.md``).
#: Same two-commit protocol as Phase B: the rows are written here and into
#: ``KNOWN_SCORES`` with ``runnable=False`` in this commit, and first scored in
#: :data:`R3_MULTI_VOLUME_FIRST_SCORED_COMMIT`, a *later* commit, so "the target
#: was fixed before the model was scored against it" is checkable from the git
#: history rather than asserted in prose.
R3_MULTI_VOLUME_ENTERED_COMMIT = "a76d0b4c35ee7c5c4e3d54bd52d4e30b1f0ec1ab"
R3_MULTI_VOLUME_ENTERED_DATE = "2026-09-11"

#: Commit in which lane R3's battery was first scored — the commit that flips
#: those 22 records to ``runnable=True`` and admits a window-carrying record to
#: the Generic dispatch.
R3_MULTI_VOLUME_FIRST_SCORED_COMMIT = "cfa6d99fc0a0fbfa0ac57dbe31d1c9dbd0f6e1b2"

#: The rule R3 bound itself to **before** it read a figure into a record.
#:
#: Written here rather than only in the lane doc because "which options did you
#: take, and why those?" is the first question a reader of a battery that
#: doubled in size asks — and because the answer has to be a rule rather than a
#: list, or the battery is a curated set of flattering shapes. The verdict for
#: every one of the 100 revenue options in the three volumes is in
#: ``fiscal_model/data_files/validation/cbo_options_multi_volume.csv``.
#:
#: Two consequences worth stating beside it. **Spending options are out of scope
#: in all three volumes**, and not because of fit: ``discretionary_spending`` is
#: already at n = 5 and is the battery's most accurate class, so excluding it can
#: only *raise* the reported mean. And **one reform, one row**: the 2022 volume's
#: Option 13 alternative 1 is already registered as ``illustrative_1pp_all.v2``
#: (lane R2 superseded it onto that very line), so it is recorded in the
#: alternatives CSV as not-registered rather than entered twice.
R3_SELECTION_RULE = (
    "From each of the three CBO Options for Reducing the Deficit volumes the "
    "battery does not already contain - 2018 (pub. 54667, FY2019-2028), 2020 "
    "(pub. 56783, FY2021-2030) and 2022 (pubs. 58164 and 58163, FY2023-2032) - "
    "take every REVENUE option whose reform is one of the six shapes "
    "create_policy_from_score already builds, and every alternative reported "
    "inside it. The six shapes: an ordinary-income rate change at a stated "
    "boundary; an AGI-inclusive surtax at a stated boundary; a long-term "
    "capital gains / qualified dividend rate change; a statutory corporate rate "
    "change; a flat rate on uncapped covered earnings; and a limit on the "
    "income-tax exclusion for employment-based health insurance. An option or "
    "alternative is excluded only where the shape does not exist or where a "
    "module constant fitted to that same reform sits in the path (leakage) - "
    "never for its answer."
)

#: Baselines the CBO options were built on, from PDF page 2 of publication
#: 60557 ("Notes About This Report").
CBO_OPTIONS_REVENUE_BASELINE = (
    "CBO February 2024 baseline (The Budget and Economic Outlook: 2024 to 2034, "
    "pub. 59710) - matched exactly by BaselineVintage.CBO_FEB_2024"
)
CBO_OPTIONS_SPENDING_BASELINE = (
    "CBO June 2024 baseline (An Update to the Budget and Economic Outlook: "
    "2024 to 2034, pub. 60039) - VINTAGE MISMATCH: the repository has no "
    "June-2024 vintage, so this row is scored on CBO_FEB_2024"
)


@dataclass(frozen=True)
class PreregisteredCase:
    """One pre-registered out-of-sample target.

    Attributes:
        case_id: Unique manifest row id. Stable forever; a revised target gets
            a *new* row with a new id rather than an edit.
        policy_id: The ``KNOWN_SCORES`` key this row registers.
        official_10yr_billions: The frozen official 10-year target ($B,
            positive = increases the deficit).
        source_name: Publishing organization.
        source_url: Link to the published estimate, or ``None`` when the
            repository only ever carried a secondhand figure.
        source_date: Publication date as carried by the source record.
        source_baseline_vintage: The budget baseline *the source* scored
            against. Recorded because the model scores everything on its own
            current baseline today; vintage matching is Phase D.
        entered_commit: Commit at which the record entered this repository.
        entered_date: ISO date of ``entered_commit``.
        first_scoring_run_commit: Commit at which the target was first actually
            scored by a validation runner.
        superseded_by: ``case_id`` of the row that replaced this one, if any.
            A row with a value here is history and is not checked against
            ``KNOWN_SCORES``.
        retired: ``True`` when the target could not be traced to any published
            source and the case has been withdrawn from the battery rather
            than replaced. Retired rows stay in the file — the point is that
            the withdrawal is visible — but they are not live, are not scored,
            and are excluded from every Tier 1 count.
        retired_reason: Why the row was withdrawn, including what was searched.
        note: Free text — provenance caveats, why a row was superseded.
    """

    case_id: str
    policy_id: str
    official_10yr_billions: float
    source_name: str
    source_url: str | None
    source_date: str
    source_baseline_vintage: str
    entered_commit: str
    entered_date: str
    first_scoring_run_commit: str
    superseded_by: str | None = None
    retired: bool = False
    retired_reason: str = ""
    note: str = ""

    @property
    def is_live(self) -> bool:
        """A row still in force: not replaced by a later row, not withdrawn."""
        return self.superseded_by is None and not self.retired


PREREGISTERED_CASES: tuple[PreregisteredCase, ...] = (
    # ---- Original four (entered 2025-12-08, scored from that commit on) ----
    PreregisteredCase(
        case_id="illustrative_1pp_all.v1",
        policy_id="illustrative_1pp_all",
        official_10yr_billions=-960.0,
        source_name="Joint Committee on Taxation",
        source_url=None,
        source_date="2023-01",
        source_baseline_vintage="CBO Feb 2023 baseline (FY2023-2032); JCT rule-of-thumb, no line item",
        entered_commit=VALIDATION_MODULE_COMMIT,
        entered_date=VALIDATION_MODULE_DATE,
        first_scoring_run_commit=VALIDATION_MODULE_COMMIT,
        superseded_by="illustrative_1pp_all.v2",
        note=(
            "Uniform 1pp on all brackets. Ordinary-income base. SUPERSEDED by "
            "lane R2: -$960B was a rule of thumb ('1pp = $85-100B/year') that "
            "appears in no JCT document, and the reform it describes is "
            "published - four times, in four CBO Options volumes, each of them "
            "a JCT estimate. The volume matching this record's own stated "
            "source, window and vintage prints -$1,081.3B."
        ),
    ),
    PreregisteredCase(
        case_id="illustrative_1pp_all.v2",
        policy_id="illustrative_1pp_all",
        official_10yr_billions=-1_081.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (FY2023-2032 window)"
        ),
        entered_commit=R2_SECONDHAND_ENTERED_COMMIT,
        entered_date=R2_SECONDHAND_ENTERED_DATE,
        first_scoring_run_commit=R2_SECONDHAND_FIRST_SCORED_COMMIT,
        note=(
            "CBO, Options for Reducing the Deficit: 2023 to 2032, Volume I: "
            "Larger Reductions (December 2022, publication 58164), Option 13 - "
            "Revenues, 'Increase Individual Income Tax Rates', first "
            "alternative: 'Raise all tax rates on ordinary income by "
            "1 percentage point', -$1,081.3B over FY2023-2032 (report p. 72; "
            "PDF p. 76). Annual path -72.4 / -106.6 / -111.3 / -102.1 / "
            "-102.2 / -107.4 / -112.0 / -117.0 / -122.3 / -127.9; five-year "
            "subtotal -494.6. 'Data source: Staff of the Joint Committee on "
            "Taxation', which is why this row keeps source_name=JCT rather "
            "than becoming a CBO row. The volume's own words for the "
            "alternative - 'in 2023, the top rate of 37 percent would increase "
            "to 38 percent, and in 2026, the top rate of 39.6 percent would "
            "increase to 40.6 percent' - are the ordinary-income base this "
            "record already declares. "
            ""
            "TWO THINGS THIS ROW IS NOT. It is not a duplicate of "
            "cbo_opt45_all_rates_1pp: that row is the same option in the "
            "*2025-2034* volume at -$1,185.3B, and CBO's own two editions "
            "differ by $104.0B (9.6%) for one unchanged reform, which is the "
            "size of a decade. It is not scored on its target's decade either: "
            "the runner opens its window in FY2025, so about that $104.0B of "
            "this row's residual is the window rather than the model. "
            "FY2022_TARGET_WINDOW_RULE exists for exactly this and would set "
            "scoring_window_first_year=2023 - but applying it moves a model "
            "output, which R2 may not do, so the figure is published here and "
            "the .v3 decision is the owner's. " + R2_RETIREMENT_RULE
        ),
    ),
    PreregisteredCase(
        case_id="illustrative_top_rate_5pp.v1",
        policy_id="illustrative_top_rate_5pp",
        official_10yr_billions=-700.0,
        source_name="Tax Policy Center",
        source_url=None,
        source_date="2023-06",
        source_baseline_vintage="CBO Feb 2023 baseline (FY2023-2032), as reported",
        entered_commit=VALIDATION_MODULE_COMMIT,
        entered_date=VALIDATION_MODULE_DATE,
        first_scoring_run_commit=VALIDATION_MODULE_COMMIT,
        retired=True,
        retired_reason=(
            "Lane R2. -$700B for a +5pp top rate above $1,000,000 is in no "
            "publication. Phase E enumerated TPC's entire sitemap for it - 11 "
            "sub-sitemaps, ~20,600 URLs, ~6,500 model-estimate pages, none of "
            "the 82 t23-* tables a top-rate table - and R2 added the other "
            "half of the search: the individual-rate option of ALL FOUR CBO "
            "Options volumes (2018 pub. 54667 Option 1; 2020 pub. 56783 Option "
            "1; 2022 pub. 58164 Option 13; 2024 pub. 60557 Option 45), every "
            "alternative of which is a uniform change at a *bracket* boundary "
            "or an AGI surtax at the standard deduction, the fourth-bracket "
            "floor, $20,000/$40,000 or $100,000/$200,000. No scorekeeper "
            "prices a rate change at a $1,000,000 threshold at all. The "
            "record's own name and notes call it 'Illustrative', which is the "
            "repository describing its own synthetic figure. Withdrawn rather "
            "than corrected, because there is nothing to correct it to: the "
            "nearest published quantities are PWBM's new 39.6% bracket above "
            "$1M at $222.4B (FY2026-2035, a ~2.6pp change on the same "
            "threshold) and TPC T19-0037 Option 3's 10pp AGI surtax above $2M "
            "married / $1M other at $633.897B (FY2019-2029), and neither is "
            "this reform. top_rate_45.v1 is the precedent, and "
            "docs/VALIDATION.md has listed this row beside it as an open owner "
            "decision since Phase E; ROUTE_TO_8_5.md §1 R2 is the plan that "
            "names it, so the decision is now taken rather than deferred. "
            + R2_RETIREMENT_RULE
        ),
        note="AGI-inclusive base (target includes the preferential LTCG/QDIV portion).",
    ),
    PreregisteredCase(
        case_id="illustrative_500k_2pp.v1",
        policy_id="illustrative_500k_2pp",
        official_10yr_billions=400.0,
        source_name="Tax Policy Center",
        source_url=None,
        source_date="2023-06",
        source_baseline_vintage="CBO Feb 2023 baseline (FY2023-2032), as reported",
        entered_commit=VALIDATION_MODULE_COMMIT,
        entered_date=VALIDATION_MODULE_DATE,
        first_scoring_run_commit=VALIDATION_MODULE_COMMIT,
        retired=True,
        retired_reason=(
            "Lane R2. +$400B for a 2pp rate CUT above $500,000 is in no "
            "publication, and the search is short for a structural reason "
            "worth writing down: CBO's Options volumes are deficit-REDUCTION "
            "menus and contain no rate cut at all, in any of the four editions "
            "(2018, 2020, 2022, 2024), so three quarters of the natural search "
            "space cannot contain this row by construction. JCT scores cuts "
            "only as estimates of enacted or introduced bills, none of which "
            "is a 2pp cut at a $500,000 floor; Phase E's full TPC sitemap "
            "enumeration found no table for it either. The record calls itself "
            "'Illustrative estimate'. "
            ""
            "WHAT THE BATTERY LOSES, STATED SO IT IS NOT LOST QUIETLY: this is "
            "the tier's only rate CUT and the only row with a positive target, "
            "so after this retirement every Tier 1 revenue row is an increase, "
            "and the battery no longer tests the model in the direction a user "
            "of the Tailor page most often asks about. That is a real cost of "
            "being honest about the target, and the replacement is a scored "
            "cut with a document - R3's `leg_rev_*` series in CBO's own "
            "revenue-detail file carry the annual revenue effect of every "
            "major act since 1981, several of them cuts. Carried over there "
            "rather than fixed here, because registering a new case is a "
            "different lane. " + R2_RETIREMENT_RULE
        ),
        note="AGI-inclusive base. Rate cut, so the target is a cost.",
    ),
    PreregisteredCase(
        case_id="biden_high_income_tax.v1",
        policy_id="biden_high_income_tax",
        official_10yr_billions=-252.0,
        source_name="U.S. Treasury",
        source_url=(
            "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
        ),
        source_date="2024-03",
        source_baseline_vintage="Administration FY2025 Budget baseline (Green Book FY2025)",
        entered_commit=VALIDATION_MODULE_COMMIT,
        entered_date=VALIDATION_MODULE_DATE,
        first_scoring_run_commit=VALIDATION_MODULE_COMMIT,
        superseded_by="biden_high_income_tax.v2",
        note=(
            "Same target as the 'Biden 2025 Proposal' entry in CBO_SCORE_MAP; registered "
            "once so the prediction is not double-counted. Treasury describes it as "
            "'combined with other provisions', so the target is itself a bundled figure. "
            "SUPERSEDED in Wave 4: the Green Book row this record cites prints $245,924 "
            "million, not $252,000 million. Phase E transcribed the row (report p. 242; "
            "PDF p. 250) and left the manifest alone because a frozen out-of-sample "
            "target may only move through a new row. The 'combined with other "
            "provisions' caveat in this note also turns out to be wrong about the "
            "table: Treasury prints the top-rate increase as its own line."
        ),
    ),
    PreregisteredCase(
        case_id="biden_high_income_tax.v2",
        policy_id="biden_high_income_tax",
        official_10yr_billions=-245.9,
        source_name="U.S. Treasury",
        source_url=(
            "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
        ),
        source_date="2024-03",
        source_baseline_vintage="Administration FY2025 Budget baseline (Green Book FY2025)",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        note=(
            "Treasury, General Explanations of the Administration's FY2025 Revenue "
            "Proposals, Table of Revenue Estimates, row 'Increase the top marginal "
            "income tax rate for high-income earners': $245,924 million over "
            "FY2025-2034 (report p. 242; PDF p. 250). The proposal text (report p. 78) "
            "matches the shape the Generic runner scores exactly -- 39.6% on taxable "
            "income over $450,000 married / $400,000 unmarried, C-CPI-U indexed after "
            "2024 -- so this is a re-sourcing of the same design, not a change of "
            "policy. Nothing in the model reads it: the case is scored bottom-up from "
            "SOI filer counts with ETI 0.25 and the ordinary-income base, exactly as "
            "before. The FY2024 Green Book prints $235,263M for the same row over "
            "FY2024-2033, which is the check that the row is stable across vintages "
            "rather than a one-off. Moving the target improves this case's reported "
            "error (-252.0 -> -245.9 against an unchanged model), and that is a "
            "consequence of the correction rather than a reason for it: the same "
            "transcription pass moved seven Tier 2 targets *away* from their models."
        ),
    ),
    # ---- Phase A promotions: capital gains (previously stranded) ----------
    PreregisteredCase(
        case_id="biden_capital_gains_39.v1",
        policy_id="biden_capital_gains_39",
        official_10yr_billions=-456.0,
        source_name="U.S. Treasury",
        source_url=(
            "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
        ),
        source_date="2024-03",
        source_baseline_vintage="Administration FY2025 Budget baseline (Green Book FY2025)",
        entered_commit=VALIDATION_MODULE_COMMIT,
        entered_date=VALIDATION_MODULE_DATE,
        first_scoring_run_commit=PHASE_A_COMMIT,
        superseded_by="biden_capital_gains_39.v2",
        note=(
            "Record existed from 2025-12-08 but was unreachable: get_validation_targets() "
            "kept only policy_type == 'income_tax'. First scored in Phase A on the "
            "uncalibrated capital-gains path with frozen module-default elasticities. "
            "SUPERSEDED in Phase E: -$456B appears in no Treasury volume. The FY2025 "
            "Green Book's combined 'Reform the taxation of capital income' row is "
            "$288,583M (report p. 242; PDF p. 250), and Treasury never splits the rate "
            "change from the realization-at-death change, so there is no decomposition "
            "-456 could have been assembled from. Phase A flagged this row and its "
            "FY2022 twin as 42% apart for one policy shape; opening the document is "
            "what resolved it."
        ),
    ),
    PreregisteredCase(
        case_id="biden_capital_gains_39.v2",
        policy_id="biden_capital_gains_39",
        official_10yr_billions=-288.6,
        source_name="U.S. Treasury",
        source_url=(
            "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
        ),
        source_date="2024-03",
        source_baseline_vintage="Administration FY2025 Budget baseline (Green Book FY2025)",
        entered_commit=PHASE_E_PROVENANCE_COMMIT,
        entered_date=PHASE_E_PROVENANCE_DATE,
        first_scoring_run_commit=PHASE_E_PROVENANCE_COMMIT,
        note=(
            "Re-sourced target: FY2025 Green Book, Table of Revenue Estimates, "
            "'Reform the taxation of capital income', $288,583M over FY2025-2034. "
            "The *shape* was corrected to the source's own definition rather than the "
            "number being fitted to the model: the threshold is taxable income over "
            "$1M (the FY2022 volume says AGI), and the exclusion for gains at death is "
            "$5M per donor, portable to $10M per couple (report p. 89), where the "
            "module default and the FY2022 proposal are $1M per person. Nothing else "
            "moved; the frozen 0.8/0.4 elasticities still apply."
        ),
    ),
    PreregisteredCase(
        case_id="treasury_capgains_39_plus_stepup_elim.v1",
        policy_id="treasury_capgains_39_plus_stepup_elim",
        official_10yr_billions=-322.0,
        source_name="U.S. Treasury",
        source_url=None,
        source_date="2021-05",
        source_baseline_vintage="Administration FY2022 Budget baseline (Green Book FY2022)",
        entered_commit=TREASURY_CAPGAINS_COMMIT,
        entered_date=TREASURY_CAPGAINS_DATE,
        first_scoring_run_commit=PHASE_A_COMMIT,
        superseded_by="treasury_capgains_39_plus_stepup_elim.v2",
        note=(
            "Structurally identical to biden_capital_gains_39 (39.6% above $1M plus "
            "step-up elimination) but published against a different baseline and three "
            "years earlier; the two official targets differ by 42%. "
            "SUPERSEDED 2026-09-06: this row was scored over FY2025-2034 against a "
            "target published over FY2022-2031, and both of the shape's channels grow "
            "at 5.80%/yr, so 28.7 of its 43.3 points were the window rather than the "
            "model. Its -$461.5B / 43.3% stays on the record here."
        ),
    ),
    # ---- The FY2022 Green Book's own window (entered, then scored) --------
    PreregisteredCase(
        case_id="treasury_capgains_39_plus_stepup_elim.v2",
        policy_id="treasury_capgains_39_plus_stepup_elim",
        official_10yr_billions=-322.0,
        source_name="U.S. Treasury",
        source_url=(
            "https://home.treasury.gov/system/files/131/General-Explanations-FY2022.pdf"
        ),
        source_date="2021-05",
        source_baseline_vintage="Administration FY2022 Budget baseline (Green Book FY2022)",
        entered_commit=FY2022_WINDOW_ENTERED_COMMIT,
        entered_date=FY2022_WINDOW_ENTERED_DATE,
        first_scoring_run_commit=FY2022_WINDOW_FIRST_SCORED_COMMIT,
        note=(
            "**The target does not change.** This row replaces v1's *shape "
            "input*, not Treasury's $322,485M: the official number, the source, "
            "the document and the window are all identical, and the window is "
            "the point. v1 was scored over FY2025-2034 because the runner has "
            "one window and no case could name its own; the target is the "
            "FY2022 Green Book's 'Reform the taxation of capital income' row "
            "over FY2022-2031 (report p. 105; PDF p. 111, transcribed to the "
            "annual in planning/memos/FY2022_TARGET_WINDOW.md). Both of this "
            "shape's channels grow with household net worth at 5.80%/yr - the "
            "rate channel through realizations_projection_factor, the death "
            "channel through gains_at_death_billions - so a decade three years "
            "later scores higher mechanically: -$461.5B against -$369.0B on the "
            "target's own decade, 28.7 of the row's 43.3 points. Scoring it "
            "there needs no 2021 baseline, because the capital-gains shape "
            "reads none (estimate_static_revenue_effect opens '_ = "
            "baseline_revenue'); what was missing was a window, not a vintage. "
            "The source_url is also filled in, where v1 carried None. What is "
            "left at 14.6% is a shape disagreement rather than an accounting "
            "one, and the memo sizes it: Treasury books -$66.0B over FY2022-24 "
            "where the model books -$6.1B, because the model's enactment year "
            "is a $59.8B revenue loss from the transitory response against "
            "Treasury's $7.7B gain. " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    # ---- Phase A promotions: preset-backed surtax / top-rate targets ------
    PreregisteredCase(
        case_id="warren_ultramillionaire_surtax_3pp.v1",
        policy_id="warren_ultramillionaire_surtax_3pp",
        official_10yr_billions=-350.0,
        source_name="Tax Policy Center",
        source_url="https://www.taxpolicycenter.org/",
        source_date="2020",
        source_baseline_vintage="unstated (secondhand 'TPC-range' figure carried in CBO_SCORE_MAP)",
        entered_commit=PHASE_A_COMMIT,
        entered_date=PHASE_A_DATE,
        first_scoring_run_commit=PHASE_A_COMMIT,
        retired=True,
        retired_reason=(
            "Lane R2. TPC's *AGI Surtax Options* simulation was read in full: "
            "thirteen tables (T19-0037 through T19-0050), every one of them a "
            "**10 percent** surtax, and exactly one revenue table among them. "
            "T19-0037 (23 September 2019, Urban-Brookings Microsimulation "
            "Model version 0319-1) prices three options over FY2019-2029 - "
            "$585.325B for 10pp on AGI above $2,000,000 unindexed, $500.635B "
            "at a $2.5M threshold, $633.897B at $2M married / $1M other. There "
            "is no 3pp row, here or anywhere: no CBO Options volume prices a "
            "surtax at a $2M threshold in any of its four editions. Scaling "
            "$585.325B to 3pp would be CONSTRUCTING a target, which "
            "PROVENANCE_corporate_ptc.md already refused in as many words "
            "('summing two rows of PWBM's table would be constructing a target "
            "rather than reading one'), and the arithmetic would not be linear "
            "anyway - CBO warns that 'the deficit effects of large rate "
            "increases or surtaxes might not be proportional to the estimates "
            "shown here'. "
            ""
            "AND THE ROW'S NAME IS WRONG, WHICH IS THE SHARPER FINDING. "
            "Senator Warren's Ultra-Millionaire Tax Act is a **wealth** tax on "
            "net worth - 2% above $50 million, 3% above $1 billion - not an "
            "income surtax. The '3pp' is the billionaire *wealth* rate "
            "transplanted onto an AGI base and the '$2M' is a threshold from a "
            "different proposal entirely, so this row's shape corresponds to "
            "no proposal anybody has scored, which is why no search could have "
            "found its target. What R2 leaves for the owner: T19-0037 Option 1 "
            "is the same base and the same threshold at a different rate, so a "
            "new case scoring a 10pp shape against $585.325B is registrable "
            "and would be a genuine TPC line item - but it needs a shape "
            "change, and a provenance lane may not move a model output. "
            + R2_RETIREMENT_RULE
        ),
        note=(
            "Shipped as a sidebar preset with an official number but no runner. "
            "Provenance is weak (bare homepage URL, year only) — Phase E should replace "
            "it with a line item or demote it. R2 demoted it."
        ),
    ),
    PreregisteredCase(
        case_id="top_rate_45.v1",
        policy_id="top_rate_45",
        official_10yr_billions=-420.0,
        source_name="Tax Policy Center",
        source_url="https://www.taxpolicycenter.org/",
        source_date="2023",
        source_baseline_vintage="unstated (secondhand 'TPC-range' figure carried in CBO_SCORE_MAP)",
        entered_commit=PHASE_A_COMMIT,
        entered_date=PHASE_A_DATE,
        first_scoring_run_commit=PHASE_A_COMMIT,
        retired=True,
        retired_reason=(
            "Phase E: -$420B is not a published figure. TPC's sitemap was "
            "enumerated in full (11 sub-sitemaps, ~20,600 URLs, ~6,500 "
            "model-estimate pages) and the only '45 percent' tables are for the "
            "estate-tax top rate and an EITC phase-in rate; TPC's 82 t23-* "
            "tables contain no top-rate table at all, and its top-rate "
            "collections are all pre-2010 vintage (36% / 39.6% / 37.5%). "
            "CBO and JCT publish no +8pp top-bracket option and CBO warns that "
            "'the deficit effects of large rate increases or surtaxes might not "
            "be proportional to the estimates shown here'. The nearest real "
            "published analogues, PWBM (May 2025, FY2026-2035), bracket the "
            "range at $401.6B for reverting the top bracket to 39.6% and "
            "$222.4B for a new 39.6% bracket above $1M — which makes -$420B for "
            "+8pp above $609,350 implausibly low, the opposite direction from "
            "the model's -$916B. Withdrawn rather than corrected: there is no "
            "figure to correct it to. Phase A registered this row precisely so "
            "that its removal would have to be explicit."
        ),
        note=(
            "Phase A kept this despite a 118% miss and flagged that the target "
            "fails an internal coherence check against illustrative_top_rate_5pp "
            "(same claimed source: +5pp above $1M = -$700B). Phase E resolved the "
            "incoherence in the direction Phase A did not expect: *neither* "
            "figure exists. -$700B is equally untraceable and is listed in "
            "docs/VALIDATION.md as an open owner decision; only this row, which "
            "the plan named, is withdrawn here."
        ),
    ),
    PreregisteredCase(
        case_id="medicare_surcharge_2pp.v1",
        policy_id="medicare_surcharge_2pp",
        official_10yr_billions=-310.0,
        source_name="U.S. Treasury",
        source_url=(
            "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
        ),
        source_date="2024",
        source_baseline_vintage="Administration FY2025 Budget baseline (Green Book FY2025)",
        entered_commit=PHASE_A_COMMIT,
        entered_date=PHASE_A_DATE,
        first_scoring_run_commit=PHASE_A_COMMIT,
        retired=True,
        retired_reason=(
            "Lane R2, and this row is the test of R2_RETIREMENT_RULE rather "
            "than an easy application of it. Treasury's FY2025 Green Book was "
            "read page by page. The proposal this record names is there, and "
            "it is a **1.2 percentage point** increase - 'The proposal would "
            "increase the additional Medicare tax rate by 1.2 percentage "
            "points for taxpayers with more than $400,000 of earnings... "
            "bringing the marginal Medicare tax rate up to 5 percent', and the "
            "same 1.2pp on the NIIT (report pp. 76-77; PDF pp. 84-85). Its "
            "revenue row, 'Increase the net investment income tax rate and "
            "additional Medicare tax rate for high-income taxpayers', prints "
            "**$403,790M** over FY2025-2034 (report p. 242; PDF p. 250; "
            "FY2025-29 subtotal $178,466M). The FY2024 volume prints "
            "**$344,371M** over FY2024-2033 for the identical proposal (report "
            "p. 213-equivalent; PDF p. 221), and the FY2023 volume has no such "
            "proposal at all. -$310.0B is none of these. The nearest figures "
            "anywhere in the FY2025 volume are the child-credit expansion at "
            "**-$310,024M** - 0.008% away, and a *cost*, the opposite sign to "
            "the raiser this row scores - and the FY2024 pass-through NIIT row "
            "at $305,944M, which is a base expansion rather than a rate "
            "change. Neither coincidence is evidence of where the figure came "
            "from; what they establish is that it is not the proposal's. "
            ""
            "WHY THIS ROW PROVES THE RULE RATHER THAN BENDING TO IT. The model "
            "scores -$408.6B here, which is **1.2% from Treasury's published "
            "$403,790M**, so adopting that figure would have turned the tier's "
            "third-worst row into one of its best in a single line of diff. It "
            "is not adopted, because the model applies **2pp** where the "
            "document applies **1.2pp** - 1.67x the rate - and a small error "
            "bought by a rate mismatch is two errors cancelling, which is the "
            "reading Wave 4 gave treasury_capgains_39_plus_stepup_elim's 0.2% "
            "and Wave 7 gave cbo_opt46_agi_surtax_2pp_100k's 16.1%. The static "
            "path is linear in rate_change, so restating the model on the "
            "document's own rate gives -$408.6 x 0.6 = **-$245.2B against "
            "-$403.8B, 39.3% under** - which is what this row's accuracy "
            "actually is, and it is worse than the 31.8% it was reporting. "
            "PR #144 saw the shadow of this and said so: 'a row cannot sit "
            "within 1.5% of a published figure on a base held three years "
            "stale unless something else over-states by about as much.' "
            ""
            "WHAT IS LEFT FOR THE OWNER: a .v2 registering -$403.8B with "
            "rate_change=0.012 is a genuine Treasury line item and would be "
            "the right row. It moves a model output, so R2 may not take it. "
            "Note also the base: the statutory base is wages plus net "
            "investment income, which is neither SOI column (PR #146 finding "
            "3), so a .v2 inherits an open base question this retirement does "
            "not close. " + R2_RETIREMENT_RULE
        ),
        note="AGI-inclusive base: the surcharge applies to wage *and* investment income.",
    ),

    # ---- Phase B: CBO Options for Reducing the Deficit, 2025-2034 ---------
    # Publication 60557 (December 2024; reposted October 2025). 76 options, of
    # which 14 alternatives are expressible by the uncalibrated path; the other
    # 62 options carry a one-line exclusion reason in
    # ``fiscal_model/validation/cbo_options.py``. Targets are each option's own
    # published 10-year total, never the Table 1-1 range.
    PreregisteredCase(
        case_id="cbo_opt45_all_rates_1pp.v1",
        policy_id="cbo_opt45_all_rates_1pp",
        official_10yr_billions=-1_185.3,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note="Option 45, alternative 1 (report p. 55; PDF p. 61). JCT estimate.",
    ),
    PreregisteredCase(
        case_id="cbo_opt45_top4_brackets_2pp.v1",
        policy_id="cbo_opt45_top4_brackets_2pp",
        official_10yr_billions=-569.5,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 45, alternative 2 (report p. 55; PDF p. 61). The bracket "
            "boundary is filing-status specific and moves in 2026 when the "
            "pre-2018 rate schedule returns; the model holds one fixed threshold."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt46_agi_surtax_1pp_20k.v1",
        policy_id="cbo_opt46_agi_surtax_1pp_20k",
        official_10yr_billions=-1_440.1,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note="Option 46, alternative 1 (report p. 56; PDF p. 62). AGI-inclusive base.",
    ),
    PreregisteredCase(
        case_id="cbo_opt46_agi_surtax_2pp_100k.v1",
        policy_id="cbo_opt46_agi_surtax_2pp_100k",
        official_10yr_billions=-1_051.0,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note="Option 46, alternative 2 (report p. 56; PDF p. 62). AGI-inclusive base.",
    ),
    PreregisteredCase(
        case_id="cbo_opt47_ltcg_qdiv_2pp.v1",
        policy_id="cbo_opt47_ltcg_qdiv_2pp",
        official_10yr_billions=-103.3,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 47 (report p. 57; PDF p. 63). The first out-of-sample "
            "capital-gains case that is a plain rate change with no step-up "
            "component, so it isolates the frozen realization elasticities."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt51_gains_at_death.v1",
        policy_id="cbo_opt51_gains_at_death",
        official_10yr_billions=-536.1,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 51, alternative 2 (report p. 61; PDF p. 67). Alternative 1 "
            "(carryover basis) is out of scope: the module implements deemed "
            "realization at death, not deferral to the heir's sale."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt61_new_payroll_tax_1pct.v1",
        policy_id="cbo_opt61_new_payroll_tax_1pct",
        official_10yr_billions=-1_281.5,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 61, alternative 1 (report p. 72; PDF p. 78). Scored on the "
            "Medicare base (all covered earnings, no taxable maximum). The "
            "module's covered-wage bands - which ARE calibrated - are not used "
            "by this path; Option 62 is excluded precisely because it would use "
            "them."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt61_new_payroll_tax_2pct.v1",
        policy_id="cbo_opt61_new_payroll_tax_2pct",
        official_10yr_billions=-2_540.0,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note="Option 61, alternative 2 (report p. 72; PDF p. 78).",
    ),
    PreregisteredCase(
        case_id="cbo_opt64_corporate_rate_1pp.v1",
        policy_id="cbo_opt64_corporate_rate_1pp",
        official_10yr_billions=-135.7,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 64 (report p. 75; PDF p. 81). The first out-of-sample "
            "corporate case: the calibrated Corporate runner is tuned to the "
            "21%->28% Biden score, and this 1pp step tests the same machinery "
            "at a rate change seven times smaller."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt37_international_affairs.v1",
        policy_id="cbo_opt37_international_affairs",
        official_10yr_billions=-187.0,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_SPENDING_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 37 (report p. 46; PDF p. 52). First live case for the "
            "spending shape added in Phase A. Input is CBO's first-year budget "
            "authority (-$23B, 2026); target is CBO's 10-year outlay total, so "
            "the residual measures the spend-out lag the shape cannot represent."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt38_national_service.v1",
        policy_id="cbo_opt38_national_service",
        official_10yr_billions=-10.3,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_SPENDING_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note="Option 38 (report p. 47; PDF p. 53). First-year budget authority -$1.3B.",
    ),
    PreregisteredCase(
        case_id="cbo_opt39_pell_eligibility.v1",
        policy_id="cbo_opt39_pell_eligibility",
        official_10yr_billions=-22.1,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_SPENDING_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 39 (report p. 48; PDF p. 54). Target is the discretionary "
            "outlay total only; CBO reports a separate -$9.2B mandatory effect "
            "that this shape does not cover (Table 1-1 footnote b)."
        ),
    ),
    PreregisteredCase(
        case_id="cbo_opt42_nondefense_discretionary.v1",
        policy_id="cbo_opt42_nondefense_discretionary",
        official_10yr_billions=-339.0,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_SPENDING_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note="Option 42 (report p. 51; PDF p. 57). First-year spending authority -$41B.",
    ),
    PreregisteredCase(
        case_id="cbo_opt43_state_local_grants.v1",
        policy_id="cbo_opt43_state_local_grants",
        official_10yr_billions=-66.7,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_SPENDING_BASELINE,
        entered_commit=PHASE_B_ENTERED_COMMIT,
        entered_date=PHASE_B_ENTERED_DATE,
        first_scoring_run_commit=PHASE_B_FIRST_SCORED_COMMIT,
        note=(
            "Option 43, total row (report pp. 52-53; PDF pp. 58-59). The 2026 "
            "budget authority is inflated by IIJA advance funding, so a level "
            "shape anchored on it over-states every later year."
        ),
    ),
    # ---- Phase D: enacted-law component replications (entered, then scored) --
    # ---- Wave 3 promotion: CBO Option 56, previously excluded as leakage ----
    PreregisteredCase(
        case_id="cbo_opt56_employer_health_income_only.v1",
        policy_id="cbo_opt56_employer_health_income_only",
        official_10yr_billions=-697.0,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/60557",
        source_date="2024-12",
        source_baseline_vintage=CBO_OPTIONS_REVENUE_BASELINE,
        entered_commit=OPTION_56_ENTERED_COMMIT,
        entered_date=OPTION_56_ENTERED_DATE,
        first_scoring_run_commit=OPTION_56_FIRST_SCORED_COMMIT,
        note=(
            "Option 56, third alternative (report p. 66; PDF p. 72), row "
            "'Decrease (-) in the deficit': -$697B over FY2025-2034, which is "
            "$709B of added revenue net of $12B of added mandatory outlays. "
            "The option was out of scope in Phase B for leakage — the only "
            "path that could score it was the fitted `cap_employer_health` "
            "annual — and lane L6 removed that dependency by giving the "
            "module a premium distribution, so the score is now built from a "
            "published expenditure level times a share the distribution "
            "supplies. Shape inputs are fixed by OPTION_56_SHAPE_RULE. Only "
            "this one of the option's three alternatives is registered: the "
            "other two limit the payroll-tax exclusion as well, and the "
            "expenditure module has no payroll base, so scoring them would be "
            "a known base mismatch rather than a prediction. Provenance "
            "caveat, stated rather than buried: the premium distribution's "
            "*shape* parameter is identified from the two percentile values "
            "this same option prints. That is a design input, exactly like "
            "the budget-authority level a spending option donates to its own "
            "prediction; the target — the revenue CBO scores — is a different "
            "series and is not read anywhere."
        ),
    ),
    PreregisteredCase(
        case_id="ssfa_wep_gpo_repeal_outlays.v1",
        policy_id="ssfa_wep_gpo_repeal_outlays",
        official_10yr_billions=195.65,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/system/files/2024-09/hr82.pdf",
        source_date="2024-09",
        source_baseline_vintage=(
            "CBO June 2024 baseline (the estimate is dated 9 September 2024) - "
            "VINTAGE MISMATCH: the repository has no 2024 mid-year vintage, so "
            "this row is scored on the model's current default baseline. The "
            "shape is bottom-up from a stated benefit level and reads nothing "
            "off the baseline, so the mismatch does not move the score."
        ),
        entered_commit=PHASE_D_ENTERED_COMMIT,
        entered_date=PHASE_D_ENTERED_DATE,
        first_scoring_run_commit=PHASE_D_FIRST_SCORED_COMMIT,
        note=(
            "Component record, not the bill total. The repository's existing "
            "'social_security_fairness_2023' record carries a rounded $196B and "
            "used to cite publication 59434, which is CBO's estimate of H.R. "
            "3938, a different bill; the provenance pass repointed it at the "
            "H.R. 82 estimate this row transcribes and noted the $195.65B "
            "component figure there. The rounded target itself is unchanged. "
            + PHASE_D_SPENDING_LEVEL_RULE
        ),
    ),
    PreregisteredCase(
        case_id="fra_2023_discretionary_caps.v1",
        policy_id="fra_2023_discretionary_caps",
        official_10yr_billions=-1331.8,
        source_name="Congressional Budget Office",
        source_url=(
            "https://www.cbo.gov/system/files/2023-05/hr3746_Letter_McCarthy.pdf"
        ),
        source_date="2023-05",
        source_baseline_vintage=(
            "CBO May 2023 baseline (stated in the letter) - VINTAGE MISMATCH: "
            "the repository's oldest vintage is CBO_FEB_2024, so this row is "
            "scored on the model's current default baseline."
        ),
        entered_commit=PHASE_D_ENTERED_COMMIT,
        entered_date=PHASE_D_ENTERED_DATE,
        first_scoring_run_commit=PHASE_D_FIRST_SCORED_COMMIT,
        note=(
            "Discretionary-caps component only; the bill's -$1.5T total also "
            "bundles the Toxic Exposures Fund, student loans, an IRS rescission "
            "and debt service. " + PHASE_D_SPENDING_LEVEL_RULE
        ),
    ),
    PreregisteredCase(
        case_id="iija_2021_discretionary.v1",
        policy_id="iija_2021_discretionary",
        official_10yr_billions=415.448,
        source_name="Congressional Budget Office",
        source_url=(
            "https://www.cbo.gov/system/files/2021-08/hr3684_infrastructure.pdf"
        ),
        source_date="2021-08",
        source_baseline_vintage=(
            "CBO July 2021 baseline - VINTAGE MISMATCH: the repository's oldest "
            "vintage is CBO_FEB_2024, so this row is scored on the model's "
            "current default baseline."
        ),
        entered_commit=PHASE_D_ENTERED_COMMIT,
        entered_date=PHASE_D_ENTERED_DATE,
        first_scoring_run_commit=PHASE_D_FIRST_SCORED_COMMIT,
        note=(
            "Discretionary component only; the bill's +$256B net also nets "
            "-$110B of direct spending and +$50B of revenues. Expected to miss "
            "badly and kept anyway: CBO's own table shows front-loaded budget "
            "authority ($163.0B in 2022) producing a humped outlay path (peak "
            "$70.0B in 2026), which a level SpendingPolicy with no spend-out "
            "model cannot reproduce. " + PHASE_D_SPENDING_LEVEL_RULE
        ),
        superseded_by="iija_2021_discretionary.v2",
    ),
    # ---- The IIJA authorization path (entered, then scored) ---------------
    PreregisteredCase(
        case_id="iija_2021_discretionary.v2",
        policy_id="iija_2021_discretionary",
        official_10yr_billions=415.448,
        source_name="Congressional Budget Office",
        source_url=(
            "https://www.cbo.gov/system/files/2021-08/hr3684_infrastructure.pdf"
        ),
        source_date="2021-08",
        source_baseline_vintage=(
            "CBO July 2021 baseline - VINTAGE MISMATCH: the repository's oldest "
            "vintage is CBO_FEB_2024, so this row is scored on the model's "
            "current default baseline."
        ),
        entered_commit=IIJA_AUTHORIZATION_PATH_ENTERED_COMMIT,
        entered_date=IIJA_AUTHORIZATION_PATH_ENTERED_DATE,
        first_scoring_run_commit=IIJA_AUTHORIZATION_PATH_FIRST_SCORED_COMMIT,
        note=(
            "**The target does not change.** This row replaces v1's *shape "
            "input*, not CBO's $415.448B figure: the official number, the "
            "source, the document and the window are all identical. What "
            "changes is what the model is given to work from. v1 applied "
            "PHASE_D_SPENDING_LEVEL_RULE, which reads the first fully-funded "
            "year off the source and carries it forward at 2%/yr - the only "
            "shape a SpendingPolicy could express when v1 was entered. The "
            "source does not state a level; it states a five-year "
            "authorization that then falls to about $2B/yr, and "
            "SpendingPolicy.budget_authority_path (lane L2, PR #85) can now "
            "carry that schedule. Keeping v1 would have meant scoring a shape "
            "the source contradicts because the model used to be unable to "
            "express the one it states. v1 stays in this file, unedited, with "
            "its +$1,894B / 356% and post-spend-out +$1,621B / 290% both on "
            "the record. " + IIJA_AUTHORIZATION_PATH_RULE
        ),
        superseded_by="iija_2021_discretionary.v3",
    ),
    # ---- The IIJA window (entered, then scored) ---------------------------
    PreregisteredCase(
        case_id="iija_2021_discretionary.v3",
        policy_id="iija_2021_discretionary",
        official_10yr_billions=415.448,
        source_name="Congressional Budget Office",
        source_url=(
            "https://www.cbo.gov/system/files/2021-08/hr3684_infrastructure.pdf"
        ),
        source_date="2021-08",
        source_baseline_vintage=(
            "CBO July 2021 baseline - the repository's oldest vintage is "
            "CBO_FEB_2024, so this row is still scored on the model's current "
            "default baseline. What moves here is the WINDOW, not the "
            "VINTAGE: a discretionary SpendingPolicy scores its own "
            "source-stated budget authority and reads no baseline LEVEL, so "
            "the decade this row is scored on can be the decade its target "
            "covers without a 2021 baseline existing."
        ),
        entered_commit=IIJA_WINDOW_ENTERED_COMMIT,
        entered_date=IIJA_WINDOW_ENTERED_DATE,
        first_scoring_run_commit=IIJA_WINDOW_FIRST_SCORED_COMMIT,
        note=(
            "**The target does not change.** This row replaces v2's *shape "
            "input* for the second time, and CBO's $415.448B figure, the "
            "source, the document and the published window are all identical "
            "to v1's and v2's. v2 scored the source's own authorization "
            "schedule on the runner's FY2025-2034 decade, and the residual it "
            "left was arithmetic rather than behaviour: the path outlays "
            "$434.1B in total (4.5% above CBO's figure, which is the "
            "construction_and_capital profile's 0.9727 spend-out sum applied "
            "to the full authority), but $92.6B of that falls in FY2022-2024, "
            "before the window opens, so $340.0B was compared against a total "
            "covering FY2021-2031 and the row read 18.2%. This row scores the "
            "ten fiscal years the target covers, which the record's own "
            "budget_window has said are FY2022-2031 since it was entered on "
            "2026-09-01. v2 stays in this file, unedited, with its +$340.0B / "
            "18.2% on the record beside v1's +$1,894B / 356% and post-spend-out "
            "+$1,621B / 290%; between them the three rows separate the three "
            "defects this case surfaced - the missing spend-out model (L2), "
            "the missing authorization path (v2) and the window (this row). "
            "The number was published before the decision was taken: "
            "planning/memos/FY2022_TARGET_WINDOW.md section 6 computed +$414.3B "
            "and 0.3% on this window and explicitly left the .v3 decision to "
            "the owner, precisely so that taking it would be a visible choice "
            "rather than a lane's correction. "
            + IIJA_AUTHORIZATION_PATH_RULE
            + " "
            + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    # ---- Lane R3: the 2018, 2020 and 2022 Options volumes ----------------
    #
    # Twenty-two rows, selected by R3_SELECTION_RULE below before any of them
    # was scored, and entered here in a commit that leaves every one of them
    # ``runnable=False``. The commit that flips them is the one that first
    # scores them - Phase B's two-commit protocol, unchanged.
    #
    # Each row is scored on the decade its own volume published
    # (``scoring_window_first_year``) and on ``CBO_FEB_2024``, the oldest
    # baseline vintage this repository carries; the mismatch with the volume's
    # own baseline is recorded per row below rather than silently absorbed.
    PreregisteredCase(
        case_id="cbo2019_opt1_all_rates_1pp.v1",
        policy_id="cbo2019_opt1_all_rates_1pp",
        official_10yr_billions=-905.4,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 1, first "
            "alternative (report p. 204): 'Raise all tax rates on ordinary "
            "income by 1 percentage point', +$905.4B over FY2019-2028. 'Source: "
            "Staff of the Joint Committee on Taxation.' The option takes effect "
            "in January 2019. Bracket 1's floor is $0 in every year of every "
            "vintage, so the schedule path returns the same threshold the "
            "record is written with."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2019_opt1_top4_brackets_1pp.v1",
        policy_id="cbo2019_opt1_top4_brackets_1pp",
        official_10yr_billions=-222.9,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 1, second "
            "alternative (report p. 204): 'Raise all tax rates on ordinary "
            "income in the top four brackets (24 percent and over from 2018 "
            "through 2025, and 28 percent and over after 2025) by 1 percentage "
            "point', +$222.9B over FY2019-2028."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2019_opt1_top2_brackets_1pp.v1",
        policy_id="cbo2019_opt1_top2_brackets_1pp",
        official_10yr_billions=-123.4,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 1, third "
            "alternative (report p. 204): 'Raise all tax rates on ordinary "
            "income in the top two brackets (35 percent and over) by 1 "
            "percentage point', +$123.4B over FY2019-2028. 'The two highest "
            "brackets' of seven is the floor of bracket 6; the amounts are "
            "CBO's own CY2021 figures, which the schedule clamp makes the "
            "amounts actually applied."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2019_opt2_ltcg_qdiv_2pp.v1",
        policy_id="cbo2019_opt2_ltcg_qdiv_2pp",
        official_10yr_billions=-69.6,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 2, first "
            "alternative (report p. 207): 'Raise rates on long-term capital "
            "gains and dividends by 2 percentage points', +$69.6B over "
            "FY2019-2028. Applies to every rate bracket, so the threshold is "
            "zero. The option's other two alternatives ALSO realign the "
            "preferential-rate brackets with the ordinary brackets, which "
            "CapitalGainsPolicy cannot express; they are recorded as "
            "not-registered in the alternatives CSV."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2019_opt18_hi_payroll_1pp.v1",
        policy_id="cbo2019_opt18_hi_payroll_1pp",
        official_10yr_billions=-898.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 18, first "
            "alternative (report p. 251): +$898.3B over FY2019-2028. Scored on "
            "the same shape as CBO 2024 Option 61 because CBO states the same "
            "base for both: 'Unlike the payroll tax for Social Security, which "
            "applies to earnings up to an annual maximum, the 2.9 percent HI "
            "tax is levied on total earnings.' A 1pp increase in the basic HI "
            "rate on total earnings and a new 1 percent tax on all covered "
            "earnings are the same base times the same rate; what differs is "
            "which trust fund receives it, which no revenue estimate turns on."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2019_opt18_hi_payroll_2pp.v1",
        policy_id="cbo2019_opt18_hi_payroll_2pp",
        official_10yr_billions=-1_786.5,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 18, second "
            "alternative (report p. 251): +$1,786.5B over FY2019-2028."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2019_opt24_corporate_rate_1pp.v1",
        policy_id="cbo2019_opt24_corporate_rate_1pp",
        official_10yr_billions=-96.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/54667",
        source_date="2018-12",
        source_baseline_vintage=(
            "CBO April 2018 baseline, as stated by Options for Reducing the "
            "Deficit: 2019 to 2028 (pub. 54667, FY2019-2028 window) - VINTAGE "
            "MISMATCH: the repository carries no April-2018 vintage, so this "
            "row is scored on CBO_FEB_2024, the oldest it has, on its own "
            "FY2019-2028 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2019-2028 (pub. 54667), revenue option 24 (report p. "
            "266): +$96.3B over FY2019-2028, 'Source: Staff of the Joint "
            "Committee on Taxation.' The second of four editions of one reform "
            "- $96.3B (FY2019-2028), $99.3B (FY2021-2030), $129.3B "
            "(FY2023-2032), $135.7B (FY2025-2034) - which is what gives the "
            "corporate class more than one observation for the first time."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt1_all_rates_1pp.v1",
        policy_id="cbo2021_opt1_all_rates_1pp",
        official_10yr_billions=-884.0,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 1, first "
            "alternative (report p. 204): +$884.0B over FY2021-2030, 'Data "
            "source: Staff of the Joint Committee on Taxation.'"
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt1_top4_brackets_1pp.v1",
        policy_id="cbo2021_opt1_top4_brackets_1pp",
        official_10yr_billions=-203.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 1, second "
            "alternative (report p. 204): +$203.3B over FY2021-2030. The "
            "amounts are CBO's own CY2021 bracket-4 floors from the transcribed "
            "parameter schedule - the option's own first calendar year."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt1_top2_brackets_1pp.v1",
        policy_id="cbo2021_opt1_top2_brackets_1pp",
        official_10yr_billions=-113.8,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 1, third "
            "alternative (report p. 204): +$113.8B over FY2021-2030. The "
            "smallest target in the battery, and the only row that prices the "
            "top two brackets alone."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt2_ltcg_qdiv_2pp.v1",
        policy_id="cbo2021_opt2_ltcg_qdiv_2pp",
        official_10yr_billions=-75.2,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 2 (report p. "
            "207): +$75.2B over FY2021-2030. Unlike the 2018 edition, this one "
            "does not realign the preferential brackets, so the option is the "
            "rate change alone."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt15_hi_payroll_1pp.v1",
        policy_id="cbo2021_opt15_hi_payroll_1pp",
        official_10yr_billions=-877.5,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 15, first "
            "alternative (report p. 285): +$877.5B over FY2021-2030. Same base "
            "as CBO 2024 Option 61 and as the 2018 edition's option 18: the HI "
            "tax on total earnings, with no taxable maximum."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt15_hi_payroll_2pp.v1",
        policy_id="cbo2021_opt15_hi_payroll_2pp",
        official_10yr_billions=-1_736.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 15, second "
            "alternative (report p. 285): +$1,736.3B over FY2021-2030."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2021_opt19_corporate_rate_1pp.v1",
        policy_id="cbo2021_opt19_corporate_rate_1pp",
        official_10yr_billions=-99.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/56783",
        source_date="2020-12",
        source_baseline_vintage=(
            "CBO September 2020 baseline, as stated by Options for Reducing the "
            "Deficit: 2021 to 2030 (pub. 56783, FY2021-2030 window) - VINTAGE "
            "MISMATCH: the repository carries no September-2020 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2021-2030 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2021-2030 (pub. 56783), revenue option 19 (report p. "
            "293): +$99.3B over FY2021-2030, 'Data source: Staff of the Joint "
            "Committee on Taxation.'"
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt13_top4_brackets_2pp.v1",
        policy_id="cbo2023_opt13_top4_brackets_2pp",
        official_10yr_billions=-501.9,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume I (pub. 58164), option 13, second "
            "alternative (report p. 72): -$501.9B over FY2023-2032. The same "
            "reform cbo_opt45_top4_brackets_2pp scores on the 2024 volume's "
            "decade, so the pair measures the model's sensitivity to the decade "
            "and not two independent predictions. Amounts are CBO's own CY2023 "
            "bracket-4 floors."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt13_agi_surtax_1pp_stdded.v1",
        policy_id="cbo2023_opt13_agi_surtax_1pp_stdded",
        official_10yr_billions=-1_329.1,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume I (pub. 58164), option 13, third "
            "alternative (report p. 72): -$1,329.1B over FY2023-2032. The "
            "largest revenue raiser in the individual-rate option of any of the "
            "four volumes, and the only AGI surtax outside the 2024 edition. "
            "CBO's own words put it on AGI - 'a surtax of 1 percentage point on "
            "AGI above the standard deduction and exemption' - which is what "
            "AGI_BASE_RULE reads."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt13_agi_surtax_2pp_bracket4.v1",
        policy_id="cbo2023_opt13_agi_surtax_2pp_bracket4",
        official_10yr_billions=-773.8,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume I (pub. 58164), option 13, fourth "
            "alternative (report p. 72): -$773.8B over FY2023-2032. This is the "
            "one published surtax whose boundary is stated as a sum of three "
            "statutory parameters rather than as a dollar amount, and it is "
            "registered because all three are parameters CBO itself publishes "
            "for the option's own first calendar year."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt15_new_payroll_1pct.v1",
        policy_id="cbo2023_opt15_new_payroll_1pct",
        official_10yr_billions=-1_135.7,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume I (pub. 58164), option 15, first "
            "alternative (report p. 76): -$1,135.7B over FY2023-2032. The same "
            "reform as CBO 2024 Option 61 alternative 1 on the previous decade."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt15_new_payroll_2pct.v1",
        policy_id="cbo2023_opt15_new_payroll_2pct",
        official_10yr_billions=-2_252.7,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume I (pub. 58164), option 15, second "
            "alternative (report p. 76): -$2,252.7B over FY2023-2032."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt6_employer_health_income_only.v1",
        policy_id="cbo2023_opt6_employer_health_income_only",
        official_10yr_billions=-651.4,
        source_name="Congressional Budget Office",
        source_url="https://www.cbo.gov/publication/58164",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume I (pub. 58164), option 6, third "
            "alternative (report p. 30), 'Decrease (-) in the Deficit' row: "
            "-$651.4B over FY2023-2032. The cap dollars are CBO's own stated "
            "design - 'contributions that exceeded $8,900 a year for individual "
            "coverage and $21,600 a year for family coverage would be included "
            "in employees' taxable income', the 50th percentile of 2024 "
            "premiums indexed to 2026 - and the option takes effect in January "
            "2026, which CBO's zeros for 2023-2025 confirm. As in the 2024 "
            "edition, this is the only one of the option's three alternatives "
            "the module can express: the other two limit the payroll-tax "
            "exclusion as well."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt37_ltcg_qdiv_2pp.v1",
        policy_id="cbo2023_opt37_ltcg_qdiv_2pp",
        official_10yr_billions=-102.1,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58163",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume II (pub. 58163), revenue option 37 "
            "(report p. 89): -$102.1B over FY2023-2032. Applies to every rate "
            "bracket, so the threshold is zero. Its 2024 sibling "
            "(cbo_opt47_ltcg_qdiv_2pp) carries -$103.3B on the next decade: "
            "CBO's own two editions differ by 1.2% for one unchanged reform, "
            "where the individual-rate option's differ by 9.6%."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
    PreregisteredCase(
        case_id="cbo2023_opt50_corporate_rate_1pp.v1",
        policy_id="cbo2023_opt50_corporate_rate_1pp",
        official_10yr_billions=-129.3,
        source_name="Joint Committee on Taxation",
        source_url="https://www.cbo.gov/publication/58163",
        source_date="2022-12",
        source_baseline_vintage=(
            "CBO May 2022 baseline, as stated by Options for Reducing the "
            "Deficit: 2023 to 2032 (pubs. 58164 and 58163, FY2023-2032 window) "
            "- VINTAGE MISMATCH: the repository carries no May-2022 vintage, so "
            "this row is scored on CBO_FEB_2024 on its own FY2023-2032 window"
        ),
        entered_commit=R3_MULTI_VOLUME_ENTERED_COMMIT,
        entered_date=R3_MULTI_VOLUME_ENTERED_DATE,
        first_scoring_run_commit=R3_MULTI_VOLUME_FIRST_SCORED_COMMIT,
        note=(
            "CBO Options 2023-2032 Volume II (pub. 58163), revenue option 50 "
            "(report p. 115): -$129.3B over FY2023-2032, 'Data source: Staff of "
            "the Joint Committee on Taxation.' CORPORATE_PER_POINT_YIELD.md "
            "showed JCT's per-point yield is flat in the rate; these four "
            "editions show what it does in TIME, which the memo could not."
            + " " + R3_SELECTION_RULE
            + " " + FY2022_TARGET_WINDOW_RULE
        ),
    ),
)


def live_cases() -> dict[str, PreregisteredCase]:
    """Manifest rows still in force, keyed by ``policy_id``."""
    return {case.policy_id: case for case in PREREGISTERED_CASES if case.is_live}


def superseded_cases() -> tuple[PreregisteredCase, ...]:
    """Manifest rows no longer in force (kept as history).

    Covers both replacements (``superseded_by``) and withdrawals
    (``retired``); :func:`retired_cases` narrows to the latter.
    """
    return tuple(case for case in PREREGISTERED_CASES if not case.is_live)


def retired_cases() -> tuple[PreregisteredCase, ...]:
    """Manifest rows withdrawn because the target could not be sourced."""
    return tuple(case for case in PREREGISTERED_CASES if case.retired)


def get_case(policy_id: str) -> PreregisteredCase | None:
    """Live manifest row for a policy id, if registered."""
    return live_cases().get(policy_id)


def manifest_problems(scorecard: Any) -> list[str]:
    """
    Return every pre-registration violation found, as human-readable strings.

    Checks, in order:

    * ``case_id`` values are unique.
    * A policy has at most one live row.
    * Every live row names a real ``KNOWN_SCORES`` record.
    * Every live row's target equals the ``KNOWN_SCORES`` value — a changed
      target must be a *new* row, never an edit.
    * Every ``superseded_by`` points at an existing row.
    * Every Generic (out-of-sample) scorecard entry has a live row, and the
      entry's official value matches it.
    """
    problems: list[str] = []

    seen_ids: set[str] = set()
    live_by_policy: dict[str, str] = {}
    all_ids = {case.case_id for case in PREREGISTERED_CASES}

    for case in PREREGISTERED_CASES:
        if case.case_id in seen_ids:
            problems.append(f"duplicate manifest case_id: {case.case_id}")
        seen_ids.add(case.case_id)

        if case.superseded_by is not None and case.superseded_by not in all_ids:
            problems.append(
                f"{case.case_id}: superseded_by '{case.superseded_by}' is not a manifest row"
            )

        # Withdrawing a case removes evidence from the honest tier, so it has
        # to state why. A retired row with no reason is indistinguishable from
        # a case quietly dropped because it scored badly.
        if case.retired and not case.retired_reason.strip():
            problems.append(f"{case.case_id}: retired with no retired_reason")
        if case.retired and case.superseded_by is not None:
            problems.append(
                f"{case.case_id}: is both retired and superseded_by "
                f"'{case.superseded_by}'; a target is either replaced or "
                f"withdrawn, not both"
            )

        if not case.is_live:
            continue

        if case.policy_id in live_by_policy:
            problems.append(
                f"{case.policy_id}: two live manifest rows "
                f"({live_by_policy[case.policy_id]} and {case.case_id})"
            )
        live_by_policy[case.policy_id] = case.case_id

        score = KNOWN_SCORES.get(case.policy_id)
        if score is None:
            problems.append(f"{case.case_id}: no KNOWN_SCORES record '{case.policy_id}'")
            continue
        if float(score.ten_year_cost) != float(case.official_10yr_billions):
            problems.append(
                f"{case.case_id}: pre-registered target "
                f"{case.official_10yr_billions:+.1f}B != KNOWN_SCORES "
                f"{score.ten_year_cost:+.1f}B — a changed target must be a NEW row "
                f"with a new case_id, with the old one marked superseded_by."
            )

    registered = live_cases()
    for entry in getattr(scorecard, "entries", []):
        if getattr(entry, "category", None) != "Generic":
            continue
        policy_id = getattr(entry, "policy_id", "unknown")
        case = registered.get(policy_id)
        if case is None:
            problems.append(
                f"out-of-sample entry '{policy_id}' has no pre-registration row; "
                f"add one to fiscal_model/validation/preregistered.py before scoring it"
            )
            continue
        official = float(getattr(entry, "official_10yr_billions", 0.0))
        if official != float(case.official_10yr_billions):
            problems.append(
                f"{policy_id}: scorecard official {official:+.1f}B != pre-registered "
                f"{case.official_10yr_billions:+.1f}B"
            )

    return problems


def assert_preregistered(scorecard: Any) -> None:
    """Raise ``AssertionError`` if the manifest and the scorecard disagree."""
    problems = manifest_problems(scorecard)
    if problems:
        raise AssertionError(
            "pre-registration manifest violations:\n  - " + "\n  - ".join(problems)
        )


def summarize_preregistration() -> dict[str, Any]:
    """Compact manifest summary for dashboards and API payloads."""
    live = live_cases()
    return {
        "live_cases": len(live),
        "superseded_cases": len(superseded_cases()),
        "retired_cases": len(retired_cases()),
        "policy_ids": sorted(live),
        "phase_a_commit": PHASE_A_COMMIT,
        "phase_b_entered_commit": PHASE_B_ENTERED_COMMIT,
        "phase_b_first_scored_commit": PHASE_B_FIRST_SCORED_COMMIT,
        "phase_d_entered_commit": PHASE_D_ENTERED_COMMIT,
        "phase_d_first_scored_commit": PHASE_D_FIRST_SCORED_COMMIT,
        "iija_authorization_path_entered_commit": (
            IIJA_AUTHORIZATION_PATH_ENTERED_COMMIT
        ),
        "iija_authorization_path_first_scored_commit": (
            IIJA_AUTHORIZATION_PATH_FIRST_SCORED_COMMIT
        ),
        "fy2022_window_entered_commit": FY2022_WINDOW_ENTERED_COMMIT,
        "fy2022_window_first_scored_commit": FY2022_WINDOW_FIRST_SCORED_COMMIT,
        "iija_window_entered_commit": IIJA_WINDOW_ENTERED_COMMIT,
        "iija_window_first_scored_commit": IIJA_WINDOW_FIRST_SCORED_COMMIT,
        "rows": [
            {
                "case_id": case.case_id,
                "policy_id": case.policy_id,
                "official_10yr_billions": case.official_10yr_billions,
                "source_name": case.source_name,
                "source_url": case.source_url,
                "source_date": case.source_date,
                "source_baseline_vintage": case.source_baseline_vintage,
                "entered_commit": case.entered_commit,
                "entered_date": case.entered_date,
                "first_scoring_run_commit": case.first_scoring_run_commit,
            }
            for case in PREREGISTERED_CASES
            if case.is_live
        ],
    }


__all__ = [
    "CBO_OPTIONS_REVENUE_BASELINE",
    "CBO_OPTIONS_SPENDING_BASELINE",
    "FY2022_TARGET_WINDOW_RULE",
    "FY2022_WINDOW_ENTERED_COMMIT",
    "FY2022_WINDOW_FIRST_SCORED_COMMIT",
    "IIJA_AUTHORIZATION_PATH_ENTERED_COMMIT",
    "IIJA_AUTHORIZATION_PATH_FIRST_SCORED_COMMIT",
    "IIJA_AUTHORIZATION_PATH_RULE",
    "IIJA_WINDOW_ENTERED_COMMIT",
    "IIJA_WINDOW_FIRST_SCORED_COMMIT",
    "PHASE_A_COMMIT",
    "PHASE_B_ENTERED_COMMIT",
    "PHASE_B_FIRST_SCORED_COMMIT",
    "PHASE_D_ENTERED_COMMIT",
    "PHASE_D_FIRST_SCORED_COMMIT",
    "PHASE_D_SPENDING_LEVEL_RULE",
    "PHASE_E_PROVENANCE_COMMIT",
    "PREREGISTERED_CASES",
    "PreregisteredCase",
    "assert_preregistered",
    "get_case",
    "live_cases",
    "manifest_problems",
    "retired_cases",
    "summarize_preregistration",
    "superseded_cases",
]
