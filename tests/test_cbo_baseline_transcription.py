"""R1's gate: CBO's own tables, read back out of the transcription.

The lane's falsification conditions live here
(``planning/lanes/R1_baseline_transcription.md`` section 4). The load-bearing
one is the first: if the February 2026 vintage's FY2026-2035 deficits do not
sum to the figure CBO's own document prints, nothing else in the lane is worth
reading.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from fiscal_model import cbo_baseline_data as cbo_data
from fiscal_model.baseline import (
    CORPORATE_RECEIPTS_SOURCING,
    VINTAGE_SOURCING,
    BaselineVintage,
    CBOBaseline,
    cbo_baseline_budget,
    vintage_assumptions,
)

#: CBO's own printed FY2026-2035 total, February 2026 edition. The sum of
#: ``proj_deficit_total`` over those ten fiscal years in
#: ``cbo-data/data/budget/ten_year_budget/annual_fy_2026-02.csv``.
CBO_FEB_2026_TEN_YEAR_DEFICIT = 23_143.3

#: What the reconstruction returned for the same window before this lane, and
#: the reason R1 outranked every score-ranked item in the plan: it is the
#: number on the landing page, in Build's target strip and in Ask's
#: ``get_cbo_baseline``.
RECONSTRUCTED_TEN_YEAR_DEFICIT = 29_529.1


# ── The headline ───────────────────────────────────────────────────────────


def test_feb_2026_reproduces_cbos_own_ten_year_deficit():
    """Section 4 falsification 1. Everything else is downstream of this."""
    projection = CBOBaseline(
        start_year=2026, vintage=BaselineVintage.CBO_FEB_2026, use_real_data=True
    ).generate()
    total = float(projection.deficit.sum())
    assert total == pytest.approx(CBO_FEB_2026_TEN_YEAR_DEFICIT, abs=0.05)
    # And it is a long way from what it replaced, or the lane did nothing.
    assert abs(total - RECONSTRUCTED_TEN_YEAR_DEFICIT) > 6_000.0


def test_both_loader_paths_agree_for_a_transcribed_vintage():
    """``use_real_data`` must not change a vintage CBO publishes in full.

    Before PR #130 the two paths disagreed by 8.6% and 35.5% on the corporate
    line alone. Where CBO publishes the whole budget table they must now agree
    to the cent, on every category.
    """
    real = CBOBaseline(start_year=2026, use_real_data=True).generate()
    fallback = CBOBaseline(start_year=2026, use_real_data=False).generate()
    for field in (
        "individual_income_tax", "corporate_income_tax", "payroll_taxes",
        "other_revenues", "social_security", "medicare", "medicaid",
        "other_mandatory", "defense_discretionary", "nondefense_discretionary",
        "net_interest", "debt_held_by_public", "nominal_gdp",
    ):
        assert np.allclose(getattr(real, field), getattr(fallback, field)), field


@pytest.mark.parametrize(
    ("vintage", "start_year"),
    [
        (BaselineVintage.CBO_JAN_2025, 2025),
        (BaselineVintage.CBO_JAN_2025, 2026),
        (BaselineVintage.CBO_FEB_2026, 2026),
    ],
)
def test_the_generated_deficit_is_cbos_own_line(vintage, start_year):
    """Not just the total: each year's deficit is CBO's ``proj_deficit_total``.

    ``other_mandatory`` is a residual against CBO's outlay total, so this is
    the check that the residual is doing what it claims and not absorbing a
    mapping error somewhere else.
    """
    budget = cbo_baseline_budget(vintage)
    assert budget is not None
    published = budget["deficit_total"]
    projection = CBOBaseline(
        start_year=start_year, vintage=vintage, use_real_data=True
    ).generate()
    for offset, year in enumerate(range(start_year, start_year + 10)):
        if year not in published:
            continue
        assert projection.deficit[offset] == pytest.approx(-published[year], abs=0.05)


def test_the_other_mandatory_residual_is_never_negative():
    """A negative residual would mean a gross line was read for a net one."""
    for vintage in BaselineVintage:
        if cbo_baseline_budget(vintage) is None:
            continue
        projection = CBOBaseline(
            start_year=2026, vintage=vintage, use_real_data=True
        ).generate()
        assert np.all(projection.other_mandatory > 0), vintage


# ── The grade says what was actually transcribed ───────────────────────────


def test_feb_2024_has_an_economic_table_and_no_budget_table():
    """And the grade may not round that up to "sourced".

    ``cbo-data``'s ``ten_year_budget`` carries 2024-06, 2025-01 and 2026-02.
    June 2024 is publication 60039, a different document -- its FY2025 deficit
    is $1,937.9B against the January 2025 edition's $1,865.3B for the same
    year -- so borrowing it would be a false provenance claim.
    """
    assert cbo_data.has_economic_table("cbo_feb_2024") is True
    assert cbo_data.has_budget_table("cbo_feb_2024") is False
    assert cbo_baseline_budget(BaselineVintage.CBO_FEB_2024) is None
    assert VINTAGE_SOURCING[BaselineVintage.CBO_FEB_2024] == {
        "economic": "transcribed",
        "budget": "reconstructed",
    }


def test_the_grade_is_computed_from_the_data_not_declared():
    """Remove a vintage's block and its grade must fall, without an edit."""
    from fiscal_model.baseline import vintage_sourcing

    original = cbo_data.budget_tables
    try:
        cbo_data.budget_tables = lambda: {}
        assert vintage_sourcing(BaselineVintage.CBO_FEB_2026)["budget"] == (
            "reconstructed"
        )
    finally:
        cbo_data.budget_tables = original
    assert vintage_sourcing(BaselineVintage.CBO_FEB_2026)["budget"] == "transcribed"


