"""The illustrative group — H12's demotion of five sectoral presets.

``planning/lanes/HSD_h12_illustrative_group.md``. Owner decision ⑨ moved the
four pharma presets and ``irs-enforcement-double`` off the headline surfaces
into one explicitly-labelled group. The lane is presentational, so the tests
split the same way its falsification section does:

1. **The flag is declared, not derived.** One preset in the group
   (``drug-reform-comprehensive``) has no scorecard row at all, so a rule keyed
   on "the badge is bad" would have exempted the worst case. The declared set
   and the flagged set are pinned equal.
2. **Nothing is removed.** The whole point of a *demotion* is that it is not a
   deletion — "no removing a case to go green" (CLAUDE.md). Every one of the
   five keeps its scorecard row, its badge, its share link and its Build row.
3. **The group is separate, last, and named after the tier it holds**, on both
   surfaces, and no non-demoted preset moves.
4. **The copy says what kind of number these are** — the group note names the
   tier, each row carries a line, and the one with no row says so rather than
   printing nothing.

The AppTest layer is deliberately thin: the routing is pure-function data
(``_preset_category`` and ``build_catalog``), which is where the assertions
belong, and one rendered run is enough to show the demoted presets still reach
the page through a share link.
"""

from __future__ import annotations

import pytest

from fiscal_model.app_data import (
    CBO_SCORE_MAP,
    HEADLINE_SURFACE_ILLUSTRATIVE,
    ILLUSTRATIVE_GROUP_LABEL,
    ILLUSTRATIVE_GROUP_NOTE,
    ILLUSTRATIVE_NO_ROW_NOTE,
    ILLUSTRATIVE_PRESET_IDS,
    PRESET_POLICIES,
    PRESETS_BY_ID,
    is_illustrative,
)
from fiscal_model.preset_ids import (
    CATALOG_PRESET_IDS,
    label_for_preset_id,
    resolve_preset,
)
from fiscal_model.ui.policy_input_presets import (
    _CATEGORY_ORDER,
    ILLUSTRATIVE_CATEGORY,
    _preset_category,
)
from fiscal_model.ui.preset_validation import (
    ILLUSTRATIVE_ROW_NOTE_NO_FIGURE,
    PRESET_ID_TO_SCORECARD_ID,
    illustrative_note,
)
from fiscal_model.ui.tabs.deficit_target import (
    _AREA_ORDER,
    _area_sort_key,
    build_catalog,
)

#: The five, by stable id. Spelled out here rather than imported so that a
#: change to the shipped set has to be made in two places on purpose.
THE_FIVE = frozenset(
    {
        "drug-negotiation-expand",
        "drug-reference-pricing",
        "drug-reform-comprehensive",
        "insulin-cap-universal",
        "irs-enforcement-double",
    }
)

#: The one member with no scorecard row of any tier. It is the reason the flag
#: is declared data: a rule derived from a bad badge would not have caught it.
NO_ROW_ID = "drug-reform-comprehensive"


@pytest.fixture(scope="module")
def catalog():
    return build_catalog(CBO_SCORE_MAP)


# ---------------------------------------------------------------------------
# 1. The flag
# ---------------------------------------------------------------------------


def test_the_declared_set_and_the_flagged_set_are_the_same():
    """Requirement: the membership cannot drift between the two declarations."""
    flagged = {pid for pid, preset in PRESETS_BY_ID.items() if is_illustrative(preset)}
    assert flagged == set(ILLUSTRATIVE_PRESET_IDS) == set(THE_FIVE)


def test_every_flag_carries_the_one_declared_value():
    """A second spelling of "illustrative" would route somewhere by accident."""
    values = {
        preset.get("headline_surface")
        for preset in PRESET_POLICIES.values()
        if preset.get("headline_surface") is not None
    }
    assert values == {HEADLINE_SURFACE_ILLUSTRATIVE}


def test_no_other_preset_is_flagged():
    unflagged = set(CATALOG_PRESET_IDS) - set(THE_FIVE)
    assert not any(is_illustrative(PRESETS_BY_ID[pid]) for pid in unflagged)


def test_the_one_member_with_no_row_really_has_none():
    """Pins the premise of the "declared, not derived" design."""
    assert NO_ROW_ID not in PRESET_ID_TO_SCORECARD_ID
    assert set(THE_FIVE) - {NO_ROW_ID} <= set(PRESET_ID_TO_SCORECARD_ID)


# ---------------------------------------------------------------------------
# 2. Nothing is removed — a demotion is not a deletion
# ---------------------------------------------------------------------------


def test_every_demoted_preset_keeps_its_scorecard_row():
    """CLAUDE.md: "no removing a case to go green"."""
    from fiscal_model.ui.preset_validation import get_validation_badge

    for preset_id in sorted(THE_FIVE - {NO_ROW_ID}):
        badge = get_validation_badge(preset_id)
        assert badge is not None, preset_id
        assert badge["tier"] == "reconstruction", preset_id


