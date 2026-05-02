"""
Regression tests for capital-gains validation calibration.
"""

from __future__ import annotations

import pytest

from fiscal_model.validation.specialized_capital_gains import (
    validate_capital_gains_policy,
)


@pytest.mark.parametrize(
    "scenario_id",
    [
        "cbo_2pp_all_brackets",
        "pwbm_39_with_stepup",
        "pwbm_39_no_stepup",
    ],
)
def test_capital_gains_benchmarks_remain_within_acceptability_band(scenario_id):
    result = validate_capital_gains_policy(scenario_id, verbose=False)

    assert result.accuracy_rating in {"Excellent", "Good", "Acceptable"}
    assert result.is_accurate


def test_pwbm_no_stepup_residual_avoidance_multiplier_closes_outlier():
    result = validate_capital_gains_policy("pwbm_39_no_stepup", verbose=False)

    assert result.accuracy_rating == "Excellent"
    assert result.abs_percent_difference <= 5.0
    assert result.model_parameters["no_step_up_avoidance_multiplier"] == pytest.approx(1.5)
