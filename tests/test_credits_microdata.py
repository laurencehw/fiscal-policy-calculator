"""
Per-unit credit scoring over the CPS microdata (Wave 3, lane L3).

Three things are pinned here:

1. **The statutory schedule is one source.** The microsim engine and
   ``credits_core`` used to restate the EITC parameters separately and had
   drifted apart on the maxima and, worse, on the phase-out rate — a single
   21.06% applied to every child count where the statute sets four.
2. **The dead levers reach something.** ``expand_qualifying_age``,
   ``include_childless_adults`` and ``take_up_rate_change`` were declared
   fields no code path read; ``make_fully_refundable`` and ``remove_phase_out``
   reached only unreachable flat constants.
3. **The derived path never reads a fitted annual.** All three credit
   benchmarks carry an annual that is the published target divided by exactly
   ten, so a derivation that touched it would be reading the answer key.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fiscal_model.credits import (
    create_arp_recovery_rebate,
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_ctc_permanent_extension,
)
from fiscal_model.credits_core import (
    CREDIT_APP_MODE,
    CREDIT_HELD_OUT_MODE,
    CREDIT_MODE_DERIVED,
    CREDIT_MODE_REPORTED,
    CREDIT_SCORECARD_MODE,
    CTC_CURRENT_LAW,
    EITC_CURRENT_LAW,
    CreditType,
    TaxCreditPolicy,
)
from fiscal_model.credits_microdata import (
    current_law_ctc_schedule,
    current_law_eitc_schedule,
    weighted_liability_change,
)
from fiscal_model.microsim.engine import MicroTaxCalculator
from fiscal_model.policies import PolicyType


class TestStatutorySchedule:
    """Rev. Proc. 2023-34 sec. 2.06 (EITC) and IRC sec. 24 (CTC)."""

    def test_engine_reads_the_credits_core_eitc_maxima(self):
        calc = MicroTaxCalculator()
        assert calc.eitc_max_0_children == EITC_CURRENT_LAW[0]["max_credit"]
        assert calc.eitc_max_1_child == EITC_CURRENT_LAW[1]["max_credit"]
        assert calc.eitc_max_2_children == EITC_CURRENT_LAW[2]["max_credit"]
        assert calc.eitc_max_3plus_children == EITC_CURRENT_LAW[3]["max_credit"]
        # The values that were stale in the engine's own copy.
        assert (calc.eitc_max_1_child, calc.eitc_max_2_children) == (4213.0, 6960.0)

    def test_phase_out_rate_varies_by_child_count(self):
        """IRC sec. 32(b)(1): 7.65 / 15.98 / 21.06 / 21.06 percent.

        The engine applied 21.06% to every count, which over-phases the
        childless credit by a factor of nearly three — and the childless
        population is exactly what a childless expansion is about.
        """
        calc = MicroTaxCalculator()
        assert calc.eitc_phaseout_rate_0_children == pytest.approx(0.0765)
        assert calc.eitc_phaseout_rate_1_child == pytest.approx(0.1598)
        assert calc.eitc_phaseout_rate_2_children == pytest.approx(0.2106)
        assert calc.eitc_phaseout_rate_3plus_children == pytest.approx(0.2106)

    def test_childless_credit_phases_out_at_the_childless_rate(self):
        calc = MicroTaxCalculator()
        pop = pd.DataFrame(
            {
                "agi": [13_000.0],
                "wages": [13_000.0],
                "married": [0],
                "children": [0],
                "weight": [1.0],
                "age_head": [30],
            }
        )
        result = calc.calculate(pop)
        excess = 13_000.0 - EITC_CURRENT_LAW[0]["phase_out_start_single"]
        expected = 632.0 - excess * 0.0765
        assert result.loc[0, "eitc_value"] == pytest.approx(expected, abs=1.0)

    def test_engine_reads_the_credits_core_ctc_parameters(self):
        calc = MicroTaxCalculator()
        assert calc.ctc_amount == CTC_CURRENT_LAW["credit_per_child"]
        assert calc.actc_max_per_child == CTC_CURRENT_LAW["refundable_max"]
        assert calc.ctc_qualifying_age == CTC_CURRENT_LAW["qualifying_age"]


class TestQualifyingChildren:
    def _unit(self, **bands):
        row = {
            "agi": 30_000.0,
            "wages": 30_000.0,
            "married": 0,
            "children": 1,
            "weight": 1.0,
            "age_head": 40,
            "dependents_under_6": 0,
            "dependents_6_to_16": 1,
            "dependents_age_17": 0,
            "dependents_age_18": 0,
            "dependents_19_to_23_student": 0,
        }
        row.update(bands)
        return pd.DataFrame([row])

    def test_eitc_counts_18_year_olds_and_students(self):
        """IRC sec. 32(c)(3): under 19, or under 24 and a full-time student."""
        calc = MicroTaxCalculator()
        pop = self._unit(dependents_age_18=1, dependents_19_to_23_student=1)
        assert calc.eitc_qualifying_children(pop)[0] == 3

    def test_ctc_stops_at_17_under_current_law(self):
        calc = MicroTaxCalculator()
        pop = self._unit(dependents_age_17=1, dependents_age_18=1)
        under_6, older = calc.ctc_qualifying_children(pop)
        assert under_6[0] + older[0] == 1

    def test_ctc_includes_17_year_olds_when_the_age_is_expanded(self):
        calc = MicroTaxCalculator()
        calc.ctc_qualifying_age = 18
        pop = self._unit(dependents_age_17=1, dependents_age_18=1)
        under_6, older = calc.ctc_qualifying_children(pop)
        assert under_6[0] + older[0] == 2

    def test_falls_back_to_children_when_bands_are_absent(self):
        """A fixture without the age bands keeps the engine's old behaviour."""
        calc = MicroTaxCalculator()
        pop = pd.DataFrame(
            {
                "agi": [30_000.0],
                "wages": [30_000.0],
                "married": [0],
                "children": [2],
                "weight": [1.0],
                "age_head": [40],
            }
        )
        assert calc.eitc_qualifying_children(pop)[0] == 2
        under_6, older = calc.ctc_qualifying_children(pop)
        assert (under_6[0], older[0]) == (0, 2)


