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
