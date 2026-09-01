"""
Behavioural guard for the newly keyed Tailor forms.

Adding an explicit ``key=`` to a Streamlit widget changes where its value lives
(session state instead of positional widget identity). That is the whole point
— the redesign moves these forms out of the sidebar onto ``/tailor`` — but it
must not change what the forms *return*. These tests pin the pre-key defaults,
the persistence the keys buy, and the one place where a stable key would have
changed behaviour if left alone: the spending form's preset-driven fields.

Also pins the fragile preset share-link round trip described in
``planning/redesign/NOTES.md`` §3.3, so a future reordering cannot break the
fallback path silently. This commit deliberately does **not** fix that
round trip (Phase 5 does, with stable preset ids) — it just stops it regressing.
"""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.ui.policy_input_presets import _short_display_name
from fiscal_model.ui.policy_input_spending import (
    SPENDING_PRESETS,
    render_spending_policy_inputs,
)
from fiscal_model.ui.policy_input_tax import render_tax_policy_inputs
from fiscal_model.ui.share_links import apply_share_query_params, build_share_url

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
    """Streamlit stand-in with real keyed-widget semantics.

    A keyed widget reads its value from ``session_state`` when the key is
    present and ignores the passed default; otherwise it stores the default.
    A selectbox whose stored value is not among the options raises, exactly as
    Streamlit does — that is what the eviction guards in the modules prevent.
    """

    def __init__(self, query_params=None):
        self.query_params = dict(query_params or {})
        self.session_state = _SessionState()
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.warnings: list[str] = []
        self.reruns = 0

    # --- non-widget surface -------------------------------------------------
    def markdown(self, body="", *args, **kwargs):
        self.markdowns.append(body)

    def caption(self, body="", *args, **kwargs):
        self.captions.append(body)

    def warning(self, body="", *args, **kwargs):
        self.warnings.append(body)

    def info(self, *args, **kwargs):
        return None

    def rerun(self):
        self.reruns += 1

    def expander(self, *args, **kwargs):
        return _Ctx()

    # --- widgets ------------------------------------------------------------
    def _resolve(self, key, fallback):
        if key is None:
            return fallback
        if key in self.session_state:
            return self.session_state[key]
        self.session_state[key] = fallback
        return fallback

    def selectbox(self, label, options=None, index=0, key=None, **kwargs):
        opts = list(options or [])
        if key is not None and key in self.session_state:
            current = self.session_state[key]
            if current not in opts:
                raise ValueError(
                    f"session_state[{key!r}] = {current!r} is not among {opts!r} "
                    "— Streamlit raises here; the module must evict or re-seed."
                )
            return current
        value = opts[index or 0]
        if key is not None:
            self.session_state[key] = value
        return value

    def text_input(self, label, value=_MISSING, key=None, **kwargs):
        return self._resolve(key, "" if value is _MISSING else value)

    def checkbox(self, label, value=_MISSING, key=None, **kwargs):
        return self._resolve(key, False if value is _MISSING else bool(value))

    def number_input(
        self, label, value=_MISSING, min_value=None, max_value=None, key=None, **kwargs
    ):
        fallback = value if value is not _MISSING else (min_value if min_value is not None else 0)
        return self._resolve(key, fallback)

    def slider(
        self, label, min_value=None, max_value=None, value=_MISSING, key=None, **kwargs
    ):
        fallback = value if value is not _MISSING else min_value
        return self._resolve(key, fallback)


def _tcja_full_extension_label() -> str:
    for name in PRESET_POLICIES:
        if _short_display_name(name) == "TCJA Full Extension":
            return name
    raise AssertionError("TCJA Full Extension preset is missing from PRESET_POLICIES")


# ---------------------------------------------------------------------------
# Custom tax form — the keys must not move the numbers
# ---------------------------------------------------------------------------


def test_custom_tax_form_returns_the_pre_key_defaults():
    st = _FakeStreamlit()
    out = render_tax_policy_inputs(st, PRESET_POLICIES, use_preset=False)

    assert out["policy_name"] == "Tax Rate Change"
    assert out["policy_type"] == "Income Tax Rate"
    assert out["rate_change_pct"] == -2.0
    assert out["rate_change"] == pytest.approx(-0.02)
    assert out["threshold"] == 400_000
    assert out["duration"] == 10
    assert out["phase_in"] == 1
    assert out["eti"] == 0.25
    assert out["manual_taxpayers"] == 0.0
    assert out["manual_avg_income"] == 0
    assert out["ordinary_income_base"] is True


def test_custom_tax_form_values_survive_a_rerender():
    """The reason for the keys: values persist across a change of location."""
    st = _FakeStreamlit()
    render_tax_policy_inputs(st, PRESET_POLICIES, use_preset=False)

    st.session_state["tailor_tax_rate_change_pct"] = 5.0
    st.session_state["tailor_tax_eti"] = 0.4
    st.session_state["tailor_tax_ordinary_base"] = False
    st.session_state["tailor_tax_threshold_choice"] = "Millionaires ($1M+)"

    out = render_tax_policy_inputs(st, PRESET_POLICIES, use_preset=False)
    assert out["rate_change_pct"] == 5.0
    assert out["rate_change"] == pytest.approx(0.05)
    assert out["eti"] == 0.4
    assert out["ordinary_income_base"] is False
    assert out["threshold"] == 1_000_000


def test_custom_threshold_input_is_used_when_custom_amount_selected():
    st = _FakeStreamlit()
    st.session_state["tailor_tax_threshold_choice"] = "Custom amount"
    st.session_state["tailor_tax_custom_threshold"] = 275_000

    out = render_tax_policy_inputs(st, PRESET_POLICIES, use_preset=False)
    assert out["threshold"] == 275_000


