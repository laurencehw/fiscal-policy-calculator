"""
The single result object and the shared result panel.

One run produces one :class:`ScoredResult`. Every surface that shows a number
— the headline, Key Metrics, the decomposition waterfall, the Dynamic view, the
deep sub-views, Copy Summary, CSV, the text export and the share link — renders
from that object, so they cannot disagree.

Three rules, implemented here and in
``fiscal_model/ui/tabs/{results_summary,dynamic_scoring}.py``:

1. **One sign convention app-wide: + increases the deficit**, stated once in
   the panel caption (``results_summary.SIGN_CONVENTION_CAPTION``).
2. **The headline is always the conventional score** (static + behavioral).
   Flipping dynamic scoring never moves it, so a calibrated preset keeps
   matching its official benchmark. Dynamic scoring adds a labeled
   "Dynamic view" (revenue feedback, debt service, dynamic total) computed by
   one function — ``dynamic_scoring.compute_dynamic_view`` — from the same
   macro adapter the Economic Effects tab runs.
3. **Stale results are never displayed as current.** The panel recomputes the
   policy-spec hash on every render; if the form or the settings moved since
   the run, it renders "Configuration changed — score again to refresh"
   *instead of* the numbers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import streamlit as _st

#: Session-state key holding the current :class:`ScoredResult`. Registered in
#: ``fiscal_model/ui/session_state.py`` as ``KEY_SCORED_RESULT``.
SCORED_RESULT_KEY = "scored_result"

#: Settings that change the *number*. Presentation-only settings (dark mode)
#: are deliberately excluded so a theme toggle does not invalidate a run.
SCORING_SETTING_KEYS: tuple[str, ...] = (
    "use_real_data",
    "dynamic_scoring",
    "macro_model",
    "use_microsim",
    "use_microsim_distribution",
    "data_year",
)

INVALIDATION_NOTICE = (
    "**Configuration changed — score again to refresh.** "
    "The inputs no longer match the last run, so the previous numbers are "
    "hidden rather than shown as current."
)

DYNAMIC_TOGGLE_LABEL = "Dynamic scoring"
DYNAMIC_TOGGLE_HELP = (
    "Adds a labeled Dynamic view (revenue feedback, debt service, dynamic "
    "total) using FRB/US-calibrated multipliers. The headline stays the "
    "conventional score either way."
)
_DYNAMIC_SCORING_KEY = "sidebar_setting_dynamic_scoring"


# ---------------------------------------------------------------------------
# The result object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Benchmark:
    """An official score this result is measured against."""

    name: str
    official_billions: float
    source: str
    source_date: str
    source_url: str | None = None
    notes: str = ""
    #: True when the benchmark scores *this* policy; False when it is only the
    #: nearest same-signed validated anchor for an uncalibrated run.
    is_exact: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "official_billions": self.official_billions,
            "source": self.source,
            "source_date": self.source_date,
            "source_url": self.source_url,
            "notes": self.notes,
            "is_exact": self.is_exact,
        }


@dataclass(frozen=True)
class ScoredResult:
    """Everything one completed run says, in one immutable object."""

    policy_spec_hash: str
    policy_name: str
    display_name: str
    mode: str  # "conventional" | "dynamic"
    window: str  # e.g. "FY2026-FY2035"
    headline: float  # conventional 10-year deficit effect (+ = adds deficit)
    static: float
    behavioral: float
    feedback: float  # macro-adapter revenue feedback; 0.0 when conventional
    debt_service: float
    dynamic_total: float
    per_year: list[float]
    tier: str  # "calibrated" | "benchmarked" | "generic"
    tier_label: str
    benchmark: dict[str, Any] | None
    baseline_vintage: str
    policy_status: str
    created_at: str
    sensitivity: tuple[float, float] | None
    sensitivity_note: str = ""
    is_spending: bool = False
    macro_model: str | None = None
    window_start: int = 0
    window_end: int = 0
    n_years: int = 10
    accuracy_pct: float | None = None
    credibility: Any = field(default=None, repr=False, compare=False)

    # -- construction -------------------------------------------------------

    @classmethod
    def from_pipeline(
        cls,
        *,
        result_data: dict[str, Any],
        policy_spec_hash: str,
        dynamic_scoring: bool,
        dynamic_view: Any = None,
        cbo_score_map: dict[str, dict[str, Any]] | None = None,
        baseline_vintage: str | None = None,
    ) -> ScoredResult:
        """Build the object at the single point where a run completes.

        Called from ``calculation_controller.execute_calculation_if_requested``
        immediately after the scorer returns, with the ``DynamicView`` from the
        one macro-adapter run this result gets.
        """
        from fiscal_model.ui.tabs.results_summary import summarize_result

        summary = summarize_result(
            result_data,
            dynamic_scoring=dynamic_scoring,
            dynamic_view=dynamic_view,
            cbo_score_map=cbo_score_map,
            baseline_vintage=baseline_vintage,
        )
        return cls(
            policy_spec_hash=policy_spec_hash,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **summary,
        )

    # -- convenience --------------------------------------------------------

    @property
    def is_dynamic(self) -> bool:
        return self.mode == "dynamic"

    @property
    def benchmark_obj(self) -> Benchmark | None:
        if not self.benchmark:
            return None
        return Benchmark(**{k: v for k, v in self.benchmark.items()})

    def as_dict(self) -> dict[str, Any]:
        """Serializable view (drops the live credibility object)."""
        return {
            "policy_spec_hash": self.policy_spec_hash,
            "policy_name": self.policy_name,
            "display_name": self.display_name,
            "mode": self.mode,
            "window": self.window,
            "headline": self.headline,
            "static": self.static,
            "behavioral": self.behavioral,
            "feedback": self.feedback,
            "debt_service": self.debt_service,
            "dynamic_total": self.dynamic_total,
            "per_year": list(self.per_year),
            "tier": self.tier,
            "tier_label": self.tier_label,
            "benchmark": dict(self.benchmark) if self.benchmark else None,
            "baseline_vintage": self.baseline_vintage,
            "policy_status": self.policy_status,
            "created_at": self.created_at,
            "sensitivity": list(self.sensitivity) if self.sensitivity else None,
            "sensitivity_note": self.sensitivity_note,
            "is_spending": self.is_spending,
            "macro_model": self.macro_model,
        }


# ---------------------------------------------------------------------------
# Spec hash + session storage
# ---------------------------------------------------------------------------


def compute_policy_spec_hash(calc_context: dict[str, Any], settings: dict[str, Any]) -> str:
    """Hash the inputs that define a score: the form/preset plus model settings.

    Reuses ``controller_utils.compute_run_id`` so the run id written by the
    calculation controller and the spec hash carried on the result are the same
    string — one identity, no drift between "is this stale?" and "which run
    produced this?".
    """
    from fiscal_model.ui.controller_utils import compute_run_id

    scoring_settings = {key: settings.get(key) for key in SCORING_SETTING_KEYS}
    return compute_run_id(calc_context=calc_context, settings=scoring_settings)


def store_scored_result(st_module: Any, scored: ScoredResult | None) -> None:
    st_module.session_state[SCORED_RESULT_KEY] = scored


def get_scored_result(st_module: Any) -> ScoredResult | None:
    session = getattr(st_module, "session_state", None)
    if session is None:
        return None
    try:
        return session.get(SCORED_RESULT_KEY)
    except Exception:  # pragma: no cover — exotic session stand-ins
        return getattr(session, SCORED_RESULT_KEY, None)


def resolve_baseline_vintage() -> str:
    """Live baseline vintage (``CBO Feb 2026``), not a hard-coded string."""
    from fiscal_model.ui.tabs.results_summary import DEFAULT_BASELINE_VINTAGE

    try:
        from fiscal_model.ui.cache import get_health_snapshot

        vintage = (get_health_snapshot().get("baseline") or {}).get("vintage")
    except Exception:
        return DEFAULT_BASELINE_VINTAGE
    if not vintage or vintage == "unknown":
        return DEFAULT_BASELINE_VINTAGE
    text = str(vintage)
    return text if text.upper().startswith("CBO") else f"CBO {text}"


# ---------------------------------------------------------------------------
# Panel pieces
# ---------------------------------------------------------------------------


def render_headline(result: ScoredResult, *, st_module: Any = None, result_data: dict | None = None) -> None:
    """Tier badge, big number, sign convention, sensitivity, provenance."""
    from fiscal_model.ui.tabs.results_summary import render_headline_block

    st_module = st_module or _st
    render_headline_block(st_module, result, result_data or {})


def render_decomposition(
    result: ScoredResult, *, st_module: Any = None, result_data: dict | None = None
) -> None:
    """Key Metrics, the labeled Dynamic view, and the waterfall."""
    from fiscal_model.ui.tabs.results_summary import render_metrics_block

    st_module = st_module or _st
    render_metrics_block(st_module, result, result_data or {})


def render_exports(
    result: ScoredResult, *, st_module: Any = None, result_data: dict | None = None
) -> None:
    """CSV / text / share link / Copy Summary — all carrying full provenance."""
    from fiscal_model.ui.tabs.results_summary import render_export_block

    st_module = st_module or _st
    render_export_block(st_module, result, result_data or {})


def render_deep_views(
    result: ScoredResult,
    *,
    st_module: Any = None,
    deps: Any,
    settings: dict[str, Any],
    result_data: dict[str, Any],
    model_available: bool = True,
) -> None:
    """Distribution · Economic Effects · Scoring Models · Generational · State · Details."""
    from fiscal_model.ui.tabs_controller import build_main_tabs, render_result_tabs

    st_module = st_module or _st
    tabs = build_main_tabs(st_module=st_module, mode="", include_summary=False)
    render_result_tabs(
        st_module=st_module,
        deps=deps,
        tabs=tabs,
        settings=settings,
        model_available=model_available,
        is_spending=bool(result.is_spending),
        mode="",
        include_summary=False,
        scored=result,
    )
    del result_data


def render_invalidation_notice(st_module: Any = None) -> None:
    """Chip ⑩: replace the numbers, don't just warn above them."""
    st_module = st_module or _st
    st_module.warning(INVALIDATION_NOTICE)


