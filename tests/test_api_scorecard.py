"""
End-to-end tests for the GET /validation/scorecard endpoint.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("FISCAL_API_KEYS", raising=False)
    from api import app
    return TestClient(app)


def test_scorecard_endpoint_returns_consolidated_payload(client):
    r = client.get("/validation/scorecard")
    assert r.status_code == 200, r.text
    payload = r.json()

    # Top-level shape.
    for key in (
        "total_entries", "within_5pct", "within_10pct", "within_15pct",
        "within_20pct", "direction_match", "poor",
        "mean_abs_percent_difference", "median_abs_percent_difference",
        "ratings_breakdown", "by_category", "entries",
    ):
        assert key in payload, f"missing key {key!r}"

    assert payload["total_entries"] == len(payload["entries"])
    # Each tolerance bucket nests inside the next.
    assert payload["within_5pct"] <= payload["within_10pct"] <= payload["within_15pct"] <= payload["within_20pct"]


def test_scorecard_entries_have_required_fields(client):
    payload = client.get("/validation/scorecard").json()
    assert payload["entries"], "scorecard returned zero entries"

    sample = payload["entries"][0]
    for key in (
        "category", "policy_id", "policy_name",
        "official_10yr_billions", "official_source",
        "model_10yr_billions", "percent_difference", "abs_percent_difference",
        "rating", "direction_match", "known_limitations", "notes",
    ):
        assert key in sample, f"entry missing field {key!r}"

    assert isinstance(sample["known_limitations"], list)
    assert sample["rating"] in {"Excellent", "Good", "Acceptable", "Poor", "Error"}


def test_scorecard_categories_cover_specialized_validators(client):
    payload = client.get("/validation/scorecard").json()
    cats = set(payload["by_category"].keys())
    # Specialized runners must all be represented; Generic is the catch-all.
    expected = {
        "TCJA", "Corporate", "Credits", "Estate", "Payroll",
        "AMT", "PTC", "CapitalGains", "Expenditures", "Generic",
    }
    assert expected.issubset(cats)


def test_scorecard_aggregate_arithmetic_matches_entries(client):
    payload = client.get("/validation/scorecard").json()
    abs_diffs = [e["abs_percent_difference"] for e in payload["entries"]]

    assert payload["within_15pct"] == sum(1 for d in abs_diffs if d <= 15.0)
    assert payload["poor"] == sum(1 for e in payload["entries"] if e["rating"] == "Poor")
    assert payload["direction_match"] == sum(1 for e in payload["entries"] if e["direction_match"])

    if abs_diffs:
        expected_mean = sum(abs_diffs) / len(abs_diffs)
        assert payload["mean_abs_percent_difference"] == pytest.approx(expected_mean)
