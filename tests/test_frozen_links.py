"""Frozen assignment links — the classroom deep link (FOLLOWUPS, classroom item).

The promise a frozen link makes is narrow and testable: *everyone who opens it
scores the same numbers*. Three things have to hold for that, and each is a
layer here.

1. **The codec is exact.** ``frozen=1`` plus the provenance stamps decode to
   one lock, and encoding that lock reproduces the same URL — pinned without a
   Streamlit runtime, the way ``share_links.rewrite_legacy_query`` is.
2. **A link this deployment cannot honour is refused, not approximated.** The
   baseline vintage is a property of the deployment, so a link naming another
   one cannot be restored; the page must say so and score nothing rather than
   hand a student numbers off the wrong baseline.
3. **The lock is visible and enforced in the real app.** Run through the actual
   router with ``AppTest``: the policy inputs and the model settings render
   disabled, the label and the provenance line are on the page, and an
   ordinary (non-frozen) link is untouched.

Build is the same three layers over a *package* rather than a single score
(final section). One extra thing has to hold there and is pinned explicitly:
freezing must change what can be **touched** and never what is **counted**, so
a frozen package and an open one are compared metric by metric and bar by bar.

The AppTest fixtures are module-scoped: each one is a full script run of
``app.py`` including a scoring pass, which is seconds, not milliseconds.
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

import pytest
from streamlit.testing.v1 import AppTest

from components.results import SCORED_RESULT_KEY
from fiscal_model.ui.frozen_links import (
    FROZEN_LABEL,
    FROZEN_REFUSAL_HEADING,
    FrozenAssignment,
    FrozenBuildPackage,
    build_assignment_url,
    build_package_assignment_url,
    build_package_spec_hash,
    decode_frozen_assignment,
    decode_frozen_build,
    engine_token,
    freeze_url,
    frozen_build_refusal,
    frozen_build_unresolved_refusal,
    frozen_refusal,
    is_classroom_request,
)
from fiscal_model.ui.share_links import baseline_vintage_token, rewrite_legacy_query

# The app logs a running commentary of every baseline load; quiet for tests.
logging.getLogger("fiscal_model").setLevel(logging.WARNING)

EXPLORE = "app_pages/explore.py"
TAILOR = "app_pages/tailor.py"
TCJA_ID = "tcja-full-extension"
TCJA_LABEL = "🏛️ TCJA Full Extension (CBO: $4.6T)"

#: The vintage this deployment actually serves, e.g. ``february2026``. Read
#: rather than hard-coded: the point of the refusal is that it tracks the
#: deployment, so a test that hard-codes the token would stop testing it the
#: next time the baseline is refreshed.
LIVE_BASELINE = baseline_vintage_token()


def _frozen_params(**overrides: str) -> dict[str, str]:
    """A frozen ``/explore`` link for the TCJA preset."""
    params = {
        "preset": TCJA_ID,
        "dynamic": "0",
        "run": "1",
        "baseline": LIVE_BASELINE,
        "engine": "frbus_lite",
        "spec": "0123456789ab",
        "mode": "conventional",
        "frozen": "1",
    }
    params.update(overrides)
    return {key: value for key, value in params.items() if value is not None}


# ---------------------------------------------------------------------------
# Layer 1 — the codec, without a runtime
# ---------------------------------------------------------------------------


def test_an_ordinary_share_link_carries_no_lock():
    """Requirement: a non-frozen link is unchanged. It decodes to nothing."""
    assert decode_frozen_assignment({}) is None
    assert (
        decode_frozen_assignment(
            {"preset": TCJA_ID, "baseline": LIVE_BASELINE, "spec": "abc", "mode": "conventional"}
        )
        is None
    )
    # ...and a flag that reads false is not a lock either.
    assert decode_frozen_assignment({"frozen": "0", "baseline": LIVE_BASELINE}) is None


def test_decode_reads_the_whole_lock():
    frozen = decode_frozen_assignment(_frozen_params(dynamic="1", mode="dynamic"))

    assert frozen == FrozenAssignment(
        baseline=LIVE_BASELINE,
        engine="frbus_lite",
        dynamic=True,
        spec="0123456789ab",
        mode="dynamic",
    )
    assert frozen.engine_label == "FRB/US-Lite (recommended)"
    assert frozen.mode_label == "dynamic"


def test_decode_accepts_the_list_shaped_params_urlparse_produces():
    """``st.query_params`` yields strings; ``parse_qs`` yields lists of them."""
    listed = {key: [value] for key, value in _frozen_params().items()}
    assert decode_frozen_assignment(listed) == decode_frozen_assignment(_frozen_params())


def test_the_lock_round_trips_through_its_own_query_params():
    frozen = decode_frozen_assignment(_frozen_params())
    assert decode_frozen_assignment(frozen.as_query_params()) == frozen


def test_freeze_url_adds_the_lock_and_keeps_everything_else():
    share = (
        "https://example.com/explore?preset=tcja-full-extension&dynamic=0&run=1"
        f"&baseline={LIVE_BASELINE}&spec=abc123&mode=conventional"
    )
    frozen_url = freeze_url(share, engine="FRB/US-Lite (recommended)")
    params = {key: value[0] for key, value in parse_qs(urlparse(frozen_url).query).items()}

    assert urlparse(frozen_url).path == "/explore"
    assert params["preset"] == TCJA_ID
    assert params["run"] == "1"
    assert params["frozen"] == "1"
    assert params["engine"] == "frbus_lite"
    # The provenance stamps the share link already carried are untouched.
    assert params["baseline"] == LIVE_BASELINE
    assert params["spec"] == "abc123"
    assert params["mode"] == "conventional"


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("FRB/US-Lite (recommended)", "frbus_lite"),
        ("frbus_lite", "frbus_lite"),
        ("FRB/US-Lite", "frbus_lite"),
        ("Simple Multiplier", "simple"),
        ("simple", "simple"),
        (None, None),
        ("", None),
        ("some engine nobody has", None),
    ],
)
def test_engine_token_folds_every_spelling(label, expected):
    """The setting, the adapter's own name and the token must agree."""
    assert engine_token(label) == expected


