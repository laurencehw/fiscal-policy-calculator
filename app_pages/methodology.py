"""Methodology — assumptions, data sources, validation (``/methodology``)."""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Methodology"
URL_PATH = "methodology"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Methodology surface (body unchanged)."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)
    deps.render_methodology_tab(st_module=st_module)
    render_page_footer(st_module)
