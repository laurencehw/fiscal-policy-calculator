"""Pinned tracker corrections: H.R. 1, H.Con.Res. 14, coverage, nightly overwrite."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
FALLBACK = ROOT / "bill_tracker" / "cbo_manual_scores.json"
MAPPINGS = ROOT / "bill_tracker" / "manual_mappings.json"
PINNED = ROOT / "bill_tracker" / "pinned_corrections.json"


@pytest.fixture
def sample_bill():
    from bill_tracker.ingestor import BillMetadata

    return BillMetadata(
        bill_id="hr-1-119",
        congress=119,
        chamber="house",
        number="1",
        bill_type="hr",
        title="An act to provide for reconciliation pursuant to title II of H. Con. Res. 14.",
        sponsor="Unknown",
        introduced_date=datetime(2025, 1, 3),
        latest_action="Became Public Law No: 119-21.",
        latest_action_date=datetime(2025, 7, 4),
        status="enacted",
        summary="Reconciliation act.",
        url="https://www.congress.gov/bill/119th-congress/house-bill/1",
    )


@pytest.fixture
def budget_resolution():
    from bill_tracker.ingestor import BillMetadata

    return BillMetadata(
        bill_id="hconres-14-119",
        congress=119,
        chamber="house",
        number="14",
        bill_type="hconres",
        title="Establishing the congressional budget for the United States Government for fiscal year 2025.",
        sponsor="Unknown",
        introduced_date=datetime(2025, 2, 18),
        latest_action="Star Print ordered on the reported concurrent resolution.",
        latest_action_date=datetime(2025, 5, 20),
        status="committee",
        summary="Budget resolution.",
        url="https://www.congress.gov/bill/119th-congress/house-concurrent-resolution/14",
    )


def test_hr1_mapping_has_no_corporate_rate_cut():
    data = json.loads(MAPPINGS.read_text(encoding="utf-8"))
    entry = data["hr-1-119"]
    for policy in entry["policies"]:
        assert policy["policy_type"] != "corporate"
        params = policy.get("parameters") or {}
        assert params.get("rate_change") in (None, 0, 0.0)
    assert any("corporate" in text.lower() for text in entry["unmapped_provisions"]) is False
    assert "unmapped_provisions" in entry
    assert len(entry["unmapped_provisions"]) >= 4


def test_hr1_override_is_never_high_confidence():
    from bill_tracker.provision_mapper import ProvisionMapper

    mapper = ProvisionMapper(anthropic_client=MagicMock())
    result = mapper.map_bill("hr-1-119", "ignored")
    assert result.extraction_method == "manual"
    assert result.confidence != "high"
    assert result.confidence == "medium"
    assert "provisions mapped" in result.confidence_reason
    assert not any(p.get("policy_type") == "corporate" for p in result.policies)


def test_partial_mapping_never_high_for_llm():
    from bill_tracker.provision_mapper import ProvisionMapper

    llm_response = json.dumps(
        [
            {
                "policy_type": "income_tax",
                "parameters": {"rate_change": 0.01},
                "confidence": "high",
                "provision_text": "Raises the top rate 1pp",
            },
            {
                "policy_type": "other",
                "parameters": {"description": "Medicaid work requirements"},
                "confidence": "high",
                "provision_text": "Adds Medicaid work requirements",
            },
        ]
    )
    mock_content = MagicMock()
    mock_content.text = llm_response
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    mapper = ProvisionMapper(anthropic_client=mock_client)
    result = mapper.map_bill("hr-9876-119", "Raises the top rate 1pp. Adds Medicaid work requirements.")
    assert result.confidence != "high"
    assert result.unmapped_provisions
    assert "provisions mapped" in result.confidence_reason


def test_fully_mapped_high_confidence_still_allowed():
    from bill_tracker.confidence import mapping_confidence

    conf, reason = mapping_confidence(
        [{"policy_type": "income_tax", "confidence": "high", "provision_text": "a"}],
        [],
    )
    assert conf == "high"
    assert "1 of 1" in reason


def test_cbo_title_parser_does_not_map_pursuant_to_budget_resolution():
    from bill_tracker.cbo_fetcher import CBOCostEstimate, CBOScoreFetcher
    from bill_tracker.citations import is_concurrent_resolution, subject_bill_id

    title = (
        "Public Law 119-21, to Provide for Reconciliation Pursuant to Title II of H. Con. Res. 14"
    )
    assert subject_bill_id(title) == "hr-1-119"
    assert is_concurrent_resolution("hconres-14-119")

    estimate = CBOCostEstimate(
        bill_id="",
        title=title,
        estimate_date=datetime(2025, 10, 28),
        ten_year_cost_billions=84.95,
        cbo_url="https://www.cbo.gov/publication/61838",
    )
    fetcher = CBOScoreFetcher()
    assert fetcher.match_to_bill_from_estimates(
        "hconres-14-119",
        "Establishing the congressional budget for FY2025",
        [estimate],
    ) is None
    matched = fetcher.match_to_bill_from_estimates(
        "hr-1-119",
        "One Big Beautiful Bill Act",
        [estimate],
    )
    assert matched is not None
    assert matched.bill_id == "hr-1-119"


def test_hr1_does_not_match_hr10():
    from bill_tracker.cbo_fetcher import CBOCostEstimate, CBOScoreFetcher

    estimate = CBOCostEstimate(
        bill_id="",
        title="H.R. 10, Some Other Act",
        estimate_date=datetime(2025, 6, 1),
        ten_year_cost_billions=1.0,
    )
    fetcher = CBOScoreFetcher()
    assert (
        fetcher.match_to_bill_from_estimates("hr-1-119", "Reconciliation", [estimate]) is None
    )
    matched = fetcher.match_to_bill_from_estimates("hr-10-119", "Some Other Act", [estimate])
    assert matched is not None
    assert matched.bill_id == "hr-10-119"


def test_fallback_json_has_no_conres_and_hr1_points_at_61570():
    from bill_tracker.citations import is_concurrent_resolution, title_bill_id_mismatch

    payload = json.loads(FALLBACK.read_text(encoding="utf-8"))
    scores = payload["scores"]
    hr1 = [s for s in scores if s.get("bill_id") == "hr-1-119"]
    assert len(hr1) == 1
    assert hr1[0]["ten_year_cost_billions"] == 3400.0
    assert hr1[0]["cbo_url"].endswith("/61570")
    for row in scores:
        bid = str(row.get("bill_id", ""))
        assert not is_concurrent_resolution(bid), bid
        assert title_bill_id_mismatch(bid, row.get("title", "")) is None, row


def test_pinned_file_names_enacted_cbo_and_no_budget_resolution_score():
    pinned = json.loads(PINNED.read_text(encoding="utf-8"))
    hr1 = pinned["cbo_scores"]["hr-1-119"]
    assert hr1["ten_year_cost_billions"] == 3400.0
    assert hr1["cbo_url"].endswith("/61570")
    assert "hconres-14-119" in pinned["no_cbo_score"]
    assert pinned["status"]["hconres-14-119"]["status"] == "adopted"


def test_apply_pinned_corrections_overwrites_live_cbo(tmp_path, sample_bill, budget_resolution):
    from bill_tracker.cbo_fetcher import CBOCostEstimate
    from bill_tracker.corrections import apply_pinned_corrections
    from bill_tracker.database import BillDatabase

    db = BillDatabase(str(tmp_path / "bills.db"))
    db.upsert_bill(sample_bill)
    db.upsert_bill(budget_resolution)
    db.upsert_cbo_score(
        CBOCostEstimate(
            bill_id="hr-1-119",
            title="H.R. 1, One Big, Beautiful Bill Act",
            estimate_date=datetime(2025, 7, 22),
            ten_year_cost_billions=3500.0,
            cbo_url="https://www.cbo.gov/publication/61571",
        )
    )
    db.upsert_cbo_score(
        CBOCostEstimate(
            bill_id="hconres-14-119",
            title="Public Law 119-21, to Provide for Reconciliation Pursuant to Title II of H. Con.",
            estimate_date=datetime(2025, 10, 28),
            ten_year_cost_billions=84.95,
            cbo_url="https://www.cbo.gov/publication/61838",
        )
    )

    mock_scorer = MagicMock()
    mock_result = MagicMock()
    mock_result.static_revenue_effect = 4000.0
    mock_result.behavioral_offset = 0.0
    mock_result.final_deficit_effect = 4000.0
    mock_scorer.score_policy.return_value = mock_result
    from bill_tracker.auto_scorer import AutoScorer

    counts = apply_pinned_corrections(db, scorer=AutoScorer(scorer=mock_scorer))
    assert counts["cbo_replaced"] == 1
    assert counts["cbo_cleared"] == 1
    assert counts["status"] == 1
    assert counts["rescored"] == 1

    hr1 = db.get_cbo_score("hr-1-119")
    assert hr1 is not None
    assert hr1["ten_year_cost_billions"] == 3400.0
    assert hr1["cbo_url"].endswith("/61570")
    assert db.get_cbo_score("hconres-14-119") is None
    assert db.get_bill("hconres-14-119")["has_cbo_score"] == 0
    assert db.get_bill("hconres-14-119")["status"] == "adopted"
    auto = db.get_auto_score("hr-1-119")
    assert auto is not None
    assert auto["confidence"] != "high"
    policies = json.loads(auto["policies_json"])
    assert not any(p.get("policy_type") == "corporate" for p in policies)
    assert any(p.get("mapped") is False for p in policies)


def test_skip_live_cbo_match_covers_pins_and_conres():
    from bill_tracker.corrections import skip_live_cbo_match

    assert skip_live_cbo_match("hr-1-119") is True
    assert skip_live_cbo_match("hconres-14-119") is True
    assert skip_live_cbo_match("sconres-7-119") is True
    assert skip_live_cbo_match("hr-1234-119") is False


def test_auto_scorer_stores_unmapped_for_coverage():
    from bill_tracker.auto_scorer import AutoScorer
    from bill_tracker.provision_mapper import MappingResult

    mock_scorer = MagicMock()
    mock_result = MagicMock()
    mock_result.static_revenue_effect = 100.0
    mock_result.behavioral_offset = 0.0
    mock_result.final_deficit_effect = 100.0
    mock_scorer.score_policy.return_value = mock_result
    mapping = MappingResult(
        bill_id="hr-1-119",
        policies=[
            {
                "policy_type": "tcja_extension",
                "parameters": {"extend_all": True, "keep_salt_cap": True},
                "confidence": "high",
                "provision_text": "Extend TCJA",
            }
        ],
        confidence="medium",
        confidence_reason="Partial mapping; 1 of 3 provisions mapped",
        unmapped_provisions=["SNAP changes", "Medicaid work requirements"],
        extraction_method="manual",
    )
    score = AutoScorer(scorer=mock_scorer).score(mapping)
    assert score is not None
    assert score.confidence == "medium"
    assert sum(1 for p in score.policies_json if p.get("mapped") is False) == 2


def test_nightly_update_script_applies_pins_after_the_fetch_loop():
    text = (ROOT / "scripts" / "update_bills.py").read_text(encoding="utf-8")
    assert "apply_pinned_corrections" in text
    assert "skip_live_cbo_match" in text
    workflow = (ROOT / ".github" / "workflows" / "update-bills.yml").read_text(encoding="utf-8")
    assert "pinned_corrections.json" in workflow


def test_committed_database_reflects_the_pins():
    from bill_tracker.database import BillDatabase

    db = BillDatabase(str(ROOT / "fiscal_model" / "data_files" / "bills.db"))
    cbo = db.get_cbo_score("hr-1-119")
    assert cbo is not None
    assert cbo["ten_year_cost_billions"] == 3400.0
    assert cbo["cbo_url"].endswith("/61570")
    assert db.get_cbo_score("hconres-14-119") is None
    assert db.get_bill("hconres-14-119")["has_cbo_score"] == 0
    assert db.get_bill("hconres-14-119")["status"] == "adopted"
    auto = db.get_auto_score("hr-1-119")
    assert auto is not None
    assert auto["confidence"] != "high"
    policies = json.loads(auto["policies_json"])
    assert not any(p.get("policy_type") == "corporate" for p in policies)


def test_export_coverage_helper():
    from scripts.export_static import _auto_coverage

    label = _auto_coverage(
        {
            "policies_json": json.dumps(
                [
                    {"policy_type": "tcja_extension", "confidence": "high"},
                    {"policy_type": "other", "mapped": False, "provision_text": "SNAP"},
                ]
            )
        }
    )
    assert label == "1 of 2 provisions mapped"