def test_capital_gains_subform_returns_the_pre_key_defaults():
    st = _FakeStreamlit()
    st.session_state["tailor_tax_type"] = "Capital Gains"

    out = render_tax_policy_inputs(st, PRESET_POLICIES, use_preset=False)
    assert out["policy_type"] == "Capital Gains"
    assert out["cg_base_year"] == 2024
    assert out["baseline_cg_rate"] == 0.238
    assert out["baseline_realizations"] == 0.0
    assert out["use_time_varying"] is True
    assert out["short_run_elasticity"] == 0.8
    assert out["long_run_elasticity"] == 0.4
    assert out["transition_years"] == 3
    assert out["realization_elasticity"] == pytest.approx(0.6)
    assert out["eliminate_step_up"] is False
    assert out["step_up_exemption"] == 0.0
    assert out["step_up_lock_in_multiplier"] == 2.0


def test_capital_gains_step_up_branch_defaults():
    st = _FakeStreamlit()
    st.session_state["tailor_tax_type"] = "Capital Gains"
    st.session_state["tailor_tax_cg_eliminate_step_up"] = True

    out = render_tax_policy_inputs(st, PRESET_POLICIES, use_preset=False)
    assert out["eliminate_step_up"] is True
    assert out["step_up_exemption"] == 1_000_000
    assert out["gains_at_death"] == 54.0
    assert out["step_up_lock_in_multiplier"] == 1.0


# ---------------------------------------------------------------------------
# Spending form — stable keys must not break preset-driven defaults
# ---------------------------------------------------------------------------


def test_spending_form_returns_the_selected_presets_values():
    st = _FakeStreamlit()
    out = render_spending_policy_inputs(st, default_preset=None)

    custom = SPENDING_PRESETS["Custom program"]
    assert out["selected_preset"] == "Custom program"
    assert out["annual_spending"] == custom["annual_spending"]
    assert out["multiplier"] == custom["multiplier"]
    assert out["duration"] == custom["duration"]
    assert out["is_one_time"] is False


def test_switching_spending_preset_reseeds_every_derived_field():
    """Unkeyed widgets re-derived their default from the preset on every switch.

    A stable key removes that implicit reset, so the module re-seeds the fields
    explicitly. Without it, picking a new program would keep the old numbers.
    """
    st = _FakeStreamlit()
    render_spending_policy_inputs(st, default_preset=None)

    st.session_state["sidebar_spending_preset"] = "Disaster Relief ($30B one-time)"
    out = render_spending_policy_inputs(st, default_preset=None)

    preset = SPENDING_PRESETS["Disaster Relief ($30B one-time)"]
    assert out["annual_spending"] == preset["annual_spending"]
    assert out["multiplier"] == preset["multiplier"]
    assert out["duration"] == preset["duration"]
    assert out["growth_rate"] == pytest.approx(preset["growth_rate"])
    assert out["spending_category"] == preset["category"]
    assert out["is_one_time"] is True


def test_manual_spending_override_survives_a_rerender_of_the_same_preset():
    st = _FakeStreamlit()
    st.session_state["sidebar_spending_preset"] = "Infrastructure Investment ($100B/yr)"
    render_spending_policy_inputs(st, default_preset=None)

    st.session_state["tailor_spend_multiplier"] = 0.5
    out = render_spending_policy_inputs(st, default_preset=None)
    assert out["multiplier"] == 0.5
    assert out["selected_preset"] == "Infrastructure Investment ($100B/yr)"


# ---------------------------------------------------------------------------
# Preset share link — NOTES §3.3 regression guard
# ---------------------------------------------------------------------------


def test_tcja_share_link_still_restores_and_selects_the_preset():
    """End-to-end: build a share URL for TCJA, replay it, land on the preset.

    Restoration works through the ``default_preset`` query-param fallback
    (``calculation_controller.py:50-56``), *not* through the session-state
    write at ``share_links.py:107`` — see the next test.
    """
    full_label = _tcja_full_extension_label()
    share_url = build_share_url(
        result_data={
            "policy_name": full_label,
            "result": SimpleNamespace(dynamic_effects=None),
            "is_spending": False,
        },
        public_app_url="https://example.com",
    )
    params = {k: v[0] for k, v in parse_qs(urlparse(share_url).query).items()}
    assert params["preset"] == full_label

    st = _FakeStreamlit(query_params=params)
    apply_share_query_params(st_module=st)
    assert st.session_state["sidebar_policy_area"] == "TCJA / Individual"

    # Mirrors calculation_controller.render_sidebar_inputs' default_preset read.
    default_preset = st.query_params.get("policy") or st.query_params.get("preset")
    out = render_tax_policy_inputs(
        st, PRESET_POLICIES, use_preset=True, default_preset=default_preset
    )

    assert out["preset_choice"] == full_label


def test_share_links_session_state_write_is_evicted_by_the_selectbox():
    """Documents the known fragility; do not 'fix' it here (Phase 5 owns it).

    ``share_links`` writes the *full* label into ``sidebar_preset_choice`` but
    the selectbox only offers *short* names and deletes anything else. If this
    test starts failing because the key survives, the round trip has changed
    and the Phase 5 preset-id work needs revisiting.
    """
    full_label = _tcja_full_extension_label()
    st = _FakeStreamlit(query_params={"analysis": "preset", "preset": full_label})
    apply_share_query_params(st_module=st)

    # The write happens...
    assert st.session_state["sidebar_preset_choice"] == full_label

    render_tax_policy_inputs(
        st, PRESET_POLICIES, use_preset=True, default_preset=full_label
    )

    # ...and is immediately replaced by the short name the widget offers.
    assert st.session_state["sidebar_preset_choice"] == "TCJA Full Extension"
