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
    _CBO_JAN_2025_BASE_LEVELS,
    _VINTAGE_CORPORATE_BASE_LEVELS,
    CORPORATE_RECEIPTS_SOURCING,
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
    """The grade is per line, and it is computed rather than declared.

    One string per vintage could not say "economic path transcribed, budget
    levels reconstructed", which is February 2024's exact state -- so it said
    ``"sourced"`` for a vintage whose real GDP growth was 0.60pp from CBO's own
    table. Two fields, each derived from what the transcription contains.
    """
    grade = VINTAGE_SOURCING[vintage]
    assert set(grade) == {"economic", "budget"}
    assert set(grade.values()) <= {"transcribed", "reconstructed"}
    assert VINTAGE_SOURCE_DOCUMENT[vintage]


def test_jan_2025_is_transcribed_not_interpolated():
    """The Phase D deliverable, now on CBO's own machine-readable table.

    If either half flips back to ``reconstructed``, every claim that a
    P.L. 119-21 benchmark was scored on its own published baseline becomes
    false.
    """
    grade = VINTAGE_SOURCING[BaselineVintage.CBO_JAN_2025]
    assert grade == {"economic": "transcribed", "budget": "transcribed"}
    assert (
        _baseline(BaselineVintage.CBO_JAN_2025).baseline_vintage_sourcing
        == "transcribed"
    )
    assert "61172" in VINTAGE_SOURCE_DOCUMENT[BaselineVintage.CBO_JAN_2025]


def test_feb_2024_cannot_claim_a_budget_table_it_does_not_have():
    """CBO's GitHub publishes no February 2024 ten-year budget table.

    ``ten_year_budget`` carries 2024-06, 2025-01 and 2026-02, and June 2024 is
    publication 60039 -- a different document, whose FY2025 deficit is
    $1,937.9B against the January 2025 edition's $1,865.3B for the same year.
    The one-word grade must therefore be ``partial``, never ``transcribed``.
    """
    b = _baseline(BaselineVintage.CBO_FEB_2024)
    assert b.vintage_sourcing_detail == {
        "economic": "transcribed",
        "budget": "reconstructed",
    }
    assert b.baseline_vintage_sourcing == "partial"
    assert "budget" not in b.vintage_provenance
    assert b.vintage_provenance["economic"]["sha256"]


def test_metadata_exposes_sourcing_and_citation():
    meta = _baseline(BaselineVintage.CBO_JAN_2025).metadata
    assert meta["vintage_sourcing"] == "transcribed"
    assert meta["vintage_sourcing_detail"]["budget"] == "transcribed"
    provenance = meta["vintage_provenance"]["budget"]
    assert provenance["repository"].endswith("US-CBO/cbo-data")
    assert len(provenance["commit_sha"]) == 40
    assert len(provenance["sha256"]) == 64
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
    """The fallback is the midpoint of the two HAND-ENTERED blocks.

    ``interpolated_jan_2025_assumptions`` averages ``_CBO_FEB_2024_ASSUMPTIONS``
    and ``_CBO_FEB_2026_ASSUMPTIONS`` directly, and since R1
    ``vintage_assumptions`` returns CBO's own transcribed series instead of
    those literals -- so the two are no longer the same thing, and this test
    compares the fallback against what it is actually built from.
    """
    from fiscal_model.baseline import _HAND_ENTERED_ASSUMPTIONS

    fallback = interpolated_jan_2025_assumptions()
    feb_2024 = _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2024]
    feb_2026 = _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2026]
    for key, series in fallback.items():
        assert np.allclose(series, (feb_2024[key] + feb_2026[key]) / 2.0)


def test_transcribed_assumptions_replaced_the_hand_entered_ones():
    """And the two are not close on two of the three vintages.

    If they were, the transcription would be decoration. Measured maxima over
    the ten-year window: February 2024's real GDP growth is out by 0.60pp and
    its labour force participation by 1.05pp; February 2026's ten-year note
    FALLS 4.5% to 3.9% where CBO's own table RISES 4.10% to 4.38%. January
    2025's residual is at most 0.11pp, which is the calendar/fiscal basis.
    """
    from fiscal_model.baseline import _HAND_ENTERED_ASSUMPTIONS

    worst = {}
    for vintage in BaselineVintage:
        live = vintage_assumptions(vintage)
        hand = _HAND_ENTERED_ASSUMPTIONS[vintage]
        worst[vintage] = max(
            float(np.max(np.abs(np.asarray(live[key]) - np.asarray(hand[key]))))
            for key in hand
        )

    assert worst[BaselineVintage.CBO_FEB_2024] > 0.005
    assert worst[BaselineVintage.CBO_FEB_2026] > 0.005
    assert worst[BaselineVintage.CBO_JAN_2025] < 0.002

    # The February 2026 ten-year note runs the wrong way in the literals.
    hand_rate = np.asarray(
        _HAND_ENTERED_ASSUMPTIONS[BaselineVintage.CBO_FEB_2026]["interest_rate_10yr"]
    )
    live_rate = np.asarray(
        vintage_assumptions(BaselineVintage.CBO_FEB_2026)["interest_rate_10yr"]
    )
    assert hand_rate[-1] < hand_rate[0]
    assert live_rate[-1] > live_rate[0]


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
    # ``base_gdp`` is now CBO's own level for ``start_year - 1`` -- FY2024 here,
    # since ``_baseline`` opens on 2025 and ``_project_gdp`` compounds the
    # first window year off it. The FY2025 figure this line used to assert,
    # 30,136.0, is what CBO's own economic table returns for FY2025, and
    # ``test_jan_2025_projection_lands_near_cbos_own_deficit`` still pins it.
    assert b.base_gdp == pytest.approx(28_823.0)
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