def test_every_corporate_line_is_now_a_published_path():
    """The grade ``baseline.py`` said may not otherwise be reported as CBO's.

    Two vintages reach it through ``cbo_baseline/`` and February 2024 through
    ``data_files/corporate/cbo_corporate_receipts.csv`` (PR #121's
    transcription of publication 59710 Table 1-1).
    """
    for vintage in BaselineVintage:
        assert CORPORATE_RECEIPTS_SOURCING[vintage] == "published_path"


def test_provenance_names_a_repository_commit_and_digest_per_transcribed_line():
    for vintage in BaselineVintage:
        baseline = CBOBaseline(
            start_year=2026, vintage=vintage, use_real_data=False
        )
        provenance = baseline.vintage_provenance
        assert "economic" in provenance
        for record in provenance.values():
            assert record["repository"].startswith("https://github.com/US-CBO/")
            assert len(record["commit_sha"]) == 40
            assert len(record["sha256"]) == 64
            assert record["fetch_date"]


# ── The transcription is CBO's, byte for byte ──────────────────────────────


def _raw_rows(name: str) -> list[dict[str, str]]:
    path = cbo_data.DATA_DIR / name
    with open(path, encoding="utf-8", newline="") as handle:
        body = [line for line in handle if not line.startswith("#")]
    return list(csv.DictReader(body))


def test_the_csvs_carry_the_cbo_variable_behind_every_row():
    """So a mapping decision is auditable without rerunning the fetch script."""
    for name in ("cbo_budget_baseline.csv", "cbo_economic_baseline.csv"):
        rows = _raw_rows(name)
        assert rows
        assert all(row["cbo_variable"] for row in rows)


def test_the_discretionary_split_sums_to_cbos_own_total():
    """Section 4 falsification 4 -- the check that fired on the first run.

    January 2025 publishes the defence/nondefence split of outlays only in its
    timing-adjusted form, and a timing-adjusted pair does not sum to the
    unadjusted total in a year where 1 October falls on a weekend. The
    transcription therefore takes the split as a share and apportions it onto
    ``proj_outlays_discretionary``.
    """
    for vintage in BaselineVintage:
        budget = cbo_baseline_budget(vintage)
        if budget is None:
            continue
        for year, total in budget["discretionary_total"].items():
            split = (
                budget["defense_discretionary"][year]
                + budget["nondefense_discretionary"][year]
            )
            assert split == pytest.approx(total, abs=0.01), (vintage, year)


