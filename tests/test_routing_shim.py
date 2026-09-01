"""Routing, share links and back-compat — Phase 5.

Three layers, cheapest first:

1. **The pure rewrite** (``share_links.rewrite_legacy_query``) — covered in
   ``tests/test_share_links.py``; here we test the *router* half that talks to
   Streamlit's ``PagesManager``.
2. **The shim against a fake ``st``** — no runtime, so it runs in milliseconds
   and pins the query-param rewriting and the retired-pathname table.
3. **``AppTest`` end to end** — a real script run on ``app.py``: a legacy TCJA
   link lands on Explore with the preset selected and a result present, the new
   ``/explore?preset=<id>&run=1`` contract scores, ``/tailor?…&run=1`` scores
   with ``phase >= 1``, and the share URL emitted afterwards round-trips.

Acceptance criteria: plan §9.7 (legacy link restores and auto-runs on
``/explore``) and §7.1-7.4 (URL contract, stable ids, shim, ``baseline=``).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from streamlit.testing.v1 import AppTest

import app
from components.results import SCORED_RESULT_KEY
from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.ui.share_links import build_share_url

EXPLORE = "app_pages/explore.py"
TAILOR = "app_pages/tailor.py"
SCORE_BUTTON = "score_policy_button"

# The app logs a running commentary of every baseline load; quiet for tests.
logging.getLogger("fiscal_model").setLevel(logging.WARNING)

TCJA_LABEL = "🏛️ TCJA Full Extension (CBO: $4.6T)"
TCJA_ID = "tcja-full-extension"


# ---------------------------------------------------------------------------
# Layer 2 — the shim against a fake Streamlit
# ---------------------------------------------------------------------------


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _FakeStreamlit:
    def __init__(self, query_params=None):
        self.query_params = dict(query_params or {})
        self.session_state = _SessionState()


class _FakePagesManager:
    """Just the two members the shim touches."""

    def __init__(self, page_name="", page_hash=""):
        self.intended_page_name = page_name
        self.intended_page_script_hash = page_hash
        self.intents: list[tuple[str, str]] = []

    def set_script_intent(self, page_script_hash, page_name):
        self.intents.append((page_script_hash, page_name))
        self.intended_page_script_hash = page_script_hash
        self.intended_page_name = page_name


@pytest.fixture
def routed(monkeypatch):
    """Run the shim with a stubbed script-run context; return the pages manager."""

    def _run(query_params=None, *, page_name="", page_hash=""):
        pages_manager = _FakePagesManager(page_name, page_hash)
        monkeypatch.setattr(
            app, "_script_run_ctx", lambda: SimpleNamespace(pages_manager=pages_manager)
        )
        st_module = _FakeStreamlit(query_params)
        app._apply_legacy_url_shim(st_module)
        return pages_manager, st_module

    return _run


def test_legacy_preset_link_is_routed_to_explore_with_the_stable_id(routed):
    pages_manager, st_module = routed(
        {"analysis": "preset", "preset": TCJA_LABEL, "dynamic": "0", "run": "1"}
    )

    assert pages_manager.intents == [("", "explore")]
    assert st_module.query_params == {
        "preset": TCJA_ID,
        "dynamic": "0",
        "run": "1",
    }
    assert st_module.session_state[app._LEGACY_ROUTE_KEY] == "explore"


def test_legacy_custom_and_spending_links_are_routed_to_tailor(routed):
    pages_manager, st_module = routed({"analysis": "custom", "run": "1"})
    assert pages_manager.intents == [("", "tailor")]
    assert st_module.query_params["type"] == "income"

    pages_manager, st_module = routed(
        {"analysis": "spending", "spending_preset": "Infrastructure Investment ($100B/yr)"}
    )
    assert pages_manager.intents == [("", "tailor")]
    assert st_module.query_params["type"] == "spending"
    assert st_module.query_params["spending_preset"] == (
        "Infrastructure Investment ($100B/yr)"
    )


def test_ask_pathname_is_canonicalised_to_the_default_page(routed):
    """Streamlit forces the default page's url_path to "", so /ask is unknown."""
    pages_manager, st_module = routed({"q": "what is the deficit?"}, page_name="ask")

    assert pages_manager.intents == [("", "")]
    # The prefill is untouched — Ask reads it in this same run.
    assert st_module.query_params == {"q": "what is the deficit?"}


def test_retired_studio_pathname_opens_the_build_values_panel(routed):
    pages_manager, st_module = routed({}, page_name="studio")

    assert pages_manager.intents == [("", "build")]
    assert st_module.query_params.get("load") == "1"
    assert st_module.query_params.get("values")


