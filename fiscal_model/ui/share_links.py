"""
Share-link helpers for supported Streamlit calculator flows.

The URL contract (redesign plan §7, wireframe ``05-ia-map-url-contract``):

===================================================== ==========================
URL                                                   Surface
===================================================== ==========================
``/?q=…``                                             Ask, prefilled
``/explore?preset=<id>&dynamic=0|1&run=1``            Explore, restore + run
``/tailor?type=…&rate=…&who=…&phase=…&run=1``         Tailor, restore + run
``/build?policies=<ids>&target=…&metric=…``           Build (codec below)
``/?analysis=preset&preset=<label>&…``                legacy → shimmed
===================================================== ==========================

Two rules hold everywhere:

1. **Emitted links carry stable ids, never display labels.**
   ``preset=tcja-full-extension``, not ``preset=🏛️ TCJA Full Extension
   (CBO: $4.6T)``. Emoji labels move whenever a score is refreshed; ids are
   frozen (``fiscal_model/preset_ids.py``).
2. **Decoding accepts every legacy spelling forever**, through
   ``preset_ids.resolve_preset`` — the id, the emoji label, the URL-encoded
   label, the short dropdown name, the score-stripped name.

Restoration writes the keys the *widgets actually read* — ``sidebar_policy_area``
plus the **short** name in ``sidebar_preset_choice`` — instead of the full label
the selectbox used to evict on sight (NOTES §3.3).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.preset_ids import preset_id_for_token, resolve_preset

from .helpers import PUBLIC_APP_URL
from .policy_input_presets import _preset_category, _short_display_name
from .session_state import seed_widget_default

PRESET_ANALYSIS_MODE = "📋 Tax proposal (preset)"
SPENDING_ANALYSIS_MODE = "💰 Spending program"
_SHARE_TOKEN_KEY = "_applied_share_token"
_DYNAMIC_SCORING_KEY = "sidebar_setting_dynamic_scoring"
_TRUTHY_QUERY_VALUES = {"1", "true", "yes", "on"}

#: Registered ``st.Page`` url paths this module builds links against.
EXPLORE_URL_PATH = "explore"
TAILOR_URL_PATH = "tailor"
ASK_URL_PATH = "ask"

#: Session key holding the ``?preset=`` token that resolved to nothing, so the
#: page can say so once instead of silently scoring something else.
UNRESOLVED_PRESET_KEY = "_share_preset_unresolved"


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
    """Parse the preset/spending half of the URL contract.

    ``preset`` is resolved through ``preset_ids.resolve_preset``, so a stable
    id, an emoji label, a URL-encoded label and a short dropdown name all land
    on the same canonical entry. A token that resolves to nothing is kept as
    ``unresolved`` rather than dropped, so the page can say so.
    """
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
        canonical = resolve_preset(preset)
        return {
            "analysis_mode": PRESET_ANALYSIS_MODE,
            "preset": canonical,
            "unresolved": None if canonical else preset,
            "dynamic_scoring": _query_flag(query_params, "dynamic"),
            "run": _query_flag(query_params, "run"),
        }

    return None


def _preset_policy_area(preset_name: str | None) -> str | None:
    canonical = resolve_preset(preset_name)
    if canonical is None:
        return None
    preset = PRESET_POLICIES.get(canonical)
    return None if preset is None else _preset_category(preset)


def apply_share_query_params(st_module: Any) -> str | None:
    """
    Prime widget-backed session state from supported share-link query params.

    This runs before widgets are created so Streamlit accepts the state updates.
    Applied at most once per distinct link: the request is hashed into
    ``_applied_share_token``, so a rerun (or a second call from the page and the
    pipeline) does not re-arm the auto-run or undo a manual change.

    **NOTES §3.3 fix.** The old code wrote the *full* label into
    ``sidebar_preset_choice``; the selectbox offers ``_short_display_name``
    values and evicts anything else, so the write was dead and restoration
    limped along on the ``default_preset`` query-param fallback. It now writes
    the two keys the pickers really read — ``sidebar_policy_area`` (the
    category) and the **short** name in ``sidebar_preset_choice`` — through
    ``seed_widget_default``, which keeps the cross-page mirror in step.

    Returns the ``?preset=`` token that resolved to nothing, if any.
    """
    query_params = getattr(st_module, "query_params", {})
    share_request = _share_request_from_query_params(query_params)
    if not share_request:
        return None

    token_payload = json.dumps(share_request, sort_keys=True)
    token = hashlib.sha256(token_payload.encode("utf-8")).hexdigest()[:12]
    if st_module.session_state.get(_SHARE_TOKEN_KEY) == token:
        return st_module.session_state.get(UNRESOLVED_PRESET_KEY)

    st_module.session_state[_SHARE_TOKEN_KEY] = token
    st_module.session_state["sidebar_analysis_mode"] = share_request["analysis_mode"]
    st_module.session_state[_DYNAMIC_SCORING_KEY] = share_request["dynamic_scoring"]

    unresolved = share_request.get("unresolved")
    if unresolved:
        st_module.session_state[UNRESOLVED_PRESET_KEY] = unresolved
    else:
        st_module.session_state.pop(UNRESOLVED_PRESET_KEY, None)

    preset = share_request.get("preset")
    if preset:
        st_module.session_state.pop("sidebar_spending_preset", None)
        preset_area = _preset_policy_area(preset)
        if preset_area:
            seed_widget_default(st_module, "sidebar_policy_area", preset_area, force=True)
        seed_widget_default(
            st_module, "sidebar_preset_choice", _short_display_name(preset), force=True
        )

    spending_preset = share_request.get("spending_preset")
    if spending_preset:
        st_module.session_state.pop("sidebar_preset_choice", None)
        st_module.session_state.pop("sidebar_policy_area", None)
        seed_widget_default(
            st_module, "sidebar_spending_preset", spending_preset, force=True
        )

    if share_request["run"]:
        st_module.session_state["qs_calculate"] = True

    return unresolved or None


# ── Baseline vintage stamp ───────────────────────────────────────────────
_VINTAGE_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def baseline_vintage_token(vintage: str | None = None) -> str:
    """Slugify the live baseline vintage for the ``baseline=`` URL stamp.

    ``"CBO Feb 2026"`` -> ``"feb2026"``. Both the share URL and the export
    headers derive from the *same* source — ``components.results
    .resolve_baseline_vintage()``, which reads the health snapshot — so a URL
    can never claim a different vintage from the CSV it came with.
    """
    if vintage is None:
        try:
            from components.results import resolve_baseline_vintage

            vintage = resolve_baseline_vintage()
        except Exception:  # pragma: no cover — defensive
            return ""
    text = str(vintage or "").strip().lower()
    if text.startswith("cbo"):
        text = text[3:]
    return _VINTAGE_TOKEN_RE.sub("", text)


def build_share_url(
    result_data: dict[str, Any],
    public_app_url: str = PUBLIC_APP_URL,
    scored: Any = None,
) -> str | None:
    """Build a shareable URL for supported calculator results.

    Emits the new contract — ``/explore?preset=<stable id>`` (or
    ``/tailor?type=spending&spending_preset=…``) — plus three provenance stamps
    taken from the run's :class:`~components.results.ScoredResult`:

    ``baseline``
        the baseline vintage the numbers were scored against (``feb2026``);
    ``spec``
        the policy-spec hash, so a link identifies *which run* produced it;
    ``mode``
        ``conventional`` or ``dynamic``.

    ``analysis=`` is still emitted: links are pasted into documents and read by
    the legacy reader, and keeping it costs nothing.
    """
    if result_data.get("is_microsim"):
        return None

    dynamic_enabled = bool(getattr(result_data.get("result"), "dynamic_effects", None))

    def _provenance() -> dict[str, str]:
        stamps: dict[str, str] = {}
        vintage = getattr(scored, "baseline_vintage", None)
        token = baseline_vintage_token(vintage)
        if token:
            stamps["baseline"] = token
        spec_hash = getattr(scored, "policy_spec_hash", None)
        if spec_hash:
            stamps["spec"] = str(spec_hash)
        stamps["mode"] = str(
            getattr(scored, "mode", None)
            or ("dynamic" if dynamic_enabled else "conventional")
        )
        return stamps

    if result_data.get("is_spending"):
        selected_preset = result_data.get("selected_spending_preset")
        if not selected_preset or selected_preset == "Custom program":
            return None
        params = {
            "analysis": "spending",
            "type": "spending",
            "spending_preset": selected_preset,
            "dynamic": "1" if dynamic_enabled else "0",
            "run": "1",
            **_provenance(),
        }
        return f"{public_app_url}/{TAILOR_URL_PATH}?{urlencode(params)}"

    preset_name = result_data.get("policy_name")

    # A generic Tailor run has a user-typed name that is not in the catalog, so
    # there is no preset id to link to — but the policy is fully described by
    # its own parameters, which ``/tailor`` reads. Emit that link instead of
    # dropping the share button (Phase 5 leftover, REDESIGN_PLAN §7).
    # "Custom Policy" is the *placeholder* label, not a proposal — it resolves
    # to an id but names nothing, so it takes the generic path too.
    preset_id = (
        preset_id_for_token(preset_name)
        if preset_name and preset_name != "Custom Policy"
        else None
    )
    if preset_id is None:
        return generic_tailor_share_url(
            result_data,
            public_app_url=public_app_url,
            provenance=_provenance(),
            dynamic=dynamic_enabled,
        )

    params = {
        "analysis": "preset",
        "preset": preset_id,
        "dynamic": "1" if dynamic_enabled else "0",
        "run": "1",
        **_provenance(),
    }
    return f"{public_app_url}/{EXPLORE_URL_PATH}?{urlencode(params)}"


# ── Tailor query params (Phase 5) ────────────────────────────────────────
#
#   /tailor?type=income&rate=2&who=top400k&phase=1&duration=10&run=1
#
# ``type`` selects the policy-type chip; ``who`` is a small enum over the
# thresholds the "Who is affected?" picker offers (a bare number is accepted
# too and becomes a custom amount). Everything is optional: a link may set one
# field and leave the rest at their current values.

_TAILOR_SHARE_TOKEN_KEY = "_applied_tailor_share_token"

#: ``?type=`` -> the Tailor policy-type chip (``app_pages.tailor.POLICY_KINDS``).
TAILOR_TYPES: dict[str, str] = {
    "income": "Income",
    "income_tax": "Income",
    "corporate": "Corporate",
    "corporate_tax": "Corporate",
    "capital_gains": "Capital gains",
    "capital-gains": "Capital gains",
    "capitalgains": "Capital gains",
    "gains": "Capital gains",
    "cg": "Capital gains",
    "spending": "Spending",
    "outlays": "Spending",
}

#: ``?who=`` -> the income threshold the rate change applies above. The keys are
#: the documented enum; a bare number (``who=275000``) is also accepted.
TAILOR_WHO_THRESHOLDS: dict[str, int] = {
    "all": 0,
    "everyone": 0,
    "top50k": 50_000,
    "top100k": 100_000,
    "top200k": 200_000,
    "top400k": 400_000,
    "top500k": 500_000,
    "top1m": 1_000_000,
    "millionaires": 1_000_000,
}

#: The spelling each value is *written* as. Decoding accepts every alias above;
#: encoding picks exactly one, so a link built twice is byte-identical.
TAILOR_TYPE_TOKENS: dict[str, str] = {
    "Income": "income",
    "Corporate": "corporate",
    "Capital gains": "capital_gains",
    "Spending": "spending",
}
TAILOR_WHO_TOKENS: dict[int, str] = {
    0: "all",
    50_000: "top50k",
    100_000: "top100k",
    200_000: "top200k",
    400_000: "top400k",
    500_000: "top500k",
    1_000_000: "top1m",
}

_WHO_SUFFIX = re.compile(r"^(\d+(?:\.\d+)?)([kmb]?)$")
_WHO_MULTIPLIER = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


def parse_tailor_who(value: Any) -> int | None:
    """Fold a ``?who=`` token to an income threshold in dollars.

    Accepts the enum (``top400k``), a bare number (``400000``), and the
    shorthand a human would type (``400k``, ``$400,000``, ``1M``).
    """
    raw = _normalize_query_value(value)
    if raw is None:
        return None
    token = raw.strip().lower().replace("$", "").replace(",", "").replace("+", "")
    token = token.replace(" ", "").replace("-", "").replace("_", "")
    if token in TAILOR_WHO_THRESHOLDS:
        return TAILOR_WHO_THRESHOLDS[token]
    if token.startswith("top"):
        token = token[3:]
    match = _WHO_SUFFIX.match(token)
    if match is None:
        return None
    amount = float(match.group(1)) * _WHO_MULTIPLIER[match.group(2)]
    if not 0 <= amount <= 10_000_000:
        return None
    return int(amount)


def _query_number(query_params: Mapping[str, Any], key: str) -> float | None:
    raw = _normalize_query_value(query_params.get(key))
    if raw is None:
        return None
    try:
        return float(raw.replace("%", "").replace("pp", "").replace(",", "").strip())
    except ValueError:
        return None


def decode_tailor_query(query_params: Mapping[str, Any]) -> dict[str, Any]:
    """Parse ``/tailor`` query params. Absent fields come back as ``None``.

    Returned keys: ``kind`` (a ``POLICY_KINDS`` member), ``rate`` (percentage
    points), ``threshold`` (dollars), ``phase`` and ``duration`` (years), and
    ``run`` / ``dynamic`` flags.
    """
    kind = None
    raw_type = _normalize_query_value(query_params.get("type"))
    if raw_type:
        kind = TAILOR_TYPES.get(raw_type.strip().lower().replace(" ", "_"))

    phase = _query_number(query_params, "phase")
    duration = _query_number(query_params, "duration")
    rate = _query_number(query_params, "rate")

    return {
        "kind": kind,
        "rate": rate,
        "threshold": parse_tailor_who(query_params.get("who")),
        # Engine contract: phase_in_years >= 1 (chip ⑨).
        "phase": None if phase is None else max(1, min(5, int(phase))),
        "duration": None if duration is None else max(1, min(10, int(duration))),
        "dynamic": _query_flag(query_params, "dynamic"),
        # Absent is not the same as ``dynamic=0``: a link that says nothing
        # about scoring mode must not silently switch the toggle off.
        "has_dynamic": _normalize_query_value(query_params.get("dynamic")) is not None,
        "run": _query_flag(query_params, "run"),
        "has_params": any(
            _normalize_query_value(query_params.get(key)) is not None
            for key in ("type", "rate", "who", "phase", "duration")
        ),
    }


#: ``PolicyType`` value -> the Tailor chip that can re-create it. Types absent
#: here (payroll, estate, the transfer programs) have no Tailor form, so a
#: generic run of one is not shareable as a ``/tailor`` link.
POLICY_TYPE_TO_TAILOR_KIND: dict[str, str] = {
    "income_tax": "Income",
    "corporate_tax": "Corporate",
    "capital_gains_tax": "Capital gains",
}


def encode_tailor_share(
    *,
    kind: str = "Income",
    rate: float | None = None,
    threshold: int | None = None,
    phase: int | None = None,
    duration: int | None = None,
    dynamic: bool = False,
    run: bool = True,
    public_app_url: str = PUBLIC_APP_URL,
    provenance: Mapping[str, str] | None = None,
) -> str:
    """Build a ``/tailor`` URL. The inverse of :func:`decode_tailor_query`.

    ``provenance`` carries the same ``baseline`` / ``spec`` / ``mode`` stamps
    :func:`build_share_url` puts on a preset link, so a custom run's link
    identifies its baseline vintage and the exact run that produced it.
    """
    params: dict[str, str] = {"type": TAILOR_TYPE_TOKENS.get(kind, "income")}
    if rate is not None:
        params["rate"] = f"{float(rate):g}"
    if threshold is not None:
        params["who"] = TAILOR_WHO_TOKENS.get(int(threshold), str(int(threshold)))
    if phase is not None:
        params["phase"] = str(int(phase))
    if duration is not None:
        params["duration"] = str(int(duration))
    params["dynamic"] = "1" if dynamic else "0"
    if run:
        params["run"] = "1"
    if provenance:
        params.update({str(k): str(v) for k, v in provenance.items()})
    return f"{public_app_url}/{TAILOR_URL_PATH}?{urlencode(params)}"


def generic_tailor_share_url(
    result_data: Mapping[str, Any],
    *,
    public_app_url: str = PUBLIC_APP_URL,
    provenance: Mapping[str, str] | None = None,
    dynamic: bool = False,
) -> str | None:
    """Share URL for a custom (non-catalog) tax run, or ``None``.

    Reads the scored ``Policy`` object rather than the widget state, so the
    link describes what was actually scored — including when the run came from
    a link in the first place.
    """
    policy = result_data.get("policy")
    if policy is None:
        return None
    policy_type = getattr(getattr(policy, "policy_type", None), "value", None)
    kind = POLICY_TYPE_TO_TAILOR_KIND.get(str(policy_type))
    if kind is None:
        return None

    rate_change = getattr(policy, "rate_change", None)
    threshold = getattr(policy, "affected_income_threshold", None)
    return encode_tailor_share(
        kind=kind,
        # The engine stores a fraction; ``?rate=`` is in percentage points.
        rate=None if rate_change is None else round(float(rate_change) * 100, 4),
        threshold=None if threshold is None else int(threshold),
        phase=int(getattr(policy, "phase_in_years", 1) or 1),
        duration=int(getattr(policy, "duration_years", 10) or 10),
        dynamic=dynamic,
        run=True,
        public_app_url=public_app_url,
        provenance=provenance,
    )


# ── Legacy URL shim (Phase 5) ────────────────────────────────────────────
#: ``?analysis=`` value -> the page that now owns that flow.
LEGACY_ANALYSIS_PAGES: dict[str, str] = {
    "preset": EXPLORE_URL_PATH,
    "custom": TAILOR_URL_PATH,
    "spending": TAILOR_URL_PATH,
}

#: Query params that survive a legacy rewrite untouched: they address the
#: runtime, not the policy (admin gate, iframe embedding).
_PRESERVED_QUERY_KEYS: tuple[str, ...] = (
    "admin",
    "embed",
    "embed_options",
    "theme",
    "utm_source",
)


def rewrite_legacy_query(
    query_params: Mapping[str, Any],
) -> tuple[str, dict[str, str]] | None:
    """Translate a pre-redesign URL into ``(url_path, new query params)``.

    Pure function — no Streamlit, no session state — so the router's shim stays
    three lines and this stays unit-testable.

    ============================================== ===============================
    Legacy                                          New
    ============================================== ===============================
    ``?analysis=preset&preset=<label>&run=1``       ``/explore?preset=<id>&run=1``
    ``?policy=<label>&run=1``                       ``/explore?preset=<id>&run=1``
    ``?analysis=spending&spending_preset=X``        ``/tailor?type=spending&…``
    ``?analysis=custom``                            ``/tailor?type=income``
    ============================================== ===============================

    Returns ``None`` when the URL carries nothing legacy — including when it
    already speaks the new contract (a bare ``?preset=<id>`` on ``/explore``).

    Retired *pathnames* (``/ask``, ``/studio``) are not query params and are
    handled in ``app._apply_legacy_url_shim`` instead.
    """
    analysis = _normalize_query_value(query_params.get("analysis"))
    legacy_policy = _normalize_query_value(query_params.get("policy"))
    spending_preset = _normalize_query_value(query_params.get("spending_preset"))
    preset_token = _normalize_query_value(query_params.get("preset")) or legacy_policy

    if analysis is None and legacy_policy is None and spending_preset is None:
        return None

    analysis = (analysis or "").lower()
    if analysis not in LEGACY_ANALYSIS_PAGES:
        # ``?policy=`` / ``?spending_preset=`` without an ``analysis`` key: the
        # other two shapes old links come in.
        analysis = "spending" if spending_preset else "preset"

    params: dict[str, str] = {
        key: value
        for key in _PRESERVED_QUERY_KEYS
        if (value := _normalize_query_value(query_params.get(key))) is not None
    }
    params["dynamic"] = "1" if _query_flag(query_params, "dynamic") else "0"
    if _query_flag(query_params, "run"):
        params["run"] = "1"

    if analysis == "spending":
        params["type"] = "spending"
        if spending_preset:
            params["spending_preset"] = spending_preset
        return TAILOR_URL_PATH, params

    if analysis == "custom":
        params["type"] = "income"
        return TAILOR_URL_PATH, params

    # ``preset``: emit the stable id when the token resolves, and pass an
    # unknown token through untouched so the page can name it in a notice.
    if preset_token:
        params["preset"] = preset_id_for_token(preset_token) or preset_token
    return EXPLORE_URL_PATH, params


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


# ---------------------------------------------------------------------------
# Build — "Start from your values" links  (REDESIGN_PLAN.md §5b.7, chip ⑮)
# ---------------------------------------------------------------------------
#
#     /build?values=egalitarian            — an archetype card, by stable slug
#     /build?vector=<urlsafe-base64 json>  — a hand-edited vector
#     …&load=1                             — apply it to the checklist on arrival
#
# Two forms because they answer to different things. ``values`` is the durable
# one: it names a philosophy, so a link shared in a syllabus still means what it
# meant even after the catalog is re-scored. ``vector`` carries the reader's own
# edits, which no slug can name. When both are present the vector wins and the
# archetype is kept only as the label for the reading, because the vector is the
# thing that was actually contested.
#
# ``load=1`` is what turns a link into an assignment: the package lands in the
# checklist and the reader starts from an editable package rather than a panel.

VALUES_QUERY_KEY = "values"
VECTOR_QUERY_KEY = "vector"
VALUES_LOAD_KEY = "load"


def encode_values_share(
    archetype_id: str | None = None,
    vector: Any = None,
    *,
    load: bool = False,
    public_app_url: str = PUBLIC_APP_URL,
) -> str:
    """Shareable ``/build`` URL for a starting philosophy or an edited vector.

    ``vector`` may be a :class:`~fiscal_model.composer.values_schema.ValuesVector`
    or any mapping of its fields; anything unusable is dropped rather than
    encoded, so a bad call produces a plain ``/build`` link instead of a broken
    one.
    """
    params: dict[str, str] = {}

    slug = _normalize_query_value(archetype_id)
    if slug:
        params[VALUES_QUERY_KEY] = slug

    token = _encode_vector_token(vector)
    if token:
        params[VECTOR_QUERY_KEY] = token

    if load and params:
        params[VALUES_LOAD_KEY] = "1"

    if not params:
        return f"{public_app_url}/{BUILD_URL_PATH}"
    return f"{public_app_url}/{BUILD_URL_PATH}?{urlencode(params)}"


def _encode_vector_token(vector: Any) -> str:
    """``ValuesVector`` or mapping -> the ``?vector=`` payload; ``""`` if unusable."""
    if vector is None:
        return ""
    try:
        from fiscal_model.composer.values_schema import ValuesVector

        if not isinstance(vector, ValuesVector):
            vector = ValuesVector.from_dict(dict(vector))
        return vector.to_base64()
    except Exception:
        return ""


def decode_values_share(query_params: Mapping[str, Any]) -> dict[str, Any]:
    """Parse ``/build?values=…&vector=…&load=…`` into a restorable request.

    Returns ``{"archetype_id": str | None, "vector": ValuesVector | None,
    "load": bool}``. Both halves are validated: an unknown slug and an
    unreadable vector both come back as ``None``, because query strings are
    user input and the panel has a perfectly good default to fall back to.
    """
    archetype_id: str | None = None
    raw_values = _normalize_query_value(query_params.get(VALUES_QUERY_KEY))
    if raw_values:
        try:
            from fiscal_model.composer.archetypes import get_archetype

            archetype = get_archetype(raw_values)
        except Exception:  # pragma: no cover — a broken YAML must not 500 /build
            archetype = None
        if archetype is not None:
            archetype_id = archetype.id

    vector = None
    raw_vector = _normalize_query_value(query_params.get(VECTOR_QUERY_KEY))
    if raw_vector:
        try:
            from fiscal_model.composer.values_schema import ValuesVector

            vector = ValuesVector.from_base64(raw_vector)
        except Exception:  # pragma: no cover — defensive
            vector = None

    return {
        "archetype_id": archetype_id,
        "vector": vector,
        "load": _query_flag(query_params, VALUES_LOAD_KEY),
    }
