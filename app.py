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
  /about           — About the project       (More)
  /admin           — Assistant admin         (only with a matching ?admin= token)
  /?mode=classroom — back-compat alias for /classroom

Query-param contract per page — ``/?q=``, ``/explore?preset=``,
``/tailor?type=``, ``/build?policies=`` — is documented in each page module and
implemented in ``fiscal_model/ui/share_links.py``.

Streamlit forces the default page's ``url_path`` to ``""``
(``StreamlitPage.url_path`` returns ``""`` when ``_default``), so ``/ask`` is
not a registered pathname and would draw a transient "page not found" notice
before falling back to the default page. :func:`_apply_legacy_url_shim`
canonicalises it — along with the pre-redesign ``?analysis=`` URLs and the
retired ``/studio`` — *before* ``st.navigation`` runs, which is where that
decision is made.
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
    _blurb = (
        "Estimate the budgetary impact of tax and spending proposals. "
        "Policies benchmarked against CBO/JCT/Treasury scores."
    )
    try:
        from fiscal_model.ui.helpers import validated_policy_count

        # 0 means the scorecard could not be computed. Say nothing about
        # coverage rather than print a number the scorecard cannot back.
        if (_n := validated_policy_count()) > 0:
            _blurb = (
                "Estimate the budgetary impact of tax and spending proposals. "
                f"{_n} policies benchmarked against CBO/JCT/Treasury scores."
            )
    except Exception:
        pass
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


#: Session key recording the page a legacy URL was rewritten onto. Read by
#: ``tests/test_routing_shim.py``; nothing in the app depends on it.
_LEGACY_ROUTE_KEY = "_legacy_route_target"

#: Pathnames that no longer exist and where they now live. ``ask`` maps to the
#: default page: Streamlit forces the default page's public ``url_path`` to
#: ``""`` (``StreamlitPage.url_path`` returns ``""`` when ``_default``), so
#: ``ask`` is not a registered pathname and ``st.navigation`` would enqueue a
#: "page not found" notice before falling back to Ask anyway.
_RETIRED_PATHNAMES: dict[str, str] = {"ask": "", "studio": "build"}


def _requested_page_name(st_module: Any) -> str | None:
    """The URL pathname this request asked for, e.g. ``"explore"``.

    ``None`` when there is no script-run context (unit tests with a fake ``st``
    module) or when the request addressed a page by *hash* rather than by name
    — in-app navigation clicks and ``AppTest.switch_page`` both do that, and
    neither is a URL the shim should second-guess.
    """
    del st_module
    ctx = _script_run_ctx()
    if ctx is None:
        return None
    if ctx.pages_manager.intended_page_script_hash:
        return None
    return ctx.pages_manager.intended_page_name or ""


def _script_run_ctx() -> Any:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
    except Exception:  # pragma: no cover — defensive
        return None
    return ctx if ctx is not None and getattr(ctx, "pages_manager", None) else None


def _request_page(st_module: Any, url_path: str) -> bool:
    """Point this run at ``url_path`` *before* ``st.navigation`` resolves it.

    ``st.navigation`` picks the page by matching the requested pathname against
    the registered ones, so rewriting the intent here redirects inside the same
    script run — no ``st.switch_page`` round trip, no flash of a "page not
    found" notice, and no second scoring pass. An empty ``url_path`` means "the
    default page" (Ask).
    """
    del st_module
    ctx = _script_run_ctx()
    if ctx is None:
        return False
    ctx.pages_manager.set_script_intent("", url_path)
    return True


def _studio_redirect_params() -> dict[str, str]:
    """``/studio`` -> the Build panel that replaced it, on its first archetype.

    Package Studio was a page between Phase 1 and Phase 3b and is now Build's
    "Start from your values" panel (DECISIONS.md #3), so a ``/studio`` link that
    got out should open that panel rather than 404.
    """
    try:
        from fiscal_model.composer.archetypes import archetype_ids

        first = next(iter(archetype_ids()), "")
    except Exception:  # pragma: no cover — archetypes YAML missing/broken
        return {}
    return {"values": first, "load": "1"} if first else {}


