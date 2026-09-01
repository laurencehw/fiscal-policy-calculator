"""Assistant admin dashboard (``/admin``).

Registered only when the request carries a matching ``?admin=<token>`` — the
same gate ``app_controller`` used for the conditional Admin tab. Non-admins
never see the nav entry and the page is not registered for them at all.
"""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Admin"
URL_PATH = "admin"


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the token-gated assistant admin surface."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    from fiscal_model.ui.tabs.assistant_admin import render_assistant_admin_tab

    render_assistant_admin_tab(st_module=st_module)

    render_page_footer(st_module)
