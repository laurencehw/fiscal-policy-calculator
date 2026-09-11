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
    IIJA_AUTHORIZATION_PATH_RULE,
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
        if case.retired:
            # Withdrawn, not replaced: there is no successor row to point at.
            continue
        assert case.superseded_by in ids


def test_retired_rows_say_why_and_are_not_live():
    """A case can leave the honest tier only by saying what was searched.
    Silently dropping a badly-scoring target is the failure mode this guards."""
    from fiscal_model.validation.preregistered import retired_cases

    retired = retired_cases()
    assert retired, "expected at least one retired row (top_rate_45.v1)"
    for case in retired:
        assert not case.is_live
        assert case.superseded_by is None
        assert len(case.retired_reason.strip()) > 80, (
            f"{case.case_id} was withdrawn with a one-line excuse"
        )


def test_retired_row_without_a_reason_is_rejected(monkeypatch):
    import fiscal_model.validation.preregistered as prereg

    tampered = tuple(
        replace(case, retired=True, retired_reason="")
        if case.policy_id == "biden_high_income_tax" and case.is_live
        else case
        for case in PREREGISTERED_CASES
    )
    monkeypatch.setattr(prereg, "PREREGISTERED_CASES", tampered)
    problems = prereg.manifest_problems(SimpleNamespace(entries=[]))
    assert any("retired with no retired_reason" in p for p in problems)


# ── A shape input may change only by superseding its row ───────────────────


def test_iija_shape_change_is_a_new_row_with_the_same_target():
    """The IIJA authorization path replaced a *shape input*, not a target. The
    rule is the same either way: a new row, the old one superseded and kept,
    and CBO's published figure untouched on both."""
    rows = {c.case_id: c for c in PREREGISTERED_CASES}
    v1 = rows["iija_2021_discretionary.v1"]
    v2 = rows["iija_2021_discretionary.v2"]

    assert v1.superseded_by == "iija_2021_discretionary.v2"
    # v2 is itself superseded now (owner decision (3) registered .v3), so
    # neither is live. What this test pins is the supersession chain and the
    # target's immobility across it, not which row is in force — and a
    # superseded row must stay in the file unedited, which is what makes the
    # chain readable.
    assert not v1.is_live and not v2.is_live
    assert v1.official_10yr_billions == v2.official_10yr_billions
    assert v1.source_url == v2.source_url
    assert v1.source_date == v2.source_date
    # The entry commit must precede the first scoring run: the shape input is
    # frozen in the history before the mechanism is allowed to read it.
    assert v2.entered_commit != v2.first_scoring_run_commit


def test_iija_window_change_is_a_third_row_with_the_same_target():
    """Owner decision (3): the window is the third shape input this case has
    carried, and the target has not moved once across all three.

    The interesting assertion is the last one. ``effective_start_year`` was
    already 2022, so the *policy* does not move at all — only the scorer's
    window does, which is what separates a window from a vintage and from an
    effective date.
    """
    rows = {c.case_id: c for c in PREREGISTERED_CASES}
    v2 = rows["iija_2021_discretionary.v2"]
    v3 = rows["iija_2021_discretionary.v3"]

    assert v2.superseded_by == "iija_2021_discretionary.v3"
    assert not v2.is_live and v3.is_live
    assert (
        rows["iija_2021_discretionary.v1"].official_10yr_billions
        == v2.official_10yr_billions
        == v3.official_10yr_billions
        == 415.448
    )
    assert v2.source_url == v3.source_url
    assert v2.source_date == v3.source_date
    # The entry commit must precede the first scoring run.
    assert v3.entered_commit != v3.first_scoring_run_commit
    # Both rules apply to the live row: the authority path is still CBO's own.
    assert IIJA_AUTHORIZATION_PATH_RULE in v3.note

    score = KNOWN_SCORES["iija_2021_discretionary"]
    assert score.scoring_window_first_year == 2022
    assert score.effective_start_year == 2022


