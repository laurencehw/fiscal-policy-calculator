"""
Shared utilities for UI controller modules.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any


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
            import traceback

            st_module.error(f"{error_prefix}: {e}")
            with st_module.expander("Show technical details"):
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


def render_input_guardrails(st_module: Any, tax_inputs: dict[str, Any]) -> None:
    """
    Show contextual warnings for extreme parameter values.

    Checks for:
    - ETI outside typical range
    - Very high income thresholds
    - Large rate changes

    Warnings appear in sidebar near inputs, not blocking calculation.
    """
    eti = tax_inputs.get("eti", 0.25)
    threshold = tax_inputs.get("threshold", 0)
    rate_change_pct = tax_inputs.get("rate_change_pct", 0.0)

    # Check ETI values
    if eti > 1.0:
        st_module.error(
            "⚠️ ETI above 1.0 implies revenue-losing Laffer effects. "
            "Consider using a value in the 0.1–0.5 range."
        )
    elif eti > 0.5:
        st_module.warning(
            f"⚠️ ETI of {eti:.2f} is above the typical academic range (0.1–0.4). "
            "CBO uses 0.25. Results may overstate behavioral responses."
        )

    # Check income threshold
    if threshold > 10_000_000:
        st_module.info(
            f"ℹ️ Very few taxpayers earn above ${threshold:,}. "
            "The scored effect may be near zero."
        )

    # Check rate change magnitude
    if abs(rate_change_pct) > 10.0:
        st_module.info(
            f"ℹ️ A {rate_change_pct:+.1f}pp rate change is large. "
            "For context, the top marginal rate is currently 37%."
        )


def get_confidence_context(st_module: Any, policy: Any, result: Any) -> str:
    """
    Generate a markdown string with confidence notes about the result.

    Returns:
    - The ETI used and its academic range
    - Whether dynamic scoring was enabled
    - The baseline vintage
    - A confidence rating: "High", "Moderate", or "Exploratory"

    Checks if the policy matches a known CBO-validated policy.
    """
    try:
        from fiscal_model.app_data import CBO_SCORE_MAP

        # Try to infer confidence level from policy name
        policy_name = getattr(policy, "name", "Unknown Policy")
        is_validated = False
        confidence = "Exploratory"

        if policy_name in CBO_SCORE_MAP:
            is_validated = True
            confidence = "High confidence"

        # Check result error if available
        if hasattr(result, "error_pct"):
            error_pct = abs(result.error_pct)
            if error_pct < 5:
                confidence = "High confidence"
            elif error_pct < 15:
                confidence = "Moderate confidence"
            else:
                confidence = "Exploratory"
        elif is_validated:
            confidence = "High confidence"

        # Build confidence context markdown
        eti = getattr(policy, "taxable_income_elasticity", 0.25)
        dynamic_scoring = getattr(result, "is_dynamic", False)

        context = f"""
**Confidence:** {confidence}

- **Elasticity (ETI):** {eti:.2f} (academic range: 0.1–0.4, CBO consensus: 0.25)
- **Dynamic scoring:** {'Enabled' if dynamic_scoring else 'Static only'}
- **Baseline:** CBO Feb 2026 economic assumptions
"""

        if is_validated:
            context += "\n- **Validation:** Policy matches CBO/JCT official estimate within 15%"
        else:
            context += "\n- **Validation:** Custom policy, not yet validated against official sources"

        return context
    except Exception:
        # Fallback if anything fails
        return (
            "**Confidence:** Unable to determine\n\n"
            "See methodology tab for scoring assumptions."
        )