def test_classroom_flag_is_read_from_either_spelling():
    assert is_classroom_request({"classroom": "1"})
    assert is_classroom_request({"mode": "classroom"})
    assert not is_classroom_request({})
    assert not is_classroom_request({"mode": "conventional"})


# ---------------------------------------------------------------------------
# Layer 1 — what is refused
# ---------------------------------------------------------------------------


def test_nothing_is_refused_when_the_vintage_matches():
    assert frozen_refusal(decode_frozen_assignment(_frozen_params())) is None
    assert frozen_refusal(None) is None


def test_a_link_naming_another_vintage_is_refused_by_name():
    problem = frozen_refusal(decode_frozen_assignment(_frozen_params(baseline="january2025")))

    assert problem is not None
    # Both vintages are named, so the reader can act: the one the assignment
    # wants, and the one they are looking at.
    assert "CBO January 2025" in problem
    assert LIVE_BASELINE[:3].capitalize() in problem


def test_a_frozen_link_without_a_baseline_is_refused():
    problem = frozen_refusal(decode_frozen_assignment(_frozen_params(baseline=None)))

    assert problem is not None
    assert "baseline" in problem


def test_a_link_pinning_an_engine_this_build_lacks_is_refused():
    problem = frozen_refusal(decode_frozen_assignment(_frozen_params(engine="dsge-9000")))

    assert problem is not None
    assert "dsge-9000" in problem


def test_the_lock_survives_the_legacy_url_shim():
    """An assignment issued in the pre-redesign URL shape stays an assignment.

    ``rewrite_legacy_query`` rebuilds the query string from an allowlist, so a
    key it does not know is dropped. Dropping these would silently demote a
    frozen link to an ordinary one — scored on whatever the student's own
    settings happened to be, which is the exact failure the lock exists for.
    """
    url_path, params = rewrite_legacy_query(
        {
            "analysis": "preset",
            "preset": TCJA_LABEL,
            "run": "1",
            "baseline": LIVE_BASELINE,
            "engine": "frbus_lite",
            "spec": "0123456789ab",
            "mode": "conventional",
            "frozen": "1",
            "classroom": "1",
        }
    )

    assert url_path == "explore"
    assert params["preset"] == TCJA_ID
    assert decode_frozen_assignment(params) == FrozenAssignment(
        baseline=LIVE_BASELINE,
        engine="frbus_lite",
        dynamic=False,
        spec="0123456789ab",
        mode="conventional",
    )
    assert is_classroom_request(params)


# ---------------------------------------------------------------------------
# Layer 2 — AppTest, through the real router
# ---------------------------------------------------------------------------


def _app(query_params: dict[str, str], page: str) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=300)
    at.query_params = dict(query_params)
    at.run()
    at.switch_page(page)
    at.query_params = dict(query_params)
    at.run()
    return at


def _state(at: AppTest, key: str, default=None):
    try:
        return at.session_state[key]
    except Exception:
        return default


