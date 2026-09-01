"""
Tests for the responsive CSS in fiscal_model/ui/styles.py.

These pin the contract that mobile breakpoints exist and target the
Streamlit DOM elements we depend on, so a future refactor doesn't
quietly drop the responsive layer.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

from components.chrome import APP_TITLE
from fiscal_model.ui.styles import APP_STYLES, apply_app_styles

MOBILE_QUERY = "@media screen and (max-width: 640px)"


def _media_blocks(query: str) -> list[str]:
    """Return the body of every ``@media`` block matching ``query``.

    Brace-matched rather than regexed so a nested rule can't truncate the
    block and make an assertion pass vacuously.
    """
    blocks: list[str] = []
    for match in re.finditer(re.escape(query), APP_STYLES):
        start = APP_STYLES.index("{", match.end())
        depth, i = 0, start
        while i < len(APP_STYLES):
            if APP_STYLES[i] == "{":
                depth += 1
            elif APP_STYLES[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        blocks.append(APP_STYLES[start + 1 : i])
    return blocks


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


def test_mobile_heading_sizes_override_streamlit():
    """Mobile heading rules must beat Streamlit's own heading CSS.

    Streamlit sizes headings from an emotion class scoped to the markdown
    container (``.st-emotion-cache-xxxxx h3``, specificity 0-1-1), so the bare
    element selectors here lose and the whole mobile type scale is dead CSS.
    Measured in Chrome at 412px before the fix: ``h1`` computed to 44px and
    ``h3`` to 28px, i.e. the desktop sizes.
    """
    body = "\n".join(_media_blocks(MOBILE_QUERY))
    for tag in ("h1", "h2", "h3"):
        rule = re.search(rf"(?<![.\w-])\b{tag}\s*{{([^}}]*)}}", body)
        assert rule is not None, f"mobile block defines no {tag} rule"
        assert "font-size" in rule.group(1)
        assert "!important" in rule.group(1), (
            f"{tag} font-size on mobile must be !important or Streamlit's "
            "emotion class wins and the rule does nothing"
        )


def test_mobile_brand_title_fits_one_line():
    """The chrome brand line must not wrap on a phone.

    At Streamlit's native 28px the title measured 361.6px against 346px of
    available text width at a 412px viewport, so it wrapped to
    "Fiscal Policy Impact" / "Calculator". Because
    ``header[data-testid="stHeader"]`` is an opaque 60px band painted over the
    scrolling ``stMain``, a ~134px scroll hid line one and the heading read
    just "Calculator" (the reported bug). Desktop never wrapped.

    Measured advance width for this string is ~12.92em; available text width
    is roughly ``viewport - 66px``, so at a 320px floor the cap is
    ``254 / 12.92 = 19.7px`` ≈ 1.23rem.
    """
    body = "\n".join(_media_blocks(MOBILE_QUERY))
    rule = re.search(r"(?<![.\w-])\bh3\s*{([^}]*)}", body)
    assert rule is not None
    size = re.search(r"font-size:\s*([\d.]+)rem", rule.group(1))
    assert size is not None, "mobile h3 size must be expressed in rem"
    assert float(size.group(1)) <= 1.2, (
        f"{APP_TITLE!r} (~12.92em wide) wraps below a 320px viewport above "
        "1.2rem"
    )


def test_desktop_heading_sizes_untouched():
    """No bare heading font-size may leak outside a media query."""
    outside = APP_STYLES
    for query in (MOBILE_QUERY, "@media screen and (min-width: 641px)"):
        for block in _media_blocks(query):
            outside = outside.replace(block, "")
    assert re.search(r"(?<![.\w-])\bh[123]\s*{[^}]*font-size", outside) is None


def test_apply_app_styles_emits_markdown_with_html_allowed():
    st = MagicMock()
    apply_app_styles(st)
    assert st.markdown.called
    args, kwargs = st.markdown.call_args
    # Style block is passed as the first positional with unsafe_allow_html.
    assert "<style>" in args[0]
    assert kwargs.get("unsafe_allow_html") is True
