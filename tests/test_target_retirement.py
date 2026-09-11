"""
Tests for the calibrated-target ledger's third state: **retirement**.

A supersession says *the target moved here*. An ``EXAMINED_NOT_REVISED`` verdict
says *somebody opened the document and kept the carried figure*. Retirement says
the third thing — *this figure is not a score of anything and nothing replaces
it* — and it is the only one of the three that removes a row's target without
providing another.

That makes it the one state that could be abused, so most of what is asserted
here is the guard rather than the feature: a retired row keeps its scorecard
entry, is counted, and is reported beside the tier it left **with the tier
recomputed as if it had stayed**. `planning/HIGH_STAKES_ACCURACY.md` §5's "no
removing a case to go green" is the rule; these tests are what makes it
checkable.

Nothing is retired today — owner decision (4) on the two pharma illustrations is
open — so the state is exercised on synthetic ledger rows. The first test pins
that emptiness, so applying a retirement can never be an accident.
"""

from __future__ import annotations

import dataclasses

import pytest

from fiscal_model.validation.scorecard import (
    GENERIC_CATEGORY,
    ScorecardEntry,
    cached_default_scorecard,
)
from fiscal_model.validation.target_revisions import (
    CALIBRATED_TARGETS,
    EXAMINED_NOT_REVISED,
    RETIRED_POLICY_IDS,
    REVISED_POLICY_IDS,
    CalibratedTarget,
    live_target_for,
    retired_target_for,
    retired_targets,
    target_was_retired,
    target_was_revised,
)

#: A benchmark whose target the ledger has *revised*, used as the donor for the
#: synthetic retirements below.
DONOR = "pillar_two_adoption"


def _retired_row(policy_id: str = "synthetic_benchmark", **overrides):
    """One well-formed retired ledger row."""
    fields = {
        "revision_id": f"{policy_id}.v1",
        "policy_id": policy_id,
        "official_10yr_billions": -500.0,
        "source_name": "none",
        "source_date": "2024",
        "window": "stated as 10-year; not traceable to any published window",
        "entered_commit": "0" * 40,
        "entered_date": "2026-09-09",
        "first_scoring_run_commit": "0" * 40,
        "retired": True,
        "retired_reason": (
            "Withdrawn: the figure is the repository's own extrapolation and no "
            "published score of this policy exists to replace it. Searched CBO, "
            "JCT, CMS and CRFB."
        ),
    }
    fields.update(overrides)
    return CalibratedTarget(**fields)


def _about(policy_id: str, problems: list[str]) -> list[str]:
    """Only the problems naming one benchmark.

    ``target_revision_problems(entries)`` reports every ledger row that has no
    matching scorecard entry, so a test that supplies one entry cannot compare
    the whole list to ``[]``.
    """
    return [p for p in problems if p.startswith(f"{policy_id}:")]


def _with_rows(monkeypatch, *rows):
    """Run the ledger with ``rows`` appended to the live registry."""
    from fiscal_model.validation import target_revisions as tr

    monkeypatch.setattr(
        tr, "CALIBRATED_TARGETS", tuple(CALIBRATED_TARGETS) + tuple(rows)
    )
    return tr


# ---------------------------------------------------------------------------
# The state exists and is not applied
# ---------------------------------------------------------------------------


def test_exactly_the_two_targets_the_owner_withdrew_are_retired():
    """Owner decision (4), applied: the pharma pair and nothing else.

    This test was ``test_nothing_is_retired_yet`` while the decision was open,
    and inverting it is the whole point of it — the set is pinned in both
    states, so a third retirement cannot arrive without somebody editing this
    line and saying why in a PR. Each row also has to state a reason and keep
    the withdrawn figure, because a retirement that carried neither would be a
    deletion wearing the state's name.
    """
    assert RETIRED_POLICY_IDS == frozenset(
        {"expand_drug_negotiation", "international_reference_pricing"}
    )
    rows = {row.policy_id: row for row in retired_targets()}
    assert set(rows) == RETIRED_POLICY_IDS
    assert rows["expand_drug_negotiation"].official_10yr_billions == -500.0
    assert rows["international_reference_pricing"].official_10yr_billions == -100.0
    for row in rows.values():
        # The search, and what would bring the target back. Both verdicts name
        # the CBO document that scores the nearest published quantity.
        assert "Searched on 2026-09-09" in row.retired_reason
        assert "WHAT WOULD BRING IT BACK" in row.retired_reason
        assert not row.is_live and row.superseded_by is None

    scorecard = cached_default_scorecard()
    assert scorecard.retired_target_entries == 2
    withdrawn = [e for e in scorecard.entries if e.target_retired]
    assert {e.policy_id for e in withdrawn} == RETIRED_POLICY_IDS
    for entry in withdrawn:
        # Kept, not deleted: the row still prints its model figure and the
        # figure that was withdrawn, and it leaves the fitted tier the way a
        # revision does.
        assert entry.model_10yr_billions != 0.0
        assert entry.calibrated_to_target is False
        assert entry.target_retirement_reason


