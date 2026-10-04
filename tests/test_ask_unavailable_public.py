"""The keyless Ask page must not show deployer diagnostics to the public.

Defect (2026-10 hunt): with no ``ANTHROPIC_API_KEY`` the Ask page rendered,
to every visitor, a "Diagnostic — what was checked" expander (open by
default) listing whether ``st.secrets`` was accessible and the *names of
every top-level secret* the deployment holds (or "(error enumerating
keys)"), plus a "How to set the key" expander of operator instructions.

Now the public sees one short sentence; the setup help and the diagnostic
render only behind the admin-dashboard gate (``?admin=<token>`` matching
``ASSISTANT_ADMIN_TOKEN``) or the ``ASSISTANT_SHOW_SETUP`` env flag.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest

from fiscal_model.ui.tabs import ask_assistant as page


class _Secrets(dict):
    """Dict-like stand-in for ``st.secrets`` (iterable, ``[]`` raises)."""


class _FakeSt:
    def __init__(self, *, secrets: Any = None, query_params: dict | None = None) -> None:
        self.session_state: dict[str, Any] = {}
        self.secrets = secrets
        self.query_params = query_params or {}
        self.out: list[tuple[str, str]] = []

    def _log(self, kind: str, body: Any = "") -> None:
        self.out.append((kind, str(body)))

    def info(self, body: Any, **_: Any) -> None:
        self._log("info", body)

    def markdown(self, body: Any, **_: Any) -> None:
        self._log("markdown", body)

    def error(self, body: Any, **_: Any) -> None:
        self._log("error", body)

    def caption(self, body: Any, **_: Any) -> None:
        self._log("caption", body)

    def expander(self, label: str, **_: Any) -> Any:
        self._log("expander", label)
        return contextlib.nullcontext()

    @property
    def text(self) -> str:
        return "\n".join(body for _, body in self.out)


class _NoKeyAssistant:
    def is_available(self) -> bool:
        return False


SECRET_NAMES = _Secrets({"ANTHROPC_API_KEY": "x", "DATABASE_URL": "postgres://..."})


@pytest.fixture(autouse=True)
def _no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASSISTANT_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv(page.SHOW_SETUP_ENV, raising=False)


def _render(st: _FakeSt) -> None:
    page._render_body(st, _NoKeyAssistant(), None, show_hero=False)


def test_public_keyless_page_shows_only_a_friendly_sentence() -> None:
    st = _FakeSt(secrets=SECRET_NAMES)
    _render(st)

    assert [kind for kind, _ in st.out] == ["info"]
    assert "Ask is not configured on this deployment" in st.text
    for leaked in (
        "st.secrets",
        "accessible",
        "enumerating",
        "ANTHROPC_API_KEY",
        "DATABASE_URL",
        "ANTHROPIC_API_KEY",
        "Diagnostic",
        "How to set the key",
        "sk-ant",
    ):
        assert leaked not in st.text, leaked


def test_public_page_hides_the_enumeration_error_marker() -> None:
    class _Broken(_Secrets):
        def __iter__(self):
            raise RuntimeError("no secrets file")

    st = _FakeSt(secrets=_Broken())
    _render(st)
    assert "(error enumerating keys)" not in st.text
    assert [kind for kind, _ in st.out] == ["info"]


def test_wrong_admin_token_is_still_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "s3cret")
    st = _FakeSt(secrets=SECRET_NAMES, query_params={"admin": "guess"})
    _render(st)
    assert "DATABASE_URL" not in st.text
    assert [kind for kind, _ in st.out] == ["info"]


def test_admin_token_reveals_setup_help_and_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "s3cret")
    st = _FakeSt(secrets=SECRET_NAMES, query_params={"admin": "s3cret"})
    _render(st)
    labels = [body for kind, body in st.out if kind == "expander"]
    assert "How to set the key" in labels
    assert any(label.startswith("Diagnostic") for label in labels)
    assert "`DATABASE_URL`" in st.text
    assert "Likely typo" in st.text  # ANTHROPC_API_KEY is one edit away


def test_env_flag_reveals_setup_help(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(page.SHOW_SETUP_ENV, "1")
    st = _FakeSt(secrets=SECRET_NAMES)
    _render(st)
    labels = [body for kind, body in st.out if kind == "expander"]
    assert "How to set the key" in labels