def _widget(at: AppTest, kind: str, label: str):
    for element in getattr(at, kind):
        if element.label == label:
            return element
    raise AssertionError(f"no {kind} labelled {label!r}")


def _texts(at: AppTest) -> list[str]:
    """Every string the page rendered, whatever element carried it.

    A widget's ``value`` is looked up in session state and raises when the
    widget's state was garbage-collected on a page switch, so each read is
    guarded: this helper is asking "what does the page say", not "what does
    every widget hold".
    """
    out: list[str] = []
    for element in at.main:
        try:
            value = getattr(element, "value", None)
        except Exception:
            continue
        if isinstance(value, str):
            out.append(value)
    return out


@pytest.fixture(scope="module")
def frozen_explore() -> AppTest:
    return _app(_frozen_params(), EXPLORE)


@pytest.fixture(scope="module")
def open_explore() -> AppTest:
    """The same link with the lock taken off — the control case."""
    params = _frozen_params()
    params.pop("frozen")
    return _app(params, EXPLORE)


def test_a_frozen_link_scores_and_says_it_is_frozen(frozen_explore):
    at = frozen_explore
    assert not at.exception, at.exception

    scored = _state(at, SCORED_RESULT_KEY)
    assert scored is not None, "a frozen link must still score"
    assert scored.policy_name == TCJA_LABEL
    assert scored.mode == "conventional"

    assert any(FROZEN_LABEL in text for text in _texts(at)), "no frozen label on the page"


def test_a_frozen_link_disables_the_policy_inputs(frozen_explore):
    at = frozen_explore
    assert _widget(at, "selectbox", "Policy area").disabled
    assert _widget(at, "selectbox", "Select a proposal").disabled


def test_a_frozen_link_disables_the_scoring_mode_control(frozen_explore):
    """The lock has to hold on both copies of the toggle — they share a key."""
    assert _widget(frozen_explore, "toggle", "Dynamic scoring").disabled
    assert _state(frozen_explore, "sidebar_setting_dynamic_scoring") is False


def test_the_settings_popover_shows_and_honours_the_lock(frozen_explore):
    captions = _texts(frozen_explore)
    assert any(
        FROZEN_LABEL in text and "cannot be changed here" in text for text in captions
    ), "the ⚙ popover does not say the settings are frozen"


def test_the_result_carries_a_compact_provenance_line(frozen_explore):
    at = frozen_explore
    scored = _state(at, SCORED_RESULT_KEY)
    expected = (
        f"Scored on {scored.baseline_vintage} baseline · conventional · "
        "frozen by your instructor"
    )
    assert expected in _texts(at)


def test_a_non_frozen_link_is_unchanged(open_explore):
    at = open_explore
    assert not at.exception, at.exception

    assert _state(at, SCORED_RESULT_KEY) is not None
    assert not _widget(at, "selectbox", "Select a proposal").disabled
    assert not _widget(at, "toggle", "Dynamic scoring").disabled
    assert not any(FROZEN_LABEL in text for text in _texts(at))


def test_a_link_naming_another_vintage_scores_nothing(open_explore):
    """Requirement (d): refuse honestly rather than fall back silently.

    ``open_explore`` runs first on purpose — it leaves a scored result in a
    *different* session, so a refusal that merely hid the panel while scoring
    anyway would not pass by accident.
    """
    del open_explore
    at = _app(_frozen_params(baseline="january2025"), EXPLORE)

    assert not at.exception, at.exception
    assert _state(at, SCORED_RESULT_KEY) is None
    refusals = [text for text in _texts(at) if FROZEN_REFUSAL_HEADING in text]
    assert refusals, "the refusal was not shown"
    assert "CBO January 2025" in refusals[0]
    # Nothing was scored, so no policy picker was drawn to edit either.
    assert not [element for element in at.selectbox if element.label == "Select a proposal"]


def test_a_frozen_link_without_a_baseline_scores_nothing():
    at = _app(_frozen_params(baseline=None), EXPLORE)

    assert not at.exception, at.exception
    assert _state(at, SCORED_RESULT_KEY) is None
    assert any(FROZEN_REFUSAL_HEADING in text for text in _texts(at))


