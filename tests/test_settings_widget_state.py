"""
Behavioural guard for the newly keyed model settings.

Five of the seven model settings were unkeyed (``planning/redesign/NOTES.md``
§2), so moving the panel out of the sidebar into a settings popover would have
reset them. These tests pin the values the panel returns before and after the
keys were added, and cover the two cases where a key could have changed
behaviour: the dark-mode toggle (whose code key is written *after* the widget
renders) and the IRS data year (whose option list is discovered from disk).
"""

from __future__ import annotations

from fiscal_model.ui.settings_controller import (
    _available_irs_data_years,
    render_settings_tab,
)

_MISSING = object()


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeStreamlit:
    """Streamlit stand-in with real keyed-widget semantics (see conftest note).

    A keyed widget reads session state when the key is present and ignores the
    passed default; a selectbox whose stored value is not among the options
    raises, as Streamlit does.
    """

    def __init__(self):
        self.session_state = _SessionState()
        self.captions: list[str] = []
        self.warnings: list[str] = []
        self.reruns = 0

    def markdown(self, *args, **kwargs):
        return None

    def caption(self, body="", *args, **kwargs):
        self.captions.append(body)

    def warning(self, body="", *args, **kwargs):
        self.warnings.append(body)

    def rerun(self):
        self.reruns += 1

    def expander(self, *args, **kwargs):
        return _Ctx()

    def _resolve(self, key, fallback):
        if key is None:
            return fallback
        if key in self.session_state:
            return self.session_state[key]
        self.session_state[key] = fallback
        return fallback

    def checkbox(self, label, value=_MISSING, key=None, **kwargs):
        return self._resolve(key, False if value is _MISSING else bool(value))

    def selectbox(self, label, options=None, index=0, key=None, **kwargs):
        opts = list(options or [])
        if key is not None and key in self.session_state:
            current = self.session_state[key]
            if current not in opts:
                raise ValueError(
                    f"session_state[{key!r}] = {current!r} is not among {opts!r}"
                )
            return current
        value = opts[index or 0]
        if key is not None:
            self.session_state[key] = value
        return value


def test_settings_defaults_match_the_pre_key_behaviour():
    st = _FakeStreamlit()
    out = render_settings_tab(st, _Ctx())

    assert out["use_real_data"] is True
    assert out["dynamic_scoring"] is False
    assert out["macro_model"] is None  # only rendered when dynamic scoring is on
    assert out["use_microsim"] is False
    assert out["use_microsim_distribution"] is True
    assert out["dark_mode"] is False
    assert out["data_year"] == _available_irs_data_years()[0]


def test_macro_model_appears_only_with_dynamic_scoring():
    st = _FakeStreamlit()
    st.session_state["sidebar_setting_dynamic_scoring"] = True

    out = render_settings_tab(st, _Ctx())
    assert out["dynamic_scoring"] is True
    assert out["macro_model"] == "FRB/US-Lite (recommended)"
    assert st.session_state["setting_macro_model"] == "FRB/US-Lite (recommended)"


def test_settings_survive_a_rerender():
    """The point of the keys: values persist across a change of location."""
    st = _FakeStreamlit()
    render_settings_tab(st, _Ctx())

    st.session_state["setting_use_real_data"] = False
    st.session_state["setting_use_microsim"] = True
    st.session_state["setting_use_microsim_distribution"] = False

    out = render_settings_tab(st, _Ctx())
    assert out["use_real_data"] is False
    assert out["use_microsim"] is True
    assert out["use_microsim_distribution"] is False


def test_stale_data_year_falls_back_to_the_newest_vintage():
    """The option list is discovered from disk, so a stored year can go stale."""
    st = _FakeStreamlit()
    st.session_state["setting_data_year"] = 1999  # never shipped

    out = render_settings_tab(st, _Ctx())
    assert out["data_year"] == _available_irs_data_years()[0]


def test_data_year_schema_default_of_none_is_resolved():
    """``initialize_session_state`` seeds None; the panel must not pass it on."""
    st = _FakeStreamlit()
    st.session_state["setting_data_year"] = None

    out = render_settings_tab(st, _Ctx())
    assert out["data_year"] == _available_irs_data_years()[0]


def test_dark_mode_widget_key_is_separate_from_the_dark_mode_code_key():
    """``dark_mode`` is written after the widget renders, so it needs its own key.

    Streamlit forbids assigning to a key already bound to an instantiated
    widget, which is why the toggle is keyed ``setting_dark_mode``.
    """
    st = _FakeStreamlit()
    render_settings_tab(st, _Ctx())
    assert st.session_state["setting_dark_mode"] is False
    assert st.session_state["dark_mode"] is False
    assert st.reruns == 0

    # User ticks the box: the widget key changes, the code key follows.
    st.session_state["setting_dark_mode"] = True
    out = render_settings_tab(st, _Ctx())
    assert out["dark_mode"] is True
    assert st.session_state["dark_mode"] is True
    assert st.reruns == 1
