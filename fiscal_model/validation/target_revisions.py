"""
Supersede ledger for **calibrated (Tier 2) benchmark targets**.

Why this file exists
--------------------
:mod:`.preregistered` gives the out-of-sample tier a rule for changing a
target: *never edit a row.* Mark the old row ``superseded_by`` and add a new
one, so the change is a diff a reviewer can read rather than a number that
quietly moved. The calibrated tier had no such rule, and Phase E of
``planning/VALIDATION_EXPANSION.md`` §5b hit the consequence head-on. It read
24 calibrated targets out of a primary document, found **15 of them disagreed
with the figure the repository carries** — one in sign — and then deliberately
moved none of them, because "every calibrated target has a module constant
fitted to it, so editing one silently converts a 0% row into a miss that says
nothing about the model." The disagreement was parked on
``ScorecardEntry.official_10yr_billions_line_item`` and left as an owner
decision.

This module is the mechanism that owner decision needs. It is the smallest
possible mirror of :mod:`.preregistered`: the old figure is kept as a row with
``superseded_by`` set, the new figure arrives as a new row carrying its
document, table, row, page, date and the reason, and
:func:`target_revision_problems` fails if the live row and the registry the app
and the runners actually read ever disagree.

What it does *not* do
---------------------
It does not inject a target anywhere. Exactly like ``assert_preregistered``,
this is a **ledger plus a consistency check**: the live figure is written into
``AMT_VALIDATION_SCENARIOS_COMPARE`` / ``CBO_SCORE_MAP`` where the runner and
the app read it, and the check asserts the two agree. A ledger that also
supplied the number could not catch a registry drifting away from it.

The three consequences a revision has, all of them deliberate
-------------------------------------------------------------
1. **The transcription stops disagreeing.** ``benchmark_sources`` flips from
   ``line_item_differs`` to ``line_item`` once the carried target *is* the
   published figure. The gap does not vanish, it moves onto this ledger.
2. **A fitted row becomes an unfitted one.** A module constant fitted to the
   superseded figure is, by definition, not fitted to the live one.
   :func:`target_was_revised` is what ``scorecard.py`` reads to turn
   ``calibrated_to_target`` off, so the entry is reported in the
   *reconstruction* tier where a miss is a finding rather than in the fitted
   tier where a miss is a regression. This is a correction to a claim the flag
   makes about provenance, not a relaxation of a gate: retuning the constant to
   the new target would be the relaxation, and is forbidden.
3. **The headline moves, and it should.** Correcting a target the constants
   were fitted to converts a 0% row into a real miss. Both readings — the
   fitted tier with the row held in it, and the fitted tier with the row moved
   out — are reported in ``planning/lanes/PROVENANCE_amt_insulin.md``. Neither
   is quoted without the other.

The third state: retirement
---------------------------
A supersession says *the target moved here*. An ``EXAMINED_NOT_REVISED`` verdict
says *somebody opened the document and decided to keep the carried figure*.
Neither can say the third thing, which is *this figure is not a score of
anything and no published score of this policy exists to put in its place* —
so ``retired=True`` does, mirroring :mod:`.preregistered`'s own withdrawal
state. Three rules keep it from becoming a way to go green:

* the **row stays** in this ledger and the **benchmark keeps its scorecard
  row**. Nothing is deleted; ``planning/HIGH_STAKES_ACCURACY.md`` §5's *"no
  removing a case to go green"* binds here as everywhere else.
* the entry leaves the reconstruction tier's mean, because a withdrawn figure
  is not a benchmark and an error against it measures nothing — **and** the
  scorecard counts retired rows and the dashboard prints the same tier with
  them folded back at the error they carried on the day they were withdrawn.
  A mean that fell because two rows left is then a visible omission rather
  than an invisible one.
* ``retired_reason`` is required, and states what was searched and what would
  bring the target back.

``entered_commit`` note: a file cannot contain its own commit hash, so rows
added in a change are stamped with that change's hash in the immediately
following commit — the same two-commit protocol ``preregistered.py`` uses, and
for the same reason: it makes "the target moved before the model was allowed to
see it" checkable from the git history rather than asserted in prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: A revision id is ``<policy_id>.v<n>``. The version suffix is checked, not
#: only the prefix: an id that does not sort by version is a ledger whose
#: history cannot be read in order.
_REVISION_ID = re.compile(r"^[A-Za-z0-9_]+\.v[1-9][0-9]*$")

#: Commit that introduced this ledger and its first four rows — two
#: supersessions, each a superseded row plus its live replacement. Stamped in
#: the commit that follows it.
AMT_INSULIN_PROVENANCE_ENTERED_COMMIT = (
    "2a341d8e3deaf07a565306c77adc1af123ccf5af"
)
AMT_INSULIN_PROVENANCE_ENTERED_DATE = "2026-09-02"

#: Commit in which the revised targets were first actually scored — the commit
#: that writes the new figures into ``scenarios.py`` and ``app_data.py``.
AMT_INSULIN_PROVENANCE_FIRST_SCORED_COMMIT = (
    "d6288922bc082608bda35111f58217b13a121eb2"
)

#: Commit that entered the Wave 3 provenance rows — the Pillar Two range and
#: the estate row's examined-and-left verdict — and, being one change, the
#: commit they were first scored against too. Unlike the AMT/insulin pair
#: these move no registry figure, so there is no second commit to separate:
#: the range's whole content is that the carried point is not a published
#: target, and the check it introduces is a containment test the existing
#: -$80B already satisfied.
WAVE3_PROVENANCE_ENTERED_COMMIT = "d5985c41970dd6fd6a900af8bc5441df1787f950"
WAVE3_PROVENANCE_ENTERED_DATE = "2026-09-02"

WAVE3_PROVENANCE_FIRST_SCORED_COMMIT = "d5985c41970dd6fd6a900af8bc5441df1787f950"

#: Commit that entered the Wave 4 rows — eleven point revisions and one range —
#: and, unlike Wave 3, every one of them moves a figure the app and the runners
#: read. So the AMT/insulin two-commit split applies again: the ledger rows
#: land here, and the commit that follows writes the figures into
#: ``CBO_SCORE_MAP`` / ``scenarios.py`` and renames the preset labels that
#: embed them. "The target moved before the model was scored against it" is
#: therefore checkable from ``git log`` rather than asserted in prose.
WAVE4_PROVENANCE_ENTERED_COMMIT = (
    "318be6bea12f92ae02300e0a5da6b84b98a6bff0"
)
WAVE4_PROVENANCE_ENTERED_DATE = "2026-09-02"

#: Commit in which the Wave 4 targets were first actually scored.
WAVE4_PROVENANCE_FIRST_SCORED_COMMIT = (
    "22ccdd24182f5e319eebb16caf7128ed8e6537b2"
)

#: Commit that entered the corporate/PTC provenance rows — one supersession
#: (``trump_corporate_15``, a ``model_estimate`` target replaced by a published
#: range) and one examined-and-left verdict (``repeal_ptc``). The supersession
#: moves a figure the runner reads, so the two-commit split applies again: the
#: ledger row lands here and the commit that follows writes the figure into
#: ``scenarios.py``.
CORPORATE_PTC_PROVENANCE_ENTERED_COMMIT = (
    "32d275aa915d6f084a289d0410ce45f4a060c6c8"
)
CORPORATE_PTC_PROVENANCE_ENTERED_DATE = "2026-09-05"

#: Commit in which the corporate target was first actually scored.
CORPORATE_PTC_PROVENANCE_FIRST_SCORED_COMMIT = (
    "fba838021c26089c9e624abbcf56ecfc778a5aad"
)

#: Commit that entered the H9 rows — lane
#: ``planning/lanes/HSB_h9_provenance.md``, the pass over the eighteen
#: calibrated targets that were not ``line_item``. Four revisions (three points
#: and one range) plus five new examined-and-left verdicts. Every one of the
#: four moves a figure the runners read, so the two-commit split applies: the
#: ledger rows land here and the commit that follows writes the figures into
#: ``scenarios.py`` and ``CBO_SCORE_MAP``.
H9_PROVENANCE_ENTERED_COMMIT = "cf9eb539043ec578879466c1ede017e7e4f7c842"
H9_PROVENANCE_ENTERED_DATE = "2026-09-09"

#: Commit in which the H9 targets were first actually scored.
H9_PROVENANCE_FIRST_SCORED_COMMIT = "63e76b8d8b978de6c6be1782ea2e54ba4f6bcd0a"

#: Commit of owner decision (4) — ``planning/HIGH_STAKES_ACCURACY.md`` §4 —
#: which withdraws the two pharma targets H9 searched and recommended
#: retiring. These are the ledger's **first two retirements**.
#:
#: The two-commit split does not apply and the reason is worth stating rather
#: than inferring: a supersession moves a figure a runner reads, so the target
#: must be frozen in the history before the model is scored against it. A
#: retirement moves no figure at all — both rows keep their model output, their
#: withdrawn target and their scorecard entry, and what changes is which tier's
#: mean they are counted in. There is nothing for a later commit to score, so
#: ``entered_commit`` and ``first_scoring_run_commit`` are the same commit, as
#: ``HSB_h9_provenance.md`` §8.7's prepared edit specifies.
RETIREMENT_DECISION_COMMIT = "6f1c769b06edb9c5e0884ab18043dcc9420af621"
RETIREMENT_DECISION_DATE = "2026-09-11"


@dataclass(frozen=True)
class CalibratedTarget:
    """One calibrated benchmark target, live or superseded.

    A row is either a **point** target (``official_10yr_billions`` set, the
    usual case) or a **range** target (both bounds set, the point ``None``).
    A range is not a stylistic choice: it is what the ledger says when the
    publishing agency scored the policy under several scenarios and published
    no single figure, so that any point a repository carries is an editorial
    midpoint rather than something the document contains. For a range row the
    consistency check asks whether the figure the scorecard carries lies
    *inside* the published bounds, not whether it equals a number.

    Attributes:
        revision_id: Stable row id, ``<policy_id>.v<n>``. Never reused.
        policy_id: Scorecard entry this target belongs to.
        official_10yr_billions: The target, in the repository's sign convention
            (**positive increases the deficit**). ``None`` on a range row.
        published_low_10yr_billions: Low bound of a published range, same
            convention. Set together with the high bound, or neither.
        published_high_10yr_billions: High bound of a published range.
        source_name: Publishing organization, as the record credits it.
        source_document: Full document title, as published. Empty for a
            superseded row whose figure was never traced to a document — which
            is usually *why* it was superseded.
        source_url: Deep link to the document.
        source_date: ``YYYY-MM`` where the document states a month, ``YYYY``
            where it does not — which is the usual state of a *superseded*
            row, since a figure nobody could trace to a document rarely came
            with a month either.
        source_table: Table name/number the row sits in.
        source_row: The row label, quoted from the source.
        source_page: Page reference.
        window: The budget window the figure covers.
        entered_commit: Commit at which this row entered the repository.
        entered_date: ISO date of ``entered_commit``.
        first_scoring_run_commit: Commit at which this figure was first scored
            against.
        superseded_by: ``revision_id`` of the row that replaced this one. A row
            with a value here is history: it is not checked against the live
            registries and is not the target of anything.
        retired: ``True`` when the target was **withdrawn and not replaced** —
            the third state, distinct from both a supersession (which has a
            replacement) and an ``EXAMINED_NOT_REVISED`` verdict (which keeps
            the carried figure as a target). It says: *this figure is not a
            score of anything, and no published score of this policy exists to
            put in its place.* The row stays in the ledger, because the point
            is that the withdrawal is visible; it is not live, is not the
            target of anything, and the benchmark it belongs to keeps its
            scorecard row. See :meth:`is_retired` and §4 of
            ``planning/lanes/HSB_h9_provenance.md`` for what it does to the
            tiers — in particular why a retired row is *counted and reported*
            rather than quietly dropped from a mean.
        retired_reason: Why the target was withdrawn, including what was
            searched and what would bring it back. Required on a retired row.
        reason: Why the row was superseded (on the old row) or why it replaces
            its predecessor (on the new one). Required on both halves of a
            supersession — a target that moves without a stated reason is
            exactly the silent edit this ledger exists to prevent.
        note: Free text: corroborating figures, definitional caveats.
    """

    revision_id: str
    policy_id: str
    official_10yr_billions: float | None
    source_name: str
    source_date: str
    window: str
    entered_commit: str
    entered_date: str
    first_scoring_run_commit: str
    source_document: str = ""
    source_url: str | None = None
    source_table: str | None = None
    source_row: str | None = None
    source_page: str | None = None
    published_low_10yr_billions: float | None = None
    published_high_10yr_billions: float | None = None
    superseded_by: str | None = None
    retired: bool = False
    retired_reason: str = ""
    reason: str = ""
    note: str = ""

    @property
    def is_live(self) -> bool:
        """A row still in force: not replaced by a later row, not withdrawn."""
        return self.superseded_by is None and not self.retired

    @property
    def is_retired(self) -> bool:
        """A target withdrawn with nothing to replace it."""
        return self.retired

    @property
    def is_range(self) -> bool:
        """Whether this row's target is a published range rather than a point."""
        return (
            self.published_low_10yr_billions is not None
            and self.published_high_10yr_billions is not None
        )

    def contains(self, value: float) -> bool:
        """Whether ``value`` lies inside this row's published range."""
        if not self.is_range:
            return False
        return (
            self.published_low_10yr_billions
            <= value
            <= self.published_high_10yr_billions
        )

    def distance_to_range(self, value: float) -> float:
        """How far ``value`` sits outside the range, in $B. 0.0 when inside."""
        if not self.is_range:
            return 0.0
        if value < self.published_low_10yr_billions:
            return self.published_low_10yr_billions - value
        if value > self.published_high_10yr_billions:
            return value - self.published_high_10yr_billions
        return 0.0


# ---------------------------------------------------------------------------
# Shared document handles
# ---------------------------------------------------------------------------

_CRS_R48286 = (
    "Congressional Research Service, R48286, 'Expiring Provisions of "
    "P.L. 115-97 (the Tax Cuts and Jobs Act): Economic Issues'"
)
_CRS_R48286_URL = (
    "https://www.congress.gov/crs_external_products/R/HTML/R48286.web.html"
)
_CRS_R48286_TABLE = (
    "Table 1, 'Revenue Costs of Extending the TCJA: Major Provisions "
    "(Billions of Dollars)', transcribing CBO, Budgetary Outcomes Under "
    "Alternative Assumptions About Spending and Revenues (8 May 2024, "
    "publication 60114/60271)"
)

_CBO_57957 = (
    "CBO, Estimated Budgetary Effects of H.R. 6833, the Affordable Insulin "
    "Now Act, publication 57957"
)
_CBO_57957_URL = "https://www.cbo.gov/publication/57957"

_JCX_22_23 = (
    "Joint Committee on Taxation, JCX-22-23, 'Possible Effects of Adopting "
    "the OECD's Pillar Two, Both Worldwide and in the United States'"
)
_JCX_22_23_URL = (
    "https://www.jct.gov/getattachment/07a143e4-277b-4344-b230-c499a9c16be3/"
    "OECD-Pillar-Two-Report-June-2023.pdf"
)
_JCX_22_23_TABLE = (
    "Table 2, 'Fiscal Year Federal Tax Receipt Revenue Effects for Various "
    "Scenarios', column 2023-2033"
)

_GREEN_BOOK_FY2025 = (
    "U.S. Treasury, General Explanations of the Administration's Fiscal Year "
    "2025 Revenue Proposals (Green Book)"
)
_GREEN_BOOK_FY2025_URL = (
    "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
)
_GREEN_BOOK_TABLE = "Table of Revenue Estimates (the volume's only table)"

_CBO_60557 = "CBO, Options for Reducing the Deficit: 2025 to 2034"
_CBO_60557_URL = "https://www.cbo.gov/publication/60557"

_CBO_58390 = (
    "CBO, letter to Rep. Kevin Brady and Rep. Jason Smith, 'Additional "
    "Information About Increased Enforcement by the Internal Revenue "
    "Service', publication 58390"
)
_CBO_58390_URL = "https://www.cbo.gov/publication/58390"

