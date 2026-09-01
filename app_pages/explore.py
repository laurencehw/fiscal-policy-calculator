"""Explore — presets, worked examples, and the shared result panel (``/explore``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer
from components.results import render_score_surface
from fiscal_model.ui.app_controller import CLASSROOM_BLURB
from fiscal_model.ui.calculation_controller import PRESET_ANALYSIS_MODE
from fiscal_model.ui.settings_controller import claim_inline_dynamic_toggle

PAGE_TITLE = "Explore"
URL_PATH = "explore"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Explore surface — the old Calculator tab, minus the sidebar.

    Same preset picker, quick-start cards and "How is this scored?" panel as
    Phase 1; Phase 4 swaps the result area for the shared panel
    (``components.results``), adds the inline dynamic-scoring toggle beside
    Calculate, and invalidates the panel when the preset or the toggle changes
    rather than showing the previous preset's numbers under a warning.
    """
    claim_inline_dynamic_toggle(st_module)
    settings = render_chrome(st_module=st_module, deps=deps)

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