def test_a_retired_benchmark_is_not_also_examined_and_left():
    """The two states contradict each other and the ledger enforces it, so the
    keys the owner withdrew must have left ``EXAMINED_NOT_REVISED`` with them.
    """
    assert RETIRED_POLICY_IDS.isdisjoint(EXAMINED_NOT_REVISED)


def test_retired_and_revised_are_different_states():
    """A withdrawal is not a supersession, and the accessors must not blur them.

    ``superseded_targets_for`` is keyed on ``superseded_by``, never on "not
    live", because a retired row is also not live — and a surface reporting
    ``superseded_10yr_billions`` would then show a withdrawn figure as a
    revision's history.
    """
    assert RETIRED_POLICY_IDS.isdisjoint(REVISED_POLICY_IDS)
    assert target_was_revised(DONOR)
    assert not target_was_retired(DONOR)


def test_a_retired_row_is_not_reported_as_superseded(monkeypatch):
    tr = _with_rows(monkeypatch, _retired_row())
    assert tr.superseded_targets_for("synthetic_benchmark") == ()
    assert tr.retired_target_for("synthetic_benchmark") is not None
    assert tr.live_target_for("synthetic_benchmark") is None
    assert tr.target_revision_problems() == []


# ---------------------------------------------------------------------------
# The ledger's guards
# ---------------------------------------------------------------------------


def test_a_retirement_must_state_its_reason(monkeypatch):
    """A row withdrawn with no reason is indistinguishable from a deletion."""
    tr = _with_rows(monkeypatch, _retired_row(retired_reason="   "))
    assert any("retired with no retired_reason" in p for p in tr.target_revision_problems())


def test_a_row_cannot_be_both_retired_and_superseded(monkeypatch):
    """A withdrawal has no replacement; a supersession is nothing but one."""
    tr = _with_rows(
        monkeypatch,
        _retired_row(superseded_by="synthetic_benchmark.v2"),
        _retired_row(
            policy_id="synthetic_benchmark",
            revision_id="synthetic_benchmark.v2",
            retired=False,
            retired_reason="",
            reason="replacement",
        ),
    )
    problems = tr.target_revision_problems()
    assert any("both retired and superseded_by" in p for p in problems)


def test_a_withdrawal_is_final(monkeypatch):
    """Nothing may be live after a retirement.

    Otherwise the ledger asserts both "this target does not exist" and "this is
    the target" for the same benchmark.
    """
    tr = _with_rows(
        monkeypatch,
        _retired_row(),
        _retired_row(
            revision_id="synthetic_benchmark.v2",
            retired=False,
            retired_reason="",
            official_10yr_billions=-400.0,
        ),
    )
    problems = tr.target_revision_problems()
    assert any("a withdrawal is final" in p for p in problems)


def test_a_retirement_and_an_examined_verdict_are_mutually_exclusive(monkeypatch):
    """Three states, and a benchmark is in exactly one of them."""
    tr = _with_rows(monkeypatch, _retired_row())
    monkeypatch.setattr(
        tr,
        "EXAMINED_NOT_REVISED",
        {**EXAMINED_NOT_REVISED, "synthetic_benchmark": "contradiction"},
    )
    problems = tr.target_revision_problems()
    assert any("examined-and-left AND carries a ledger row" in p for p in problems)


def test_the_scorecard_must_say_a_retired_target_is_retired(monkeypatch):
    """The consistency check a retirement replaces the equality check with.

    A point row is checked by asking whether the scorecard scores against the
    live figure. A retired row has no live figure, so what is checked instead
    is that the entry is *marked* — a withdrawn target still reported as an
    ordinary benchmark is the silent deletion this state exists to prevent.
    """
    tr = _with_rows(monkeypatch, _retired_row())
    unmarked = _entry("synthetic_benchmark", official=-500.0, model=-33.5)
    problems = tr.target_revision_problems([unmarked])
    assert any("not marked retired" in p for p in problems)

    # Only this benchmark's verdict is under test: passing a one-entry list
    # makes every *other* ledger row report a missing scorecard entry.
    marked = dataclasses.replace(unmarked, target_retired=True)
    assert _about("synthetic_benchmark", tr.target_revision_problems([marked])) == []