class TestChildlessAgeTest:
    def _worker(self, age):
        return pd.DataFrame(
            {
                "agi": [9_000.0],
                "wages": [9_000.0],
                "married": [0],
                "children": [0],
                "weight": [1.0],
                "age_head": [age],
            }
        )

    @pytest.mark.parametrize("age", [19, 24, 65, 70])
    def test_ineligible_outside_25_to_64(self, age):
        calc = MicroTaxCalculator()
        assert calc.calculate(self._worker(age)).loc[0, "eitc_value"] == 0.0

    @pytest.mark.parametrize("age", [25, 40, 64])
    def test_eligible_inside_25_to_64(self, age):
        calc = MicroTaxCalculator()
        assert calc.calculate(self._worker(age)).loc[0, "eitc_value"] > 0.0

    def test_expansion_reaches_a_22_year_old(self):
        calc = MicroTaxCalculator()
        result = calc.apply_reform(
            self._worker(22),
            {"eitc_childless_min_age": 19, "eitc_childless_max_age": 200},
        )
        assert result.loc[0, "eitc_value"] > 0.0

    def test_the_age_bounds_are_restored_after_a_reform(self):
        calc = MicroTaxCalculator()
        calc.apply_reform(
            self._worker(22),
            {"eitc_childless_min_age": 19, "eitc_childless_max_age": 200},
        )
        assert (calc.eitc_childless_min_age, calc.eitc_childless_max_age) == (25, 65)


