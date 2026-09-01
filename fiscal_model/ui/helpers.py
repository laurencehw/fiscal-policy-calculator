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
    """Count of benchmark entries scored against a *published* figure.

    The footer, welcome text, and scorecard used to quote three different
    hardcoded numbers (25 / 25+ / 33). Everything now reads the same
    computed source the Validation Scorecard tab reports.

    Phase E §5.2: this reads ``published_entries``, not ``total_entries``.
    The scorecard also carries *illustrations* — policy shapes for which no
    official score exists at all, compared against a model estimate — and
    counting those inside a sentence ending "validated against CBO/JCT"
    would make a claim about exactly the rows that have no CBO/JCT number.

    Returns **0** when the scorecard cannot be computed, and callers must drop
    the whole clause rather than print a zero. The fallback used to be a
    hard-coded 25, which asserted validation coverage at precisely the moment
    the thing that measures it had failed.
    """
    try:
        from fiscal_model.validation.scorecard import cached_default_scorecard

        return int(cached_default_scorecard().published_entries)
    except Exception:
        return 0

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


# ── Preset categorisation ───────────────────────────────────────────────
# Every scoring module the preset handler can route to, in the order
# `policy_input_presets._preset_category` resolves them. This list used to
# cover only the first eight flags, which silently dropped 28 of the 52
# presets (all of International / Trade / Climate / Drug Pricing / IRS
# Enforcement) and emptied 4 of the 12 PRESET_POLICY_PACKAGES. Adding a
# policy module means adding a row here; `tests/test_policy_catalog.py`
# fails if a preset ever falls through again.
#
# These are *scoring-module* names, not the sidebar's display areas, so
# `ui_category` (a display override on four entries) is deliberately not
# consulted here.
PRESET_CATEGORY_BY_FLAG: tuple[tuple[str, str], ...] = (
    ("is_tcja", "TCJA"),
    ("is_corporate", "Corporate"),
    ("is_international", "International Tax"),
    ("is_credit", "Tax Credits"),
    ("is_estate", "Estate Tax"),
    ("is_payroll", "Payroll Tax"),
    ("is_amt", "AMT"),
    ("is_ptc", "Premium Tax Credits"),
    ("is_expenditure", "Tax Expenditures"),
    ("is_enforcement", "IRS Enforcement"),
    ("is_pharma", "Drug Pricing"),
    ("is_trade", "Trade / Tariffs"),
    ("is_climate", "Climate / Energy"),
)

#: Presets with no module flag are plain rate-and-threshold income-tax
#: policies (Warren surtax, Top Rate to 45%, ...). They are scored as a
#: generic `TaxPolicy` and are just as selectable as the calibrated ones.
GENERIC_PRESET_CATEGORY = "Income Tax"

# What makes an unflagged entry a real generic preset rather than a stub:
# it has to carry the parameters the generic scoring path reads.
_GENERIC_PRESET_FIELDS = ("rate_change", "threshold")


def preset_scoring_category(preset_data: dict[str, Any]) -> str | None:
    """Scoring-module category for one preset, or ``None`` if unscorable.

    Derived from the ``is_*`` module flags the preset handler itself routes
    on, with a fallback to the generic rate-and-threshold path — never from
    an optional per-entry field, which is how the previous version came to
    drop half the catalog.
    """
    for flag_name, category in PRESET_CATEGORY_BY_FLAG:
        if preset_data.get(flag_name):
            return category
    if any(field in preset_data for field in _GENERIC_PRESET_FIELDS):
        return GENERIC_PRESET_CATEGORY
    return None


def build_scorable_policy_map(preset_policies: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Index scorable preset policies by scoring-module category.

    Keyed by display label (callers still key on labels); each value carries
    the entry's stable ``preset_id`` too, so Build-side consumers can move to
    ids without a second lookup.
    """
    from fiscal_model.preset_ids import CUSTOM_POLICY_LABEL

    all_scorable_policies: dict[str, dict[str, Any]] = {}

    for name, data in preset_policies.items():
        if name == CUSTOM_POLICY_LABEL:
            continue

        category = preset_scoring_category(data)
        if category is None:
            continue

        all_scorable_policies[name] = {
            "category": category,
            "preset_id": data.get("preset_id"),
            "data": data,
        }

    return all_scorable_policies