_CBO_60437 = (
    "CBO, letter to Chairman Jodey Arrington and Chairman Jason Smith, 'The "
    "Effects of Permanently Extending the Expansion of the Premium Tax "
    "Credit...', publication 60437"
)
_CBO_60437_URL = (
    "https://www.cbo.gov/system/files/2024-06/60437-Arrington-Smith-Letter.pdf"
)

_JCX_35_25 = (
    "Joint Committee on Taxation, JCX-35-25, estimated budget effects of the "
    "revenue provisions of H.R. 1 as passed by the Senate"
)
_JCX_35_25_URL = (
    "https://www.jct.gov/getattachment/eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/"
    "x-35-25.pdf"
)

_PWBM_SALT = (
    "Penn Wharton Budget Model, Brendan Novak, 'Lifting the SALT Cap: "
    "Estimated Budgetary Effects, 2024 and Beyond'"
)
_PWBM_SALT_URL = (
    "https://budgetmodel.wharton.upenn.edu/issues/2024/2/8/"
    "lifting-the-salt-cap-budget-effect"
)

_TF_FF861 = (
    "Erica York and Alex Durante, 'How Much Revenue Can Tariffs Really Raise "
    "for the Federal Government?', Tax Foundation Fiscal Fact 861"
)
_TF_FF861_URL = "https://taxfoundation.org/wp-content/uploads/2025/04/FF861.pdf"

_TF_TRACKER = (
    "Tax Foundation, 'Trump Tariffs: Tracking the Economic Impact of the "
    "Trump Trade War' (a living tracker; read at its 20 August 2026 revision)"
)
_TF_TRACKER_URL = (
    "https://taxfoundation.org/research/all/federal/trump-tariffs-trade-war/"
)

_CRFB_TARIFFS = (
    "Committee for a Responsible Federal Budget, 'How Much Will Trump's New "
    "Tariffs Raise?'"
)
_CRFB_TARIFFS_URL = (
    "https://www.crfb.org/blogs/how-much-will-trumps-new-tariffs-raise"
)

_TF_CORPORATE_15 = (
    "Garrett Watson and Erica York, 'A Lower Corporate Tax Rate Can Be Part "
    "of Broader Tax Reform', Tax Foundation (17 July 2024, updated "
    "23 October 2024)"
)
_TF_CORPORATE_15_URL = "https://taxfoundation.org/blog/trump-corporate-tax-cut/"

_PWBM_TRUMP_2024 = (
    "Penn Wharton Budget Model, 'The 2024 Trump Campaign Policy Proposals: "
    "Budgetary, Economic and Distributional Effects' (26 August 2024)"
)
_PWBM_TRUMP_2024_URL = (
    "https://budgetmodel.wharton.upenn.edu/issues/2024/8/26/"
    "trump-campaign-policy-proposals-2024"
)

_CRFB_CORPORATE_15 = (
    "Committee for a Responsible Federal Budget, 'Donald Trump's Proposal to "
    "Lower the Corporate Tax Rate to 15%' (6 September 2024)"
)
_CRFB_CORPORATE_15_URL = (
    "https://www.crfb.org/blogs/donald-trumps-proposal-lower-corporate-tax-rate-15"
)

_TF_OPTIONS_3 = (
    "Tax Foundation, 'Options for Reforming America's Tax Code 3.0: A "
    "Policymaker's Guide to Tax Reform Trade-Offs' (July 2026). Every option "
    "is scored on a post-P.L. 119-21 baseline over calendar years 2027-2036, "
    "on the Tax Foundation General Equilibrium Model."
)
_TF_OPTIONS_3_URL = (
    "https://taxfoundation.org/wp-content/uploads/2026/07/Options3_book_7-22.pdf"
)

_CRS_IF13190 = (
    "Congressional Research Service, IF13190, 'The Mortgage Interest "
    "Deduction' (23 March 2026)"
)
_CRS_IF13190_URL = "https://www.congress.gov/crs-product/IF13190"


