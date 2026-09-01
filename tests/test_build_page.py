"""Tests for the Build page (Phase 3 of the ask-first redesign).

Two layers:

* **Pure** — the share codec, the overlap reconciler and the export builders are
  ordinary functions and are tested as such (fast, and they are what Phase 3b
  will call).
* **Rendered** — ``streamlit.testing.v1.AppTest`` drives the real router, so the
  guardrails are asserted on the widgets Streamlit actually emits rather than on
  a hand-rolled ``st_module`` fake. ``AppTest.switch_page`` selects a
  ``st.navigation`` page by the md5 of its name, and ``StreamlitPage``'s script
  hash is the md5 of its ``url_path`` — so passing ``app_pages/build.py``
  resolves to the page registered with ``url_path="build"``.

Each rendered run boots the whole dependency graph (~10s), so the fixtures are
module-scoped and every assertion group reuses one.
"""

from __future__ import annotations

import os

import pytest

from fiscal_model.ui.share_links import (
    BUILD_METRIC_PCT_GDP,
    BUILD_METRIC_USD_B,
    decode_build_share,
    encode_build_share,
)
from fiscal_model.ui.tabs.deficit_target import (
    DroppedSelection,
    apply_preselection,
    build_catalog,
    build_package_csv,
    export_header_lines,
    resolve_selection,
    selection_blockers,
    short_vintage,
    window_label,
)

SS_GROUP = ("ss-cap-90pct", "ss-donut-250k", "ss-cap-eliminate")


@pytest.fixture(scope="module")
def catalog():
    from fiscal_model.app_data import CBO_SCORE_MAP

    return build_catalog(CBO_SCORE_MAP)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


def test_catalog_covers_the_whole_scored_score_map(catalog):
    from fiscal_model.app_data import CBO_SCORE_MAP

    scored = [k for k, v in CBO_SCORE_MAP.items() if v.get("official_score", 0)]
    assert len(catalog) == len(scored), "every scored policy must be checkable"
    assert len(catalog) >= 45, "the wireframe promises '45+ scored policies'"


def test_every_option_has_a_stable_id_and_an_area(catalog):
    for build_id, option in catalog.items():
        assert build_id == option.build_id
        assert build_id and " " not in build_id
        assert option.area and option.area != ""


def test_ss_cap_options_share_one_exclusive_group(catalog):
    groups = [set(catalog[pid].exclusive_groups) for pid in SS_GROUP]
    assert all("ss-wage-cap" in group for group in groups)


# ---------------------------------------------------------------------------
# Overlap reconciliation
# ---------------------------------------------------------------------------


def test_resolve_selection_keeps_the_first_member_of_a_group(catalog):
    kept, dropped = resolve_selection(SS_GROUP, catalog)
    assert kept == ["ss-cap-90pct"]
    assert [d.dropped_id for d in dropped] == ["ss-donut-250k", "ss-cap-eliminate"]
    assert all(d.reason == "exclusive" and d.kept_id == "ss-cap-90pct" for d in dropped)


def test_resolve_selection_order_decides_the_survivor(catalog):
    kept, _ = resolve_selection(["ss-donut-250k", "ss-cap-90pct"], catalog)
    assert kept == ["ss-donut-250k"]


def test_resolve_selection_lets_a_bundle_evict_its_components(catalog):
    # Either order: the bundle wins, because that is what the checklist shows.
    for order in (
        ["tcja-full-extension", "ctc-extension"],
        ["ctc-extension", "tcja-full-extension"],
    ):
        kept, dropped = resolve_selection(order, catalog)
        assert kept == ["tcja-full-extension"]
        assert [(d.dropped_id, d.reason) for d in dropped] == [
            ("ctc-extension", "subsumed")
        ]


def test_resolve_selection_leaves_independent_policies_alone(catalog):
    picks = ["ss-donut-250k", "corporate-28pct", "irs-enforcement-ira"]
    kept, dropped = resolve_selection(picks, catalog)
    assert kept == picks
    assert dropped == []


