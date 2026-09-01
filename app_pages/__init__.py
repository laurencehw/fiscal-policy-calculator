"""
One module per navigable surface of the Streamlit app.

Deliberately **not** named ``pages/``: Streamlit auto-discovers a ``pages/``
directory next to the entrypoint and switches to legacy (v1) multipage
behaviour. ``PagesManager.uses_pages_directory`` is latched at process start —
before ``app.py`` ever runs — and the script runner then builds its own
navigation from ``pages/*.py`` instead of executing our router
(``streamlit/runtime/scriptrunner/script_runner.py`` -> ``_mpa_v1``). Naming the
package ``app_pages/`` keeps ``st.navigation`` in sole control, which is also
the safe side of the upstream double-nav quirk (streamlit/streamlit#13224).

Each module exposes ``render(st_module, deps, app_root=None)`` plus
``PAGE_TITLE`` / ``URL_PATH`` constants, and is a thin wrapper over an existing
renderer in ``fiscal_model/ui/`` — the page bodies themselves are unchanged by
the navigation redesign.
"""

__all__ = [
    "admin",
    "ask",
    "build",
    "classroom",
    "explore",
    "methodology",
    "tailor",
    "tracker",
]