CALIBRATED_TARGETS: tuple[CalibratedTarget, ...] = (
    # ------------------------------------------------------------------
    # AMT: extend TCJA relief — a five-year figure in a ten-year column
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="extend_tcja_amt.v1",
        policy_id="extend_tcja_amt",
        official_10yr_billions=450.0,
        source_name="CBO/JCT",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="extend_tcja_amt.v2",
        reason=(
            "Never traceable to a document, and the Phase E sourcing pass "
            "found what it most likely is: CRS R48286 Table 1 prints $466.2B "
            "over FY2025-FY2029 and $1,357.1B over FY2025-FY2034 for the same "
            "provision. $450B is 3.5% from the five-year figure and 66.8% from "
            "the ten-year one, so the repository was carrying a five-year cost "
            "in a ten-year column. Superseded rather than edited: the AMT "
            "module's fitted annual reproduces THIS number, and the ledger is "
            "what keeps that visible."
        ),
    ),
    CalibratedTarget(
        revision_id="extend_tcja_amt.v2",
        policy_id="extend_tcja_amt",
        official_10yr_billions=1_357.1,
        source_name="Congressional Research Service (transcribing CBO)",
        source_document=_CRS_R48286,
        source_url=_CRS_R48286_URL,
        source_date="2024-11",
        source_table=_CRS_R48286_TABLE,
        source_row="Increased Alternative Minimum Tax Exemption",
        source_page="Table 1 (FY2025-FY2034 column)",
        window="FY2025-2034",
        entered_commit=AMT_INSULIN_PROVENANCE_ENTERED_COMMIT,
        entered_date=AMT_INSULIN_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=AMT_INSULIN_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The published ten-year cost of the provision this benchmark "
            "names, read off the row: $1,357.1B over FY2025-FY2034, against "
            "$466.2B over FY2025-FY2029 in the adjacent column."
        ),
        note=(
            "Corroborated twice, independently of CRS. (1) JCT's own JCX-35-25 "
            "scores P.L. 119-21's AMT-exemption provision at $1,362.810B over "
            "FY2025-2034 — 0.4% from this figure — and that row is already in "
            "this repository as the `pl119_21_amt_exemption` benchmark. "
            "(2) The Bipartisan Policy Center's 2025 tax-debate explainer "
            "states, citing JCT: 'Extending the TCJA's individual AMT changes "
            "would reduce revenues by nearly $1.4 trillion from FY2025 through "
            "FY2034'. Definitional caveat, stated rather than split: CRS/CBO "
            "score the AMT provision inside a full TCJA-extension package, "
            "where extended rate cuts push more filers into AMT than a "
            "standalone AMT extension would. TPC's T25-0049 reconstructs the "
            "standalone counterfactual and implies roughly $855B. Both are "
            "published; the package figure is the one this benchmark's own "
            "description ('Keep higher exemptions instead of sunset to "
            "pre-TCJA levels', scored by CBO/JCT) asks for, and it is the only "
            "one of the two that is a scored provision rather than a baseline "
            "projection."
        ),
    ),
    # ------------------------------------------------------------------
    # Universal insulin cap — the sign was wrong, not the magnitude
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="universal_insulin_cap.v1",
        policy_id="universal_insulin_cap",
        official_10yr_billions=-15.0,
        source_name="Congressional Budget Office",
        source_date="2022",
        window="stated as 10-year; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="universal_insulin_cap.v2",
        reason=(
            "Points the wrong way. A $35 monthly cap is a *cost-sharing* cap: "
            "it moves a patient's liability onto the plan and onto the federal "
            "subsidy for that plan, so it adds to the deficit. CBO scores "
            "exactly this policy — a $35 cap extended from Medicare to private "
            "plans — as +$6.566B of outlays and -$4.793B of revenues, about "
            "+$11.4B ADDED to the deficit. The stored -$15B is a saving, and "
            "no CBO document produces it."
        ),
    ),
    CalibratedTarget(
        revision_id="universal_insulin_cap.v2",
        policy_id="universal_insulin_cap",
        official_10yr_billions=11.4,
        source_name="Congressional Budget Office",
        source_document=_CBO_57957,
        source_url=_CBO_57957_URL,
        source_date="2022-03",
        source_table="Estimated budgetary effects, by fiscal year, 2022-2031",
        source_row=(
            "Secs. 2 and 3, Cost-Sharing for Certain Insulin Products: "
            "estimated outlays 6,566; revenues -4,793"
        ),
        source_page="table p. 1",
        window="FY2022-2031",
        entered_commit=AMT_INSULIN_PROVENANCE_ENTERED_COMMIT,
        entered_date=AMT_INSULIN_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=AMT_INSULIN_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "$6.566B of added outlays plus $4.793B of forgone revenue is "
            "$11.359B of added deficit over FY2022-2031, carried here as the "
            "$11.4B the sourcing pass transcribed (0.4% of rounding)."
        ),
        note=(
            "cbo.gov returns HTTP 403 to every non-browser client, so the "
            "figures are corroborated against a second published account of "
            "the same table: InsideHealthPolicy, 'CBO: Insulin Cost Cap Hikes "
            "Spending $6.6B, Lowers Revenues $4.8B' (31 March 2022). The sign "
            "correction retires the repository's only benchmark that "
            "disagreed with its own model about what a policy *does*: lane L7 "
            "fixed the module side (it now scores +$7.0B) and this row fixes "
            "the target side, so the remaining ~39% is an accuracy statement "
            "rather than a direction dispute."
        ),
    ),
    # ------------------------------------------------------------------
    # Pillar Two — a point where the document publishes a range
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="pillar_two_adoption.v1",
        policy_id="pillar_two_adoption",
        official_10yr_billions=-80.0,
        source_name="JCT (2023)",
        source_date="2023",
        window="stated as 10-year; not traceable to any published scenario",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="pillar_two_adoption.v2",
        reason=(
            "-$80B is the midpoint of the '$50-120B' range "
            "`international.py` documents in its own module header, not a "
            "figure JCT publishes. JCT scored this policy under five "
            "scenarios and printed five numbers; none of them is $80B, and "
            "the two that describe the design this benchmark names span "
            "*both signs*. Superseded by a range rather than by another "
            "point: choosing one scenario would mean choosing the rest of "
            "the world's behaviour, which is not part of the US policy "
            "being scored, and the scenario the module's own mechanism "
            "matches is also the one it scores best against — exactly the "
            "selection this ledger exists to prevent."
        ),
    ),
    CalibratedTarget(
        revision_id="pillar_two_adoption.v2",
        policy_id="pillar_two_adoption",
        official_10yr_billions=None,
        published_low_10yr_billions=-102.6,
        published_high_10yr_billions=56.5,
        source_name="Joint Committee on Taxation",
        source_document=_JCX_22_23,
        source_url=_JCX_22_23_URL,
        source_date="2023-06",
        source_table=_JCX_22_23_TABLE,
        source_row=(
            "Scenario 4, 'Rest of the world does not enact Pillar Two; United "
            "States enacts Pillar Two in 2025, but no U.S. UTPR': +$102.6B of "
            "US receipts, i.e. -$102.6B of deficit. Scenario 2, 'Rest of the "
            "world enacts Pillar Two; United States enacts Pillar Two in "
            "2025, but no U.S. UTPR': -$56.5B of US receipts, i.e. +$56.5B of "
            "deficit."
        ),
        source_page="report p. 10",
        window="FY2023-2033",
        entered_commit=WAVE3_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE3_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE3_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The published target for 'the United States adopts Pillar Two "
            "with no U.S. UTPR' is a range, because JCT's own answer depends "
            "on a variable outside the policy: whether the rest of the world "
            "enacts. Its two scenarios for that design bracket the answer at "
            "-$102.6B and +$56.5B of deficit effect, and the range contains "
            "zero. That is the honest statement of what is known, and it is "
            "not expressible as a point."
        ),
        note=(
            "The two scenarios JCT publishes that are NOT this design are "
            "recorded so the bounds cannot be mistaken for a selection: "
            "Scenario 1 (rest of the world enacts, the US does not) loses "
            "$122.0B of US receipts, and Scenario 5 (the US enacts *with* a "
            "UTPR) gains $236.5B — a different instrument, which the module "
            "carries behind its own `adopt_utpr` flag and which this "
            "benchmark does not set. What follows for the scorecard: the "
            "model's -$61.2B is inside the range, distance to the nearest "
            "bound $0.0B, so the 23.5% this row reports against the carried "
            "-$80B is a distance from an editorial midpoint and is not a "
            "measurement of accuracy. The point figure is deliberately left "
            "where it is in the registries rather than moved to a bound: a "
            "range row's consistency check asks whether the carried figure "
            "lies inside the published bounds, and -$80B does."
        ),
    ),
    # ------------------------------------------------------------------
    # Wave 4. Phase E transcribed fourteen calibrated targets that disagree
    # with the document they cite and moved none of them. Waves 1-3 resolved
    # three. The eleven point revisions and one range below are the rest,
    # each with the same per-target test: does the module score the design
    # the document scored? Where the answer was no, the row is in
    # EXAMINED_NOT_REVISED instead, and there are five of those.
    # ------------------------------------------------------------------
    # Eliminate the SALT deduction — CBO's option is the policy label
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="eliminate_salt.v1",
        policy_id="eliminate_salt",
        official_10yr_billions=-1_200.0,
        source_name="JCT (2024)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published table",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="eliminate_salt.v2",
        reason=(
            "Attributed to JCT with no table behind it, and JCT has no clean "
            "counterpart: its nearest figure, JCX-46-17 item I.D.1, is "
            "$1,253.4B over FY2018-2027 but repeals most itemized deductions "
            "while *keeping* $10,000 of real property tax, so it is both "
            "broader and narrower than this policy. CBO, meanwhile, scores "
            "exactly this reform under exactly this label."
        ),
    ),
    CalibratedTarget(
        revision_id="eliminate_salt.v2",
        policy_id="eliminate_salt",
        official_10yr_billions=-1_621.0,
        source_name="Congressional Budget Office",
        source_document=_CBO_60557,
        source_url=_CBO_60557_URL,
        source_date="2024-12",
        source_table="Option 49, 'Eliminate or Limit Itemized Deductions'",
        source_row="Eliminate state and local tax deductions",
        source_page="report p. 59; PDF p. 65",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The same reform, scored by CBO under the same name, on the same "
            "ten-year window, and on the same lapsed-cap baseline the "
            "expenditure module's own `limitation` block already cites this "
            "very option for ('Beginning in 2026, deductions for state and "
            "local taxes will not be limited', report p. 59). Nothing in the "
            "module reads $1,621.0B, so this is a measurement rather than a "
            "mirror: PR #100 replaced the leaked `annual_cost_no_cap = 120.0` "
            "-- which was the superseded $1,200B target over ten -- with "
            "$89.55B computed from IRS SOI Table 2.1, and this revision "
            "retires the last echo of that constant."
        ),
        note=(
            "Baseline caveat, recorded rather than corrected: CBO's option is "
            "measured on the Feb/June 2024 baseline, where IRC 164(b)(6)'s "
            "$10,000 cap lapses after 2025. P.L. 119-21 has since raised the "
            "cap to $40,000 for 2025-2029 (indexed 1%/yr, phased down above "
            "$500,000 of MAGI, never below $10,000) and reverts it "
            "permanently to $10,000 from 2030, so a post-2025 'eliminate the "
            "SALT deduction' reform is no longer scored against a no-cap "
            "world for most of the window. Fixing that needs a "
            "baseline-vintage concept the expenditure module does not have; "
            "it is a model gap, not a target one. CBO's adjacent alternative "
            "-- eliminate *all* itemized deductions -- is $3,423.5B, which is "
            "the check that the transcribed row is the SALT-only one."
        ),
    ),
    # ------------------------------------------------------------------
    # Repeal the SALT cap — the $1.1T was PWBM's, against extended TCJA
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="repeal_salt_cap.v1",
        policy_id="repeal_salt_cap",
        official_10yr_billions=1_100.0,
        source_name="JCT (2024)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published table",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="repeal_salt_cap.v2",
        reason=(
            "The JCT attribution is wrong: JCT has never published a "
            "standalone score of repealing the $10,000 cap. What $1,100B "
            "*is* turns out to be findable -- it is Penn Wharton's figure, "
            "rounded, and the rounding hid the thing that matters about it. "
            "PWBM scores this reform twice in one paper, at -$1,116B against "
            "an extended-TCJA baseline and at -$197B against current law, a "
            "factor of 5.7 apart, because the cap was scheduled to expire "
            "after 2025 and a repeal therefore bit for one year. A target "
            "carried without its baseline is ambiguous by an order of "
            "magnitude, which is what this row was."
        ),
    ),
    CalibratedTarget(
        revision_id="repeal_salt_cap.v2",
        policy_id="repeal_salt_cap",
        official_10yr_billions=1_169.0,
        source_name="Penn Wharton Budget Model",
        source_document=_PWBM_SALT,
        source_url=_PWBM_SALT_URL,
        source_date="2024-02",
        source_table=(
            "Table 3, 'Conventional budget estimates: Policy Options for the "
            "SALT Cap Against Extended TCJA FY25-34'"
        ),
        source_row="Repeal SALT Cap",
        source_page=(
            "Table 3 (the 8 February 2024 brief as updated by its "
            "17 September 2024 addendum)"
        ),
        window="FY2025-2034, against an extended-TCJA baseline",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The published figure on the repository's own ten-year window, "
            "from the paper the carried number came from: 'This proposal, to "
            "eliminate the SALT cap entirely beginning in 2025, would cost an "
            "additional $1,169 billion over the 2025 to 2034 budget window.' "
            "The v1 row's $1,100B is PWBM's FY2024-2033 figure ($1,116B) "
            "rounded, so this moves the target onto the right decade as well "
            "as onto a document. The baseline now travels with it, which is "
            "the substantive change: this is the marginal, stacked cost of "
            "repeal *on top of* a permanent TCJA extension, i.e. against a "
            "permanent $10,000 cap -- and that is the counterfactual the "
            "expenditure module's derived path actually computes, since it "
            "prices repeal as (unlimited SALT expenditure - limited SALT "
            "expenditure) with the cap in force throughout."
        ),
        note=(
            "The same paper's Table 1, 'Against Current Law Baseline FY24-33', "
            "scores the identical reform at -$197B (-48 / -98 / -51 / zero "
            "thereafter), because under the law as it stood the cap expired "
            "after 2025. Both are published and they answer different "
            "questions; the extended-TCJA figure is the one the module's "
            "construction asks for. Two things a reader should know and this "
            "lane did not fix. (1) `eliminate_salt` is scored on the opposite "
            "baseline -- CBO Option 49 measures a world where the cap has "
            "lapsed -- so the repository's two SALT benchmarks now state "
            "contradictory baselines instead of hiding them; reconciling them "
            "needs a baseline-vintage concept the module does not have. "
            "(2) P.L. 119-21 sec. 70120 replaced the $10,000 cap with $40,000 "
            "for 2025, rising 1%/yr through 2029, phased down by 30% of MAGI "
            "above $500,000 but never below $10,000, and reverting "
            "permanently to $10,000 in 2030. 'Repeal the $10,000 cap' "
            "therefore describes no live reform for 2025-2029, and the "
            "nearest current-law anchor is JCT's own JCX-35-25 row for that "
            "provision, +$946.2B over FY2025-2034 -- already carried in this "
            "repository as `pl119_21_salt_cap_40k`, which is why it is an "
            "anchor and not a replacement target."
        ),
    ),
    # ------------------------------------------------------------------
    # Three Treasury FY2025 Green Book rows and one Treasury subtotal
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="biden_gilti_reform.v1",
        policy_id="biden_gilti_reform",
        official_10yr_billions=-280.0,
        source_name="Treasury (FY2025 Green Book)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published row",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="biden_gilti_reform.v2",
        reason=(
            "Credited to the volume that contains the proposal but to no row "
            "inside it. Treasury prints one figure for this proposal and it "
            "is 25% larger."
        ),
    ),
    CalibratedTarget(
        revision_id="biden_gilti_reform.v2",
        policy_id="biden_gilti_reform",
        official_10yr_billions=-373.9,
        source_name="U.S. Treasury, Office of Tax Analysis",
        source_document=_GREEN_BOOK_FY2025,
        source_url=_GREEN_BOOK_FY2025_URL,
        source_date="2024-03",
        source_table=_GREEN_BOOK_TABLE,
        source_row=(
            "Revise the global minimum tax regime, limit inversions, and make "
            "related reforms"
        ),
        source_page="report p. 239; PDF p. 247",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "$373,919 million, the only figure Treasury publishes for the "
            "proposal this benchmark names, on the repository's own window. "
            "The proposal text (report p. 29) is the design the module "
            "constructs: the QBAI exemption eliminated, the rate to 21%, and "
            "a jurisdiction-by-jurisdiction calculation."
        ),
        note=(
            "The row title bundles 'limit inversions, and make related "
            "reforms' with the minimum-tax change, and Treasury publishes no "
            "split, so the target is the whole proposal where the module "
            "carries only the minimum-tax legs. That is a bundle caveat, not "
            "a different policy -- the anti-inversion rules are the same "
            "proposal's ancillary provisions -- and it is the reason to read "
            "the residual as an upper bound on the module's own miss. Two "
            "earlier vintages of the same row, for scale on how much this "
            "number moves: FY2022 $533,503M (FY2022-2031, the title the "
            "repository's description was copied from) and FY2024 $493,341M "
            "(FY2024-2033). GILTI's two self-declared calibration constants "
            "(`gilti_cbc_revenue_multiplier`, `gilti_ftc_offset_rate`) were "
            "set against the superseded -$280B and are deliberately not "
            "retuned here: closing the gap by re-fitting is the move this "
            "ledger exists to make visible rather than to invite."
        ),
    ),
    CalibratedTarget(
        revision_id="fdii_repeal.v1",
        policy_id="fdii_repeal",
        official_10yr_billions=-200.0,
        source_name="Treasury (FY2025 Green Book)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published row",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="fdii_repeal.v2",
        reason=(
            "-$200B matches neither figure Treasury prints for this proposal: "
            "not the gross repeal row ($157,993M, 21% away) and not the "
            "volume's own 'Subtotal, Repeal the deduction for foreign-derived "
            "intangible income' of $0, which nets the repeal against the "
            "R&D-support proposal Treasury pairs it with one-for-one."
        ),
    ),
    CalibratedTarget(
        revision_id="fdii_repeal.v2",
        policy_id="fdii_repeal",
        official_10yr_billions=-158.0,
        source_name="U.S. Treasury, Office of Tax Analysis",
        source_document=_GREEN_BOOK_FY2025,
        source_url=_GREEN_BOOK_FY2025_URL,
        source_date="2024-03",
        source_table=_GREEN_BOOK_TABLE,
        source_row="Repeal the deduction for foreign-derived intangible income",
        source_page="report p. 239; PDF p. 247",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The gross row is the design the module scores. "
            "`InternationalTaxPolicy` repeals the section 250 deduction and "
            "applies no research-and-development offset, so Treasury's $0 "
            "subtotal scores a two-provision package the module does not "
            "construct while the $157,993M row scores the one it does."
        ),
        note=(
            "Not leakage: the module's repeal identity runs on FDII income "
            "inverted from Treasury OTA's *tax expenditure* for the deduction "
            "($13.023B/yr, Tax Expenditures FY2026 Table 1 line 5), which is "
            "a different published series from this repeal row. The two do "
            "not agree, and the module's own docstring says why: Treasury's "
            "$157,993M repeals the deduction on a baseline that already "
            "carries the same volume's 28% corporate rate, and "
            "13.023 x 10 x (28/21) = $173.6B before behaviour, which is where "
            "the row's ~21% premium over the tax expenditure comes from. "
            "Earlier vintages of the same pair: FY2022 gross $123,943M / net "
            "$0; FY2024 gross $115,621M / net $0."
        ),
    ),
    CalibratedTarget(
        revision_id="biden_full_international.v1",
        policy_id="biden_full_international",
        official_10yr_billions=-700.0,
        source_name="Treasury (FY2025)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published row",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="biden_full_international.v2",
        reason=(
            "A round number 10.7% above Treasury's own printed subtotal for "
            "the package this benchmark names, and the description behind it "
            "named a 'BEAT replacement' that is not in the FY2025 volume at "
            "all -- SHIELD was an FY2022 row ($390,051M) that the undertaxed "
            "profits rule replaced."
        ),
    ),
    CalibratedTarget(
        revision_id="biden_full_international.v2",
        policy_id="biden_full_international",
        official_10yr_billions=-632.2,
        source_name="U.S. Treasury, Office of Tax Analysis",
        source_document=_GREEN_BOOK_FY2025,
        source_url=_GREEN_BOOK_FY2025_URL,
        source_date="2024-03",
        source_table=_GREEN_BOOK_TABLE,
        source_row="Subtotal, Reform International Taxation",
        source_page="report p. 240; PDF p. 248",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "This benchmark's design *is* the package, and Treasury prints "
            "the package's subtotal: $632,200 million. Unlike "
            "`biden_estate_reform`, where the module constructs a narrow "
            "reform and the document totals a ten-section bill, here the "
            "label and the document agree about the object and it is the "
            "module that is short of it."
        ),
        note=(
            "What the residual now measures, stated so it is not read as "
            "accuracy: the three provisions the module implements sum to "
            "$510,232M inside this subtotal (global minimum tax $373,919M + "
            "undertaxed profits rule $136,313M + FDII net $0), so roughly a "
            "fifth of the target is provisions `international.py` does not "
            "carry. The superseded -$700B was larger still, so the move is "
            "toward the document in both senses."
        ),
    ),
    CalibratedTarget(
        revision_id="biden_eitc_childless.v1",
        policy_id="biden_eitc_childless",
        official_10yr_billions=178.0,
        source_name="JCT (2021)",
        source_date="2021",
        window="stated as ten-year; not traceable to any published row",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="biden_eitc_childless.v2",
        reason=(
            "Credited to JCT in 2021 with no table behind it, while the "
            "proposal the benchmark scores is a Treasury one with a printed "
            "figure 9.5% lower on the repository's own window."
        ),
    ),
    CalibratedTarget(
        revision_id="biden_eitc_childless.v2",
        policy_id="biden_eitc_childless",
        official_10yr_billions=162.6,
        source_name="U.S. Treasury, Office of Tax Analysis",
        source_document=_GREEN_BOOK_FY2025,
        source_url=_GREEN_BOOK_FY2025_URL,
        source_date="2024-03",
        source_table=_GREEN_BOOK_TABLE,
        source_row=(
            "Restore and make permanent the American Rescue Plan expansion of "
            "the earned income tax credit for workers without qualifying "
            "children"
        ),
        source_page="report p. 242; PDF p. 250",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "$162,553 million, Treasury's published cost of exactly the "
            "design the credits module constructs -- the ARP childless "
            "expansion restored and made permanent, with the age range "
            "widened and the maximum credit roughly tripled. Footnote /3 on "
            "the row confirms it includes the outlay effect of the refundable "
            "portion, which is the leg the module's microsimulation prices."
        ),
        note=(
            "The credits module's per-unit constant reproduces the superseded "
            "$178B, so this revision converts a bookkeeping 0.0% into a real "
            "9.5% and nothing is retuned to close it. The held-out reading is "
            "the one to quote: `run_loo.py` derives this case from CPS ASEC "
            "tax units and never touches the fitted annual."
        ),
    ),
    # ------------------------------------------------------------------
    # IRS enforcement — CBO's own revised revenue figure
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="ira_enforcement.v1",
        policy_id="ira_enforcement",
        official_10yr_billions=-200.0,
        source_name="CBO (2022)",
        source_date="2022",
        window="stated as FY2025-2034; CBO's figure is FY2022-2031",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="ira_enforcement.v2",
        reason=(
            "The record's own description called it 'the rounded revenue "
            "side', and it rounds the wrong estimate: -$200B is 11% above "
            "CBO's current figure and 2% below the one CBO explicitly "
            "superseded ($203.7B). Carrying a withdrawn estimate is worse "
            "than carrying a round one."
        ),
    ),
    CalibratedTarget(
        revision_id="ira_enforcement.v2",
        policy_id="ira_enforcement",
        official_10yr_billions=-180.4,
        source_name="Congressional Budget Office",
        source_document=_CBO_58390,
        source_url=_CBO_58390_URL,
        source_date="2022-08",
        source_table="Letter text",
        source_row=(
            "revenues will increase by $180.4 billion over the 2022-2031 "
            "period"
        ),
        source_page="letter p. 1",
        window="FY2022-2031",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "CBO's own current estimate of the revenue effect of the "
            "Inflation Reduction Act's IRS enforcement funding, which is the "
            "quantity this benchmark and the enforcement module both score. "
            "It explicitly revises CBO's earlier $203.7B."
        ),
        note=(
            "Two mismatches this revision does *not* close, both of them "
            "model findings rather than target ones. (1) CBO's $180.4B is the "
            "revenue side; the *net* deficit effect is roughly $101B once the "
            "$79B appropriation is counted, and this benchmark scores the "
            "revenue side by construction. (2) CBO says the act provides $79B "
            "of total IRS funding of which $46B is enforcement, where the "
            "module assumes $80B of enforcement funding -- so the module "
            "prices a larger dose than the one CBO scored. The enforcement "
            "module's ROI multiplier was fitted to the superseded -$200B, so "
            "this row leaves the fitted tier."
        ),
    ),
    # ------------------------------------------------------------------
    # EV credits — the two sections the module names, summed from JCT
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="repeal_ev_credits.v1",
        policy_id="repeal_ev_credits",
        official_10yr_billions=-200.0,
        source_name="CBO (July 2025)",
        source_date="2025-07",
        window="stated as FY2025-2034",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="repeal_ev_credits.v2",
        reason=(
            "Attributed to CBO; the estimate is JCT's. And -$200B is 9.7% "
            "above the sum of the two sections the module's own stated scope "
            "names, which JCT prints as separate rows in the document the "
            "record already links."
        ),
    ),
    CalibratedTarget(
        revision_id="repeal_ev_credits.v2",
        policy_id="repeal_ev_credits",
        official_10yr_billions=-182.3,
        source_name="Joint Committee on Taxation",
        source_document=_JCX_35_25,
        source_url=_JCX_35_25_URL,
        source_date="2025-07",
        source_table="Chapter 5, Subchapter A, fiscal years 2025-2034",
        source_row=(
            "Termination of clean vehicle credit (sec. 30D) 77,829 + "
            "Termination of qualified commercial clean vehicles credit "
            "(sec. 45W) 104,516"
        ),
        source_page="p. 3 (PDF p. 5)",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "$77,829M + $104,516M = $182,345M, the sum of exactly the two "
            "sections the climate module's stated scope names, from JCT's own "
            "line items. Both rows are already transcribed in this repository "
            "in `data_files/validation/pl119_21_jct_line_items.csv`, so the "
            "target is now the same arithmetic the P.L. 119-21 block reads."
        ),
        note=(
            "The Phase E record transcribed this sum as -$182.4B; the two "
            "rows add to $182.345B, so the figure is corrected to -$182.3B "
            "here and the source record is corrected with it. Adding the "
            "previously-owned clean vehicle credit (sec. 25E, $7.4B) would "
            "give $189.8B, and the module does not score it. For scale on how "
            "far this number has travelled, JCX-18-22 scored the same credits "
            "at $14.2B over FY2022-2031."
        ),
    ),
    # ------------------------------------------------------------------
    # Enhanced premium tax credits — the figure and its vintage disagreed
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="extend_enhanced_ptc.v1",
        policy_id="extend_enhanced_ptc",
        official_10yr_billions=350.0,
        source_name="CBO (2024)",
        source_date="2024",
        window="stated as FY2025-2034; the figure is a FY2026-2035 one",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="extend_enhanced_ptc.v2",
        reason=(
            "The number and its stated vintage disagree by one budget window. "
            "$350B is CBO/JCT's *September 2025* re-estimate (publication "
            "61734) over FY2026-2035, reported by CRS R48290 as "
            "'approximately $350 billion'; CBO's 2024 estimate, which is what "
            "the record claims and what the repository's FY2025-2034 window "
            "asks for, is $335B. A target whose window does not match the "
            "window the record declares is not a target, it is two."
        ),
    ),
    CalibratedTarget(
        revision_id="extend_enhanced_ptc.v2",
        policy_id="extend_enhanced_ptc",
        official_10yr_billions=335.0,
        source_name="Congressional Budget Office / Joint Committee on Taxation",
        source_document=_CBO_60437,
        source_url=_CBO_60437_URL,
        source_date="2024-06",
        source_table="Letter text (CBO's June 2024 baseline)",
        source_row=(
            "CBO and JCT estimate that making the policy permanent would "
            "increase the budget deficit by $335 billion over the 2025-2034 "
            "period"
        ),
        source_page="letter p. 1",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The 2024 CBO/JCT estimate the record names, on the window the "
            "record declares, of the design the module scores: making "
            "permanent the ARP premium-tax-credit expansion later extended "
            "through 2025. The letter decomposes it as a $415B increase in "
            "the cost of the credit -- $250B of outlays and $164B of forgone "
            "revenue -- against $80B of offsetting effects."
        ),
        note=(
            "The letter is addressed to Chairman Jodey Arrington and Chairman "
            "Jason Smith; the Phase E record said Sen. Crapo, and that is "
            "corrected here. The September 2025 re-estimate (publication "
            "61734, ~$350B over FY2026-2035) is the superseded figure and "
            "remains the right target for anyone scoring on a FY2026-2035 "
            "window; some outlets carried $383B, which is $335B plus $48B of "
            "debt service. The PTC module's annual is fitted to the "
            "superseded $350B, so this row leaves the fitted tier and its "
            "residual becomes a measurement."
        ),
    ),
    # ------------------------------------------------------------------
    # Tariffs — three targets, three different failures
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="trump_universal_10.v1",
        policy_id="trump_universal_10",
        official_10yr_billions=-2_000.0,
        source_name="Tax Foundation / Yale Budget Lab",
        source_date="2024",
        window="stated as FY2025-2034",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="trump_universal_10.v2",
        reason=(
            "The conventional figure rounded down, carried with a second "
            "attribution that scores nothing: Yale publishes no standalone "
            "ten-year figure for a 10% universal tariff. Rounding $2,171.1B "
            "to '$2T' also puts the target 7.9% from the only published "
            "estimate of this policy, and close enough to Tax Foundation's "
            "*dynamic* $1,721B to be misread as one."
        ),
    ),
    CalibratedTarget(
        revision_id="trump_universal_10.v2",
        policy_id="trump_universal_10",
        official_10yr_billions=-2_171.1,
        source_name="Tax Foundation",
        source_document=_TF_FF861,
        source_url=_TF_FF861_URL,
        source_date="2025-04",
        source_table="Table 3, 'Conventional Revenue Estimates, in Billions'",
        source_row="10 Percent Universal Tariff, column 2025-2034",
        source_page="report p. 4",
        window="2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The published conventional estimate of exactly this policy, on "
            "the repository's window, from the table's own row. Conventional "
            "is the right tier: Tax Foundation's conventional tariff scores "
            "already net the income-and-payroll offset (averaging 26.2% in "
            "FF861), which is the offset lane L8 built into `trade.py`, so "
            "the two now measure the same object."
        ),
        note=(
            "Tax Foundation's other two tiers for the same policy, recorded "
            "so the conventional figure cannot be mistaken for a choice among "
            "them: $1,720.8B dynamic and $1,442.5B dynamic with tit-for-tat "
            "retaliation (Table 5, report p. 8). FF861's method, for anyone "
            "checking the comparison: import elasticity -0.997, 8% "
            "noncompliance, and revenue computed on the tax-inclusive rate "
            "t/(1+t). Lane L8 already de-fitted this row -- "
            "`universal_coverage_rate` became a Census measurement -- so no "
            "constant is fitted to either the superseded figure or this one."
        ),
    ),
    CalibratedTarget(
        revision_id="auto_tariff_25.v1",
        policy_id="auto_tariff_25",
        official_10yr_billions=-100.0,
        source_name="Committee for a Responsible Federal Budget (2024)",
        source_date="2024",
        window="stated as FY2025-2034",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="auto_tariff_25.v2",
        reason=(
            "Not a scorekeeper estimate at all, and not a ten-year one. CRFB, "
            "the stated source, itemises no auto tariff in any of its "
            "tariff-revenue posts. The figure traces instead to a White House "
            "claim -- Peter Navarro, 30 March 2025, 'We're going to raise "
            "about $100 billion with the auto tariffs alone' -- which was "
            "stated *per year*, inside the '$6 to $7 trillion over the "
            "10-year period' that FactCheck.org and the Washington Post Fact "
            "Checker both ran down as unsupported. So this is the same "
            "failure mode as `extend_tcja_amt`: a short-window figure sitting "
            "in a ten-year column, here by a factor of ten."
        ),
    ),
    CalibratedTarget(
        revision_id="auto_tariff_25.v2",
        policy_id="auto_tariff_25",
        official_10yr_billions=-386.2,
        source_name="Tax Foundation",
        source_document=_TF_TRACKER,
        source_url=_TF_TRACKER_URL,
        source_date="2026-08",
        source_table="Table 5, 'Detailed Tariff Revenue Estimates'",
        source_row=(
            "Section 232 Autos, Heavy Trucks, Buses, and Parts, conventional "
            "revenue column"
        ),
        source_page="Table 5 (2026-2035 column)",
        window="2026-2035",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The only ten-year conventional estimate printed as a table row "
            "for the design this preset describes -- '25% tariff on imported "
            "vehicles and parts'. Same publisher, same model family and same "
            "revenue tier as `trump_universal_10`'s FF861 row, so the two "
            "trade benchmarks are now scored against one methodology instead "
            "of against a talking point and a table."
        ),
        note=(
            "A point rather than a range, and the reason is that the second "
            "published figure is not a second estimate of the same thing. "
            "Yale Budget Lab (28 March 2025) put 25% auto tariffs at "
            "'$600-650 billion over 2026-35', but that scores the tariff *as "
            "announced*, before the trade-deal carve-outs and US-content "
            "exceptions that the Tax Foundation tracker's as-in-force row "
            "reflects. A range across the two would assert a bracket neither "
            "publisher supports. The design gaps that remain are stated "
            "rather than adjusted: the transcribed row bundles heavy trucks "
            "and buses (at 10%, not 25%) and auto parts with passenger "
            "vehicles, and neither publisher applies the 65% USMCA carve-out "
            "`trade.py` models -- they model US-content exceptions instead. "
            "The source is a living tracker, so the revision it was read at "
            "is part of the citation."
        ),
    ),
    CalibratedTarget(
        revision_id="reciprocal_tariffs.v1",
        policy_id="reciprocal_tariffs",
        official_10yr_billions=-1_200.0,
        source_name="Yale Budget Lab / Tax Foundation (2024)",
        source_date="2024",
        window="stated as FY2025-2034",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="reciprocal_tariffs.v2",
        reason=(
            "A tier error, not a magnitude error. -$1,200B is exactly Tax "
            "Foundation's *dynamic* score of the reciprocal tariffs, sitting "
            "in a scorecard whose every other target is conventional -- and "
            "below all three published conventional estimates of the same "
            "policy. Superseded by a range rather than by another point "
            "because the three modellers who scored it disagree by 29% and "
            "none of their figures is more authoritative than the others."
        ),
    ),
    CalibratedTarget(
        revision_id="reciprocal_tariffs.v2",
        policy_id="reciprocal_tariffs",
        official_10yr_billions=None,
        published_low_10yr_billions=-1_800.0,
        published_high_10yr_billions=-1_400.0,
        source_name="Committee for a Responsible Federal Budget",
        source_document=_CRFB_TARIFFS,
        source_url=_CRFB_TARIFFS_URL,
        source_date="2025-04",
        source_table=(
            "'Ten-Year Scores of Trump's Tariffs, If Made Permanent', "
            "fiscal years 2025-2034"
        ),
        source_row=(
            "Reciprocal Tariffs: conventional $1.8 trillion (CRFB), $1.5 "
            "trillion (Tax Foundation), $1.4 trillion (Yale Budget Lab); "
            "dynamic $1.6 / $1.2 / $1.0 trillion"
        ),
        source_page="the post's only table",
        window="FY2025-2034",
        entered_commit=WAVE4_PROVENANCE_ENTERED_COMMIT,
        entered_date=WAVE4_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=WAVE4_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "Three organisations scored the same announced schedule on the "
            "same fiscal window and published conventional figures spanning "
            "$1.4T to $1.8T. That spread is the honest target: it is "
            "disagreement between models about one policy, which is exactly "
            "what a range row asserts and a point cannot. The carried figure "
            "moves to the middle of the three -- Tax Foundation's $1.5T "
            "conventional -- because Tax Foundation is the publisher the "
            "repository's other two tariff benchmarks are scored against, so "
            "the anchor is a published figure from the transcribed table "
            "rather than an invented midpoint."
        ),
        note=(
            "Design caveat that the range does not close: the published "
            "estimates score the April 2025 schedule -- a 10% floor rising to "
            "50%, set by halving each partner's bilateral-deficit-to-imports "
            "ratio, and exempting steel, aluminium, autos and auto parts, "
            "copper, pharmaceuticals, semiconductors and lumber -- while "
            "`trade.py` applies a flat ~20pp to a `reciprocal_coverage_rate` "
            "of 0.50. The exemptions make 'about half of goods imports' a "
            "fair characterisation of the base, but the flat rate is the "
            "module's assumption and no publisher scores it. An internal "
            "cross-check on the scale: FF861 puts a 20% tariff on *all* "
            "imports at $3,399.7B conventional, so ~20pp on half of imports "
            "lands near $1,700B, inside this range and well above the "
            "superseded point. Separately, the tariffs these figures score "
            "were struck down by the Supreme Court in February 2026; the "
            "benchmark scores the policy, not its legal survival."
        ),
    ),
    # ------------------------------------------------------------------
    # Trump corporate 15% — the target was this model's own output
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="trump_corporate_15.v1",
        policy_id="trump_corporate_15",
        official_10yr_billions=1_920.0,
        source_name="none (this repository's own model output)",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="trump_corporate_15.v2",
        reason=(
            "Not a target at all. The scenario's own note reads 'No official "
            "score; expected estimate derived from model', and Phase E "
            "labelled it `model_estimate` on exactly that admission -- so "
            "every error the row has ever reported was a distance from this "
            "model's own answer. PR #119 showed how thin even that was: the "
            "module's annual reproduced +$1,920B only because "
            "`estimate_behavioral_offset` returned `abs(static)`, adding 12.5% "
            "of a rate CUT's static effect to the deficit instead of taking it "
            "off, and signing the offset moved the row 0.1% -> 22.3% with no "
            "constant touched. Superseded rather than retired because two "
            "primary published conventional estimates of the same statutory "
            "rate change exist on this repository's own window; retiring a "
            "benchmark that has a document is the failure mode this ledger "
            "exists to prevent."
        ),
    ),
    CalibratedTarget(
        revision_id="trump_corporate_15.v2",
        policy_id="trump_corporate_15",
        official_10yr_billions=None,
        published_low_10yr_billions=595.0,
        published_high_10yr_billions=673.1,
        source_name="Tax Foundation (anchor); Penn Wharton Budget Model",
        source_document=_TF_CORPORATE_15,
        source_url=_TF_CORPORATE_15_URL,
        source_date="2024-07",
        source_table=(
            "Table 2, 'Revenue Effects of Reducing the Corporate Rate to 15 "
            "Percent (Billions)'"
        ),
        source_row=(
            "Conventional revenue, 2025-2034: -$673.1B (Tax Foundation); "
            "PWBM Table 1, 'Lower the corporate income tax rate to 15%', "
            "-$595B over 2025-2034"
        ),
        source_page="Table 2 (the post's only revenue table)",
        window="FY2025-2034",
        entered_commit=CORPORATE_PTC_PROVENANCE_ENTERED_COMMIT,
        entered_date=CORPORATE_PTC_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=CORPORATE_PTC_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "Two houses scored the same reform -- 21% to 15% for all "
            "corporations -- on this repository's own FY2025-2034 window and "
            "published conventional figures 13% apart, and CRFB's 6 September "
            "2024 post prints both side by side. That spread is the honest "
            "target, so the row takes a range on the mechanism Wave 3 built "
            "for `pillar_two_adoption` and Wave 4 used for "
            "`reciprocal_tariffs`. The carried anchor is Tax Foundation's "
            "$673.1B, on a rule that has nothing to do with the model: "
            "Tax Foundation's is a STANDALONE analysis of this one reform "
            "with its own revenue table, while PWBM's is one stacked row "
            "inside a whole-campaign package and therefore carries "
            "interaction with the rest of the package. The anchor is a "
            "published figure from a transcribed table, never a midpoint."
        ),
        note=(
            "Three things a reader needs before quoting this row's error. "
            "(1) SCOPE. `create_republican_corporate_cut` sets "
            "`extend_bonus_depreciation=True`, and neither published figure "
            "includes bonus depreciation -- PWBM prints it separately inside "
            "'Extend the business tax provisions of TCJA' (-$623B). Measured "
            "on this branch, the module's bonus-depreciation leg is "
            "**+$294.15B** of the model's +$1,491.8B in `reported` mode "
            "(+$287.06B of +$1,698.6B in `derived`), so the rate leg alone "
            "reads +$1,197.6B, or +77.9% against the anchor rather than "
            "+121.6%. The scope gap is stated rather than adjusted away: no "
            "published figure scores rate-plus-bonus-depreciation as one line, "
            "and summing two rows from PWBM's table would be constructing a "
            "target rather than reading one. (2) DIRECTION. Tax Foundation's "
            "Options 2.0 is the only document that prices both directions in "
            "one edition and one model -- 21%->28% at $126.6B per point and "
            "21%->15% at $163.2B per point -- so a point of CUT costs 29% more "
            "than a point of increase yields, and `corporate.py` prices both "
            "at the same per-point rate. (3) The rest is the level "
            "`planning/memos/CORPORATE_PER_POINT_YIELD.md` documents: the "
            "module's implied marginal base is 82-91% of the average base "
            "against 55-64% for every published estimator. Dynamic figures, "
            "carried so nobody mistakes the tier: Tax Foundation -$459.5B; "
            "PWBM publishes no dynamic dollar figure for the line. CRFB's own "
            "$200B is a DIFFERENT policy -- a revived section 199 deduction "
            "reaching a 15% effective rate for domestic manufacturers only -- "
            "and is not a bound of this range. Low bound: "
            + _PWBM_TRUMP_2024
            + " ("
            + _PWBM_TRUMP_2024_URL
            + "). Both figures printed together in "
            + _CRFB_CORPORATE_15
            + " ("
            + _CRFB_CORPORATE_15_URL
            + ")."
        ),
    ),
    # ------------------------------------------------------------------
    # H9 — the Social Security donut hole: a think-tank explainer's figure
    # standing in for a printed CBO row on this repository's own window
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="ss_donut_250k.v1",
        policy_id="ss_donut_250k",
        official_10yr_billions=-2_700.0,
        source_name="Social Security Trustees (as credited by the record)",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="ss_donut_250k.v2",
        reason=(
            "The credited source does not publish it. SSA's Office of the "
            "Chief Actuary does score this provision -- E2.5, 'Apply 12.4 "
            "percent payroll tax rate on earnings above $250,000 starting in "
            "2026... Do not provide benefit credit' -- and its run 418 tables "
            "report only percent of taxable payroll (+2.50%) and a depletion "
            "date moving 2034 to 2057. Lane HSA_h13 verified that the words "
            "'billion' and 'trillion' do not appear once in the whole "
            "six-page provisions category summary. The '$2.7 trillion over 10 "
            "years' traces to a Peter G. Peterson Foundation explainer with "
            "no report year, no run number and no window. Superseded rather "
            "than left, because a published ten-year dollar score of the SAME "
            "design exists on this repository's own window -- and it is 47% "
            "below. `payroll.py` documents its own arithmetic ('2_177.0  # "
            "270 / 0.124'), so the 0.0% this row reported was the target "
            "divided by ten, divided by the statutory rate, times the rate, "
            "times ten. No constant was retuned."
        ),
    ),
    CalibratedTarget(
        revision_id="ss_donut_250k.v2",
        policy_id="ss_donut_250k",
        official_10yr_billions=-1_426.8,
        source_name="Congressional Budget Office (data source: JCT and CBO)",
        source_document=_CBO_60557,
        source_url=_CBO_60557_URL,
        source_date="2024-12",
        source_table=(
            "Option 62, 'Increase the Maximum Taxable Earnings for the Social "
            "Security Payroll Tax', table stub 'Decrease (-) in the deficit', "
            "column 2025-2034"
        ),
        source_row="Subject earnings greater than $250,000 to payroll taxes",
        source_page="report p. 73 (PDF p. 79)",
        window="FY2025-2034",
        entered_commit=H9_PROVENANCE_ENTERED_COMMIT,
        entered_date=H9_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=H9_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "Same design, this repository's own window, and CBO is already "
            "the publisher the sibling alternative in the same option is "
            "scored against (`ss_cap_90_pct`). CBO's own text matches the "
            "module's shape twice over: 'The second alternative would apply "
            "the 12.4 percent payroll tax to earnings over $250,000 in "
            "addition to earnings below the maximum taxable amount under "
            "current law... The taxable maximum would continue to grow with "
            "average wages, but the $250,000 threshold would not change, so "
            "the gap between the two would shrink', and 'The current-law "
            "taxable maximum would still be used for calculating benefits, so "
            "scheduled benefits would not change under this alternative' -- "
            "which is OCACT E2.5's 'do not provide benefit credit'. Adopted "
            "although it makes the row far worse (0.0% -> 89.2%): the "
            "document is the reason, not the distance."
        ),
        note=(
            "BASIS. The 2024 volume prints one stub for both alternatives, "
            "'Decrease (-) in the deficit', where the 2018 and 2020 volumes "
            "printed 'Change in Revenues' separately; so $1,426.8B is a "
            "deficit figure and the payroll module scores a deficit effect "
            "too. Two wedges, both stated rather than adjusted. (1) CBO's "
            "table note reads 'An offset to reflect reduced income and "
            "payroll taxes has been applied to the estimates in this table', "
            "and the module has no income-tax offset channel, so the model's "
            "figure sits above CBO's for a reason independent of the base. "
            "(2) Footnote 'a' -- 'Estimates include increased outlays for "
            "additional payments of Social Security benefits' -- is attached "
            "to alternative 1 ONLY, because this alternative changes no "
            "scheduled benefit. So the benefit-outlay wedge that makes "
            "`ss_cap_90_pct`'s revenue and deficit lines differ does not "
            "exist here. VINTAGES: the same alternative reads $1,222.6B "
            "(2018 volume, revenue, FY2019-2028), $1,024.0B (2020 volume, "
            "revenue, FY2021-2030) and $1,203.9B (2022 volume, deficit, "
            "FY2023-2032). Four windows, not four estimators, so this is a "
            "point revision and not a range. cbo.gov returns HTTP 403 to "
            "scripted clients; the figure is independently in this "
            "repository already, transcribed with its annual path by "
            "`scripts/extract_cbo_options.py` to "
            "`data_files/validation/cbo_options_2025_2034_alternatives.csv` "
            "(row 62.2)."
        ),
    ),
    # ------------------------------------------------------------------
    # H9 — TCJA rates only: a single published row existed all along
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="tcja_rates_only.v1",
        policy_id="tcja_rates_only",
        official_10yr_billions=3_185.0,
        source_name="none (this repository's own decomposition)",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="tcja_rates_only.v2",
        reason=(
            "The scenario's own note says what it is: 'Rate cuts only: ~$3.2T "
            "calibrated. This is an illustrative scenario.' Phase E labelled "
            "it `model_estimate` on that admission. What the sourcing pass "
            "found is that a single published row for exactly this provision "
            "has existed since May 2024, in the same table, the same column "
            "and the same window this repository already reads "
            "`extend_tcja_amt`'s $1,357.1B out of -- and it is a third "
            "smaller. No summing was required, so PR #122's rule against "
            "constructing a target by adding rows never came into play."
        ),
    ),
    CalibratedTarget(
        revision_id="tcja_rates_only.v2",
        policy_id="tcja_rates_only",
        official_10yr_billions=2_158.7,
        source_name="Congressional Research Service (transcribing CBO/JCT)",
        source_document=_CRS_R48286,
        source_url=_CRS_R48286_URL,
        source_date="2024-11",
        source_table=_CRS_R48286_TABLE,
        source_row="Reduced Individual Tax Rates",
        source_page="Table 1 (FY2025-FY2034 column)",
        window="FY2025-2034",
        entered_commit=H9_PROVENANCE_ENTERED_COMMIT,
        entered_date=H9_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=H9_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "$2,158.7B over FY2025-2034 ($821.8B over FY2025-2029), read from "
            "the row CRS labels 'Reduced Individual Tax Rates' and CBO's own "
            "supplemental workbook labels '10%, 12%, 22%, 24%, 32%, 35%, and "
            "37% income tax rate brackets' (estimator: JCT, effective tyba "
            "12/31/25). Adopted because it is the same document, table, "
            "column and window as the AMT row this repository already scores "
            "`extend_tcja_amt` against, and because the scenario it replaces "
            "was declared illustrative by its own author. It makes the row "
            "much worse (2.2% -> 44.3%), which is the point: a decomposition "
            "of a fitted aggregate reproducing itself was never evidence."
        ),
        note=(
            "The standard deduction ($1,251.0B), personal-exemption repeal "
            "(-$1,717.5B), child credit, QBI and AMT are separate rows in the "
            "same table, so this is the rate structure alone -- which is the "
            "scenario's own design (`extend_all=False`, `extend_rates=True`, "
            "everything else False). CRS's table note is carried with it: "
            "'The revenue cost depends on the order of estimation due to "
            "interactions between the provisions.' Corroborated from the "
            "other side by JCT's JCX-35-25 p. 1 row 1, 'Extension and limited "
            "enhancement of reduced rates', -$2,193.4B over the same window "
            "-- 1.6% away, and not adopted because the 'limited enhancement' "
            "is P.L. 119-21's, not TCJA's."
        ),
    ),
    # ------------------------------------------------------------------
    # H9 — estate tax repeal: a `model_estimate` with a published score
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="eliminate_estate_tax.v1",
        policy_id="eliminate_estate_tax",
        official_10yr_billions=350.0,
        source_name="none (this repository's own model output)",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="eliminate_estate_tax.v2",
        reason=(
            "Never a target: the scenario's source field literally reads "
            "'Model estimate', and the module reproduced it to the cent. A "
            "published ten-year score of estate-tax repeal on a CURRENT-LAW "
            "baseline now exists, which is what was missing before -- JCT's "
            "only repeal-era figures are bundled with the exemption doubling "
            "and the 35% gift rate (JCX-46-17 row H, -$171.5B; JCX-54-17 row "
            "G, -$150.7B; the conference agreement dropped repeal entirely), "
            "and CBO/JCT's standalone score of the Death Tax Repeal Act of "
            "2015 ($269B, FY2015-2025) prices repeal of a tax with a $5.43M "
            "exemption, a materially different instrument."
        ),
    ),
    CalibratedTarget(
        revision_id="eliminate_estate_tax.v2",
        policy_id="eliminate_estate_tax",
        official_10yr_billions=407.2,
        source_name="Tax Foundation",
        source_document=_TF_OPTIONS_3,
        source_url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "eliminate-the-estate-and-gift-tax/"
        ),
        source_date="2026-07",
        source_table="Option 83, table '10-Year Change in the Deficit, 2027-2036'",
        source_row="Conventional Primary Deficit Change",
        source_page="printed p. 105",
        window="CY2027-2036",
        entered_commit=H9_PROVENANCE_ENTERED_COMMIT,
        entered_date=H9_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=H9_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "'This option repeals the estate and gift taxes', scored on the "
            "post-P.L. 119-21 baseline this repository's own scoring assumes "
            "($15M individual / $30M joint exemption, 40% top rate): "
            "+$407.2B conventional primary deficit, +$489.4B total. It is "
            "adopted where the two agency figures are not, because both of "
            "those price a different instrument -- a bundle in 2017, and a "
            "$5.43M-exemption tax in 2015. Tax Foundation is already the "
            "publisher four benchmarks here are anchored on, and this is a "
            "standalone option with its own printed table."
        ),
        note=(
            "SCOPE: the option repeals the estate tax AND the gift tax, where "
            "`create_eliminate_estate_tax` constructs estate repeal; CRS "
            "R48183 (p. 16) puts the estate share at about 90% of estate and "
            "gift receipts, so the published figure is the broader of the "
            "two and this row's error is a slight over-statement. WINDOW is "
            "stated rather than adjusted, on `biden_corporate_28_fy2022`'s "
            "precedent: CY2027-2036 against the runner's FY2025-2034. NOT a "
            "target, and refused for the same reason `repeal_ptc` refuses "
            "publication 51298: CBO's February 2026 baseline (pub. 61882) "
            "Table 4-1 projects estate and gift receipts of $403B over "
            "FY2027-2036, which is a projection of what the tax raises, not "
            "a score of repealing it -- its closeness to $407.2B is not "
            "corroboration, it is what a repeal score of a small tax with "
            "little behaviour looks like."
        ),
    ),
    # ------------------------------------------------------------------
    # H9 — IRA credit repeal: a repeal score, not a cost projection
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="repeal_ira_credits.v1",
        policy_id="repeal_ira_credits",
        official_10yr_billions=-783.0,
        source_name="CBO (as credited by the record)",
        source_date="2024-03",
        window="stated as FY2025-2034; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="repeal_ira_credits.v2",
        reason=(
            "The cited publication -- 'CBO, budgetary effects of the "
            "energy-related tax provisions of P.L. 117-169 (upward "
            "revision)' -- does not exist, and -$783B appears in no CBO or "
            "JCT document. Every figure in its neighbourhood is a BASELINE "
            "PROJECTION of what the credits cost rather than a scored "
            "repeal: JCT's $663B (2023-2033), CRFB reading CBO's 2024 "
            "baseline at 'closer to $800 billion', Treasury and JCT's "
            "tax-expenditure estimates at about $1.2T (2025-2034). A repeal "
            "score prices the behavioural response; a tax expenditure does "
            "not, and Tax Foundation states the distinction in the document "
            "that replaces this row. `climate.py`'s annual is this figure "
            "restated, so the 0.0% was never evidence."
        ),
    ),
    CalibratedTarget(
        revision_id="repeal_ira_credits.v2",
        policy_id="repeal_ira_credits",
        official_10yr_billions=-851.0,
        source_name="Tax Foundation",
        source_document=(
            "William McBride, 'Testimony: The Inflation Reduction Act's Green "
            "Energy Tax Credits', Tax Foundation, submitted to the U.S. House "
            "Committee on Oversight and Government Reform, 20 May 2025"
        ),
        source_url=(
            "https://taxfoundation.org/testimony/"
            "inflation-reduction-act-ira-green-energy-tax-credits/"
        ),
        source_date="2025-05",
        source_table="Testimony text (the document states the figure in prose)",
        source_row=(
            "'We have estimated that full repeal of the credits would reduce "
            "deficits by $851 billion over the next decade (2025-2034).'"
        ),
        source_page="testimony body",
        window="FY2025-2034",
        entered_commit=H9_PROVENANCE_ENTERED_COMMIT,
        entered_date=H9_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=H9_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "A scored FULL repeal, on this repository's own window, from a "
            "document that itself draws the line this benchmark had been on "
            "the wrong side of: 'The latest tax expenditure estimates from "
            "the Treasury Department and JCT indicate the cost of the credits "
            "has grown to about $1.2 trillion over the next decade "
            "(2025-2034)' -- a cost, against $851B of deficit reduction from "
            "eliminating them. Chosen over JCT's own repeal score on scope, "
            "not on distance (see note)."
        ),
        note=(
            "WHY NOT JCT. JCX-7-23 (26 April 2023) scores Title III of "
            "H.R. 2811, captioned 'REPEAL MARKET DISTORING GREEN TAX "
            "CREDITS' [sic], at a NET TOTAL of $515,078M over FY2023-2033 -- "
            "an actual scorekeeper scoring actual bill text, and the first "
            "instinct is to prefer it. Two things printed on the document "
            "itself stop that. Footnote [1], 'Estimates of outlay effects "
            "presently unavailable', is attached to eleven of its lines, so "
            "the total is revenue-only and omits the refundable and "
            "direct-pay side; and items 11 and 12 -- the clean-vehicle and "
            "previously-owned-clean-vehicle credits -- read 'Presently "
            "Unavailable', so all three vehicle credits are out of the total "
            "(item 13 is folded into 11). An acknowledged-incomplete total is "
            "a lower bound, and adopting a lower bound as a point target "
            "would measure the missing lines. Its window is FY2023-2033 "
            "besides. Recorded here so the next pass does not re-find it and "
            "reach the opposite conclusion silently."
        ),
    ),
    # ------------------------------------------------------------------
    # H9 — the 60% China tariff: a standalone estimate did exist
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="trump_china_60.v1",
        policy_id="trump_china_60",
        official_10yr_billions=-500.0,
        source_name="Tax Foundation (as credited by the record)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="trump_china_60.v2",
        reason=(
            "The credited publisher scores a 60% China tariff only inside a "
            "bundle ('Universal 20% Tariff on All Imports Plus Additional 50% "
            "Tariff on Imports from China', $3,823.9B conventional over "
            "2025-2034), and its standalone China post gives '$200 billion' "
            "as an ANNUAL static figure with no window. So -$500B was only "
            "ever obtainable as a residual from someone else's bundle. What "
            "the H9 pass found is that a standalone conventional ten-year "
            "estimate of exactly this policy does exist and had not been "
            "located: it is CRFB's, not Tax Foundation's, and it is 30% "
            "larger."
        ),
    ),
    CalibratedTarget(
        revision_id="trump_china_60.v2",
        policy_id="trump_china_60",
        official_10yr_billions=-650.0,
        source_name="Committee for a Responsible Federal Budget",
        source_document=(
            "Committee for a Responsible Federal Budget, 'Options to Raise "
            "Tariff Revenue' (17 December 2024)"
        ),
        source_url="https://www.crfb.org/blogs/options-raise-tariff-revenue",
        source_date="2024-12",
        source_table=(
            "'Tariff Scenarios and Their Net Impact on Revenue', section "
            "'Chinese Tariffs', column 'Conventional Impact (2026-2035)'"
        ),
        source_row="60% Import Tariff on Chinese Goods",
        source_page="the post's only revenue table",
        window="FY2026-2035",
        entered_commit=H9_PROVENANCE_ENTERED_COMMIT,
        entered_date=H9_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=H9_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "The only located standalone ten-year conventional estimate of a "
            "60% tariff on Chinese goods with no other tariff alongside it. "
            "The adjacent row prices the same tariff on top of a 10% "
            "universal baseline at $575B, which is the discipline that makes "
            "the $650B row unambiguously the module's shape "
            "(`create_trump_china_60` applies no universal tariff). CRFB is "
            "already the transcribed source behind `reciprocal_tariffs`' "
            "range. It takes the row 44.3% -> 57.2%, which is the shape a "
            "provenance pass has."
        ),
        note=(
            "Four caveats printed on the table, carried rather than adjusted "
            "away. (1) WINDOW: 'these options are based on the FY 2026-2035 "
            "budget window; savings would likely be 15 percent less over the "
            "FY 2025-2034 budget window' -- CRFB's own sizing of the offset "
            "the runner's window would introduce; the figure is taken as "
            "printed. (2) 'Numbers are rough and rounded' -- to the nearest "
            "$5B, which is 0.8% here. (3) DEFINITION: 'Conventional estimates "
            "reflect the average of scenarios where lost trade is and isn't "
            "diverted to other trading partners', and they 'assume... that "
            "all gained tariff revenue would be subject to income and payroll "
            "tax revenue offsets'. (4) CURRENCY: the post now carries an "
            "update banner saying the December 2024 estimates predate the "
            "2025 tariffs and 'may no longer be applicable' -- which is about "
            "what has since been enacted, not about the hypothetical this "
            "benchmark scores. Everyone else bundles: Yale Budget Lab's "
            "twelve scenarios all pair 60% China with a 10% or 20% broad "
            "tariff (Table 2, p. 6), TPC's T24-0050 and T24-0079 are both "
            "'60 Percent ... and 10/20 Percent ... All Other Countries', and "
            "PIIE's Clausing & Lovely figure is annual."
        ),
    ),
    # ------------------------------------------------------------------
    # H9 — mortgage interest: the 2.4x was the standard deduction, and a
    # third, independent estimator has since published
    # ------------------------------------------------------------------
    CalibratedTarget(
        revision_id="eliminate_mortgage.v1",
        policy_id="eliminate_mortgage",
        official_10yr_billions=-300.0,
        source_name="CBO (as credited by the record)",
        source_date="2024",
        window="stated as FY2025-2034; not traceable to any published window",
        entered_commit="unknown (predates the validation manifest)",
        entered_date="2025-12-08",
        first_scoring_run_commit="unknown (predates the validation manifest)",
        superseded_by="eliminate_mortgage.v2",
        reason=(
            "Wave 4 examined this row and left it, on a premise a document "
            "published since has contradicted. That verdict read: 'the only "
            "two ten-year repeal figures -- CRS IF13190's $495B and Yale's "
            "close to $1.2 trillion -- come from the SAME SIMULATOR and "
            "differ by 2.4x, [which] is itself the argument against adopting "
            "either.' Tax Foundation's July 2026 guide supplies a third "
            "figure from an independent general-equilibrium model, and with "
            "it the 2.4x resolves: Yale's $1.2T is scored against **pre-"
            "P.L. 119-21** current law, where TCJA's larger standard "
            "deduction lapses and itemisers roughly double, while CRS's "
            "$495B and Tax Foundation's $367.9B are both post-OBBBA. The gap "
            "was a BASELINE gap, not a simulator disagreement, and -$300B "
            "matches none of the three."
        ),
    ),
    CalibratedTarget(
        revision_id="eliminate_mortgage.v2",
        policy_id="eliminate_mortgage",
        official_10yr_billions=None,
        published_low_10yr_billions=-495.0,
        published_high_10yr_billions=-367.9,
        source_name=(
            "Tax Foundation (anchor); Congressional Research Service, "
            "computing on the Yale Budget Lab Tax-Simulator"
        ),
        source_document=_TF_OPTIONS_3,
        source_url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "eliminate-the-home-mortgage-interest-deduction/"
        ),
        source_date="2026-07",
        source_table="Option 25, table '10-Year Change in the Deficit, 2027-2036'",
        source_row=(
            "Conventional Primary Deficit Change -$367.9B (anchor); "
            + _CRS_IF13190
            + " Table 2, 'Repeal MID $495' over FY2026-2035 ("
            + _CRS_IF13190_URL
            + ")"
        ),
        source_page=(
            "Option 25 (Individual Taxes), the guide's per-option topline "
            "table; CRS IF13190 Table 2"
        ),
        window="CY2027-2036 (anchor); FY2026-2035 (the other bound)",
        entered_commit=H9_PROVENANCE_ENTERED_COMMIT,
        entered_date=H9_PROVENANCE_ENTERED_DATE,
        first_scoring_run_commit=H9_PROVENANCE_FIRST_SCORED_COMMIT,
        reason=(
            "Two independent models now price full repeal of the mortgage "
            "interest deduction on a post-P.L. 119-21 baseline over ten "
            "years and disagree by 35%: Tax Foundation's general-equilibrium "
            "model at -$367.9B conventional (CY2027-2036) and the Yale Budget "
            "Lab Tax-Simulator, transcribed by CRS, at -$495B (FY2026-2035). "
            "No agency has scored repeal at all -- CBO has published no "
            "post-TCJA option, JCT publishes the tax expenditure, and there "
            "is no FY2027 Green Book. So no point is publishable and the row "
            "takes a range on the mechanism Wave 3 built for "
            "`pillar_two_adoption`. The anchor is Tax Foundation's, chosen on "
            "the documents: it is a standalone modelled option with its own "
            "printed deficit table, where CRS's figure is CRS transcribing "
            "somebody else's simulator and labelling it 'not considered "
            "official for revenue scoring purposes'. State plainly what that "
            "rule delivered here: the better-standing bound is also the one "
            "NEARER the model (-$367.9B puts the row at 26.5%, -$495B would "
            "put it at 45.4%), which is the opposite of `trump_corporate_15`, "
            "where the same rule anchored on the FARTHER bound. The rule is "
            "the constant; which bound it lands on is not, and both bounds "
            "ride on this row so a reader can apply either."
        ),
        note=(
            "Yale's own June 2025 'close to $1.2 trillion' is NOT a bound: it "
            "is scored 'relative to current law' as that stood before "
            "P.L. 119-21, i.e. with TCJA's standard deduction lapsing, which "
            "roughly doubles the itemising population a repeal would reach. "
            "Tax Foundation states the baseline it uses: 'The One Big "
            "Beautiful Bill Act made the temporary $750,000 cap permanent "
            "instead of allowing the cap to rise back to $1 million at the "
            "end of 2025.' JCT's tax expenditures (JCX-48-24 $382.2B "
            "FY2024-2028; JCX-45-25 $261.1B FY2025-2029) are not repeal "
            "scores and are not bounds. The two modelling hand-offs Wave 4 "
            "recorded are unchanged and still not this lane's: the record's "
            "`annual_cost = 25.0` is a pre-P.L.119-21 level, and "
            "`annual_cost_no_limit = 100.0` is a pre-TCJA-LAW level whose "
            "name misdescribes it."
        ),
    ),
    # ------------------------------------------------------------------
    # Owner decision (4): the two pharma targets are withdrawn
    # ------------------------------------------------------------------
    # The ledger's first two retirements. Neither figure is a score of
    # anything, and each is contradicted by every published quantity in its
    # neighbourhood. H9 (PR #153) searched both in full, wrote the verdicts,
    # built the `retire` state and applied it to nothing, because the decision
    # is the owner's; this is that decision. Both rows keep their scorecard
    # entries, their model figures and their withdrawn targets, both are
    # counted by `ScorecardSummary.retired_target_entries`, and the
    # reconstruction tier is reported twice - once without them and once with
    # them folded back at the error they carried when they were withdrawn - so
    # the roughly eighteen points the tier "improves" by are never quotable
    # without the arithmetic on the same page.
    CalibratedTarget(
        revision_id="expand_drug_negotiation.v1",
        policy_id="expand_drug_negotiation",
        official_10yr_billions=-500.0,
        source_name="none (this repository's own extrapolation)",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit=RETIREMENT_DECISION_COMMIT,
        entered_date=RETIREMENT_DECISION_DATE,
        first_scoring_run_commit=RETIREMENT_DECISION_COMMIT,
        retired=True,
        retired_reason=(
            "Searched on 2026-09-09 (lane HSB_h9_provenance) and no published "
            "score of EXPANDING the negotiation program exists. CBO's December "
            "2024 Options volume contains no drug-negotiation option at all "
            "(searched in full for 'negotiat', 'drug price', 'prescription "
            "drug'). The nearest published quantities are neither this policy: "
            "CBO's score of the IRA's existing program, publication PL117-169 "
            "(7 September 2022) Table 1 p. 5, sec. 11001 'Providing for Lower "
            "Prices for Certain High-Priced Single Source Drugs', -$98,521M "
            "over FY2022-2031 -- which is the CURRENT program, not an "
            "expansion; and the FY2025 Budget's Table S-6 (report p. 143), "
            "-$200,000M over FY2025-2034 for 'Expand Medicare drug "
            "negotiation, extend inflation rebates and out-of-pocket cost caps "
            "to the commercial market, and other steps to build on the "
            "Inflation Reduction Act (IRA) drug provisions' -- a bundle in "
            "which the negotiation expansion is not separable from two "
            "commercial-market reforms `pharma.py` does not model. Worth "
            "recording precisely: the phrase 'at least 50 drugs' appears "
            "NOWHERE in the FY2025 Budget; it comes from the March 2024 State "
            "of the Union, and no scored document uses it. H.R. 4895 / "
            "H.R. 6166, which would raise the cohort from 20 to 50, have no "
            "CBO estimate. So -$500B is the repository's own extrapolation "
            "from $237B, a figure `W4_pharma_part_d.md` finding 2 established "
            "was never a negotiation score at all but CBO's total for the "
            "whole drug-pricing title. WHAT WOULD BRING IT BACK: a published "
            "ten-year score of an expansion of the negotiation program on a "
            "post-IRA baseline -- a CBO estimate of H.R. 4895 or H.R. 6166, or "
            "a drug-negotiation option in a future Options volume. A separable "
            "negotiation leg of the FY2025 Budget's bundle would also do it. "
            "Until then the benchmark keeps its scorecard row and its model "
            "figure and is reported as retired, never deleted."
        ),
    ),
    CalibratedTarget(
        revision_id="international_reference_pricing.v1",
        policy_id="international_reference_pricing",
        official_10yr_billions=-100.0,
        source_name="none (derived from a RAND price index)",
        source_date="2024",
        window="stated as 10-year; not traceable to any published window",
        entered_commit=RETIREMENT_DECISION_COMMIT,
        entered_date=RETIREMENT_DECISION_DATE,
        first_scoring_run_commit=RETIREMENT_DECISION_COMMIT,
        retired=True,
        retired_reason=(
            "Searched on 2026-09-09 (lane HSB_h9_provenance). A published "
            "score of international reference pricing does exist and it prices "
            "a materially narrower instrument, on a baseline this repository "
            "cannot use. CBO's letter to Chairman Frank Pallone of 10 December "
            "2019 (publication 55936) scores Title I of H.R. 3, the Elijah E. "
            "Cummings Lower Drug Costs Now Act -- prices for SELECTED drugs "
            "negotiated so they 'did not exceed 120 percent of the average in "
            "a reference group of six foreign countries' -- at 'about $456 "
            "billion over the 2020-2029 period' of direct-spending reduction "
            "(Table 1: -455,927 million) plus $45B of revenues. Three things "
            "stop it being this row's target. (1) SCOPE: H.R. 3 caps a "
            "selected cohort; the module prices a cap across Medicare drug "
            "spending, so the published figure is a floor on a narrower "
            "policy. (2) BASELINE: it is scored against a PRE-IRA world in "
            "which Medicare had no negotiation authority, and the IRA has "
            "since enacted a program CBO scores at -$98.5B, so a large part of "
            "H.R. 3's savings is now law -- adopting the figure would "
            "double-count it. (3) WINDOW: FY2020-2029, and this repository "
            "carries no 2019 vintage. The other published quantities are "
            "further away: CMS's Most Favored Nation interim final rule "
            "(85 FR 76180, 27 November 2020) estimates $85.5B of net Part B "
            "savings over a SEVEN-year model period and was rescinded "
            "effective 28 February 2022; and the Council of Economic "
            "Advisers' May 2026 MFN paper's '$529B in domestic savings in the "
            "next 10 years across all markets' is economy-wide across all "
            "payers, not a federal budget effect -- its only federal-scoped "
            "figure is $36.6B of Medicaid savings. So -$100B stands sourced to "
            "nothing but a RAND price index, which is a price statistic and "
            "not a budget score, and it is contradicted in both directions: a "
            "fifth of CBO's figure for a NARROWER policy and an eighth of the "
            "module's own answer. WHAT WOULD BRING IT BACK: a ten-year federal "
            "budget score of a Medicare-wide international reference price on "
            "a post-IRA baseline. This row is the reconstruction tier's single "
            "largest error at 701.0%, which is exactly why withdrawing it "
            "needed the owner's signature; it keeps its scorecard row and its "
            "model figure and is reported as retired, never deleted."
        ),
    ),
)