def test_classroom_and_new_contract_urls_are_left_alone(routed):
    for params, page_name in (
        ({"mode": "classroom"}, ""),
        ({"preset": TCJA_ID, "run": "1"}, "explore"),
        ({"type": "income", "rate": "2"}, "tailor"),
        ({"policies": "ss-donut-250k"}, "build"),
        ({}, ""),
    ):
        pages_manager, st_module = routed(params, page_name=page_name)
        assert pages_manager.intents == [], f"{params} was needlessly rerouted"
        assert st_module.query_params == params


def test_a_page_addressed_by_hash_is_never_second_guessed(routed):
    """In-app nav clicks and ``AppTest.switch_page`` address pages by hash."""
    pages_manager, _ = routed({}, page_name="ask", page_hash="deadbeef")
    assert pages_manager.intents == []


def test_shim_is_inert_without_a_script_run_context(monkeypatch):
    monkeypatch.setattr(app, "_script_run_ctx", lambda: None)
    st_module = _FakeStreamlit({"analysis": "preset", "preset": TCJA_LABEL})

    assert app._apply_legacy_url_shim(st_module) is None
    # The query params are still rewritten; only the page switch needs a ctx.
    assert st_module.query_params["preset"] == TCJA_ID


# ---------------------------------------------------------------------------
# Why the /ask rewrite is needed, at the level Streamlit actually decides it
# ---------------------------------------------------------------------------


def _registered_pages() -> dict:
    """The page table ``st.navigation`` builds for this app.

    ``StreamlitPage.url_path`` returns ``""`` for the default page regardless of
    the ``url_path=`` passed to ``st.Page``, so the *public* pathname of Ask is
    the empty string and ``ask`` is registered nowhere.
    """
    from streamlit.util import calc_md5

    def _entry(url_path: str, public: str | None = None) -> dict:
        return {
            "page_script_hash": calc_md5(url_path),
            "page_name": url_path,
            "icon": "",
            "script_path": "",
            "url_pathname": url_path if public is None else public,
        }

    return {
        calc_md5("ask"): _entry("ask", public=""),  # the default page
        calc_md5("build"): _entry("build"),
        calc_md5("tailor"): _entry("tailor"),
        calc_md5("explore"): _entry("explore"),
    }


def test_ask_pathname_is_unresolvable_until_the_shim_rewrites_it():
    """The "page not found" flash, reproduced and then fixed, in one test.

    ``st.navigation`` sends ``page_not_found`` exactly when
    ``PagesManager.get_page_script`` returns ``None``. Requesting ``ask`` by
    name does, because no registered page has that *public* pathname; after the
    shim rewrites the intent to ``""`` it resolves to the default page instead.
    """
    from streamlit.runtime.pages_manager import PagesManager
    from streamlit.util import calc_md5

    pages_manager = PagesManager("app.py")
    pages_manager.set_pages(_registered_pages())
    default_hash = calc_md5("ask")

    pages_manager.set_script_intent("", "ask")
    assert pages_manager.get_page_script(fallback_page_hash=default_hash) is None

    pages_manager.set_script_intent("", "")  # what _request_page(st, "") does
    found = pages_manager.get_page_script(fallback_page_hash=default_hash)
    assert found is not None and found["page_script_hash"] == default_hash


def test_shim_page_names_resolve_to_registered_pages():
    """Every page the shim can redirect to must be addressable by pathname."""
    from streamlit.runtime.pages_manager import PagesManager
    from streamlit.util import calc_md5

    for url_path in ("explore", "tailor", "build"):
        pages_manager = PagesManager("app.py")
        pages_manager.set_pages(_registered_pages())
        pages_manager.set_script_intent("", url_path)

        found = pages_manager.get_page_script(fallback_page_hash=calc_md5("ask"))
        assert found is not None, f"the shim would 404 on {url_path}"
        assert found["page_script_hash"] == calc_md5(url_path)


# ---------------------------------------------------------------------------
# Layer 3 — AppTest, end to end
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


@pytest.fixture(scope="module")
def explore_from_legacy_link() -> AppTest:
    """§9.7: the exact legacy URL, replayed on the page the shim sends it to.

    ``AppTest`` addresses pages by script hash, so it cannot reproduce the
    browser's pathname-based routing; the shim's page switch is covered by the
    fake-``st`` tests above. What this covers is the other half — that the
    rewritten query params really do restore *and score* the preset.
    """
    from fiscal_model.ui.share_links import rewrite_legacy_query

    url_path, params = rewrite_legacy_query(
        {"analysis": "preset", "preset": TCJA_LABEL, "dynamic": "0", "run": "1"}
    )
    assert url_path == "explore"
    return _app(params, EXPLORE)


def test_legacy_link_restores_the_preset_and_auto_runs(explore_from_legacy_link):
    at = explore_from_legacy_link
    assert not at.exception, at.exception

    assert _state(at, "sidebar_policy_area") == "TCJA / Individual"
    assert _state(at, "sidebar_preset_choice") == "TCJA Full Extension"

    scored = _state(at, SCORED_RESULT_KEY)
    assert scored is not None, "run=1 did not score the preset"
    assert scored.policy_name == TCJA_LABEL
    assert scored.headline > 0  # a tax cut adds to the deficit


