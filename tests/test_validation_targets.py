"""
Shape-based validation target dispatch.

The old gate kept only ``policy_type == "income_tax"`` records with a
``rate_change``, which silently stranded 21 of 31 benchmarks. Dispatch is now
on the record's *shape*, and every record must be accounted for: runnable by
some runner, or explicitly excluded with a one-line reason.
"""

import pytest

from fiscal_model.corporate import CorporateTaxPolicy
from fiscal_model.policies import CapitalGainsPolicy, SpendingPolicy, TaxPolicy
from fiscal_model.validation.cbo_scores import (
    KNOWN_SCORES,
    MIN_GENERIC_BASELINE_YEAR,
    CBOScore,
    ScoreSource,
    describe_target_coverage,
    get_excluded_scores,
    get_specialized_targets,
    get_validation_targets,
    validation_shape,
)
from fiscal_model.validation.core import create_policy_from_score

# ── Accounting: no record may be silently dropped ──────────────────────────


def test_every_known_score_is_runnable_or_explicitly_excluded():
    runnable = [s for s in KNOWN_SCORES.values() if s.runnable]
    excluded = [s for s in KNOWN_SCORES.values() if not s.runnable]

    assert len(KNOWN_SCORES) == len(runnable) + len(excluded)
    assert runnable, "expected at least one runnable benchmark"
    assert excluded, "expected some records to be explicitly out of scope"


def test_every_excluded_record_states_why():
    for score in get_excluded_scores():
        reason = score.not_runnable_reason
        assert reason, f"{score.policy_id} is not runnable but gives no reason"
        assert len(reason.split()) >= 4, f"{score.policy_id} reason is too terse: {reason!r}"


def test_no_runnable_record_falls_through_the_dispatch():
    """A runnable record must reach *some* runner: a shape or a specialized one."""
    coverage = describe_target_coverage()
    assert coverage["unaccounted"] == []
    assert coverage["total"] == (
        len(coverage["generic"]) + len(coverage["specialized"]) + len(coverage["excluded"])
    )


def test_generic_and_specialized_targets_are_disjoint():
    """A benchmark counted in both tiers would inflate the calibrated tier and
    contaminate the out-of-sample one."""
    generic = {s.policy_id for s in get_validation_targets()}
    specialized = {s.policy_id for s in get_specialized_targets()}
    assert generic & specialized == set()


def test_generic_targets_respect_the_baseline_vintage_floor():
    for score in get_validation_targets():
        assert score.baseline_year >= MIN_GENERIC_BASELINE_YEAR


def test_capital_gains_records_are_no_longer_stranded():
    """The whole point of the widened filter: non-income-tax shapes now run."""
    generic = {s.policy_id for s in get_validation_targets()}
    assert "biden_capital_gains_39" in generic
    assert "treasury_capgains_39_plus_stepup_elim" in generic


def test_promoted_preset_targets_are_registered_as_generic():
    generic = {s.policy_id for s in get_validation_targets()}
    for policy_id in (
        "warren_ultramillionaire_surtax_3pp",
        "medicare_surcharge_2pp",
    ):
        assert policy_id in generic


def test_retired_target_is_not_dispatched():
    """``top_rate_45`` was promoted in Phase A and retired in Phase E: its
    -$420B target is in no TPC, CBO or JCT publication. The record stays in
    KNOWN_SCORES so the withdrawal is visible in the diff, but it must not be
    scored."""
    record = KNOWN_SCORES["top_rate_45"]
    assert not record.runnable
    assert record.not_runnable_reason and "RETIRED" in record.not_runnable_reason
    assert "top_rate_45" not in {s.policy_id for s in get_validation_targets()}


def test_biden_2025_preset_is_not_double_registered():
    """'Biden 2025 Proposal' in CBO_SCORE_MAP is the same Treasury target
    already carried as ``biden_high_income_tax``; registering it twice would
    count one prediction twice.

    The figure moved in the Wave 4 provenance lane (-$252.0B -> -$245.9B, the
    Green Book row this record always cited), so the test pins the revised
    number and, separately, that the superseded one is gone from every target:
    a stale duplicate would be exactly the double-registration this guards.
    """
    targets_at_official = [
        s for s in get_validation_targets() if s.ten_year_cost == -245.9
    ]
    assert [s.policy_id for s in targets_at_official] == ["biden_high_income_tax"]
    assert not [s for s in get_validation_targets() if s.ten_year_cost == -252.0]


# ── Shape dispatch ─────────────────────────────────────────────────────────


def _score(**kwargs) -> CBOScore:
    base = {
        "policy_id": "synthetic",
        "name": "Synthetic",
        "description": "Synthetic test record",
        "ten_year_cost": -100.0,
        "source": ScoreSource.CBO,
        "source_date": "2025-01",
        "baseline_year": 2025,
    }
    base.update(kwargs)
    return CBOScore(**base)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"policy_type": "income_tax", "rate_change": 0.02}, "ordinary_rate"),
        ({"policy_type": "income_tax", "rate_change": None}, None),
        ({"policy_type": "capital_gains_tax", "rate_change": 0.05}, "capital_gains"),
        ({"policy_type": "corporate_tax", "rate_change": 0.07}, "corporate_rate"),
        ({"policy_type": "spending", "annual_amount_billions": 25.0}, "spending"),
        ({"policy_type": "spending", "annual_amount_billions": None}, None),
        ({"policy_type": "tariff", "rate_change": 0.10}, None),
        ({"policy_type": "comprehensive"}, None),
        ({"policy_type": "other"}, None),
    ],
)
def test_validation_shape_dispatch(kwargs, expected):
    assert validation_shape(_score(**kwargs)) == expected


