"""
Smoke tests for the top-level Streamlit router (``app.py``).

``app.py`` is an ``st.navigation`` router: it sets the page config once,
registers every surface as an ``st.Page``, runs the Phase-5 legacy-URL shim,
and then runs the selected page. These tests drive it with a hand-rolled fake
``st`` module — the same dependency-injection style the rest of the UI suite
uses — so nothing here needs a live Streamlit server.
"""

from __future__ import annotations

from types import SimpleNamespace

import app
import classroom_app


class _FakePage:
    """Stand-in for ``streamlit.navigation.page.StreamlitPage``."""

    def __init__(self, run_fn, *, title=None, url_path=None, default=False, **kwargs):
        self.run_fn = run_fn
        self.title = title
        self.url_path = url_path
        self.default = default
        self.extra = kwargs
        self.ran = False

    def run(self) -> None:
        self.ran = True
        self.run_fn()


class _FakeNavigation:
    def __init__(self, sections, position):
        self.sections = sections
        self.position = position
        self.ran = False

    def run(self) -> None:
        self.ran = True


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _DummyStreamlit:
    def __init__(self, query_params=None) -> None:
        self.query_params = query_params or {}
        self.session_state = _SessionState()
        self.errors: list[str] = []
        self.page_config_calls: list[dict[str, object]] = []
        self.markdown_calls: list[str] = []
        self.pages: list[_FakePage] = []
        self.navigation_calls: list[_FakeNavigation] = []

    # -- page config / output ------------------------------------------------
    def set_page_config(self, **kwargs):
        self.page_config_calls.append(kwargs)

    def markdown(self, text, *args, **kwargs):
        del args, kwargs
        self.markdown_calls.append(text)

    def error(self, message):
        self.errors.append(message)

    # -- navigation ----------------------------------------------------------
    def Page(self, page, **kwargs):  # Streamlit API name
        created = _FakePage(page, **kwargs)
        self.pages.append(created)
        return created

    def navigation(self, pages, *, position="sidebar", **kwargs):
        del kwargs
        nav = _FakeNavigation(pages, position)
        self.navigation_calls.append(nav)
        return nav

    # -- convenience ---------------------------------------------------------
    @property
    def page_map(self) -> dict[str, _FakePage]:
        return {page.url_path: page for page in self.pages}


def _fake_deps(**overrides) -> SimpleNamespace:
    base = {
        "apply_app_styles": lambda st: None,
        "PRESET_POLICIES": {},
        "CBO_SCORE_MAP": {},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------


def test_set_page_config_called_exactly_once():
    st_module = _DummyStreamlit()
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    assert len(st_module.page_config_calls) == 1
    config = st_module.page_config_calls[0]
    assert config["layout"] == "wide"
    assert "Fiscal Policy Impact Calculator" in config["page_title"]


def test_head_metadata_emits_open_graph_tags():
    st_module = _DummyStreamlit()
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    assert any('property="og:title"' in text for text in st_module.markdown_calls)


# ---------------------------------------------------------------------------
# Page registration
# ---------------------------------------------------------------------------

EXPECTED_PRIMARY_PATHS = ["ask", "build", "tailor", "explore"]
# Package Studio was registered here in Phase 1 and retired in Phase 3b: it
# is now Build's "Start from your values" panel (DECISIONS.md #3).
EXPECTED_MORE_PATHS = ["tracker", "methodology", "classroom", "about"]


def test_router_registers_expected_pages_with_ask_default():
    st_module = _DummyStreamlit()
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    nav = st_module.navigation_calls[0]
    assert nav.position == "top"

    primary = [page.url_path for page in nav.sections[""]]
    more = [page.url_path for page in nav.sections["More"]]
    assert primary == EXPECTED_PRIMARY_PATHS
    assert more == EXPECTED_MORE_PATHS

    defaults = [page.url_path for page in st_module.pages if page.default]
    assert defaults == ["ask"], "Ask must be the one and only default page"


def test_router_page_titles_match_the_wireframe_nav():
    st_module = _DummyStreamlit()
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    titles = {page.url_path: page.title for page in st_module.pages}
    assert titles["ask"] == "Ask"
    assert titles["build"] == "Build"
    assert titles["tailor"] == "Tailor"
    assert titles["explore"] == "Explore"
    assert titles["classroom"] == "Classroom"
    assert titles["about"] == "About"


def test_admin_page_hidden_without_matching_token(monkeypatch):
    monkeypatch.setattr(app, "_is_admin_request", lambda st_module: False)
    st_module = _DummyStreamlit()
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    assert "admin" not in st_module.page_map


def test_admin_page_registered_when_token_matches(monkeypatch):
    monkeypatch.setattr(app, "_is_admin_request", lambda st_module: True)
    st_module = _DummyStreamlit()
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    assert "admin" in st_module.page_map
    assert st_module.page_map["admin"] in st_module.navigation_calls[0].sections["More"]


def test_navigation_is_run_after_the_legacy_url_shim(monkeypatch):
    order: list[str] = []
    monkeypatch.setattr(app, "_apply_legacy_url_shim", lambda st_module: order.append("shim"))

    st_module = _DummyStreamlit()

    class _RecordingNav(_FakeNavigation):
        def run(self):
            order.append("nav.run")
            super().run()

    def _navigation(pages, *, position="sidebar", **kwargs):
        del kwargs
        nav = _RecordingNav(pages, position)
        st_module.navigation_calls.append(nav)
        return nav

    st_module.navigation = _navigation
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: _fake_deps())

    assert order == ["shim", "nav.run"]


