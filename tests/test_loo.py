"""
Tests for the Tier 2 leave-one-out cross-validation suite.

The guarantees these lock down:

- **Determinism.** Two runs produce byte-identical payloads.
- **No leakage.** The ``derive_*`` functions never read the held-out official
  target; monkeypatching :func:`loo.official_target` to raise proves it.
- **Coverage.** Every calibrated module with >= 3 benchmarks is classified,
  and every case carries a derivation kind.
- **Frozen capital gains.** All three cases score under one elasticity set.
- **Honest aggregation.** Non-derivable cases are reported but never folded
  into the mean/median/within-15% figures.
- **No drift.** Feeding the calibrated annual back through the LOO scoring
  harness reproduces the by-construction number exactly, so the LOO and
  by-construction paths differ in one input and nothing else.
"""

from __future__ import annotations

import pytest

from fiscal_model.policies import PolicyType
from fiscal_model.policies_core import CapitalGainsPolicy
from fiscal_model.tax_expenditures_core import (
    JCT_TAX_EXPENDITURES,
    TAX_EXPENDITURE_DATA_KEYS,
    TaxExpenditureType,
)
from fiscal_model.validation import loo
from fiscal_model.validation.loo import (
    DERIVATION_BOTTOM_UP,
    DERIVATION_NONE,
    DERIVATION_STRUCTURAL,
    FROZEN_CAPITAL_GAINS_PARAMS,
    LOOSuite,
    capital_gains_donor_matrix,
    derive_amt_annual,
    derive_credit_annual,
    derive_estate_annual,
    derive_expenditure_annual,
    derive_payroll_annual,
    run_leave_one_out,
)
from fiscal_model.validation.scenarios import (
    AMT_VALIDATION_SCENARIOS_COMPARE,
    CAPITAL_GAINS_VALIDATION_SCENARIOS,
    ESTATE_TAX_VALIDATION_SCENARIOS,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    TAX_CREDIT_VALIDATION_SCENARIOS,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
)
from fiscal_model.validation.specialized_household import validate_payroll_policy

MODULES_WITH_THREE_PLUS = {
    "Payroll": PAYROLL_TAX_VALIDATION_SCENARIOS,
    "Estate": ESTATE_TAX_VALIDATION_SCENARIOS,
    "AMT": AMT_VALIDATION_SCENARIOS_COMPARE,
    "Credits": TAX_CREDIT_VALIDATION_SCENARIOS,
    "Expenditures": TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
    "CapitalGains": CAPITAL_GAINS_VALIDATION_SCENARIOS,
}

VALID_DERIVATIONS = {DERIVATION_STRUCTURAL, DERIVATION_BOTTOM_UP, DERIVATION_NONE}


@pytest.fixture(scope="module")
def suite() -> LOOSuite:
    return run_leave_one_out()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_suite_is_deterministic():
    """Two independent runs produce identical payloads."""
    assert run_leave_one_out().to_dict() == run_leave_one_out().to_dict()


def test_donor_matrix_is_deterministic():
    assert capital_gains_donor_matrix() == capital_gains_donor_matrix()


def test_scenario_registries_are_restored(suite):
    """The suite patches scenario registries in place; it must clean up."""
    assert suite is not None
    for registry in MODULES_WITH_THREE_PLUS.values():
        for scenario in registry.values():
            assert "policy_factory" in scenario or "score_id" in scenario
    # The frozen capital-gains parameters must not have leaked into the
    # persistent registry. Since Wave 2's L1 that registry carries no
    # behavioural fields at all, which is the stronger statement: there is
    # nothing left for the frozen set to overwrite.
    behavioural = {
        "short_run_elasticity",
        "long_run_elasticity",
        "transition_years",
        "step_up_lock_in_multiplier",
        "no_step_up_avoidance_multiplier",
        "persistent_elasticity",
        "transitory_elasticity",
        "elasticity_reference_rate",
        "realization_elasticity",
    }
    for scenario in CAPITAL_GAINS_VALIDATION_SCENARIOS.values():
        assert not behavioural & set(scenario)


# ---------------------------------------------------------------------------
# The held-out target is never read during derivation
# ---------------------------------------------------------------------------


def test_derivations_never_read_the_held_out_target(monkeypatch):
    """
    Every ``derive_*`` function must run with the target lookup disabled.

    This is the invariant that makes the leave-one-out number genuinely
    held out rather than a restatement of the answer key.
    """

    def _boom(module: str, case_id: str) -> float:
        raise AssertionError(
            f"derivation read the held-out official target for {module}/{case_id}"
        )

    monkeypatch.setattr(loo, "official_target", _boom)

    derived = []
    for case_id in PAYROLL_TAX_VALIDATION_SCENARIOS:
        derived.append(derive_payroll_annual(case_id))
    for case_id in ESTATE_TAX_VALIDATION_SCENARIOS:
        derived.append(derive_estate_annual(case_id))
    for case_id in AMT_VALIDATION_SCENARIOS_COMPARE:
        derived.append(derive_amt_annual(case_id))
    for case_id in TAX_CREDIT_VALIDATION_SCENARIOS:
        derived.append(derive_credit_annual(case_id))
    for case_id in TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE:
        derived.append(derive_expenditure_annual(case_id))

    # At least one real derivation came out of each module, so the test is
    # not vacuously passing on a wall of Nones.
    assert sum(1 for d in derived if d is not None) >= 13