def test_resolve_selection_drops_unknown_and_duplicate_ids(catalog):
    kept, dropped = resolve_selection(
        ["ss-donut-250k", "ss-donut-250k", "not-a-policy"], catalog
    )
    assert kept == ["ss-donut-250k"]
    assert dropped == []


def test_selection_blockers_dim_siblings_but_never_the_selection(catalog):
    blockers = selection_blockers(["ss-donut-250k"], catalog)
    assert "ss-donut-250k" not in blockers
    assert blockers["ss-cap-90pct"] == ("exclusive:ss-wage-cap", "ss-donut-250k")
    assert blockers["ss-cap-eliminate"] == ("exclusive:ss-wage-cap", "ss-donut-250k")
    assert "corporate-28pct" not in blockers


def test_selection_blockers_mark_subsumed_components(catalog):
    blockers = selection_blockers(["tcja-full-extension"], catalog)
    assert blockers["ctc-extension"] == ("subsumed", "tcja-full-extension")


def test_dropped_selection_messages_name_both_policies(catalog):
    exclusive = DroppedSelection(
        "ss-donut-250k", "ss-cap-90pct", "exclusive", "ss-wage-cap"
    )
    assert "cap option" in exclusive.message(catalog)
    subsumed = DroppedSelection("ctc-extension", "tcja-full-extension", "subsumed")
    assert "already included in" in subsumed.message(catalog)


# ---------------------------------------------------------------------------
# Share codec
# ---------------------------------------------------------------------------


def test_encode_build_share_uses_the_documented_url_shape():
    url = encode_build_share(["ss-donut-250k", "corporate-28pct"], 3.0)
    assert url.endswith(
        "/build?policies=ss-donut-250k,corporate-28pct&target=3.0&metric=pct_gdp"
    )


def test_encode_build_share_dedupes_and_keeps_order():
    url = encode_build_share(["b", "a", "b", "", "c"], 1.5)
    assert "policies=b,a,c" in url


def test_encode_build_share_formats_a_dollar_target_as_an_integer():
    url = encode_build_share(["ss-donut-250k"], 1200.0, BUILD_METRIC_USD_B)
    assert "target=1200&metric=usd_b" in url


def test_build_share_round_trips():
    ids = ["ss-donut-250k", "corporate-28pct", "tariff-universal-10pct"]
    url = encode_build_share(ids, 2.5)
    query = dict(
        pair.split("=", 1) for pair in url.split("?", 1)[1].split("&")
    )
    decoded = decode_build_share(query)
    assert decoded == {
        "preset_ids": ids,
        "target": 2.5,
        "metric": BUILD_METRIC_PCT_GDP,
    }


def test_decode_build_share_resolves_legacy_labels():
    decoded = decode_build_share(
        {"policies": "💰 SS Donut Hole $250K (-$2.7T),Biden 2025 Proposal"}
    )
    assert decoded["preset_ids"] == ["ss-donut-250k", "top-rate-39-6"]


def test_decode_build_share_tolerates_junk_and_missing_params():
    decoded = decode_build_share({"policies": " , ", "target": "not-a-number"})
    assert decoded == {"preset_ids": [], "target": None, "metric": "pct_gdp"}


def test_decode_build_share_keeps_unresolvable_tokens_for_the_page():
    # The four score-map-only Build options have no preset_ids registry slug.
    decoded = decode_build_share({"policies": "mortgage-deduction-eliminate"})
    assert decoded["preset_ids"] == ["mortgage-deduction-eliminate"]


def test_decode_build_share_accepts_metric_aliases():
    assert decode_build_share({"metric": "dollars"})["metric"] == BUILD_METRIC_USD_B
    assert decode_build_share({"metric": "GDP"})["metric"] == BUILD_METRIC_PCT_GDP


def test_existing_preset_share_helpers_are_untouched():
    """Phase 5 owns the preset codec; Phase 3 only added functions."""
    from fiscal_model.ui import share_links

    assert hasattr(share_links, "apply_share_query_params")
    assert hasattr(share_links, "build_share_url")


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