def render_results(
    result: ScoredResult | None,
    *,
    variant: str = "full",
    st_module: Any = None,
    deps: Any = None,
    settings: dict[str, Any] | None = None,
    result_data: dict[str, Any] | None = None,
    model_available: bool = True,
) -> None:
    """Render the shared result panel.

    ``variant="full"`` — headline, decomposition, exports, and the deep views
    as tabs inside the panel (Tailor and Explore).
    ``variant="compact"`` — headline and decomposition only, for embedding
    beside something else (the package-level Build scoreboard).
    """
    st_module = st_module or _st
    if result is None:
        st_module.info("Score a policy to see results here.")
        return

    result_data = result_data or {}
    render_headline(result, st_module=st_module, result_data=result_data)
    render_decomposition(result, st_module=st_module, result_data=result_data)
    if variant == "compact":
        return

    render_exports(result, st_module=st_module, result_data=result_data)
    if deps is not None and settings is not None:
        st_module.markdown("---")
        render_deep_views(
            result,
            st_module=st_module,
            deps=deps,
            settings=settings,
            result_data=result_data,
            model_available=model_available,
        )


# ---------------------------------------------------------------------------
# The inline dynamic-scoring toggle (DECISIONS #2 — no sidebar anywhere)
# ---------------------------------------------------------------------------


