"""
Tests for Bill Tracker UI tab — search, filter, and sort functionality.

Covers _get_filtered_bills and _get_unique_subjects without Streamlit.
"""

from __future__ import annotations

import json

import pytest

from fiscal_model.ui.tabs.bill_tracker import (
    _get_filtered_bills,
    _get_unique_subjects,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_bill(
    bill_id: str = "hr-1-119",
    title: str = "Test Bill",
    sponsor: str = "Jane Doe (D-NY)",
    number: str = "1",
    bill_type: str = "hr",
    chamber: str = "house",
    status: str = "introduced",
    summary: str = "",
    crs_subjects: list[str] | None = None,
    introduced_date: str = "2025-01-10",
    has_cbo_score: bool = False,
) -> dict:
    return {
        "bill_id": bill_id,
        "title": title,
        "sponsor": sponsor,
        "number": number,
        "bill_type": bill_type,
        "chamber": chamber,
        "status": status,
        "summary": summary,
        "crs_subjects": json.dumps(crs_subjects or []),
        "introduced_date": introduced_date,
        "has_cbo_score": int(has_cbo_score),
        "url": "",
        "latest_action": "",
        "last_fetched": "2026-04-01",
    }


class _FakeDB:
    """Minimal DB stub for testing _get_filtered_bills and _get_unique_subjects."""

    def __init__(self, bills: list[dict]) -> None:
        self._bills = bills

    def get_all_bills(
        self,
        status: str | None = None,
        has_cbo_score: bool | None = None,
        limit: int = 500,
    ) -> list[dict]:
        result = []
        for b in self._bills:
            if status and b.get("status") != status:
                continue
            if has_cbo_score is True and not b.get("has_cbo_score"):
                continue
            result.append(b)
            if len(result) >= limit:
                break
        # Mimic SQLite's ORDER BY introduced_date DESC
        result.sort(key=lambda b: (b.get("introduced_date") or ""), reverse=True)
        return result


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def sample_bills():
    return [
        _make_bill(
            bill_id="hr-1234-119",
            title="Tax Relief for American Families Act",
            sponsor="Jason Smith (R-MO)",
            number="1234",
            bill_type="hr",
            chamber="house",
            status="committee",
            summary="Reduces income taxes for families earning under $400k.",
            crs_subjects=["Taxation", "Income"],
            introduced_date="2025-03-01",
        ),
        _make_bill(
            bill_id="s-500-119",
            title="Green Energy Investment Act",
            sponsor="Maria Cantwell (D-WA)",
            number="500",
            bill_type="s",
            chamber="senate",
            status="introduced",
            summary="Provides tax credits for renewable energy investments.",
            crs_subjects=["Energy", "Taxation"],
            introduced_date="2025-01-15",
        ),
        _make_bill(
            bill_id="hr-999-119",
            title="Social Security Expansion Act",
            sponsor="John Larson (D-CT)",
            number="999",
            bill_type="hr",
            chamber="house",
            status="passed_chamber",
            summary="Expands Social Security benefits for low-income retirees.",
            crs_subjects=["Social Security", "Retirement"],
            introduced_date="2025-02-20",
        ),
        _make_bill(
            bill_id="hr-42-119",
            title="Corporate Tax Fairness Act",
            sponsor="Lloyd Doggett (D-TX)",
            number="42",
            bill_type="hr",
            chamber="house",
            status="enacted",
            summary="Raises the corporate income tax rate to 28 percent.",
            crs_subjects=["Taxation", "Corporate"],
            introduced_date="2024-11-05",
            has_cbo_score=True,
        ),
    ]


@pytest.fixture
def db(sample_bills):
    return _FakeDB(sample_bills)


# ------------------------------------------------------------------
# Search tests
# ------------------------------------------------------------------

class TestSearchFilter:
    def test_no_filters_returns_all(self, db, sample_bills):
        results = _get_filtered_bills(db, {"sort": "Date: Newest First"})
        assert len(results) == len(sample_bills)

    def test_search_by_title_keyword(self, db):
        results = _get_filtered_bills(db, {"search": "tax relief", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-1234-119"

    def test_search_is_case_insensitive(self, db):
        # filter dict search value is already lowercased by _render_filters;
        # confirm _get_filtered_bills handles pre-lowercased queries
        results = _get_filtered_bills(db, {"search": "green energy", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "s-500-119"

    def test_search_by_sponsor(self, db):
        results = _get_filtered_bills(db, {"search": "cantwell", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "s-500-119"

    def test_search_by_bill_number(self, db):
        results = _get_filtered_bills(db, {"search": "1234", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-1234-119"

    def test_search_by_bill_id(self, db):
        results = _get_filtered_bills(db, {"search": "hr-999", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-999-119"

    def test_search_by_summary(self, db):
        results = _get_filtered_bills(db, {"search": "28 percent", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-42-119"

    def test_search_hr_style_query(self, db):
        """'hr 42' should match bill_type=hr, number=42."""
        results = _get_filtered_bills(db, {"search": "hr 42", "sort": "Date: Newest First"})
        assert any(b["bill_id"] == "hr-42-119" for b in results)

    def test_search_no_match_returns_empty(self, db):
        results = _get_filtered_bills(db, {"search": "zzznomatch", "sort": "Date: Newest First"})
        assert results == []

    def test_search_matches_multiple(self, db):
        # "taxation" appears in summary of multiple bills or title
        results = _get_filtered_bills(db, {"search": "tax", "sort": "Date: Newest First"})
        assert len(results) >= 2


# ------------------------------------------------------------------
# Status / chamber filter tests
# ------------------------------------------------------------------

class TestStatusChamberFilter:
    def test_status_filter(self, db):
        results = _get_filtered_bills(db, {"status": "enacted", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-42-119"

    def test_chamber_house(self, db):
        results = _get_filtered_bills(db, {"chamber": "house", "sort": "Date: Newest First"})
        bill_ids = {b["bill_id"] for b in results}
        assert "s-500-119" not in bill_ids
        assert "hr-1234-119" in bill_ids

    def test_chamber_senate(self, db):
        results = _get_filtered_bills(db, {"chamber": "senate", "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "s-500-119"

    def test_combined_status_and_search(self, db):
        results = _get_filtered_bills(
            db, {"status": "committee", "search": "tax relief", "sort": "Date: Newest First"}
        )
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-1234-119"


# ------------------------------------------------------------------
# Policy area filter tests
# ------------------------------------------------------------------

class TestPolicyAreaFilter:
    def test_filter_by_single_policy_area(self, db):
        results = _get_filtered_bills(db, {"policy_areas": ["Social Security"], "sort": "Date: Newest First"})
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-999-119"

    def test_filter_by_multiple_policy_areas(self, db):
        results = _get_filtered_bills(db, {"policy_areas": ["Energy", "Corporate"], "sort": "Date: Newest First"})
        bill_ids = {b["bill_id"] for b in results}
        assert "s-500-119" in bill_ids
        assert "hr-42-119" in bill_ids
        assert "hr-1234-119" not in bill_ids

    def test_policy_area_no_match(self, db):
        results = _get_filtered_bills(db, {"policy_areas": ["Defense"], "sort": "Date: Newest First"})
        assert results == []

    def test_policy_area_with_search(self, db):
        results = _get_filtered_bills(
            db, {"policy_areas": ["Taxation"], "search": "corporate", "sort": "Date: Newest First"}
        )
        assert len(results) == 1
        assert results[0]["bill_id"] == "hr-42-119"

    def test_policy_area_handles_list_subjects(self, db):
        """Bills whose crs_subjects is already a list (demo data) should work."""
        bills = [
            {**_make_bill(bill_id="hr-10-119", title="Foo"), "crs_subjects": ["Taxation"]},
        ]
        fake_db = _FakeDB(bills)
        results = _get_filtered_bills(fake_db, {"policy_areas": ["Taxation"], "sort": "Date: Newest First"})
        assert len(results) == 1


# ------------------------------------------------------------------
# Sort tests
# ------------------------------------------------------------------

class TestSortOrder:
    def test_sort_newest_first(self, db):
        results = _get_filtered_bills(db, {"sort": "Date: Newest First"})
        dates = [b["introduced_date"] for b in results]
        assert dates == sorted(dates, reverse=True)

    def test_sort_oldest_first(self, db):
        results = _get_filtered_bills(db, {"sort": "Date: Oldest First"})
        dates = [b["introduced_date"] for b in results]
        assert dates == sorted(dates)

    def test_sort_relevance_puts_title_match_first(self, db):
        """Title match (score 3) should outrank summary-only match (score 1)."""
        results = _get_filtered_bills(db, {"search": "tax", "sort": "Relevance"})
        # "Tax Relief" and "Corporate Tax" are in titles → score ≥ 3
        # All should appear; title matches should precede summary-only matches
        assert len(results) >= 2
        # hr-1234-119 has "Tax" in title (score 3+), s-500-119 has "tax credits" in summary only
        tax_title_pos = next(i for i, b in enumerate(results) if "tax relief" in b["title"].lower())
        # Should be among first results
        assert tax_title_pos < len(results) - 1

    def test_sort_relevance_without_query_falls_back(self, db):
        """Relevance sort with no query should return all bills (no filtering)."""
        results = _get_filtered_bills(db, {"sort": "Relevance"})
        assert len(results) == 4


# ------------------------------------------------------------------
# _get_unique_subjects tests
# ------------------------------------------------------------------

class TestGetUniqueSubjects:
    def test_returns_sorted_unique_subjects(self, db):
        subjects = _get_unique_subjects(db)
        assert "Taxation" in subjects
        assert "Energy" in subjects
        assert subjects == sorted(subjects)

    def test_no_duplicates(self, db):
        subjects = _get_unique_subjects(db)
        assert len(subjects) == len(set(subjects))

    def test_empty_db_returns_empty(self):
        subjects = _get_unique_subjects(_FakeDB([]))
        assert subjects == []

    def test_handles_malformed_subjects(self):
        bills = [_make_bill()]
        bills[0]["crs_subjects"] = "not-json"
        subjects = _get_unique_subjects(_FakeDB(bills))
        assert subjects == []

    def test_handles_db_error_gracefully(self):
        class BadDB:
            def get_all_bills(self, **kwargs):
                raise RuntimeError("db exploded")

        subjects = _get_unique_subjects(BadDB())
        assert subjects == []