def test_export_header_carries_provenance():
    lines = export_header_lines(
        vintage_label="Feb 2026",
        window_label="FY2025–2034",
        selection=["ss-donut-250k"],
        target_label="3.0% of GDP",
    )
    joined = "\n".join(lines)
    assert "# Baseline: CBO Feb 2026" in joined
    assert "# Window: FY2025–2034" in joined
    assert "+ increases the deficit" in joined
    assert "# Policy ids: ss-donut-250k" in joined


def test_csv_header_contains_the_baseline_vintage(catalog):
    csv_text = build_package_csv(
        ["ss-donut-250k", "corporate-28pct"],
        catalog,
        10,
        vintage_label="Feb 2026",
        window_label="FY2025–2034",
        target_label="3.0% of GDP",
    )
    header, _, table = csv_text.partition("Policy ID,")
    assert "Feb 2026" in header
    assert "ss-donut-250k,corporate-28pct" in header
    assert "ss-donut-250k" in table and "-2,700" in table


def test_short_vintage_and_window_label_are_derived_not_hardcoded():
    assert short_vintage("February 2026") == "Feb 2026"
    assert short_vintage(None) == "unknown vintage"
    assert window_label([2025, 2026, 2034]) == "FY2025–2034"
    assert window_label([]) == "unknown window"


# ---------------------------------------------------------------------------
# apply_preselection — the Phase 3b entry point
# ---------------------------------------------------------------------------


class _FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover - attribute protocol
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _FakeStreamlit:
    def __init__(self):
        self.session_state = _FakeSessionState()


def test_apply_preselection_loads_a_package_into_the_checklist():
    fake = _FakeStreamlit()
    applied = apply_preselection(["ss-donut-250k", "corporate-28pct"], st_module=fake)
    assert applied == ["ss-donut-250k", "corporate-28pct"]
    assert fake.session_state["build_selection"] == applied
    assert fake.session_state["dt_ss-donut-250k"] is True
    assert fake.session_state["dt_ss-cap-90pct"] is False


def test_apply_preselection_runs_the_conflict_dropping_logic():
    fake = _FakeStreamlit()
    applied = apply_preselection(list(SS_GROUP), st_module=fake)
    assert applied == ["ss-cap-90pct"]
    notice = fake.session_state["_build_dropped_notice"]
    assert [d.dropped_id for d in notice] == ["ss-donut-250k", "ss-cap-eliminate"]


def test_apply_preselection_accepts_labels_and_flags_unknown_ids():
    fake = _FakeStreamlit()
    applied = apply_preselection(
        ["💰 SS Donut Hole $250K (-$2.7T)", "no-such-policy"], st_module=fake
    )
    assert applied == ["ss-donut-250k"]
    assert any(
        "no-such-policy" in str(item)
        for item in fake.session_state["_build_dropped_notice"]
    )


# ---------------------------------------------------------------------------
# Rendered page (AppTest through the real router)
# ---------------------------------------------------------------------------


def _run_build(query_params=None, session_state=None, timeout=300):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=timeout)
    at.switch_page("app_pages/build.py")
    for key, value in (query_params or {}).items():
        at.query_params[key] = value
    for key, value in (session_state or {}).items():
        at.session_state[key] = value
    at.run()
    return at


def _checkbox_state(at):
    return {
        box.key: (box.value, box.disabled)
        for box in at.checkbox
        if box.key and box.key.startswith("dt_")
    }


@pytest.fixture(scope="module")
def plain_build():
    return _run_build()


@pytest.fixture(scope="module")
def checked_build():
    """A fresh page with the SS donut-hole option ticked by hand.

    Deliberately not derived from ``plain_build``: ``AppTest.run`` mutates the
    instance in place, so sharing one would retro-actively change what the
    "nothing selected" assertions see.
    """
    at = _run_build()
    at.checkbox(key="dt_ss-donut-250k").check().run()
    return at