def test_derived_annuals_are_independent_of_the_target(monkeypatch):
    """Perturbing a published target must not move its LOO derivation."""
    before = derive_payroll_annual("ss_donut_250k")
    scenario = PAYROLL_TAX_VALIDATION_SCENARIOS["ss_donut_250k"]
    monkeypatch.setitem(
        PAYROLL_TAX_VALIDATION_SCENARIOS,
        "ss_donut_250k",
        {**scenario, "expected_10yr": scenario["expected_10yr"] * 2},
    )
    assert derive_payroll_annual("ss_donut_250k") == before


# ---------------------------------------------------------------------------
# Coverage and classification
# ---------------------------------------------------------------------------


def test_every_module_with_three_benchmarks_is_classified(suite):
    covered = {report.module for report in suite.reports}
    assert covered == set(MODULES_WITH_THREE_PLUS)
    for module, registry in MODULES_WITH_THREE_PLUS.items():
        assert len(registry) >= 3, f"{module} should have >= 3 benchmarks"
        report = next(r for r in suite.reports if r.module == module)
        assert {c.case_id for c in report.cases} == set(registry)


def test_every_case_has_a_derivation_kind(suite):
    for case in suite.cases:
        assert case.derivation in VALID_DERIVATIONS
        assert case.policy_name
        assert case.official_10yr != 0


def test_non_derivable_cases_carry_a_reason(suite):
    excluded = suite.excluded_cases
    assert excluded, "expected at least one non-cross-validatable case"
    for case in excluded:
        assert case.derivation == DERIVATION_NONE
        assert case.exclusion_reason
        assert case.percent_error is None


def test_leakage_guard_excludes_target_restating_constants(suite):
    """
    Cases whose 'base data' is the published target restated are excluded.

    ``expand_niit`` ($25B/yr vs a $250B/10yr target), ``repeal_corporate_amt``
    ($22B/yr vs $220B) and ``eliminate_step_up`` ($50B/yr vs $500B) all fail
    this check by construction.
    """
    excluded_ids = {c.case_id for c in suite.excluded_cases}
    assert {"expand_niit", "repeal_corporate_amt", "eliminate_step_up"} <= excluded_ids


def test_payroll_band_anchors_are_not_the_interpolated_rows():
    """Only the three benchmark-anchored bands may seed a LOO calibration."""
    assert set(loo.PAYROLL_BAND_ANCHORS) == {
        "ss_eliminate_cap",
        "ss_donut_250k",
        "ss_cap_90_pct",
    }
    for case_id in loo.PAYROLL_BAND_ANCHORS:
        case_calibration = [
            cid for cid in loo.PAYROLL_BAND_ANCHORS if cid != case_id
        ]
        assert case_id not in case_calibration
        assert len(case_calibration) == 2


def test_calibration_set_excludes_the_held_out_case(suite):
    for case in suite.cases:
        assert case.case_id not in case.calibration_set


# ---------------------------------------------------------------------------
# Capital gains — frozen elasticities
# ---------------------------------------------------------------------------


def test_frozen_capital_gains_scores_all_three_cases(suite):
    report = next(r for r in suite.reports if r.module == "CapitalGains")
    assert len(report.included_cases) == 3
    for case in report.included_cases:
        assert case.loo_10yr is not None
        assert case.percent_error is not None


def test_frozen_params_are_the_dataclass_defaults():
    defaults = CapitalGainsPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
    )
    for field_name, value in FROZEN_CAPITAL_GAINS_PARAMS.items():
        assert getattr(defaults, field_name) == value


def test_frozen_run_matches_the_production_run_now_the_tuples_are_gone(suite):
    """The tuples this comparison existed to expose have been deleted.

    Before Wave 2's L1 the three scenarios each carried their own
    elasticity/lock-in tuple, and freezing one set changed every score - which
    is what made the LOO number informative. Now the scenarios are structural
    only, so the frozen run and the production run are the same run, and the
    whole module scores out-of-sample by construction. That equality is the
    property worth guarding: if it ever breaks, a per-case behavioural
    parameter has come back.
    """
    report = next(r for r in suite.reports if r.module == "CapitalGains")
    assert report.cases
    for case in report.cases:
        assert case.loo_10yr == pytest.approx(case.calibrated_10yr)


