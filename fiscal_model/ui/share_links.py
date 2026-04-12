"""
Share-link helpers for supported Streamlit calculator flows.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from .helpers import PUBLIC_APP_URL

PRESET_ANALYSIS_MODE = "📋 Tax proposal (preset)"
SPENDING_ANALYSIS_MODE = "💰 Spending program"
_SHARE_TOKEN_KEY = "_applied_share_token"
_DYNAMIC_SCORING_KEY = "sidebar_setting_dynamic_scoring"
_TRUTHY_QUERY_VALUES = {"1", "true", "yes", "on"}


def _normalize_query_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return _normalize_query_value(value[0])
    normalized = str(value).strip()
    return normalized or None


def _query_flag(query_params: Mapping[str, Any], key: str) -> bool:
    value = _normalize_query_value(query_params.get(key))
    return value is not None and value.lower() in _TRUTHY_QUERY_VALUES


def _share_request_from_query_params(query_params: Mapping[str, Any]) -> dict[str, Any] | None:
    preset = _normalize_query_value(query_params.get("preset") or query_params.get("policy"))
    spending_preset = _normalize_query_value(query_params.get("spending_preset"))
    analysis = _normalize_query_value(query_params.get("analysis"))

    if spending_preset or analysis == "spending":
        return {
            "analysis_mode": SPENDING_ANALYSIS_MODE,
            "spending_preset": spending_preset,
            "dynamic_scoring": _query_flag(query_params, "dynamic"),
            "run": _query_flag(query_params, "run"),
        }

    if preset:
        return {
            "analysis_mode": PRESET_ANALYSIS_MODE,
            "preset": preset,
            "dynamic_scoring": _query_flag(query_params, "dynamic"),
            "run": _query_flag(query_params, "run"),
        }

    return None


def apply_share_query_params(st_module: Any) -> None:
    """
    Prime widget-backed session state from supported share-link query params.

    This runs before widgets are created so Streamlit accepts the state updates.
    """
    query_params = getattr(st_module, "query_params", {})
    share_request = _share_request_from_query_params(query_params)
    if not share_request:
        return

    token_payload = json.dumps(share_request, sort_keys=True)
    token = hashlib.sha256(token_payload.encode("utf-8")).hexdigest()[:12]
    if st_module.session_state.get(_SHARE_TOKEN_KEY) == token:
        return

    st_module.session_state[_SHARE_TOKEN_KEY] = token
    st_module.session_state["sidebar_analysis_mode"] = share_request["analysis_mode"]
    st_module.session_state[_DYNAMIC_SCORING_KEY] = share_request["dynamic_scoring"]

    preset = share_request.get("preset")
    if preset:
        st_module.session_state["sidebar_preset_choice"] = preset

    spending_preset = share_request.get("spending_preset")
    if spending_preset:
        st_module.session_state["sidebar_spending_preset"] = spending_preset

    if share_request["run"]:
        st_module.session_state["qs_calculate"] = True


def build_share_url(result_data: dict[str, Any], public_app_url: str = PUBLIC_APP_URL) -> str | None:
    """Build a shareable URL for supported calculator results."""
    if result_data.get("is_microsim"):
        return None

    dynamic_enabled = bool(getattr(result_data.get("result"), "dynamic_effects", None))

    if result_data.get("is_spending"):
        selected_preset = result_data.get("selected_spending_preset")
        if not selected_preset or selected_preset == "Custom program":
            return None
        params = {
            "analysis": "spending",
            "spending_preset": selected_preset,
            "dynamic": "1" if dynamic_enabled else "0",
            "run": "1",
        }
        return f"{public_app_url}/?{urlencode(params)}"

    preset_name = result_data.get("policy_name")
    if not preset_name or preset_name == "Custom Policy":
        return None

    params = {
        "analysis": "preset",
        "preset": preset_name,
        "dynamic": "1" if dynamic_enabled else "0",
        "run": "1",
    }
    return f"{public_app_url}/?{urlencode(params)}"
