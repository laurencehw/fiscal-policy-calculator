"""
Shared utilities for UI controller modules.
"""

from __future__ import annotations

from typing import Any, Callable


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
