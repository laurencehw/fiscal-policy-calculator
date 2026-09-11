"""
Preset categorization and display helpers for sidebar policy inputs.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.app_data import ILLUSTRATIVE_GROUP_LABEL, is_illustrative

#: The demoted group's own policy area. It is **last** in
#: :data:`_CATEGORY_ORDER` and its name states the tier, because the whole job
#: of the group is to say what kind of number these presets carry
#: (H12, ``planning/lanes/HSD_h12_illustrative_group.md``).
ILLUSTRATIVE_CATEGORY = ILLUSTRATIVE_GROUP_LABEL

_CATEGORY_ORDER = [
    "TCJA / Individual",
    "Corporate",
    "International Tax",
    "Tax Credits",
    "Estate Tax",
    "Payroll / SS",
    "AMT",
    "ACA / Healthcare",
    "Tax Expenditures",
    "IRS Enforcement",
    "Drug Pricing",
    "Trade / Tariffs",
    "Climate / Energy",
    "Income Tax",
    ILLUSTRATIVE_CATEGORY,
]


def _preset_category(preset: dict[str, Any]) -> str:
    # The demoted group wins over every substantive area: a preset flagged
    # illustrative must appear there and **nowhere else**, so this test comes
    # before ``ui_category`` and before the ``is_*`` ladder below.
    if is_illustrative(preset):
        return ILLUSTRATIVE_CATEGORY
    if preset.get("ui_category"):
        return preset["ui_category"]
    if preset.get("is_tcja"):
        return "TCJA / Individual"
    if preset.get("is_corporate"):
        return "Corporate"
    if preset.get("is_international"):
        return "International Tax"
    if preset.get("is_credit"):
        return "Tax Credits"
    if preset.get("is_estate"):
        return "Estate Tax"
    if preset.get("is_payroll"):
        return "Payroll / SS"
    if preset.get("is_amt"):
        return "AMT"
    if preset.get("is_ptc"):
        return "ACA / Healthcare"
    if preset.get("is_expenditure"):
        return "Tax Expenditures"
    if preset.get("is_enforcement"):
        return "IRS Enforcement"
    if preset.get("is_pharma"):
        return "Drug Pricing"
    if preset.get("is_trade"):
        return "Trade / Tariffs"
    if preset.get("is_climate"):
        return "Climate / Energy"
    return "Income Tax"


def _strip_emoji_prefix(name: str) -> str:
    """Remove leading emoji + space from preset names for cleaner display."""
    for ch in name:
        if ch.isalpha() or ch == "(":
            return name[name.index(ch):]
    return name


def _short_display_name(name: str) -> str:
    """Strip emoji prefix and trailing official score label for dropdown display.

    Also drops the markdown ``\\$`` escape a few preset keys carry: a selectbox
    *option* is plain text, so the escape reached the dropdown as a visible
    backslash ("Carbon Tax \\$50/ton").
    """
    import re as _re

    from fiscal_model.ui.helpers import unescape_markdown_dollars

    stripped = _strip_emoji_prefix(unescape_markdown_dollars(name))
    return _re.sub(r"\s*\((?:CBO|JCT):[^)]+\)\s*$", "", stripped).strip()


def _extract_cbo_score(name: str) -> str | None:
    """Return the CBO/JCT score string from a preset name."""
    import re as _re

    match = _re.search(r"\(((?:CBO|JCT):[^)]+)\)", name)
    return match.group(1) if match else None