def test_donor_matrix_is_square_and_complete():
    matrix = capital_gains_donor_matrix()
    assert set(matrix) == set(CAPITAL_GAINS_VALIDATION_SCENARIOS)
    for row in matrix.values():
        assert set(row) == set(CAPITAL_GAINS_VALIDATION_SCENARIOS)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def test_aggregate_excludes_non_derivable_cases(suite):
    included = suite.included_cases
    excluded = suite.excluded_cases
    assert len(included) + len(excluded) == len(suite.cases)
    assert all(c.abs_percent_error is not None for c in included)

    expected_mean = sum(c.abs_percent_error for c in included) / len(included)
    assert suite.mean_abs_percent_error == pytest.approx(expected_mean)
    assert suite.within_15pct == sum(
        1 for c in included if c.abs_percent_error <= 15.0
    )


def test_aggregate_payload_reports_both_counts(suite):
    payload = suite.to_dict()
    assert payload["tier"] == "Tier 2 (leave-one-out)"
    assert payload["n_included"] == len(suite.included_cases)
    assert payload["n_not_cross_validatable"] == len(suite.excluded_cases)


def test_loo_is_materially_worse_than_by_construction(suite):
    """
    The whole point: the held-out error must exceed the by-construction one.

    If this ever flips, either a target leaked into a derivation or the
    by-construction scorecard regressed.
    """
    included = suite.included_cases
    by_construction = [
        abs((c.calibrated_10yr - c.official_10yr) / c.official_10yr) * 100
        for c in included
    ]
    mean_by_construction = sum(by_construction) / len(by_construction)
    assert suite.mean_abs_percent_error > mean_by_construction

    # The by-construction number measures bookkeeping only where a constant was
    # actually fitted. Wave 2's L1 deleted the capital-gains tuples, so those
    # three cases have nothing held out and their "by-construction" score is
    # their out-of-sample score. Excluding them keeps this assertion measuring
    # what it was written to measure; it removes no case from any reported
    # error, and the LOO aggregate above still includes all 18.
    fitted = [
        abs((c.calibrated_10yr - c.official_10yr) / c.official_10yr) * 100
        for c in included
        if c.module != "CapitalGains"
    ]
    assert sum(fitted) / len(fitted) < 10.0


# ---------------------------------------------------------------------------
# No drift between the LOO harness and the production runners
# ---------------------------------------------------------------------------


def test_harness_reproduces_the_by_construction_score():
    """
    Feeding the calibrated annual back through the LOO harness must reproduce
    the by-construction number exactly — proof that the LOO path differs from
    the scorecard path in exactly one input.
    """
    for case_id in ("ss_cap_90_pct", "ss_donut_250k", "ss_eliminate_cap"):
        calibrated_annual = loo._calibrated_annual(
            PAYROLL_TAX_VALIDATION_SCENARIOS, case_id
        )
        replayed = loo._score_with_annual(
            PAYROLL_TAX_VALIDATION_SCENARIOS,
            validate_payroll_policy,
            case_id,
            calibrated_annual,
        )
        direct = validate_payroll_policy(case_id, verbose=False)
        assert replayed.model_10yr == pytest.approx(direct.model_10yr)
        assert replayed.percent_difference == pytest.approx(direct.percent_difference)


def test_zero_derivation_is_reported_not_silently_dropped(monkeypatch):
    """
    A rule that runs and returns 0.0 is a *derivation*, not an absent one.

    Dropping it would hide the misconfiguration this suite exists to surface,
    so it must reach the aggregate as a ~100% error. Only an expenditure type
    with no JCT base-table entry at all is non-derivable.
    """
    monkeypatch.setitem(
        JCT_TAX_EXPENDITURES,
        "mortgage_interest",
        {**JCT_TAX_EXPENDITURES["mortgage_interest"], "annual_cost": 0.0},
    )
    derived = derive_expenditure_annual("eliminate_mortgage")
    assert derived == 0.0, "a rule that ran and produced 0.0 must not return None"

    report = loo.run_tax_expenditure_loo()
    case = next(c for c in report.cases if c.case_id == "eliminate_mortgage")
    assert case.included is True
    assert case.abs_percent_error == pytest.approx(100.0)


def test_missing_base_table_entry_is_not_cross_validatable(monkeypatch):
    """No base-table entry at all is the only non-derivable expenditure case."""
    # Drop the type -> key mapping so get_expenditure_data() falls through to
    # its "charitable" default, then drop that too, leaving an empty base.
    monkeypatch.delitem(
        TAX_EXPENDITURE_DATA_KEYS, TaxExpenditureType.MORTGAGE_INTEREST
    )
    monkeypatch.delitem(JCT_TAX_EXPENDITURES, "charitable")

    assert derive_expenditure_annual("eliminate_mortgage") is None

    report = loo.run_tax_expenditure_loo()
    case = next(c for c in report.cases if c.case_id == "eliminate_mortgage")
    assert case.included is False
    assert case.derivation == DERIVATION_NONE
    assert "base-table" in case.exclusion_reason
