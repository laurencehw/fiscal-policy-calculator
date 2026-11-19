"""Lane B3: the Social Security $250K donut priced from SSA's wage distribution.

Pre-registration: ``planning/lanes/B3_ss_donut_mechanism.md``. These tests pin
what that file predicted and what it said must not move.
"""

from __future__ import annotations

import itertools

import pytest

from fiscal_model import FiscalPolicyScorer
from fiscal_model.payroll import (
    OASDI_EMPLOYER_SHARE,
    PayrollTaxPolicy,
    create_ss_donut_hole,
    donut_covered_wages,
    ssa_net_compensation,
    ssa_wages_above,
    taxable_maximum,
)
from fiscal_model.policies import PolicyType

# ── The data file is SSA's table ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("year", "earners", "aggregate"),
    [
        # The page totals. 2023's rows sum $0.02 below its printed aggregate,
        # rounding in SSA's own cells, which the data file's header records.
        (2023, 173_670_935, 11_103_241_227_338.01),
        (2025, 175_588_374, 12_266_915_421_173.40),
    ],
)
def test_the_transcription_adds_up_to_ssas_own_totals(year, earners, aggregate):
    rows = ssa_net_compensation(year)
    assert len(rows) == 59
    assert sum(r[1] for r in rows) == earners
    assert sum(r[2] for r in rows) == pytest.approx(aggregate, abs=0.05)


def test_2024_is_not_invented():
    with pytest.raises(ValueError, match="2024"):
        ssa_net_compensation(2024)


def test_wages_above_a_table_boundary_is_exact():
    rows = ssa_net_compensation(2025)
    above = [r for r in rows if r[0] >= 250_000.0]
    exact = (sum(r[2] for r in above) - 250_000.0 * sum(r[1] for r in above)) / 1e9
    assert ssa_wages_above(250_000.0) == pytest.approx(exact, rel=1e-12)
    assert ssa_wages_above(250_000.0) == pytest.approx(1_423.86, abs=0.01)


def test_the_tail_falls_monotonically_through_brackets_and_the_open_top():
    points = [180_000, 250_000, 333_333, 1_000_000, 49_000_000, 50_000_000, 80_000_000]
    values = [ssa_wages_above(t) for t in points]
    assert all(a > b > 0 for a, b in itertools.pairwise(values))


def test_the_backtest_the_lane_reported():
    """Uniform scaling of 2023 to 2025 understates the actual tail by 8.0%."""
    awi = 69_861.77 / 63_932.64
    earners = 175_588_374 / 173_670_935
    predicted = earners * awi * ssa_wages_above(250_000.0 / awi, 2023)
    gap = predicted / ssa_wages_above(250_000.0, 2025) - 1.0
    assert gap == pytest.approx(-0.080, abs=0.001)


# ── The year path ────────────────────────────────────────────────────────


def test_the_anchor_year_reads_the_table_unscaled():
    assert donut_covered_wages(2025, 250_000.0, "cbo_feb_2024") == pytest.approx(
        ssa_wages_above(250_000.0), rel=1e-12
    )


def test_a_closed_donut_taxes_wages_above_the_cap():
    """Once CBO's maximum passes the threshold the two thresholds coincide."""
    year = 2035
    cap = taxable_maximum(year, "cbo_feb_2026")
    assert cap > 250_000.0
    assert donut_covered_wages(year, 250_000.0, "cbo_feb_2026") == pytest.approx(
        donut_covered_wages(year, cap, "cbo_feb_2026"), rel=1e-12
    )


def test_the_taxable_maximum_is_cbos_schedule_and_extends_past_it():
    assert taxable_maximum(2025, "cbo_feb_2024") == 176_100.0
    assert taxable_maximum(2034, "cbo_feb_2024") == 242_100.0
    growth = 242_100.0 / taxable_maximum(2033, "cbo_feb_2024")
    assert taxable_maximum(2036, "cbo_feb_2024") == pytest.approx(242_100.0 * growth**2)


# ── The pre-registered figures ───────────────────────────────────────────


def test_the_battery_row_lands_on_its_preregistered_central_and_band():
    from fiscal_model.ui.tabs.results_summary import _DONUT_BATTERY_10YR
    from fiscal_model.validation.specialized_household import validate_payroll_policy

    result = validate_payroll_policy("ss_donut_250k", verbose=False)
    assert result.official_10yr == -1_426.8, "no target is built from the option"
    assert result.model_10yr == pytest.approx(-1_670.5, abs=0.05)
    assert -1_750.0 <= result.model_10yr <= -1_590.0
    # The caption's pin is this figure.
    assert result.model_10yr == pytest.approx(_DONUT_BATTERY_10YR, abs=0.05)


