"""Package Studio — goal-driven policy-mix composer (``/studio``).

Registered under **More** so nothing shipped in #65 is lost to the navigation
change. Per ``planning/redesign/DECISIONS.md`` #3 this surface is temporary:
Phase 3b folds the composer into the "Start from your values" panel inside
Build and retires this page.
"""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Package Studio"
URL_PATH = "studio"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Package Studio surface (body unchanged)."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    from fiscal_model.ui.tabs.package_studio import render_package_studio_tab

    render_package_studio_tab(st_module=st_module)

    render_page_footer(st_module)
