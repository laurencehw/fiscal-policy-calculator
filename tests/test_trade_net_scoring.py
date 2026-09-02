"""The tariff module's net scoring chain, and the data behind it.

Lane L8 of ``planning/MODELING_IMPROVEMENT.md`` turned ``trade.py`` from a
gross-customs-revenue calculator into a conventional net score. These tests pin
the mechanism rather than the numbers it happens to produce:

* every ``TRADE_BASELINE`` level matches the transcribed Census row it came
  from, so the module and its provenance file cannot drift apart;
* the netting chain is exactly avoidance, the income-and-payroll offset and
  retaliation, in that order, with no double counting;
* the import-demand response runs through the *border* pass-through, not the
  retail one;
* no coverage constant is fitted to a benchmark any more - the two that were
  are derived or deleted, and a per-case elasticity override is gone;
* the steel preset is incremental over the Section 232 duty actually collected;
* every shipped tariff preset renders the note that explains the new number.
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.constants import MARGINAL_REVENUE_RATE
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.trade import (
    TRADE_BASELINE,
    TariffPolicy,
    create_auto_tariff_25,
    create_reciprocal_tariffs,
    create_steel_tariff_25,
    create_trump_china_60,
    create_trump_universal_10,
)
from fiscal_model.ui.tabs.results_summary import tariff_net_caption

CSV_PATH = (
    Path(__file__).parent.parent
    / "fiscal_model"
    / "data_files"
    / "trade"
    / "tariff_scoring_inputs.csv"
)

FACTORIES = (
    create_trump_universal_10,
    create_trump_china_60,
    create_auto_tariff_25,
    create_steel_tariff_25,
    create_reciprocal_tariffs,
)


class _FakeStreamlit:
    """Enough Streamlit to render the headline block and collect its captions."""

    def __init__(self):
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.codes: list[str] = []

    def markdown(self, body="", *args, **kwargs):
        self.markdowns.append(body)

    def caption(self, body="", *args, **kwargs):
        self.captions.append(body)

    def code(self, body="", *args, **kwargs):
        self.codes.append(body)


def _transcribed_rows() -> dict[str, dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8") as fh:
        lines = [line for line in fh if not line.startswith("#")]
    return {row["key"]: row for row in csv.DictReader(lines)}


class TestTranscribedInputs:
    """The module's constants are the transcribed ones, not near-misses."""

    def test_csv_exists_and_parses(self):
        rows = _transcribed_rows()
        assert rows, "tariff_scoring_inputs.csv parsed to nothing"
        assert {"model_input", "context", "external_check"} >= {
            row["role"] for row in rows.values()
        }

    def test_every_model_input_matches_trade_baseline(self):
        rows = _transcribed_rows()
        inputs = {k: v for k, v in rows.items() if v["role"] == "model_input"}
        assert len(inputs) >= 15
        for key, row in inputs.items():
            assert key in TRADE_BASELINE, f"{key} is transcribed but not in TRADE_BASELINE"
            assert TRADE_BASELINE[key] == pytest.approx(float(row["value"]), rel=1e-9), (
                f"{key}: TRADE_BASELINE has {TRADE_BASELINE[key]}, "
                f"the CSV has {row['value']}"
            )

    def test_every_row_carries_a_source(self):
        for key, row in _transcribed_rows().items():
            assert row["source"].strip(), f"{key} has no source"
            assert row["url"].strip(), f"{key} has no url"

    def test_marginal_receipts_rate_reuses_the_app_constant(self):
        """Not a new constant: the app's own dynamic-scoring rate."""
        assert TRADE_BASELINE["marginal_receipts_rate"] == MARGINAL_REVENUE_RATE


