"""Lane H8 — the tariff's GDP-feedback channel, and the two things it moved.

Three claims are under test here, and each of them was a defect before this
lane:

1. **The conventional score carries no retaliation.** Every target in the
   repository's trade block is a conventional estimate, and a conventional
   estimate does not net foreign retaliation — Tax Foundation FF861 prints
   $2,171.1B conventional, $1,721.0B dynamic and $1,443.0B dynamic-with-
   retaliation for the *same* policy. Subtracting retaliation inside the score
   made the model a different object from its own benchmark. What is left is a
   constant ratio, ``0.95 × 0.75 = 0.7125`` of gross duty, in both directions.

2. **The GDP-feedback channel exists and runs through the adapter**, not
   through a reduced form of this module's own, and it is *reported* rather
   than scored.

3. **The reciprocal schedule is a reconstruction of a document.** It is
   checked against sixteen published Annex I rates that the module never reads.
"""

from __future__ import annotations

import csv

import numpy as np
import pytest

from fiscal_model.models import FRBUSAdapterLite, MacroScenario
from fiscal_model.models.macro_adapter import policy_to_scenario
from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.trade import (
    RECIPROCAL_SCHEDULE_PATH,
    TRADE_BASELINE,
    TariffPolicy,
    create_auto_tariff_25,
    create_reciprocal_tariffs,
    create_steel_tariff_25,
    create_trump_china_60,
    create_trump_universal_10,
    load_reciprocal_schedule,
)

PRESETS = (
    create_trump_universal_10,
    create_trump_china_60,
    create_auto_tariff_25,
    create_steel_tariff_25,
    create_reciprocal_tariffs,
)

#: (1 - avoidance) x (1 - income and payroll offset). FF861's own conventional
#: identity implies 0.738 with its 26.2% offset and its noncompliance folded
#: into the base instead of taken as a line.
CONVENTIONAL_RATIO = 0.95 * 0.75


class TestRetaliationIsNotAConventionalChannel:
    @pytest.mark.parametrize("factory", PRESETS, ids=lambda f: f.__name__)
    def test_every_preset_nets_to_the_same_conventional_ratio(self, factory):
        summary = factory().get_trade_summary()
        assert summary["net_to_gross_ratio"] == pytest.approx(
            CONVENTIONAL_RATIO, abs=1e-9
        )

    @pytest.mark.parametrize("factory", PRESETS, ids=lambda f: f.__name__)
    def test_the_retaliation_flag_cannot_touch_the_score(self, factory):
        """The load-bearing test: the flag is a *reporting* switch now.

        Before this lane the same policy scored two different numbers
        depending on ``include_retaliation``, and one of them was compared
        against a conventional target.
        """
        with_retaliation = factory()
        without = factory()
        without.include_retaliation = False
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
        assert scorer.score_policy(with_retaliation).total_10_year_cost == (
            pytest.approx(scorer.score_policy(without).total_10_year_cost, abs=1e-9)
        )

    def test_the_offset_is_avoidance_and_the_income_payroll_offset_only(self):
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        gross = policy.estimate_static_revenue_effect(0)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        offset = (gross - avoidance) * TRADE_BASELINE["income_payroll_offset_rate"]
        assert policy.estimate_behavioral_offset(gross) == pytest.approx(
            avoidance + offset, abs=1e-9
        )

    def test_retaliation_is_still_computed_and_still_reported(self):
        summary = create_trump_universal_10().get_trade_summary()
        assert summary["retaliation_revenue_loss"] > 0
        assert (
            summary["dynamic_with_retaliation_revenue"] < summary["dynamic_revenue"]
        )

    def test_a_cut_still_erodes_rather_than_amplifying(self):
        """PR #119's contract, re-checked with the retaliation term gone."""
        cut = TariffPolicy(
            name="Cut",
            description="Test",
            tariff_rate_change=-0.05,
            import_base_billions=1000.0,
        )
        gross = cut.estimate_static_revenue_effect(0)
        assert gross < 0
        offset = cut.estimate_behavioral_offset(gross)
        assert offset < 0
        # The engine books `-static_revenue + behavioral`, so the scored
        # magnitude is `gross - offset` and an offset carrying the static
        # sign erodes it.
        assert abs(gross - offset) < abs(gross)