def test_revenue_components_sum_to_cbos_published_total():
    """Section 4 falsification 2. Catches a dropped customs column."""
    for vintage in BaselineVintage:
        budget = cbo_baseline_budget(vintage)
        if budget is None:
            continue
        for year, total in budget["revenues_total"].items():
            parts = sum(
                budget.get(name, {}).get(year, 0.0)
                for name in (
                    "individual_income_tax", "corporate_income_tax",
                    "payroll_taxes", "other_revenues_core",
                    "other_revenues_customs",
                )
            )
            assert parts == pytest.approx(total, abs=0.35), (vintage, year)


def test_only_february_2026_splits_customs_out_of_other_revenues():
    """A real difference between editions, and the loader must absorb it."""
    feb_2026 = cbo_baseline_budget(BaselineVintage.CBO_FEB_2026)
    jan_2025 = cbo_baseline_budget(BaselineVintage.CBO_JAN_2025)
    assert "other_revenues_customs" in feb_2026
    assert "other_revenues_customs" not in jan_2025


# ── The assumptions are CBO's, and they are not what they replaced ─────────


def test_the_feb_2026_ten_year_note_rises_where_the_literals_fell():
    """The macro survey's finding 1, asserted rather than recalled.

    The hand-entered block ran 4.5% down to 3.9%; CBO's own February 2026
    fiscal table runs 4.10% up to 4.38%. A baseline whose interest-rate path
    points the wrong way prices debt service the wrong way.
    """
    rates = vintage_assumptions(BaselineVintage.CBO_FEB_2026)["interest_rate_10yr"]
    assert rates[0] == pytest.approx(0.0410, abs=5e-4)
    assert rates[-1] == pytest.approx(0.0438, abs=5e-4)
    assert rates[-1] > rates[0]


def test_a_vintage_without_an_economic_block_falls_back_rather_than_borrowing():
    """The behaviour that keeps a provenance claim honest."""
    from fiscal_model.baseline import _HAND_ENTERED_ASSUMPTIONS

    original = cbo_data.economic_tables
    try:
        cbo_data.economic_tables = lambda: {}
        fallback = vintage_assumptions(BaselineVintage.CBO_FEB_2026)
        hand = _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2026]
        for key, series in hand.items():
            assert np.allclose(fallback[key], series)
    finally:
        cbo_data.economic_tables = original


# ── The index reads published levels rather than extrapolating them ────────


def test_the_index_reads_cbos_own_pre_window_level():
    """The SOI anchor is a tax year several years before the window.

    ``nominal_income_index``'s rule is unchanged; this is the one extension --
    a year CBO publishes is read, not back-extrapolated from the window's first
    growth rate.
    """
    projection = CBOBaseline(
        start_year=2026, vintage=BaselineVintage.CBO_FEB_2026, use_real_data=True
    ).generate()
    published = cbo_data.nominal_gdp_table("cbo_feb_2026")
    assert published is not None
    for year in (2023, 2024, 2025):
        assert projection.nominal_income_index(year) == pytest.approx(
            published[year]
        )


def test_the_projection_factor_moved_and_the_size_is_the_lanes_own():
    """Section 3.1's mechanism, in one assertion.

    CBO's own FY2023 -> FY2025 nominal growth is 10.70% where the hand-entered
    February 2026 block assumed 8.99%, which is why ten Tier 1 rows and eight
    shipped presets moved and why the tier got worse rather than better.
    """
    published = cbo_data.nominal_gdp_table("cbo_feb_2026")
    cbo_growth = published[2025] / published[2023] - 1.0
    assert cbo_growth == pytest.approx(0.1070, abs=5e-4)

    from fiscal_model.baseline import _HAND_ENTERED_ASSUMPTIONS

    hand = _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2026]
    step = 1.0 + float(hand["real_gdp_growth"][0]) + float(hand["inflation"][0])
    assert step ** 2 - 1.0 == pytest.approx(0.0899, abs=5e-4)