@pytest.fixture(scope="module")
def shared_build():
    ids = ["ss-donut-250k", "corporate-28pct"]
    url = encode_build_share(ids, 4.0)
    query = dict(pair.split("=", 1) for pair in url.split("?", 1)[1].split("&"))
    return _run_build(query_params=query)


@pytest.fixture(scope="module")
def conflicted_build():
    return _run_build(
        query_params={"policies": "ss-cap-90pct,ss-donut-250k", "target": "3.0"}
    )


def test_build_page_renders_without_error(plain_build):
    assert not plain_build.exception


def test_build_page_lists_the_whole_catalog(plain_build, catalog):
    assert len(_checkbox_state(plain_build)) == len(catalog)


def test_checking_an_option_disables_its_exclusive_siblings(checked_build):
    state = _checkbox_state(checked_build)
    assert state["dt_ss-donut-250k"] == (True, False)
    assert state["dt_ss-cap-90pct"] == (False, True)
    assert state["dt_ss-cap-eliminate"] == (False, True)
    # A policy from another group is untouched.
    assert state["dt_corporate-28pct"] == (False, False)


def test_totals_update_when_a_policy_is_checked(plain_build, checked_build):
    def package_metric(at):
        return next(m for m in at.metric if m.label.startswith("Your package"))

    before = package_metric(plain_build)
    after = package_metric(checked_build)
    assert "0 policies" in before.label and before.value == "$0B/yr"
    assert "1 policy" in after.label
    assert after.value == "$-270B/yr"
    assert "-2,700B over 10 years" in after.delta


def test_scoreboard_reports_baseline_and_adjusted_deficit(checked_build):
    labels = [m.label for m in checked_build.metric]
    assert "Baseline deficit" in labels
    assert "Adjusted deficit" in labels
    assert any(label.startswith(("Remaining gap to", "Gap to")) for label in labels)


def test_pick_one_chip_is_rendered_for_exclusive_groups(plain_build):
    chips = [m.value for m in plain_build.markdown if "PICK ONE" in m.value]
    assert any("CAP OPTION" in chip for chip in chips)


def test_waterfall_caption_states_the_per_year_conversion(checked_build):
    captions = [c.value for c in checked_build.caption]
    assert any("÷ 10" in caption for caption in captions), captions


def test_footer_sentence_carries_the_live_baseline_vintage(plain_build):
    footer = next(
        c.value for c in plain_build.caption if c.value.startswith("Scored against CBO")
    )
    assert "list prices, no interaction effects" in footer
    assert "overlapping options are mutually exclusive" in footer
    assert "unknown vintage" not in footer


def test_sign_convention_is_stated_once(plain_build):
    statements = [
        m.value for m in plain_build.markdown if "Sign convention" in m.value
    ]
    assert len(statements) == 1
    assert "increases the deficit" in statements[0]


def test_share_link_round_trips_into_selection_and_target(shared_build):
    state = _checkbox_state(shared_build)
    assert state["dt_ss-donut-250k"][0] is True
    assert state["dt_corporate-28pct"][0] is True
    assert shared_build.session_state["build_selection"] == [
        "ss-donut-250k",
        "corporate-28pct",
    ]
    target = next(
        s for s in shared_build.slider if s.label.startswith("Target deficit")
    )
    assert target.value == 4.0


def test_conflicting_share_link_drops_the_later_member_with_a_notice(conflicted_build):
    state = _checkbox_state(conflicted_build)
    assert state["dt_ss-cap-90pct"] == (True, False)
    assert state["dt_ss-donut-250k"] == (False, True)

    notices = [info.value for info in conflicted_build.info]
    assert any("overlap" in text for text in notices), notices
    assert any("SS Donut Hole" in text for text in notices)


def test_search_box_filters_the_checklist():
    at = _run_build(session_state={"build_search": "tariff"})
    keys = set(_checkbox_state(at))
    assert keys, "the filter should still show the tariff options"
    assert all("tariff" in key for key in keys)


