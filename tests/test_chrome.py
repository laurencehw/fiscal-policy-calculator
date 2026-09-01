"""
Tests for the shared page chrome that replaced the global sidebar.

Covers the two things that must not regress when the sidebar goes away:
the data-status pill/popover, and the settings panel that pages read their
model configuration from.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from components import chrome
from fiscal_model.ui.app_controller import _short_vintage, data_status_pill


class _Ctx:
    def __init__(self, recorder=None, label=None):
        self.recorder = recorder
        self.label = label

    def __enter__(self):
        if self.recorder is not None:
            self.recorder.append(self.label)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _ChromeStreamlit:
    """Minimal ``st`` stand-in that records what the chrome renders."""

    def __init__(self) -> None:
        self.session_state = _SessionState()
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.popovers: list[str] = []
        self.expanders: list[str] = []

    def markdown(self, text="", *args, **kwargs):
        del args, kwargs
        self.markdowns.append(text)

    def caption(self, text="", *args, **kwargs):
        del args, kwargs
        self.captions.append(text)

    def warning(self, text, *args, **kwargs):
        del args, kwargs
        self.warnings.append(text)

    def error(self, text, *args, **kwargs):
        del args, kwargs
        self.errors.append(text)

    def columns(self, spec, **kwargs):
        del kwargs
        n = spec if isinstance(spec, int) else len(spec)
        return [_Ctx() for _ in range(n)]

    def container(self, *args, **kwargs):
        del args, kwargs
        return _Ctx()

    def popover(self, label, **kwargs):
        del kwargs
        self.popovers.append(label)
        return _Ctx()

    def expander(self, label, **kwargs):
        del kwargs
        self.expanders.append(label)
        return _Ctx()

    def checkbox(self, label, value=False, **kwargs):
        del label, kwargs
        return value

    def selectbox(self, label, options, index=0, **kwargs):
        del label, kwargs
        return list(options)[index]

    def rerun(self):
        return None


_HEALTH_OK = {
    "baseline": {"status": "ok", "vintage": "February 2026"},
    "irs_soi": {"status": "ok", "latest_year": 2023},
    "fred": {"status": "ok", "source": "live"},
    "runtime": {"status": "ok", "python_version": "3.12.0"},
}

_HEALTH_DEGRADED = {
    **_HEALTH_OK,
    "baseline": {
        "status": "degraded",
        "vintage": "February 2026",
        "freshness": {"is_stale": True, "message": "past its refresh window"},
    },
}


# ---------------------------------------------------------------------------
# Pill
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("February 2026", "Feb 2026"),
        ("September 2024", "Sep 2024"),
        ("", "unknown"),
        (None, "unknown"),
        ("FY2026 update", "FY2026 update"),
    ],
)
def test_short_vintage(raw, expected):
    assert _short_vintage(raw) == expected


def test_pill_label_matches_the_wireframe():
    pill = data_status_pill(_HEALTH_OK)
    assert pill["label"] == "CBO Feb 2026 · SOI 2023"
    assert pill["dot"] == "🟢"
    assert pill["severity"] == "ok"


def test_pill_dot_reflects_the_worst_component():
    assert data_status_pill(_HEALTH_DEGRADED)["dot"] == "🟡"
    errored = {**_HEALTH_OK, "fred": {"status": "error"}}
    assert data_status_pill(errored)["dot"] == "🔴"


def test_pill_survives_an_empty_health_payload():
    pill = data_status_pill({})
    assert "CBO unknown" in pill["label"]
    assert "SOI unavailable" in pill["label"]


# ---------------------------------------------------------------------------
# render_chrome
# ---------------------------------------------------------------------------


def _render(monkeypatch, health):
    monkeypatch.setattr(chrome, "get_health_snapshot", lambda: health)
    monkeypatch.setattr(
        chrome,
        "render_data_status",
        lambda **kwargs: kwargs["st_module"].markdown("**📊 Data Status**"),
    )
    st_module = _ChromeStreamlit()
    settings = chrome.render_chrome(st_module=st_module, deps=SimpleNamespace())
    return st_module, settings


def test_chrome_renders_the_status_pill_as_a_popover(monkeypatch):
    st_module, _ = _render(monkeypatch, _HEALTH_OK)
    assert any("CBO Feb 2026 · SOI 2023" in label for label in st_module.popovers)


def test_chrome_returns_the_model_settings_dict(monkeypatch):
    _, settings = _render(monkeypatch, _HEALTH_OK)
    for key in (
        "use_real_data",
        "dynamic_scoring",
        "use_microsim",
        "use_microsim_distribution",
        "data_year",
        "dark_mode",
    ):
        assert key in settings


def test_chrome_renders_the_degraded_banner_exactly_once(monkeypatch):
    st_module, _ = _render(monkeypatch, _HEALTH_DEGRADED)
    banners = [w for w in st_module.warnings if "older snapshots" in w]
    assert len(banners) == 1


def test_chrome_shows_no_banner_when_data_is_healthy(monkeypatch):
    st_module, _ = _render(monkeypatch, _HEALTH_OK)
    assert not [w for w in st_module.warnings if "older snapshots" in w]
    assert st_module.errors == []


def test_chrome_seeds_session_state_defaults(monkeypatch):
    from fiscal_model.ui.session_state import ALL_KEYS

    st_module, _ = _render(monkeypatch, _HEALTH_OK)
    missing = [key for key in ALL_KEYS if key not in st_module.session_state]
    assert missing == []