def test_every_demoted_preset_still_resolves_from_a_share_link():
    """``?preset=<id>`` must land on the same label it always did."""
    for preset_id in sorted(THE_FIVE):
        label = resolve_preset(preset_id)
        assert label == label_for_preset_id(preset_id)
        assert label in PRESET_POLICIES


def test_the_four_with_an_official_score_are_still_in_builds_catalog(catalog):
    """A demoted row is still checkable, still exportable, still linkable."""
    expected = THE_FIVE - {NO_ROW_ID}
    assert expected <= set(catalog)
    for build_id in sorted(expected):
        assert catalog[build_id].illustrative is True
        assert catalog[build_id].score != 0


def test_build_catalog_insertion_order_follows_the_score_map(catalog):
    """Only the *area* moves.

    ``build_catalog`` iterates ``CBO_SCORE_MAP`` and the exports, the scoreboard
    and the waterfall all read that order, so the demotion must not re-sort it.
    Reconstructed here from the score map rather than from a frozen list, so the
    assertion still means something when a preset is added.
    """
    from fiscal_model.preset_ids import preset_id_for_token
    from fiscal_model.ui.tabs.deficit_target import _SCORE_ONLY_ENTRIES

    expected: list[str] = []
    for label, data in CBO_SCORE_MAP.items():
        if not float(data.get("official_score", 0) or 0):
            continue
        build_id = (
            _SCORE_ONLY_ENTRIES.get(label, {}).get("build_id")
            or preset_id_for_token(label)
        )
        if build_id and build_id not in expected:
            expected.append(build_id)
    assert list(catalog) == expected
    # and the demoted rows sit where they always did, not bunched at the end
    positions = [i for i, build_id in enumerate(catalog) if build_id in THE_FIVE]
    assert max(positions) < len(catalog) - 1


# ---------------------------------------------------------------------------
# 3. The group is separate, last, and holds exactly the five
# ---------------------------------------------------------------------------


def test_explore_puts_the_five_in_the_group_and_nowhere_else():
    by_category: dict[str, list[str]] = {}
    for label, preset in PRESET_POLICIES.items():
        if label == "Custom Policy":
            continue
        by_category.setdefault(_preset_category(preset), []).append(label)

    group = by_category.get(ILLUSTRATIVE_CATEGORY, [])
    assert len(group) == len(THE_FIVE)
    assert {
        pid for pid in CATALOG_PRESET_IDS if label_for_preset_id(pid) in group
    } == set(THE_FIVE)

    for category, labels in by_category.items():
        if category == ILLUSTRATIVE_CATEGORY:
            continue
        ids = {pid for pid in CATALOG_PRESET_IDS if label_for_preset_id(pid) in labels}
        assert not (ids & THE_FIVE), category


def test_the_explore_group_is_last_and_named_after_the_tier():
    assert _CATEGORY_ORDER[-1] == ILLUSTRATIVE_CATEGORY
    assert _CATEGORY_ORDER.count(ILLUSTRATIVE_CATEGORY) == 1
    assert ILLUSTRATIVE_CATEGORY == ILLUSTRATIVE_GROUP_LABEL
    lowered = ILLUSTRATIVE_CATEGORY.lower()
    assert "illustrative" in lowered
    assert "unfitted" in lowered and "reconstruction" in lowered


def test_build_sorts_the_group_last_in_both_directional_sections(catalog):
    assert _AREA_ORDER[-1] == ILLUSTRATIVE_GROUP_LABEL
    rows = list(catalog.values())
    for options in (
        [o for o in rows if o.raises_revenue],
        [o for o in rows if not o.raises_revenue],
    ):
        areas: dict[str, list[str]] = {}
        for option in options:
            areas.setdefault(option.area, []).append(option.build_id)
        ordered = sorted(areas, key=_area_sort_key)
        assert ordered[-1] == ILLUSTRATIVE_GROUP_LABEL
        assert set(areas[ILLUSTRATIVE_GROUP_LABEL]) <= set(THE_FIVE)


def test_no_demoted_row_appears_in_a_substantive_build_area(catalog):
    for option in catalog.values():
        if option.build_id in THE_FIVE:
            assert option.area == ILLUSTRATIVE_GROUP_LABEL, option.build_id
        else:
            assert option.area != ILLUSTRATIVE_GROUP_LABEL, option.build_id


def test_every_other_preset_keeps_its_area(catalog):
    """The areas the demotion is allowed to touch are exactly two.

    ``Drug pricing`` empties (both of its Build rows were demoted) and
    ``IRS enforcement`` loses one of two. Nothing else may move, and nothing
    else may appear.
    """
    survivors = {
        option.build_id: option.area
        for option in catalog.values()
        if option.build_id not in THE_FIVE
    }
    assert "Drug pricing" not in set(survivors.values())
    assert survivors["irs-enforcement-ira"] == "IRS enforcement"
    # a spot-check across the untouched areas, by id so a label rename is free
    assert survivors["tcja-full-extension"] == "TCJA / Individual"
    assert survivors["ss-donut-250k"] == "Payroll / Social Security"
    assert survivors["tariff-universal-10pct"] == "Trade / tariffs"
    assert survivors["aca-ptc-repeal"] == "Healthcare"


