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
        "top_rate_45",
        "medicare_surcharge_2pp",
    ):
        assert policy_id in generic


def test_biden_2025_preset_is_not_double_registered():
    """'Biden 2025 Proposal' in CBO_SCORE_MAP is the same -$252B Treasury target
    already carried as ``biden_high_income_tax``; registering it twice would
    count one prediction twice."""
    targets_at_252 = [
        s for s in get_validation_targets() if s.ten_year_cost == -252.0
    ]
    assert [s.policy_id for s in targets_at_252] == ["biden_high_income_tax"]


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
    assert policy.short_run_elasticity == 0.8
    assert policy.long_run_elasticity == 0.4
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
    assert {(p.short_run_elasticity, p.long_run_elasticity) for p in policies} == {(0.8, 0.4)}


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


def test_create_policy_returns_none_without_a_shape():
    assert create_policy_from_score(_score(policy_type="other")) is None
    assert create_policy_from_score(_score(policy_type="tariff", rate_change=0.1)) is None