#: Targets a provenance pass opened the document for and deliberately did
#: **not** move, with the reason. Recorded rather than left in a lane file so
#: that "somebody checked this and decided against" is machine-readable state:
#: without it, a benchmark whose published figure disagrees with the carried
#: one is indistinguishable from one nobody has examined, and the question gets
#: re-opened every pass. A row here must NOT also have a live revision — a
#: target is either moved or left, never both — and ``target_revision_problems``
#: enforces that.
EXAMINED_NOT_REVISED: dict[str, str] = {
    "biden_estate_reform": (
        "JCT scores the 'For the 99.5 Percent Act' at $429.6B over "
        "FY2021-2031 and the repository carries $450B, 4.7% apart, so the "
        "gap alone would argue for moving it. The design does not. JCT's "
        "figure is the total for a ten-section bill: graduated 50/55/65% "
        "brackets above $10M/$50M/$1B, denial of grantor-trust step-up, "
        "valuation-discount limits, a 10-year minimum GRAT term and GST "
        "changes. `estate.py` constructs an exemption change to $3.5M and a "
        "single top rate of 45% — not even the whole rate section, since it "
        "carries no graduated schedule. $429.6B is therefore an upper bound "
        "on a superset, and adopting an upper bound as a point target would "
        "convert a bookkeeping 0.0% into a 4.7% that measures the eight "
        "sections the module does not model rather than the two it does. "
        "Reported both ways for the record (2026-09-02): fitted -$450.0B is "
        "0.00% against $450B and -4.75% against $429.6B; the structural "
        "derived path's -$457.2B is -1.60% and -6.43%. Neither reading "
        "changes the verdict. What would change it is a JCT or Treasury "
        "score of an exemption-and-rate change alone; none exists. Recorded "
        "in `benchmark_sources.py` as `line_item_differs`, which is where a "
        "disagreement lives when it is not moved."
    ),
    "ctc_extension": (
        "Two published figures score a child-credit extension and neither is "
        "a replacement for this benchmark's $600B. (1) CRS R48286 Table 1, "
        "transcribing CBO's May 2024 pub. 60114/60271, prints $735.3B over "
        "FY2025-2034 for 'Increase and Modification of Child and Dependent "
        "Credit' -- but CRS states the figure 'include[s] the budgetary "
        "impact of the Credit for other dependents', which `credits.py` does "
        "not score, so it is a superset. (2) JCT's JCX-35-25 scores "
        "P.L. 119-21's child credit at +$816.846B over the same window -- a "
        "$2,200 indexed credit against this benchmark's $2,000 flat one, and "
        "already carried in this repository as the `pl119_21_child_tax_credit` "
        "benchmark. Adopting it here would score one JCT row as two "
        "benchmarks and count one document twice. Both published figures sit "
        "*above* the module's design rather than bracketing it, so a range "
        "row would assert a containment neither publisher supports. Reported "
        "both ways for the record (2026-09-02): the fitted $600.0B is 0.00% "
        "against $600B, -18.4% against CRS and -26.5% against JCT; the "
        "held-out structural path's $714.2B is +19.0%, -2.9% and -12.6%. The "
        "structural path is twice as close to JCT's row as the fitted "
        "constant while scoring worse against the carried target, which is "
        "the finding -- and it is only visible because the two disagree. What "
        "would move this target is a published score of a $2,000 flat "
        "extension without the other-dependents credit; none exists."
    ),
    "double_enforcement": (
        "Treasury's American Families Plan Tax Compliance Agenda (report "
        "p. 18) says '$320 billion', 6% from the carried -$340B, so the gap "
        "alone would argue for moving it. The dose does not. That $320B is "
        "the yield on an **$80 billion** increase in the IRS budget, scored "
        "in 2021 on a **pre-IRA** baseline. This preset's own description is "
        "'Double IRS enforcement beyond IRA levels (~$16B/year)', i.e. about "
        "$160B of additional funding stacked *on top of* the IRA's $80B -- "
        "twice the dose, on a baseline that already contains the dose "
        "Treasury scored. Adopting $320B would convert a bookkeeping number "
        "into a 6% agreement that measures nothing, because the two figures "
        "are not estimates of the same reform. Treasury's $700B headline is "
        "the full package including bank information reporting ($460B of "
        "it), which the module does not implement at all, so it is not a "
        "candidate either. Recorded in `benchmark_sources.py` as "
        "`line_item_differs`, which is where a disagreement lives when it is "
        "not moved."
    ),
    "steel_tariff_25": (
        "Searched again on 2026-09-02 and the answer is still that nobody "
        "scored this. A 25% Section 232 rate on steel and aluminium was in "
        "force only from 12 March 2025 to 3 June 2025, when it doubled to "
        "50%, and no scorekeeper published a ten-year estimate for the "
        "ten-week regime. The nearest published figures score different "
        "policies: Tax Foundation's tariff tracker Table 5 gives 'Section 232 "
        "Steel, Aluminum, and Copper' at $341.4B conventional / $235.9B "
        "dynamic over 2026-2035, but at **50%**, with copper folded in and "
        "derivatives included; CRFB's two steel/aluminium posts score "
        "*derivative-rule* changes (+$70B through FY2036 in April 2026, "
        "revised to -$90B once the proclamation landed), not a base tariff; "
        "and CRS IN12519, the one congressional product on the tariff, "
        "carries no revenue estimate at all -- its full text was extracted to "
        "confirm that. On the derivatives question the sourcing pass asked: "
        "every published figure includes them and none separates with from "
        "without, so the distinction cannot be sourced either. The carried "
        "-$60B is therefore left in place and left unsourced rather than "
        "replaced by a 50%-plus-copper figure, and it is not retired, because "
        "retiring a case to avoid reporting an unsourced target is the "
        "failure mode this ledger exists to prevent. `searched` on the "
        "`benchmark_sources` row carries the full negative result. "
        "RE-SEARCHED 2026-09-09 by lane H9: still nothing. Tax Foundation's "
        "*Options 3.0* (July 2026) adds 86 modelled options and none of them "
        "is a Section 232 steel rate; the ten-week 25% regime remains the one "
        "tariff in this repository that no scorekeeper ever priced."
    ),
    "repeal_ptc": (
        "Searched on 2026-09-05 and the carried -$1,100B now has a most "
        "likely origin, which is exactly why it is not adopted. CBO and JCT's "
        "June 2024 baseline projections (Health Insurance and Its Federal "
        "Subsidies, publication 51298, Table 2, read from CBO's own PDF via a "
        "Wayback mirror because cbo.gov returns HTTP 403 here) print, under "
        "'Premium tax credits and related spending', outlays of $966B and "
        "revenue reductions of $176B over FY2025-2034 -- **$1,142B together, "
        "3.8% from the figure this repository carries**. So the target is a "
        "BASELINE PROJECTION of what the credit costs, sitting in a column "
        "captioned as a repeal score. That is the same class of quantity the "
        "`benchmark_sources` row already refuses for this benchmark "
        "(JCX-48-24's exchange-subsidy tax expenditure) and the same one "
        "`repeal_individual_amt` refuses TPC's T25-0049 for: a projection of a "
        "provision's cost is not a score of repealing it, because it carries "
        "no coverage response and no interaction with Medicaid, employer "
        "coverage or taxable wages, all of which every published repeal "
        "estimate prices. Adopting it would also make the row WORSE, not "
        "better -- the model's -$896.9B is 18.5% from -$1,100B and 21.5% from "
        "-$1,142B -- so this is not a case of a lane declining an improvement. "
        "No scored repeal exists to move to: CBO/JCT publication 61734 "
        "(18 September 2025), the most recent menu of marketplace policies, "
        "scores permanently extending the expanded credit (~$350B) and "
        "repealing five sections of the 2025 reconciliation act ($271.9B "
        "together) and contains no option eliminating the credit at all; the "
        "2018, 2020, 2022 and 2025 CBO options volumes carry no such option; "
        "and the 2017 AHCA/BCRA estimates score ACA subsidy repeal bundled "
        "with Medicaid, on a pre-enhancement statute and a 2017-2026 window. "
        "One thing the owner should weigh, since it is a modelling decision a "
        "provenance lane may not take: `create_repeal_ptc` sets "
        "`coverage_elasticity=0.0` ('Not modeling coverage offset'), so what "
        "the module computes IS a baseline cost rather than a repeal score, "
        "and the mismatch is in the shape as much as in the target. Left in "
        "place, left `secondhand`, and explicitly not retired -- retiring a "
        "case to avoid reporting an unsourced target is the failure mode this "
        "ledger exists to prevent, and this one is a locked "
        "`holdout.py` id besides. RE-SEARCHED 2026-09-09 by lane H9 and "
        "nothing has been published since: CBO/JCT publication 61734 was read "
        "in full and scores three policies, all of them EXTENSIONS or repeals "
        "of the 2025 act's restrictions (permanently expanding the ARPA "
        "structure, $350B; nullifying a June 2025 HHS rule, $40B; repealing "
        "title VII subtitle B of the reconciliation act, $272B) and none of "
        "them elimination of the credit; CBO's cost estimates through "
        "September 2026 contain none (the nearest, H.R. 6703 of 16 December "
        "2025, is association health plans and PBM standards at -$35.6B); no "
        "2025 or 2026 JCX scores repeal of section 36B; and the phrase "
        "'premium tax credit' does not appear anywhere in Tax Foundation's "
        "86-option *Options 3.0* guide."
    ),
    # ----- H9 (2026-09-09) -------------------------------------------------
    "ss_eliminate_cap": (
        "Searched on 2026-09-09 and the only published ten-year dollar score "
        "of this design cannot be adopted, for a reason the ledger states "
        "mechanically. No CBO Options volume scores cap ELIMINATION at all: "
        "all four (2018 Option 20, 2020 Option 17, 2022 Option 9, 2024 Option "
        "62) offer the same two alternatives, a 90% taxable share and the "
        "$250,000 donut. OCACT scores provision E2.1 ('Eliminate the taxable "
        "maximum... Do not provide benefit credit', run 415) in percent of "
        "payroll only. What does exist is Tax Foundation, Alex Durante, "
        "'Uncapping the Payroll Tax Would Be the Largest Tax Increase in "
        "Decades' (24 June 2026, updated 25 June): 'It would raise $3.2 "
        "trillion from 2027 through 2036 on a conventional basis and $1.5 "
        "trillion after accounting for the negative economic effects', on a "
        "proposal that applies the tax to all earnings above the cap 'with no "
        "corresponding changes to benefits' -- the same design. THE LEDGER "
        "ITSELF REFUSES IT. $3.2 trillion is -$3,200.0B to the digit the "
        "document states, which is exactly the figure this repository "
        "carries, and `target_revision_problems` fails any supersession that "
        "'restates the old target'. So it cannot be recorded as a revision; "
        "and recording it as a confirmation would assert that a constant "
        "chosen to produce -$3.2T ('320.0  # window-average of Trustees $3.2T "
        "over 10yr' in `payroll.py`) had been validated by a document "
        "published a year and a half later, on a window this repository does "
        "not use, at one significant figure. That is the failure "
        "`repeal_individual_amt` refuses TPC T25-0049 for. Two further "
        "published figures, neither this design: the Peter G. Peterson "
        "Foundation's '$3.4 trillion over 10 years (2026 to 2035)' is "
        "explicitly the variant 'while providing benefit credit for those "
        "earnings'; and SSA OACT's letter on the Medicare and Social Security "
        "Fair Share Act (11 July 2023, Table 1b.n, 'Total 2023-2032' = "
        "$3,035.1B nominal) scores a $400,000 DONUT with no benefit credit "
        "and no income-tax offset. That last one corrects a claim this "
        "repository has been making: OCACT's *provisions* tables publish no "
        "dollars, but OCACT's bill-specific solvency letters do, so 'OCACT "
        "publishes no ten-year dollar amount for any payroll provision' is "
        "true of the category summary and false of the office. Left in place, "
        "left `secondhand`, and named in `HSB_h9_provenance.md` as a "
        "retirement candidate for the owner alongside the pharma pair."
    ),
    "cap_charitable": (
        "Searched on 2026-09-09. No official score of a charitable-ONLY rate "
        "limitation exists, in any volume or any year. Every official rate cap "
        "applies to all itemized deductions (CBO's 2017-2026 volume Option 8, "
        "'Limit the tax benefits of itemized deductions to 28 percent of their "
        "total value', $171.5B FY2017-2026, JCT; the Green Book's 'Reduce the "
        "value of certain tax expenditures', $645,538M FY2017-2026, which also "
        "reaches five exclusions), and every official charitable-only option is "
        "a floor or a cash-only rule (CBO's 2013 volume $212B; 2019-2028 "
        "$175.6B floor / $145.7B cash-only; 2025-2034 Option 50 $347.7B / "
        "$324.3B). CBO's own 'Options for Changing the Tax Treatment of "
        "Charitable Giving' (May 2011) has eleven options, none a rate cap, "
        "and its results are stated 'for tax year 2006' rather than as "
        "ten-year scores. One non-official ten-year figure for the exact "
        "design was located and is NOT adopted: CRFB, 'The Tax Break-Down: "
        "Charitable Deduction' (16 December 2013), table 'Revenue Impact from "
        "Reforming the Charitable Deduction (Billions, 2014-2023)', row "
        "'Impose a 28% limit on the value of the deduction | $75', with the "
        "caveat printed beneath it -- 'All scores are rough estimates and may "
        "not match official CBO scores. Scores were chiefly estimated from a "
        "2011 CBO analysis based on 2006 data.' A rough estimate derived from "
        "tax-year-2006 microdata, on a window that closed in 2023, is not a "
        "target; adopting it would move the row from 0.3% to 167% on the "
        "strength of a figure its own publisher declines to stand behind. "
        "Recorded so the next pass does not re-find it and decide otherwise. "
        "Adjacent and also not adopted: Tax Foundation *Options 3.0* (July "
        "2026) Option 24 tightens the OBBBA limitation 'to 28 cents on the "
        "dollar' at -$169.0B over 2027-2036 -- all itemized deductions again."
    ),
    "cap_employer_health": (
        "Searched on 2026-09-09 and the carried -$450B now has a most likely "
        "origin, which is the reason not to adopt it. CBO's *Budget Options, "
        "Volume 1: Health Care* (December 2008), Option 9, p. 24, is the only "
        "published option that states the cap in DOLLARS: it would tax "
        "employer and employee contributions 'that together exceeded $1,440 a "
        "month for family coverage or $565 a month for individual coverage', "
        "and JCT scores it at revenues of $452.1B over FY2009-2018 -- **0.5% "
        "from the figure this repository carries**. But CBO derives those "
        "dollars from the 75th percentile of 2010 premiums, and $1,440 a "
        "month is $17,280 a year against the $50,000 cap this benchmark's own "
        "description states: the same class of quantity at a third of the "
        "level, on a window that closed in 2018. So the target is most likely "
        "a figure for a far tighter cap, a decade earlier, sitting in this "
        "column -- the same shape as `extend_tcja_amt`'s five-year cost in a "
        "ten-year column, and there is nothing to move it TO. No agency has "
        "ever scored a cap set at a chosen dollar level: CBO's 2016 volume "
        "gives -$429B (50th percentile) and -$174B (75th), FY2017-2026; its "
        "2019-2028 volume $670B / $270B revenues; its 2022 volume -$893.2B / "
        "-$499.8B / -$651.4B; its 2024 volume Option 56 $965.0B / $521.0B / "
        "$697.0B. The Senate Finance Committee's May 2009 options paper "
        "discusses capping and publishes no estimate; JCT's companion "
        "background paper says the exclusion 'could be reduced by capping the "
        "dollar amount' and prints no table. Non-agency and also not a dollar "
        "cap: Urban (May 2013) 75th percentile, $264.0B over 2014-2023; Tax "
        "Foundation *Options 3.0* Option 30, 80th percentile ($14,816 single "
        "/ $38,185 family), -$318.5B over 2027-2036. The $50,000 design is "
        "the module's, and no scorekeeper has priced it."
    ),
    "eliminate_step_up": (
        "Searched on 2026-09-09. No published estimate scores realization at "
        "death WITH an exclusion as a standalone provision, and the carried "
        "-$500B is above every standalone figure that does exist by about "
        "2.4x -- in the direction that cannot be explained by the design, "
        "because an exclusion makes a repeal NARROWER. Standalone, all "
        "without an exclusion: PWBM, 'The Biden Tax Plan' (23 January 2020) "
        "Table 1, row 'Eliminate stepped-up basis', $204B over FY2021-2030; "
        "CBO's 2021-2030 volume Option 6, 'Change the Tax Treatment of "
        "Capital Gains From Sales of Inherited Assets', $110.3B (carryover "
        "basis, JCT); Tax Foundation *Options 3.0* Option 15, -$206.4B over "
        "2027-2036 (carryover again). Bundled, with an exclusion: JCT's "
        "JCX-15-16 item XI.B, 'Reform the Taxation of Capital Income', "
        "$248,739M FY2016-2026, which is Obama's 28% rate AND gains at death "
        "with a $100,000 exclusion in one line; PWBM's American Families Plan "
        "row, $376B FY2022-2031, which is three provisions in one line; and "
        "Treasury's combined 'Reform the taxation of capital income' row in "
        "every Green Book. The STEP Act was searched specifically and JCT has "
        "not scored it -- Senator Van Hollen's own one-pager describes the $1 "
        "million exclusion this benchmark models and cites only a JCT TAX "
        "EXPENDITURE, '$41.9 billion in 2021 alone'. CBO's Option 51 "
        "alternative 2 ($536.1B, FY2025-2034) remains out for the reason "
        "Phase E gave: no exemption, a materially broader policy, and already "
        "carried here as the Tier 1 case `cbo_opt51_gains_at_death`. So the "
        "target stays, the incoherence is on the record -- a fitted constant "
        "reproducing a figure 2.4x every published score of a BROADER version "
        "of the same reform -- and `HSB_h9_provenance.md` names it as a "
        "retirement candidate for the owner."
    ),
    "repeal_individual_amt": (
        "Searched a third time on 2026-09-09, and the verdict the AMT/insulin "
        "lane and Wave 4 reached is unchanged: $450B is traceable to nothing "
        "and there is nothing to move it to. One document is new and it does "
        "not qualify. Tax Foundation *Options 3.0* (July 2026) Option 38, "
        "'Eliminate the Individual Alternative Minimum Tax', prints +$271.1B "
        "conventional over 2027-2036 -- but it is scored against POST-"
        "P.L. 119-21 law, where TCJA's enlarged exemption is permanent, and "
        "this benchmark's stated design is repeal against a baseline in which "
        "that exemption has LAPSED. The two baselines are opposites and "
        "repeal costs far more under the second, so adopting it would score "
        "one policy against another's figure. JCT's standalone repeal line "
        "was re-read and is where Phase E left it: JCX-46-17 p. 3 row G and "
        "JCX-54-17 p. 3 row H, 'Repeal of Alternative Minimum Tax on "
        "Individuals', -$695.5B over FY2018-2027 -- a pre-TCJA baseline and a "
        "different decade. TPC's T25-0049 stays refused for the two reasons "
        "on the `benchmark_sources` row: it is a baseline projection of what "
        "the AMT raises rather than a scored repeal, and it is `amt.py`'s own "
        "input. Nothing in JCT's or CBO's 2025-2026 output scores repeal. One "
        "new observation for the owner: P.L. 119-21 made the enlarged "
        "exemption permanent, so the lapsed-exemption baseline this benchmark "
        "is defined on is now a counterfactual rather than current law -- "
        "which is a modelling question for `amt.py`, not a provenance one. "
        "The row is also a locked id in `holdout.py`'s "
        "revenue-scorecard-post-lock-2026-05-02 protocol, which has no "
        "re-registration path."
    ),
    "carbon_tax_50": (
        "Searched on 2026-09-09. NO published ten-year estimate of a carbon "
        "tax starting at $50 per metric ton with a 5% annual escalator "
        "exists, and the carried -$1,700B is `climate.py`'s own calibration "
        "target by the module's own admission ('Calibrated so $50/ton yields "
        "~$170B/yr avg -> ~$1.7T/10yr'). Two published totals sit near the "
        "design and both use a 2% REAL escalator, not 5%. Treasury's Office "
        "of Tax Analysis Working Paper 115 (January 2017), 'Methodology for "
        "Analyzing a Carbon Tax', p. 10: a tax starting at '$49 per metric "
        "ton CO2-e on January 1, 2019 and rising at roughly a 2 percent real "
        "rate' raises '$2,221 billion in net revenue over the 10-year window "
        "from 2019 through 2028' ($1,846B if confined to energy-related CO2; "
        "gross $2,962B before the 25% excise offset). And Rhodium Group for "
        "Columbia SIPA's Center on Global Energy Policy (July 2018), Table 2, "
        "report p. 50: a '$50/ton' scenario 'rises at an approximately 2 "
        "percent real rate annually' raising $1,682-1,781 billion of 2016 "
        "dollars over 2020-2029. THE CARRIED FIGURE FALLS INSIDE THAT RANGE, "
        "AND THAT IS NOT EVIDENCE: the window is six years earlier, the units "
        "are 2016 dollars, and the escalator is not the module's, so the "
        "coincidence is two offsetting differences rather than agreement -- "
        "which is exactly why it is not adopted as a range revision. CRS "
        "R45625 Table 1 (report p. 23) reports annual 2020 figures only and "
        "its one $50/5% line is a single-year 2040 range ('approximately $250 "
        "billion to $475 billion'). No JCT score of any carbon-fee bill "
        "exists -- congress.gov records zero CBO cost estimates for S.1128 "
        "(116th) -- and the '$2.1 / $2.3 trillion' figures in Whitehouse "
        "press releases carry no window and no JCX number. CBO's own Option "
        "73 alternative 1 is the one figure on this repository's window with "
        "the module's exact escalator, $919.3B FY2025-2034 for $25/ton rising "
        "5% -- and doubling it would be constructing a target. Left in place "
        "and named in `HSB_h9_provenance.md` as a retirement candidate: a "
        "target that restates the model's own calibration is not a benchmark."
    ),
    "tcja_no_salt_cap": (
        "Searched on 2026-09-09. No agency has scored 'extend the TCJA and "
        "let the SALT cap lapse' as a single row, and the two rows that would "
        "have to be added carry CBO's own warning against adding them. CBO's "
        "supplemental workbook for publication 60114 prints the block total "
        "$3,255,900M and, separately, the itemized-deduction row at "
        "-$1,244,276M over FY2025-2034, under the note 'the estimate of "
        "extending any single provision may differ from that reported here "
        "because of interactions with other estimates... they do not include "
        "all potential interaction effects of permanently extending the "
        "provisions together'. Summing two rows to make a target is what "
        "PR #122 declined for `trump_corporate_15`'s bonus-depreciation leg. "
        "One published single row does exist and is NOT adopted: CRFB, 'SALT "
        "Cap Expiration Could Be Costly Mistake' (28 August 2024), table "
        "'Fiscal Impact of Various TCJA Extension Scenarios', row 'Extend "
        "except SALT cap' = $5.1 trillion over FY2026-2035, from CRFB's own "
        "Build Your Own Tax Extensions tool. It pairs with that table's OTHER "
        "row -- 'Extend all individual and estate provisions | $3.9 trillion' "
        "-- and this repository scores the base extension against CBO's "
        "$4.6T. Adopting $5.1T while `tcja_extension` keeps $4,600B would mix "
        "two publishers' bases in one decomposition, and most of the "
        "resulting error would be the CRFB-versus-CBO base gap rather than "
        "anything about the SALT cap. Worth recording that the two "
        "publications AGREE on the increment that is actually at issue: CRFB "
        "puts it at +$1.2 trillion and CRS R48286's itemized-deduction row at "
        "$1,244.3B, against the ~$1.1T this repository's own decomposition "
        "assumes. Left as `model_estimate`, and see `HSB_h9_provenance.md` "
        "for the $6,500B-versus-$5,700B inconsistency this search exposed "
        "between `CBO_SCORE_MAP` and the benchmark's own target."
    ),
}


