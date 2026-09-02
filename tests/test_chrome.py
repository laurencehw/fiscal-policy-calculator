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

# Degraded for reasons that say nothing about how current the numbers are:
# microdata coverage against SOI, and the local Python version. Every *data
# vintage* here is inside its own release calendar — SOI's three-year lag is
# the publication lag, not lateness (``is_stale`` is False).
_HEALTH_CAVEATS_ONLY = {
    "baseline": {
        "status": "ok",
        "vintage": "February 2026",
        "source": "real_data",
        "freshness": {"level": "fresh", "is_stale": False},
    },
    "irs_soi": {
        "status": "ok",
        "latest_year": 2023,
        "freshness": {"level": "aging", "is_stale": False, "message": "lag 3y"},
    },
    "fred": {"status": "ok", "source": "live", "cache_is_expired": False},
    "microdata": {"status": "degraded", "coverage_overcount": True},
    "runtime": {
        "status": "degraded",
        "python_version": "3.14.0",
        "message": "Python 3.14.0 is outside supported range",
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


def _notices(st_module) -> list[str]:
    """Every page-level degraded/error notice the chrome drew."""
    return [
        text
        for text in st_module.expanders + st_module.warnings + st_module.errors
        if "refresh window" in text or "older snapshots" in text or "Data error" in text
    ]


def test_chrome_renders_the_degraded_banner_exactly_once(monkeypatch):
    st_module, _ = _render(monkeypatch, _HEALTH_DEGRADED)
    # Since 2026-09-01 the non-error notice is a collapsed expander (quieter,
    # per the owner) rather than an st.warning box.
    assert _notices(st_module) == [chrome.DEGRADED_NOTICE_LABEL]
    # …and as an expander, not a full-width st.warning box.
    assert not [w for w in st_module.warnings if "refresh window" in w]


def test_chrome_shows_no_banner_when_data_is_healthy(monkeypatch):
    st_module, _ = _render(monkeypatch, _HEALTH_OK)
    assert _notices(st_module) == []
    assert st_module.errors == []


# ---------------------------------------------------------------------------
# Degraded-notice calibration (external UI review, 2026-09-01)
# ---------------------------------------------------------------------------


def test_caveats_alone_do_not_raise_a_page_level_notice(monkeypatch):
    """Microdata coverage and a stray interpreter version are not staleness.

    The reviewer's complaint was that the app announced "some data sources are
    running on older snapshots" on a deployment whose every vintage was
    current. Those two conditions are the ones that fired.
    """
    st_module, _ = _render(monkeypatch, _HEALTH_CAVEATS_ONLY)
    assert chrome._sources_past_tolerance(_HEALTH_CAVEATS_ONLY) == []
    assert _notices(st_module) == []


@pytest.mark.parametrize(
    ("health", "expected"),
    [
        pytest.param(
            {"baseline": {"source": "hardcoded_fallback"}}, ["baseline"], id="fallback"
        ),
        pytest.param(
            {"baseline": {"freshness": {"is_stale": True}}}, ["baseline"], id="stale"
        ),
        pytest.param({"fred": {"source": "fallback"}}, ["fred"], id="fred-fallback"),
        pytest.param(
            {"fred": {"source": "bundled", "cache_is_expired": True}},
            ["fred"],
            id="fred-expired",
        ),
        pytest.param(
            {"fred": {"source": "bundled", "cache_is_expired": False}},
            [],
            id="fred-bundled-fresh",
        ),
        # An expired on-disk *cache* is late in the same way an expired bundled
        # snapshot is, and ``summarize_data_degradation`` now writes a reason
        # line for it, so the headline and the reasons agree.
        pytest.param(
            {"fred": {"source": "cache", "cache_is_expired": True}},
            ["fred"],
            id="fred-expired-cache",
        ),
        pytest.param(
            {"fred": {"source": "cache", "cache_is_expired": False}},
            [],
            id="fred-cache-fresh",
        ),
        pytest.param(
            {"irs_soi": {"freshness": {"level": "aging", "is_stale": False}}},
            [],
            id="soi-publication-lag",
        ),
        pytest.param(
            {"irs_soi": {"freshness": {"is_stale": True}}}, ["irs_soi"], id="soi-stale"
        ),
        pytest.param({"microdata": {"status": "degraded"}}, [], id="microdata-caveat"),
        pytest.param({"runtime": {"status": "degraded"}}, [], id="runtime-caveat"),
        pytest.param({}, [], id="empty"),
    ],
)
def test_sources_past_tolerance(health, expected):
    assert chrome._sources_past_tolerance(health) == expected


def test_quiet_notice_is_shown_once_per_session(monkeypatch):
    """Every nav click is a full rerun; the notice must not re-fire each time."""
    monkeypatch.setattr(chrome, "get_health_snapshot", lambda: _HEALTH_DEGRADED)
    monkeypatch.setattr(chrome, "render_data_status", lambda **kwargs: None)
    st_module = _ChromeStreamlit()

    chrome.render_chrome(st_module=st_module, deps=SimpleNamespace())
    assert _notices(st_module) == [chrome.DEGRADED_NOTICE_LABEL]

    # Second page in the same session (session_state persists).
    chrome.render_chrome(st_module=st_module, deps=SimpleNamespace())
    assert _notices(st_module) == [chrome.DEGRADED_NOTICE_LABEL]


def test_a_data_error_still_interrupts_every_page(monkeypatch):
    """Errors are not rationed: a component that failed to load repeats."""
    errored = {**_HEALTH_OK, "fred": {"status": "error"}}
    monkeypatch.setattr(chrome, "get_health_snapshot", lambda: errored)
    monkeypatch.setattr(chrome, "render_data_status", lambda **kwargs: None)
    st_module = _ChromeStreamlit()

    chrome.render_chrome(st_module=st_module, deps=SimpleNamespace())
    chrome.render_chrome(st_module=st_module, deps=SimpleNamespace())
    assert len([e for e in st_module.errors if "Data error" in e]) == 2


# ---------------------------------------------------------------------------
# Cold start (external UI review, 2026-09-01)
# ---------------------------------------------------------------------------


def test_the_brand_paints_before_the_health_probe_runs(monkeypatch):
    """Order matters: Streamlit streams elements as they are created.

    ``get_health_snapshot`` costs ~2-3s on a container's first request and
    every later run is a memo hit. Computing it before the title meant the
    whole of that showed as a blank page. Nothing above the pill needs the
    payload, so the title must already be on the wire when the probe starts.
    """
    order: list[str] = []

    def _probe():
        order.append("health")
        return _HEALTH_OK

    monkeypatch.setattr(chrome, "get_health_snapshot", _probe)
    monkeypatch.setattr(chrome, "render_data_status", lambda **kwargs: None)

    st_module = _ChromeStreamlit()
    original_markdown = st_module.markdown

    def _record(text="", *args, **kwargs):
        if str(text).startswith("### "):
            order.append("brand")
        return original_markdown(text, *args, **kwargs)

    st_module.markdown = _record
    chrome.render_chrome(st_module=st_module, deps=SimpleNamespace())

    assert order[:2] == ["brand", "health"], order


def test_notice_label_names_the_number_of_late_sources(monkeypatch):
    both_late = {
        **_HEALTH_OK,
        "baseline": {"status": "degraded", "source": "hardcoded_fallback"},
        "fred": {"status": "degraded", "source": "fallback"},
    }
    st_module, _ = _render(monkeypatch, both_late)
    assert _notices(st_module) == ["🟡 2 data sources are past their refresh window — details"]


def test_chrome_seeds_session_state_defaults(monkeypatch):
    from fiscal_model.ui.session_state import ALL_KEYS

    st_module, _ = _render(monkeypatch, _HEALTH_OK)
    missing = [key for key in ALL_KEYS if key not in st_module.session_state]
    assert missing == []
