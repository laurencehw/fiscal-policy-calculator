"""
Structural tests for the multipage scaffold.

Guards the three things the navigation redesign can silently break:

1. every page module still imports and exposes ``render``;
2. the router still registers exactly the expected URL paths, with Ask default;
3. the global sidebar stays gone.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import app

REPO_ROOT = Path(__file__).resolve().parent.parent

# url_path -> module name. Admin is registered conditionally and tested apart.
EXPECTED_PAGES: dict[str, str] = {
    "ask": "ask",
    "build": "build",
    "tailor": "tailor",
    "explore": "explore",
    "tracker": "tracker",
    "methodology": "methodology",
    "classroom": "classroom",
    "about": "about",
}

ALL_PAGE_MODULES = [*EXPECTED_PAGES.values(), "admin"]


# ---------------------------------------------------------------------------
# Page modules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_name", ALL_PAGE_MODULES)
def test_page_module_imports_and_exposes_render(module_name: str):
    module = importlib.import_module(f"app_pages.{module_name}")
    assert callable(module.render), f"app_pages.{module_name}.render must be callable"
    assert isinstance(module.PAGE_TITLE, str) and module.PAGE_TITLE
    assert isinstance(module.URL_PATH, str) and module.URL_PATH


@pytest.mark.parametrize(("url_path", "module_name"), sorted(EXPECTED_PAGES.items()))
def test_page_module_url_path_matches_the_router(url_path: str, module_name: str):
    module = importlib.import_module(f"app_pages.{module_name}")
    assert module.URL_PATH == url_path


def test_page_package_is_not_named_pages():
    """A ``pages/`` directory would hand navigation back to legacy Streamlit.

    ``PagesManager.uses_pages_directory`` is latched at process start, before
    ``app.py`` runs, and the script runner then builds its own sidebar nav from
    ``pages/*.py`` instead of executing our ``st.navigation`` router.
    """
    assert (REPO_ROOT / "app_pages").is_dir()
    assert not (REPO_ROOT / "pages").exists(), (
        "A top-level pages/ directory re-enables legacy multipage navigation; "
        "the page package must stay app_pages/."
    )


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


class _FakePage:
    def __init__(self, run_fn, *, title=None, url_path=None, default=False, **kwargs):
        self.run_fn = run_fn
        self.title = title
        self.url_path = url_path
        self.default = default
        self.extra = kwargs


class _FakeNav:
    def __init__(self, sections, position):
        self.sections = sections
        self.position = position

    def run(self) -> None:
        return None


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _RouterStreamlit:
    def __init__(self, query_params=None) -> None:
        self.query_params = query_params or {}
        self.session_state = _SessionState()
        self.pages: list[_FakePage] = []
        self.nav: _FakeNav | None = None
        self.errors: list[str] = []
        self.markdowns: list[str] = []

    def set_page_config(self, **kwargs):
        return None

    def markdown(self, text, *args, **kwargs):
        del args, kwargs
        self.markdowns.append(text)

    def error(self, message):
        self.errors.append(message)

    def Page(self, page, **kwargs):  # Streamlit API name
        created = _FakePage(page, **kwargs)
        self.pages.append(created)
        return created

    def navigation(self, pages, *, position="sidebar", **kwargs):
        del kwargs
        self.nav = _FakeNav(pages, position)
        return self.nav


def _build_router(query_params=None) -> _RouterStreamlit:
    st_module = _RouterStreamlit(query_params=query_params)
    deps = SimpleNamespace(apply_app_styles=lambda st: None)
    app.main(st_module=st_module, pd_module=object(), deps_builder=lambda **kw: deps)
    return st_module


def test_router_registers_exactly_the_expected_url_paths():
    st_module = _build_router()
    assert {page.url_path for page in st_module.pages} == set(EXPECTED_PAGES)


def test_router_uses_top_navigation():
    assert _build_router().nav.position == "top"


def test_router_groups_secondary_surfaces_under_more():
    sections = _build_router().nav.sections
    assert set(sections) == {"", "More"}
    assert {page.url_path for page in sections["More"]} == {
        "tracker",
        "methodology",
        "classroom",
        "about",
    }


def test_ask_is_the_only_default_page():
    st_module = _build_router()
    defaults = [page.url_path for page in st_module.pages if page.default]
    assert defaults == ["ask"]


def test_every_registered_page_is_runnable():
    """Each registered page is a zero-argument callable wrapped in a guard."""
    st_module = _build_router()
    for page in st_module.pages:
        assert callable(page.run_fn)


def test_legacy_url_shim_leaves_a_plain_request_alone():
    """A URL with nothing legacy in it must pass through untouched.

    The shim's rewriting behaviour lives in ``tests/test_routing_shim.py``;
    this only guards the router's contract with it — it is called on *every*
    request, so it has to be inert and non-throwing on the common path.
    """
    st_module = _RouterStreamlit()
    assert app._apply_legacy_url_shim(st_module) is None
    assert st_module.query_params == {}


# ---------------------------------------------------------------------------
# No global sidebar
# ---------------------------------------------------------------------------

_SIDEBAR_CALL = re.compile(r"\b(?:st|st_module)\s*\.\s*sidebar\b")

# Surfaces allowed to render a sidebar deliberately. Classroom Mode is a
# self-contained teaching app with its own assignment picker.
_SIDEBAR_ALLOWLIST = {Path("classroom_app.py")}


def _python_sources(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _code_without_comments(path: Path) -> str:
    """Source with ``#`` comments stripped.

    The redesign left explanatory comments that mention the removed
    ``with st.sidebar`` block; those are history, not usage.
    """
    return "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())


def test_no_sidebar_usage_remains_in_ui_package():
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in _python_sources(REPO_ROOT / "fiscal_model" / "ui")
        if _SIDEBAR_CALL.search(_code_without_comments(path))
    ]
    assert offenders == [], (
        "The global sidebar was removed in the ask-first redesign; "
        f"sidebar usage reappeared in: {offenders}"
    )


def test_no_sidebar_usage_in_pages_or_chrome():
    offenders = []
    for root in (REPO_ROOT / "app_pages", REPO_ROOT / "components"):
        offenders += [
            str(path.relative_to(REPO_ROOT))
            for path in _python_sources(root)
            if _SIDEBAR_CALL.search(_code_without_comments(path))
        ]
    assert offenders == []


def test_classroom_is_the_only_deliberate_sidebar():
    """Documents the one intentional exception so it cannot spread silently."""
    assert _SIDEBAR_CALL.search(_code_without_comments(REPO_ROOT / "classroom_app.py"))
    assert Path("classroom_app.py") in _SIDEBAR_ALLOWLIST
