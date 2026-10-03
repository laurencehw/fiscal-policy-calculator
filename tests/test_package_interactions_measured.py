"""CPS-microsim measurements behind the Build page's interaction disclosure.

Every figure here is a **share** of a member's own standalone yield. The
microsim's levels are not on the scale of the Build page's list prices, which
is why :class:`InteractionMeasurement` exposes dollars only for audit and the
page prints only the share.

Reform dicts for the exactness cases are written out by hand where
``policy_to_microsim_reforms`` returns ``{}`` for the shipped preset (the CTC
extension is priced against a sunset baseline, which the microsim's current-law
baseline cannot express).
"""

from __future__ import annotations

import pytest

from fiscal_model import package_interactions as pi
from fiscal_model.package_interactions import (
    ReformClashError,
    measure_reforms,
    measured_interaction_share,
    merge_reforms,
)

RATE_400K = {"income_rate_change": 0.026, "income_rate_change_threshold": 400_000.0}
SURTAX_1M = {"income_rate_change": 0.05, "income_rate_change_threshold": 1_000_000.0}
SALT_REPEAL = {"salt_cap": None}
AMT_PLUS = {"amt_exemption_adjustment": 100_000.0}
STD_PLUS = {"std_deduction_bonus": 10_000}
CTC_3K = {"ctc_amount": 3_000.0}
EITC_CHILDLESS = {
    "eitc_childless_max_credit": 1_500.0,
    "eitc_childless_phasein_rate": 0.153,
    "eitc_childless_phaseout_rate": 0.153,
}


# ---------------------------------------------------------------------------
# Exact additivity
# ---------------------------------------------------------------------------


def test_two_overlapping_rate_policies_are_exactly_additive():
    m = measure_reforms("a-rate", RATE_400K, "b-surtax", SURTAX_1M)
    assert m is not None
    assert abs(m.interaction) < 1e-9
    assert m.standalone_a != 0 and m.standalone_b != 0


def test_ctc_and_eitc_are_exactly_additive():
    m = measure_reforms("a-ctc", CTC_3K, "b-eitc", EITC_CHILDLESS)
    assert m is not None
    assert abs(m.interaction) < 1e-9


@pytest.mark.parametrize("other", [AMT_PLUS, CTC_3K, EITC_CHILDLESS])
def test_rate_changes_are_additive_by_construction_with_amt_and_credits(other):
    # True because apply_reform adds the rate change after calculate() -- a fact
    # about the code. The classifier labels these "structurally additive" and
    # never "measured zero"; this test is the evidence the label is not wrong.
    m = measure_reforms("a-rate", RATE_400K, "b-other", other)
    assert m is not None and abs(m.interaction) < 1e-9


# ---------------------------------------------------------------------------
# The interactions that matter
# ---------------------------------------------------------------------------


def test_salt_repeal_with_the_top_rate_item_is_negative_and_in_a_sane_band():
    m = measured_interaction_share("top-rate-39-6", "salt-cap-repeal")
    assert m is not None
    assert m.interaction < 0
    assert m.reference == "top-rate-39-6"  # the rate item
    assert m.share is not None and -0.30 < m.share < -0.05
    # SALT repeal costs revenue and the rate item raises it, so the sum of the
    # two overstates the joint revenue: the rate item yields less once SALT is
    # uncapped (fewer high earners' taxable income is what the rate multiplies).
    assert m.standalone_a < 0 < m.standalone_b or m.standalone_b < 0 < m.standalone_a


def test_a_surtax_above_one_million_loses_about_a_fifth_to_salt_repeal():
    m = measure_reforms("a-surtax", SURTAX_1M, "b-salt", SALT_REPEAL)
    assert m is not None
    assert m.share is not None and -0.35 < m.share < -0.10
    # The sum of the parts and the joint score have opposite signs here.
    parts = m.standalone_a + m.standalone_b
    assert parts > 0 > m.joint