class TestGDPFeedbackChannel:
    def test_the_impulse_exceeds_the_receipts_the_tariff_collects(self):
        """The whole point of the channel, in one assertion.

        Households pay ``tau`` on every dollar that still arrives; the Treasury
        collects ``tau/(1+tau)``, less avoidance and the income-and-payroll
        offset. The gap is deadweight plus offset, and a macro model fed the
        receipts figure sees a smaller shock than the tariff imposes.
        """
        policy = create_trump_universal_10()
        summary = policy.get_trade_summary()
        assert summary["macro_demand_impulse"] > summary["gross_tariff_revenue"]
        assert summary["macro_demand_impulse"] > summary["conventional_revenue"] * 1.5

    def test_the_impulse_is_the_gross_duty_grossed_back_up(self):
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        gross = policy.estimate_static_revenue_effect(0)
        assert policy.macro_demand_impulse() == pytest.approx(
            gross * (1 + policy.tariff_rate_change), abs=1e-9
        )

    def test_the_channel_is_the_adapter_and_not_a_local_reduced_form(self):
        """No macro constant lives in ``trade.py``; the adapter owns them all."""
        policy = create_trump_universal_10()
        scenario = MacroScenario(
            name="check",
            description="check",
            start_year=policy.start_year,
            horizon_years=10,
            receipts_change=np.full(10, policy.macro_demand_impulse()),
        )
        expected = -FRBUSAdapterLite().run(scenario).cumulative_revenue_feedback
        assert policy.estimate_gdp_feedback_revenue_loss(10) == pytest.approx(
            expected, abs=1e-6
        )

    def test_the_feedback_is_not_in_the_score(self):
        policy = create_trump_universal_10()
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
        scored = scorer.score_policy(policy).total_10_year_cost
        summary = policy.get_trade_summary()
        assert scored == pytest.approx(-summary["conventional_revenue"] * 10, rel=1e-6)
        assert summary["gdp_feedback_revenue_loss_total"] > 0

    def test_a_cut_gains_receipts_rather_than_losing_them(self):
        cut = TariffPolicy(
            name="Cut",
            description="Test",
            tariff_rate_change=-0.05,
            import_base_billions=1000.0,
        )
        assert cut.macro_demand_impulse() < 0
        assert cut.estimate_gdp_feedback_revenue_loss(10) < 0

    def test_the_dynamic_column_sits_between_the_published_ones(self):
        """FF861's three columns for the 10% universal tariff.

        Conventional $2,171.1B, dynamic $1,721.0B, dynamic-with-retaliation
        $1,443.0B. The module's base carves out USMCA-qualifying goods and
        FF861's does not, so the *levels* are not comparable; the *ordering*
        is, and the drag has to sit between nothing and everything.
        """
        summary = create_trump_universal_10().get_trade_summary()
        assert (
            summary["dynamic_with_retaliation_revenue"]
            < summary["dynamic_revenue"]
            < summary["conventional_revenue"]
        )
        drag_share = (
            summary["conventional_revenue"] - summary["dynamic_revenue"]
        ) / summary["conventional_revenue"]
        # FF861's own drag is 20.7% of its conventional column.
        assert 0.10 < drag_share < 0.30


class TestMacroScenarioHook:
    def test_a_tariff_hands_the_adapter_its_own_impulse(self):
        policy = create_trump_universal_10()
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
        result = scorer.score_policy(policy)
        scenario = policy_to_scenario(policy, result)
        assert scenario.receipts_change[0] == pytest.approx(
            policy.macro_demand_impulse(), abs=1e-9
        )

    @pytest.mark.parametrize(
        "policy",
        [
            SpendingPolicy(
                name="Test spending",
                description="Test",
                policy_type=PolicyType.MANDATORY_SPENDING,
                annual_spending_change_billions=50.0,
            ),
            TaxPolicy(
                name="Test tax",
                description="Test",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=0.02,
                affected_income_threshold=400_000,
            ),
        ],
        ids=["spending", "tax"],
    )
    def test_every_other_policy_family_is_unchanged(self, policy):
        """The branch is additive: only a policy defining the method takes it.

        Everything else still reads the deficit path, split by policy type,
        exactly as it did before.
        """
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
        result = scorer.score_policy(policy)
        scenario = policy_to_scenario(policy, result)
        assert not hasattr(policy, "macro_demand_impulse")
        if "SPENDING" in policy.policy_type.name:
            assert scenario.outlays_change[0] == pytest.approx(
                result.final_deficit_effect[0], abs=1e-9
            )
            assert scenario.receipts_change[0] == pytest.approx(0.0, abs=1e-9)
        else:
            assert scenario.receipts_change[0] == pytest.approx(
                -result.final_deficit_effect[0], abs=1e-9
            )
            assert scenario.outlays_change[0] == pytest.approx(0.0, abs=1e-9)


