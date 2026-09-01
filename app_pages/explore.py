"""Explore — presets, worked examples, and the shared result panel (``/explore``).

URL contract (redesign plan §7)::

    /explore?preset=<stable_id>&dynamic=0|1&run=1

``preset`` accepts a stable id *and* every legacy spelling (emoji label,
URL-encoded label, short dropdown name) through ``preset_ids.resolve_preset``.
``run=1`` scores it once per distinct link — see :func:`_apply_query_params`.
"""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer
from components.results import render_score_surface
from fiscal_model.ui.app_controller import CLASSROOM_BLURB
from fiscal_model.ui.calculation_controller import PRESET_ANALYSIS_MODE
from fiscal_model.ui.settings_controller import claim_inline_dynamic_toggle
from fiscal_model.ui.share_links import apply_share_query_params

PAGE_TITLE = "Explore"
URL_PATH = "explore"


def _apply_query_params(st_module: Any) -> str | None:
    """Restore the preset picker from ``?preset=…&dynamic=…&run=1``.

    Runs before any widget on the page so Streamlit accepts the session-state
    writes. ``apply_share_query_params`` is idempotent — it hashes the request
    into ``_applied_share_token`` — so auto-run fires once per distinct link and
    a later manual change is not overwritten on the next rerun. The scoring
    pipeline calls it again further down; the token makes that a no-op.

    Returns a ``?preset=`` token that matched nothing, so the caller can say so.
    """
    try:
        return apply_share_query_params(st_module=st_module)
    except Exception:  # pragma: no cover — a bad link must not take the page down
        return None


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Explore surface — the old Calculator tab, minus the sidebar.

    Same preset picker, quick-start cards and "How is this scored?" panel as
    Phase 1; Phase 4 swaps the result area for the shared panel
    (``components.results``), adds the inline dynamic-scoring toggle beside
    Calculate, and invalidates the panel when the preset or the toggle changes
    rather than showing the previous preset's numbers under a warning.
    """
    unresolved_preset = _apply_query_params(st_module)
    claim_inline_dynamic_toggle(st_module)
    settings = render_chrome(st_module=st_module, deps=deps)

    if unresolved_preset:
        st_module.info(
            f'No proposal matches **{unresolved_preset}** — it may have been '
            "renamed since that link was made. Pick one below; every other "
            "part of the link still applied."
        )

    render_score_surface(
        st_module=st_module,
        deps=deps,
        settings=settings,
        app_root=app_root,
        modes=(PRESET_ANALYSIS_MODE,),
        inputs_heading="Choose a proposal",
        score_label="Calculate Impact",
        show_quick_start=True,
        split_layout=False,
    )

    with st_module.expander("🎓 Classroom Mode", expanded=False):
        st_module.markdown(CLASSROOM_BLURB)

    render_page_footer(st_module)