class TestNoFittedConstants:
    """The two coverage constants fitted to benchmarks are gone."""

    def test_china_effective_coverage_is_deleted(self):
        assert "china_effective_coverage" not in TRADE_BASELINE

    def test_universal_coverage_is_the_usmca_carve_out(self):
        """1 minus the Canada + Mexico share of goods imports."""
        rows = _transcribed_rows()
        share = float(rows["usmca_partner_import_share"]["value"])
        assert TRADE_BASELINE["universal_coverage_rate"] == pytest.approx(
            1 - share, abs=5e-4
        )

    def test_china_preset_taxes_the_whole_base_at_the_incremental_rate(self):
        policy = create_trump_china_60()
        assert policy.import_base_billions == TRADE_BASELINE["china_imports_billions"]
        assert policy.tariff_rate_change == pytest.approx(
            0.60 - TRADE_BASELINE["china_existing_avg_tariff"]
        )

    def test_no_factory_overrides_the_frozen_elasticity(self):
        """One frozen, literature-sourced value per mechanism (plan section 4)."""
        for factory in FACTORIES:
            policy = factory()
            assert policy.import_elasticity == TRADE_BASELINE["import_price_elasticity"], (
                f"{policy.name} carries a per-case import elasticity"
            )

    def test_reciprocal_coverage_is_not_a_literal_in_the_factory(self):
        policy = create_reciprocal_tariffs()
        expected = (
            TRADE_BASELINE["total_imports_billions"]
            * TRADE_BASELINE["reciprocal_coverage_rate"]
        )
        assert policy.import_base_billions == pytest.approx(expected)

    def test_dead_shadow_copies_of_the_targets_are_gone(self):
        import fiscal_model.trade as trade

        assert not hasattr(trade, "CBO_TRADE_ESTIMATES")
        assert not hasattr(trade, "TRADE_VALIDATION_SCENARIOS")


class TestPassThrough:
    """Border pass-through drives demand; retail pass-through drives display."""

    def test_border_pass_through_is_frozen_at_one(self):
        assert TRADE_BASELINE["border_pass_through_rate"] == 1.00

    def test_retail_pass_through_is_a_separate_and_smaller_number(self):
        assert (
            TRADE_BASELINE["consumer_pass_through_rate"]
            < TRADE_BASELINE["border_pass_through_rate"]
        )

    def test_demand_response_uses_the_border_rate(self):
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        assert policy.import_price_change() == pytest.approx(0.10)
        expected = 1 + TRADE_BASELINE["import_price_elasticity"] * 0.10
        assert policy.import_volume_factor() == pytest.approx(expected)

    def test_halving_border_pass_through_softens_the_volume_response(self):
        full = TariffPolicy(
            name="Full",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
        )
        half = TariffPolicy(
            name="Half",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
            border_pass_through_rate=0.50,
        )
        assert half.import_volume_factor() > full.import_volume_factor()
        assert half.estimate_static_revenue_effect(0) > full.estimate_static_revenue_effect(0)

    def test_retail_pass_through_does_not_touch_the_score(self):
        base = TariffPolicy(
            name="Base",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
        )
        cheap = TariffPolicy(
            name="Cheap",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
            pass_through_rate=0.20,
        )
        assert cheap.estimate_static_revenue_effect(0) == base.estimate_static_revenue_effect(0)
        assert cheap.estimate_consumer_cost() < base.estimate_consumer_cost()


class TestNettingChain:
    """Avoidance, then the JCT offset, then retaliation. No double counting."""

    def test_chain_reproduces_the_documented_identity(self):
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.15,
            import_base_billions=800.0,
        )
        base = 800.0
        rate = 0.15
        volume = 1 + TRADE_BASELINE["import_price_elasticity"] * rate
        gross = base * volume * rate / (1 + rate)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        offset = (gross - avoidance) * TRADE_BASELINE["income_payroll_offset_rate"]
        retaliation = (
            TRADE_BASELINE["marginal_receipts_rate"]
            * TRADE_BASELINE["retaliation_rate"]
            * rate
            * policy.retaliation_export_base_billions
        )
        assert policy.estimate_static_revenue_effect(0) == pytest.approx(gross)
        assert policy.estimate_behavioral_offset(gross) == pytest.approx(
            avoidance + offset + retaliation
        )

    def test_the_offset_applies_to_gross_net_of_avoidance_only_once(self):
        """The JCT offset is a quarter of duty actually collected, not of gross."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        gross = policy.estimate_static_revenue_effect(0)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        assert policy.estimate_income_payroll_offset() == pytest.approx(
            (gross - avoidance) * TRADE_BASELINE["income_payroll_offset_rate"]
        )
        assert policy.estimate_income_payroll_offset() < gross * 0.25

    def test_tax_inclusive_rate_is_used(self):
        """base x volume x tau/(1+tau), not base x volume x tau."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.25,
            import_base_billions=1000.0,
        )
        exclusive = 1000.0 * policy.import_volume_factor() * 0.25
        assert policy.estimate_static_revenue_effect(0) == pytest.approx(exclusive / 1.25)

    def test_retaliation_can_be_switched_off_without_touching_the_rest(self):
        kwargs = dict(
            name="Test",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
        )
        with_retaliation = TariffPolicy(**kwargs)
        without = TariffPolicy(**kwargs, include_retaliation=False)
        gross = with_retaliation.estimate_static_revenue_effect(0)
        assert without.estimate_static_revenue_effect(0) == pytest.approx(gross)
        delta = (
            with_retaliation.estimate_behavioral_offset(gross)
            - without.estimate_behavioral_offset(gross)
        )
        assert delta == pytest.approx(with_retaliation.estimate_retaliation_revenue_loss())

    def test_offset_scales_with_a_phased_in_gross(self):
        """Half the gross duty nets down by half, retaliation included."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
        )
        gross = policy.estimate_static_revenue_effect(0)
        assert policy.estimate_behavioral_offset(gross / 2) == pytest.approx(
            policy.estimate_behavioral_offset(gross) / 2
        )

    def test_net_is_a_stable_share_of_gross_across_the_presets(self):
        """A netted score sits above the 40-50% band the knowledge base quotes.

        The band includes a GDP-feedback drag this module does not carry, so
        landing inside or below it would mean something is being counted twice.
        """
        for factory in FACTORIES:
            summary = factory().get_trade_summary()
            assert 0.50 < summary["net_to_gross_ratio"] < 0.75, factory.__name__

    def test_the_score_is_the_net_figure(self):
        policy = create_trump_universal_10()
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
        result = scorer.score_policy(policy, dynamic=False)
        annual_net = policy.get_trade_summary()["net_revenue"]
        assert result.total_10_year_cost == pytest.approx(-annual_net * 10, rel=1e-6)


class TestTariffCutSigns:
    """A tariff cut must have its cost eroded, not amplified.

