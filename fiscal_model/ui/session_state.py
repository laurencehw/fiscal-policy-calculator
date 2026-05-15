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
KEY_DYNAMIC_SCORING = "dynamic_scoring_enabled"

# Share-link handling
KEY_SHARE_TOKEN = "_share_link_token"

# Ask assistant
KEY_ASK_HISTORY = "ask_history"


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
)


ALL_KEYS: frozenset[str] = frozenset(spec.name for spec in _SESSION_KEYS)
_KEY_INDEX: dict[str, _KeySpec] = {spec.name: spec for spec in _SESSION_KEYS}


def initialize_session_state(st_module: Any) -> None:
    """Ensure every known key exists with its default.

    Safe to call multiple times per rerun. Never overwrites an existing
    value — Streamlit reruns depend on prior state being preserved.
    """
    state = st_module.session_state
    for spec in _SESSION_KEYS:
        if spec.name not in state:
            state[spec.name] = spec.default


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
    "KEY_SHARE_TOKEN",
    "KEY_SIDEBAR_ANALYSIS_MODE",
    "KEY_SIDEBAR_POLICY_AREA",
    "KEY_SIDEBAR_PRESET_CHOICE",
    "KEY_SIDEBAR_SPENDING_PRESET",
    "SafeSessionState",
    "initialize_session_state",
]
