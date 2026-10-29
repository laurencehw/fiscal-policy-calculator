"""``POST /score/views`` and ``POST /olg``: the site's live result views."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api as api_module

REQUEST = {"rate_change": 0.026, "income_threshold": 400_000, "policy_type": "income_tax"}


def _client() -> TestClient:
    return TestClient(api_module.app)


def test_score_views_agree_with_score():
    client = _client()
    score = client.post("/score", json={**REQUEST, "dynamic": True}).json()
    views = client.post("/score/views", json=REQUEST)
    assert views.status_code == 200
    body = views.json()
    assert set(body) == {"distribution", "economic", "models"}
    assert body["distribution"]["available"] is True
    assert set(body["distribution"]["groupings"]) == {"quintile", "decile", "jct_dollar"}
    econ = body["economic"]
    assert econ["available"] is True
    assert abs(econ["conventional_billions"] - score["ten_year_deficit_impact"]) < 0.05
    assert abs(econ["dynamic_total_billions"] - score["dynamic_adjusted_impact"]) < 0.05
    first = body["models"]["results"][0]
    assert abs(first["ten_year_billions"] - score["ten_year_deficit_impact"]) < 0.05


def test_score_views_rejects_bad_input():
    response = _client().post("/score/views", json={**REQUEST, "policy_type": "not_a_type"})
    assert response.status_code == 400


def test_olg_baseline_is_unchanged():
    body = _client().post("/olg", json={}).json()
    assert body["changed"] is False
    assert body["rates"] == body["baseline_rates"]


def test_olg_reform_returns_long_run_and_accounts():
    response = _client().post(
        "/olg", json={"capital_tax_rate": 0.35, "payroll_tax_rate": 0.124, "replacement_rate": 0.40}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    # A higher capital tax shrinks the long-run capital stock.
    assert body["long_run"]["capital_pct"] < 0
    assert len(body["years"]) == len(body["gdp_path_pct"]) > 0
    assert body["accounts"]["by_age"]
    # The site hides the path when it does not end at the long-run answer.
    assert isinstance(body["path_settles"], bool)


def test_olg_rejects_out_of_range_rates():
    assert _client().post("/olg", json={"capital_tax_rate": 0.9}).status_code == 422