@pytest.mark.parametrize(
    "pair",
    [(SALT_REPEAL, AMT_PLUS), (SALT_REPEAL, STD_PLUS), (STD_PLUS, AMT_PLUS)],
)
def test_deduction_and_amt_exemption_changes_do_not_add(pair):
    m = measure_reforms("a", pair[0], "b", pair[1])
    assert m is not None and abs(m.interaction) > 0.1


# ---------------------------------------------------------------------------
# Symmetry, caching, refusal
# ---------------------------------------------------------------------------


def test_measurement_is_symmetric_in_its_arguments():
    ab = measured_interaction_share("top-rate-39-6", "salt-cap-repeal")
    ba = measured_interaction_share("salt-cap-repeal", "top-rate-39-6")
    assert ab == ba
    assert pi._measured_sorted.cache_info().hits >= 1
    flipped = measure_reforms("b-salt", SALT_REPEAL, "a-rate", RATE_400K)
    straight = measure_reforms("a-rate", RATE_400K, "b-salt", SALT_REPEAL)
    assert flipped == straight


def test_same_key_clashes_are_refused_not_silently_overridden():
    assert measure_reforms("a", SALT_REPEAL, "b", {"salt_cap": 5_000}) is None
    assert measure_reforms("a", STD_PLUS, "b", {"std_deduction_bonus": 5_000}) is None
    assert measure_reforms("a", AMT_PLUS, "b", AMT_PLUS) is None
    assert measure_reforms("a", {"new_top_rate": 0.4}, "b", {"new_top_rate": 0.45}) is None
    with pytest.raises(ReformClashError):
        merge_reforms([SALT_REPEAL, {"salt_cap": 5_000}])


def test_two_reforms_of_one_instrument_family_clash_even_with_different_keys():
    # ctc_amount sets the under-6 and protected amounts too; a later
    # ctc_amount_under_6 would silently win over it.
    with pytest.raises(ReformClashError):
        merge_reforms([CTC_3K, {"ctc_amount_under_6": 2_500.0}])
    # ...but different instruments, and rate tranches, compose.
    merged, extra = merge_reforms([CTC_3K, EITC_CHILDLESS, RATE_400K, SURTAX_1M])
    assert merged["income_rate_change"] == 0.026 and extra == [(1_000_000.0, 0.05)]


def test_merge_is_order_invariant():
    forward = merge_reforms([RATE_400K, SURTAX_1M, SALT_REPEAL])
    backward = merge_reforms([SALT_REPEAL, SURTAX_1M, RATE_400K])
    assert forward == backward


def test_no_microsim_reform_means_no_measurement():
    assert measure_reforms("a", {}, "b", SALT_REPEAL) is None
    assert measured_interaction_share("corporate-28pct", "top-rate-39-6") is None
    assert measured_interaction_share("top-rate-39-6", "top-rate-39-6") is None


def test_measure_package_measures_only_interacting_measurable_pairs():
    found = pi.measure_package(["top-rate-39-6", "salt-cap-repeal", "corporate-28pct"])
    assert set(found) == {("salt-cap-repeal", "top-rate-39-6")}


def test_salt_repeal_and_a_childless_eitc_measure_as_zero():
    # The classifier says "no overlap" for this pair; here is the evidence.
    m = measured_interaction_share("eitc-childless-expansion", "salt-cap-repeal")
    assert m is not None and abs(m.interaction) < 1e-9


def test_a_measured_report_upgrades_the_status_and_states_the_share():
    selection = ["top-rate-39-6", "salt-cap-repeal"]
    measurements = pi.measure_package(selection)
    report = pi.classify_package(selection, measurements=measurements)
    assert report.status == "interacting_measured"
    (finding,) = report.measurable
    sentence = pi.describe_measurement(report, finding)
    assert "approximate" in sentence and "share and not a dollar figure" in sentence
    assert "$" not in sentence  # shares only: the levels are not list-price scale
    assert "lower than the two alone sum to" in sentence
