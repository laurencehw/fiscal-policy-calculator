"""
End-to-end tests for the GET /validation/scorecard endpoint.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api as api_module


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
        "calibrated_entries", "generic_entries", "holdout_entries", "validation_note",
        "ratings_breakdown", "by_category", "entries", "issues",
    ):
        assert key in payload, f"missing key {key!r}"

    assert payload["total_entries"] == len(payload["entries"])
    assert payload["calibrated_entries"] + payload["generic_entries"] == payload["total_entries"]
    assert payload["holdout_entries"] >= 8
    assert "post-lock holdout protocol" in payload["validation_note"]
    assert isinstance(payload["issues"], list)
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
        "evidence_type", "holdout_status",
    ):
        assert key in sample, f"entry missing field {key!r}"

    assert isinstance(sample["known_limitations"], list)
    assert sample["rating"] in {"Excellent", "Good", "Acceptable", "Poor", "Error"}
    assert sample["holdout_status"] in {
        "calibration_reference",
        "post_lock_holdout",
        "generic_reference",
    }

    holdouts = [entry for entry in payload["entries"] if entry["holdout_status"] == "post_lock_holdout"]
    assert holdouts
    assert all(entry["evidence_type"] == "locked_holdout_benchmark" for entry in holdouts)


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


def test_scorecard_endpoint_issues_match_material_entry_problems(client):
    payload = client.get("/validation/scorecard").json()
    issue_policy_ids = {issue["policy_id"] for issue in payload["issues"]}
    material_policy_ids = {
        entry["policy_id"]
        for entry in payload["entries"]
        if (
            entry["rating"] in {"Poor", "Error"}
            or not entry["direction_match"]
        )
    }

    assert issue_policy_ids == material_policy_ids
    assert all(issue["surface"] == "revenue_scorecard" for issue in payload["issues"])
    assert all(issue["severity"] in {"warn", "fail"} for issue in payload["issues"])


def test_scorecard_entry_issues_classify_failures_and_warnings():
    issues = api_module._scorecard_entry_issues([
        SimpleNamespace(
            category="TCJA",
            policy_id="ok",
            rating="Good",
            direction_match=True,
            known_limitations=[],
            abs_percent_difference=4.0,
            holdout_status="calibration_reference",
        ),
        SimpleNamespace(
            category="TCJA",
            policy_id="undocumented_poor",
            rating="Poor",
            direction_match=True,
            known_limitations=[],
            abs_percent_difference=40.0,
            holdout_status="calibration_reference",
        ),
        SimpleNamespace(
            category="Generic",
            policy_id="generic_poor",
            rating="Poor",
            direction_match=True,
            known_limitations=[],
            abs_percent_difference=40.0,
            holdout_status="generic_reference",
        ),
        SimpleNamespace(
            category="Credits",
            policy_id="wrong_direction",
            rating="Excellent",
            direction_match=False,
            known_limitations=[],
            abs_percent_difference=1.0,
            holdout_status="post_lock_holdout",
        ),
        SimpleNamespace(
            category="Payroll",
            policy_id="error_case",
            rating="Error",
            direction_match=True,
            known_limitations=[],
            abs_percent_difference=0.0,
            holdout_status="calibration_reference",
        ),
    ])

    by_policy = {issue.policy_id: issue for issue in issues}

    assert "ok" not in by_policy
    assert by_policy["undocumented_poor"].severity == "fail"
    assert by_policy["undocumented_poor"].details["reason"] == "undocumented_poor"
    assert by_policy["generic_poor"].severity == "warn"
    assert by_policy["wrong_direction"].severity == "fail"
    assert by_policy["wrong_direction"].details["reason"] == "direction_mismatch"
    assert by_policy["error_case"].severity == "fail"
    assert by_policy["error_case"].details["reason"] == "error_rating"