def test_the_donut_is_declared_unfitted():
    from fiscal_model.validation.specialized_household import validate_payroll_policy

    result = validate_payroll_policy("ss_donut_250k", verbose=False)
    assert result.model_parameters["calibrated_to_target"] is False
    for other in ("ss_eliminate_cap", "ss_cap_90_pct", "expand_niit"):
        assert validate_payroll_policy(other, verbose=False).model_parameters[
            "calibrated_to_target"
        ] is True


@pytest.mark.parametrize(
    ("case", "expected"),
    [("ss_eliminate_cap", -3_200.0), ("ss_cap_90_pct", -800.0), ("expand_niit", -250.0)],
)
def test_no_other_payroll_row_moved(case, expected):
    from fiscal_model.validation.specialized_household import validate_payroll_policy

    assert validate_payroll_policy(case, verbose=False).model_10yr == pytest.approx(expected)


def test_the_shipped_preset_on_the_app_window():
    policy = create_ss_donut_hole(start_year=2026)
    result = FiscalPolicyScorer(start_year=2026).score_policy(policy)
    assert result.total_10_year_cost == pytest.approx(-1_794.7, abs=0.05)
    # A path, not a flat annual: it ramps every year.
    path = list(result.final_deficit_effect)
    assert all(a > b for a, b in itertools.pairwise(path))


def test_the_offset_is_the_modules_payroll_rule_at_the_statutory_split():
    policy = create_ss_donut_hole()
    assert policy.employer_share == OASDI_EMPLOYER_SHARE == 0.5
    assert policy.new_earnings_tax_offset_share() == pytest.approx(0.3122, abs=1e-4)
    assert policy.estimate_behavioral_offset(100.0) == pytest.approx(31.22, abs=0.01)
    assert policy.estimate_behavioral_offset(-100.0) == pytest.approx(-31.22, abs=0.01)


def test_a_donut_with_another_component_keeps_the_old_table():
    combined = PayrollTaxPolicy(
        name="donut + rate",
        description="donut and a rate change",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_donut_hole_start=250_000.0,
        ss_rate_change=0.01,
        labor_supply_elasticity=0.0,
        tax_avoidance_elasticity=0.0,
    )
    assert not combined.uses_donut_path()
    assert not combined.uses_covered_earnings_base()


def test_an_explicit_annual_still_wins():
    """Leave-one-out sets an annual on the factory's policy; that leg is unchanged."""
    policy = create_ss_donut_hole()
    policy.annual_revenue_change_billions = 266.4
    assert not policy.uses_donut_path()
    assert policy.estimate_static_revenue_effect(0.0) == 266.4


def test_leave_one_out_derivation_is_unchanged():
    from fiscal_model.validation.loo import derive_payroll_annual

    assert derive_payroll_annual("ss_donut_250k") * 10 == pytest.approx(2_664.0, abs=0.1)


# ── The Social Security page does not move ───────────────────────────────


def test_the_social_security_page_export_is_byte_identical():
    """OCACT's figures are read by the Social Security page, never by payroll.py."""
    import json
    from pathlib import Path

    from scripts.export_static import social_security_payload

    committed = json.loads(
        (Path(__file__).resolve().parents[1] / "site_data" / "social-security.json").read_text(
            encoding="utf-8"
        )
    )
    assert json.loads(json.dumps(social_security_payload(), allow_nan=False)) == committed


# ── Decision 6 caption ───────────────────────────────────────────────────


def test_the_caption_is_computed_from_the_scored_result():
    from fiscal_model.ui.tabs.results_summary import ss_donut_mechanism_caption

    policy = create_ss_donut_hole(start_year=2026)
    result = FiscalPolicyScorer(start_year=2026).score_policy(policy)
    text = ss_donut_mechanism_caption(policy, result)
    assert "until 2026-11-19" in text and "2,700.0B" in text
    assert r"\$1,795B" in text  # the net computed from this run
    assert r"\$2,609B gross" in text
    assert "31.2%" in text
    assert "In 2035" in text  # the donut closes inside the app's window
    assert "17.1% higher" in text


def test_the_caption_is_silent_off_the_donut_path():
    from fiscal_model.payroll import create_ss_eliminate_cap
    from fiscal_model.ui.tabs.results_summary import ss_donut_mechanism_caption

    policy = create_ss_eliminate_cap()
    result = FiscalPolicyScorer(start_year=2025).score_policy(policy)
    assert ss_donut_mechanism_caption(policy, result) == ""
    assert ss_donut_mechanism_caption(object(), result) == ""
