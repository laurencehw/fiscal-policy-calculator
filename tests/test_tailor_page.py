"""End-to-end tests for ``/tailor`` through Streamlit's ``AppTest``.

Covers the three things the redesign plan asks for by name (§9.5 and the
Phase 1 handoff):

1. the page's defaults score successfully — no ``phase_in_years`` error
   (chip ⑨: the widget minimum is 1, the engine contract is ``>= 1``);
2. editing an input after a run *replaces* the numbers with the invalidation
   notice (chip ⑩) instead of leaving stale figures on screen;
3. navigating Tailor -> Explore -> Tailor preserves ``tailor_tax_policy_name``.

(3) is the Phase 1 known-issue. Streamlit resolves a widget key through the
widget's own state and falls back to the last value *code* wrote; once the
widget is garbage-collected on another page that fallback silently reverts the
field. ``ui/session_state.py`` mirrors each keyed value and detects the echo.
"""

from __future__ import annotations

import logging

import pytest
from streamlit.testing.v1 import AppTest

from components.results import INVALIDATION_NOTICE, SCORED_RESULT_KEY

TAILOR = "app_pages/tailor.py"
EXPLORE = "app_pages/explore.py"
NAME_KEY = "tailor_tax_policy_name"
RATE_KEY = "tailor_tax_rate_change_pct"
SCORE_BUTTON = "score_policy_button"
DYNAMIC_KEY = "sidebar_setting_dynamic_scoring"

# The app logs a running commentary of every baseline load; quiet for tests.
logging.getLogger("fiscal_model").setLevel(logging.WARNING)


def _state(at: AppTest, key: str, default=None):
    """Read a session key without raising when it is absent."""
    try:
        return at.session_state[key]
    except Exception:
        return default


@pytest.fixture(scope="module")
def tailor_app() -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=300)
    at.run()
    at.switch_page(TAILOR)
    at.run()
    assert not at.exception, at.exception
    return at


def _fresh() -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=300)
    at.run()
    at.switch_page(TAILOR)
    at.run()
    return at


# ---------------------------------------------------------------------------
# The form card (wireframe 03-tailor)
# ---------------------------------------------------------------------------


def test_tailor_renders_the_wireframe_form_controls(tailor_app):
    keys = {group.key for group in tailor_app.button_group}
    assert {"tailor_start_from", "tailor_policy_kind"} <= keys

    assert [button.key for button in tailor_app.button] == [SCORE_BUTTON]
    assert tailor_app.button(key=SCORE_BUTTON).label == "Score this policy"


def test_dynamic_toggle_sits_inline_and_shares_the_chrome_key(tailor_app):
    """DECISIONS #2: inline beside Score, same key as chrome and share links."""
    toggles = {toggle.key for toggle in tailor_app.toggle}
    assert DYNAMIC_KEY in toggles
    # Exactly one widget on that key — two would be a DuplicateWidgetID error.
    assert sum(1 for toggle in tailor_app.toggle if toggle.key == DYNAMIC_KEY) == 1
    assert not tailor_app.exception


def test_phase_in_widget_minimum_is_one(tailor_app):
    """Chip ⑨: the engine rejects ``phase_in_years < 1``."""
    phase_in = tailor_app.slider(key="tailor_tax_phase_in")
    assert phase_in.min == 1
    assert _state(tailor_app, "tailor_tax_phase_in") >= 1


# ---------------------------------------------------------------------------
# 1. Defaults score cleanly
# ---------------------------------------------------------------------------


def test_default_configuration_scores_without_a_phase_in_error():
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()

    assert not at.exception, at.exception
    errors = [element.value for element in at.error]
    assert errors == [], errors
    assert not any("phase_in_years" in text for text in errors)

    scored = _state(at, SCORED_RESULT_KEY)
    assert scored is not None
    assert scored.mode == "conventional"
    assert scored.window.startswith("FY")
    assert scored.per_year and len(scored.per_year) == scored.n_years


def test_scoring_publishes_a_result_whose_hash_matches_the_current_run():
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()

    scored = _state(at, SCORED_RESULT_KEY)
    assert scored.policy_spec_hash == _state(at, "current_run_id")
    assert scored.policy_spec_hash == _state(at, "results_run_id")


def test_the_panel_opens_the_deep_views_as_tabs_inside_it():
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()

    labels = [tab.label for tab in at.tabs]
    for expected in ("👥 Distribution", "🌍 Economic Effects", "📋 Details"):
        assert expected in labels, labels
    # The headline lives above the tabs now, not in a "Results & Details" tab.
    assert "📊 Results & Details" not in labels


# ---------------------------------------------------------------------------
# 2. Invalidation (chip ⑩)
# ---------------------------------------------------------------------------


def _headline_is_rendered(at: AppTest) -> bool:
    return any("Deficit Impact (conventional)" in element.value for element in at.markdown)


def test_editing_an_input_after_a_run_replaces_the_numbers_with_the_notice():
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()
    assert _headline_is_rendered(at)

    at.slider(key=RATE_KEY).set_value(4.0)
    at.run()

    warnings = [element.value for element in at.warning]
    assert any("Configuration changed" in text for text in warnings), warnings
    assert INVALIDATION_NOTICE in warnings
    assert not _headline_is_rendered(at), "stale numbers must not stay on screen"


