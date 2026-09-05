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
from fiscal_model.preset_ids import PRESET_ID_BY_LABEL, SCORE_ONLY_ID_BY_LABEL
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


#: Every revision the ledger carries, pinned as ``policy_id -> (superseded,
#: live)``. Three are the AMT/insulin and Wave 3 passes; the other twelve are
#: the Wave 4 provenance lane. A ``None`` live figure is a range row, whose
#: bounds are pinned separately below.
_LEDGER: dict[str, tuple[float, float | None]] = {
    # AMT / insulin pass
    "extend_tcja_amt": (450.0, 1_357.1),
    "universal_insulin_cap": (-15.0, 11.4),
    # Wave 3
    "pillar_two_adoption": (-80.0, None),
    # Wave 4 -- the twelve targets the provenance lane moved
    "auto_tariff_25": (-100.0, -386.2),
    "biden_eitc_childless": (178.0, 162.6),
    "biden_full_international": (-700.0, -632.2),
    "biden_gilti_reform": (-280.0, -373.9),
    "eliminate_salt": (-1_200.0, -1_621.0),
    "extend_enhanced_ptc": (350.0, 335.0),
    "fdii_repeal": (-200.0, -158.0),
    "ira_enforcement": (-200.0, -180.4),
    "reciprocal_tariffs": (-1_200.0, None),
    "repeal_ev_credits": (-200.0, -182.3),
    "repeal_salt_cap": (1_100.0, 1_169.0),
    "trump_universal_10": (-2_000.0, -2_171.1),
}

#: The label each revised benchmark is shown under, since a label embeds the
#: official figure and so has to move with it. ``eliminate_salt`` is a
#: score-only entry: it has an official score and a Build id but no preset row.
_REVISED_LABELS: dict[str, str] = {
    "auto_tariff_25": "\U0001f3ed 25% Auto Tariff (-$386B)",
    "biden_eitc_childless": "\U0001f4bc EITC Childless Expansion (Treasury: $163B)",
    "biden_full_international": "\U0001f30d Biden International Package (-$632B)",
    "biden_gilti_reform": "\U0001f30d Biden GILTI Reform (-$374B)",
    "eliminate_salt": "\U0001f4cb Eliminate SALT Deduction (-$1.62T)",
    "extend_enhanced_ptc": "\U0001f3e5 Extend ACA Enhanced PTCs ($335B)",
    "extend_tcja_amt": "⚖️ AMT: Extend TCJA Relief ($1.36T)",
    "fdii_repeal": "\U0001f30d Repeal FDII (-$158B)",
    "ira_enforcement": "\U0001f50d IRA Enforcement Funding (-$180B)",
    "pillar_two_adoption": "\U0001f30d Pillar Two Adoption (-$80B)",
    "reciprocal_tariffs": "\U0001f3ed Reciprocal Tariffs (-$1.5T)",
    "repeal_ev_credits": "\U0001f331 Repeal EV Credits ($182B)",
    "repeal_salt_cap": "\U0001f4cb Repeal SALT Cap ($1.17T)",
    "trump_universal_10": "\U0001f3ed Trump Universal 10% Tariff (-$2.17T)",
    "universal_insulin_cap": "\U0001f48a Universal Insulin Cap ($11B)",
}

#: Score-only entries live in their own id map, so the label test looks for
#: them there rather than in the preset catalog.
_SCORE_ONLY_REVISIONS = frozenset({"eliminate_salt"})

#: The stable id each revised preset resolves to. Written out rather than read
#: back off the catalog, because a test that derives the id from the catalog
#: cannot notice the catalog renaming it.
_STABLE_IDS_FOR_REVISED: dict[str, str] = {
    "auto_tariff_25": "tariff-auto-25pct",
    "biden_eitc_childless": "eitc-childless-expansion",
    "biden_full_international": "international-package",
    "biden_gilti_reform": "gilti-reform",
    "eliminate_salt": "salt-deduction-eliminate",
    "extend_enhanced_ptc": "aca-ptc-extend-enhanced",
    "extend_tcja_amt": "amt-extend-tcja-relief",
    "fdii_repeal": "fdii-repeal",
    "ira_enforcement": "irs-enforcement-ira",
    "pillar_two_adoption": "pillar-two-adoption",
    "reciprocal_tariffs": "tariff-reciprocal",
    "repeal_ev_credits": "ev-credit-repeal",
    "repeal_salt_cap": "salt-cap-repeal",
    "trump_universal_10": "tariff-universal-10pct",
    "universal_insulin_cap": "insulin-cap-universal",
}


