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
    reason: str = ""
    note: str = ""

    @property
    def is_live(self) -> bool:
        """A row still in force: not replaced by a later row."""
        return self.superseded_by is None

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
        "`benchmark_sources` row carries the full negative result."
    ),
    "eliminate_mortgage": (
        "Searched again on 2026-09-02, and no official repeal score exists. "
        "CBO has published no budget option repealing the mortgage interest "
        "deduction since TCJA; JCT publishes the *tax expenditure* rather "
        "than a repeal estimate (JCX-48-24 Table 1, $382.2B over FY2024-2028; "
        "JCX-45-25 Table 1, $261.1B over FY2025-2029), and a tax expenditure "
        "is not a repeal score because it omits the behavioural and "
        "itemisation response. The only located ten-year repeal figure "
        "remains CRS In Focus IF13190 (23 March 2026) Table 2, 'Repeal MID "
        "$495' over FY2026-2035, which CRS itself labels an estimate from the "
        "Yale Budget Lab Tax-Simulator and 'not considered official for "
        "revenue scoring purposes'; Yale's own June 2025 options paper puts "
        "full repeal against current law at 'close to $1.2 trillion', a "
        "figure that differs from CRS's by 2.4x on the same simulator, which "
        "is itself the argument against adopting either. The carried -$300B "
        "matches none of them and stays where it is. Two things a reader "
        "should know, both handed off rather than acted on because they are "
        "modelling changes: the record's `annual_cost = 25.0` is a "
        "pre-P.L.119-21 level -- JCT's JCX-45-25 puts the capped expenditure "
        "at $45.5B in FY2025 rising to $54.9B in FY2029, because raising the "
        "SALT cap to $40,000 took itemising claimants from 11.8M to 17.8M "
        "returns -- and Treasury's FY2027 edition gives $23.9B falling to "
        "$14.1B on the *same* statute, a 2-4x disagreement driven by "
        "Treasury's comprehensive-income baseline against JCT's normal-tax "
        "one. Whichever is adopted is an owner decision with a visible "
        "consequence for `eliminate_mortgage`, and a provenance lane may not "
        "make it."
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
    """Every retired row for one benchmark, oldest first."""
    return tuple(t for t in revisions_for(policy_id) if not t.is_live)


def target_was_revised(policy_id: str) -> bool:
    """Whether this benchmark's target has been moved by this ledger.

    ``scorecard.py`` reads this to turn ``calibrated_to_target`` off: a module
    constant fitted to the superseded figure is not fitted to the live one, and
    the flag asserts precisely that relationship.
    """
    return bool(superseded_targets_for(policy_id))


#: Benchmarks whose target this ledger has moved. Frozen at import so a caller
#: can test membership without rebuilding the index.
REVISED_POLICY_IDS: frozenset[str] = frozenset(
    t.policy_id for t in CALIBRATED_TARGETS if not t.is_live
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
    "EXAMINED_NOT_REVISED",
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
    "revisions_for",
    "superseded_targets_for",
    "target_revision_problems",
    "target_was_revised",
]
