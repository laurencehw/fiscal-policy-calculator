"""
Type-safe session state for the Streamlit app.

Streamlit's ``session_state`` is a loose dict. Over time the app accrued keys
that are set in one place and read in many, with no central inventory. This
module provides:

* A canonical enum of known keys (so typos become a failing test)
* A small dataclass-style schema describing defaults and types
* ``initialize_session_state`` to make sure every key exists with the right
  default before widgets are constructed
* ``SafeSessionState``: a thin wrapper with typed accessors so callers can
  read expected keys without writing ``.get(..., default)`` everywhere

Keeping this in one file means future widget renames or additions have a
single place to update, eliminating a class of silent bugs where a widget key
gets renamed in one tab and stale state leaks into another.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical keys
# ---------------------------------------------------------------------------
#
# Grouped by purpose. Keep alphabetized within each group so merges stay
# clean. Adding a key here is the authoritative way to teach the app about
# new session state — ``initialize_session_state`` will default it, and
# tests that iterate over ``ALL_KEYS`` will cover it.


# Results lifecycle — populated by calculation_controller after a run
KEY_RESULTS = "results"
# The single result object (``components.results.ScoredResult``). ``results``
# stays populated with the raw pipeline dict for back-compat; every *surface*
# reads this one instead.
KEY_SCORED_RESULT = "scored_result"
KEY_LAST_RUN_ID = "last_run_id"
KEY_LAST_RUN_AT = "last_run_at"
KEY_RESULTS_RUN_ID = "results_run_id"
KEY_CURRENT_RUN_ID = "current_run_id"

# Quick-start card flow
KEY_QS_CALCULATE = "qs_calculate"
KEY_QUICK_START_DISMISSED = "quick_start_dismissed"
KEY_PENDING_SIDEBAR_UPDATES = "_pending_sidebar_updates"

# Sidebar widgets (must match the ``key=`` params on the widgets)
KEY_SIDEBAR_ANALYSIS_MODE = "sidebar_analysis_mode"
KEY_SIDEBAR_POLICY_AREA = "sidebar_policy_area"
KEY_SIDEBAR_PRESET_CHOICE = "sidebar_preset_choice"
KEY_SIDEBAR_SPENDING_PRESET = "sidebar_spending_preset"

# Settings
KEY_DARK_MODE = "dark_mode"
# Widget key on the "Enable dynamic scoring" checkbox
# (``settings_controller._DYNAMIC_SCORING_KEY``); also written by share links.
# It used to be declared here as "dynamic_scoring_enabled", a literal nothing
# read or wrote, so ``SafeSessionState`` logged "unknown key" for the real one.
KEY_DYNAMIC_SCORING = "sidebar_setting_dynamic_scoring"

# Share-link handling — matches ``share_links._SHARE_TOKEN_KEY`` (was declared
# here as the never-used "_share_link_token").
KEY_SHARE_TOKEN = "_applied_share_token"

# Ask assistant
KEY_ASK_HISTORY = "ask_history"

# ---------------------------------------------------------------------------
# Redesign prep - explicit widget keys (behaviour-neutral)
# ---------------------------------------------------------------------------
#
# The custom tax form, the spending form and the model settings were rendered
# with unkeyed widgets, so their values lived only in Streamlit's positional
# widget identity. Moving them out of the sidebar (onto ``/tailor`` and a
# settings popover) would silently reset every field. Pinning them to explicit
# keys makes that move a no-op.
#
# Naming: ``tailor_tax_*`` / ``tailor_spend_*`` for the two policy forms and
# ``setting_*`` for model settings. Pre-existing keys keep their (now stale)
# ``sidebar_*`` prefix - renaming them would break share links.

# Tailor page shell (``app_pages/tailor.py``) - Phase 4
# "Start from: Blank / A preset" and the Income / Corporate / Capital gains /
# Spending chips. The chips drive both the analysis mode and ``tailor_tax_type``,
# so the form module must not render its own type selectbox on that key.
KEY_TAILOR_START_FROM = "tailor_start_from"
KEY_TAILOR_SEED_PRESET = "tailor_seed_preset"
KEY_TAILOR_POLICY_KIND = "tailor_policy_kind"
#: Code key: which preset last seeded the form fields (so a manual edit sticks).
KEY_TAILOR_SEED_APPLIED = "_tailor_seed_applied"

# Tailor - custom tax policy form (``ui/policy_input_tax.py``)
KEY_TAILOR_TAX_POLICY_NAME = "tailor_tax_policy_name"
KEY_TAILOR_TAX_TYPE = "tailor_tax_type"
KEY_TAILOR_TAX_RATE_CHANGE_PCT = "tailor_tax_rate_change_pct"
KEY_TAILOR_TAX_THRESHOLD_CHOICE = "tailor_tax_threshold_choice"
KEY_TAILOR_TAX_CUSTOM_THRESHOLD = "tailor_tax_custom_threshold"
KEY_TAILOR_TAX_DURATION = "tailor_tax_duration"
KEY_TAILOR_TAX_PHASE_IN = "tailor_tax_phase_in"
KEY_TAILOR_TAX_ETI = "tailor_tax_eti"
KEY_TAILOR_TAX_MANUAL_TAXPAYERS = "tailor_tax_manual_taxpayers"
KEY_TAILOR_TAX_MANUAL_AVG_INCOME = "tailor_tax_manual_avg_income"
KEY_TAILOR_TAX_ORDINARY_BASE = "tailor_tax_ordinary_base"

# Tailor - capital-gains sub-form (same module)
KEY_TAILOR_TAX_CG_BASE_YEAR = "tailor_tax_cg_base_year"
KEY_TAILOR_TAX_CG_BASELINE_RATE = "tailor_tax_cg_baseline_rate"
KEY_TAILOR_TAX_CG_BASELINE_REALIZATIONS = "tailor_tax_cg_baseline_realizations"
KEY_TAILOR_TAX_CG_TIME_VARYING = "tailor_tax_cg_time_varying"
KEY_TAILOR_TAX_CG_SHORT_RUN_ELASTICITY = "tailor_tax_cg_short_run_elasticity"
KEY_TAILOR_TAX_CG_LONG_RUN_ELASTICITY = "tailor_tax_cg_long_run_elasticity"
KEY_TAILOR_TAX_CG_TRANSITION_YEARS = "tailor_tax_cg_transition_years"
KEY_TAILOR_TAX_CG_REALIZATION_ELASTICITY = "tailor_tax_cg_realization_elasticity"
KEY_TAILOR_TAX_CG_ELIMINATE_STEP_UP = "tailor_tax_cg_eliminate_step_up"
KEY_TAILOR_TAX_CG_STEP_UP_EXEMPTION = "tailor_tax_cg_step_up_exemption"
KEY_TAILOR_TAX_CG_GAINS_AT_DEATH = "tailor_tax_cg_gains_at_death"
KEY_TAILOR_TAX_CG_LOCK_IN_MULTIPLIER = "tailor_tax_cg_lock_in_multiplier"

# Tailor - spending program form (``ui/policy_input_spending.py``)
KEY_TAILOR_SPEND_PROGRAM_NAME = "tailor_spend_program_name"
KEY_TAILOR_SPEND_ANNUAL = "tailor_spend_annual"
KEY_TAILOR_SPEND_CATEGORY = "tailor_spend_category"
KEY_TAILOR_SPEND_DURATION = "tailor_spend_duration"
KEY_TAILOR_SPEND_GROWTH_RATE = "tailor_spend_growth_rate"
KEY_TAILOR_SPEND_MULTIPLIER = "tailor_spend_multiplier"
KEY_TAILOR_SPEND_ONE_TIME = "tailor_spend_one_time"
# Code key (not a widget): which spending preset last seeded the fields above.
# Unkeyed widgets re-derived their default from the preset on every switch
# because the default was part of the widget identity; with stable keys the
# re-seed has to be explicit, and this records what was last applied.
KEY_TAILOR_SPEND_PRESET_APPLIED = "_tailor_spend_preset_applied"

# Model settings (``ui/settings_controller.py``). ``dark_mode`` (code) and
# ``sidebar_setting_dynamic_scoring`` (widget) already exist elsewhere.
KEY_SETTING_DARK_MODE = "setting_dark_mode"
KEY_SETTING_MACRO_MODEL = "setting_macro_model"
KEY_SETTING_USE_REAL_DATA = "setting_use_real_data"
KEY_SETTING_DATA_YEAR = "setting_data_year"
KEY_SETTING_USE_MICROSIM = "setting_use_microsim"
KEY_SETTING_USE_MICROSIM_DISTRIBUTION = "setting_use_microsim_distribution"

# ---------------------------------------------------------------------------
# Build page (``ui/tabs/deficit_target.py``) - Phase 3
# ---------------------------------------------------------------------------
#
# ``build_selection`` is the durable, non-widget record of the checked policy
# ids. The per-policy ``dt_<preset_id>`` checkboxes cannot be the source of
# truth on their own: Streamlit garbage-collects the session state of a widget
# that is not instantiated in a run, so filtering the list with the search box
# would silently un-check everything the filter hides. The checkboxes are
# reconciled from this list at the top of every render instead.

KEY_BUILD_MODE = "build_mode"
KEY_BUILD_SEARCH = "build_search"
KEY_BUILD_METRIC = "build_metric"
KEY_BUILD_TARGET_PCT = "build_target_pct"
KEY_BUILD_TARGET_USD = "build_target_usd"
#: Code key: list[str] of selected build ids, in selection order.
KEY_BUILD_SELECTION = "build_selection"
#: Code key: overlap conflicts dropped on this run, rendered once as st.info.
KEY_BUILD_DROPPED_NOTICE = "_build_dropped_notice"
#: Code key: hash of the last applied ``/build?policies=...`` link, so a share
#: link restores once instead of clobbering edits on every rerun.
KEY_BUILD_SHARE_TOKEN = "_build_share_token"


# ---------------------------------------------------------------------------
# Cross-page widget persistence (the "shadow key" mirror)
# ---------------------------------------------------------------------------
#
# Streamlit scopes widget state by ``active_script_hash``. Under
# ``st.navigation`` every page is a different script, so a keyed widget that
# does not render on the current page is garbage-collected: leaving ``/tailor``
# for ``/explore`` and coming back re-seeded every ``tailor_*`` field to its
# default (verified with ``tailor_tax_policy_name``).
#
# Fix: mirror each keyed value to a plain, non-widget session key. Plain keys
# are never GC'd, so the mirror survives the page switch and the value is
# restored before the widget is instantiated.

SHADOW_PREFIX = "_shadow:"

#: Records the last value *code* wrote to a widget key. Streamlit resolves a
#: user key through the widget's own state first and falls back to the plain
#: session-state entry; once the widget is garbage-collected that fallback is
#: exactly this value. So "the key still holds the last thing we wrote, but the
#: mirror holds something else" is a precise signal that the widget state was
#: dropped on another page — and that the mirror, not the key, is the truth.
SEED_ECHO_PREFIX = "_shadow_seed:"

#: Key namespaces that get the mirror treatment: the two Tailor policy forms,
#: the model settings, and the preset pickers. These are the widget keys that
#: render on some pages and not others. Result/run bookkeeping keys are left
#: alone — they are code state, and ``results`` is large enough that mirroring
#: it would double the session's memory for no benefit.
MIRRORED_KEY_PREFIXES: tuple[str, ...] = ("tailor_", "setting_", "sidebar_")

_MISSING = object()


def shadow_key(key: str) -> str:
    """Name of the non-widget mirror for ``key``."""
    return f"{SHADOW_PREFIX}{key}"


def _echo_key(key: str) -> str:
    """Name of the record of the last code-written value for ``key``."""
    return f"{SEED_ECHO_PREFIX}{key}"


def _write_widget_value(state: Any, key: str, value: Any) -> None:
    """Write a value by code and keep the mirror and echo in step."""
    state[key] = value
    state[shadow_key(key)] = value
    state[_echo_key(key)] = value


def _is_stale_echo(state: Any, key: str) -> bool:
    """True when ``state[key]`` is Streamlit's echo of our own last write.

    That happens when the widget did not render on the page the user was just
    on: its state is gone and the lookup falls back to the code-written value,
    silently reverting the field. The mirror still holds what the user chose.
    """
    mirror = shadow_key(key)
    echo = _echo_key(key)
    if mirror not in state or echo not in state:
        return False
    return state[key] == state[echo] and state[mirror] != state[echo]


def seed_widget_default(st_module: Any, key: str, default: Any, *, force: bool = False) -> None:
    """Seed a widget key before instantiation, mirroring it across pages.

    Passing both ``key=`` and ``value=``/``index=`` makes Streamlit warn once
    the key is pre-seeded, so the pattern throughout the app is: seed here,
    omit the default on the widget.

    ``force=True`` re-seeds an existing key — needed where an unkeyed widget's
    identity used to include its default (the spending form's preset-driven
    fields), so switching presets must overwrite explicitly.
    """
    state = st_module.session_state
    if force:
        _write_widget_value(state, key, default)
        return
    if key not in state:
        mirror = shadow_key(key)
        _write_widget_value(state, key, state.get(mirror, default))
        return
    if _is_stale_echo(state, key):
        _write_widget_value(state, key, state[shadow_key(key)])
        return
    state[shadow_key(key)] = state[key]


def restore_widget_value(st_module: Any, key: str) -> None:
    """Bring a widget value back from its mirror after a page switch.

    Used where there is no single default to seed — the preset pickers resolve
    theirs from the options actually available this run.
    """
    state = st_module.session_state
    mirror = shadow_key(key)
    if key not in state:
        if mirror in state:
            _write_widget_value(state, key, state[mirror])
        return
    if _is_stale_echo(state, key):
        _write_widget_value(state, key, state[mirror])
        return
    state[mirror] = state[key]


def mirror_widget_value(st_module: Any, key: str) -> None:
    """Copy a widget's current value into its mirror (call after the widget)."""
    state = st_module.session_state
    if key in state:
        state[shadow_key(key)] = state[key]


