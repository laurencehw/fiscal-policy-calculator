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

#: Commit of the Phase E provenance pass (plan §5.1-§5.2): the pass that opened
#: the primary documents and transcribed the rows behind the benchmark targets.
#: It supersedes one out-of-sample row — ``biden_capital_gains_39`` — because
#: its -$456B target turned out to appear in no Treasury volume. A *re-sourced*
#: target is exactly the case the "new row, never an edit" rule exists for: the
#: old row and the reason it went are both still in this file.
PHASE_E_PROVENANCE_COMMIT = "0bcfbc3b4ba1e4a73864369d8f50f3bb6528efe5"
PHASE_E_PROVENANCE_DATE = "2026-09-01"

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
        note="Uniform 1pp on all brackets. Ordinary-income base.",
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
        note=(
            "Same target as the 'Biden 2025 Proposal' entry in CBO_SCORE_MAP; registered "
            "once so the prediction is not double-counted. Treasury describes it as "
            "'combined with other provisions', so the target is itself a bundled figure."
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
        note=(
            "Structurally identical to biden_capital_gains_39 (39.6% above $1M plus "
            "step-up elimination) but published against a different baseline and three "
            "years earlier; the two official targets differ by 42%."
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
        note=(
            "Shipped as a sidebar preset with an official number but no runner. "
            "Provenance is weak (bare homepage URL, year only) — Phase E should replace "
            "it with a line item or demote it."
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
    "IIJA_AUTHORIZATION_PATH_ENTERED_COMMIT",
    "IIJA_AUTHORIZATION_PATH_FIRST_SCORED_COMMIT",
    "IIJA_AUTHORIZATION_PATH_RULE",
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