# ── The corporate receipts line ────────────────────────────────────────────
#
# ``planning/MODELING_IMPROVEMENT.md`` §6.2 item 30: the corporate line used to
# be a vintage-free level (18% of the latest IRS SOI individual-tax aggregate)
# grown by a GDP-plus-1pp rule, so under ``use_real_data=True`` - the app's own
# default - all three vintages started from $386.62B to the cent and grew at
# 4.80-4.88%/yr against CBO's own published 1.21%. Both halves are pinned here.


@pytest.mark.parametrize("vintage", list(BaselineVintage))
def test_every_vintage_declares_how_its_corporate_line_was_obtained(vintage):
    assert CORPORATE_RECEIPTS_SOURCING[vintage] in {
        "published_path",
        "published_base_level",
        "vintage_estimate",
    }


@pytest.mark.parametrize("use_real_data", [True, False])
def test_three_vintages_give_three_corporate_paths(use_real_data):
    """The defect this replaces: one base level and one path for every vintage.

    Both data modes, because the override that caused it lived in the real-data
    loader and the symptom was that the two modes disagreed with each other.
    """
    paths = {}
    for vintage in BaselineVintage:
        baseline = CBOBaseline(
            start_year=2025, use_real_data=use_real_data, vintage=vintage
        )
        paths[vintage] = baseline.generate().corporate_income_tax

    bases = {v: round(float(p[0]), 4) for v, p in paths.items()}
    assert len(set(bases.values())) == len(BaselineVintage), bases
    ends = {v: round(float(p[-1]), 4) for v, p in paths.items()}
    assert len(set(ends.values())) == len(BaselineVintage), ends


@pytest.mark.parametrize("use_real_data", [True, False])
def test_feb_2024_corporate_path_is_cbos_transcribed_table(use_real_data):
    """February 2024 *is* CBO publication 59710 Table 1-1, not a growth rule.

    Scored on the FY2025-2034 window the table covers, so nothing here is an
    extrapolation. The sum is 5,093.9 against the 5,094.0 CBO prints as its own
    total - a tenth of a billion of CBO's rounding, the artefact
    ``tests/test_corporate_derived.py`` already documents.
    """
    published = [
        494.1, 491.4, 484.1, 490.7, 500.9,
        510.6, 518.7, 519.2, 533.4, 550.8,
    ]
    projection = CBOBaseline(
        start_year=2025,
        use_real_data=use_real_data,
        vintage=BaselineVintage.CBO_FEB_2024,
    ).generate()
    assert projection.corporate_income_tax == pytest.approx(published, abs=1e-9)
    assert float(projection.corporate_income_tax.sum()) == pytest.approx(5093.9, abs=0.05)


def test_feb_2024_corporate_growth_is_cbos_not_the_rules():
    """1.21%/yr over CBO's own window, not the rule's 4.88%."""
    path = CBOBaseline(
        start_year=2025,
        use_real_data=True,
        vintage=BaselineVintage.CBO_FEB_2024,
    ).generate().corporate_income_tax
    cagr = (float(path[-1]) / float(path[0])) ** (1 / 9) - 1
    assert cagr == pytest.approx(0.0121, abs=0.0005)
    # And it *falls* in FY2026 and FY2027, which no compounding rule can do.
    assert path[1] < path[0]
    assert path[2] < path[1]


def test_app_window_extrapolates_the_last_year_at_the_tables_own_rate():
    """FY2035 is outside CBO's FY2025-2034 block; the loader's rule supplies it.

    The app's window is FY2026-FY2035, so this is the one year of the shipped
    corporate line that is an extrapolation rather than a transcription.
    """
    path = CBOBaseline(
        start_year=2026,
        use_real_data=True,
        vintage=BaselineVintage.CBO_FEB_2024,
    ).generate().corporate_income_tax
    assert float(path[0]) == pytest.approx(491.4)
    assert float(path[-1]) == pytest.approx(550.8 * (550.8 / 533.4), abs=0.01)


@pytest.mark.parametrize("vintage", list(BaselineVintage))
def test_both_data_paths_agree_about_the_corporate_base(vintage):
    """The real-data loader must not override the vintage's own figure.

    Before this, ``use_real_data=True`` and ``False`` disagreed by 8.6% on
    February 2026 and 35.5% on January 2025, and the mode with "real data" in
    its name was the one with no vintage in it.
    """
    real = CBOBaseline(start_year=2025, use_real_data=True, vintage=vintage)
    fallback = CBOBaseline(start_year=2025, use_real_data=False, vintage=vintage)
    assert real.baseline_data_source == "real_data"
    assert real.base_corporate_tax == pytest.approx(fallback.base_corporate_tax)
    assert real.generate().corporate_income_tax == pytest.approx(
        fallback.generate().corporate_income_tax
    )


def test_jan_2025_corporate_base_matches_its_own_transcribed_table():
    """One map, and it must agree with the Table B-1 transcription beside it."""
    assert _VINTAGE_CORPORATE_BASE_LEVELS[
        BaselineVintage.CBO_JAN_2025
    ] == pytest.approx(_CBO_JAN_2025_BASE_LEVELS["base_corporate_tax"])


def test_metadata_reports_the_corporate_sourcing_grade():
    """A report must be able to tell CBO's path from this module's estimate."""
    for vintage, expected in CORPORATE_RECEIPTS_SOURCING.items():
        meta = CBOBaseline(
            start_year=2025, use_real_data=False, vintage=vintage
        ).metadata
        assert meta["corporate_receipts_sourcing"] == expected
