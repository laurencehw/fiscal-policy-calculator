"""
Tests for CBO's household universe in the distributional engine.

What is pinned here, and why:

- **The equivalence scale and the ranking measure**, because they are CBO's
  published methodology and not parameters this repository may choose. A test
  that fails when somebody edits the exponent is the point.
- **The people-weighted group construction**, including CBO's own observation
  that equal numbers of people means *unequal* numbers of households.
- **The universe is honestly reported.** A household request that cannot reach
  the microsim must say it produced a tax-unit table.
- **The tax-unit path is inert.** Every default-constructed engine must behave
  exactly as it did before the household layer existed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import fiscal_model.microsim as _microsim
from fiscal_model.distribution import (
    DistributionalEngine,
    IncomeGroupType,
)
from fiscal_model.distribution_households import (
    HOUSEHOLD,
    HOUSEHOLD_EQUIVALENCE_EXPONENT,
    TAX_UNIT,
    aggregate_to_households,
    assign_people_weighted_groups,
    build_household_groups,
    supports_household_universe,
)
from fiscal_model.microsim.data_builder import summarize_tax_units
from fiscal_model.validation.benchmark_runners import (
    _combine_distributional_results,
    default_model_runner,
)
from fiscal_model.validation.cbo_distributions import (
    CBO_ARP_2021,
    CBO_JCT_BENCHMARKS,
    JCT_SALT_REPEAL_2024,
    compare_distribution,
)

MICRODATA = pd.read_csv(
    Path(_microsim.__file__).parent / "tax_microdata_2024.csv"
)


def _toy_frame() -> pd.DataFrame:
    """Two households: one four-person unit, one two-unit pair sharing a roof.

    Hand-built so the arithmetic below can be checked by eye rather than by
    re-running the same code that produced it.
    """
    return pd.DataFrame(
        [
            # household 1: one tax unit, four people, $40,000 of wages.
            {
                "household_id": 1,
                "household_weight": 10.0,
                "household_persons": 4,
                "member_count": 4,
                "agi": 40_000.0,
                "social_security": 0.0,
                "tax_change": -400.0,
                "final_tax": 1_000.0,
                "reform_tax": 600.0,
            },
            # household 2: two tax units, one person each. The second has no
            # AGI at all — the dependent-filer / secondary-unit case that a
            # tax-unit ranking puts in its own bottom bucket.
            {
                "household_id": 2,
                "household_weight": 5.0,
                "household_persons": 2,
                "member_count": 1,
                "agi": 30_000.0,
                "social_security": 20_000.0,
                "tax_change": -100.0,
                "final_tax": 2_000.0,
                "reform_tax": 1_900.0,
            },
            {
                "household_id": 2,
                "household_weight": 5.0,
                "household_persons": 2,
                "member_count": 1,
                "agi": 0.0,
                "social_security": 0.0,
                "tax_change": -50.0,
                "final_tax": 0.0,
                "reform_tax": -50.0,
            },
        ]
    )


class TestCBOMethodologyIsWhatIsImplemented:
    def test_equivalence_scale_is_the_square_root_of_household_size(self):
        """CBO divides household income by the square root of household size.

        Published, not chosen: "CBO calculates adjusted household income by
        dividing household income by the square root of the number of people in
        the household." A change to this constant is a change to CBO's
        methodology, not a tuning decision.
        """
        assert HOUSEHOLD_EQUIVALENCE_EXPONENT == 0.5

    def test_ranking_income_is_market_income_plus_social_insurance(self):
        """Income before transfers and taxes = agi + social security here."""
        households = aggregate_to_households(_toy_frame())
        # Household 2's two units: $30,000 AGI + $20,000 Social Security.
        assert households.loc[2, "income_before_transfers_and_taxes"] == 50_000.0
        assert households.loc[1, "income_before_transfers_and_taxes"] == 40_000.0

    def test_size_adjustment_divides_by_the_square_root_of_size(self):
        households = aggregate_to_households(_toy_frame())
        assert households.loc[1, "adjusted_income"] == pytest.approx(
            40_000.0 / np.sqrt(4)
        )
        assert households.loc[2, "adjusted_income"] == pytest.approx(
            50_000.0 / np.sqrt(2)
        )

    def test_size_adjustment_touches_only_the_ranking_key(self):
        """"All other income measures ... are unadjusted." So they must be."""
        households = aggregate_to_households(
            _toy_frame(), sum_columns=("tax_change", "final_tax")
        )
        assert households.loc[1, "agi"] == 40_000.0
        assert households.loc[1, "tax_change"] == -400.0
        assert households.loc[1, "final_tax"] == 1_000.0


class TestAggregationIsExactArithmetic:
    def test_tax_units_are_summed_into_their_household(self):
        households = aggregate_to_households(
            _toy_frame(), sum_columns=("tax_change", "final_tax", "reform_tax")
        )
        assert len(households) == 2
        assert households.loc[2, "tax_change"] == -150.0
        assert households.loc[2, "final_tax"] == 2_000.0
        assert households.loc[2, "reform_tax"] == 1_850.0

    def test_household_weight_and_roster_are_read_not_summed(self):
        households = aggregate_to_households(_toy_frame())
        # Two tax units, one household weight — not 10.0.
        assert households.loc[2, "household_weight"] == 5.0
        assert households.loc[2, "household_persons"] == 2

    def test_person_weight_is_households_times_their_size(self):
        households = aggregate_to_households(_toy_frame())
        assert households["person_weight"].sum() == 10.0 * 4 + 5.0 * 2

    def test_missing_household_columns_raise_a_directed_error(self):
        frame = _toy_frame().drop(columns=["household_weight"])
        with pytest.raises(KeyError, match="household_weight"):
            aggregate_to_households(frame)

    def test_supports_household_universe_detects_the_columns(self):
        assert supports_household_universe(_toy_frame()) is True
        assert supports_household_universe(_toy_frame().drop(columns=["agi"])) is False


class TestPeopleWeightedGroups:
    def test_groups_hold_equal_numbers_of_people(self):
        households = aggregate_to_households(MICRODATA)
        index = assign_people_weighted_groups(households, IncomeGroupType.QUINTILE)
        people = households.groupby(index)["person_weight"].sum()
        assert len(people) == 5
        # A household straddling a boundary falls whole into the lower group,
        # so "roughly equal" is CBO's own word; on 56,251 households the groups
        # come within a tenth of a percent of each other.
        assert people.max() / people.min() < 1.001

    def test_groups_hold_unequal_numbers_of_households(self):
        """CBO: 'quintiles generally contain unequal numbers of households.'"""
        households = aggregate_to_households(MICRODATA)
        index = assign_people_weighted_groups(households, IncomeGroupType.QUINTILE)
        counts = households.groupby(index)["household_weight"].sum()
        # The bottom quintile holds the most households because its households
        # are the smallest; if these came out equal, the groups were cut on
        # households rather than on people.
        assert counts.idxmax() == 0
        assert counts.max() / counts.min() > 1.15

    def test_deciles_are_supported_and_quintiles_nest_inside_them(self):
        households = aggregate_to_households(MICRODATA)
        quintiles = assign_people_weighted_groups(households, IncomeGroupType.QUINTILE)
        deciles = assign_people_weighted_groups(households, IncomeGroupType.DECILE)
        # Decile d must sit inside quintile d // 2 for all but the boundary
        # households, which round differently between the two cuts.
        agreement = (deciles // 2 == quintiles).mean()
        assert agreement > 0.999

    def test_dollar_bracket_groupings_are_refused(self):
        households = aggregate_to_households(_toy_frame())
        with pytest.raises(ValueError, match="filing-unit construct"):
            assign_people_weighted_groups(households, IncomeGroupType.JCT_DOLLAR)

    def test_a_non_finite_ranking_key_is_refused_not_ranked_last(self):
        """A non-finite ranking key sorts to the end — i.e. to the top quintile.

        A household whose income could not be computed would otherwise be
        ranked silently as the richest in the country, which is the worst
        failure mode a ranking function has. It must raise instead.

        (A NaN in a source column would not get this far: ``groupby.sum`` skips
        it, so the household is ranked on its remaining income. An infinity
        propagates, which is what this exercises.)
        """
        frame = _toy_frame()
        frame.loc[0, "agi"] = float("inf")
        households = aggregate_to_households(frame)
        with pytest.raises(ValueError, match="non-finite income"):
            assign_people_weighted_groups(households, IncomeGroupType.QUINTILE)

    def test_group_rows_carry_household_counts_and_ranking_bounds(self):
        households = aggregate_to_households(
            MICRODATA.assign(final_tax=0.0), sum_columns=("final_tax",)
        )
        index = assign_people_weighted_groups(households, IncomeGroupType.QUINTILE)
        groups = build_household_groups(households, index, IncomeGroupType.QUINTILE)
        assert [g.name for g in groups] == [
            "Lowest Quintile",
            "Second Quintile",
            "Middle Quintile",
            "Fourth Quintile",
            "Top Quintile",
        ]
        # 132.4M households, and the top group is open-ended.
        assert sum(g.num_returns for g in groups) == pytest.approx(132_391_925, rel=1e-6)
        assert groups[-1].ceiling is None
        # Bounds are in the *adjusted* ranking income, and they ascend.
        floors = [g.floor for g in groups]
        assert floors == sorted(floors)


class TestBundledMicrodataCarriesTheHouseholdLayer:
    def test_columns_are_present(self):
        assert supports_household_universe(MICRODATA)

    def test_tax_units_partition_the_household_roster(self):
        """If this fails, the household layer loses or duplicates people."""
        summary = summarize_tax_units(MICRODATA)
        assert summary["households_with_roster_mismatch"] == 0.0

    def test_weighted_totals_match_the_cps_household_file(self):
        summary = summarize_tax_units(MICRODATA)
        assert summary["weighted_households"] == pytest.approx(132_391_925, rel=1e-6)
        assert summary["weighted_household_persons"] == pytest.approx(
            320_890_854, rel=1e-6
        )

    def test_the_household_universe_is_far_smaller_than_the_tax_unit_one(self):
        """The lane's whole premise, as a number."""
        summary = summarize_tax_units(MICRODATA)
        assert summary["weighted_tax_units"] > 1.4 * summary["weighted_households"]