class TestTwoTierCTC:
    def _family(self, agi):
        return pd.DataFrame(
            {
                "agi": [agi],
                "wages": [agi],
                "married": [1],
                "children": [1],
                "weight": [1.0],
                "age_head": [40],
                "dependents_under_6": [1],
                "dependents_6_to_16": [0],
                "dependents_age_17": [0],
                "dependents_age_18": [0],
                "dependents_19_to_23_student": [0],
            }
        )

    ARP = {
        "ctc_amount": 3000.0,
        "ctc_amount_under_6": 3600.0,
        "ctc_qualifying_age": 18,
        "ctc_protected_amount": 2000.0,
        "ctc_phaseout_start_low_single": 75_000.0,
        "ctc_phaseout_start_low_married": 150_000.0,
        "ctc_fully_refundable": True,
    }

    def test_full_amount_below_the_low_threshold(self):
        calc = MicroTaxCalculator()
        assert calc.apply_reform(self._family(100_000.0), self.ARP).loc[
            0, "ctc_value"
        ] == pytest.approx(3600.0)

    def test_increment_phases_out_but_the_base_survives(self):
        """At $200,000 the $1,600 increment is gone and the $2,000 remains.

        A single-tier phase-out from $150,000 would take the whole credit to
        zero here, which is what the old flat-$3,300 shape did.
        """
        calc = MicroTaxCalculator()
        assert calc.apply_reform(self._family(200_000.0), self.ARP).loc[
            0, "ctc_value"
        ] == pytest.approx(2000.0)

    def test_base_phases_out_from_the_high_threshold(self):
        calc = MicroTaxCalculator()
        value = calc.apply_reform(self._family(420_000.0), self.ARP).loc[0, "ctc_value"]
        assert value == pytest.approx(2000.0 - 20 * 50)

    def test_current_law_is_a_single_tier(self):
        calc = MicroTaxCalculator()
        assert calc.calculate(self._family(300_000.0)).loc[
            0, "ctc_value"
        ] == pytest.approx(2000.0)


class TestPerPersonRebate:
    def _household(self, agi, dependents=2):
        return pd.DataFrame(
            {
                "agi": [agi],
                "wages": [agi],
                "married": [1],
                "children": [dependents],
                "dependent_count": [dependents],
                "weight": [1.0],
                "age_head": [40],
            }
        )

    REBATE = {"rebate_per_person": 1400.0}

    def test_zero_under_current_law(self):
        calc = MicroTaxCalculator()
        assert calc.calculate(self._household(50_000.0)).loc[0, "rebate_value"] == 0.0

    def test_pays_every_person_in_the_unit(self):
        calc = MicroTaxCalculator()
        result = calc.apply_reform(self._household(50_000.0), self.REBATE)
        # Filer + spouse + two dependents.
        assert result.loc[0, "rebate_value"] == pytest.approx(4 * 1400.0)

    def test_phases_out_completely_across_the_band(self):
        calc = MicroTaxCalculator()
        assert calc.apply_reform(self._household(160_000.0), self.REBATE).loc[
            0, "rebate_value"
        ] == pytest.approx(0.0)
        half = calc.apply_reform(self._household(155_000.0), self.REBATE).loc[
            0, "rebate_value"
        ]
        assert half == pytest.approx(4 * 1400.0 * 0.5)

    def test_is_refundable(self):
        """A household with no liability still receives the whole payment."""
        calc = MicroTaxCalculator()
        pop = self._household(0.0)
        base = calc.calculate(pop).loc[0, "final_tax"]
        reform = calc.apply_reform(pop, self.REBATE).loc[0, "final_tax"]
        assert base - reform == pytest.approx(4 * 1400.0)