# ---------------------------------------------------------------------------
# 4. The copy names the tier, and the error
# ---------------------------------------------------------------------------


def test_the_group_note_names_the_tier_and_says_it_is_not_a_score():
    lowered = ILLUSTRATIVE_GROUP_NOTE.lower()
    assert "illustrative" in lowered
    assert "unfitted reconstruction" in lowered
    assert "not validated scores" in lowered
    assert "no constant in the model is fitted" in lowered


def test_the_explore_row_note_carries_the_tier_and_the_live_error():
    """Requirement: the figure is read from the badge, never hard-coded."""
    from fiscal_model.ui.preset_validation import get_validation_badge

    for preset_id in sorted(THE_FIVE - {NO_ROW_ID}):
        badge = get_validation_badge(preset_id)
        note = illustrative_note(preset_id)
        assert note.lower().startswith("↳ illustrative")
        assert "unfitted reconstruction" in note.lower()
        assert f"{badge['abs_pct']:.1f}%" in note
        assert "not a validated score" in note.lower()


def test_the_member_with_no_row_says_so_rather_than_printing_nothing():
    note = illustrative_note(NO_ROW_ID)
    assert "illustrative" in note.lower()
    assert ILLUSTRATIVE_NO_ROW_NOTE in note


def test_the_cheap_variant_names_the_tier_and_touches_no_scorecard():
    """Build's row note must not force a 6-second scorecard materialisation."""
    from fiscal_model.ui import preset_validation

    preset_validation.reset_scorecard_cache()
    note = illustrative_note("drug-reference-pricing", with_figure=False)
    assert note == ILLUSTRATIVE_ROW_NOTE_NO_FIGURE
    assert "illustrative" in note.lower()
    assert "unfitted reconstruction" in note.lower()
    assert "not a validated score" in note.lower()
    # nothing was computed: the lru_cache is still empty
    assert preset_validation._scorecard_index.cache_info().currsize == 0


def test_each_demoted_preset_says_illustrative_in_its_own_description():
    for preset_id in sorted(THE_FIVE):
        description = PRESETS_BY_ID[preset_id]["description"]
        assert "**Illustrative**" in description, preset_id


def test_a_package_containing_a_demoted_preset_says_so():
    from fiscal_model.ui.policy_packages import PRESET_POLICY_PACKAGES

    demoted_labels = {label_for_preset_id(pid) for pid in THE_FIVE}
    for name, package in PRESET_POLICY_PACKAGES.items():
        members = set(package.get("policies") or ())
        if members & demoted_labels:
            assert "illustrative" in package["description"].lower(), name


# ---------------------------------------------------------------------------
# 5. Through the real app — a demoted preset is still reachable and still scores
# ---------------------------------------------------------------------------


def _state(at, key, default=None):
    """``session_state`` has no ``.get``, and a missing key raises."""
    try:
        return at.session_state[key]
    except Exception:
        return default


def _explore(params: dict[str, str]):
    """Boot the real router and land on ``/explore`` with ``params`` applied."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=300)
    at.query_params = dict(params)
    at.run()
    at.switch_page("app_pages/explore.py")
    at.query_params = dict(params)
    at.run()
    return at


@pytest.mark.parametrize(
    "preset_id",
    ["drug-negotiation-expand", "drug-reform-comprehensive", "irs-enforcement-double"],
)
def test_a_share_link_still_scores_a_demoted_preset(preset_id):
    """Falsification: a demoted preset must never become unreachable.

    One per group member class — a pharma row with a scorecard row, the pharma
    row with none, and the enforcement row — rather than all five, because each
    run boots the whole dependency graph.
    """
    from components.results import SCORED_RESULT_KEY

    at = _explore({"preset": preset_id, "dynamic": "0", "run": "1"})

    assert not at.exception, at.exception
    assert _state(at, SCORED_RESULT_KEY) is not None, f"{preset_id} did not score"
    assert _state(at, "sidebar_policy_area") == ILLUSTRATIVE_CATEGORY


def test_a_frozen_assignment_link_still_scores_a_demoted_preset():
    """A frozen link naming a demoted preset must score, not refuse."""
    from components.results import SCORED_RESULT_KEY
    from fiscal_model.ui.frozen_links import baseline_vintage_token

    params = {
        "preset": "drug-reference-pricing",
        "dynamic": "0",
        "run": "1",
        "baseline": baseline_vintage_token(),
        "engine": "frbus_lite",
        "spec": "0123456789ab",
        "mode": "conventional",
        "frozen": "1",
    }
    at = _explore(params)

    assert not at.exception, at.exception
    assert _state(at, SCORED_RESULT_KEY) is not None