def test_fy2022_window_change_is_a_new_row_with_the_same_target():
    """The FY2022 Green Book window replaced a *shape input*, not a target —
    the same move IIJA's .v2 made, and held to the same rule: a new row, the
    old one superseded and kept, and Treasury's published figure untouched on
    both."""
    rows = {c.case_id: c for c in PREREGISTERED_CASES}
    v1 = rows["treasury_capgains_39_plus_stepup_elim.v1"]
    v2 = rows["treasury_capgains_39_plus_stepup_elim.v2"]

    assert v1.superseded_by == "treasury_capgains_39_plus_stepup_elim.v2"
    assert not v1.is_live and v2.is_live
    assert v1.official_10yr_billions == v2.official_10yr_billions == -322.0
    assert v1.source_date == v2.source_date
    assert v1.source_baseline_vintage == v2.source_baseline_vintage
    # The entry commit must precede the first scoring run: the shape input is
    # frozen in the history before the mechanism is allowed to read it.
    assert v2.entered_commit != v2.first_scoring_run_commit
    # v1 carried no URL; the successor names the volume it transcribes.
    assert v1.source_url is None
    assert v2.source_url is not None and "FY2022" in v2.source_url


def test_the_fy2022_window_rule_is_recorded_not_left_per_case():
    """A per-case choice of decade would be a knob. One rule sets it, and it
    names the record field the window is already transcribed into."""
    from fiscal_model.validation.preregistered import FY2022_TARGET_WINDOW_RULE

    assert "budget_window" in FY2022_TARGET_WINDOW_RULE
    assert "effective_start_year" in FY2022_TARGET_WINDOW_RULE
    rows = {c.case_id: c for c in PREREGISTERED_CASES}
    # Every live row that carries a window quotes the rule that set it, so the
    # rule cannot be a preamble one row honours and the next does not.
    windowed = {
        policy_id
        for policy_id, score in KNOWN_SCORES.items()
        if score.scoring_window_first_year is not None
    }
    live = {case.policy_id: case for case in PREREGISTERED_CASES if case.is_live}
    assert windowed <= set(live)
    for policy_id in windowed:
        assert FY2022_TARGET_WINDOW_RULE in live[policy_id].note, (
            f"{live[policy_id].case_id} carries a window without quoting the "
            f"rule that sets it"
        )
    assert FY2022_TARGET_WINDOW_RULE in rows[
        "treasury_capgains_39_plus_stepup_elim.v2"
    ].note


def test_the_window_a_case_is_scored_on_is_the_one_its_source_published():
    """The shape input itself: the record's scoring window must equal the first
    year of the window its own ``budget_window`` states. A window chosen any
    other way would be a knob, and this is the assertion that says so."""
    score = KNOWN_SCORES["treasury_capgains_39_plus_stepup_elim"]
    assert score.budget_window == "FY2022-2031"
    assert score.scoring_window_first_year == 2022


def test_only_rows_the_manifest_superseded_name_their_own_window():
    """Every other record keeps the runner's window, so the field cannot be a
    general lever on the tier.

    Two cases carry one, and each got it through a manifest supersession whose
    target did not move: ``treasury_capgains_39_plus_stepup_elim.v2`` (PR #126)
    and ``iija_2021_discretionary.v3`` (owner decision (3)). The stronger
    assertion is the second one — a window is not a number a lane may pick, it
    is the first year of the window the record's own ``budget_window`` states,
    which is :data:`FY2022_TARGET_WINDOW_RULE` written as a test.
    """
    named = {
        policy_id
        for policy_id, score in KNOWN_SCORES.items()
        if score.scoring_window_first_year is not None
    }
    assert named == {
        "treasury_capgains_39_plus_stepup_elim",
        "iija_2021_discretionary",
    }
    for policy_id in named:
        score = KNOWN_SCORES[policy_id]
        stated = int(str(score.budget_window).split("-")[0].removeprefix("FY"))
        assert score.scoring_window_first_year == stated, (
            f"{policy_id}: window {score.scoring_window_first_year} is not the "
            f"first year of its own budget_window {score.budget_window}"
        )