def _by_policy() -> dict[str, list[CalibratedTarget]]:
    grouped: dict[str, list[CalibratedTarget]] = {}
    for target in CALIBRATED_TARGETS:
        grouped.setdefault(target.policy_id, []).append(target)
    return grouped


def revisions_for(policy_id: str) -> tuple[CalibratedTarget, ...]:
    """Every ledger row for one benchmark, in entry order."""
    return tuple(_by_policy().get(policy_id, ()))


def live_target_for(policy_id: str) -> CalibratedTarget | None:
    """The row currently in force for one benchmark, or ``None``."""
    for target in revisions_for(policy_id):
        if target.is_live:
            return target
    return None


def superseded_targets_for(policy_id: str) -> tuple[CalibratedTarget, ...]:
    """Every *replaced* row for one benchmark, oldest first.

    Deliberately keyed on ``superseded_by`` rather than on ``not is_live``: a
    **retired** row is also not live, and the two states mean different things.
    A supersession says "the target moved here"; a retirement says "the target
    should not exist and nothing replaces it". Folding the second into the
    first would let a withdrawal read as a revision on every surface that
    reports ``superseded_10yr_billions``.
    """
    return tuple(
        t for t in revisions_for(policy_id) if t.superseded_by is not None
    )


def retired_target_for(policy_id: str) -> CalibratedTarget | None:
    """The withdrawn row for one benchmark, if its target was retired."""
    for target in revisions_for(policy_id):
        if target.is_retired:
            return target
    return None