class TestReciprocalSchedule:
    def test_the_coverage_constant_is_gone(self):
        assert "reciprocal_coverage_rate" not in TRADE_BASELINE

    def test_the_schedule_covers_the_non_usmca_base(self):
        """Consistency with the universal preset, which the lane did not touch.

        Covered imports plus the Annex II exemptions must come back to the
        non-USMCA goods base the universal tariff already uses, because both
        are the same Census measurement read two ways.
        """
        rows = _rows_with_role("model_input")
        total = sum(float(r["imports_2024_billions"]) for r in rows)
        universal_base = (
            TRADE_BASELINE["total_imports_billions"]
            * TRADE_BASELINE["universal_coverage_rate"]
        )
        assert total == pytest.approx(universal_base, rel=0.005)

    def test_the_published_annex_i_rates_are_reproduced(self):
        """The out-of-sample check, and it is the load-bearing one.

        Sixteen rates are transcribed from Executive Order 14257's Annex I and
        marked ``external_check``; ``load_reciprocal_schedule`` refuses to read
        them. A reconstruction that drifts from the document fails here.
        """
        published = {
            row["cty_code"]: float(row["reciprocal_rate"])
            for row in _rows_with_role("external_check")
        }
        assert len(published) >= 16
        derived = {
            row["cty_code"]: float(row["reciprocal_rate"])
            for row in _model_input_rows()
        }
        for code, rate in published.items():
            assert code in derived, f"Annex I partner {code} missing from the schedule"
            # Annex I rounds up, so the reconstruction sits just below every
            # published rate; a point and a half is the whole spread.
            assert derived[code] == pytest.approx(rate, abs=0.015), code

    def test_the_loader_never_reads_a_check_row(self):
        """The published rates are in the same file and must stay out of it.

        Sixteen ``external_check`` rows carry a ``reciprocal_rate`` column and
        no base. If the loader ever stopped filtering on ``role`` they would
        be scored as partners, which is the exact leakage the check exists to
        detect.
        """
        loaded = load_reciprocal_schedule()
        assert len(loaded) == len(_rows_with_role("model_input"))
        assert all(base > 0 for _, base, _ in loaded)

    def test_the_schedule_prices_partners_at_different_rates(self):
        rates = {rate for _, _, rate in load_reciprocal_schedule()}
        assert len(rates) > 20
        assert min(rates) == pytest.approx(0.10, abs=1e-9)
        assert max(rates) > 0.40

    def test_an_average_rate_would_not_reproduce_the_schedule(self):
        """Why the schedule is summed rather than averaged.

        The volume response is convex in the rate — the elasticity doubles
        above a 30pp price change — so evaluating once at the base-weighted
        average is not the same object as evaluating row by row.
        """
        scheduled = create_reciprocal_tariffs()
        flat = TariffPolicy(
            name="Flat",
            description="Test",
            tariff_rate_change=scheduled.tariff_rate_change,
            import_base_billions=scheduled.import_base_billions,
        )
        assert scheduled.estimate_static_revenue_effect(
            0
        ) != pytest.approx(flat.estimate_static_revenue_effect(0), rel=0.01)

    def test_a_single_row_schedule_is_the_scalar_path(self):
        """The schedule must be a generalisation, not a second implementation."""
        scheduled = TariffPolicy(
            name="One row",
            description="Test",
            rate_schedule=(("only", 1000.0, 0.10),),
        )
        scalar = TariffPolicy(
            name="Scalar",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        assert scheduled.estimate_static_revenue_effect(0) == pytest.approx(
            scalar.estimate_static_revenue_effect(0), abs=1e-9
        )
        assert scheduled.macro_demand_impulse() == pytest.approx(
            scalar.macro_demand_impulse(), abs=1e-9
        )


class TestSteelDerivativeBracket:
    def test_the_derivative_chapter_is_in_the_shipped_base(self):
        policy = create_steel_tariff_25()
        assert policy.import_base_billions == pytest.approx(
            TRADE_BASELINE["steel_aluminum_imports_billions"]
            + TRADE_BASELINE["steel_derivative_imports_billions"],
            abs=1e-9,
        )

    def test_the_floor_is_one_argument_away(self):
        floor = create_steel_tariff_25(include_derivatives=False)
        assert floor.import_base_billions == pytest.approx(
            TRADE_BASELINE["steel_aluminum_imports_billions"], abs=1e-9
        )
        assert floor.estimate_static_revenue_effect(
            0
        ) < create_steel_tariff_25().estimate_static_revenue_effect(0)

    def test_the_two_bases_keep_their_own_collected_duty(self):
        """Not blended: HS 73 pays 5.63% where HS 72 plus HS 76 pay 3.06%."""
        rates = {rate for _, _, rate in create_steel_tariff_25().rate_schedule}
        assert len(rates) == 2

    def test_including_derivatives_does_not_triple_the_base(self):
        """The repository said "roughly triple" in three places. It is 1.84x."""
        ratio = (
            TRADE_BASELINE["steel_aluminum_imports_billions"]
            + TRADE_BASELINE["steel_derivative_imports_billions"]
        ) / TRADE_BASELINE["steel_aluminum_imports_billions"]
        assert 1.8 < ratio < 1.9


def _all_rows():
    with RECIPROCAL_SCHEDULE_PATH.open(encoding="utf-8") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    yield from csv.DictReader(lines)


def _rows_with_role(role: str):
    return [row for row in _all_rows() if row.get("role") == role]


def _model_input_rows():
    return [
        row
        for row in _all_rows()
        if row.get("role") == "model_input" and row["cty_code"] != "REMAINDER"
    ]
