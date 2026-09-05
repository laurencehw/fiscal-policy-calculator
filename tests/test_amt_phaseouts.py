"""
Tests for the AMT module's statutory phase-out — Wave 4 lane 3c.

What these lock down:

- **The statutory table is transcribed faithfully**, and its internal
  arithmetic checks out against the IRS's own printed "Complete Phaseout
  Amount": threshold + exemption / rate must reproduce it, which is what
  confirms the 25% claw-back under TCJA and the 50% one under P.L. 119-21.
- **One indexation rule, no stopped tables.** Every schedule carries forward
  and backward at the rate the published TCJA threshold series implies, and
  the published exemption series implies the same rate.
- **The exemption-equivalent behaves.** It equals the exemption when the
  phase-out cannot bind, rises with the exemption and with the threshold, and
  falls as the claw-back rate rises.
- **`phase_out_threshold_change` is alive.** It was declared and never read, so
  every value of it scored exactly 0.0 — the same dead branch L5 found in the
  exemption leg. Cutting the threshold must now raise revenue and raising it
  must lose revenue.
- **The benchmarks did not move.** Both individual-AMT benchmarks sit exactly
  on a published regime anchor, so the phase-out must leave them alone to the
  cent. That is this lane's central pre-registered claim, and it is a test
  rather than a paragraph.
"""

from __future__ import annotations

import pytest

from fiscal_model.amt import (
    AMT_MODE_DERIVED,
    AMT_MODE_REPORTED,
    AMT_STATUTES,
    LAST_TCJA_STATUTE_YEAR,
    SOI_GRID_YEAR,
    STATUTE_PL119_21,
    STATUTE_PRE_TCJA,
    STATUTE_TCJA,
    AMTPolicy,
    AMTType,
    amt_clawback_per_filer,
    amt_exemption_equivalent,
    amt_statutory_year,
    create_amt_phase_out_threshold_change,
    create_extend_tcja_amt_relief,
    create_pl119_21_amt,
    create_repeal_individual_amt,
    current_law_amt_effective_exemption_mfj,
    current_law_amt_exemption_mfj,
    current_law_amt_statute,
    estimate_amt_revenue,
    load_statutory_amt_parameters,
    statutory_indexation_rate,
)
from fiscal_model.policies import PolicyType

STATUSES = ("single", "mfj", "mfs")


# ---------------------------------------------------------------------------
# The transcribed statute
# ---------------------------------------------------------------------------


def test_every_statute_loads_with_published_rows():
    table = load_statutory_amt_parameters()
    assert set(table) == set(AMT_STATUTES)
    assert set(table[STATUTE_TCJA]) == set(range(2018, 2026))
    assert set(table[STATUTE_PRE_TCJA]) == {2017, 2018}
    assert set(table[STATUTE_PL119_21]) == {2026}
    for statute in AMT_STATUTES:
        for row in table[statute].values():
            assert row.published is True
            assert row.source


@pytest.mark.parametrize(
    ("statute", "year", "status", "printed_complete_phase_out"),
    [
        # Rev. Proc. 2024-40 sec. 3.11, "Complete Phaseout Amount" column.
        (STATUTE_TCJA, 2025, "mfj", 1_800_700),
        (STATUTE_TCJA, 2025, "single", 978_750),
        # Rev. Proc. 2025-32 sec. 3.10 — the rows that pin the 50% rate.
        (STATUTE_PL119_21, 2026, "mfj", 1_280_400),
        (STATUTE_PL119_21, 2026, "single", 680_200),
        (STATUTE_PL119_21, 2026, "mfs", 640_200),
    ],
)
def test_the_clawback_rate_reproduces_the_printed_complete_phaseout(
    statute, year, status, printed_complete_phase_out
):
    """
    The rate is not taken on trust from the statutory text. Each Revenue
    Procedure prints threshold + exemption / rate beside the threshold, so the
    transcription is checkable arithmetic — and it is the check that confirms
    P.L. 119-21 raised the claw-back from 25% to 50%.
    """
    row = amt_statutory_year(statute, year)
    assert row.complete_phase_out_for(status) == pytest.approx(
        printed_complete_phase_out, abs=1.0
    )


def test_pl119_21_tightens_the_phase_out_relative_to_tcja():
    """The reset moved thresholds DOWN and the rate UP. Both directions matter."""
    tcja = amt_statutory_year(STATUTE_TCJA, 2025)
    obbba = amt_statutory_year(STATUTE_PL119_21, 2026)
    assert obbba.threshold_for("mfj") < tcja.threshold_for("mfj")
    assert obbba.phase_out_rate == 0.50
    assert tcja.phase_out_rate == 0.25
    # The exemption itself went up, which is why the provision is a net cost.
    assert obbba.exemption_for("mfj") > tcja.exemption_for("mfj")