def render_inline_dynamic_toggle(
    st_module: Any, settings: dict[str, Any], frozen: Any = None
) -> bool:
    """Render the dynamic toggle beside the Score button and sync ``settings``.

    Uses the pre-existing ``sidebar_setting_dynamic_scoring`` key so share
    links, the settings popover and this control are the same piece of state.
    The page claims the key from the chrome first (see
    ``settings_controller.claim_inline_dynamic_toggle``) — two widgets sharing a
    key in one run is a Streamlit ``DuplicateWidgetID`` error.

    Under a frozen assignment link the toggle renders disabled and the link's
    value wins, exactly as in the ⚙ popover: the two controls are one piece of
    state, so locking one and not the other would lock nothing.
    """
    widget = getattr(st_module, "toggle", None) or st_module.checkbox
    if _DYNAMIC_SCORING_KEY not in st_module.session_state:
        st_module.session_state[_DYNAMIC_SCORING_KEY] = bool(
            settings.get("dynamic_scoring", False)
        )
    kwargs: dict[str, Any] = {"key": _DYNAMIC_SCORING_KEY, "help": DYNAMIC_TOGGLE_HELP}
    label = DYNAMIC_TOGGLE_LABEL
    if frozen is not None:
        from fiscal_model.ui.frozen_links import FROZEN_LABEL

        kwargs["disabled"] = True
        kwargs["help"] = f"{FROZEN_LABEL} — set by the assignment link."
    enabled = bool(widget(label, **kwargs))
    if frozen is not None:
        enabled = bool(frozen.dynamic)
    settings["dynamic_scoring"] = enabled
    if enabled and not settings.get("macro_model"):
        settings["macro_model"] = st_module.session_state.get(
            "setting_macro_model", "FRB/US-Lite (recommended)"
        )
    return enabled


