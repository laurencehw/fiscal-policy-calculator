"""
Share-link helpers for supported Streamlit calculator flows.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from fiscal_model.app_data import PRESET_POLICIES

from .helpers import PUBLIC_APP_URL
from .policy_input_presets import _preset_category, _short_display_name

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


def _preset_policy_area(preset_name: str | None) -> str | None:
    if not preset_name:
        return None

    preset = PRESET_POLICIES.get(preset_name)
    if preset is None:
        for canonical_name, candidate in PRESET_POLICIES.items():
            if _short_display_name(canonical_name) == preset_name:
                preset = candidate
                break
        if preset is None:
            return None

    return _preset_category(preset)


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
        st_module.session_state.pop("sidebar_spending_preset", None)
        preset_area = _preset_policy_area(preset)
        if preset_area:
            st_module.session_state["sidebar_policy_area"] = preset_area
        st_module.session_state["sidebar_preset_choice"] = preset

    spending_preset = share_request.get("spending_preset")
    if spending_preset:
        st_module.session_state.pop("sidebar_preset_choice", None)
        st_module.session_state.pop("sidebar_policy_area", None)
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


# ── Build-page share links (Phase 3) ─────────────────────────────────────
# The Build page is a *package* of catalog policies plus a deficit target, so
# it needs its own codec rather than the single-preset one above. Deliberately
# separate functions: the preset share round-trip is Phase 5's to rework, and
# nothing here touches it.
#
#   /build?policies=ss-donut-250k,corporate-28pct&target=3.0&metric=pct_gdp
#
# ``policies`` carries stable ``preset_id`` slugs (fiscal_model/preset_ids.py),
# comma separated and unescaped, so the URL stays readable and pasteable.

BUILD_URL_PATH = "build"
BUILD_METRIC_PCT_GDP = "pct_gdp"
BUILD_METRIC_USD_B = "usd_b"
BUILD_METRICS: tuple[str, ...] = (BUILD_METRIC_PCT_GDP, BUILD_METRIC_USD_B)

#: Spellings of the metric that a hand-edited or older link might carry.
_BUILD_METRIC_ALIASES: dict[str, str] = {
    "pct_gdp": BUILD_METRIC_PCT_GDP,
    "pct": BUILD_METRIC_PCT_GDP,
    "gdp": BUILD_METRIC_PCT_GDP,
    "percent": BUILD_METRIC_PCT_GDP,
    "%": BUILD_METRIC_PCT_GDP,
    "usd_b": BUILD_METRIC_USD_B,
    "usd": BUILD_METRIC_USD_B,
    "dollars": BUILD_METRIC_USD_B,
    "$b": BUILD_METRIC_USD_B,
    "billions": BUILD_METRIC_USD_B,
}


def normalize_build_metric(value: Any) -> str:
    """Fold any accepted metric spelling to ``pct_gdp`` / ``usd_b``."""
    normalized = _normalize_query_value(value)
    if normalized is None:
        return BUILD_METRIC_PCT_GDP
    return _BUILD_METRIC_ALIASES.get(normalized.lower(), BUILD_METRIC_PCT_GDP)


def encode_build_share(
    preset_ids: Sequence[str],
    target: float | None = None,
    metric: str = BUILD_METRIC_PCT_GDP,
    *,
    public_app_url: str = PUBLIC_APP_URL,
) -> str:
    """Build the shareable ``/build`` URL for a package + deficit target.

    ``preset_ids`` are stable slugs in selection order; duplicates and blanks
    are dropped, order is preserved (the Build page resolves overlap conflicts
    by keeping the *first* member of a group, so order is meaningful).
    """
    metric_value = normalize_build_metric(metric)

    seen: set[str] = set()
    ordered: list[str] = []
    for raw in preset_ids or ():
        token = str(raw).strip()
        if token and token not in seen:
            seen.add(token)
            ordered.append(token)

    params: dict[str, str] = {"policies": ",".join(ordered)}
    if target is not None:
        params["target"] = (
            f"{float(target):.1f}"
            if metric_value == BUILD_METRIC_PCT_GDP
            else f"{float(target):.0f}"
        )
    params["metric"] = metric_value

    # ``safe=","`` keeps the id list human-readable instead of %2C-escaped.
    return f"{public_app_url}/{BUILD_URL_PATH}?{urlencode(params, safe=',')}"


def decode_build_share(query_params: Mapping[str, Any]) -> dict[str, Any]:
    """Parse ``/build`` query params into ``{preset_ids, target, metric}``.

    Every ``policies`` token is run through ``preset_ids.resolve_preset`` (via
    :func:`~fiscal_model.preset_ids.preset_id_for_token`), so legacy emoji
    labels and short display names in an old link resolve to their stable id.
    A token that resolves to nothing is passed through unchanged rather than
    dropped: the Build catalog carries a handful of score-map-only options that
    have no entry in ``PRESET_POLICIES``, and it validates the list itself.

    ``target`` is ``None`` when absent or unparseable, so the caller keeps its
    own default instead of snapping to zero.
    """
    from fiscal_model.preset_ids import preset_id_for_token

    raw_policies = _normalize_query_value(query_params.get("policies"))
    preset_ids: list[str] = []
    if raw_policies:
        for token in raw_policies.replace("|", ",").split(","):
            candidate = token.strip()
            if not candidate:
                continue
            resolved = preset_id_for_token(candidate) or candidate
            if resolved not in preset_ids:
                preset_ids.append(resolved)

    metric = normalize_build_metric(query_params.get("metric"))

    target: float | None = None
    raw_target = _normalize_query_value(query_params.get("target"))
    if raw_target is not None:
        try:
            target = float(raw_target.replace("%", "").replace(",", "").strip())
        except ValueError:
            target = None

    return {"preset_ids": preset_ids, "target": target, "metric": metric}
