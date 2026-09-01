"""Tailor — define your own tax or spending policy (``/tailor``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer
from fiscal_model.ui.app_controller import render_policy_workbench
from fiscal_model.ui.calculation_controller import (
    CUSTOM_ANALYSIS_MODE,
    SPENDING_ANALYSIS_MODE,
)

PAGE_TITLE = "Tailor"
URL_PATH = "tailor"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Tailor surface.

    Phase 1 is a *move*: the sidebar "Define your policy" and "Spending
    program" forms render in a left column with the result panel on the right.
    Phase 4 redesigns this page (start-from-a-preset, policy-type chips, an
    inline dynamic-scoring toggle beside Score).
    """
    settings = render_chrome(st_module=st_module, deps=deps)

    render_policy_workbench(
        st_module=st_module,
        deps=deps,
        settings=settings,
        model_available=True,
        app_root=app_root,
        modes=(CUSTOM_ANALYSIS_MODE, SPENDING_ANALYSIS_MODE),
        inputs_heading="Define your policy",
        show_quick_start=False,
        split_layout=True,
    )

    render_page_footer(st_module)