def test_a_frozen_tailor_link_renders_the_form_read_only():
    at = _app(
        _frozen_params(
            preset=None,
            type="income",
            rate="2",
            who="top400k",
            phase="1",
            spec="0123456789ab",
        ),
        TAILOR,
    )

    assert not at.exception, at.exception
    assert _state(at, SCORED_RESULT_KEY) is not None

    # The parameters the link named are in the form...
    assert at.session_state["tailor_tax_rate_change_pct"] == 2.0
    assert at.session_state["tailor_tax_threshold_choice"] == "Top earners ($400K+)"
    # ...and none of them can be moved, including the page's own chips.
    assert _widget(at, "slider", "Rate change (percentage points)").disabled
    assert _widget(at, "selectbox", "Who is affected?").disabled
    assert _widget(at, "text_input", "Policy name").disabled
    assert _widget(at, "button_group", "Policy type").disabled
    # Scoring it is still the student's to do.
    assert not _widget(at, "button", "Score this policy").disabled


# ---------------------------------------------------------------------------
# Making one: the instructor's control
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def classroom_explore() -> AppTest:
    params = _frozen_params()
    params.pop("frozen")
    params["classroom"] = "1"
    return _app(params, EXPLORE)


def test_the_assignment_link_control_is_classroom_only(classroom_explore, open_explore):
    assert any("Assignment link" in text for text in _texts(classroom_explore))
    assert not any("Assignment link" in text for text in _texts(open_explore))


def test_the_emitted_assignment_link_round_trips_onto_the_same_lock(classroom_explore):
    """Encode → decode → identical settings, on a link the app really built."""
    at = classroom_explore
    scored = _state(at, SCORED_RESULT_KEY)
    url = build_assignment_url(
        _state(at, "results"),
        scored,
        public_app_url="https://example.com",
        engine="FRB/US-Lite (recommended)",
    )
    assert url is not None

    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}
    frozen = decode_frozen_assignment(params)

    assert frozen is not None
    assert frozen.baseline == baseline_vintage_token(scored.baseline_vintage)
    assert frozen.spec == scored.policy_spec_hash
    assert frozen.mode == scored.mode
    assert frozen.dynamic is (scored.mode == "dynamic")
    assert frozen.engine == "frbus_lite"
    assert frozen_refusal(frozen) is None
    # The policy travels on the contract that already existed.
    assert params["preset"] == TCJA_ID


def test_replaying_the_emitted_link_reproduces_the_run(classroom_explore):
    at = classroom_explore
    url = build_assignment_url(
        _state(at, "results"),
        _state(at, SCORED_RESULT_KEY),
        public_app_url="https://example.com",
    )
    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}

    replayed = _app(params, EXPLORE)
    assert not replayed.exception, replayed.exception

    original = _state(at, SCORED_RESULT_KEY)
    restored = _state(replayed, SCORED_RESULT_KEY)
    assert restored is not None
    assert restored.policy_name == original.policy_name
    assert restored.headline == pytest.approx(original.headline)
    assert restored.baseline_vintage == original.baseline_vintage
    # The spec *hashes* are deliberately not compared here. ``AppTest`` reaches
    # a page by running the default page and then switching, and Streamlit
    # drops the state of widgets that did not render on the page just left, so
    # two sessions that a browser would treat identically can arrive at the
    # settings popover holding different values. That is the reason the spec
    # check in ``frozen_links.render_frozen_provenance`` is a caption rather
    # than a refusal — it reports a divergence, it does not block the page.
    # The replay is frozen even though the original session was not.
    assert _widget(replayed, "selectbox", "Select a proposal").disabled
    assert any(FROZEN_LABEL in text for text in _texts(replayed))


# ---------------------------------------------------------------------------
# The alias the whole feature hangs off
# ---------------------------------------------------------------------------


class _FakeClassroomSt:
    """The two calls ``app_pages.classroom`` makes for its instructor note."""

    def __init__(self) -> None:
        self.rendered: list[str] = []

    def expander(self, label, expanded=False):
        import contextlib

        self.rendered.append(str(label))
        return contextlib.nullcontext()

    def markdown(self, text="", *args, **kwargs):
        self.rendered.append(str(text))


def test_the_mode_classroom_alias_still_renders_classroom(monkeypatch):
    """``?mode=classroom`` predates all of this and must keep working.

    It routes through ``app.main`` before the navigation frame exists, so the
    alias is checked at the router; that the body it renders now carries the
    instructor note is checked on the page itself.
    """
    import app as app_module
    import classroom_app

    rendered = {"classroom": 0}
    monkeypatch.setattr(
        classroom_app,
        "render_classroom_app",
        lambda: rendered.__setitem__("classroom", rendered["classroom"] + 1),
    )

    st_module = _FakeClassroomSt()

    class _Alias:
        """Just enough of ``st`` for ``app.main``'s classroom branch."""

        def __init__(self):
            self.query_params = {"mode": "classroom"}
            self.errors: list[str] = []

        def set_page_config(self, **kwargs):
            pass

        def markdown(self, *args, **kwargs):
            pass

        def error(self, message):
            self.errors.append(str(message))

    alias_st = _Alias()
    app_module.main(
        st_module=alias_st,
        pd_module=object(),
        deps_builder=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("the alias must not build the scoring deps")
        ),
        classroom_renderer=lambda: classroom_page_render(st_module),
    )

    assert alias_st.errors == []
    assert rendered["classroom"] == 1
    assert any("assignment link" in text.lower() for text in st_module.rendered)