# ---------------------------------------------------------------------------
# The shared score-a-policy surface (Tailor + Explore)
# ---------------------------------------------------------------------------


def _full_width_button(st_module: Any, label: str) -> bool:
    """Primary Score button, full width.

    ``use_container_width`` is deprecated from Streamlit 1.56 and renders a
    notice in the app itself; ``width="stretch"`` is the replacement. The
    fallback keeps the hand-rolled ``st_module`` fakes in the UI tests working.
    """
    try:
        return bool(
            st_module.button(
                label, type="primary", width="stretch", key="score_policy_button"
            )
        )
    except TypeError:  # pragma: no cover - older Streamlit / test fakes
        return bool(st_module.button(label, type="primary", key="score_policy_button"))


def render_score_surface(
    *,
    st_module: Any,
    deps: Any,
    settings: dict[str, Any],
    app_root: Any,
    modes: tuple[str, ...],
    inputs_heading: str,
    score_label: str = "Score this policy",
    show_quick_start: bool = False,
    split_layout: bool = True,
    before_inputs: Any = None,
    tax_input_kwargs: dict[str, Any] | None = None,
    frozen: Any = None,
) -> None:
    """Inputs on the left, the shared result panel on the right.

    The successor to ``app_controller.render_policy_workbench``: same widgets,
    same session keys, same calculation pipeline — plus the inline dynamic
    toggle, the single result object, and hash-based invalidation.

    ``frozen`` is the :class:`~fiscal_model.ui.frozen_links.FrozenAssignment`
    an ``?frozen=1`` link put in force. The whole input column is then rendered
    through ``frozen_links.frozen_input_module`` — the same widgets, on the
    same keys, holding the same values, but disabled — so the student can
    press Score and read the number without being able to change what is
    scored. Quick-start cards are suppressed for the same reason: they are
    one-click preset switches.

    ``before_inputs`` is called with the module the inputs render through, so
    a page that owns part of its own form (Tailor's chips) is frozen too.
    """
    from fiscal_model.ui.app_controller import (
        _HOW_SCORED_MARKDOWN,
        _apply_pending_sidebar_updates,
        render_quick_start,
    )
    from fiscal_model.ui.calculation_controller import (
        ensure_results_state,
        execute_calculation_if_requested,
        render_policy_inputs,
    )
    from fiscal_model.ui.session_state import KEY_QS_CALCULATE

    _apply_pending_sidebar_updates(st_module=st_module)

    hero = st_module.container()

    if split_layout:
        input_col, result_col = st_module.columns([2, 3], gap="large")
    else:
        input_col = st_module.container(border=True)
        result_col = st_module.container()

    from fiscal_model.ui.frozen_links import (
        frozen_input_module,
        render_frozen_banner,
    )

    inputs_module = frozen_input_module(st_module, frozen)

    with input_col:
        st_module.subheader(inputs_heading)
        if frozen is not None:
            render_frozen_banner(st_module, frozen)
        if before_inputs is not None:
            before_inputs(inputs_module)
        calc_context = render_policy_inputs(
            st_module=inputs_module,
            deps=deps,
            modes=modes,
            tax_input_kwargs=tax_input_kwargs,
        )

        button_col, toggle_col = st_module.columns([3, 2])
        with button_col:
            calculate = _full_width_button(st_module, score_label)
        with toggle_col:
            render_inline_dynamic_toggle(st_module, settings, frozen)

        if getattr(st_module.session_state, KEY_QS_CALCULATE, False):
            del st_module.session_state[KEY_QS_CALCULATE]
            calculate = True
        calc_context["calculate"] = calculate

    spec_hash = compute_policy_spec_hash(calc_context, settings)
    calc_context["run_id"] = spec_hash
    st_module.session_state.current_run_id = spec_hash

    with hero:
        if show_quick_start and frozen is None:
            render_quick_start(
                st_module=st_module, calculating=bool(calc_context.get("calculate"))
            )
        with st_module.expander("🔍 How is this scored?", expanded=False):
            st_module.markdown(_HOW_SCORED_MARKDOWN)

    with result_col:
        st_module.markdown(RESULTS_ANCHOR_HTML, unsafe_allow_html=True)

        ensure_results_state(st_module=st_module)
        execute_calculation_if_requested(
            st_module=st_module,
            deps=deps,
            app_root=app_root,
            model_available=True,
            calc_context=calc_context,
            settings=settings,
        )

        result_data = st_module.session_state.get("results")
        if calc_context.get("calculate") and result_data:
            scroll_to_results_anchor(run_id=spec_hash)

        render_result_panel(
            st_module=st_module,
            deps=deps,
            settings=settings,
            spec_hash=spec_hash,
            score_label=score_label,
            frozen=frozen,
        )


