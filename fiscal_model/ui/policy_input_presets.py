"""
Preset categorization and display helpers for sidebar policy inputs.
"""

from __future__ import annotations

from typing import Any

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
]


def _preset_category(preset: dict[str, Any]) -> str:
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
    """Strip emoji prefix and trailing official score label for dropdown display."""
    import re as _re

    stripped = _strip_emoji_prefix(name)
    return _re.sub(r"\s*\((?:CBO|JCT):[^)]+\)\s*$", "", stripped).strip()


def _extract_cbo_score(name: str) -> str | None:
    """Return the CBO/JCT score string from a preset name."""
    import re as _re

    match = _re.search(r"\(((?:CBO|JCT):[^)]+)\)", name)
    return match.group(1) if match else None