def test_auto_run_is_spent_once_per_link(explore_from_legacy_link):
    """A rerun of the same URL must not re-score (or re-arm) on every refresh."""
    at = explore_from_legacy_link
    assert _state(at, "qs_calculate") is None


def test_new_explore_contract_scores_on_arrival():
    at = _app({"preset": TCJA_ID, "dynamic": "0", "run": "1"}, EXPLORE)

    assert not at.exception, at.exception
    assert _state(at, "sidebar_preset_choice") == "TCJA Full Extension"
    assert _state(at, SCORED_RESULT_KEY) is not None


def test_unknown_preset_shows_a_notice_and_does_not_crash():
    at = _app({"preset": "a-policy-that-never-existed", "run": "1"}, EXPLORE)

    assert not at.exception, at.exception
    notices = [element.value for element in at.info]
    assert any("a-policy-that-never-existed" in str(text) for text in notices)


def test_tailor_contract_scores_with_the_link_parameters():
    at = _app(
        {"type": "income", "rate": "2", "who": "top400k", "phase": "1", "run": "1"},
        TAILOR,
    )

    assert not at.exception, at.exception
    assert at.session_state["tailor_policy_kind"] == "Income"
    assert at.session_state["tailor_tax_rate_change_pct"] == 2.0
    assert at.session_state["tailor_tax_threshold_choice"] == "Top earners ($400K+)"
    # Chip ⑨ — the engine contract the old default violated.
    assert at.session_state["tailor_tax_phase_in"] >= 1

    scored = _state(at, SCORED_RESULT_KEY)
    assert scored is not None, "run=1 did not score the tailored policy"
    assert scored.headline < 0  # a rate *increase* reduces the deficit


def test_tailor_contract_selects_the_spending_form():
    at = _app({"type": "spending"}, TAILOR)

    assert not at.exception, at.exception
    assert at.session_state["tailor_policy_kind"] == "Spending"


# ---------------------------------------------------------------------------
# The share URL a run emits
# ---------------------------------------------------------------------------


def test_share_url_after_a_run_carries_id_baseline_spec_and_mode(
    explore_from_legacy_link,
):
    at = explore_from_legacy_link
    scored = _state(at, SCORED_RESULT_KEY)
    result_data = _state(at, "results")

    url = build_share_url(
        result_data=result_data, public_app_url="https://example.com", scored=scored
    )
    parsed = urlparse(url)
    params = {key: value[0] for key, value in parse_qs(parsed.query).items()}

    assert parsed.path == "/explore"
    assert params["preset"] == TCJA_ID
    assert params["baseline"]  # e.g. "feb2026"
    assert params["spec"] == scored.policy_spec_hash
    assert params["mode"] == scored.mode
    assert params["run"] == "1"

    # ...and the vintage in the URL is the one the exports print.
    from fiscal_model.ui.share_links import baseline_vintage_token

    assert params["baseline"] == baseline_vintage_token(scored.baseline_vintage)


def test_emitted_share_url_round_trips_onto_the_same_preset(explore_from_legacy_link):
    at = explore_from_legacy_link
    url = build_share_url(
        result_data=_state(at, "results"),
        public_app_url="https://example.com",
        scored=_state(at, SCORED_RESULT_KEY),
    )
    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}

    replayed = _app(params, EXPLORE)
    assert not replayed.exception, replayed.exception
    assert _state(replayed, SCORED_RESULT_KEY).policy_name == TCJA_LABEL


def test_exports_and_the_share_url_agree_on_the_baseline_vintage(
    explore_from_legacy_link,
):
    """§9.10 + §7.4: the CSV header, the Copy Summary and the link agree."""
    from fiscal_model.ui.share_links import baseline_vintage_token
    from fiscal_model.ui.tabs.results_summary import (
        build_csv_export,
        build_text_summary,
    )

    at = explore_from_legacy_link
    scored = _state(at, SCORED_RESULT_KEY)
    result_data = _state(at, "results")
    url = build_share_url(
        result_data=result_data, public_app_url="https://example.com", scored=scored
    )

    csv_export = build_csv_export(scored, result_data, url)
    text_export = build_text_summary(scored, result_data, url)

    for export in (csv_export, text_export):
        assert f"Baseline vintage: {scored.baseline_vintage}" in export
        assert f"Share URL: {url}" in export

    token = f"baseline={baseline_vintage_token(scored.baseline_vintage)}"
    assert token in url


def test_the_acceptance_criterion_label_is_still_the_live_one():
    """§9.7 quotes this label verbatim; guard it against a silent rename."""
    assert TCJA_LABEL in PRESET_POLICIES