def render_result_panel(
    *,
    st_module: Any,
    deps: Any,
    settings: dict[str, Any],
    spec_hash: str,
    score_label: str = "Score this policy",
    model_available: bool = True,
    frozen: Any = None,
) -> None:
    """Render the panel for whatever is in session state, or say why not.

    Chip ⑩: when the recomputed spec hash differs from the stored result's, the
    stale numbers are *replaced* by the invalidation notice.

    Under a frozen assignment link the number carries a compact provenance
    line naming the baseline it was scored on, the scoring mode, and that a
    person — not the reader — chose both.
    """
    result_data = st_module.session_state.get("results")
    if not result_data:
        _render_empty_state(st_module, score_label)
        return

    if result_data.get("is_microsim"):
        from fiscal_model.ui.tabs.results_summary import render_microsim_summary

        render_microsim_summary(st_module, result_data)
        return

    scored = get_scored_result(st_module)
    if scored is None or scored.policy_spec_hash != spec_hash:
        render_invalidation_notice(st_module)
        st_module.caption(
            f"Click **{score_label}** to re-run with the current configuration."
        )
        return

    if frozen is not None:
        from fiscal_model.ui.frozen_links import render_frozen_provenance

        render_frozen_provenance(st_module, scored, frozen, spec_hash=spec_hash)

    render_results(
        scored,
        variant="full",
        st_module=st_module,
        deps=deps,
        settings=settings,
        result_data=result_data,
        model_available=model_available,
    )


def _render_empty_state(st_module: Any, score_label: str) -> None:
    st_module.markdown("### Your result appears here")
    st_module.markdown(
        f"Choose or define a policy, then click **{score_label}** to see the "
        "10-year budgetary effect, its confidence tier, and a sensitivity band."
    )
    st_module.caption(
        "Scores use CBO methodology with IRS Statistics of Income data. "
        "Calibrated presets reproduce official scores by construction; "
        "custom policies are genuine out-of-sample predictions (\\~8% mean error)."
    )


def now_ts() -> float:
    """Wall-clock helper (kept here so pages don't import ``time`` directly)."""
    return time.time()


# ── Anchor scroll ────────────────────────────────────────────────────────
#
# One utility, one call site. It lives beside ``render_score_surface`` — the
# only place that both emits ``#results-anchor`` and scrolls to it — rather
# than in ``app_controller``, which no longer renders results at all
# (REDESIGN_PLAN.md §8.2).

RESULTS_ANCHOR_ID = "results-anchor"

RESULTS_ANCHOR_HTML = f'<div id="{RESULTS_ANCHOR_ID}"></div>'


def scroll_to_results_anchor(run_id: str | None = None) -> None:
    """Scroll the result heading into view after a Score/Calculate click.

    Streamlit sanitizes ``<script>`` in markdown, so this uses a zero-height
    component iframe (same-origin) to scroll the parent document. Clicking
    Score otherwise produces no visible change on a phone — the result panel
    renders well below the fold.

    Two failure modes this must handle:

    - Streamlit reuses a component iframe when its HTML is byte-identical, so
      the script would run only on the *first* calculation. Embedding the run
      id plus a nonce makes each calculation's HTML unique and forces a reload.
    - The anchor may not be laid out yet when the iframe script first runs (the
      page is still rendering), so retry briefly instead of giving up.
    """
    try:
        import streamlit.components.v1 as components

        # run_id repeats for identical settings, so add a per-render nonce —
        # this only renders on Score clicks, so uniqueness is cheap.
        cache_buster = f"{run_id or 'unkeyed'}:{time.time_ns()}"
        components.html(
            "<script>"
            f"/* run:{cache_buster} */"
            "const tryScroll = (n) => {"
            "  const anchor = window.parent.document.getElementById("
            f"'{RESULTS_ANCHOR_ID}');"
            "  if (anchor && anchor.isConnected) {"
            "    anchor.scrollIntoView({behavior: 'smooth', block: 'start'});"
            "  } else if (n > 0) {"
            "    setTimeout(() => tryScroll(n - 1), 150);"
            "  }"
            "};"
            "setTimeout(() => tryScroll(10), 100);"
            "</script>",
            height=0,
        )
    except Exception:
        # Non-Streamlit contexts (unit tests with stub st modules) skip the scroll.
        pass
