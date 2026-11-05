"""The Tailor shapes that claim to reproduce a preset must do so to the cent.

The web list in ``web/lib/adjust.ts`` records the same five shapes. This test
sends each one through the function ``/score`` uses, so a later change to the
income path cannot leave the claim true only against a hard-coded number.
"""

from __future__ import annotations

import pytest

import api

# (preset id, rate in percentage points, income threshold, policy type)
SHAPES = [
    ("top-rate-39-6", 2.6, 400_000, "income_tax"),
    ("middle-class-rate-cut-2pp", -2.0, 50_000, "income_tax"),
    ("across-the-board-rate-cut-5pp", -5.0, 0, "income_tax"),
    ("top-rate-45", 8.0, 609_350, "income_tax"),
    ("corporate-28pct", 7.0, 0, "corporate_tax"),
]

# The 15% corporate preset also extends bonus depreciation, so a rate-only
# Tailor request must not match it.
NOT_A_SHAPE = ("corporate-15pct", -6.0, 0, "corporate_tax")


def _score(preset_id: str, rate_points: float, threshold: int, policy_type: str) -> tuple[float, float]:
    custom = api.score_policy(
        api.ScorePolicyRequest(
            name="tailor",
            description="tailor",
            rate_change=rate_points / 100.0,
            income_threshold=threshold,
            duration_years=10,
            policy_type=policy_type,
        ),
        _api_key_label="tailor-shape",
    )
    preset = api.score_preset(
        api.ScorePresetRequest(preset_name=preset_id, dynamic=False),
        _api_key_label="tailor-shape",
    )
    return float(custom.ten_year_deficit_impact), float(preset.ten_year_deficit_impact)


@pytest.mark.parametrize("preset_id,rate_points,threshold,policy_type", SHAPES)
def test_each_tailor_shape_matches_its_preset_to_the_cent(preset_id, rate_points, threshold, policy_type):
    custom, preset = _score(preset_id, rate_points, threshold, policy_type)
    assert custom == pytest.approx(preset, abs=0.01)


def test_the_15_percent_corporate_preset_is_not_a_tailor_shape():
    preset_id, rate_points, threshold, policy_type = NOT_A_SHAPE
    custom, preset = _score(preset_id, rate_points, threshold, policy_type)
    assert abs(custom - preset) > 1