def test_pre_tcja_thresholds_are_far_below_tcjas():
    """
    The claw-back is what makes high-income filers AMT payers post-sunset: the
    pre-TCJA threshold sits an order of magnitude lower than TCJA's.
    """
    assert (
        amt_statutory_year(STATUTE_PRE_TCJA, 2018).threshold_for("mfj")
        < amt_statutory_year(STATUTE_TCJA, 2018).threshold_for("mfj") / 5
    )


# ---------------------------------------------------------------------------
# One indexation rule, no stopped tables
# ---------------------------------------------------------------------------


def test_indexation_rate_is_the_published_threshold_series_own_rate():
    rate = statutory_indexation_rate()
    assert rate == pytest.approx((1_252_700 / 1_000_000) ** (1 / 7) - 1, rel=1e-12)
    assert 0.02 < rate < 0.04


def test_the_published_exemption_series_implies_the_same_rate():
    """
    Two independent § 1(f)(3) series over the same years must agree, or the one
    the module picks would be a choice rather than a measurement.
    """
    exemption_rate = (137_000 / 109_400) ** (1 / 7) - 1
    assert exemption_rate == pytest.approx(statutory_indexation_rate(), abs=1e-4)


@pytest.mark.parametrize("statute", AMT_STATUTES)
def test_schedules_index_forward_instead_of_stopping(statute):
    """
    ``AMT_PHASEOUT_TCJA`` used to stop at 2030 and the exemption tables at
    2034. Every schedule now runs as far as it is asked, monotonically.
    """
    rows = load_statutory_amt_parameters()[statute]
    last = max(rows)
    projected = [amt_statutory_year(statute, year) for year in range(last, last + 16)]
    for status in STATUSES:
        thresholds = [row.threshold_for(status) for row in projected]
        exemptions = [row.exemption_for(status) for row in projected]
        assert thresholds == sorted(thresholds)
        assert exemptions == sorted(exemptions)
        assert thresholds[-1] > thresholds[0]
    assert projected[0].published is True
    assert projected[-1].published is False
    assert projected[-1].phase_out_rate == projected[0].phase_out_rate


def test_indexation_rounds_to_the_statutory_hundred():
    row = amt_statutory_year(STATUTE_TCJA, 2035)
    for status in STATUSES:
        assert row.exemption_for(status) % 100 == 0
        assert row.threshold_for(status) % 100 == 0


def test_a_year_before_a_schedule_starts_does_not_read_a_later_row():
    """The half of the old clamp test that is still the right behaviour."""
    early = amt_statutory_year(STATUTE_PL119_21, 2020)
    assert early.threshold_for("mfj") < amt_statutory_year(
        STATUTE_PL119_21, 2026
    ).threshold_for("mfj")


def test_current_law_statute_is_tpcs_baseline_not_enacted_law():
    """
    The derived path's current law is the TCJA sunset, because that is what
    TPC T25-0049 projects and what both benchmarks describe. Enacted P.L.
    119-21 is expressible as a *reform* and deliberately not as the baseline.
    """
    assert current_law_amt_statute(LAST_TCJA_STATUTE_YEAR) == STATUTE_TCJA
    assert current_law_amt_statute(LAST_TCJA_STATUTE_YEAR + 1) == STATUTE_PRE_TCJA
    assert STATUTE_PL119_21 not in {
        current_law_amt_statute(year) for year in range(2018, 2046)
    }


# ---------------------------------------------------------------------------
# The exemption-equivalent
# ---------------------------------------------------------------------------


def test_no_phase_out_leaves_the_exemption_untouched():
    for rate in (0.0, 0.25, 0.5):
        assert amt_exemption_equivalent(120_000, float("inf"), rate, 2026) == 120_000
    assert amt_exemption_equivalent(120_000, 200_000, 0.0, 2026) == 120_000


def test_a_binding_phase_out_lowers_the_effective_exemption():
    plain = amt_exemption_equivalent(120_000, float("inf"), 0.25, 2026)
    clawed = amt_exemption_equivalent(120_000, 200_000, 0.25, 2026)
    assert 0 < clawed < plain


def test_effective_exemption_rises_with_the_threshold():
    values = [
        amt_exemption_equivalent(112_000, threshold, 0.25, 2026)
        for threshold in (150_000, 200_000, 400_000, 1_000_000, 5_000_000)
    ]
    assert values == sorted(values)
    assert values[-1] == pytest.approx(112_000, rel=3e-3)


