"""Ask — the citation-grounded assistant, and the home page of the app (``/``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Ask"
URL_PATH = "ask"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Ask surface.

    Phase 1 is a straight lift of the old "Ask" tab. Phase 2 turns this into
    the hero + chips + doorway-card home from the wireframe.
    """
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    deps.render_ask_tab(
        st_module=st_module,
        fiscal_assistant=deps.fiscal_assistant,
        scoring_result=st_module.session_state.get("results"),
    )

    render_page_footer(st_module)