def retired_targets() -> tuple[CalibratedTarget, ...]:
    """Every withdrawn target in the ledger, in entry order."""
    return tuple(t for t in CALIBRATED_TARGETS if t.is_retired)


def target_was_revised(policy_id: str) -> bool:
    """Whether this benchmark's target has been moved by this ledger.

    ``scorecard.py`` reads this to turn ``calibrated_to_target`` off: a module
    constant fitted to the superseded figure is not fitted to the live one, and
    the flag asserts precisely that relationship.
    """
    return bool(superseded_targets_for(policy_id))


def target_was_retired(policy_id: str) -> bool:
    """Whether this benchmark's target has been **withdrawn** by this ledger.

    Read by ``scorecard.py`` for the same reason ``target_was_revised`` is: a
    constant fitted to a figure the ledger has withdrawn is not fitted to
    anything live, so the row leaves the fitted tier. It leaves the
    *reconstruction* tier's mean too — there is no target to be measured
    against — which is why the scorecard counts retired rows separately and the
    dashboard prints the reading with them folded back in. Dropping a row from
    a mean without printing the mean it was in is how a withdrawal becomes an
    improvement.
    """
    return bool(retired_target_for(policy_id))


#: Benchmarks whose target this ledger has moved. Frozen at import so a caller
#: can test membership without rebuilding the index.
REVISED_POLICY_IDS: frozenset[str] = frozenset(
    t.policy_id for t in CALIBRATED_TARGETS if t.superseded_by is not None
)

