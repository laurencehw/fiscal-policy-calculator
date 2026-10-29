"""The States page prices the SALT cap against current law, not the old $10,000 cap."""

from __future__ import annotations

import pytest

from fiscal_model.models.state import (
    StateTaxDatabase,
    compute_salt_interaction,
    compute_salt_lift,
)
from fiscal_model.models.state.database import SUPPORTED_STATES
from fiscal_model.result_views import states_view
from fiscal_model.tax_expenditures_core import SaltCapBaseline


@pytest.fixture(scope="module")
def db() -> StateTaxDatabase:
    return StateTaxDatabase(2025)


def test_representative_itemizer_cannot_see_the_raised_cap(db):
    # The reason for the new method: every state's average deduction is below
    # $40,000, so the old method reports no effect from lifting the cap at all.
    for code in SUPPORTED_STATES:
        assert db.get_state(code).avg_salt_deduction_itemizers < 40_000
        old = compute_salt_interaction(code, baseline_cap=40_000, reform_cap=None, db=db)
        assert old.federal_revenue_change_billions == 0.0


def test_lifting_the_current_law_cap_costs_revenue_in_every_state(db):
    for code in SUPPORTED_STATES:
        result = compute_salt_lift(code, 2025, db=db)
        assert result.baseline_cap == 40_000.0
        assert result.reform_cap is None
        assert result.federal_revenue_change_billions < 0.0
        assert result.affected_filers > 0.0


def test_reversion_to_10k_in_2030_makes_lifting_cost_more(db):
    for code in SUPPORTED_STATES:
        raised = compute_salt_lift(code, 2025, db=db)
        reverted = compute_salt_lift(code, 2030, db=db)
        assert reverted.baseline_cap == 10_000.0
        assert reverted.federal_revenue_change_billions < raised.federal_revenue_change_billions
        assert reverted.affected_filers > raised.affected_filers


def test_high_salt_states_carry_the_most_cost(db):
    cost = {c: -compute_salt_lift(c, 2025, db=db).federal_revenue_change_billions for c in SUPPORTED_STATES}
    top_two = sorted(cost, key=cost.get, reverse=True)[:2]
    assert set(top_two) == {"CA", "NY"}


def test_lapsed_baseline_has_nothing_to_lift(db):
    result = compute_salt_lift("NY", 2026, baseline=SaltCapBaseline.LAPSED_CAP, db=db)
    assert result.baseline_cap is None
    assert result.federal_revenue_change_billions == 0.0


def test_states_view_reports_the_current_law_cap():
    view = states_view(2025)
    assert view["salt_cap_baseline"] == 40_000.0
    assert view["salt_cap_phasedown_threshold"] == 500_000.0
    assert view["salt_cap_reversion_year"] == 2030
    assert view["salt_cap_reverted"] == 10_000.0
    for state in view["states"]:
        assert state["salt_cap_lift"]["federal_revenue_change_billions"] < 0.0
        assert "salt_cap_lift_reverted" in state
