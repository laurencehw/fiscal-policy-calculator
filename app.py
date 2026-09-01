"""
Fiscal Policy Impact Calculator — Streamlit router.

``app.py`` stays the deployment entry point (Streamlit Community Cloud is
configured against this filename); since the ask-first redesign it is a
``st.navigation`` router rather than a tab host.

URL routing:
  /                — Ask (default page)
  /build           — Build a deficit-reduction package
  /tailor          — Tailor your own policy
  /explore         — Explore scored proposals
  /tracker         — Bill Tracker            (More)
  /methodology     — Methodology             (More)
  /classroom       — Classroom Mode          (More)
  /studio          — Package Studio          (More; folded into Build in Phase 3b)
  /admin           — Assistant admin         (only with a matching ?admin= token)
  /?mode=classroom — back-compat alias for /classroom

Known Streamlit limitation: ``StreamlitPage.url_path`` is forced to ``""`` for
the default page, so the Ask page answers ``/`` but ``/ask`` is not a
registered pathname — Streamlit emits a transient "page not found" notice and
then renders the default page (Ask) anyway. Canonicalising ``/ask`` -> ``/``
belongs in :func:`_apply_legacy_url_shim` in Phase 5.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from fiscal_model.ui.runtime_logging import (
    build_runtime_metadata,
    configure_runtime_logger,
    log_runtime_event,
)

_DEPS_SESSION_KEY = "_app_dependencies"


def _render_head_metadata(st_module: Any) -> None:
    """Set the page config (exactly once per run) and emit social metadata."""
    st_module.set_page_config(
        page_title="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring",
        page_icon="📊",
        layout="wide",
        # "auto": expanded on desktop, collapsed on small screens. The app no
        # longer uses a global sidebar, but Classroom Mode still renders one.
        initial_sidebar_state="auto",
    )
    try:
        from fiscal_model.ui.helpers import validated_policy_count

        _blurb = (
            "Estimate the budgetary impact of tax and spending proposals. "
            f"{validated_policy_count()} policies benchmarked against "
            "CBO/JCT/Treasury scores."
        )
    except Exception:
        _blurb = (
            "Estimate the budgetary impact of tax and spending proposals. "
            "Policies benchmarked against CBO/JCT/Treasury scores."
        )
    st_module.markdown(
        f"""
        <meta name="description" content="{_blurb}">
        <meta property="og:title" content="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring">
        <meta property="og:description" content="{_blurb}">
        <meta property="og:type" content="website">
        <meta name="twitter:card" content="summary">
        <meta name="twitter:title" content="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring">
        <meta name="twitter:description" content="{_blurb}">
        """,
        unsafe_allow_html=True,
    )


def _default_deps_builder(*, pd_module):
    from fiscal_model.ui.dependencies import build_app_dependencies

    return build_app_dependencies(pd_module=pd_module)


def _default_classroom_renderer() -> None:
    from app_pages import classroom

    classroom.render()


def _apply_legacy_url_shim(st_module: Any) -> None:
    """Hook for Phase 5 — rewrite legacy query-param URLs onto the new routes.

    Runs on every request **before** ``nav.run()`` so a redirect happens before
    any page body renders. Intentionally a no-op today; Phase 5 fills it in
    together with the ``preset_id`` registry.

    What it will need to handle:

    - ``/?analysis=preset&preset=<label>&dynamic=1&run=1`` -> ``/explore?...``
      (the shape ``ui/share_links.apply_share_query_params`` still reads);
    - ``/?analysis=custom|spending`` -> ``/tailor``;
    - ``/?tab=ask`` (written by ``assistant/share.py``) -> ``/``;
    - ``/ask`` -> ``/`` (Streamlit forces the default page's ``url_path`` to
      ``""``, so the pathname the wireframe's URL contract names is not
      registered and currently falls through to a "page not found" notice);
    - ``?mode=classroom`` is handled separately in :func:`main`, because it must
      keep working without the navigation frame (CI smoke-tests that URL).
    """
    del st_module


def _get_dependencies(st_module: Any, pd_module: Any, builder: Any) -> Any:
    """Build the ``AppDependencies`` bundle once per session and reuse it.

    Under ``st.tabs`` switching surfaces was a client-side operation; under
    ``st.navigation`` every page change is a full script rerun. Rebuilding the
    bundle each time would re-instantiate ``FiscalPolicyScorer`` and spawn a
    fresh Ask prompt-cache pre-warm thread on every click, so the bundle is
    cached in ``st.session_state`` (per browser session, like the object graph
    it holds) and shared by all pages in a run.
    """
    session_state = getattr(st_module, "session_state", None)
    if session_state is None:
        return builder(pd_module=pd_module)

    try:
        cached = session_state.get(_DEPS_SESSION_KEY)
    except Exception:  # pragma: no cover — exotic session_state stand-ins
        cached = None
    if cached is not None:
        return cached

    deps = builder(pd_module=pd_module)
    with contextlib.suppress(Exception):  # pragma: no cover — exotic stand-ins
        session_state[_DEPS_SESSION_KEY] = deps
    return deps


def _page_runner(
    st_module: Any,
    deps: Any,
    app_root: Path | None,
    section_label: str,
    render_fn: Any,
) -> Any:
    """Wrap a page renderer in the shared error boundary.

    A page body that raises shows a contained error instead of a blank app;
    the navigation bar is rendered by Streamlit itself and survives regardless.
    """
    from fiscal_model.ui.app_controller import _render_guarded_section

    def _run() -> None:
        _render_guarded_section(
            st_module,
            section_label,
            lambda: render_fn(st_module=st_module, deps=deps, app_root=app_root),
        )

    return _run


def _is_admin_request(st_module: Any) -> bool:
    """Mirror the old conditional-Admin-tab gate."""
    try:
        from fiscal_model.assistant.admin import is_admin_request
    except Exception:  # pragma: no cover — defensive
        return False

    try:
        query_params = st_module.query_params
    except AttributeError:  # older Streamlit
        try:
            query_params = st_module.experimental_get_query_params()
        except Exception:
            query_params = {}
    try:
        return bool(is_admin_request(query_params))
    except Exception:  # pragma: no cover — defensive
        return False


def build_navigation(st_module: Any, deps: Any, app_root: Path | None) -> Any:
    """Register every page and return the selected ``StreamlitPage``.

    Ask is the default page, so it answers ``/``. Tracker, Methodology,
    Classroom and Package Studio sit under a "More" section; Admin is only
    registered when the request carries a matching ``?admin=`` token.
    """
    from app_pages import (
        admin,
        ask,
        build,
        classroom,
        explore,
        methodology,
        studio,
        tailor,
        tracker,
    )

    def _page(module: Any, *, default: bool = False) -> Any:
        return st_module.Page(
            _page_runner(st_module, deps, app_root, module.PAGE_TITLE, module.render),
            title=module.PAGE_TITLE,
            url_path=module.URL_PATH,
            default=default,
        )

    primary = [
        _page(ask, default=True),
        _page(build),
        _page(tailor),
        _page(explore),
    ]
    more = [
        _page(tracker),
        _page(methodology),
        _page(classroom),
        # Temporary home for #65; Phase 3b folds it into Build.
        _page(studio),
    ]
    if _is_admin_request(st_module):
        more.append(_page(admin))

    return st_module.navigation({"": primary, "More": more}, position="top")


def main(
    *,
    st_module=st,
    pd_module=pd,
    app_root: Path | None = None,
    deps_builder=None,
    classroom_renderer=None,
) -> None:
    """Bootstrap the Streamlit router in a testable, import-safe wrapper."""
    logger = configure_runtime_logger(__name__)
    route_mode = getattr(st_module, "query_params", {}).get("mode", "")
    metadata = build_runtime_metadata(entrypoint="app.py", mode=route_mode or "calculator")
    log_runtime_event(logger, "app_boot", **metadata)

    _render_head_metadata(st_module)

    # ``?mode=classroom`` predates the router and is linked from the app copy,
    # the README and the CI smoke check (``scripts/check_streamlit_boot.py``).
    # Keep it as an alias that renders Classroom directly — no navigation
    # frame, exactly as it behaves today. ``/classroom`` is the new canonical
    # route and does the same thing from inside the nav.
    if route_mode == "classroom":
        renderer = classroom_renderer or _default_classroom_renderer
        try:
            log_runtime_event(logger, "app_route", route="classroom")
            renderer()
        except Exception:
            logger.exception("Classroom mode bootstrap failed")
            st_module.error(
                "⚠️ Classroom mode failed to start. Please reload the page or check the deployment logs."
            )
        return

    builder = deps_builder or _default_deps_builder
    app_root = app_root or Path(__file__).parent

    try:
        deps = _get_dependencies(st_module, pd_module, builder)
    except ImportError as exc:
        logger.exception("App dependency import failed")
        st_module.error(f"⚠️ Could not import fiscal model: {exc}")
        return

    try:
        deps.apply_app_styles(st_module)
        nav = build_navigation(st_module=st_module, deps=deps, app_root=app_root)
        _apply_legacy_url_shim(st_module)
        nav.run()
    except Exception:
        logger.exception("App bootstrap failed")
        st_module.error(
            "⚠️ The app failed to start. Please reload the page or check the deployment logs."
        )


if __name__ == "__main__":
    main()
