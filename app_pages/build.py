"""Build — the deficit-reduction package builder (``/build``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Build"
URL_PATH = "build"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Build surface.

    This is ``ui/tabs/deficit_target.py`` — the live "Budget Builder" tab —
    **not** ``ui/tabs/package_builder.py``, which has no production call site
    (see ``planning/redesign/NOTES.md`` section 6.1). Phase 3 reworks the body;
    Phase 3b folds Package Studio in as its opening panel.
    """
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    from fiscal_model.ui.tabs.deficit_target import render_deficit_target_tab

    render_deficit_target_tab(
        st_module=st_module,
        cbo_score_map=deps.CBO_SCORE_MAP,
        fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
        use_real_data=True,
    )

    render_page_footer(st_module)