def classroom_page_render(st_module):
    from app_pages import classroom as classroom_page

    classroom_page.render(st_module=st_module)


# ---------------------------------------------------------------------------
# Build — the same lock over a package (FOLLOWUPS carry-over)
# ---------------------------------------------------------------------------
#
# ``/explore`` and ``/tailor`` freeze one score; ``/build`` freezes a checklist
# and a deficit target. The lock half of the URL is byte-identical (the tests
# above cover it once, for all three surfaces); what is new here is the package
# half and the promise that freezing it changes nothing about the arithmetic.

BUILD = "app_pages/build.py"
PACKAGE_IDS = ("ss-donut-250k", "corporate-28pct")


def _frozen_build_params(**overrides):
    """A frozen ``/build`` link for a two-policy package at a 3% target."""
    params = {
        "policies": ",".join(PACKAGE_IDS),
        "target": "3.0",
        "metric": "pct_gdp",
        "baseline": LIVE_BASELINE,
        "engine": "frbus_lite",
        "spec": build_package_spec_hash(PACKAGE_IDS, 3.0, "pct_gdp"),
        "mode": "conventional",
        "dynamic": "0",
        "frozen": "1",
    }
    params.update(overrides)
    return {key: value for key, value in params.items() if value is not None}


# ---------------------------------------------------------------------------
# Layer 1 — the package codec, without a runtime
# ---------------------------------------------------------------------------


def test_an_ordinary_build_link_carries_no_package():
    assert decode_frozen_build({}) is None
    assert decode_frozen_build({"policies": ",".join(PACKAGE_IDS), "target": "3.0"}) is None


def test_decode_reads_the_whole_build_package():
    package = decode_frozen_build(_frozen_build_params())

    assert package == FrozenBuildPackage(
        preset_ids=PACKAGE_IDS, target=3.0, metric="pct_gdp"
    )
    assert package.from_values is False
    assert package.target_label == "3.0% of GDP"


def test_the_build_package_round_trips_through_its_own_query_params():
    package = decode_frozen_build(_frozen_build_params())
    replayed = {**package.as_query_params(), "frozen": "1"}
    assert decode_frozen_build(replayed) == package


def test_the_build_package_decodes_legacy_labels_like_the_share_codec():
    """One resolver for both link shapes — an old label is not a broken link."""
    package = decode_frozen_build(_frozen_build_params(policies=TCJA_LABEL))
    assert package.preset_ids == (TCJA_ID,)


def test_a_dollar_target_keeps_its_own_metric():
    package = decode_frozen_build(_frozen_build_params(target="1200", metric="usd_b"))
    assert package.target == 1200.0
    assert package.target_label == "$1,200B/yr"


def test_a_frozen_build_link_naming_no_package_is_refused():
    problem = frozen_build_refusal(
        decode_frozen_build(_frozen_build_params(policies=None, target=None))
    )
    assert problem is not None
    assert "names no package" in problem


def test_a_values_link_is_a_package_and_is_not_refused():
    """The composer is deterministic, so a philosophy is a package."""
    package = decode_frozen_build(
        _frozen_build_params(policies=None, target=None, values="deficit-hawk")
    )
    assert package.from_values is True
    assert package.values_slug == "deficit-hawk"
    assert frozen_build_refusal(package) is None
    assert frozen_build_refusal(None) is None


def test_a_package_this_catalog_cannot_rebuild_is_refused_too():
    """Named but unresolvable is the same failure as unnamed, one step later."""
    ids = decode_frozen_build(_frozen_build_params())
    assert frozen_build_unresolved_refusal(ids, ["ss-donut-250k"]) is None

    problem = frozen_build_unresolved_refusal(ids, [])
    assert problem is not None and "not in this catalog" in problem

    values = decode_frozen_build(
        _frozen_build_params(policies=None, target=None, values="ghost-philosophy")
    )
    problem = frozen_build_unresolved_refusal(values, [])
    assert problem is not None and "ghost-philosophy" in problem