def test_the_ledger_holds_exactly_the_revisions_these_passes_made():
    """Pin the ledger's contents. A sixteenth revision appearing without a test
    change means a target moved without anyone deciding to move it."""
    assert sorted(REVISED_POLICY_IDS) == sorted(_LEDGER)
    # Two rows per revision: a superseded one and its live replacement.
    assert len(CALIBRATED_TARGETS) == 2 * len(_LEDGER) == 30

    for policy_id, (superseded, live_point) in sorted(_LEDGER.items()):
        live = live_target_for(policy_id)
        assert superseded_targets_for(policy_id)[-1].official_10yr_billions == (
            pytest.approx(superseded)
        ), policy_id
        if live_point is None:
            assert live.is_range, policy_id
            assert live.official_10yr_billions is None, policy_id
        else:
            assert not live.is_range, policy_id
            assert live.official_10yr_billions == pytest.approx(live_point), policy_id


def test_the_two_range_revisions_state_the_bounds_they_were_read_from():
    """A range is the ledger's strongest claim -- that the agency published no
    single figure -- so both sets of bounds are pinned rather than derived."""
    pillar = live_target_for("pillar_two_adoption")
    assert (
        pillar.published_low_10yr_billions,
        pillar.published_high_10yr_billions,
    ) == (-102.6, 56.5)
    # Wave 4: three modellers scored the same announced reciprocal schedule on
    # the same fiscal window and disagree by 29%, so the target is the spread.
    reciprocal = live_target_for("reciprocal_tariffs")
    assert (
        reciprocal.published_low_10yr_billions,
        reciprocal.published_high_10yr_billions,
    ) == (-1_800.0, -1_400.0)
    # The superseded point was not merely a different magnitude: it was Tax
    # Foundation's *dynamic* score in a column of conventional ones, which is
    # why it falls outside the conventional range entirely.
    assert not reciprocal.contains(-1_200.0)


def test_the_app_labels_carry_the_revised_figures():
    """Preset labels embed the official number, so a moved target that leaves
    the label alone would show the app quoting a figure the scorecard no longer
    scores against. The label and its ``preset_ids`` twin must move together."""
    assert set(_REVISED_LABELS) == set(REVISED_POLICY_IDS)

    for policy_id, label in sorted(_REVISED_LABELS.items()):
        assert label in CBO_SCORE_MAP, f"{label} missing from CBO_SCORE_MAP"
        if policy_id in _SCORE_ONLY_REVISIONS:
            assert label in SCORE_ONLY_ID_BY_LABEL, f"{label} lost its Build id"
        else:
            assert label in PRESET_POLICIES, f"{label} missing from PRESET_POLICIES"
            assert label in PRESET_ID_BY_LABEL, f"{label} missing from preset_ids"

        live = live_target_for(policy_id)
        carried = CBO_SCORE_MAP[label]["official_score"]
        if live.is_range:
            # A range row carries an in-range anchor rather than a transcribed
            # point, so the assertion is containment, not equality.
            assert live.contains(carried), (label, carried)
        else:
            assert carried == pytest.approx(live.official_10yr_billions), label

    # And the superseded spellings are gone, so no share link, status map or
    # validation badge can still resolve the old figure.
    for stale in (
        "⚖️ AMT: Extend TCJA Relief ($450B)",
        "\U0001f48a Universal Insulin Cap (-$15B)",
        "\U0001f3ed 25% Auto Tariff (-$100B)",
        "\U0001f4bc EITC Childless Expansion (CBO: $178B)",
        "\U0001f30d Biden International Package (-$700B)",
        "\U0001f30d Biden GILTI Reform (-$280B)",
        "\U0001f4cb Eliminate SALT Deduction (-$1.2T)",
        "\U0001f3e5 Extend ACA Enhanced PTCs ($350B)",
        "\U0001f30d Repeal FDII (-$200B)",
        "\U0001f50d IRA Enforcement Funding (-$200B)",
        "\U0001f3ed Reciprocal Tariffs (-$1.2T)",
        "\U0001f331 Repeal EV Credits ($200B)",
        "\U0001f4cb Repeal SALT Cap ($1.1T)",
        "\U0001f3ed Trump Universal 10% Tariff (-$2T)",
    ):
        assert stale not in CBO_SCORE_MAP
        assert stale not in PRESET_POLICIES
        assert stale not in PRESET_ID_BY_LABEL
        assert stale not in SCORE_ONLY_ID_BY_LABEL


def test_the_preset_ids_themselves_never_move():
    """The labels moved; the ids they resolve to must not. Share links, the
    Build checklist and every saved package address a preset by id, so a
    provenance pass that renamed an id would break links already in the wild.
    """
    for policy_id, label in sorted(_REVISED_LABELS.items()):
        expected = _STABLE_IDS_FOR_REVISED[policy_id]
        if policy_id in _SCORE_ONLY_REVISIONS:
            assert SCORE_ONLY_ID_BY_LABEL[label] == expected, policy_id
        else:
            assert PRESET_ID_BY_LABEL[label] == expected, policy_id


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


def test_a_range_row_rejects_a_carried_figure_outside_its_bounds():
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
    """A "checked this and decided against" verdict has to be stated, not prose.

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
