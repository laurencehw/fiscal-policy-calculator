"""
Reusable UI-facing helpers that keep app.py focused on rendering.
"""

from __future__ import annotations

import os
import re
from typing import Any

import numpy as np

# Streamlit markdown renders `$...$` as LaTeX math, so any string carrying two
# currency amounts turns into math salad ("−18,642(−4.42…"). Escape unescaped
# `$` before a digit in every markdown-rendered currency string.
_DOLLAR_BEFORE_DIGIT_RE = re.compile(r"(?<!\\)\$(?=\d)")


def escape_markdown_dollars(text: str) -> str:
    """Escape ``$`` before digits so Streamlit markdown shows currency, not math."""
    if not text:
        return text
    return _DOLLAR_BEFORE_DIGIT_RE.sub(r"\\$", text)


def validated_policy_count() -> int:
    """Count of CBO/JCT-validated benchmark entries, from the scorecard.

    The footer, welcome text, and scorecard used to quote three different
    hardcoded numbers (25 / 25+ / 33). Everything now reads the same
    computed source the Validation Scorecard tab reports.
    """
    try:
        from fiscal_model.validation.scorecard import cached_default_scorecard

        return int(cached_default_scorecard().total_entries)
    except Exception:
        return 25

# ── Textbook links ──────────────────────────────────────────────────────
# NOTE: "public-economcis" is the actual GitBook slug (intentional spelling).
_TEXTBOOK_BASE = (
    "https://laurence-wilse-samson.gitbook.io/textbooks/public-economcis/chapters"
)

TEXTBOOK_LINKS = {
    "optimal_taxation": f"{_TEXTBOOK_BASE}/ch16_optimal_taxation",
    "income_tax": f"{_TEXTBOOK_BASE}/ch18_income_tax",
    "corporate_tax": f"{_TEXTBOOK_BASE}/ch19_corporate_tax",
    "federal_budget": f"{_TEXTBOOK_BASE}/ch22_federal_budget",
    "fiscal_sustainability": f"{_TEXTBOOK_BASE}/ch25_macro_sustainability",
}

TEXTBOOK_HOME = (
    "https://laurence-wilse-samson.gitbook.io/textbooks/public-economcis"
)

PUBLIC_APP_URL = os.getenv(
    "FISCAL_POLICY_APP_URL",
    "https://fiscal-policy-calculator.streamlit.app",
).rstrip("/")


def build_macro_scenario(policy: Any, result: Any, is_spending_policy: bool, macro_scenario_cls: Any) -> Any:
    """
    Build a MacroScenario from a scored policy result.

    Spending policy impacts map to outlays, while tax policies map to receipts.
    """
    # behavioral_offset is deficit convention (positive = adds to deficit),
    # so the conventional deficit path is static_deficit + behavioral — the
    # same sum the scorer uses for deficit_after_behavioral. Deriving receipts
    # from static_revenue + behavioral mixed conventions (double-counting the
    # offset), and spending policies produced an all-zero scenario because
    # their impulse lives in static_spending_effect, not static_revenue_effect.
    net_deficit = result.static_deficit_effect + result.behavioral_offset
    horizon = len(net_deficit)

    if is_spending_policy:
        receipts_change = np.zeros(horizon)
        outlays_change = np.array(net_deficit)
    else:
        receipts_change = np.array(-net_deficit)
        outlays_change = np.zeros(horizon)

    return macro_scenario_cls(
        name=policy.name,
        description=f"Dynamic scoring for {policy.name}",
        start_year=int(result.baseline.years[0]),
        horizon_years=horizon,
        receipts_change=receipts_change,
        outlays_change=outlays_change,
    )


def build_scorable_policy_map(preset_policies: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Index scorable preset policies by display category.
    """
    all_scorable_policies: dict[str, dict[str, Any]] = {}

    category_flags = [
        ("is_tcja", "TCJA"),
        ("is_corporate", "Corporate"),
        ("is_credit", "Tax Credits"),
        ("is_estate", "Estate Tax"),
        ("is_payroll", "Payroll Tax"),
        ("is_amt", "AMT"),
        ("is_ptc", "Premium Tax Credits"),
        ("is_expenditure", "Tax Expenditures"),
    ]

    for name, data in preset_policies.items():
        if name == "Custom Policy":
            continue

        for flag_name, category in category_flags:
            if data.get(flag_name):
                all_scorable_policies[name] = {"category": category, "data": data}
                break

    return all_scorable_policies