def test_shape_is_independent_of_runnable_flag():
    """``validation_shape`` is a pure shape test so callers can distinguish
    'no shape' from 'deliberately excluded'."""
    score = _score(policy_type="income_tax", rate_change=0.02, runnable=False)
    assert validation_shape(score) == "ordinary_rate"


def test_create_policy_builds_ordinary_rate_tax_policy():
    policy = create_policy_from_score(_score(policy_type="income_tax", rate_change=0.02))
    assert isinstance(policy, TaxPolicy)
    assert not isinstance(policy, CapitalGainsPolicy)
    assert policy.rate_change == 0.02
    assert policy.ordinary_income_base is True


def test_create_policy_honours_agi_inclusive_base():
    policy = create_policy_from_score(
        _score(policy_type="income_tax", rate_change=0.02, agi_inclusive_base=True)
    )
    assert policy is not None
    assert policy.ordinary_income_base is False


def test_create_policy_builds_capital_gains_with_frozen_module_defaults():
    """The out-of-sample capital-gains path must use ONE frozen elasticity set
    (the module defaults), never the per-case tuples in ``scenarios.py`` —
    otherwise the most-tuned parameter in the model would be re-tuned per
    prediction."""
    policy = create_policy_from_score(
        _score(policy_type="capital_gains_tax", rate_change=0.196, eliminate_step_up=True)
    )
    assert isinstance(policy, CapitalGainsPolicy)
    assert policy.persistent_elasticity == 0.72
    assert policy.transitory_elasticity == 1.20
    assert policy.elasticity_reference_rate == 0.22
    assert policy.eliminate_step_up is True
    # Left at 0 so the SOI auto-population fills them in at scoring time.
    assert policy.baseline_realizations_billions == 0.0


def test_every_generic_capital_gains_target_shares_one_elasticity_set():
    policies = [
        create_policy_from_score(s)
        for s in get_validation_targets()
        if validation_shape(s) == "capital_gains"
    ]
    assert policies
    assert {(p.persistent_elasticity, p.transitory_elasticity) for p in policies} == {
        (0.72, 1.20)
    }


def test_create_policy_builds_corporate_rate_policy():
    policy = create_policy_from_score(_score(policy_type="corporate_tax", rate_change=0.07))
    assert isinstance(policy, CorporateTaxPolicy)
    assert policy.rate_change == 0.07


def test_create_policy_builds_spending_policy():
    policy = create_policy_from_score(
        _score(
            policy_type="spending",
            annual_amount_billions=40.0,
            annual_growth_rate=0.03,
            phase_in_years=3,
            is_one_time=False,
            spending_category="mandatory",
        )
    )
    assert isinstance(policy, SpendingPolicy)
    assert policy.annual_spending_change_billions == 40.0
    assert policy.annual_growth_rate == 0.03
    assert policy.phase_in_years == 3
    assert policy.category == "mandatory"


def test_model_parameters_report_each_shapes_real_drivers():
    """``CorporateTaxPolicy`` subclasses ``TaxPolicy`` but ignores the
    individual bracket fields, so reporting them would look auditable while
    describing nothing that moved the number."""
    from fiscal_model.validation.core import _model_parameters_for

    corporate = create_policy_from_score(_score(policy_type="corporate_tax", rate_change=0.07))
    params = _model_parameters_for(corporate)
    assert set(params) == {
        "rate_change",
        "baseline_rate",
        "corporate_elasticity",
        "baseline_revenue_billions",
        "baseline_profits_billions",
        "include_passthrough_effects",
    }

    spending = create_policy_from_score(
        _score(policy_type="spending", annual_amount_billions=40.0)
    )
    assert set(_model_parameters_for(spending)) == {
        "annual_spending_change_billions",
        "annual_growth_rate",
        "phase_in_years",
        "is_one_time",
    }

    capgains = create_policy_from_score(
        _score(policy_type="capital_gains_tax", rate_change=0.05)
    )
    capgains_params = _model_parameters_for(capgains)
    assert {"persistent_elasticity", "transitory_elasticity", "eliminate_step_up"} <= set(
        capgains_params
    )

    ordinary = create_policy_from_score(_score(policy_type="income_tax", rate_change=0.02))
    assert set(_model_parameters_for(ordinary)) == {
        "rate_change",
        "threshold",
        "taxpayers_millions",
        "avg_income",
    }


def test_create_policy_returns_none_without_a_shape():
    assert create_policy_from_score(_score(policy_type="other")) is None
    assert create_policy_from_score(_score(policy_type="tariff", rate_change=0.1)) is None
