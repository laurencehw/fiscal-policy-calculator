"""Explore — presets, worked examples, and the result sub-tabs (``/explore``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer
from fiscal_model.ui.app_controller import CLASSROOM_BLURB, render_policy_workbench
from fiscal_model.ui.calculation_controller import PRESET_ANALYSIS_MODE

PAGE_TITLE = "Explore"
URL_PATH = "explore"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Explore surface — the old Calculator tab, minus the sidebar.

    The preset picker moves out of the global sidebar into the page body; the
    quick-start cards, the "How is this scored?" panel and the six result
    sub-tabs are unchanged. The Classroom Mode blurb that used to sit at the
    bottom of the sidebar is rehomed here (Classroom is also a nav entry now).
    """
    settings = render_chrome(st_module=st_module, deps=deps)

    render_policy_workbench(
        st_module=st_module,
        deps=deps,
        settings=settings,
        model_available=True,
        app_root=app_root,
        modes=(PRESET_ANALYSIS_MODE,),
        inputs_heading="Choose a proposal",
        show_quick_start=True,
        split_layout=False,
    )

    with st_module.expander("🎓 Classroom Mode", expanded=False):
        st_module.markdown(CLASSROOM_BLURB)

    render_page_footer(st_module)