# ---------------------------------------------------------------------------
# What it does to an entry and to the tiers
# ---------------------------------------------------------------------------


def _entry(policy_id: str, *, official: float, model: float, category: str = "Pharma"):
    difference = model - official
    return ScorecardEntry(
        category=category,
        policy_id=policy_id,
        policy_name=policy_id,
        official_10yr_billions=official,
        official_source="Model estimate",
        benchmark_kind="Model estimate",
        benchmark_date=None,
        benchmark_url=None,
        model_10yr_billions=model,
        difference_billions=difference,
        percent_difference=difference / official * 100.0,
        abs_percent_difference=abs(difference / official * 100.0),
        rating="Poor",
        direction_match=True,
        known_limitations=["documented"],
        notes="",
        provenance="model_estimate",
        calibrated_to_target=False,
    )


def test_a_retired_target_leaves_the_fitted_tier_the_way_a_revision_does(monkeypatch):
    """A constant fitted to a withdrawn figure is not fitted to anything live."""
    from fiscal_model.validation import scorecard as sc
    from fiscal_model.validation.core import ValidationResult

    _with_rows(monkeypatch, _retired_row(policy_id="expand_drug_negotiation"))
    result = ValidationResult(
        policy_id="expand_drug_negotiation",
        policy_name="Expand Drug Negotiation",
        official_10yr=-500.0,
        official_source="Model estimate",
        model_10yr=-33.5,
        model_first_year=0.0,
        difference=466.5,
        percent_difference=93.3,
        direction_match=True,
        accuracy_rating="Poor",
        model_parameters={"calibrated_to_target": True},
    )
    entry = sc.ScorecardEntry.from_result("Pharma", result)
    assert entry.target_retired is True
    assert entry.calibrated_to_target is False
    # The runner still declared it fitted; only the ledger changed its mind.
    assert entry.declared_calibrated_to_target is True
    assert "no published score" in entry.target_retirement_reason
    # And a withdrawal is not a revision, so none of the revision fields fire.
    assert entry.target_revision_id is None
    assert entry.superseded_10yr_billions is None


def test_a_retired_row_leaves_the_reconstruction_mean_and_is_printed_beside_it(
    monkeypatch,
):
    """The guard that makes the whole state safe.

    Retiring the two pharma illustrations would take 93.3% and 701.0% out of a
    tier averaging 57.9% over 34 rows. Both readings are produced, so the
    smaller one can never be quoted without the larger one being on the page.
    """
    import scripts.cold_holdout as ch

    keep = _entry("kept_reconstruction", official=-100.0, model=-150.0)  # 50%
    withdrawn = _entry("withdrawn_illustration", official=-100.0, model=-800.0)  # 700%
    withdrawn = dataclasses.replace(withdrawn, target_retired=True)
    generic = _entry(
        "generic_case", official=-100.0, model=-110.0, category=GENERIC_CATEGORY
    )

    class _Summary:
        entries = [keep, withdrawn, generic]

    monkeypatch.setattr(ch, "compute_scorecard", lambda: _Summary())
    report = ch.build_report()

    recon = report["uncalibrated_reconstruction"]["summary"]
    retired = report["retired_targets"]["summary"]
    held = report["uncalibrated_reconstruction_retired_held_in_place"]["summary"]

    assert recon["n"] == 1
    assert recon["mean_abs_error"] == pytest.approx(50.0)
    assert retired["n"] == 1
    assert retired["mean_abs_error"] == pytest.approx(700.0)
    # Held in place is the tier as if nothing had been withdrawn. It is the
    # number that stops a withdrawal reading as an improvement.
    assert held["n"] == 2
    assert held["mean_abs_error"] == pytest.approx(375.0)
    # The withdrawn row keeps its scorecard entry and its model figure.
    assert report["retired_targets"]["entries"][0]["model_10yr_billions"] == pytest.approx(
        -800.0
    )
    assert report["retired_targets"]["entries"][0]["target_retired"] is True