def test_effective_exemption_rises_with_the_exemption():
    values = [
        amt_exemption_equivalent(exemption, 210_000, 0.25, 2026)
        for exemption in (80_000, 100_000, 120_000, 160_000)
    ]
    assert values == sorted(values)


def test_effective_exemption_falls_as_the_clawback_rate_rises():
    values = [
        amt_exemption_equivalent(140_000, 1_000_000, rate, 2026)
        for rate in (0.10, 0.25, 0.50, 0.75)
    ]
    assert values == sorted(values, reverse=True)


def test_clawback_per_filer_is_bounded_by_the_exemption():
    assert amt_clawback_per_filer(120_000, float("inf"), 0.25, 2026) == 0.0
    realistic = amt_clawback_per_filer(120_000, 210_000, 0.25, 2026)
    assert 0 < realistic < 120_000
    # A threshold at zero with a 100% claw-back is the hardest schedule
    # expressible: every filer loses min(exemption, AMTI). It must still be
    # bounded by the exemption, and it must dominate a realistic schedule.
    hardest = amt_clawback_per_filer(120_000, 0.0, 1.0, 2026)
    assert realistic < hardest < 120_000


def test_the_soi_grid_reproduces_published_bracket_counts_and_means():
    """
    The within-bracket shape is pinned by the bracket's own printed mean, so it
    is a measurement rather than an assumption. If the grid drifts from SOI,
    every effective exemption drifts with it.
    """
    from fiscal_model.amt import _soi_income_grid
    from fiscal_model.data.irs_soi import IRSSOIData

    incomes, weights = _soi_income_grid()
    brackets = [
        b
        for b in IRSSOIData().get_bracket_distribution(SOI_GRID_YEAR)
        if b.agi_floor > 0 and b.num_returns > 0
    ]
    assert weights.sum() == pytest.approx(sum(b.num_returns for b in brackets), rel=1e-9)
    assert float((incomes * weights).sum()) == pytest.approx(
        sum(b.total_agi for b in brackets) * 1e9, rel=0.01
    )


def test_post_sunset_clawback_bites_harder_than_tcjas():
    """
    The substantive claim. Under the sunset the threshold sits low in the
    income distribution, so the claw-back is worth an order of magnitude more
    of the exemption than it is under TCJA's own thresholds.
    """
    sunset = amt_statutory_year(STATUTE_PRE_TCJA, 2026)
    tcja = amt_statutory_year(STATUTE_TCJA, 2026)
    sunset_bite = 1 - amt_exemption_equivalent(
        sunset.exemption_for("mfj"),
        sunset.threshold_for("mfj"),
        sunset.phase_out_rate,
        2026,
    ) / sunset.exemption_for("mfj")
    tcja_bite = 1 - amt_exemption_equivalent(
        tcja.exemption_for("mfj"),
        tcja.threshold_for("mfj"),
        tcja.phase_out_rate,
        2026,
    ) / tcja.exemption_for("mfj")
    assert sunset_bite > 4 * tcja_bite
    assert current_law_amt_effective_exemption_mfj(2026) < current_law_amt_exemption_mfj(
        2026
    )


# ---------------------------------------------------------------------------
# The branch that used to be dead
# ---------------------------------------------------------------------------


def _threshold_policy(change: float) -> AMTPolicy:
    return create_amt_phase_out_threshold_change(change, start_year=2026)


def test_cutting_the_threshold_raises_revenue():
    """`phase_out_threshold_change` returned 0.0 for every value before this."""
    assert _threshold_policy(-100_000).derived_annual_effect(2026) > 0.0


def test_raising_the_threshold_loses_revenue():
    assert _threshold_policy(100_000).derived_annual_effect(2026) < 0.0


def test_threshold_effect_scales_with_the_size_of_the_change():
    effects = [
        _threshold_policy(change).derived_annual_effect(2026)
        for change in (-200_000, -100_000, -50_000, 0, 50_000, 100_000)
    ]
    assert effects == sorted(effects, reverse=True)
    assert effects[3] == pytest.approx(0.0, abs=1e-9)


def test_a_threshold_reform_leaves_the_headline_exemption_alone():
    policy = _threshold_policy(-100_000)
    assert policy.get_exemption_for_year(2026, "mfj") == current_law_amt_exemption_mfj(
        2026
    )
    assert policy.get_effective_exemption_for_year(
        2026, "mfj"
    ) < current_law_amt_effective_exemption_mfj(2026)


