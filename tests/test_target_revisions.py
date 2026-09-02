"""
Tests for the calibrated-target supersede ledger.

The ledger's job is to make a moved Tier 2 target *auditable*: the old figure
stays in the file, the new one cites the row it was read from, and the
registries the app and the runners actually read agree with the live row. These
tests assert each of those, plus the two consequences a revision has — the
transcription stops disagreeing, and the entry leaves the fitted tier.
"""

from __future__ import annotations

import dataclasses

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.preset_ids import PRESET_ID_BY_LABEL
from fiscal_model.validation.benchmark_sources import (
    CONFIRMATION_TOLERANCE_PCT,
    source_for,
)
from fiscal_model.validation.preregistered import PREREGISTERED_CASES
from fiscal_model.validation.provenance import LINE_ITEM
from fiscal_model.validation.scorecard import (
    GENERIC_CATEGORY,
    cached_default_scorecard,
)
from fiscal_model.validation.target_revisions import (
    CALIBRATED_TARGETS,
    REVISED_POLICY_IDS,
    assert_target_revisions,
    live_target_for,
    superseded_targets_for,
    target_revision_problems,
    target_was_revised,
)


@pytest.fixture(scope="module")
def scorecard():
    return cached_default_scorecard()


def test_the_ledger_is_internally_consistent():
    """Unique ids, one live row per benchmark, both halves reasoned, the
    replacement cites a document, and the figure actually moved."""
    assert target_revision_problems() == []


@pytest.mark.parametrize(
    "revision_id",
    ["extend_tcja_amt", "extend_tcja_amt.", "extend_tcja_amt.2", "extend_tcja_amt.v0"],
)
def test_a_malformed_revision_id_is_rejected(revision_id, monkeypatch):
    """The id carries the version ordering, so the suffix is checked and not
    only the prefix: a ledger whose rows do not sort cannot be read as a
    history."""
    from fiscal_model.validation import target_revisions as tr

    row = tr.CALIBRATED_TARGETS[0]
    monkeypatch.setattr(
        tr,
        "CALIBRATED_TARGETS",
        (dataclasses.replace(row, revision_id=revision_id, superseded_by=None),),
    )
    problems = tr.target_revision_problems()
    assert any("'.v<n>'" in problem for problem in problems)


def test_the_ledger_agrees_with_what_the_scorecard_scores(scorecard):
    """The check that earns the ledger its keep: it does not *supply* a target,
    so nothing stops ``scenarios.py`` or ``CBO_SCORE_MAP`` drifting away from
    it except this."""
    assert_target_revisions(scorecard.entries)


def test_a_revised_target_is_never_a_tier_1_case():
    """Tier 1 has its own manifest with its own rule. A target appearing in
    both ledgers would mean two mechanisms could move the same number."""
    tier1 = {case.policy_id for case in PREREGISTERED_CASES}
    assert REVISED_POLICY_IDS.isdisjoint(tier1)


def test_tier_1_is_untouched_by_this_pass(scorecard):
    """The out-of-sample tier must not move at all: no Generic entry has a
    revision, and none of them is even eligible for one."""
    generic = [e for e in scorecard.entries if e.category == GENERIC_CATEGORY]
    assert generic, "expected a populated out-of-sample tier"
    assert all(e.target_revision_id is None for e in generic)
    assert all(not target_was_revised(e.policy_id) for e in generic)


@pytest.mark.parametrize("policy_id", sorted(REVISED_POLICY_IDS))
def test_a_revised_row_leaves_the_fitted_tier(policy_id, scorecard):
    """The module constant reproduces the *superseded* figure, so the entry is
    no longer fitted to the target it is scored against. Reporting it in the
    fitted tier would claim a calibration that does not exist."""
    entry = next(e for e in scorecard.entries if e.policy_id == policy_id)
    assert entry.calibrated_to_target is False
    assert entry.target_revision_id == live_target_for(policy_id).revision_id
    assert entry.superseded_10yr_billions == (
        superseded_targets_for(policy_id)[-1].official_10yr_billions
    )
    assert entry.target_revision_reason.strip()