# ---------------------------------------------------------------------------
# "Start from your values" — the Phase-3b panel, through the real router
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def values_build(monkeypatch_module_env):
    """Build with no API key: the archetype path, end to end and offline."""
    return _run_build()


@pytest.fixture(scope="module")
def monkeypatch_module_env():
    """Guarantee the offline path for the module-scoped values fixtures."""
    previous = os.environ.pop("ANTHROPIC_API_KEY", None)
    yield
    if previous is not None:
        os.environ["ANTHROPIC_API_KEY"] = previous


def test_build_opens_on_the_values_panel(values_build):
    """§5b.5: Build's default door is values, not the checklist."""
    assert not values_build.exception
    assert values_build.session_state["build_mode"] == "Start from your values"
    from fiscal_model.composer.archetypes import load_archetypes

    text = [element.value for element in values_build.markdown] + [
        element.value for element in values_build.caption
    ]
    for archetype in load_archetypes().values():
        assert any(archetype.name in item for item in text), archetype.name
    # One surface: the checklist is still on screen underneath the panel.
    assert _checkbox_state(values_build)


def test_values_panel_works_with_no_api_key(values_build):
    """Cards → package → coverage, with the free-text box absent."""
    captions = [element.value for element in values_build.caption]
    assert any("ANTHROPIC_API_KEY" in caption for caption in captions)
    assert not [
        area
        for area in values_build.text_area
        if area.key == "values_text"
    ], "the free-text box must be hidden without a key"

    markdowns = [element.value for element in values_build.markdown]
    assert any("of target" in item for item in markdowns)
    assert any("starting point, not a verdict" in item for item in captions)


def test_values_panel_renders_every_dial_and_the_protected_control(values_build):
    from fiscal_model.ui.session_state import VALUES_DIMENSION_KEYS

    slider_keys = {slider.key for slider in values_build.slider}
    assert set(VALUES_DIMENSION_KEYS.values()) <= slider_keys
    assert "values_target_pct" in slider_keys
    assert any(box.key == "values_protected" for box in values_build.multiselect)


def test_archetype_card_loads_its_package_into_the_checklist(monkeypatch_module_env):
    """The full offline journey the plan asks for: card → package → checklist."""
    at = _run_build()
    at.button(key="values_card_egalitarian").click().run()

    from fiscal_model.composer.archetypes import get_archetype

    expected = get_archetype("egalitarian").vector
    assert at.session_state["values_archetype"] == "egalitarian"
    assert at.session_state["values_redistribution"] == pytest.approx(
        expected.redistribution
    )

    at.button(key="values_load").click().run()

    assert at.session_state["build_mode"] == "Start from scratch"
    selection = at.session_state["build_selection"]
    assert len(selection) >= 4
    state = _checkbox_state(at)
    for build_id in selection:
        assert state[f"dt_{build_id}"][0] is True


def test_values_link_round_trips_through_the_router(monkeypatch_module_env):
    """``?values=egalitarian`` restores the panel (§5b.8)."""
    at = _run_build(query_params={"values": "egalitarian"})

    assert not at.exception
    assert at.session_state["values_archetype"] == "egalitarian"
    assert at.session_state["build_mode"] == "Start from your values"
    from fiscal_model.composer.archetypes import get_archetype

    expected = get_archetype("egalitarian").vector
    assert at.session_state["values_target_pct"] == pytest.approx(
        expected.target_pct_gdp
    )
    assert set(at.session_state["values_protected"]) == set(expected.protected)


def test_values_link_with_load_lands_in_the_checklist(monkeypatch_module_env):
    at = _run_build(query_params={"values": "egalitarian", "load": "1"})

    assert not at.exception
    assert at.session_state["build_mode"] == "Start from scratch"
    assert len(at.session_state["build_selection"]) >= 4


def test_a_policies_link_still_opens_the_checklist(shared_build):
    """A link that names policies wants the checklist, not the panel."""
    assert shared_build.session_state["build_mode"] == "Start from scratch"
