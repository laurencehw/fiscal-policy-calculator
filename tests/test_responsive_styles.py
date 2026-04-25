"""
Tests for the responsive CSS in fiscal_model/ui/styles.py.

These pin the contract that mobile breakpoints exist and target the
Streamlit DOM elements we depend on, so a future refactor doesn't
quietly drop the responsive layer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fiscal_model.ui.styles import APP_STYLES, apply_app_styles


def test_styles_define_mobile_breakpoint():
    """Phone-sized viewports get their own block."""
    assert "@media screen and (max-width: 640px)" in APP_STYLES


def test_styles_define_tablet_breakpoint():
    """Tablets get a separate, lighter set of overrides."""
    assert "min-width: 641px" in APP_STYLES
    assert "max-width: 1024px" in APP_STYLES


def test_mobile_styles_stack_horizontal_columns():
    """The single biggest mobile fix: st.columns rows must stack vertically."""
    assert 'data-testid="stHorizontalBlock"' in APP_STYLES
    assert "flex-direction: column" in APP_STYLES


def test_mobile_styles_widen_button_taps():
    """Buttons must be at least 44px tall on phones (iOS/Material guideline)."""
    assert "min-height: 44px" in APP_STYLES


def test_mobile_styles_allow_table_horizontal_scroll():
    """Dense dataframes should scroll, not squash, on narrow viewports."""
    assert 'data-testid="stDataFrame"' in APP_STYLES
    assert "overflow-x: auto" in APP_STYLES


def test_apply_app_styles_emits_markdown_with_html_allowed():
    st = MagicMock()
    apply_app_styles(st)
    assert st.markdown.called
    args, kwargs = st.markdown.call_args
    # Style block is passed as the first positional with unsafe_allow_html.
    assert "<style>" in args[0]
    assert kwargs.get("unsafe_allow_html") is True
