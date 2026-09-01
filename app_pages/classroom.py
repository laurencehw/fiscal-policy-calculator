"""Classroom Mode (``/classroom``).

Classroom is a self-contained teaching surface with its own hero and its own
(deliberate) sidebar, so it does not render the shared chrome — a data-status
pill and a model-settings popover would be noise in a student assignment.

``/?mode=classroom`` still works: ``app.py`` treats it as a back-compat alias
and renders this same body.
"""

from __future__ import annotations

from typing import Any

PAGE_TITLE = "Classroom"
URL_PATH = "classroom"


def render(st_module: Any = None, deps: Any = None, app_root: Any = None) -> None:
    """Render Classroom Mode.

    ``classroom_app`` uses the ``streamlit`` module directly rather than the
    injected ``st_module`` seam, so the arguments are accepted and ignored;
    they keep the page signature uniform across ``app_pages/``.
    """
    del st_module, deps, app_root

    from classroom_app import render_classroom_app

    render_classroom_app()