class TestModes:
    def test_defaults_are_the_documented_ones(self):
        assert CREDIT_APP_MODE == CREDIT_MODE_REPORTED
        assert CREDIT_SCORECARD_MODE == CREDIT_MODE_REPORTED
        assert CREDIT_HELD_OUT_MODE == CREDIT_MODE_DERIVED
        assert create_biden_ctc_2021().mode == CREDIT_MODE_REPORTED

    def test_an_unknown_mode_is_refused(self):
        with pytest.raises(ValueError, match="mode must be one of"):
            TaxCreditPolicy(
                name="bad",
                description="bad",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.CHILD_TAX_CREDIT,
                mode="fitted",
            )

    def test_reported_mode_returns_the_fitted_annual(self):
        policy = create_biden_ctc_2021()
        assert policy.estimate_static_revenue_effect(0) == pytest.approx(-160.0)

    def test_derived_mode_ignores_the_fitted_annual(self):
        """The annual is the target over ten, so reading it would be leakage."""
        policy = create_biden_ctc_2021()
        policy.mode = CREDIT_MODE_DERIVED
        derived = policy.estimate_static_revenue_effect(0)
        assert derived != pytest.approx(-160.0)
        # And it stays put when the fitted annual is removed entirely.
        policy.annual_revenue_change_billions = None
        assert policy.estimate_static_revenue_effect(0) == pytest.approx(derived)

    def test_derived_annuals_are_window_averages_and_not_regrown(self):
        for factory in (
            create_biden_ctc_2021,
            create_ctc_permanent_extension,
            create_biden_eitc_childless,
        ):
            policy = factory()
            policy.mode = CREDIT_MODE_DERIVED
            assert policy.uses_window_average_annual() is True


class TestDerivedScores:
    """Levels the mechanism produces, so a silent break is visible.

    Bands are wide enough to survive a CPS revision but narrow enough to catch
    a structural regression; the point estimates are in
    ``planning/lanes/L3_credits.md`` §4.
    """

    @pytest.mark.parametrize(
        ("factory", "low", "high"),
        [
            (create_biden_ctc_2021, -170.0, -135.0),
            (create_ctc_permanent_extension, -80.0, -62.0),
            (create_biden_eitc_childless, -14.0, -8.0),
        ],
    )
    def test_derived_window_average_is_in_band(self, factory, low, high):
        policy = factory()
        policy.mode = CREDIT_MODE_DERIVED
        assert low <= policy.derived_window_average() <= high

    def test_the_counterfactual_switches_at_the_2025_sunset(self):
        """A permanent credit is scored against $1,000 from 2026, not $2,000.

        Without the switch the ARP credit costs about $0.9T over the window
        instead of about $1.5T, which is most of the gap to the $1.6T target.
        """
        policy = create_biden_ctc_2021()
        baseline_for_year, _ = policy.credit_schedules()
        assert baseline_for_year(2025).params == current_law_ctc_schedule().params
        assert baseline_for_year(2026).params["ctc_amount"] == pytest.approx(1000.0)

    def test_the_eitc_counterfactual_does_not_switch(self):
        policy = create_biden_eitc_childless()
        baseline_for_year, _ = policy.credit_schedules()
        for year in (2025, 2026, 2034):
            assert baseline_for_year(year).params == current_law_eitc_schedule().params

    def test_take_up_change_scales_the_derived_score(self):
        base = create_biden_ctc_2021()
        base.mode = CREDIT_MODE_DERIVED
        raised = create_biden_ctc_2021()
        raised.mode = CREDIT_MODE_DERIVED
        raised.take_up_rate_change = 0.10
        assert raised.derived_window_average() == pytest.approx(
            base.derived_window_average() * 1.10, rel=1e-9
        )

    def test_take_up_level_is_not_applied(self):
        """Only the change. The docstring says why; this stops it drifting."""
        policy = create_biden_eitc_childless()
        assert policy.participation_rate == pytest.approx(0.75)
        assert policy.effective_take_up_rate() == pytest.approx(1.0)

    def test_recovery_rebate_is_expressible_per_person(self):
        policy = create_arp_recovery_rebate()
        baseline_for_year, reform = policy.credit_schedules()
        assert baseline_for_year(2021).params["rebate_per_person"] == 0.0
        assert reform.params["rebate_per_person"] == pytest.approx(1400.0)


class TestScheduleArithmetic:
    def test_no_change_scores_zero(self):
        """Current law against current law must cost nothing."""
        schedule = current_law_ctc_schedule()
        assert weighted_liability_change(schedule, schedule) == pytest.approx(0.0)

    def test_a_credit_expansion_lowers_liability(self):
        from fiscal_model.credits_microdata import CreditSchedule

        richer = CreditSchedule(
            params={**current_law_ctc_schedule().params, "ctc_amount": 3000.0}
        )
        assert weighted_liability_change(current_law_ctc_schedule(), richer) < 0
