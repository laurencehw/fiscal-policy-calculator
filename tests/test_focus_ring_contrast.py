"""The keyboard-focus ring clears WCAG 1.4.11's 3:1 on every surface it can sit on.

Browser verification found the doorway and top-nav links painted no focus indicator at all.
``components.chrome`` now sets one solid ring through ``--fpc-focus-ring``; this pins the
colours to the page backgrounds in both themes, so retheming either cannot silently drop
below 3:1. ``tests/e2e`` checks the same thing in a real browser.
"""

from __future__ import annotations

from components import chrome


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lum(rgb: tuple[int, int, int]) -> float:
    def ch(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(_rgb(a)), _lum(_rgb(b))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_light_ring_clears_3_to_1_on_light_surfaces():
    for surface in ("#ffffff", "#f0f2f6"):
        assert _ratio(chrome._FOCUS_RING_LIGHT, surface) >= 3.0, surface


def test_dark_ring_clears_3_to_1_on_dark_surfaces():
    for surface in (chrome._DARK_BG, chrome._DARK_SURFACE):
        assert _ratio(chrome._FOCUS_RING_DARK, surface) >= 3.0, surface


def test_dark_overlay_overrides_the_ring_variable_after_the_light_default():
    """Same specificity, so the dark declaration must come later to win."""
    assert chrome._FOCUS_RING_LIGHT in chrome._FOCUS_CSS
    assert f"--fpc-focus-ring: {chrome._FOCUS_RING_DARK}" in chrome._DARK_MODE_CSS


def test_the_doorway_and_top_nav_links_are_covered():
    for hook in ("stPageLink-NavLink", "stTopNavLink", "stPopoverButton"):
        assert f'[data-testid="{hook}"]:focus-visible' in chrome._FOCUS_CSS