def test_the_build_spec_hash_covers_the_ids_the_target_and_the_metric():
    base = build_package_spec_hash(PACKAGE_IDS, 3.0, "pct_gdp")
    assert len(base) == 12
    assert build_package_spec_hash(list(PACKAGE_IDS), 3.0, "pct_gdp") == base
    assert build_package_spec_hash(PACKAGE_IDS[::-1], 3.0, "pct_gdp") != base
    assert build_package_spec_hash(PACKAGE_IDS, 3.5, "pct_gdp") != base
    assert build_package_spec_hash(PACKAGE_IDS, 3.0, "usd_b") != base


def test_the_emitted_build_link_round_trips_onto_the_same_package_and_lock():
    url = build_package_assignment_url(
        PACKAGE_IDS,
        3.0,
        "pct_gdp",
        engine="FRB/US-Lite (recommended)",
        baseline=LIVE_BASELINE,
        public_app_url="https://example.com",
    )
    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}

    assert urlparse(url).path == "/build"
    # The id list stays readable rather than %2C-escaped.
    assert "policies=ss-donut-250k,corporate-28pct" in url

    assert decode_frozen_build(params) == FrozenBuildPackage(
        preset_ids=PACKAGE_IDS, target=3.0, metric="pct_gdp"
    )
    frozen = decode_frozen_assignment(params)
    assert frozen == FrozenAssignment(
        baseline=LIVE_BASELINE,
        engine="frbus_lite",
        dynamic=False,
        spec=build_package_spec_hash(PACKAGE_IDS, 3.0, "pct_gdp"),
        mode="conventional",
    )
    assert frozen_refusal(frozen) is None
    assert frozen_build_refusal(decode_frozen_build(params)) is None


def test_a_values_slug_rides_along_as_a_label_never_as_a_load():
    """The ids are what is pinned; the philosophy is how it is described."""
    url = build_package_assignment_url(
        PACKAGE_IDS, 3.0, values_slug="deficit-hawk", public_app_url="https://example.com"
    )
    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}

    assert params["values"] == "deficit-hawk"
    assert params["policies"] == ",".join(PACKAGE_IDS)
    # ``load=1`` would recompose the package from a catalog that may have been
    # re-scored since the assignment was set.
    assert "load" not in params


def test_the_build_lock_survives_the_legacy_url_shim():
    """A ``/build`` link is not legacy-shaped, so the shim leaves it alone."""
    assert rewrite_legacy_query(_frozen_build_params()) is None


# ---------------------------------------------------------------------------
# Layer 2 — AppTest, through the real router
# ---------------------------------------------------------------------------


def _build_app(query_params: dict) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=300)
    at.switch_page(BUILD)
    for key, value in query_params.items():
        at.query_params[key] = value
    at.run()
    return at


def _boxes(at: AppTest) -> dict:
    return {
        box.key: (box.value, box.disabled)
        for box in at.checkbox
        if box.key and box.key.startswith("dt_")
    }


def _metrics(at: AppTest) -> list:
    return [(m.label, m.value, m.delta) for m in at.metric]


def _search_box(at: AppTest):
    return next(box for box in at.text_input if box.label.startswith("Search"))


def _one(at: AppTest, kind: str, label: str):
    """A widget AppTest has no typed accessor for (``download_button`` …)."""
    for element in at.get(kind):
        if getattr(element, "label", None) == label:
            return element
    raise AssertionError(f"no {kind} labelled {label!r}")


def _waterfall(at: AppTest) -> dict:
    """The bars themselves — labels, values and measures — from the figure spec."""
    import json

    charts = at.get("plotly_chart")
    assert charts, "the waterfall did not render"
    trace = json.loads(charts[0].proto.spec)["data"][0]
    return {key: trace[key] for key in ("x", "y", "measure")}


@pytest.fixture(scope="module")
def frozen_build() -> AppTest:
    return _build_app(_frozen_build_params())


@pytest.fixture(scope="module")
def open_build() -> AppTest:
    """The same package with the lock taken off — the control case."""
    params = _frozen_build_params()
    for key in ("frozen", "spec", "baseline", "engine", "mode", "dynamic"):
        params.pop(key, None)
    return _build_app(params)


def test_a_frozen_build_link_pins_the_package(frozen_build):
    at = frozen_build
    assert not at.exception, at.exception

    assert at.session_state["build_selection"] == list(PACKAGE_IDS)
    boxes = _boxes(at)
    assert {key for key, (checked, _) in boxes.items() if checked} == {
        f"dt_{build_id}" for build_id in PACKAGE_IDS
    }
    assert all(disabled for _, disabled in boxes.values()), "a checkbox is still editable"
    assert len(boxes) > 40, "the whole catalog should still be readable"


