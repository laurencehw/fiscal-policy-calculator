"""Tests for the Streamlit session state schema."""

from __future__ import annotations

import pytest

from fiscal_model.ui.session_state import (
    ALL_KEYS,
    KEY_DARK_MODE,
    KEY_QUICK_START_DISMISSED,
    KEY_RESULTS,
    SafeSessionState,
    initialize_session_state,
)


class _FakeStreamlit:
    """Minimal stand-in for ``streamlit`` with attribute-style state."""

    class _State(dict):
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError as exc:
                raise AttributeError(key) from exc

        def __setattr__(self, key, value):
            self[key] = value

    def __init__(self):
        self.session_state = self._State()


def test_initialize_populates_defaults():
    st = _FakeStreamlit()
    initialize_session_state(st)
    for key in ALL_KEYS:
        assert key in st.session_state, f"missing key: {key}"
    assert st.session_state[KEY_DARK_MODE] is False
    assert st.session_state[KEY_QUICK_START_DISMISSED] is False
    assert st.session_state[KEY_RESULTS] is None


def test_initialize_preserves_existing_values():
    st = _FakeStreamlit()
    st.session_state[KEY_RESULTS] = {"already": "present"}
    st.session_state[KEY_DARK_MODE] = True
    initialize_session_state(st)
    assert st.session_state[KEY_RESULTS] == {"already": "present"}
    assert st.session_state[KEY_DARK_MODE] is True


def test_initialize_idempotent():
    st = _FakeStreamlit()
    initialize_session_state(st)
    before = dict(st.session_state)
    initialize_session_state(st)
    assert dict(st.session_state) == before


def test_safe_session_state_reads_defaults():
    st = _FakeStreamlit()
    initialize_session_state(st)
    safe = SafeSessionState(_state=st.session_state)
    assert safe.results is None
    assert safe.dark_mode is False
    assert safe.quick_start_dismissed is False
    assert safe.effective_run_id is None


def test_safe_session_state_effective_run_id_prefers_results():
    st = _FakeStreamlit()
    initialize_session_state(st)
    safe = SafeSessionState(_state=st.session_state)
    st.session_state["last_run_id"] = "last"
    assert safe.effective_run_id == "last"
    st.session_state["results_run_id"] = "current"
    assert safe.effective_run_id == "current"


def test_safe_session_state_strict_rejects_unknown_keys():
    st = _FakeStreamlit()
    safe = SafeSessionState(_state=st.session_state, _strict=True)
    with pytest.raises(KeyError):
        safe.get("nonexistent")
    with pytest.raises(KeyError):
        safe.set("nonexistent", 1)


def test_safe_session_state_strict_enforces_types():
    st = _FakeStreamlit()
    safe = SafeSessionState(_state=st.session_state, _strict=True)
    with pytest.raises(TypeError):
        safe.set(KEY_DARK_MODE, "not a bool")
    # Correct type passes
    safe.set(KEY_DARK_MODE, True)
    assert st.session_state[KEY_DARK_MODE] is True


def test_safe_session_state_non_strict_tolerant():
    st = _FakeStreamlit()
    safe = SafeSessionState(_state=st.session_state, _strict=False)
    # Should not raise — logs a warning internally.
    safe.set("some_unknown_key", 123)
    assert st.session_state["some_unknown_key"] == 123