def test_a_threshold_reform_moves_the_affected_population():
    baseline = _threshold_policy(0).estimate_affected_taxpayers(2026)
    tightened = _threshold_policy(-200_000).estimate_affected_taxpayers(2026)
    loosened = _threshold_policy(200_000).estimate_affected_taxpayers(2026)
    assert tightened > baseline > loosened


def test_a_higher_clawback_rate_raises_revenue():
    policy = AMTPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        new_phase_out_rate=0.50,
        start_year=2026,
        mode=AMT_MODE_DERIVED,
    )
    assert policy.get_phase_out_rate(2026) == 0.50
    assert policy.derived_annual_effect(2026) > 0.0


def test_an_explicit_mfj_threshold_scales_the_other_statuses():
    policy = AMTPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        new_phase_out_threshold_mfj=500_000,
        start_year=2026,
    )
    assert policy.get_phase_out_threshold_for_year(2026, "mfj") == 500_000
    statutory = amt_statutory_year(STATUTE_PRE_TCJA, 2026)
    ratio = 500_000 / statutory.threshold_for("mfj")
    assert policy.get_phase_out_threshold_for_year(2026, "single") == pytest.approx(
        statutory.threshold_for("single") * ratio
    )


def test_a_threshold_cannot_go_negative():
    policy = _threshold_policy(-10_000_000)
    assert policy.get_phase_out_threshold_for_year(2026, "mfj") == 0.0


# ---------------------------------------------------------------------------
# P.L. 119-21 as a reform — the mechanism measured against a published figure
# ---------------------------------------------------------------------------


def test_pl119_21_costs_less_than_a_naive_tcja_extension():
    """
    The whole point of modelling the phase-out. P.L. 119-21 extends the same
    exemption but claws it back from lower income and twice as fast, so it must
    cost *less* than simply extending TCJA — a difference the module could not
    represent at all before this lane, since both would have scored the
    identical exemption path.
    """
    extension = estimate_amt_revenue(
        create_extend_tcja_amt_relief(start_year=2026, mode=AMT_MODE_DERIVED)
    )["ten_year_static"]
    enacted = estimate_amt_revenue(create_pl119_21_amt(start_year=2026))[
        "ten_year_static"
    ]
    assert extension < enacted < 0
    assert abs(enacted) < abs(extension)


def test_pl119_21_lands_in_the_pre_registered_band_against_jct():
    """
    JCX-35-25 scores the provision at +$1,362.810B over FY2025-2034; the lane
    pre-registered $780B-$880B for the derived path, i.e. -35% to -43%. This is
    **not** a benchmark — `pl119_21_amt_exemption` is scored by ``tcja.py`` and
    nothing here touches it — it is the one published quantity in the repository
    that prices the mechanism this lane adds, so the band is pinned.
    """
    enacted = abs(
        estimate_amt_revenue(create_pl119_21_amt(start_year=2026))["ten_year_static"]
    )
    assert 780.0 <= enacted <= 880.0
    error = (enacted - 1_362.810) / 1_362.810
    assert -0.43 <= error <= -0.35


# ---------------------------------------------------------------------------
# What must not have moved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "kwargs", "expected"),
    [
        (create_extend_tcja_amt_relief, {"start_year": 2026}, 855.33),
        (create_repeal_individual_amt, {"start_year": 2026}, 948.90),
    ],
)
def test_the_derived_benchmarks_did_not_move(factory, kwargs, expected):
    """
    This lane's central pre-registered claim, as a test. Both individual-AMT
    benchmarks sit exactly on a published regime anchor, and each anchor's
    coordinate is computed from that anchor's own statutory triple — so adding a
    phase-out returns the same published row and the same score. A failure here
    is a defect, not a result.
    """
    from fiscal_model.scoring import FiscalPolicyScorer

    policy = factory(mode=AMT_MODE_DERIVED, **kwargs)
    result = FiscalPolicyScorer(
        start_year=policy.start_year, use_real_data=False
    ).score_policy(policy, dynamic=False)
    assert result.total_10_year_cost == pytest.approx(expected, abs=0.05)


def test_reported_mode_still_ignores_every_phase_out_parameter():
    """The app default reads its fitted annual, so no shipped preset moved."""
    policy = create_extend_tcja_amt_relief(start_year=2026, mode=AMT_MODE_REPORTED)
    policy.phase_out_threshold_change = -500_000
    policy.new_phase_out_rate = 0.9
    assert policy.estimate_static_revenue_effect(0.0) == -39.3