class TestEngineUniverseSelection:
    def test_default_is_tax_units(self):
        assert DistributionalEngine().unit == TAX_UNIT

    def test_unknown_unit_is_refused_at_construction(self):
        with pytest.raises(ValueError, match="Unknown distributional unit"):
            DistributionalEngine(unit="family")

    def test_unknown_unit_is_refused_per_call(self):
        engine = DistributionalEngine()
        with pytest.raises(ValueError, match="Unknown distributional unit"):
            engine._resolve_unit("family")

    def test_household_request_on_a_microsim_policy_reports_household(self):
        from fiscal_model.credits import create_arp_recovery_rebate

        engine = DistributionalEngine(data_year=2021, unit=HOUSEHOLD)
        result = engine.analyze_policy(
            create_arp_recovery_rebate(), group_type=IncomeGroupType.QUINTILE
        )
        assert result.unit == HOUSEHOLD
        assert result.engine == "microsim"
        # 132.4M households, not 191.1M tax units.
        assert sum(r.income_group.num_returns for r in result.results) == pytest.approx(
            132_391_925, rel=1e-6
        )

    def test_household_request_on_a_synthetic_policy_reports_tax_units(self):
        """The honest fallback: say what was ranked, not what was asked for."""
        from fiscal_model.tcja import create_tcja_extension

        engine = DistributionalEngine(data_year=2018, unit=HOUSEHOLD)
        result = engine.analyze_policy(
            create_tcja_extension(extend_all=True), group_type=IncomeGroupType.DECILE
        )
        assert result.engine == "synthetic"
        assert result.unit == TAX_UNIT

    def test_tax_unit_path_is_unchanged_by_the_option(self):
        from fiscal_model.credits import create_arp_recovery_rebate

        policy = create_arp_recovery_rebate()
        default = DistributionalEngine(data_year=2021).analyze_policy(
            policy, group_type=IncomeGroupType.QUINTILE
        )
        explicit = DistributionalEngine(data_year=2021, unit=TAX_UNIT).analyze_policy(
            policy, group_type=IncomeGroupType.QUINTILE
        )
        assert default.unit == TAX_UNIT
        assert [r.tax_change_total for r in default.results] == [
            r.tax_change_total for r in explicit.results
        ]