def _apply_legacy_url_shim(st_module: Any) -> None:
    """Rewrite pre-redesign URLs onto the new routes, before ``st.navigation``.

    Runs on every request **before** the router registers its pages, so the
    redirect resolves in the same script run and no page body renders twice.

    ============================================ ==============================
    Old URL                                      New route
    ============================================ ==============================
    ``/?analysis=preset&preset=<label>&run=1``   ``/explore?preset=<id>&run=1``
    ``/?policy=<label>&run=1``                   ``/explore?preset=<id>&run=1``
    ``/?analysis=spending&spending_preset=X``    ``/tailor?type=spending&…``
    ``/?analysis=custom``                        ``/tailor?type=income``
    ``/ask``, ``/ask?q=…``                       the default page (Ask)
    ``/studio``                                  ``/build?values=<archetype>``
    ============================================ ==============================

    The label→id translation and the ``?analysis=`` mapping live in
    ``ui/share_links.rewrite_legacy_query`` — a pure function, so the rewrite is
    unit-testable without a Streamlit runtime.

    Two URLs are deliberately *not* touched: ``?mode=classroom`` (handled in
    :func:`main` before the navigation frame exists — CI smoke-tests it) and
    ``/?ask_share=…&tab=ask``, which already lands on Ask because Ask is the
    default page.
    """
    from fiscal_model.ui.share_links import rewrite_legacy_query

    try:
        query_params = st_module.query_params
    except AttributeError:  # pragma: no cover — exotic test doubles
        return

    requested = _requested_page_name(st_module)
    rewritten = rewrite_legacy_query(query_params)

    if rewritten is None:
        if requested in _RETIRED_PATHNAMES:
            target = _RETIRED_PATHNAMES[requested]
            if requested == "studio":
                _merge_query_params(query_params, _studio_redirect_params())
            _request_page(st_module, target)
            _record_route(st_module, target)
        return

    url_path, new_params = rewritten
    _replace_query_params(query_params, new_params)
    _request_page(st_module, url_path)
    _record_route(st_module, url_path)


def _replace_query_params(query_params: Any, new_params: dict[str, str]) -> None:
    # pragma: no cover — the suppressed path is a read-only query-param stand-in
    with contextlib.suppress(Exception):
        query_params.clear()
        query_params.update(new_params)


def _merge_query_params(query_params: Any, extra: dict[str, str]) -> None:
    with contextlib.suppress(Exception):  # pragma: no cover — read-only stand-ins
        query_params.update(extra)


def _record_route(st_module: Any, url_path: str) -> None:
    """Note the rewrite for the tests and the runtime log; harmless otherwise."""
    with contextlib.suppress(Exception):
        st_module.session_state[_LEGACY_ROUTE_KEY] = url_path


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
    Classroom and About sit under a "More" section; Admin is only registered
    when the request carries a matching ``?admin=`` token.
    """
    from app_pages import (
        about,
        admin,
        ask,
        build,
        classroom,
        explore,
        methodology,
        tailor,
        tracker,
    )

    registry: dict[str, Any] = {}

    def _page(module: Any, *, default: bool = False) -> Any:
        page = st_module.Page(
            _page_runner(st_module, deps, app_root, module.PAGE_TITLE, module.render),
            title=module.PAGE_TITLE,
            url_path=module.URL_PATH,
            default=default,
        )
        registry[module.URL_PATH] = page
        return page

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
        _page(about),
    ]
    if _is_admin_request(st_module):
        more.append(_page(admin))

    # Page bodies link to each other through this registry — ``st.page_link``
    # cannot resolve a *path* for callable-registered pages. See
    # ``components.chrome.page_link``.
    _register_page_links(registry)

    return st_module.navigation({"": primary, "More": more}, position="top")


def _register_page_links(registry: dict[str, Any]) -> None:
    """Hand the registered pages to ``components.chrome`` for cross-links."""
    try:
        from components.chrome import register_pages

        register_pages(registry)
    except Exception:  # pragma: no cover — links degrade to Markdown fallbacks
        pass


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
        # Before the router registers its pages: ``st.navigation`` decides which
        # page runs (and whether to send a "page not found" notice) at call
        # time, so a legacy URL has to be rewritten ahead of it, not after.
        _apply_legacy_url_shim(st_module)
        nav = build_navigation(st_module=st_module, deps=deps, app_root=app_root)
        nav.run()
    except Exception:
        logger.exception("App bootstrap failed")
        st_module.error(
            "⚠️ The app failed to start. Please reload the page or check the deployment logs."
        )


if __name__ == "__main__":
    main()