def test_re_scoring_after_an_edit_brings_the_panel_back():
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()
    at.slider(key=RATE_KEY).set_value(4.0)
    at.run()
    at.button(key=SCORE_BUTTON).click()
    at.run()

    assert _headline_is_rendered(at)
    assert not any("Configuration changed" in w.value for w in at.warning)
    scored = _state(at, SCORED_RESULT_KEY)
    assert scored.policy_spec_hash == _state(at, "current_run_id")


def test_flipping_the_dynamic_toggle_invalidates_and_then_adds_a_dynamic_view():
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()
    assert _state(at, SCORED_RESULT_KEY).mode == "conventional"

    at.toggle(key=DYNAMIC_KEY).set_value(True)
    at.run()
    assert any("Configuration changed" in w.value for w in at.warning)

    at.button(key=SCORE_BUTTON).click()
    at.run()
    scored = _state(at, SCORED_RESULT_KEY)
    assert scored.mode == "dynamic"
    assert scored.macro_model
    # The headline is still the conventional score; the dynamic total differs.
    assert scored.headline == pytest.approx(scored.static + scored.behavioral, abs=1e-6)
    assert scored.dynamic_total == pytest.approx(
        scored.headline - scored.feedback + scored.debt_service, abs=1e-6
    )


def test_explore_invalidates_on_a_preset_change_too():
    """Chip ⑩ applies to Explore, not only to the Tailor form."""
    at = AppTest.from_file("app.py", default_timeout=300)
    at.run()
    at.switch_page(EXPLORE)
    at.run()
    assert not at.exception, at.exception

    at.button(key=SCORE_BUTTON).click()
    at.run()
    assert _state(at, SCORED_RESULT_KEY) is not None

    picker = at.selectbox(key="sidebar_preset_choice")
    other = next(option for option in picker.options if option != picker.value)
    picker.set_value(other)
    at.run()

    assert any("Configuration changed" in w.value for w in at.warning)


# ---------------------------------------------------------------------------
# 3. Cross-page widget state (the Phase 1 known issue)
# ---------------------------------------------------------------------------


def test_navigating_away_and_back_preserves_the_policy_name():
    at = _fresh()
    at.text_input(key=NAME_KEY).set_value("My surcharge")
    at.run()
    assert _state(at, NAME_KEY) == "My surcharge"

    at.switch_page(EXPLORE)
    at.run()
    assert not at.exception, at.exception

    at.switch_page(TAILOR)
    at.run()
    assert not at.exception, at.exception
    assert _state(at, NAME_KEY) == "My surcharge"
    assert at.text_input(key=NAME_KEY).value == "My surcharge"


def test_navigating_away_and_back_preserves_the_numeric_form_fields():
    at = _fresh()
    at.slider(key=RATE_KEY).set_value(6.5)
    at.run()

    at.switch_page(EXPLORE)
    at.run()
    at.switch_page(TAILOR)
    at.run()

    assert _state(at, RATE_KEY) == 6.5
    assert at.slider(key=RATE_KEY).value == 6.5


def test_a_scored_result_survives_the_round_trip_and_stays_valid():
    """The panel must come back showing numbers, not the invalidation notice."""
    at = _fresh()
    at.button(key=SCORE_BUTTON).click()
    at.run()
    hash_before = _state(at, SCORED_RESULT_KEY).policy_spec_hash

    at.switch_page(EXPLORE)
    at.run()
    at.switch_page(TAILOR)
    at.run()

    assert _state(at, SCORED_RESULT_KEY).policy_spec_hash == hash_before
    assert _state(at, "current_run_id") == hash_before
    assert _headline_is_rendered(at)


# ---------------------------------------------------------------------------
# Deselecting a chip must not kill the page (live-app report, 2026-09-01)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "expected"),
    [("tailor_policy_kind", "Income"), ("tailor_start_from", "Blank")],
)
def test_deselecting_a_chip_restores_the_stored_value_instead_of_crashing(key, expected):
    """``st.segmented_control`` returns ``None`` when the active chip is clicked.

    The page used to write the widget key *after* the widget existed, and the
    resulting ``StreamlitAPIException`` surfaced through the section error
    boundary as "Tailor encountered an issue". The stored value must come back
    and the rest of the form must still render.
    """
    at = _fresh()
    assert at.button_group(key=key).value == expected
    at.button_group(key=key).set_value([])
    at.run()
    assert not at.exception, at.exception
    assert not at.error, [element.value for element in at.error]
    assert at.session_state[key] == expected
    assert at.button_group(key=key).value == expected
    assert [button.key for button in at.button] == [SCORE_BUTTON]


def test_deselecting_the_kind_chip_brings_back_the_users_last_choice():
    """The restore comes from the mirror, so a non-default choice survives."""
    at = _fresh()
    at.button_group(key="tailor_policy_kind").set_value("Corporate")
    at.run()
    assert at.session_state["tailor_policy_kind"] == "Corporate"
    at.button_group(key="tailor_policy_kind").set_value([])
    at.run()
    assert not at.exception, at.exception
    assert not at.error, [element.value for element in at.error]
    assert at.session_state["tailor_policy_kind"] == "Corporate"
