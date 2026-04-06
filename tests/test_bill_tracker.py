"""
Tests for the Bill Tracker (Feature 4).

Coverage:
- BillIngestor: metadata parsing, bill_id construction, status normalization
- CBOScoreFetcher: cost parsing, bill matching, HTML parsing
- ProvisionMapper: LLM mock extraction, JSON parsing, regex validation, overrides
- BillDatabase: CRUD operations, upsert semantics, pipeline state
- FreshnessStatus: all freshness tiers, enacted status
- AutoScorer: policy construction, scoring dispatch, aggregation
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def sample_bill_raw():
    """Raw dict from congress.gov API."""
    return {
        "type": "hr",
        "number": "1234",
        "title": "Tax Relief for American Families Act",
        "sponsors": [
            {"firstName": "Jason", "lastName": "Smith", "party": "R", "state": "MO"}
        ],
        "introducedDate": "2025-01-15",
        "latestAction": {"text": "Referred to Committee on Ways and Means", "actionDate": "2025-01-16"},
        "originChamber": "House",
        "policyArea": {"name": "Taxation"},
    }


@pytest.fixture
def sample_bill_metadata():
    from bill_tracker.ingestor import BillMetadata
    return BillMetadata(
        bill_id="hr-1234-119",
        congress=119,
        chamber="house",
        number="1234",
        bill_type="hr",
        title="Tax Relief for American Families Act",
        sponsor="Jason Smith (R-MO)",
        introduced_date=datetime(2025, 1, 15),
        latest_action="Referred to Committee on Ways and Means",
        latest_action_date=datetime(2025, 1, 16),
        status="committee",
        crs_subjects=["Taxation"],
        has_cbo_score=False,
        summary="This bill reduces individual income taxes for families earning less than $400,000.",
        url="https://www.congress.gov/bill/119th-congress/house-bill/1234",
        last_fetched=datetime(2026, 4, 1),
    )


@pytest.fixture
def tmp_db(tmp_path):
    from bill_tracker.database import BillDatabase
    return BillDatabase(str(tmp_path / "test_bills.db"))


# ==================================================================
# BillIngestor tests
# ==================================================================

class TestBillIngestor:
    def test_bill_id_format(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(sample_bill_raw, congress=119)
        assert meta is not None
        assert meta.bill_id == "hr-1234-119"

    def test_sponsor_formatting(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(sample_bill_raw, congress=119)
        assert meta is not None
        assert "Smith" in meta.sponsor
        assert "(R-MO)" in meta.sponsor

    def test_chamber_normalization(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(sample_bill_raw, congress=119)
        assert meta.chamber == "house"

    def test_senate_bill(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        raw = {**sample_bill_raw, "type": "s", "originChamber": "Senate"}
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(raw, congress=119)
        assert meta.bill_id == "s-1234-119"
        assert meta.chamber == "senate"

    def test_status_committee(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(sample_bill_raw, congress=119)
        assert meta.status == "committee"

    def test_status_enacted(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        raw = {**sample_bill_raw}
        raw["latestAction"] = {"text": "Signed by President", "actionDate": "2025-06-01"}
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(raw, congress=119)
        assert meta.status == "enacted"

    def test_status_passed_chamber(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        raw = {**sample_bill_raw}
        raw["latestAction"] = {"text": "Passed House by voice vote", "actionDate": "2025-03-01"}
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(raw, congress=119)
        assert meta.status == "passed_chamber"

    def test_status_introduced(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        raw = {**sample_bill_raw}
        raw["latestAction"] = {"text": "Introduced in House", "actionDate": "2025-01-15"}
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(raw, congress=119)
        assert meta.status == "introduced"

    def test_crs_subjects_parsed(self, sample_bill_raw):
        from bill_tracker.ingestor import BillIngestor
        ingestor = BillIngestor(api_key="test")
        meta = ingestor._parse_bill_metadata(sample_bill_raw, congress=119)
        assert "Taxation" in meta.crs_subjects

    def test_fetch_recent_bills_mocked(self):
        """Test fetch_recent_bills with mocked HTTP response."""
        from bill_tracker.ingestor import BillIngestor

        mock_response = {
            "bills": [
                {
                    "type": "hr",
                    "number": "100",
                    "title": "Test Tax Bill",
                    "sponsors": [{"firstName": "Jane", "lastName": "Doe", "party": "D", "state": "CA"}],
                    "introducedDate": "2025-02-01",
                    "latestAction": {"text": "Referred to Committee", "actionDate": "2025-02-02"},
                    "originChamber": "House",
                    "policyArea": {"name": "Taxation"},
                }
            ]
        }

        ingestor = BillIngestor(api_key="test")
        with patch.object(ingestor, "_get", return_value=mock_response):
            bills = ingestor.fetch_recent_bills(congress=119, limit=10)

        assert len(bills) == 1
        assert bills[0].bill_id == "hr-100-119"

    def test_graceful_api_failure(self):
        """Returns empty list on API failure."""
        from bill_tracker.ingestor import BillIngestor
        ingestor = BillIngestor(api_key="bad_key")
        with patch.object(ingestor, "_get", return_value=None):
            bills = ingestor.fetch_recent_bills()
        assert bills == []

    def test_ordinal_helper(self):
        from bill_tracker.ingestor import _ordinal
        assert _ordinal(119) == "119th"
        assert _ordinal(1) == "1st"
        assert _ordinal(2) == "2nd"
        assert _ordinal(3) == "3rd"
        assert _ordinal(11) == "11th"
        assert _ordinal(21) == "21st"


# ==================================================================
# CBOScoreFetcher tests
# ==================================================================

class TestCBOScoreFetcher:
    def test_parse_cost_billions_number(self):
        from bill_tracker.cbo_fetcher import _parse_cost_billions
        assert _parse_cost_billions(33.5) == 33.5
        assert _parse_cost_billions(-1350.0) == -1350.0

    def test_parse_cost_billions_string(self):
        from bill_tracker.cbo_fetcher import _parse_cost_billions
        assert _parse_cost_billions("33.5") == 33.5
        assert _parse_cost_billions("$1,234.5") == 1234.5

    def test_bill_id_to_ref(self):
        from bill_tracker.cbo_fetcher import _bill_id_to_ref
        assert _bill_id_to_ref("hr-7024-118") == "H.R. 7024"
        assert _bill_id_to_ref("s-1-119") == "S. 1"

    def test_fetch_recent_estimates_mocked(self):
        from bill_tracker.cbo_fetcher import CBOScoreFetcher
        mock_data = [
            {
                "title": "Tax Relief for American Families and Workers Act H.R. 7024",
                "publishedAt": "2024-02-01",
                "cost": -33.5,
                "url": "https://www.cbo.gov/publication/12345",
            }
        ]
        fetcher = CBOScoreFetcher()
        with patch.object(fetcher, "_get_json", return_value=mock_data):
            estimates = fetcher.fetch_recent_estimates(limit=10)

        assert len(estimates) == 1
        assert estimates[0].ten_year_cost_billions == -33.5

    def test_match_to_bill_by_bill_number(self):
        from bill_tracker.cbo_fetcher import CBOCostEstimate, CBOScoreFetcher
        estimate = CBOCostEstimate(
            bill_id="",
            title="Cost Estimate for H.R. 7024 — Tax Relief Act",
            estimate_date=datetime(2024, 2, 1),
            ten_year_cost_billions=-33.5,
        )
        fetcher = CBOScoreFetcher()
        with patch.object(fetcher, "fetch_recent_estimates", return_value=[estimate]):
            result = fetcher.match_to_bill("hr-7024-118", "Tax Relief Act")

        assert result is not None
        assert result.ten_year_cost_billions == -33.5
        assert result.bill_id == "hr-7024-118"

    def test_match_to_bill_no_match(self):
        from bill_tracker.cbo_fetcher import CBOScoreFetcher
        fetcher = CBOScoreFetcher()
        with patch.object(fetcher, "fetch_recent_estimates", return_value=[]):
            result = fetcher.match_to_bill("hr-9999-119", "Some Obscure Bill")
        assert result is None


# ==================================================================
# ProvisionMapper tests
# ==================================================================

class TestProvisionMapper:
    def _make_mock_client(self, json_response: str):
        """Create a mock Anthropic client that returns the given JSON."""
        mock_content = MagicMock()
        mock_content.text = json_response
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        return mock_client

    def test_extract_income_tax_provision(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        llm_response = json.dumps([{
            "policy_type": "income_tax",
            "parameters": {"rate_change": 0.026, "affected_income_threshold": 400000},
            "confidence": "high",
            "provision_text": "Increases top marginal rate by 2.6 percentage points on income above $400,000"
        }])
        mock_client = self._make_mock_client(llm_response)
        mapper = ProvisionMapper(anthropic_client=mock_client)
        result = mapper.map_bill(
            "hr-1234-119",
            "This bill increases the marginal income tax rate by 2.6 percentage points "
            "on income above $400,000."
        )
        assert result.bill_id == "hr-1234-119"
        assert len(result.policies) == 1
        assert result.policies[0]["policy_type"] == "income_tax"
        assert result.confidence in ("high", "medium")
        assert result.extraction_method == "llm"

    def test_extract_corporate_provision(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        llm_response = json.dumps([{
            "policy_type": "corporate",
            "parameters": {"rate_change": 0.07},
            "confidence": "high",
            "provision_text": "Raises corporate rate from 21% to 28%"
        }])
        mock_client = self._make_mock_client(llm_response)
        mapper = ProvisionMapper(anthropic_client=mock_client)
        result = mapper.map_bill("s-1-119", "Raises corporate income tax rate from 21% to 28%.")
        assert result.policies[0]["policy_type"] == "corporate"
        assert result.policies[0]["parameters"]["rate_change"] == 0.07

    def test_empty_summary_returns_low_confidence(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        mapper = ProvisionMapper(anthropic_client=MagicMock())
        result = mapper.map_bill("hr-0-119", "")
        assert result.confidence == "low"
        assert result.policies == []

    def test_none_summary_returns_low_confidence(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        mapper = ProvisionMapper(anthropic_client=MagicMock())
        result = mapper.map_bill("hr-0-119", None)
        assert result.confidence == "low"

    def test_llm_failure_returns_empty_policies(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mapper = ProvisionMapper(anthropic_client=mock_client)
        result = mapper.map_bill("hr-0-119", "Some summary text about taxes.")
        assert result.policies == []
        assert result.confidence == "low"

    def test_json_parse_with_markdown_fences(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        mapper = ProvisionMapper(anthropic_client=MagicMock())
        raw = '```json\n[{"policy_type": "income_tax", "parameters": {}, "confidence": "high", "provision_text": "test"}]\n```'
        parsed = mapper._parse_llm_json(raw)
        assert len(parsed) == 1
        assert parsed[0]["policy_type"] == "income_tax"

    def test_regex_validation_implausible_rate(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        mapper = ProvisionMapper(anthropic_client=MagicMock())
        policies = [{"policy_type": "income_tax", "parameters": {"rate_change": 0.75}, "provision_text": ""}]
        warnings = mapper._validate_with_regex(policies, "Increase tax by 75%")
        assert any("implausible" in w for w in warnings)

    def test_regex_validation_rate_not_in_text(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        mapper = ProvisionMapper(anthropic_client=MagicMock())
        # LLM says 5% but text says 2.6%
        policies = [{"policy_type": "income_tax", "parameters": {"rate_change": 0.05}, "provision_text": ""}]
        warnings = mapper._validate_with_regex(policies, "Raises rate by 2.6 percentage points")
        assert any("not found" in w for w in warnings)

    def test_manual_override_from_file(self, tmp_path):
        from bill_tracker.provision_mapper import ProvisionMapper
        override_data = {
            "hr-7024-118": {
                "policies": [{"policy_type": "credits", "parameters": {"credit_amount_billions": 33.5}}],
                "override_reason": "Test override",
                "mapped_by": "test",
            }
        }
        # Write to manual_mappings.json (the primary combined file)
        (tmp_path / "manual_mappings.json").write_text(json.dumps(override_data))

        mapper = ProvisionMapper(anthropic_client=MagicMock())
        mapper.MANUAL_OVERRIDES_PATH = tmp_path
        result = mapper.map_bill("hr-7024-118", "Some summary")

        assert result.extraction_method == "manual"
        assert result.confidence == "high"
        assert result.policies[0]["policy_type"] == "credits"

    def test_unmapped_provisions_excluded_from_policies(self):
        from bill_tracker.provision_mapper import ProvisionMapper
        llm_response = json.dumps([
            {"policy_type": "other", "parameters": {"description": "Medicaid work requirements"}, "confidence": "low", "provision_text": "Adds Medicaid work requirements"},
            {"policy_type": "income_tax", "parameters": {"rate_change": 0.026}, "confidence": "high", "provision_text": "Income tax increase"}
        ])
        mock_client = self._make_mock_client(llm_response)
        mapper = ProvisionMapper(anthropic_client=mock_client)
        # Use a bill_id that has no manual override
        result = mapper.map_bill("hr-9876-119", "Income tax increase 2.6%. Also Medicaid work requirements.")
        assert all(p["policy_type"] != "other" for p in result.policies)
        assert len(result.unmapped_provisions) == 1


# ==================================================================
# BillDatabase tests
# ==================================================================

class TestBillDatabase:
    def test_upsert_and_get_bill(self, tmp_db, sample_bill_metadata):
        tmp_db.upsert_bill(sample_bill_metadata)
        row = tmp_db.get_bill("hr-1234-119")
        assert row is not None
        assert row["title"] == "Tax Relief for American Families Act"
        assert row["sponsor"] == "Jason Smith (R-MO)"
        assert row["status"] == "committee"

    def test_upsert_updates_existing_bill(self, tmp_db, sample_bill_metadata):
        tmp_db.upsert_bill(sample_bill_metadata)
        sample_bill_metadata.status = "passed_chamber"
        tmp_db.upsert_bill(sample_bill_metadata)
        row = tmp_db.get_bill("hr-1234-119")
        assert row["status"] == "passed_chamber"

    def test_count_bills(self, tmp_db, sample_bill_metadata):
        assert tmp_db.count_bills() == 0
        tmp_db.upsert_bill(sample_bill_metadata)
        assert tmp_db.count_bills() == 1

    def test_get_all_bills_filter_status(self, tmp_db, sample_bill_metadata):
        tmp_db.upsert_bill(sample_bill_metadata)
        rows = tmp_db.get_all_bills(status="committee")
        assert len(rows) == 1
        rows_enacted = tmp_db.get_all_bills(status="enacted")
        assert len(rows_enacted) == 0

    def test_upsert_cbo_score(self, tmp_db, sample_bill_metadata):
        from bill_tracker.cbo_fetcher import CBOCostEstimate
        tmp_db.upsert_bill(sample_bill_metadata)
        estimate = CBOCostEstimate(
            bill_id="hr-1234-119",
            title="Tax Relief Act",
            estimate_date=datetime(2025, 6, 1),
            ten_year_cost_billions=-33.5,
            cbo_url="https://www.cbo.gov/1234",
        )
        tmp_db.upsert_cbo_score(estimate)
        score = tmp_db.get_cbo_score("hr-1234-119")
        assert score is not None
        assert score["ten_year_cost_billions"] == -33.5
        # Bill should now be marked as having a CBO score
        bill = tmp_db.get_bill("hr-1234-119")
        assert bill["has_cbo_score"] == 1

    def test_upsert_auto_score(self, tmp_db, sample_bill_metadata):
        from bill_tracker.auto_scorer import BillScore
        tmp_db.upsert_bill(sample_bill_metadata)
        score = BillScore(
            bill_id="hr-1234-119",
            scored_at=datetime(2026, 4, 1),
            ten_year_cost_billions=-250.0,
            annual_effects=[-25.0] * 10,
            static_cost=-260_000_000_000.0,
            behavioral_offset=10_000_000_000.0,
            confidence="high",
            policies_json=[{"policy_type": "income_tax"}],
        )
        tmp_db.upsert_auto_score(score)
        result = tmp_db.get_auto_score("hr-1234-119")
        assert result is not None
        assert result["ten_year_cost_billions"] == -250.0
        assert result["confidence"] == "high"

    def test_manual_override_roundtrip(self, tmp_db):
        policies = [{"policy_type": "tcja_extension", "parameters": {"extend_all": True}}]
        tmp_db.upsert_manual_override(
            "hr-1-119", policies, override_reason="Test", mapped_by="test_user"
        )
        assert tmp_db.has_manual_override("hr-1-119")
        assert not tmp_db.has_manual_override("hr-9999-119")

    def test_pipeline_state_roundtrip(self, tmp_db):
        assert tmp_db.get_last_update() is None
        now = datetime(2026, 4, 1, 6, 0, 0)
        tmp_db.set_last_update(now)
        retrieved = tmp_db.get_last_update()
        assert retrieved is not None
        assert retrieved.year == 2026
        assert retrieved.month == 4


# ==================================================================
# Freshness tests
# ==================================================================

class TestFreshness:
    def test_fresh_bill(self):
        from bill_tracker.freshness import check_freshness
        now = datetime(2026, 4, 1, 12, 0, 0)
        result = check_freshness(
            "hr-1-119",
            last_fetched=datetime(2026, 4, 1, 6, 0, 0),
            status="committee",
            now=now,
        )
        assert result.status == "fresh"
        assert result.badge_color == "green"
        assert result.warning is None

    def test_stale_bill_3_days(self):
        from bill_tracker.freshness import check_freshness
        now = datetime(2026, 4, 4)
        result = check_freshness(
            "hr-1-119",
            last_fetched=datetime(2026, 4, 1),
            status="committee",
            now=now,
        )
        assert result.status == "stale"
        assert result.badge_color == "yellow"
        assert result.warning is not None
        assert "3 days" in result.warning

    def test_outdated_bill_15_days(self):
        from bill_tracker.freshness import check_freshness
        now = datetime(2026, 4, 16)
        result = check_freshness(
            "hr-1-119",
            last_fetched=datetime(2026, 4, 1),
            status="introduced",
            now=now,
        )
        assert result.status == "outdated"
        assert result.badge_color == "red"

    def test_expired_bill_45_days(self):
        from bill_tracker.freshness import check_freshness
        now = datetime(2026, 5, 16)
        result = check_freshness(
            "hr-1-119",
            last_fetched=datetime(2026, 4, 1),
            status="introduced",
            now=now,
        )
        assert result.status == "expired"
        assert "days old" in result.warning

    def test_enacted_bill_always_blue(self):
        from bill_tracker.freshness import check_freshness
        now = datetime(2026, 4, 1)
        result = check_freshness(
            "hr-1-119",
            last_fetched=datetime(2025, 1, 1),  # Very old
            status="enacted",
            now=now,
        )
        assert result.status == "enacted"
        assert result.badge_color == "blue"
        assert result.warning is None

    def test_days_since_update_calculated(self):
        from bill_tracker.freshness import check_freshness
        now = datetime(2026, 4, 10)
        result = check_freshness(
            "hr-1-119",
            last_fetched=datetime(2026, 4, 5),
            status="committee",
            now=now,
        )
        assert result.days_since_update == 5

    def test_freshness_from_db_row(self, tmp_db, sample_bill_metadata):
        from bill_tracker.freshness import freshness_from_db_row
        # Insert a fresh bill
        sample_bill_metadata.last_fetched = datetime.utcnow()
        tmp_db.upsert_bill(sample_bill_metadata)
        row = tmp_db.get_bill("hr-1234-119")
        status = freshness_from_db_row(row)
        assert status.status in ("fresh", "stale", "outdated", "expired", "enacted")


# ==================================================================
# AutoScorer tests
# ==================================================================

class TestAutoScorer:
    def _make_mapping(self, policies, confidence="high", bill_id="hr-1-119"):
        from bill_tracker.provision_mapper import MappingResult
        return MappingResult(
            bill_id=bill_id,
            policies=policies,
            confidence=confidence,
            confidence_reason="test",
            extraction_method="llm",
        )

    def test_score_income_tax_policy(self):
        from bill_tracker.auto_scorer import AutoScorer
        mock_scorer = MagicMock()
        mock_result = MagicMock()
        mock_result.static_revenue_effect = -250_000_000_000.0
        mock_result.behavioral_offset = 10_000_000_000.0
        mock_result.final_deficit_effect = 240_000_000_000.0
        mock_scorer.score_policy.return_value = mock_result

        scorer = AutoScorer(scorer=mock_scorer)
        mapping = self._make_mapping([{
            "policy_type": "income_tax",
            "parameters": {"rate_change": 0.026, "affected_income_threshold": 400000},
            "confidence": "high",
            "provision_text": "Raises top rate by 2.6pp",
        }])
        result = scorer.score(mapping)
        assert result is not None
        assert result.bill_id == "hr-1-119"
        assert result.confidence == "high"

    def test_score_returns_none_for_empty_policies(self):
        from bill_tracker.auto_scorer import AutoScorer
        scorer = AutoScorer(scorer=MagicMock())
        mapping = self._make_mapping([])
        result = scorer.score(mapping)
        assert result is None

    def test_build_income_tax_policy(self):
        from bill_tracker.auto_scorer import AutoScorer
        from fiscal_model import TaxPolicy
        scorer = AutoScorer()
        policy = scorer._build_policy({
            "policy_type": "income_tax",
            "parameters": {"rate_change": 0.026, "affected_income_threshold": 400000},
            "provision_text": "test",
        })
        assert isinstance(policy, TaxPolicy)
        assert policy.rate_change == pytest.approx(0.026)

    def test_build_corporate_policy(self):
        from bill_tracker.auto_scorer import AutoScorer
        from fiscal_model.corporate import CorporateTaxPolicy
        scorer = AutoScorer()
        policy = scorer._build_policy({
            "policy_type": "corporate",
            "parameters": {"rate_change": 0.07},
            "provision_text": "test",
        })
        assert isinstance(policy, CorporateTaxPolicy)

    def test_build_spending_policy(self):
        from bill_tracker.auto_scorer import AutoScorer
        from fiscal_model import SpendingPolicy
        scorer = AutoScorer()
        policy = scorer._build_policy({
            "policy_type": "spending",
            "parameters": {"spending_change_billions": 100.0},
            "provision_text": "test",
        })
        assert isinstance(policy, SpendingPolicy)

    def test_build_unknown_policy_returns_none(self):
        from bill_tracker.auto_scorer import AutoScorer
        scorer = AutoScorer()
        policy = scorer._build_policy({
            "policy_type": "unknown_type_xyz",
            "parameters": {},
            "provision_text": "test",
        })
        assert policy is None

    def test_score_aggregates_multiple_policies(self):
        from bill_tracker.auto_scorer import AutoScorer
        mock_scorer = MagicMock()

        def mock_score(policy, dynamic=False):
            r = MagicMock()
            r.static_revenue_effect = -100_000_000_000.0
            r.behavioral_offset = 5_000_000_000.0
            r.final_deficit_effect = 95_000_000_000.0
            return r

        mock_scorer.score_policy.side_effect = mock_score
        scorer = AutoScorer(scorer=mock_scorer)

        mapping = self._make_mapping([
            {"policy_type": "income_tax", "parameters": {"rate_change": 0.02}, "confidence": "high", "provision_text": "a"},
            {"policy_type": "corporate", "parameters": {"rate_change": 0.03}, "confidence": "high", "provision_text": "b"},
        ])
        result = scorer.score(mapping)
        assert result is not None
        # Two policies each contributing 95B static → but final_deficit_effect is summed
        assert mock_scorer.score_policy.call_count == 2
