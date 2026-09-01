"""
Shared card components for the Ask home page.

Two things live here:

* **Doorway cards** — the ``Build`` / ``Tailor`` links under the Ask hero.
  ``st.page_link`` will not accept a bare ``"/build"`` string: it resolves a
  string against registered *script paths*, and this app registers its pages
  from callables, so nothing matches. It does accept a ``StreamlitPage``, and
  a page's routing identity is ``calc_md5(url_path)`` — so a lightweight page
  object built with the same ``url_path`` links to the registered page without
  ``app_pages/ask.py`` having to reach into the router. :func:`page_target`
  builds those.

* **Worked-example cards** — the four question-led cards from the wireframe.
  They read the same data the Explore quick-start grid uses
  (``app_controller._QUICK_START_CARDS``) so a headline can never drift
  between the two surfaces, and are enriched here with the policy-status chip
  (``Enacted · P.L. 119-21`` / ``Proposal``) resolved from
  ``fiscal_model.policy_status``. On Ask they PREFILL the question box rather
  than running a preset.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.policy_status import get_policy_status
from fiscal_model.ui.app_controller import _QUICK_START_CARDS

# The wireframe's Ask home shows four worked examples: TCJA, the 39.6% top
# rate, the 28% corporate rate, and the 10% universal tariff.
_ASK_CARD_KEYS: tuple[str, ...] = ("tcja", "biden400k", "corp28", "tariff10")

# P.L. 119-21 is the July 2025 reconciliation law; the status map records it
# as the thing that overtook the TCJA-extension presets.
_STATUS_CHIPS: dict[str, str] = {
    "enacted": "Enacted",
    "superseded": "Enacted · P.L. 119-21",
    "partially": "Partly enacted · P.L. 119-21",
    "proposed": "Proposal",
}


def page_target(st_module: Any, *, url_path: str, title: str, icon: str | None = None):
    """Build a ``StreamlitPage`` usable as an ``st.page_link`` target.

    The returned page is never run — only its ``url_path`` (and the routing
    hash derived from it) is read by ``st.page_link``.
    """
    def _noop() -> None:  # pragma: no cover — never executed
        return None

    return st_module.Page(_noop, title=title, url_path=url_path, icon=icon)


def _preset_label(card: dict[str, Any]) -> str | None:
    """Full preset label for a quick-start card, for the status lookup."""
    short = (card.get("preset") or {}).get("sidebar_preset_choice")
    if not short:
        return None
    try:
        from fiscal_model.app_data import PRESET_POLICIES
        from fiscal_model.ui.policy_input_presets import _short_display_name
    except Exception:  # pragma: no cover — defensive
        return None
    for name in PRESET_POLICIES:
        if _short_display_name(name) == short:
            return name
    return None


def _status_chip(card: dict[str, Any]) -> str | None:
    label = _preset_label(card)
    status = get_policy_status(label) if label else None
    if status is None:
        return None
    return f"{status.icon} {_STATUS_CHIPS.get(status.status, status.label)}"


def ask_example_cards() -> list[dict[str, Any]]:
    """The four worked-example cards, with a status chip and dated source."""
    by_key = {card["key"]: card for card in _QUICK_START_CARDS}
    cards: list[dict[str, Any]] = []
    for key in _ASK_CARD_KEYS:
        card = by_key.get(key)
        if card is None:  # pragma: no cover — guarded by tests
            continue
        enriched = dict(card)
        enriched["status_chip"] = _status_chip(card)
        cards.append(enriched)
    return cards


def render_doorway_cards(st_module: Any) -> None:
    """The two doorway cards under the hero: Build and Tailor.

    ``st.columns`` with no fixed widths, so the pair stacks on a phone.
    """
    doorways = (
        {
            "url_path": "build",
            "title": "Build",
            "icon": "🧱",
            "label": "Open Build",
            "heading": "Build a package",
            "blurb": (
                "Pick from 45+ scored policies and close the gap to a deficit "
                "target. Live totals as you check options."
            ),
        },
        {
            "url_path": "tailor",
            "title": "Tailor",
            "icon": "🎚",
            "label": "Open Tailor",
            "heading": "Tailor a policy",
            "blurb": (
                "Set the rate, threshold and timing yourself. Scored with "
                "tier-labeled confidence and a sensitivity band."
            ),
        },
    )
    cols = st_module.columns(len(doorways))
    for col, door in zip(cols, doorways, strict=True):
        with col, st_module.container(border=True):
            st_module.markdown(f"**{door['heading']}**")
            st_module.caption(door["blurb"])
            st_module.page_link(
                page_target(
                    st_module,
                    url_path=door["url_path"],
                    title=door["title"],
                    icon=door["icon"],
                ),
                label=door["label"],
                width="stretch",
            )


def render_example_cards(st_module: Any, *, key_prefix: str = "ask_ex") -> str | None:
    """Worked-example cards that prefill the question box.

    Returns the question of the card that was clicked this run, or ``None``.
    """
    cards = ask_example_cards()
    if not cards:
        return None
    st_module.caption("Worked examples — click to ask")
    picked: str | None = None
    cols = st_module.columns(len(cards))
    for col, card in zip(cols, cards, strict=True):
        with col, st_module.container(border=True):
            if card.get("status_chip"):
                st_module.caption(card["status_chip"])
            st_module.markdown(f"**{card['question']}**")
            st_module.markdown(
                f'<span style="color:{card["headline_color"]};font-weight:600">'
                f'{card["headline"]}</span>'
                f' &nbsp;<span style="opacity:0.7">({card["source"]})</span>',
                unsafe_allow_html=True,
            )
            if st_module.button(
                "Ask this →",
                key=f"{key_prefix}_{card['key']}",
                width="stretch",
            ):
                picked = card["question"]
    return picked


__all__ = [
    "ask_example_cards",
    "page_target",
    "render_doorway_cards",
    "render_example_cards",
]
