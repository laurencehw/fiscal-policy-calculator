"""
Shared utilities for UI controller modules.
"""

from __future__ import annotations

from typing import Any, Callable

import hashlib
import json


def run_with_spinner_feedback(
    st_module: Any,
    spinner_message: str,
    success_message: str,
    error_prefix: str,
    action_fn: Callable[[], None],
) -> bool:
    """
    Execute an action with spinner, success feedback, and traceback on failure.
    """
    with st_module.spinner(spinner_message):
        try:
            action_fn()
            st_module.success(success_message)
            return True
        except Exception as e:
            st_module.error(f"{error_prefix}: {e}")
            import traceback

            st_module.code(traceback.format_exc())
            return False


def compute_run_id(calc_context: dict[str, Any], settings: dict[str, Any]) -> str:
    """
    Produce a stable identifier for the current configuration (inputs + settings).
    """

    def _default(o: Any) -> str:
        return str(o)

    payload = {
        "mode": calc_context.get("mode"),
        "is_spending": calc_context.get("is_spending"),
        "tax_inputs": calc_context.get("tax_inputs", {}),
        "spending_inputs": calc_context.get("spending_inputs", {}),
        "settings": settings,
    }

    raw = json.dumps(payload, sort_keys=True, default=_default).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]
