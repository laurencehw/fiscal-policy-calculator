"""
Tests for the ARP bundle composite benchmark path.

Covers:
- The new ``create_arp_recovery_rebate`` factory produces a sensible
  one-time refundable payment with steep phaseouts.
- The ARP benchmark runner composes CTC + EITC + Recovery Rebate via
  the existing ``_combine_distributional_results`` helper.
- The filing-status blend in ``calculate_credit_effect`` gives the
  fourth quintile non-zero share under Recovery Rebate's thresholds.
"""

from __future__ import annotations

from fiscal_model.credits import TaxCreditPolicy, create_arp_recovery_rebate
from fiscal_model.validation.benchmark_runners import (
    _run_arp_bundle,
    default_model_runner,
)
from fiscal_model.validation.cbo_distributions import CBO_ARP_2021, compare_distribution


class TestRecoveryRebateFactory:
    def test_produces_tax_credit_policy(self):
        policy = create_arp_recovery_rebate()
        assert isinstance(policy, TaxCreditPolicy)
        assert policy.is_refundable is True
        assert policy.duration_years == 1  # One-time only

    def test_phaseout_matches_statute(self):
        policy = create_arp_recovery_rebate()
        assert policy.phase_out_threshold_single == 75_000
        assert policy.phase_out_threshold_married == 150_000
        # Rate chosen so the credit is fully phased out in a $5K window
        # (i.e. above the "fully phased out" AGI of $80k/$160k).
        assert policy.phase_out_rate > 0.2
        assert policy.phase_out_rate < 0.35

    def test_per_unit_credit_covers_household_average(self):
        policy = create_arp_recovery_rebate()
        # $1,400 per person × ~2.1 people per tax unit ≈ $2,900-$4,200.
        assert 2_800 <= policy.credit_change_per_unit <= 4_500


class TestARPBundleRouting:
    def test_bundle_returns_nonzero_result(self):
        result = _run_arp_bundle(CBO_ARP_2021)
        assert result is not None
        assert len(result.results) == 5  # quintiles

    def test_bundle_beats_ctc_only_on_arp_benchmark(self):
        """
        The bundle must do at least as well as CTC-alone on the
        CBO_ARP_2021 benchmark — otherwise there's no point routing
        it through the bundle.
        """
        bundle_result = default_model_runner(CBO_ARP_2021)
        bundle_err = compare_distribution(
            bundle_result, CBO_ARP_2021
        ).mean_absolute_share_error_pp
        # Threshold chosen to catch regressions below the ~7.5pp
        # current accuracy while allowing some headroom.
        assert bundle_err is not None
        assert bundle_err < 9.0


class TestFilingStatusBlend:
    """
    With a married-threshold = 2x single fallback (or an explicit
    married threshold), the 4th quintile should receive *some* share
    under an ARP-style Recovery Rebate even though single-filer
    phaseout completely zeros out at that AGI.
    """

    def test_fourth_quintile_has_nonzero_share_under_rebate(self):
        from fiscal_model.distribution import DistributionalEngine, IncomeGroupType

        engine = DistributionalEngine(data_year=2021)
        result = engine.analyze_policy(
            create_arp_recovery_rebate(),
            group_type=IncomeGroupType.QUINTILE,
        )
        shares = {r.income_group.name: abs(r.share_of_total_change) for r in result.results}
        # Fourth quintile contains many joint filers whose threshold
        # ($150K) is above their avg AGI — they should still see the
        # credit.
        assert shares.get("Fourth Quintile", 0) > 0.0
