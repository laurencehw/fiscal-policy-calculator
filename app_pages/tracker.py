"""Bill Tracker — congress.gov pipeline view (``/tracker``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Bill Tracker"
URL_PATH = "tracker"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Bill Tracker surface (body unchanged)."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)
    deps.render_bill_tracker_tab(st_module=st_module)
    render_page_footer(st_module)
