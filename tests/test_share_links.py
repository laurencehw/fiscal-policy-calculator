"""
Tests for preset share-link generation and restoration.
"""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from fiscal_model.ui.share_links import apply_share_query_params, build_share_url


class _DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _DummyStreamlit:
    def __init__(self, query_params):
        self.query_params = query_params
        self.session_state = _DummySessionState()


def test_apply_share_query_params_for_spending_preset_primes_sidebar_once():
    st_module = _DummyStreamlit(
        {
            "analysis": "spending",
            "spending_preset": "Infrastructure Investment ($100B/yr)",
            "dynamic": "1",
            "run": "1",
        }
    )

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "💰 Spending program"
    assert st_module.session_state["sidebar_spending_preset"] == "Infrastructure Investment ($100B/yr)"
    assert st_module.session_state["sidebar_setting_dynamic_scoring"] is True
    assert st_module.session_state["qs_calculate"] is True

    del st_module.session_state["qs_calculate"]
    apply_share_query_params(st_module=st_module)

    assert "qs_calculate" not in st_module.session_state


def test_apply_share_query_params_for_tax_preset_sets_preset_choice():
    st_module = _DummyStreamlit(
        {
            "analysis": "preset",
            "preset": "TCJA Full Extension",
            "dynamic": "0",
            "run": "1",
        }
    )

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "📋 Tax proposal (preset)"
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"
    assert st_module.session_state["sidebar_setting_dynamic_scoring"] is False


def test_apply_share_query_params_accepts_legacy_policy_key_and_list_values():
    st_module = _DummyStreamlit(
        {
            "policy": ["Biden 2025 Proposal"],
            "dynamic": ["yes"],
            "run": ["true"],
        }
    )

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "📋 Tax proposal (preset)"
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "Biden 2025 Proposal"
    assert st_module.session_state["sidebar_setting_dynamic_scoring"] is True
    assert st_module.session_state["qs_calculate"] is True


def test_apply_share_query_params_overrides_stale_sidebar_state():
    st_module = _DummyStreamlit(
        {
            "analysis": "preset",
            "preset": "TCJA Full Extension",
        }
    )
    st_module.session_state["sidebar_policy_area"] = "Climate / Energy"
    st_module.session_state["sidebar_spending_preset"] = "Infrastructure Investment ($100B/yr)"

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"
    assert "sidebar_spending_preset" not in st_module.session_state


def test_apply_share_query_params_for_spending_clears_tax_state():
    st_module = _DummyStreamlit(
        {
            "analysis": "spending",
            "spending_preset": "Infrastructure Investment ($100B/yr)",
        }
    )
    st_module.session_state["sidebar_policy_area"] = "Income Tax"
    st_module.session_state["sidebar_preset_choice"] = "Biden 2025 Proposal"

    apply_share_query_params(st_module=st_module)

    assert st_module.session_state["sidebar_analysis_mode"] == "💰 Spending program"
    assert st_module.session_state["sidebar_spending_preset"] == "Infrastructure Investment ($100B/yr)"
    assert "sidebar_policy_area" not in st_module.session_state
    assert "sidebar_preset_choice" not in st_module.session_state


def test_build_share_url_for_tax_preset_includes_dynamic_flag():
    result_data = {
        "policy_name": "Biden 2025 Proposal",
        "result": SimpleNamespace(dynamic_effects=object()),
        "is_spending": False,
    }

    share_url = build_share_url(result_data=result_data, public_app_url="https://example.com")
    parsed = urlparse(share_url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "example.com"
    assert params["analysis"] == ["preset"]
    assert params["preset"] == ["Biden 2025 Proposal"]
    assert params["dynamic"] == ["1"]
    assert params["run"] == ["1"]


def test_build_share_url_for_spending_preset_uses_spending_query_param():
    result_data = {
        "selected_spending_preset": "Infrastructure Investment ($100B/yr)",
        "result": SimpleNamespace(dynamic_effects=None),
        "is_spending": True,
    }

    share_url = build_share_url(result_data=result_data, public_app_url="https://example.com")
    params = parse_qs(urlparse(share_url).query)

    assert params["analysis"] == ["spending"]
    assert params["spending_preset"] == ["Infrastructure Investment ($100B/yr)"]
    assert params["dynamic"] == ["0"]


def test_build_share_url_returns_none_for_custom_or_microsim_results():
    assert build_share_url(
        result_data={"policy_name": "Custom Policy", "result": SimpleNamespace(dynamic_effects=None)},
        public_app_url="https://example.com",
    ) is None
    assert build_share_url(
        result_data={"is_spending": True, "selected_spending_preset": "Custom program"},
        public_app_url="https://example.com",
    ) is None
    assert build_share_url(
        result_data={"is_microsim": True},
        public_app_url="https://example.com",
    ) is None