def test_a_frozen_build_link_disables_the_target_slider_at_the_links_value(frozen_build):
    slider = _widget(frozen_build, "slider", "Target deficit (% of GDP)")
    assert slider.value == 3.0
    assert slider.disabled


def test_a_frozen_build_link_disables_the_rest_of_the_strip(frozen_build):
    at = frozen_build
    # Search filters what is *visible*, and the metric toggle picks the unit the
    # pinned target is expressed in; the mode toggle would swap the checklist
    # for the panel that composes a different package.
    assert _search_box(at).disabled
    labels = {group.label: group.disabled for group in at.get("button_group")}
    assert labels.get("Target metric") is True
    assert labels.get("Start from") is True


def test_a_frozen_build_link_says_it_is_frozen(frozen_build):
    texts = _texts(frozen_build)

    banner = [text for text in texts if FROZEN_LABEL in text and "2 policies" in text]
    assert banner, "no frozen banner on the page"
    assert "3.0% of GDP" in banner[0]

    provenance = [text for text in texts if "frozen by your instructor" in text]
    assert provenance, "no provenance line under the scoreboard"
    assert provenance[0].startswith("Scored against CBO ")
    assert "official list prices" in provenance[0]

    assert any(
        FROZEN_LABEL in text and "cannot be changed here" in text for text in texts
    ), "the ⚙ popover does not show the lock"


def test_a_frozen_build_counts_exactly_what_an_open_one_counts(frozen_build, open_build):
    """The promise: freezing changes what can be touched, never what is counted."""
    assert _metrics(frozen_build) == _metrics(open_build)
    assert _waterfall(frozen_build) == _waterfall(open_build)


def test_a_frozen_build_still_exports(frozen_build):
    """A student has to be able to hand something in."""
    assert not _one(frozen_build, "download_button", "Download CSV").disabled
    assert any(
        "Policy ids: ss-donut-250k,corporate-28pct" in text
        for text in _texts(frozen_build)
    ), "the copy summary is gone"


def test_a_non_frozen_build_is_unchanged(open_build):
    at = open_build
    assert not at.exception, at.exception

    assert at.session_state["build_selection"] == list(PACKAGE_IDS)
    boxes = _boxes(at)
    # Not "nothing is disabled": the overlap guardrails legitimately dim the
    # exclusive siblings of what is ticked, frozen or not. The distinction is
    # that a reader can still untick their own package and pick something else.
    assert boxes["dt_ss-donut-250k"] == (True, False)
    assert boxes["dt_corporate-28pct"] == (True, False)
    assert sum(1 for _, disabled in boxes.values() if disabled) < len(boxes) / 2
    assert not _widget(at, "slider", "Target deficit (% of GDP)").disabled
    assert not _search_box(at).disabled
    assert not any(FROZEN_LABEL in text for text in _texts(at))


def test_editing_the_package_after_freezing_is_captioned_not_refused():
    """The ``spec=`` convention, applied to ``policies=``.

    A tampered link still renders: the hash covers the whole package, so a
    retired catalog id would otherwise retire every assignment ever issued.
    The page reports the divergence where it can be read and acted on — the
    same call ``render_frozen_provenance`` makes on Explore and Tailor.
    """
    at = _build_app(_frozen_build_params(policies="ss-donut-250k"))
    assert not at.exception, at.exception

    # It scored the URL's package, not the instructor's...
    assert at.session_state["build_selection"] == ["ss-donut-250k"]
    warnings = [text for text in _texts(at) if "spec hash" in text]
    assert warnings, "the tampered package was not reported"
    assert build_package_spec_hash(["ss-donut-250k"], 3.0, "pct_gdp") in warnings[0]
    assert build_package_spec_hash(PACKAGE_IDS, 3.0, "pct_gdp") in warnings[0]
    assert "policies=" in warnings[0]
    # ...and said so rather than refusing to show anything.
    assert not any(FROZEN_REFUSAL_HEADING in text for text in _texts(at))


def test_a_build_link_naming_another_vintage_counts_nothing():
    at = _build_app(_frozen_build_params(baseline="january2025"))

    assert not at.exception, at.exception
    refusals = [text for text in _texts(at) if FROZEN_REFUSAL_HEADING in text]
    assert refusals, "the refusal was not shown"
    assert "CBO January 2025" in refusals[0]
    # Nothing was drawn to read a number off, either.
    assert not _boxes(at)
    assert not at.metric


