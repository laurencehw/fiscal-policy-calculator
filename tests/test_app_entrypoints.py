"""
Smoke tests for top-level Streamlit entrypoints.
"""

from __future__ import annotations

from types import SimpleNamespace

import app
import classroom_app


class _DummyStreamlit:
    def __init__(self, query_params=None) -> None:
        self.query_params = query_params or {}
        self.errors: list[str] = []
        self.page_config_calls: list[dict[str, object]] = []
        self.markdown_calls: list[str] = []

    def set_page_config(self, **kwargs):
        self.page_config_calls.append(kwargs)

    def markdown(self, text, *args, **kwargs):
        del args, kwargs
        self.markdown_calls.append(text)

    def error(self, message):
        self.errors.append(message)


def test_app_main_routes_to_classroom_mode():
    st_module = _DummyStreamlit(query_params={"mode": "classroom"})
    calls = {"classroom": 0}

    app.main(
        st_module=st_module,
        pd_module=object(),
        deps_builder=lambda **kwargs: (_ for _ in ()).throw(AssertionError("calculator builder should not run")),
        classroom_renderer=lambda: calls.__setitem__("classroom", calls["classroom"] + 1),
    )

    assert calls["classroom"] == 1
    assert st_module.page_config_calls == []
    assert st_module.errors == []


def test_app_main_bootstraps_calculator_mode():
    st_module = _DummyStreamlit()
    calls = {"apply_styles": 0, "run_main_app": 0}

    deps = SimpleNamespace(
        apply_app_styles=lambda st: calls.__setitem__("apply_styles", calls["apply_styles"] + 1),
        run_main_app=lambda **kwargs: calls.__setitem__("run_main_app", calls["run_main_app"] + 1),
    )

    app.main(
        st_module=st_module,
        pd_module=object(),
        deps_builder=lambda **kwargs: deps,
    )

    assert len(st_module.page_config_calls) == 1
    assert calls["apply_styles"] == 1
    assert calls["run_main_app"] == 1
    assert st_module.errors == []


def test_app_main_surfaces_dependency_import_errors():
    st_module = _DummyStreamlit()

    app.main(
        st_module=st_module,
        pd_module=object(),
        deps_builder=lambda **kwargs: (_ for _ in ()).throw(ImportError("missing dependency")),
    )

    assert len(st_module.errors) == 1
    assert "Could not import fiscal model" in st_module.errors[0]


def test_classroom_app_main_invokes_renderer(monkeypatch):
    calls = {"rendered": 0}
    monkeypatch.setattr(
        classroom_app,
        "render_classroom_app",
        lambda: calls.__setitem__("rendered", calls["rendered"] + 1),
    )

    classroom_app.main()

    assert calls["rendered"] == 1