``TaxPolicy.estimate_behavioral_offset``'s convention is that a behavioural
    offset carries the static effect's sign, because the scorer adds it to
    ``-static_revenue``.
    An unsigned offset made a 5pp tariff *cut* cost more than its own gross duty
    - the income and payroll bases were being shrunk by a tax that had just been
    reduced.
    """

    @staticmethod
    def _cut():
        return TariffPolicy(
            name="Tariff cut",
            description="Test",
            tariff_rate_change=-0.05,
            import_base_billions=1000.0,
        )

    def test_a_cut_loses_revenue(self):
        assert self._cut().estimate_static_revenue_effect(0) < 0

    def test_the_offset_carries_the_static_effect_sign(self):
        policy = self._cut()
        gross = policy.estimate_static_revenue_effect(0)
        assert policy.estimate_behavioral_offset(gross) < 0
        assert policy.estimate_income_payroll_offset() < 0

    def test_the_offset_erodes_the_cut_rather_than_amplifying_it(self):
        policy = self._cut()
        gross = policy.estimate_static_revenue_effect(0)
        result = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
            policy, dynamic=False
        )
        gross_cost = -gross * 10
        assert result.total_10_year_cost > 0, "a tariff cut widens the deficit"
        assert result.total_10_year_cost < gross_cost, (
            "the offset must shrink a cut's cost, not grow it"
        )

    def test_a_cut_invites_no_retaliation(self):
        policy = self._cut()
        assert policy.estimate_retaliation_cost() == 0.0
        assert policy.estimate_retaliation_revenue_loss() == 0.0

    def test_an_increase_still_erodes_in_the_other_direction(self):
        policy = TariffPolicy(
            name="Tariff rise",
            description="Test",
            tariff_rate_change=0.05,
            import_base_billions=1000.0,
        )
        gross = policy.estimate_static_revenue_effect(0)
        result = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
            policy, dynamic=False
        )
        assert policy.estimate_behavioral_offset(gross) > 0
        assert 0 > result.total_10_year_cost > -gross * 10


class TestRetaliationBase:
    """Partners retaliate in proportion to the harm, against a real base."""

    def test_country_targeted_policy_uses_exports_to_that_country(self):
        policy = create_trump_china_60()
        assert policy.retaliation_export_base_billions == pytest.approx(
            TRADE_BASELINE["us_exports_to_china_billions"]
        )

    def test_sectoral_policy_scales_with_its_share_of_imports(self):
        policy = create_steel_tariff_25()
        exposure = policy.import_base_billions / TRADE_BASELINE["total_imports_billions"]
        assert policy.retaliation_export_base_billions == pytest.approx(
            TRADE_BASELINE["total_exports_billions"] * exposure
        )

    def test_a_small_tariff_does_not_invite_retaliation_against_all_exports(self):
        policy = create_steel_tariff_25()
        assert (
            policy.retaliation_export_base_billions
            < TRADE_BASELINE["total_exports_billions"] * 0.05
        )
        assert policy.estimate_retaliation_cost() < policy.import_base_billions

    def test_receipts_loss_is_the_export_loss_at_the_marginal_rate(self):
        policy = create_reciprocal_tariffs()
        assert policy.estimate_retaliation_revenue_loss() == pytest.approx(
            policy.estimate_retaliation_cost() * MARGINAL_REVENUE_RATE
        )


class TestSection232Netting:
    """A proposed rate is incremental to the duty the base already pays."""

    def test_steel_nets_the_duty_actually_collected(self):
        policy = create_steel_tariff_25()
        assert policy.tariff_rate_change == pytest.approx(
            0.25 - TRADE_BASELINE["steel_aluminum_existing_avg_tariff"]
        )
        assert policy.tariff_rate_change < 0.25

    def test_auto_nets_the_duty_actually_collected(self):
        policy = create_auto_tariff_25()
        assert policy.tariff_rate_change == pytest.approx(
            0.25 - TRADE_BASELINE["auto_existing_avg_tariff"]
        )

    def test_collected_rates_are_below_their_statutory_rates(self):
        """Exemptions, quotas and duty-free entry mean collections run low.

        If these ever came back at or above the statutory Section 232 rates,
        the transcription would be measuring something other than duty paid.
        """
        assert 0.0 < TRADE_BASELINE["steel_aluminum_existing_avg_tariff"] < 0.25
        assert 0.0 < TRADE_BASELINE["auto_existing_avg_tariff"] < 0.025
        assert TRADE_BASELINE["china_existing_avg_tariff"] > (
            TRADE_BASELINE["current_avg_tariff_rate"]
        )


class TestTariffNoteOnTheScore:
    """Decision 6: the gross->net change ships with its user-facing note."""

    @staticmethod
    def _scored(factory):
        policy = factory()
        result = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
            policy, dynamic=False
        )
        return policy, result

    @pytest.mark.parametrize("factory", FACTORIES, ids=lambda f: f.__name__)
    def test_every_tariff_preset_explains_its_number(self, factory):
        policy, result = self._scored(factory)
        note = tariff_net_caption(policy, result)
        assert note, f"{policy.name} renders no note"
        assert "gross customs duty" in note
        assert "income-and-payroll offset" in note
        assert "retaliation" in note
        assert "net/gross ratio" in note

    def test_the_note_carries_the_scored_figures_not_a_restatement(self):
        policy, result = self._scored(create_trump_universal_10)
        note = tariff_net_caption(policy, result)
        gross = float(sum(result.static_revenue_effect))
        net = gross - float(sum(result.behavioral_offset))
        assert f"{gross:,.1f}B" in note
        assert f"{net:,.1f}B" in note
        assert f"{net / gross:.2f}" in note
        # And the net figure in the note is the headline the user reads.
        assert net == pytest.approx(-result.total_10_year_cost, rel=1e-9)

    def test_a_no_retaliation_score_does_not_claim_a_retaliation_channel(self):
        policy = TariffPolicy(
            name="Conventional",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            include_retaliation=False,
        )
        result = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
            policy, dynamic=False
        )
        note = tariff_net_caption(policy, result)
        assert "income-and-payroll offset" in note
        assert "retaliation" not in note

    def test_a_non_tariff_policy_renders_no_tariff_note(self):
        from fiscal_model.policies import PolicyType, TaxPolicy

        policy = TaxPolicy(
            name="Custom rate",
            description="+2pp above $400,000",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=400_000,
        )
        result = FiscalPolicyScorer(use_real_data=False).score_policy(policy, dynamic=False)
        assert tariff_net_caption(policy, result) == ""

    def test_the_headline_block_renders_the_note(self):
        from components.results import ScoredResult
        from fiscal_model.app_data import CBO_SCORE_MAP
        from fiscal_model.ui.tabs.results_summary import render_headline_block

        policy, result = self._scored(create_trump_universal_10)
        data = {"policy": policy, "result": result}
        scored = ScoredResult.from_pipeline(
            result_data=data,
            policy_spec_hash="tariff-net-note",
            dynamic_scoring=False,
            dynamic_view=None,
            cbo_score_map=CBO_SCORE_MAP,
            baseline_vintage="CBO Feb 2026",
        )
        st = _FakeStreamlit()
        render_headline_block(st, scored, data)
        assert any("Net of offsets:" in caption for caption in st.captions), st.captions
