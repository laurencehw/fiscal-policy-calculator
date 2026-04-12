"""
Policy input helpers — compatibility facade for sidebar input modules.
"""

from .policy_input_presets import (
    _CATEGORY_ORDER,
    _extract_cbo_score,
    _preset_category,
    _short_display_name,
    _strip_emoji_prefix,
)
from .policy_input_spending import (
    SPENDING_PRESETS,
    calculate_spending_policy_result,
    render_spending_policy_inputs,
)
from .policy_input_tax import render_tax_policy_inputs

__all__ = [
    "SPENDING_PRESETS",
    "_CATEGORY_ORDER",
    "_extract_cbo_score",
    "_preset_category",
    "_short_display_name",
    "_strip_emoji_prefix",
    "calculate_spending_policy_result",
    "render_spending_policy_inputs",
    "render_tax_policy_inputs",
]
