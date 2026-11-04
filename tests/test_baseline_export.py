"""The proposal chart's baseline is CBO's own February 2026 table."""

from __future__ import annotations

from scripts.export_static import baseline_payload


def test_february_2026_deficit_sums_to_cbo():
    payload = baseline_payload()
    assert payload["vintage"] == "cbo_feb_2026"
    assert [row["fiscal_year"] for row in payload["years"]] == list(range(2026, 2036))
    # CBO's sign: a deficit is negative. The printed ten-year total is $23,143.3B.
    total = sum(row["deficit_billions"] for row in payload["years"])
    assert abs(total - (-23143.3)) < 0.05
    assert all(row["nominal_gdp_billions"] > 0 for row in payload["years"])
    assert all(row["debt_held_by_public_billions"] > 0 for row in payload["years"])