def test_a_frozen_build_link_with_nothing_to_pin_is_refused():
    at = _build_app(_frozen_build_params(policies=None, target=None))

    assert not at.exception, at.exception
    refusals = [text for text in _texts(at) if FROZEN_REFUSAL_HEADING in text]
    assert refusals, "the refusal was not shown"
    assert "names no package" in refusals[0]
    assert not _boxes(at)


def test_a_frozen_link_naming_a_philosophy_nobody_has_is_refused():
    at = _build_app(
        _frozen_build_params(policies=None, target=None, values="ghost-philosophy")
    )

    assert not at.exception, at.exception
    refusals = [text for text in _texts(at) if FROZEN_REFUSAL_HEADING in text]
    assert refusals, "the refusal was not shown"
    assert "ghost-philosophy" in refusals[0]
    assert not _boxes(at), "an unrebuildable package must not render an empty one"


def test_a_frozen_values_link_composes_the_package_its_ids_would_have():
    """Freezing a philosophy is legal exactly because this is true.

    The composer is a pure function of tags × vector — the LLM only ever turns
    free text into a vector, and a URL carries the vector, not the text — so
    the philosophy and the id list it composes are two spellings of one
    package.
    """
    from fiscal_model.composer.archetypes import get_archetype
    from fiscal_model.composer.composer import compose_values_package, values_catalog

    vector = get_archetype("deficit-hawk").vector
    composed = list(compose_values_package(vector, values_catalog()).policy_ids)
    # Deterministic before anything renders: same vector, same package.
    assert composed == list(compose_values_package(vector, values_catalog()).policy_ids)

    at = _build_app(
        _frozen_build_params(policies=None, target=None, values="deficit-hawk")
    )
    assert not at.exception, at.exception
    assert at.session_state["build_selection"] == composed
    assert all(disabled for _, disabled in _boxes(at).values())
    assert any(
        "composed from the starting philosophy" in text for text in _texts(at)
    ), "the banner does not say where the package came from"


# ---------------------------------------------------------------------------
# Making one: the instructor's control on Build
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def classroom_build() -> AppTest:
    params = _frozen_build_params()
    for key in ("frozen", "spec", "baseline", "engine", "mode", "dynamic"):
        params.pop(key, None)
    params["classroom"] = "1"
    return _build_app(params)


def test_the_build_assignment_control_is_classroom_only(classroom_build, open_build):
    assert any("Assignment link" in text for text in _texts(classroom_build))
    assert not any("Assignment link" in text for text in _texts(open_build))


def test_the_values_panel_offers_the_frozen_package_it_composes():
    """An instructor who starts from a philosophy can hand out its package.

    The two links in that popover say different things and both are wanted:
    the values link means "start where I started", the assignment link means
    "hand in these numbers".
    """
    at = _build_app({"classroom": "1"})
    assert not at.exception, at.exception

    emitted = [
        text
        for text in _texts(at)
        if text.startswith("http") and "frozen=1" in text and "values=" in text
    ]
    assert emitted, "the values panel emitted no frozen link"

    params = {key: value[0] for key, value in parse_qs(urlparse(emitted[0]).query).items()}
    package = decode_frozen_build(params)
    # The philosophy is the label; the composed ids are what is pinned.
    assert package.values_slug
    assert package.preset_ids and not package.from_values
    assert frozen_refusal(decode_frozen_assignment(params)) is None
    assert "load" not in params


def test_the_emitted_build_link_replays_onto_the_same_frozen_package(classroom_build):
    """Encode → decode → replay, on a link the app really built."""
    emitted = [
        text
        for text in _texts(classroom_build)
        if text.startswith("http") and "frozen=1" in text
    ]
    assert emitted, "the instructor control emitted no frozen link"
    params = {key: value[0] for key, value in parse_qs(urlparse(emitted[0]).query).items()}

    package = decode_frozen_build(params)
    assert package.preset_ids == PACKAGE_IDS
    assert package.target == 3.0
    frozen = decode_frozen_assignment(params)
    assert frozen.baseline == LIVE_BASELINE
    assert frozen.spec == build_package_spec_hash(PACKAGE_IDS, 3.0, "pct_gdp")
    assert frozen_refusal(frozen) is None

    replayed = _build_app(params)
    assert not replayed.exception, replayed.exception
    assert replayed.session_state["build_selection"] == list(PACKAGE_IDS)
    assert all(disabled for _, disabled in _boxes(replayed).values())
    assert _metrics(replayed) == _metrics(classroom_build)
    # Replaying it raises no spec caption: the link records what the page finds.
    assert not [text for text in _texts(replayed) if "spec hash" in text]