def forget_widget_value(st_module: Any, key: str) -> None:
    """Drop a widget value *and* its mirror.

    The stale-option guards (a stored preset that is no longer in the option
    list) must clear the mirror too, or the next render restores the value the
    guard just evicted.
    """
    st_module.session_state.pop(key, None)
    st_module.session_state.pop(shadow_key(key), None)
    st_module.session_state.pop(_echo_key(key), None)


@dataclass(frozen=True)
class _KeySpec:
    """Declarative spec for a single session-state key."""

    name: str
    default: Any
    expected_type: type | tuple[type, ...] | None = None
    """If set, values written via ``SafeSessionState`` are type-checked."""


_SESSION_KEYS: tuple[_KeySpec, ...] = (
    # Results
    _KeySpec(KEY_RESULTS, None),
    _KeySpec(KEY_SCORED_RESULT, None),
    _KeySpec(KEY_LAST_RUN_ID, None, (str, type(None))),
    _KeySpec(KEY_LAST_RUN_AT, None, (float, int, type(None))),
    _KeySpec(KEY_RESULTS_RUN_ID, None, (str, type(None))),
    _KeySpec(KEY_CURRENT_RUN_ID, None, (str, type(None))),
    # Quick-start
    _KeySpec(KEY_QS_CALCULATE, False, bool),
    _KeySpec(KEY_QUICK_START_DISMISSED, False, bool),
    _KeySpec(KEY_PENDING_SIDEBAR_UPDATES, None),
    # Sidebar widget state
    _KeySpec(KEY_SIDEBAR_ANALYSIS_MODE, None, (str, type(None))),
    _KeySpec(KEY_SIDEBAR_POLICY_AREA, None, (str, type(None))),
    _KeySpec(KEY_SIDEBAR_PRESET_CHOICE, None, (str, type(None))),
    _KeySpec(KEY_SIDEBAR_SPENDING_PRESET, None, (str, type(None))),
    # Settings
    _KeySpec(KEY_DARK_MODE, False, bool),
    _KeySpec(KEY_DYNAMIC_SCORING, False, bool),
    # Share
    _KeySpec(KEY_SHARE_TOKEN, None, (str, type(None))),
    # Ask assistant — the tab initializes its own list to avoid a shared
    # mutable default; we still register the key here so it's documented.
    _KeySpec(KEY_ASK_HISTORY, None, (list, type(None))),
    # Tailor page shell
    _KeySpec(KEY_TAILOR_START_FROM, "Blank", str),
    _KeySpec(KEY_TAILOR_SEED_PRESET, None, (str, type(None))),
    _KeySpec(KEY_TAILOR_POLICY_KIND, "Income", str),
    _KeySpec(KEY_TAILOR_SEED_APPLIED, None, (str, type(None))),
    # Tailor - custom tax policy form
    _KeySpec(KEY_TAILOR_TAX_POLICY_NAME, "Tax Rate Change", str),
    _KeySpec(KEY_TAILOR_TAX_TYPE, "Income Tax Rate", str),
    _KeySpec(KEY_TAILOR_TAX_RATE_CHANGE_PCT, -2.0, float),
    _KeySpec(KEY_TAILOR_TAX_THRESHOLD_CHOICE, "Top earners ($400K+)", str),
    _KeySpec(KEY_TAILOR_TAX_CUSTOM_THRESHOLD, 400_000, int),
    _KeySpec(KEY_TAILOR_TAX_DURATION, 10, int),
    _KeySpec(KEY_TAILOR_TAX_PHASE_IN, 1, int),
    _KeySpec(KEY_TAILOR_TAX_ETI, 0.25, float),
    _KeySpec(KEY_TAILOR_TAX_MANUAL_TAXPAYERS, 0.0, float),
    _KeySpec(KEY_TAILOR_TAX_MANUAL_AVG_INCOME, 0, int),
    _KeySpec(KEY_TAILOR_TAX_ORDINARY_BASE, True, bool),
    # Tailor - capital-gains sub-form
    _KeySpec(KEY_TAILOR_TAX_CG_BASE_YEAR, 2024, int),
    _KeySpec(KEY_TAILOR_TAX_CG_BASELINE_RATE, 0.238, float),
    _KeySpec(KEY_TAILOR_TAX_CG_BASELINE_REALIZATIONS, 0.0, float),
    _KeySpec(KEY_TAILOR_TAX_CG_TIME_VARYING, True, bool),
    _KeySpec(KEY_TAILOR_TAX_CG_SHORT_RUN_ELASTICITY, 0.8, float),
    _KeySpec(KEY_TAILOR_TAX_CG_LONG_RUN_ELASTICITY, 0.4, float),
    _KeySpec(KEY_TAILOR_TAX_CG_TRANSITION_YEARS, 3, int),
    _KeySpec(KEY_TAILOR_TAX_CG_REALIZATION_ELASTICITY, 0.5, float),
    _KeySpec(KEY_TAILOR_TAX_CG_ELIMINATE_STEP_UP, False, bool),
    _KeySpec(KEY_TAILOR_TAX_CG_STEP_UP_EXEMPTION, 1_000_000, int),
    _KeySpec(KEY_TAILOR_TAX_CG_GAINS_AT_DEATH, 54.0, float),
    _KeySpec(KEY_TAILOR_TAX_CG_LOCK_IN_MULTIPLIER, 2.0, float),
    # Tailor - spending program form
    _KeySpec(KEY_TAILOR_SPEND_PROGRAM_NAME, "Infrastructure Investment", str),
    _KeySpec(KEY_TAILOR_SPEND_ANNUAL, 100.0, float),
    _KeySpec(KEY_TAILOR_SPEND_CATEGORY, "Infrastructure", str),
    _KeySpec(KEY_TAILOR_SPEND_DURATION, 10, int),
    _KeySpec(KEY_TAILOR_SPEND_GROWTH_RATE, 2.0, float),
    _KeySpec(KEY_TAILOR_SPEND_MULTIPLIER, 1.0, float),
    _KeySpec(KEY_TAILOR_SPEND_ONE_TIME, False, bool),
    _KeySpec(KEY_TAILOR_SPEND_PRESET_APPLIED, None, (str, type(None))),
    # Model settings. ``setting_data_year`` defaults to None and is resolved
    # against the years actually shipped under data_files/irs_soi at render.
    _KeySpec(KEY_SETTING_DARK_MODE, False, bool),
    _KeySpec(KEY_SETTING_MACRO_MODEL, "FRB/US-Lite (recommended)", str),
    _KeySpec(KEY_SETTING_USE_REAL_DATA, True, bool),
    _KeySpec(KEY_SETTING_DATA_YEAR, None, (int, type(None))),
    _KeySpec(KEY_SETTING_USE_MICROSIM, False, bool),
    _KeySpec(KEY_SETTING_USE_MICROSIM_DISTRIBUTION, True, bool),
    # Build page. ``build_selection`` defaults to None rather than [] so the
    # seeded default is not a single list object shared across sessions.
    _KeySpec(KEY_BUILD_MODE, "Start from scratch", str),
    _KeySpec(KEY_BUILD_SEARCH, "", str),
    _KeySpec(KEY_BUILD_METRIC, "% of GDP", str),
    _KeySpec(KEY_BUILD_TARGET_PCT, 3.0, float),
    _KeySpec(KEY_BUILD_TARGET_USD, 1000, int),
    _KeySpec(KEY_BUILD_SELECTION, None, (list, type(None))),
    _KeySpec(KEY_BUILD_DROPPED_NOTICE, None, (list, type(None))),
    _KeySpec(KEY_BUILD_SHARE_TOKEN, None, (str, type(None))),
)


