"""
Tests for ``policy_to_microsim_reforms``.

This mapping is what makes the TPC-Microsim pilot reachable from the
multi-model platform. Each supported policy type should produce a
non-empty reform dict; unsupported types return empty and the pilot
raises a descriptive error.
"""

from __future__ import annotations

import pytest

from fiscal_model.corporate import create_biden_corporate_rate_only
from fiscal_model.credits import create_biden_ctc_2021
from fiscal_model.distribution_effects import policy_to_microsim_reforms
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.tax_expenditures import create_repeal_salt_cap


def test_tax_policy_with_rate_change_produces_top_rate_reform():
    policy = TaxPolicy(
        name="Top rate +2.6pp",
        description="",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.026,
    )
    reforms = policy_to_microsim_reforms(policy)
    assert "new_top_rate" in reforms
    assert reforms["new_top_rate"] == pytest.approx(0.37 + 0.026)


def test_tax_policy_with_threshold_maps_to_threshold_rate_adjustment():
    policy = TaxPolicy(
        name="High-income rate +2.6pp",
        description="",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.026,
        affected_income_threshold=400_000,
    )

    reforms = policy_to_microsim_reforms(policy)

    assert "new_top_rate" not in reforms
    assert reforms["income_rate_change"] == pytest.approx(0.026)
    assert reforms["income_rate_change_threshold"] == pytest.approx(400_000)


def test_tax_policy_with_zero_rate_produces_no_reform():
    policy = TaxPolicy(
        name="No change",
        description="",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.0,
    )
    assert policy_to_microsim_reforms(policy) == {}


def test_biden_ctc_2021_maps_to_ctc_amount_and_refundable_flag():
    reforms = policy_to_microsim_reforms(create_biden_ctc_2021())
    assert reforms["ctc_amount"] > 2000  # base CTC + expansion
    assert reforms["ctc_fully_refundable"] is True


def test_salt_repeal_maps_to_none_cap():
    reforms = policy_to_microsim_reforms(create_repeal_salt_cap())
    assert reforms["salt_cap"] is None  # None = no cap at all


def test_corporate_policy_returns_empty():
    """Corporate tax is firm-level; microsim pilot cannot represent it."""
    reforms = policy_to_microsim_reforms(create_biden_corporate_rate_only())
    assert reforms == {}


def test_biden_eitc_childless_maps_to_the_childless_schedule_only():
    """A childless expansion must not scale the with-children maxima.

    The bridge used to return ``eitc_expansion = 1500 / 632`` — a single
    multiplier applied to all four child counts, so a reform that leaves the
    three-child maximum untouched was modelled as raising it by 137%. The
    childless keys move the childless schedule and nothing else.
    """
    from fiscal_model.credits import create_biden_eitc_childless

    reforms = policy_to_microsim_reforms(create_biden_eitc_childless())
    assert "eitc_expansion" not in reforms
    assert reforms["eitc_childless_max_credit"] == pytest.approx(1500.0)
    assert reforms["eitc_childless_phasein_rate"] == pytest.approx(0.153)
    assert reforms["eitc_childless_phaseout_rate"] == pytest.approx(0.153)
    # The age expansion the description always claimed and the code never made.
    assert reforms["eitc_childless_min_age"] == 19
    assert reforms["eitc_childless_max_age"] > 65


def test_arp_ctc_maps_to_the_two_tier_design():
    """ARPA sec. 9611's structure, not a flat credit at one threshold."""
    from fiscal_model.credits import create_biden_ctc_2021

    reforms = policy_to_microsim_reforms(create_biden_ctc_2021())
    assert reforms["ctc_amount_under_6"] == pytest.approx(3600.0)
    assert reforms["ctc_amount"] == pytest.approx(3000.0)
    assert reforms["ctc_qualifying_age"] == 18
    assert reforms["ctc_protected_amount"] == pytest.approx(2000.0)
    # The increment phases from $75k/$150k; the $2,000 base keeps $200k/$400k.
    assert reforms["ctc_phaseout_start_low_single"] == pytest.approx(75_000.0)
    assert reforms["ctc_phaseout_start_single"] == pytest.approx(200_000.0)


def test_post_sunset_credit_policy_is_not_representable():
    """A counterfactual the microsim baseline cannot express returns ``{}``.

    Extending the $2,000 CTC is scored against the post-2025 sunset. The
    microsim distributional path always computes its baseline leg from the
    engine's current-law defaults, so handing it this reform would report no
    change at all. An empty dict routes it to the synthetic path instead.
    """
    from fiscal_model.credits import create_ctc_permanent_extension

    assert policy_to_microsim_reforms(create_ctc_permanent_extension()) == {}


def test_arp_recovery_rebate_maps_to_the_per_person_rebate():
    from fiscal_model.credits import create_arp_recovery_rebate

    reforms = policy_to_microsim_reforms(create_arp_recovery_rebate())
    assert reforms["rebate_per_person"] == pytest.approx(1400.0)
    assert reforms["rebate_phaseout_start_single"] == pytest.approx(75_000.0)
    assert reforms["rebate_phaseout_end_single"] == pytest.approx(80_000.0)
    assert reforms["rebate_phaseout_end_married"] == pytest.approx(160_000.0)