def test_the_human_report_prints_both_readings(monkeypatch, capsys):
    import scripts.cold_holdout as ch

    keep = _entry("kept_reconstruction", official=-100.0, model=-150.0)
    withdrawn = dataclasses.replace(
        _entry("withdrawn_illustration", official=-100.0, model=-800.0),
        target_retired=True,
    )
    generic = _entry(
        "generic_case", official=-100.0, model=-110.0, category=GENERIC_CATEGORY
    )

    class _Summary:
        entries = [keep, withdrawn, generic]

    monkeypatch.setattr(ch, "compute_scorecard", lambda: _Summary())
    ch._print_human(ch.build_report())
    out = capsys.readouterr().out
    assert "RETIRED TARGETS" in out
    assert "withdrawn_illustration" in out
    assert "1 @ 50.0%" in out and "2 @ 375.0%" in out
    assert "is not a tier\n  that improved" in out or "not a tier" in out


def test_the_dashboard_prints_the_retired_block(monkeypatch, capsys):
    """The dashboard is the report PR #130 added because PR #119 moved two
    calibrated tiers and left it byte-identical. A withdrawal has to be visible
    there for the same reason."""
    import scripts.run_validation_dashboard as dash

    tiers = {
        "fitted": {"n": 2, "mean_abs_error": 1.7, "median_abs_error": 0.0,
                   "within_15pct": 2, "within_25pct": 2},
        "fitted_held_in_place": {"n": 3, "mean_abs_error": 5.6,
                                 "median_abs_error": 0.3, "within_15pct": 3,
                                 "within_25pct": 3},
        "reconstruction": {"n": 32, "mean_abs_error": 36.7,
                           "median_abs_error": 30.0, "within_15pct": 9,
                           "within_25pct": 12},
        "retired": {"n": 2, "mean_abs_error": 397.2, "median_abs_error": 397.2,
                    "within_15pct": 0, "within_25pct": 0},
        "reconstruction_retired_held_in_place": {
            "n": 34, "mean_abs_error": 57.9, "median_abs_error": 34.2,
            "within_15pct": 9, "within_25pct": 12,
        },
        "retired_target_ids": ["expand_drug_negotiation", "international_reference_pricing"],
        "revised_target_entries": 16,
        "revised_from_fitted_tier": [],
        "reconstruction_sub_populations": {},
        "provenance_breakdown": {},
        "calibrated_provenance_breakdown": {},
        "published_entries": 73,
        "model_estimate_entries": 4,
        "transcribed_entries": 36,
        "line_item_differs_entries": 7,
        "total_entries": 81,
    }
    dash.print_calibrated_tiers(tiers)
    out = capsys.readouterr().out
    assert "retired targets:     n=2" in out
    assert "expand_drug_negotiation" in out
    # Both readings on the page, and the sentence that says why.
    assert "... retired held in: n=34" in out
    assert "reconstructions:     n=32" in out
    assert "withdrawn with nothing to replace it" in out


def test_readiness_lists_a_retired_row_rather_than_blocking_on_it(monkeypatch):
    """A retired row has no target, so blocking on its rating would make
    deleting it the cheapest way back to green. It is listed instead."""
    from fiscal_model import readiness

    withdrawn = dataclasses.replace(
        _entry("withdrawn_illustration", official=-100.0, model=-800.0),
        target_retired=True,
    )

    class _Summary:
        entries = [
            _entry("ordinary", official=-100.0, model=-101.0),
            withdrawn,
        ]
        within_15pct = 1
        median_abs_percent_difference = 1.0

    checks = readiness._scorecard_checks(_Summary())
    scorecard_check = next(c for c in checks if c.name == "revenue_scorecard")
    assert scorecard_check.details["retired_target_policy_ids"] == [
        "withdrawn_illustration"
    ]
    # A documented Poor on an unfitted row is a warning, never a strict block.
    assert scorecard_check.status in {"warn", "pass"}


def test_a_live_row_is_still_checked_for_equality(monkeypatch):
    """The retirement branch must not swallow the check it replaces."""
    from fiscal_model.validation import target_revisions as tr

    live = live_target_for(DONOR)
    assert live is not None
    entry = _entry(DONOR, official=-80.0, model=-61.2, category="International")
    assert _about(DONOR, tr.target_revision_problems([entry])) == []
    wrong = dataclasses.replace(entry, official_10yr_billions=-999.0)
    assert any(
        "outside the published range" in p for p in tr.target_revision_problems([wrong])
    )


def test_retired_target_for_returns_none_for_an_ordinary_benchmark():
    assert retired_target_for("pillar_two_adoption") is None
    assert retired_target_for("not_a_benchmark") is None
