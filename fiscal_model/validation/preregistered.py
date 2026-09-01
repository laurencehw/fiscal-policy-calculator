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
    note: str = ""

    @property
    def is_live(self) -> bool:
        """A row still in force (not replaced by a later row)."""
        return self.superseded_by is None


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
        note=(
            "Record existed from 2025-12-08 but was unreachable: get_validation_targets() "
            "kept only policy_type == 'income_tax'. First scored in Phase A on the "
            "uncalibrated capital-gains path with frozen module-default elasticities."
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
        note=(
            "Kept despite a >100% miss. The target fails an internal coherence check "
            "against illustrative_top_rate_5pp (same source: +5pp above $1M = -$700B), "
            "so part of the error is target error. Registered so that a future "
            "correction has to appear as a new row, not an edit."
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
)


def live_cases() -> dict[str, PreregisteredCase]:
    """Manifest rows still in force, keyed by ``policy_id``."""
    return {case.policy_id: case for case in PREREGISTERED_CASES if case.is_live}


def superseded_cases() -> tuple[PreregisteredCase, ...]:
    """Manifest rows replaced by a later row (kept as history)."""
    return tuple(case for case in PREREGISTERED_CASES if not case.is_live)


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
        "policy_ids": sorted(live),
        "phase_a_commit": PHASE_A_COMMIT,
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
    "PHASE_A_COMMIT",
    "PREREGISTERED_CASES",
    "PreregisteredCase",
    "assert_preregistered",
    "get_case",
    "live_cases",
    "manifest_problems",
    "summarize_preregistration",
    "superseded_cases",
]