#: Benchmarks whose target this ledger has **withdrawn**. Disjoint from
#: :data:`REVISED_POLICY_IDS` by ``target_revision_problems``'s own check.
RETIRED_POLICY_IDS: frozenset[str] = frozenset(
    t.policy_id for t in CALIBRATED_TARGETS if t.is_retired
)


def target_revision_problems(entries: list[object] | None = None) -> list[str]:
    """Return every internal inconsistency in the ledger, as readable lines.

    Checks, in order:

    * ids are unique and shaped ``<policy_id>.v<n>``;
    * every ``superseded_by`` names a row that exists, for the same benchmark,
      and is not itself the row doing the superseding;
    * exactly one live row per benchmark;
    * a row states either a point target or a range (both bounds, low below
      high), never neither and never a half-range;
    * a supersession actually moves the target — a "revision" that restates the
      old figure is bookkeeping noise and hides the rows that matter. Replacing
      a point with a range counts as a move: it changes what is being asserted
      about the target even when a bound coincides with the old point;
    * a **retired** row states a ``retired_reason``, is not also superseded,
      and is the last word for its benchmark — nothing may be live after a
      withdrawal, or the ledger would say both "this target does not exist"
      and "this is the target";
    * both halves of a supersession state a reason;
    * a live row that replaced something cites a document (url, date, table,
      row, page): the whole point of moving a target is that the new one can be
      checked;
    * a benchmark is not both revised and recorded as examined-and-left;
    * and, when ``entries`` is supplied, that every live row agrees with the
      figure the scorecard is actually scoring against — equality for a point
      row, containment for a range row.
    """
    problems: list[str] = []
    by_id: dict[str, CalibratedTarget] = {}
    for target in CALIBRATED_TARGETS:
        if target.revision_id in by_id:
            problems.append(f"duplicate revision_id {target.revision_id}")
        by_id[target.revision_id] = target
        if not _REVISION_ID.fullmatch(
            target.revision_id
        ) or not target.revision_id.startswith(f"{target.policy_id}."):
            problems.append(
                f"{target.revision_id}: id must be its policy_id "
                f"{target.policy_id!r} followed by '.v<n>'"
            )

    for target in CALIBRATED_TARGETS:
        has_point = target.official_10yr_billions is not None
        half_range = (
            target.published_low_10yr_billions is None
        ) != (target.published_high_10yr_billions is None)
        if half_range:
            problems.append(
                f"{target.revision_id}: a range target needs both bounds; "
                "one alone says nothing"
            )
        elif target.is_range:
            if has_point:
                problems.append(
                    f"{target.revision_id}: states both a point target and a "
                    "range; a row asserts one or the other"
                )
            if (
                target.published_low_10yr_billions
                >= target.published_high_10yr_billions
            ):
                problems.append(
                    f"{target.revision_id}: range low bound "
                    f"{target.published_low_10yr_billions} is not below high "
                    f"bound {target.published_high_10yr_billions}"
                )
        elif not has_point:
            problems.append(
                f"{target.revision_id}: states neither a point target nor a range"
            )

    for target in CALIBRATED_TARGETS:
        if not target.is_retired:
            continue
        if not target.retired_reason.strip():
            problems.append(
                f"{target.revision_id}: retired with no retired_reason"
            )
        if target.superseded_by is not None:
            problems.append(
                f"{target.revision_id}: is both retired and superseded_by "
                f"{target.superseded_by}; a withdrawal has no replacement"
            )

    for policy_id in sorted(EXAMINED_NOT_REVISED):
        if not EXAMINED_NOT_REVISED[policy_id].strip():
            problems.append(
                f"{policy_id}: recorded as examined-and-left with no reason"
            )
        if policy_id in _by_policy():
            problems.append(
                f"{policy_id}: is recorded as examined-and-left AND carries a "
                "ledger row; a target is either moved or left, never both"
            )

    for target in CALIBRATED_TARGETS:
        if target.superseded_by is None:
            continue
        successor = by_id.get(target.superseded_by)
        if successor is None:
            problems.append(
                f"{target.revision_id}: superseded_by names a row that does "
                f"not exist ({target.superseded_by})"
            )
            continue
        if successor.policy_id != target.policy_id:
            problems.append(
                f"{target.revision_id}: superseded by a row for a different "
                f"benchmark ({successor.policy_id})"
            )
        if successor.revision_id == target.revision_id:
            problems.append(f"{target.revision_id}: supersedes itself")
        # Replacing a point with a range is a move even if a bound happens to
        # equal the old point: what the row asserts about the target changed.
        if (
            successor.is_range == target.is_range
            and successor.official_10yr_billions == target.official_10yr_billions
            and successor.published_low_10yr_billions
            == target.published_low_10yr_billions
            and successor.published_high_10yr_billions
            == target.published_high_10yr_billions
        ):
            problems.append(
                f"{target.revision_id}: superseded without changing the "
                "figure; a revision that restates the old target is noise"
            )
        for row, half in ((target, "superseded"), (successor, "replacement")):
            if not row.reason.strip():
                problems.append(
                    f"{row.revision_id}: the {half} half of a supersession "
                    "must state a reason"
                )

    for policy_id, rows in sorted(_by_policy().items()):
        live = [row for row in rows if row.is_live]
        retired = [row for row in rows if row.is_retired]
        if retired:
            # A withdrawal is the last word for its benchmark. Zero live rows
            # is the correct state here; a live row alongside one would have
            # the ledger asserting both "this target does not exist" and "this
            # is the target".
            if live:
                problems.append(
                    f"{policy_id}: has a retired target "
                    f"({retired[-1].revision_id}) and a live one "
                    f"({live[0].revision_id}); a withdrawal is final"
                )
            continue
        if len(live) != 1:
            problems.append(
                f"{policy_id}: expected exactly one live target, found "
                f"{len(live)} ({[row.revision_id for row in live]})"
            )
            continue
        current = live[0]
        if not superseded_targets_for(policy_id):
            continue
        missing = [
            name
            for name in (
                "source_document",
                "source_url",
                "source_date",
                "source_table",
                "source_row",
                "source_page",
            )
            if not getattr(current, name)
        ]
        if missing:
            problems.append(
                f"{current.revision_id}: a replacement target must cite its "
                f"document; missing {', '.join(missing)}"
            )

    if entries is None:
        return problems

    by_policy_entry = {
        getattr(entry, "policy_id", ""): entry for entry in entries
    }
    for policy_id, rows in sorted(_by_policy().items()):
        entry = by_policy_entry.get(policy_id)
        if entry is None:
            problems.append(
                f"{policy_id}: has a target revision but no scorecard entry"
            )
            continue
        live = next((row for row in rows if row.is_live), None)
        if live is None:
            # Retired: there is no live figure for the entry to agree with, so
            # the equality check is replaced by the requirement that the row
            # says so. A withdrawn target that the scorecard still reports as
            # an ordinary benchmark is exactly the silent deletion the state
            # exists to prevent.
            if any(row.is_retired for row in rows) and not getattr(
                entry, "target_retired", False
            ):
                problems.append(
                    f"{policy_id}: the ledger retired its target but the "
                    "scorecard entry is not marked retired"
                )
            continue
        carried = float(getattr(entry, "official_10yr_billions", float("nan")))
        if live.is_range:
            # A range row makes no claim about which point the registries
            # carry, only that the point is not outside what was published.
            if not live.contains(carried):
                problems.append(
                    f"{policy_id}: the scorecard scores against {carried}, "
                    f"outside the published range the live ledger row "
                    f"{live.revision_id} records "
                    f"[{live.published_low_10yr_billions}, "
                    f"{live.published_high_10yr_billions}]"
                )
        elif abs(carried - live.official_10yr_billions) > 1e-6:
            problems.append(
                f"{policy_id}: the scorecard scores against {carried}, but the "
                f"live ledger row {live.revision_id} says "
                f"{live.official_10yr_billions}"
            )
    return problems


