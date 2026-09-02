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
    EXAMINED_NOT_REVISED,
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


#: Revisions that moved the target to another *point*, and revisions that
#: replaced a point with a published *range*. The two make different claims, so
#: they are held to different — but equally strict — assertions below.
_POINT_REVISIONS = sorted(
    p for p in REVISED_POLICY_IDS if not live_target_for(p).is_range
)
_RANGE_REVISIONS = sorted(
    p for p in REVISED_POLICY_IDS if live_target_for(p).is_range
)


@pytest.mark.parametrize("policy_id", _POINT_REVISIONS)
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


@pytest.mark.parametrize("policy_id", _RANGE_REVISIONS)
def test_a_range_revision_publishes_its_bounds_and_keeps_the_gap_visible(
    policy_id, scorecard
):
    """A range revision makes the opposite claim to a point revision.

    It says the agency published no single figure, so the point the registries
    carry is an editorial midpoint that stays where it is. The transcription
    must therefore still read ``line_item_differs`` and still advertise the
    published figure it found — hiding that would leave the carried midpoint
    looking sourced — while the entry exposes the bounds and where the model
    falls relative to them.
    """
    entry = next(e for e in scorecard.entries if e.policy_id == policy_id)
    live = live_target_for(policy_id)

    assert entry.published_range_low_billions == live.published_low_10yr_billions
    assert entry.published_range_high_billions == live.published_high_10yr_billions
    assert entry.within_published_range is not None
    assert entry.distance_to_published_range_billions is not None
    # The carried point must be inside what was published, or the ledger is
    # asserting a range the scorecard contradicts.
    assert live.contains(entry.official_10yr_billions)
    assert entry.official_10yr_billions_line_item is not None
    assert entry.provenance != LINE_ITEM


@pytest.mark.parametrize("policy_id", _POINT_REVISIONS)
def test_a_revision_moves_the_figure_by_more_than_rounding(policy_id):
    """A "revision" that restates the old number is noise. Each of these has to
    be a change a reader would care about."""
    live = live_target_for(policy_id)
    old = superseded_targets_for(policy_id)[-1]
    gap = abs(live.official_10yr_billions - old.official_10yr_billions)
    assert gap / max(abs(live.official_10yr_billions), 1e-9) * 100 > (
        CONFIRMATION_TOLERANCE_PCT
    )


@pytest.mark.parametrize("policy_id", _RANGE_REVISIONS)
def test_a_range_revision_replaces_a_point_that_was_not_a_bound(policy_id):
    """The range has to be news too: a point that already sat on a bound would
    make the revision a relabelling rather than a correction."""
    live = live_target_for(policy_id)
    old = superseded_targets_for(policy_id)[-1]
    assert not old.is_range
    assert old.official_10yr_billions is not None
    assert old.official_10yr_billions != live.published_low_10yr_billions
    assert old.official_10yr_billions != live.published_high_10yr_billions


def test_the_summary_counts_the_revisions(scorecard):
    """A moved target shrinks the fitted tier, so the count has to be visible
    next to the mean it changes."""
    assert scorecard.revised_target_entries == len(REVISED_POLICY_IDS)


def test_the_three_revisions_are_the_ones_these_passes_made():
    """Pin the ledger's contents. A fourth revision appearing without a test
    change means a target moved without anyone deciding to move it."""
    assert sorted(REVISED_POLICY_IDS) == [
        "extend_tcja_amt",
        "pillar_two_adoption",
        "universal_insulin_cap",
    ]
    assert len(CALIBRATED_TARGETS) == 6
    pillar = live_target_for("pillar_two_adoption")
    assert pillar.is_range
    assert pillar.official_10yr_billions is None
    assert (pillar.published_low_10yr_billions, pillar.published_high_10yr_billions) == (
        -102.6,
        56.5,
    )
    assert superseded_targets_for("pillar_two_adoption")[-1].official_10yr_billions == (
        -80.0
    )
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


def test_a_range_row_rejects_a_carried_figure_outside_its_bounds(monkeypatch):
    """The containment check is the range row's version of "the ledger and the
    registry must agree", and it has to actually fail when they do not."""
    from fiscal_model.validation import target_revisions as tr

    live = live_target_for("pillar_two_adoption")
    outside = live.published_low_10yr_billions - 10.0
    entry = dataclasses.replace(
        next(
            e
            for e in cached_default_scorecard().entries
            if e.policy_id == "pillar_two_adoption"
        ),
        official_10yr_billions=outside,
    )
    problems = tr.target_revision_problems([entry])
    assert any("outside the published range" in p for p in problems)


def test_a_half_stated_range_is_rejected(monkeypatch):
    """One bound says nothing. A row that states a low without a high is a
    typo, not a range, and must not pass as one."""
    from fiscal_model.validation import target_revisions as tr

    broken = dataclasses.replace(
        live_target_for("pillar_two_adoption"), published_high_10yr_billions=None
    )
    monkeypatch.setattr(
        tr,
        "CALIBRATED_TARGETS",
        tuple(
            broken if t.revision_id == broken.revision_id else t
            for t in CALIBRATED_TARGETS
        ),
    )
    problems = tr.target_revision_problems()
    assert any("needs both bounds" in p for p in problems)


def test_the_estate_target_is_recorded_as_examined_and_not_moved():
    """"Somebody checked this and decided against" has to be state, not prose.

    Without the registry, a benchmark whose published figure disagrees with the
    carried one is indistinguishable from one nobody has opened, and the
    question gets re-opened every pass. The estate row is the case: JCT's
    $429.6B scores a ten-section bill whose other eight sections `estate.py`
    does not construct, so the figure is an upper bound on a superset and
    adopting it as a point target would measure the missing sections.
    """
    assert "biden_estate_reform" in EXAMINED_NOT_REVISED
    reason = EXAMINED_NOT_REVISED["biden_estate_reform"]
    assert "429.6" in reason
    assert "ten-section" in reason
    # Examined-and-left is the opposite of revised, and the ledger says so.
    assert not target_was_revised("biden_estate_reform")
    source = source_for("biden_estate_reform")
    assert source is not None
    assert source.published_10yr_billions == pytest.approx(-429.6)


def test_examined_and_revised_are_mutually_exclusive(monkeypatch):
    """A target is either moved or left. Claiming both hides which happened."""
    from fiscal_model.validation import target_revisions as tr

    monkeypatch.setattr(
        tr,
        "EXAMINED_NOT_REVISED",
        {**EXAMINED_NOT_REVISED, "pillar_two_adoption": "contradiction"},
    )
    problems = tr.target_revision_problems()
    assert any("examined-and-left AND carries a ledger row" in p for p in problems)
