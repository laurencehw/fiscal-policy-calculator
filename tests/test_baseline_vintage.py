"""
Baseline vintages must be sourced, not manufactured.

Phase D of ``planning/VALIDATION_EXPANSION.md`` §4 turned ``CBO_JAN_2025`` from a
0.5/0.5 interpolation between the February 2024 and February 2026 assumption
sets into a transcription of CBO's own January 2025 tables. That matters because
the P.L. 119-21 benchmarks are published against the January 2025 baseline, and
"scored on the January 2025 baseline" is only an honest sentence when the
vintage's numbers actually came from that report.

These tests pin the distinction so it cannot silently regress: the sourcing
label, the fact that the sourced assumptions differ from the interpolation that
preceded them, and a handful of transcribed levels against the published table.
"""

import numpy as np
import pytest

from fiscal_model.baseline import (
    VINTAGE_SOURCE_DOCUMENT,
    VINTAGE_SOURCING,
    BaselineVintage,
    CBOBaseline,
    interpolated_jan_2025_assumptions,
    vintage_assumptions,
)


def _baseline(vintage: BaselineVintage) -> CBOBaseline:
    return CBOBaseline(start_year=2025, use_real_data=False, vintage=vintage)


# ── The sourcing label ─────────────────────────────────────────────────────


@pytest.mark.parametrize("vintage", list(BaselineVintage))
def test_every_vintage_declares_its_sourcing(vintage):
    assert VINTAGE_SOURCING[vintage] in {"sourced", "interpolated"}
    assert VINTAGE_SOURCE_DOCUMENT[vintage]


def test_jan_2025_is_sourced_not_interpolated():
    """The Phase D deliverable in one assertion.

    If this flips back to ``interpolated``, every claim that a P.L. 119-21
    benchmark was scored on its own published baseline becomes false.
    """
    assert VINTAGE_SOURCING[BaselineVintage.CBO_JAN_2025] == "sourced"
    assert _baseline(BaselineVintage.CBO_JAN_2025).baseline_vintage_sourcing == "sourced"
    assert "61172" in VINTAGE_SOURCE_DOCUMENT[BaselineVintage.CBO_JAN_2025]


def test_metadata_exposes_sourcing_and_citation():
    meta = _baseline(BaselineVintage.CBO_JAN_2025).metadata
    assert meta["vintage_sourcing"] == "sourced"
    assert "January 2025" in meta["vintage_source_document"]


# ── The sourced figures are not the old interpolation ──────────────────────


def test_sourced_jan_2025_assumptions_differ_from_the_interpolation():
    sourced = vintage_assumptions(BaselineVintage.CBO_JAN_2025)
    interpolated = interpolated_jan_2025_assumptions()
    assert set(sourced) == set(interpolated)
    # At least one series must differ materially, or nothing was actually
    # sourced and the label above is decoration.
    assert any(
        not np.allclose(sourced[key], interpolated[key], atol=1e-4)
        for key in sourced
    )


def test_interpolation_is_still_available_as_a_documented_fallback():
    fallback = interpolated_jan_2025_assumptions()
    feb_2024 = vintage_assumptions(BaselineVintage.CBO_FEB_2024)
    feb_2026 = vintage_assumptions(BaselineVintage.CBO_FEB_2026)
    for key, series in fallback.items():
        assert np.allclose(series, (feb_2024[key] + feb_2026[key]) / 2.0)


def test_unknown_vintage_is_rejected():
    with pytest.raises(ValueError):
        vintage_assumptions("not-a-vintage")


# ── Transcribed levels match CBO's published table ─────────────────────────


def test_jan_2025_base_levels_match_cbo_table_b1():
    """Spot-check the transcription against CBO's January 2025 Table B-1.

    Values are FY2025 in billions: individual income taxes 2,621; payroll taxes
    1,759; corporate income taxes 524; other 259; GDP 30,136; debt held by the
    public 30,103.
    """
    b = _baseline(BaselineVintage.CBO_JAN_2025)
    assert b.base_individual_income_tax == pytest.approx(2621.0)
    assert b.base_payroll_tax == pytest.approx(1759.0)
    assert b.base_corporate_tax == pytest.approx(524.0)
    assert b.base_other_revenue == pytest.approx(259.0)
    assert b.base_gdp == pytest.approx(30136.0)
    assert b.base_debt == pytest.approx(30103.0)
    # Revenue components sum to CBO's stated FY2025 total of $5,163B.
    total = (
        b.base_individual_income_tax
        + b.base_payroll_tax
        + b.base_corporate_tax
        + b.base_other_revenue
    )
    assert total == pytest.approx(5163.0, abs=1.0)


def test_jan_2025_mandatory_split_sums_to_the_published_total():
    """Table B-1 puts FY2025 mandatory outlays at $4,228B.

    The model's four mandatory categories are net of the offsetting receipts in
    Table B-4, so they must still add back to that total.
    """
    b = _baseline(BaselineVintage.CBO_JAN_2025)
    mandatory = (
        b.base_social_security
        + b.base_medicare
        + b.base_medicaid
        + b.base_other_mandatory
    )
    assert mandatory == pytest.approx(4228.0, abs=1.0)


def test_jan_2025_discretionary_split_sums_to_the_published_total():
    """Table B-1 puts FY2025 discretionary outlays at $1,847.9B.

    CBO's abbreviated January 2025 report publishes no defense/nondefense split
    of discretionary *outlays*, so the split is derived from the Table B-5
    budget-authority shares. It must still reconstruct the published total.
    """
    b = _baseline(BaselineVintage.CBO_JAN_2025)
    assert b.base_defense + b.base_nondefense == pytest.approx(1847.9, abs=1.0)


def test_jan_2025_projection_lands_near_cbos_own_deficit():
    """End-to-end sanity: the generated path should look like CBO's.

    The projector applies one year of growth to the base levels, so year 0 sits
    between CBO's 2025 and 2026 columns. The resulting first-year deficit should
    still be within a few percent of CBO's $1,865B for FY2025 - if it is not,
    the transcription or the category mapping is wrong.
    """
    projection = _baseline(BaselineVintage.CBO_JAN_2025).generate()
    assert projection.deficit[0] == pytest.approx(1865.0, rel=0.05)
    assert projection.nominal_gdp[0] == pytest.approx(30136.0, rel=0.06)


def test_vintages_are_distinguishable():
    """Three vintages must produce three different paths."""
    deficits = {
        v: _baseline(v).generate().deficit[0] for v in BaselineVintage
    }
    assert len(set(round(d, 3) for d in deficits.values())) == len(BaselineVintage)
