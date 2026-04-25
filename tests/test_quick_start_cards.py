"""
Smoke tests for the quick-start landing card grid.
"""

from __future__ import annotations

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.ui.app_controller import _QUICK_START_CARDS, render_quick_start
from fiscal_model.ui.policy_input_presets import _preset_category, _short_display_name


class _SessionState(dict):
    """Mirrors Streamlit's session_state: supports both dict[] and attr access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_every_card_has_required_keys():
    for card in _QUICK_START_CARDS:
        for field in ("key", "question", "context", "headline", "headline_color", "source", "preset"):
            assert field in card, f"card {card.get('key')!r} missing field {field!r}"
        assert card["question"].endswith("?"), f"{card['key']}: question should be phrased as a question"
        assert "?" not in card["context"], f"{card['key']}: context shouldn't be a question"


def test_card_keys_are_unique():
    keys = [c["key"] for c in _QUICK_START_CARDS]
    assert len(keys) == len(set(keys)), f"duplicate card keys: {keys}"


def test_every_tax_card_references_a_real_preset():
    short_to_area = {
        _short_display_name(name): _preset_category(p)
        for name, p in PRESET_POLICIES.items()
    }
    for card in _QUICK_START_CARDS:
        preset = card["preset"]
        if preset.get("sidebar_spending_preset"):
            # Spending presets live in a different namespace; skip here.
            continue
        short = preset.get("sidebar_preset_choice")
        area = preset.get("sidebar_policy_area")
        assert short in short_to_area, (
            f"card {card['key']!r}: preset short name {short!r} is not in PRESET_POLICIES"
        )
        assert area == short_to_area[short], (
            f"card {card['key']!r}: declared area {area!r} but preset is in "
            f"{short_to_area[short]!r}; the sidebar would render the wrong area filter"
        )


def test_render_quick_start_dismissed_when_results_exist():
    """Once a calculation has been run, the landing block auto-collapses."""
    from unittest.mock import MagicMock

    st = MagicMock()
    st.session_state = _SessionState(results=object())
    render_quick_start(st)
    # No card columns should be drawn.
    assert not st.columns.called


def test_render_quick_start_draws_two_rows_for_six_cards():
    """Six cards in two rows of three; we don't pin the exact column args
    but we do require multiple `columns` calls — one per row."""
    from unittest.mock import MagicMock

    n_cards = len(_QUICK_START_CARDS)
    expected_rows = (n_cards + 2) // 3  # 6 cards -> 2 rows

    st = MagicMock()
    st.session_state = _SessionState()
    st.button.return_value = False  # Don't trigger any "Try this" path.
    # Each `st.columns(N)` returns a list of N column mocks. The dismiss
    # row uses [20, 1], so just return enough mocks to satisfy any call.
    st.columns.side_effect = lambda spec: [MagicMock() for _ in (
        spec if isinstance(spec, list) else range(spec)
    )]

    render_quick_start(st)

    # Dismiss header row + one row per group of three cards.
    assert st.columns.call_count == 1 + expected_rows
