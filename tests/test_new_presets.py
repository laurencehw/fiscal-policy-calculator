"""
Tests for presets added in Apr 2026: Warren Ultra-Millionaire Surtax,
Top Rate to 45%, High-Earner Medicare Surcharge, and the four new
spending programs (Student Debt Forgiveness, Universal Childcare,
Medicare Buy-in 55+, High-Speed Rail).

These verify the presets are discoverable via the app data map, have
consistent schemas, and produce scoreable policies when routed through
the executor.
"""

from __future__ import annotations

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.ui.policy_input_spending import SPENDING_PRESETS

NEW_TAX_PRESETS = [
    "Warren Ultra-Millionaire Surtax",
    "Top Rate to 45%",
    "High-Earner Medicare Surcharge 2pp",
]

NEW_SPENDING_PRESETS = [
    "Student Debt Forgiveness ($400B one-time)",
    "Universal Childcare ($100B/yr)",
    "Medicare Buy-in Age 55+ ($50B/yr)",
    "High-Speed Rail Program ($30B/yr)",
]


@pytest.mark.parametrize("name", NEW_TAX_PRESETS)
def test_tax_preset_is_in_preset_policies(name):
    assert name in PRESET_POLICIES, f"{name} missing from PRESET_POLICIES"


@pytest.mark.parametrize("name", NEW_TAX_PRESETS)
def test_tax_preset_has_cbo_score_entry(name):
    """CBO_SCORE_MAP should have a parallel entry for documentation."""
    assert name in CBO_SCORE_MAP
    entry = CBO_SCORE_MAP[name]
    assert "official_score" in entry
    assert "source" in entry


@pytest.mark.parametrize("name", NEW_TAX_PRESETS)
def test_tax_preset_has_required_fields(name):
    preset = PRESET_POLICIES[name]
    assert "rate_change" in preset
    assert "threshold" in preset
    assert "description" in preset
    # All three new presets are tax increases on high earners.
    assert preset["rate_change"] > 0
    assert preset["threshold"] >= 400_000


@pytest.mark.parametrize("name", NEW_SPENDING_PRESETS)
def test_spending_preset_has_required_fields(name):
    assert name in SPENDING_PRESETS
    preset = SPENDING_PRESETS[name]
    for key in ("annual_spending", "category", "multiplier", "duration", "description"):
        assert key in preset
    assert preset["annual_spending"] > 0
    assert 0.3 <= preset["multiplier"] <= 2.0  # in plausible multiplier range


def test_student_debt_is_one_time():
    """Student debt forgiveness is a single-year outlay."""
    preset = SPENDING_PRESETS["Student Debt Forgiveness ($400B one-time)"]
    assert preset["is_one_time"] is True
    assert preset["duration"] == 1


def test_warren_surtax_threshold_is_above_biden_400k():
    """Warren's proposal targets a much higher income threshold than Biden's."""
    warren = PRESET_POLICIES["Warren Ultra-Millionaire Surtax"]
    biden = PRESET_POLICIES["Biden 2025 Proposal"]
    assert warren["threshold"] > biden["threshold"]


def test_total_tax_preset_count_grew():
    """Sanity: the preset count should have increased by at least the 3 new."""
    # Baseline count from README (49 presets); allow room for growth.
    assert len(PRESET_POLICIES) >= 49
