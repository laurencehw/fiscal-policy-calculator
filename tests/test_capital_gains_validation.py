"""
Regression tests for the capital-gains validation scenarios.

These three benchmarks used to carry a hand-set elasticity/lock-in tuple each,
chosen after seeing that case's own target, and this file asserted that all
three landed inside an acceptability band. That band measured the tuples, not
the model. Wave 2's L1 deleted them (``planning/lanes/L1_capital_gains.md``),
so what is left to test is that the scenarios are structural, that one frozen
literature set scores all three, and that the mechanism gets the *sign* right
on the case the old calibration could only reach with a 5.3x multiplier.
"""

from __future__ import annotations

import pytest

from fiscal_model.validation.scenarios import CAPITAL_GAINS_VALIDATION_SCENARIOS
from fiscal_model.validation.specialized_capital_gains import (
    validate_capital_gains_policy,
)

#: Fields a scenario may set. Everything here says what the *policy* is; none
#: of it says how taxpayers respond. A behavioural field appearing in this
#: registry again would be a per-case parameter fitted to a per-case target.
STRUCTURAL_SCENARIO_FIELDS = {
    "score_id",
    "description",
    "notes",
    "baseline_realizations_billions",
    "baseline_capital_gains_rate",
    "step_up_at_death",
    "eliminate_step_up",
    "step_up_exemption",
    "score_gains_at_death",
    "benchmark_kind",
    "limitations",
}


def test_scenarios_carry_no_behavioural_parameters():
    for case_id, scenario in CAPITAL_GAINS_VALIDATION_SCENARIOS.items():
        extra = set(scenario) - STRUCTURAL_SCENARIO_FIELDS
        assert not extra, f"{case_id} carries non-structural fields: {sorted(extra)}"


@pytest.mark.parametrize("scenario_id", sorted(CAPITAL_GAINS_VALIDATION_SCENARIOS))
def test_every_scenario_scores_on_the_one_frozen_literature_set(scenario_id):
    result = validate_capital_gains_policy(scenario_id, verbose=False)
    assert result.model_parameters["persistent_elasticity"] == pytest.approx(0.72)
    assert result.model_parameters["transitory_elasticity"] == pytest.approx(1.20)
    assert result.model_parameters["elasticity_reference_rate"] == pytest.approx(0.22)


@pytest.mark.parametrize("scenario_id", sorted(CAPITAL_GAINS_VALIDATION_SCENARIOS))
def test_every_scenario_gets_the_direction_right(scenario_id):
    result = validate_capital_gains_policy(scenario_id, verbose=False)
    assert result.direction_match


def test_a_43_percent_rate_loses_revenue_while_step_up_survives():
    """PWBM's headline result, and the one the deleted 5.3x multiplier existed
    to reproduce. The semi-log form puts the revenue-maximizing rate at
    1/b = 30.6%, so 43.4% is past the peak on its own.
    """
    with_step_up = validate_capital_gains_policy("pwbm_39_with_stepup", verbose=False)
    assert with_step_up.model_10yr > 0  # adds to the deficit

    without = validate_capital_gains_policy("pwbm_39_no_stepup", verbose=False)
    assert without.model_10yr < 0  # raises revenue
    assert without.model_10yr < with_step_up.model_10yr


def test_the_step_up_wedge_is_what_separates_the_two_pwbm_cases():
    """The two PWBM rows differ only in whether death is a realization event,
    so the whole gap between them must come from the lock-in price wedge."""
    with_step_up = validate_capital_gains_policy("pwbm_39_with_stepup", verbose=False)
    without = validate_capital_gains_policy("pwbm_39_no_stepup", verbose=False)
    assert with_step_up.model_parameters["lock_in_wedge"] > 1.0
    assert without.model_parameters["lock_in_wedge"] == pytest.approx(
        with_step_up.model_parameters["lock_in_wedge"]
    )
    assert without.model_parameters["eliminate_step_up"] is True
    assert with_step_up.model_parameters["eliminate_step_up"] is False