@pytest.mark.parametrize("policy_id", sorted(REVISED_POLICY_IDS))
def test_a_revised_row_now_confirms_its_transcription(policy_id, scorecard):
    """A revision resolves a ``line_item_differs``: the carried target *is* the
    published figure now, so the entry must read as a confirmation and must not
    still advertise a gap."""
    entry = next(e for e in scorecard.entries if e.policy_id == policy_id)
    source = source_for(policy_id)
    assert source is not None
    assert entry.provenance == LINE_ITEM
    assert entry.official_10yr_billions_line_item is None
    published = source.published_10yr_billions
    assert published is not None
    gap = abs(published - entry.official_10yr_billions) / abs(published) * 100
    assert gap <= CONFIRMATION_TOLERANCE_PCT


@pytest.mark.parametrize("policy_id", sorted(REVISED_POLICY_IDS))
def test_a_revision_moves_the_figure_by_more_than_rounding(policy_id):
    """A "revision" that restates the old number is noise. Each of these has to
    be a change a reader would care about."""
    live = live_target_for(policy_id)
    old = superseded_targets_for(policy_id)[-1]
    gap = abs(live.official_10yr_billions - old.official_10yr_billions)
    assert gap / max(abs(live.official_10yr_billions), 1e-9) * 100 > (
        CONFIRMATION_TOLERANCE_PCT
    )


def test_the_summary_counts_the_revisions(scorecard):
    """A moved target shrinks the fitted tier, so the count has to be visible
    next to the mean it changes."""
    assert scorecard.revised_target_entries == len(REVISED_POLICY_IDS)


def test_the_two_revisions_are_the_ones_this_pass_made():
    """Pin the ledger's contents. A third revision appearing without a test
    change means a target moved without anyone deciding to move it."""
    assert sorted(REVISED_POLICY_IDS) == [
        "extend_tcja_amt",
        "universal_insulin_cap",
    ]
    assert len(CALIBRATED_TARGETS) == 4
    assert live_target_for("extend_tcja_amt").official_10yr_billions == 1_357.1
    assert superseded_targets_for("extend_tcja_amt")[-1].official_10yr_billions == 450.0
    assert live_target_for("universal_insulin_cap").official_10yr_billions == 11.4
    assert (
        superseded_targets_for("universal_insulin_cap")[-1].official_10yr_billions
        == -15.0
    )


def test_the_app_labels_carry_the_revised_figures():
    """Preset labels embed the official number, so a moved target that leaves
    the label alone would show the app quoting a figure the scorecard no longer
    scores against. The label and its ``preset_ids`` twin must move together."""
    amt_label = "⚖️ AMT: Extend TCJA Relief ($1.36T)"
    insulin_label = "\U0001f48a Universal Insulin Cap ($11B)"
    for label, policy_id in ((amt_label, "extend_tcja_amt"), (insulin_label, "universal_insulin_cap")):
        assert label in CBO_SCORE_MAP, f"{label} missing from CBO_SCORE_MAP"
        assert label in PRESET_POLICIES, f"{label} missing from PRESET_POLICIES"
        assert label in PRESET_ID_BY_LABEL, f"{label} missing from preset_ids"
        assert CBO_SCORE_MAP[label]["official_score"] == pytest.approx(
            live_target_for(policy_id).official_10yr_billions
        )
    # And the superseded spellings are gone, so no share link, status map or
    # validation badge can still resolve the old figure.
    for stale in (
        "⚖️ AMT: Extend TCJA Relief ($450B)",
        "\U0001f48a Universal Insulin Cap (-$15B)",
    ):
        assert stale not in CBO_SCORE_MAP
        assert stale not in PRESET_POLICIES
        assert stale not in PRESET_ID_BY_LABEL


def test_repeal_individual_amt_was_left_alone_with_the_search_recorded():
    """The third target this pass looked at, and the one it could not correct.

    No published score of a post-2025 individual-AMT repeal exists; the only
    published quantity that fits is TPC T25-0049's revenue column, which is the
    file the AMT module's derived path reads. Adopting it would manufacture a
    0% row out of leakage, so the target stays and the search is written down
    instead. This test pins the *absence* of a revision, because "we chose not
    to move it" and "we forgot" look identical in a diff.
    """
    assert not target_was_revised("repeal_individual_amt")
    source = source_for("repeal_individual_amt")
    assert source is not None
    assert "SEARCHED AGAIN 2026-09-02" in source.searched
    assert "T25-0049" in source.searched
