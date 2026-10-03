"""``POST /score`` custom policies: the base a type names, and the duration.

Two defects, both reproduced against the real scorer (no stubs), because the
dummy scorer the contract tests use cannot tell a corporate base from an
individual one:

* ``policy_type`` of ``corporate_tax`` / ``payroll_tax`` built a plain
  individual-income ``TaxPolicy`` — +1pp at threshold 0 returned -$1,420.3B for
  both, against the corporate module's -$198.9B.
* ``duration_years`` was a no-op: the policy classes honour it only when
  ``sunset`` is set and the API never set it, so 1, 5 and 10 years all scored
  -$116.2B.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api as api_module


def _client() -> TestClient:
    return TestClient(api_module.app)


def _score(**overrides):
    body = {"rate_change": 0.01, "income_threshold": 0, **overrides}
    return _client().post("/score", json=body)


# ---------------------------------------------------------------------------
# 1. policy_type is priced on the base it names
# ---------------------------------------------------------------------------


def test_corporate_tax_is_scored_by_the_corporate_module():
    from fiscal_model.baseline import APP_DEFAULT_START_YEAR
    from fiscal_model.corporate import CorporateTaxPolicy
    from fiscal_model.policies import PolicyType
    from fiscal_model.scoring import FiscalPolicyScorer

    response = _score(policy_type="corporate_tax")
    assert response.status_code == 200, response.text
    corporate = response.json()

    # The same answer the corporate module gives when called directly.
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=True)
    direct = scorer.score_policy(
        CorporateTaxPolicy(
            name="direct",
            description="direct",
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=0.01,
            start_year=APP_DEFAULT_START_YEAR,
        ),
        dynamic=False,
    )
    assert corporate["ten_year_deficit_impact"] == pytest.approx(
        float(direct.final_deficit_effect.sum())
    )

    # ...and not the individual income-tax answer it used to give.
    individual = _score(policy_type="income_tax").json()
    assert individual["ten_year_deficit_impact"] == pytest.approx(-1284.99, abs=1.0)
    assert abs(corporate["ten_year_deficit_impact"]) < 0.25 * abs(
        individual["ten_year_deficit_impact"]
    )
    assert corporate["ten_year_deficit_impact"] < 0  # a rate rise cuts the deficit


def test_corporate_tax_carries_the_corporate_class_band():
    """The accuracy context is the corporate class's, not 'no band: neither'."""
    credibility = _score(policy_type="corporate_tax").json()["credibility"]
    assert credibility["policy_class"] == "corporate"
    assert credibility["uncertainty_low"] is not None
    assert credibility["uncertainty_high"] is not None
    assert credibility["n_tier1_rows"] > 0


def test_corporate_tax_rejects_an_income_threshold():
    response = _score(policy_type="corporate_tax", income_threshold=400000)
    assert response.status_code == 400
    assert "income_threshold" in response.json()["detail"]


def test_payroll_tax_is_rejected_not_scored_on_the_wrong_base():
    response = _score(policy_type="payroll_tax")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "payroll_tax" in detail
    assert "not supported" in detail


# ---------------------------------------------------------------------------
# 2. duration_years changes the score
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        {"policy_type": "income_tax", "income_threshold": 400000},
        {"policy_type": "corporate_tax", "income_threshold": 0},
    ],
    ids=["income_tax", "corporate_tax"],
)
def test_duration_years_changes_the_total_monotonically(extra):
    totals = {}
    for duration in (1, 5, 10):
        response = _score(duration_years=duration, **extra)
        assert response.status_code == 200, response.text
        payload = response.json()
        totals[duration] = payload["ten_year_deficit_impact"]

        # Per-year rows beyond the duration are zero; inside it they are not.
        rows = payload["year_by_year"]
        assert len(rows) == 10
        for index, row in enumerate(rows):
            if index < duration:
                assert row["final_effect"] != 0.0
            else:
                assert row["final_effect"] == 0.0
                assert row["revenue_effect"] == 0.0
                assert row["behavioral_offset"] == 0.0

    # A revenue raiser's deficit effect gets more negative the longer it runs.
    assert totals[1] > totals[5] > totals[10]
    assert totals[1] < 0


def test_a_duration_at_or_beyond_the_window_is_the_default_score():
    default = _score(income_threshold=400000).json()["ten_year_deficit_impact"]
    for duration in (10, 11, 30):
        got = _score(income_threshold=400000, duration_years=duration).json()
        assert got["ten_year_deficit_impact"] == pytest.approx(default)