ALL_KEYS: frozenset[str] = frozenset(spec.name for spec in _SESSION_KEYS)
_KEY_INDEX: dict[str, _KeySpec] = {spec.name: spec for spec in _SESSION_KEYS}


def initialize_session_state(st_module: Any) -> None:
    """Ensure every known key exists, preferring a mirrored value to the default.

    Safe to call multiple times per rerun. Never overwrites an existing
    value — Streamlit reruns depend on prior state being preserved.

    For widget keys (see :data:`MIRRORED_KEY_PREFIXES`) the seed is taken from
    the mirror when one exists, and the write is recorded as a *code* write.
    Both halves matter for surviving a page switch: this function runs on every
    page via ``app_controller.bootstrap_page``, so it is the write Streamlit
    later echoes back once the widget's own state has been garbage-collected —
    which is exactly the signal :func:`seed_widget_default` uses to tell a
    reverted field from a real edit.
    """
    state = st_module.session_state
    for spec in _SESSION_KEYS:
        if spec.name in state:
            continue
        if not spec.name.startswith(MIRRORED_KEY_PREFIXES):
            state[spec.name] = spec.default
            continue
        mirror = shadow_key(spec.name)
        _write_widget_value(state, spec.name, state.get(mirror, spec.default))


@dataclass
class SafeSessionState:
    """Thin typed facade over ``st.session_state``.

    Does not try to replace direct access — existing code continues to work.
    New code can prefer ``SafeSessionState(st).results`` over
    ``st.session_state.get("results")`` so typos fail loudly.
    """

    _state: Any
    _strict: bool = field(default=False)
    """If True, raise on unknown key or type mismatch; otherwise log/warn."""

    # --- generic helpers ---------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        if key not in ALL_KEYS:
            if self._strict:
                raise KeyError(f"Unknown session_state key: {key!r}")
            logger.warning("SafeSessionState.get: unknown key %r", key)
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        spec = _KEY_INDEX.get(key)
        if spec is None:
            if self._strict:
                raise KeyError(f"Unknown session_state key: {key!r}")
            logger.warning("SafeSessionState.set: unknown key %r", key)
        elif spec.expected_type is not None and not isinstance(value, spec.expected_type):
            msg = (
                f"session_state[{key!r}] expected {spec.expected_type}, "
                f"got {type(value).__name__}"
            )
            if self._strict:
                raise TypeError(msg)
            logger.warning("SafeSessionState.set: %s", msg)
        self._state[key] = value

    # --- typed accessors (add more as call sites migrate) -----------------

    @property
    def results(self) -> Any:
        return self._state.get(KEY_RESULTS)

    @property
    def last_run_id(self) -> str | None:
        return self._state.get(KEY_LAST_RUN_ID)

    @property
    def results_run_id(self) -> str | None:
        return self._state.get(KEY_RESULTS_RUN_ID)

    @property
    def effective_run_id(self) -> str | None:
        """Best-known run id: prefer the one that produced current results."""
        return self._state.get(KEY_RESULTS_RUN_ID) or self._state.get(KEY_LAST_RUN_ID)

    @property
    def dark_mode(self) -> bool:
        return bool(self._state.get(KEY_DARK_MODE, False))

    @property
    def quick_start_dismissed(self) -> bool:
        return bool(self._state.get(KEY_QUICK_START_DISMISSED, False))