class TestBenchmarkRegistration:
    def test_every_benchmark_declares_a_universe_with_a_source(self):
        for benchmark in CBO_JCT_BENCHMARKS:
            assert benchmark.ranking_universe in (TAX_UNIT, HOUSEHOLD)
            assert benchmark.ranking_universe_source, benchmark.policy_id

    def test_cbo_tables_are_households_and_jct_tables_are_filing_units(self):
        by_source = {b.policy_id: b.ranking_universe for b in CBO_JCT_BENCHMARKS}
        assert by_source["cbo_tcja_2018"] == HOUSEHOLD
        assert by_source["cbo_arp_2021"] == HOUSEHOLD
        assert by_source["cbo_tcja_extension_2026"] == HOUSEHOLD
        assert by_source["cbo_pl119_21_2026"] == HOUSEHOLD
        assert by_source["jct_tcja_2019"] == TAX_UNIT
        assert by_source["jct_salt_repeal_2024"] == TAX_UNIT
        assert by_source["jct_corporate_28_2022"] == TAX_UNIT


class TestBenchmarkOutcomes:
    def test_arp_is_scored_on_households_and_improves(self):
        result = default_model_runner(CBO_ARP_2021)
        comparison = compare_distribution(result, CBO_ARP_2021)
        # 7.77pp on tax units before the household universe; the band this lane
        # pre-registered was 1.5-6.0pp.
        assert comparison.mean_absolute_share_error_pp == pytest.approx(3.72, abs=0.05)
        assert comparison.overall_rating == "good"

    def test_arp_bottom_quintile_stops_absorbing_the_bundle(self):
        result = default_model_runner(CBO_ARP_2021)
        shares = {
            row.income_group.name: abs(row.share_of_total_change)
            for row in result.results
        }
        # 53.4% on tax units against CBO's 34.0%.
        assert shares["Lowest quintile"] == pytest.approx(0.286, abs=0.01)

    def test_salt_repeal_stays_on_filing_units_and_does_not_move(self):
        """The control: the other microsim benchmark, on the other universe."""
        result = default_model_runner(JCT_SALT_REPEAL_2024)
        comparison = compare_distribution(result, JCT_SALT_REPEAL_2024)
        assert comparison.mean_absolute_share_error_pp == pytest.approx(5.86, abs=0.005)


class TestCompositeMergeAverages:
    def test_group_average_is_the_sum_of_the_components_not_their_mean(self):
        """A household getting $1,400 and $3,000 got $4,400, not $2,200."""
        from types import SimpleNamespace

        def component(avg: float, total: float):
            group = SimpleNamespace(name="Lowest Quintile", num_returns=1_000)
            return SimpleNamespace(
                total_tax_change=total,
                results=[
                    SimpleNamespace(
                        income_group=group,
                        tax_change_avg=avg,
                        share_of_total_change=1.0,
                    )
                ],
            )

        merged = _combine_distributional_results(
            [component(-1_400.0, -400.0), component(-3_000.0, -100.0)]
        )
        assert merged.results[0].tax_change_avg == pytest.approx(-4_400.0)
        assert merged.results[0].share_of_total_change == pytest.approx(1.0)
