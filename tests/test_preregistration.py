"""
Pre-registration manifest for the out-of-sample tier.

The Generic tier is the only one that claims predictive skill. These tests
enforce the discipline that makes the claim meaningful: every scored
out-of-sample case has a manifest row, and no manifest target may be edited to
match a later model run.
"""

import re
from dataclasses import replace
from types import SimpleNamespace

import pytest

from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.preregistered import (
    PHASE_A_COMMIT,
    PREREGISTERED_CASES,
    assert_preregistered,
    get_case,
    live_cases,
    manifest_problems,
    summarize_preregistration,
    superseded_cases,
)
from fiscal_model.validation.scorecard import cached_default_scorecard

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _entry(policy_id: str, official: float, category: str = "Generic"):
    return SimpleNamespace(
        category=category,
        policy_id=policy_id,
        official_10yr_billions=official,
    )


# ── The live scorecard must satisfy the manifest ───────────────────────────


def test_live_scorecard_is_fully_preregistered():
    assert_preregistered(cached_default_scorecard())


def test_every_generic_scorecard_entry_has_a_manifest_row():
    registered = live_cases()
    generic = [
        e for e in cached_default_scorecard().entries if e.category == "Generic"
    ]
    assert generic, "expected a non-empty out-of-sample tier"
    for entry in generic:
        assert entry.policy_id in registered, (
            f"{entry.policy_id} is scored out-of-sample but not pre-registered"
        )


def test_manifest_targets_match_the_score_database():
    for case in PREREGISTERED_CASES:
        if not case.is_live:
            continue
        score = KNOWN_SCORES[case.policy_id]
        assert float(score.ten_year_cost) == float(case.official_10yr_billions)


def test_manifest_rows_carry_full_provenance():
    for case in PREREGISTERED_CASES:
        assert case.source_name
        assert case.source_date
        assert case.source_baseline_vintage
        assert case.entered_commit
        assert case.entered_date
        assert case.first_scoring_run_commit


def test_commit_stamps_are_real_shas():
    """A row whose commit is still the 'PENDING' placeholder is unstamped and
    the manifest cannot be audited."""
    for case in PREREGISTERED_CASES:
        for field_name in ("entered_commit", "first_scoring_run_commit"):
            value = getattr(case, field_name)
            assert _SHA_RE.match(value), (
                f"{case.case_id}.{field_name} is not a 40-hex commit sha: {value!r}"
            )
    assert _SHA_RE.match(PHASE_A_COMMIT)


def test_case_ids_are_unique():
    ids = [case.case_id for case in PREREGISTERED_CASES]
    assert len(ids) == len(set(ids))


def test_one_live_row_per_policy():
    live = [case.policy_id for case in PREREGISTERED_CASES if case.is_live]
    assert len(live) == len(set(live))


def test_superseded_rows_point_at_an_existing_row():
    ids = {case.case_id for case in PREREGISTERED_CASES}
    for case in superseded_cases():
        assert case.superseded_by in ids


# ── The manifest must actually catch violations ────────────────────────────


def test_unregistered_out_of_sample_case_is_rejected():
    scorecard = SimpleNamespace(entries=[_entry("not_registered_anywhere", -100.0)])
    problems = manifest_problems(scorecard)
    assert any("no pre-registration row" in p for p in problems)
    with pytest.raises(AssertionError):
        assert_preregistered(scorecard)


def test_target_drift_between_scorecard_and_manifest_is_rejected():
    case = get_case("biden_high_income_tax")
    assert case is not None
    scorecard = SimpleNamespace(
        entries=[_entry("biden_high_income_tax", case.official_10yr_billions + 50.0)]
    )
    problems = manifest_problems(scorecard)
    assert any("!= pre-registered" in p for p in problems)


def test_edited_manifest_target_is_rejected(monkeypatch):
    """The core rule: a changed target must become a NEW row with a new
    case_id, never an in-place edit of the frozen one."""
    import fiscal_model.validation.preregistered as prereg

    tampered = tuple(
        replace(case, official_10yr_billions=case.official_10yr_billions * 1.1)
        if case.policy_id == "top_rate_45"
        else case
        for case in PREREGISTERED_CASES
    )
    monkeypatch.setattr(prereg, "PREREGISTERED_CASES", tampered)

    problems = prereg.manifest_problems(SimpleNamespace(entries=[]))
    assert any("must be a NEW row" in p for p in problems)


def test_duplicate_live_rows_are_rejected(monkeypatch):
    import fiscal_model.validation.preregistered as prereg

    original = next(c for c in PREREGISTERED_CASES if c.policy_id == "top_rate_45")
    duplicate = replace(original, case_id="top_rate_45.v2")
    monkeypatch.setattr(
        prereg, "PREREGISTERED_CASES", (*PREREGISTERED_CASES, duplicate)
    )

    problems = prereg.manifest_problems(SimpleNamespace(entries=[]))
    assert any("two live manifest rows" in p for p in problems)


def test_calibrated_entries_do_not_need_a_manifest_row():
    scorecard = SimpleNamespace(entries=[_entry("tcja_full_extension", 4600.0, "TCJA")])
    assert manifest_problems(scorecard) == []


def test_summary_is_serializable():
    summary = summarize_preregistration()
    assert summary["live_cases"] == len(live_cases())
    assert summary["rows"]
    for row in summary["rows"]:
        assert set(row) >= {
            "case_id",
            "policy_id",
            "official_10yr_billions",
            "source_name",
            "source_baseline_vintage",
            "entered_commit",
            "first_scoring_run_commit",
        }
