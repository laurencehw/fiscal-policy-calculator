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
#: the estate row's examined-and-left verdict. Provisional until the stamping
#: commit at the end of the lane: a file cannot contain its own commit hash.
WAVE3_PROVENANCE_ENTERED_COMMIT = "7f25bed2377ca52204ae02927b2ad9b8a4fcf6bb"
WAVE3_PROVENANCE_ENTERED_DATE = "2026-09-02"

#: Commit in which the Wave 3 rows were first scored against.
WAVE3_PROVENANCE_FIRST_SCORED_COMMIT = "7f25bed2377ca52204ae02927b2ad9b8a4fcf6bb"


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
    "CalibratedTarget",
    "assert_target_revisions",
    "live_target_for",
    "revisions_for",
    "superseded_targets_for",
    "target_revision_problems",
    "target_was_revised",
]