def assert_target_revisions(entries: list[object] | None = None) -> None:
    """Raise ``AssertionError`` on any ledger inconsistency."""
    problems = target_revision_problems(entries)
    if problems:
        raise AssertionError(
            "calibrated target ledger is inconsistent:\n  - "
            + "\n  - ".join(problems)
        )


__all__ = [
    "AMT_INSULIN_PROVENANCE_ENTERED_COMMIT",
    "AMT_INSULIN_PROVENANCE_ENTERED_DATE",
    "AMT_INSULIN_PROVENANCE_FIRST_SCORED_COMMIT",
    "CALIBRATED_TARGETS",
    "CORPORATE_PTC_PROVENANCE_ENTERED_COMMIT",
    "CORPORATE_PTC_PROVENANCE_ENTERED_DATE",
    "CORPORATE_PTC_PROVENANCE_FIRST_SCORED_COMMIT",
    "EXAMINED_NOT_REVISED",
    "H9_PROVENANCE_ENTERED_COMMIT",
    "H9_PROVENANCE_ENTERED_DATE",
    "H9_PROVENANCE_FIRST_SCORED_COMMIT",
    "RETIRED_POLICY_IDS",
    "REVISED_POLICY_IDS",
    "WAVE3_PROVENANCE_ENTERED_COMMIT",
    "WAVE3_PROVENANCE_ENTERED_DATE",
    "WAVE3_PROVENANCE_FIRST_SCORED_COMMIT",
    "WAVE4_PROVENANCE_ENTERED_COMMIT",
    "WAVE4_PROVENANCE_ENTERED_DATE",
    "WAVE4_PROVENANCE_FIRST_SCORED_COMMIT",
    "CalibratedTarget",
    "assert_target_revisions",
    "live_target_for",
    "retired_target_for",
    "retired_targets",
    "revisions_for",
    "superseded_targets_for",
    "target_revision_problems",
    "target_was_retired",
    "target_was_revised",
]