# ---------------------------------------------------------------------------
# Dependency wiring
# ---------------------------------------------------------------------------


def test_dependencies_are_built_once_per_session_and_shared():
    st_module = _DummyStreamlit()
    builds = {"n": 0}

    def _builder(**kwargs):
        del kwargs
        builds["n"] += 1
        return _fake_deps()

    app.main(st_module=st_module, pd_module=object(), deps_builder=_builder)
    app.main(st_module=st_module, pd_module=object(), deps_builder=_builder)

    assert builds["n"] == 1, "page navigation must not rebuild the dependency bundle"
    assert app._DEPS_SESSION_KEY in st_module.session_state


def test_app_styles_applied_before_navigation():
    st_module = _DummyStreamlit()
    calls: list[str] = []
    deps = _fake_deps(apply_app_styles=lambda st: calls.append("styles"))

    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: deps)

    assert calls == ["styles"]
    assert st_module.navigation_calls[0].ran is True


def test_app_main_surfaces_dependency_import_errors():
    st_module = _DummyStreamlit()

    app.main(
        st_module=st_module,
        pd_module=object(),
        deps_builder=lambda **kwargs: (_ for _ in ()).throw(ImportError("missing dependency")),
    )

    assert len(st_module.errors) == 1
    assert "Could not import fiscal model" in st_module.errors[0]
    assert st_module.navigation_calls == []


# ---------------------------------------------------------------------------
# ?mode=classroom back-compat alias
# ---------------------------------------------------------------------------


def test_app_main_routes_to_classroom_mode():
    st_module = _DummyStreamlit(query_params={"mode": "classroom"})
    calls = {"classroom": 0}

    app.main(
        st_module=st_module,
        pd_module=object(),
        deps_builder=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("deps builder should not run for the classroom alias")
        ),
        classroom_renderer=lambda: calls.__setitem__("classroom", calls["classroom"] + 1),
    )

    assert calls["classroom"] == 1
    assert st_module.errors == []
    # The alias predates the router but must still set the page config exactly
    # once — classroom_app no longer sets its own when embedded.
    assert len(st_module.page_config_calls) == 1
    assert st_module.navigation_calls == []


def test_classroom_alias_failure_is_contained():
    st_module = _DummyStreamlit(query_params={"mode": "classroom"})

    def _boom():
        raise RuntimeError("classroom broke")

    app.main(
        st_module=st_module,
        pd_module=object(),
        deps_builder=lambda **kwargs: _fake_deps(),
        classroom_renderer=_boom,
    )

    assert len(st_module.errors) == 1
    assert "Classroom mode failed to start" in st_module.errors[0]


def test_classroom_page_renders_the_same_body(monkeypatch):
    from app_pages import classroom as classroom_page

    calls = {"rendered": 0}
    monkeypatch.setattr(
        classroom_app,
        "render_classroom_app",
        lambda: calls.__setitem__("rendered", calls["rendered"] + 1),
    )

    classroom_page.render()

    assert calls["rendered"] == 1


def test_classroom_app_main_invokes_renderer(monkeypatch):
    calls = {"rendered": 0}
    monkeypatch.setattr(
        classroom_app,
        "render_classroom_app",
        lambda: calls.__setitem__("rendered", calls["rendered"] + 1),
    )

    classroom_app.main()

    assert calls["rendered"] == 1