def test_a_named_window_is_the_decade_the_case_is_actually_scored_on():
    """The shape input has to reach the runner, or the manifest row is prose.

    Deliberately *relational* rather than a pinned level: the death channel is
    an open modelling lane, so this asserts what the window does — the policy
    starts in the source's own first year, and the same policy on the source's
    own decade scores a smaller magnitude than on a decade three years later,
    because both channels grow with household net worth."""
    import copy

    from fiscal_model.validation.core import (
        DEFAULT_VALIDATION_START_YEAR,
        _resolve_window_start,
        build_scorer_for_vintage,
        create_policy_from_score,
    )

    score = KNOWN_SCORES["treasury_capgains_39_plus_stepup_elim"]
    assert _resolve_window_start(score) == 2022

    policy = create_policy_from_score(score)
    assert policy is not None
    assert policy.start_year == 2022

    on_source = build_scorer_for_vintage(None, start_year=2022).score_policy(
        policy, dynamic=False
    )
    later = copy.deepcopy(policy)
    later.start_year = DEFAULT_VALIDATION_START_YEAR
    on_default = build_scorer_for_vintage(
        None, start_year=DEFAULT_VALIDATION_START_YEAR
    ).score_policy(later, dynamic=False)

    assert abs(on_source.total_10_year_cost) < abs(on_default.total_10_year_cost)
    official = score.ten_year_cost
    assert abs(on_source.total_10_year_cost - official) < abs(
        on_default.total_10_year_cost - official
    )


def test_a_record_without_a_window_keeps_the_runners_own():
    """The field must be inert everywhere else, or it is a lever on the tier."""
    from fiscal_model.validation.core import (
        DEFAULT_VALIDATION_START_YEAR,
        _resolve_window_start,
        create_policy_from_score,
    )

    score = KNOWN_SCORES["warren_ultramillionaire_surtax_3pp"]
    assert score.scoring_window_first_year is None
    assert _resolve_window_start(score) == DEFAULT_VALIDATION_START_YEAR
    policy = create_policy_from_score(score)
    assert policy is not None
    assert policy.start_year == DEFAULT_VALIDATION_START_YEAR


def test_effective_start_year_still_beats_a_window():
    """A source that states an effective date states a different fact from the
    window it publishes over, and it keeps precedence — IIJA sets both."""
    from dataclasses import replace as dc_replace

    from fiscal_model.validation.core import create_policy_from_score

    tampered = dc_replace(
        KNOWN_SCORES["iija_2021_discretionary"], scoring_window_first_year=2019
    )
    policy = create_policy_from_score(tampered)
    assert policy is not None
    assert tampered.effective_start_year == 2022
    assert policy.start_year == 2022


def test_the_iija_path_rule_is_recorded_not_left_per_year():
    """A per-year choice of budget authority would be a knob. One rule sets
    every year, and it names the source's own total."""
    from fiscal_model.validation.preregistered import IIJA_AUTHORIZATION_PATH_RULE

    assert "446,306" in IIJA_AUTHORIZATION_PATH_RULE
    rows = {c.case_id: c for c in PREREGISTERED_CASES}
    assert IIJA_AUTHORIZATION_PATH_RULE in rows["iija_2021_discretionary.v2"].note


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
        if case.policy_id == "biden_high_income_tax" and case.is_live
        else case
        for case in PREREGISTERED_CASES
    )
    monkeypatch.setattr(prereg, "PREREGISTERED_CASES", tampered)

    problems = prereg.manifest_problems(SimpleNamespace(entries=[]))
    assert any("must be a NEW row" in p for p in problems)


def test_duplicate_live_rows_are_rejected(monkeypatch):
    import fiscal_model.validation.preregistered as prereg

    original = next(
        c
        for c in PREREGISTERED_CASES
        if c.policy_id == "biden_high_income_tax" and c.is_live
    )
    duplicate = replace(original, case_id="biden_high_income_tax.v3")
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
