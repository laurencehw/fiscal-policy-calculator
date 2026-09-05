"""Classroom Mode (``/classroom``).

Classroom is a self-contained teaching surface with its own hero and its own
(deliberate) sidebar, so it does not render the shared chrome — a data-status
pill and a model-settings popover would be noise in a student assignment.

``/?mode=classroom`` still works: ``app.py`` treats it as a back-compat alias
and renders this same body.

Above the assignments sits the one piece of instructor plumbing that is not an
assignment: how to make a **frozen assignment link**, so a class hands in one
set of numbers rather than one per student. The link itself is built on the
result surface (``?classroom=1`` shows the control) and decoded by
``fiscal_model/ui/frozen_links.py``.
"""

from __future__ import annotations

from typing import Any

PAGE_TITLE = "Classroom"
URL_PATH = "classroom"

INSTRUCTOR_NOTE = (
    "Score the policy you want to set on **Explore** or **Tailor**, then copy "
    "the **🔒 Assignment link** from Export Results. It pins the baseline "
    "vintage, the scoring engine, dynamic scoring and the policy itself, and "
    "shows students that it is frozen — so everyone hands in the same numbers."
)

#: Where the control lives. ``classroom=1`` is what reveals it.
ASSIGNMENT_LINK_MAKER_URL = "/explore?classroom=1"


def _render_instructor_note(st_module: Any) -> None:
    """The "make an assignment link" pointer, above the assignment picker."""
    with st_module.expander("🔒 For instructors — make an assignment link", expanded=False):
        st_module.markdown(INSTRUCTOR_NOTE)
        st_module.markdown(
            f"[Open Explore with the control shown →]({ASSIGNMENT_LINK_MAKER_URL})"
        )


def render(st_module: Any = None, deps: Any = None, app_root: Any = None) -> None:
    """Render Classroom Mode.

    ``classroom_app`` uses the ``streamlit`` module directly rather than the
    injected ``st_module`` seam, so ``deps`` and ``app_root`` are accepted and
    ignored; they keep the page signature uniform across ``app_pages/``.
    ``st_module`` is used for the instructor note this module owns, and falls
    back to ``streamlit`` for the ``?mode=classroom`` alias, which calls
    ``render()`` with no arguments.
    """
    del deps, app_root

    if st_module is None:
        import streamlit

        st_module = streamlit

    from classroom_app import render_classroom_app

    _render_instructor_note(st_module)
    render_classroom_app()