__all__ = [
    "ALL_KEYS",
    "KEY_ASK_HISTORY",
    "KEY_CURRENT_RUN_ID",
    "KEY_DARK_MODE",
    "KEY_DYNAMIC_SCORING",
    "KEY_LAST_RUN_AT",
    "KEY_LAST_RUN_ID",
    "KEY_PENDING_SIDEBAR_UPDATES",
    "KEY_QS_CALCULATE",
    "KEY_QUICK_START_DISMISSED",
    "KEY_RESULTS",
    "KEY_RESULTS_RUN_ID",
    "KEY_SCORED_RESULT",
    "KEY_SETTING_DARK_MODE",
    "KEY_SETTING_DATA_YEAR",
    "KEY_SETTING_MACRO_MODEL",
    "KEY_SETTING_USE_MICROSIM",
    "KEY_SETTING_USE_MICROSIM_DISTRIBUTION",
    "KEY_SETTING_USE_REAL_DATA",
    "KEY_SHARE_TOKEN",
    "KEY_SIDEBAR_ANALYSIS_MODE",
    "KEY_SIDEBAR_POLICY_AREA",
    "KEY_SIDEBAR_PRESET_CHOICE",
    "KEY_SIDEBAR_SPENDING_PRESET",
    "KEY_TAILOR_POLICY_KIND",
    "KEY_TAILOR_SEED_APPLIED",
    "KEY_TAILOR_SEED_PRESET",
    "KEY_TAILOR_SPEND_ANNUAL",
    "KEY_TAILOR_SPEND_CATEGORY",
    "KEY_TAILOR_SPEND_DURATION",
    "KEY_TAILOR_SPEND_GROWTH_RATE",
    "KEY_TAILOR_SPEND_MULTIPLIER",
    "KEY_TAILOR_SPEND_ONE_TIME",
    "KEY_TAILOR_SPEND_PRESET_APPLIED",
    "KEY_TAILOR_SPEND_PROGRAM_NAME",
    "KEY_TAILOR_START_FROM",
    "KEY_TAILOR_TAX_CG_BASELINE_RATE",
    "KEY_TAILOR_TAX_CG_BASELINE_REALIZATIONS",
    "KEY_TAILOR_TAX_CG_BASE_YEAR",
    "KEY_TAILOR_TAX_CG_ELIMINATE_STEP_UP",
    "KEY_TAILOR_TAX_CG_GAINS_AT_DEATH",
    "KEY_TAILOR_TAX_CG_LOCK_IN_MULTIPLIER",
    "KEY_TAILOR_TAX_CG_LONG_RUN_ELASTICITY",
    "KEY_TAILOR_TAX_CG_REALIZATION_ELASTICITY",
    "KEY_TAILOR_TAX_CG_SHORT_RUN_ELASTICITY",
    "KEY_TAILOR_TAX_CG_STEP_UP_EXEMPTION",
    "KEY_TAILOR_TAX_CG_TIME_VARYING",
    "KEY_TAILOR_TAX_CG_TRANSITION_YEARS",
    "KEY_TAILOR_TAX_CUSTOM_THRESHOLD",
    "KEY_TAILOR_TAX_DURATION",
    "KEY_TAILOR_TAX_ETI",
    "KEY_TAILOR_TAX_MANUAL_AVG_INCOME",
    "KEY_TAILOR_TAX_MANUAL_TAXPAYERS",
    "KEY_TAILOR_TAX_ORDINARY_BASE",
    "KEY_TAILOR_TAX_PHASE_IN",
    "KEY_TAILOR_TAX_POLICY_NAME",
    "KEY_TAILOR_TAX_RATE_CHANGE_PCT",
    "KEY_TAILOR_TAX_THRESHOLD_CHOICE",
    "KEY_TAILOR_TAX_TYPE",
    "MIRRORED_KEY_PREFIXES",
    "SEED_ECHO_PREFIX",
    "SHADOW_PREFIX",
    "SafeSessionState",
    "forget_widget_value",
    "initialize_session_state",
    "mirror_widget_value",
    "restore_widget_value",
    "seed_widget_default",
    "shadow_key",
]
