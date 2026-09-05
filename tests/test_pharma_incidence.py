"""Pharma incidence — who actually bears a drug-pricing change.

Lanes L7 (Wave 1) and W4-pharma of ``planning/MODELING_IMPROVEMENT.md``. These
tests pin the properties the drug-pricing module used to get wrong, and the
transcription its parameters come from:

1. A **cost-sharing cap** moves a dollar from a patient to a plan. It cannot be
   a federal saving, and extending it to private insurance cannot make the
   federal saving *larger* — which is what the pre-L7 implementation did. That
   holds for the Part D annual out-of-pocket cap as much as for insulin.
2. A **price cap** binds on brand molecules, at net prices, on the share of the
   brand book that has a foreign price to be referenced against, and the federal
   budget gets only its share of the reduction.
3. **The federal share is three channels**, and the IRA's 2025 Part D redesign
   moved cost between them. A single 2023 aggregate is a weight for a benefit
   design that no longer exists.
4. **Negotiation savings are not linear in drug count.** CMS's three selection
   cycles are a measured concentration curve, and the marginal molecule is worth
   a fraction of the first.

Nothing here asserts a validation benchmark. The three pharma reconstruction
rows are scored by ``fiscal_model/validation/specialized_sectoral.py`` against
targets no constant in this module is fitted to, two of which are provenance
``model_estimate``. Asserting a percentage error here would turn a benchmark
into an answer key. Where a *published CBO score of a different policy* is
available as a cross-check — the negotiation program's own ten-year figure —
it is asserted only as an order of magnitude, and it is not a target of
anything this module scores.
"""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path

import pytest

from fiscal_model import pharma
from fiscal_model.enforcement import ENFORCEMENT_BASELINE
from fiscal_model.pharma import (
    IRA_SELECTION_SCHEDULE,
    PHARMA_BASELINE,
    DrugPricingPolicy,
    DrugPricingReformType,
    create_comprehensive_pharma_reform,
    create_expand_drug_negotiation,
    create_insulin_cap_all,
    create_reference_pricing,
    current_law_negotiated_molecules,
    negotiated_gross_spending,
    negotiation_availability_response,
    negotiation_spending_ladder,
    part_d_federal_channels,
    part_d_federal_share,
    reference_pricing_availability_response,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer

TRANSCRIPTION = (
    Path(__file__).resolve().parents[1]
    / "fiscal_model"
    / "data_files"
    / "pharma"
    / "drug_pricing_incidence.csv"
)


def _insulin_cap(monthly: float | None, *, extend_to_private: bool) -> DrugPricingPolicy:
    return DrugPricingPolicy(
        name="Insulin cap",
        description="Insulin cost-sharing cap",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.INSULIN_CAP,
        insulin_cap_monthly=monthly,
        extend_to_private=extend_to_private,
    )


def _oop_cap(cap: float | None) -> DrugPricingPolicy:
    return DrugPricingPolicy(
        name="Part D out-of-pocket cap",
        description="Annual out-of-pocket cap",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.PART_D_REDESIGN,
        oop_cap=cap,
    )


def _score_10yr(policy: DrugPricingPolicy) -> float:
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    return scorer.score_policy(policy, dynamic=False).total_10_year_cost


# ---------------------------------------------------------------------------
# 1. The insulin cost-sharing cap
# ---------------------------------------------------------------------------


def test_insulin_cost_sharing_cap_widens_the_deficit():
    """A $35 cap is a cost shift onto plans, so it costs the federal budget.

    CBO scores the same policy at about +$11.4B over FY2022-2031 (publication
    57957: +$6.566B of outlays, -$4.793B of revenues). The direction is the
    claim; the level is not asserted.
    """
    assert _score_10yr(create_insulin_cap_all()) > 0


def test_extending_the_cap_to_private_plans_does_not_enlarge_a_federal_saving():
    """The bug lane L7 existed to kill.

    ``extend_to_private=True`` used to set ``medicare_share = 1.0``, multiplying
    the modelled federal saving by 2.5. Extending a cap to private insurance
    reaches the federal budget only through the tax exclusion for employer
    premiums, so it can only add a *small cost* on top of the Medicare channel.
    """
    medicare_only = _score_10yr(_insulin_cap(35.0, extend_to_private=False))
    with_private = _score_10yr(_insulin_cap(35.0, extend_to_private=True))

    assert medicare_only > 0
    assert with_private > medicare_only
    # The private increment runs through a 32% tax offset on a smaller
    # population, so it must stay well below the Medicare channel it sits on.
    assert (with_private - medicare_only) < 0.5 * medicare_only


def test_medicare_channel_is_the_published_shift_times_the_subsidy_share():
    """Part D channel = ASPE's $734M shift x Medicare's 74.5% subsidy share.

    Pinned exactly, because it is the whole mechanism: no availability response
    is applied to a cost-sharing cap, since it does not change what a
    manufacturer is paid.
    """
    policy = _insulin_cap(35.0, extend_to_private=False)
    expected_annual = (
        PHARMA_BASELINE["insulin_cap_reference_part_d_oop_relief_billions"]
        * PHARMA_BASELINE["part_d_basic_benefit_federal_share"]
    )
    assert policy.estimate_cost_effect(0.0) == pytest.approx(expected_annual)


def test_a_cap_above_the_average_out_of_pocket_cost_per_fill_shifts_nothing():
    """$63 is ASPE's average out-of-pocket cost per insulin fill."""
    ceiling = PHARMA_BASELINE["insulin_oop_per_fill_dollars"]
    assert _insulin_cap(ceiling, extend_to_private=True).estimate_cost_effect(0.0) == 0.0
    assert (
        _insulin_cap(ceiling + 10, extend_to_private=True).estimate_cost_effect(0.0) == 0.0
    )


def test_a_tighter_cap_shifts_more_cost_than_a_looser_one():
    tight = _insulin_cap(10.0, extend_to_private=False).estimate_cost_effect(0.0)
    loose = _insulin_cap(50.0, extend_to_private=False).estimate_cost_effect(0.0)
    assert tight > loose > 0


def test_no_insulin_cap_means_no_insulin_effect():
    assert _insulin_cap(None, extend_to_private=True).estimate_cost_effect(0.0) == 0.0


def test_the_insulin_channel_did_not_move_when_the_part_d_channels_were_built():
    """Lane W4 re-weighted the federal share of a *drug-cost* reduction.

    A cost-sharing cap reduces no drug cost — it converts beneficiary liability
    into plan liability, which is subsidised at the statutory 74.5%. So the
    insulin channel must be untouched by the three-channel work, and this test
    fails if a future change routes it through ``part_d_federal_share()``.
    """
    assert PHARMA_BASELINE["part_d_basic_benefit_federal_share"] != pytest.approx(
        part_d_federal_share()
    )
    assert _score_10yr(create_insulin_cap_all()) == pytest.approx(6.96, abs=0.05)


# ---------------------------------------------------------------------------
# 2. The Part D annual out-of-pocket cap
# ---------------------------------------------------------------------------


def test_an_out_of_pocket_cap_widens_the_deficit():
    """Same incidence as the insulin cap, one benefit phase up."""
    assert _score_10yr(_oop_cap(2000.0)) > 0


def test_the_out_of_pocket_cap_is_aspes_published_shift_times_the_subsidy_share():
    expected = (
        PHARMA_BASELINE["part_d_oop_cap_reference_relief_billions"]
        * PHARMA_BASELINE["part_d_basic_benefit_federal_share"]
    )
    assert _oop_cap(2000.0).estimate_cost_effect(0.0) == pytest.approx(expected)


def test_the_out_of_pocket_cap_interpolates_between_aspes_two_published_points():
    """$0 shifts all $14.3B; $2,000 shifts $7.2B; nothing in between is invented."""
    subsidy = PHARMA_BASELINE["part_d_basic_benefit_federal_share"]
    at_zero = _oop_cap(0.0).estimate_cost_effect(0.0)
    at_half = _oop_cap(1000.0).estimate_cost_effect(0.0)
    at_reference = _oop_cap(2000.0).estimate_cost_effect(0.0)

    assert at_zero == pytest.approx(
        PHARMA_BASELINE["part_d_oop_cap_baseline_out_of_pocket_billions"] * subsidy
    )
    assert at_half == pytest.approx((at_zero + at_reference) / 2)
    assert at_zero > at_half > at_reference > 0


def test_the_out_of_pocket_cap_refuses_to_extrapolate_above_its_source():
    """ASPE priced a $2,000 cap. Above it the module claims nothing."""
    assert _oop_cap(2500.0).estimate_cost_effect(0.0) == 0.0
    assert _oop_cap(None).estimate_cost_effect(0.0) == 0.0


def test_the_out_of_pocket_cap_is_the_right_order_of_magnitude_against_cbo():
    """CBO scored the whole Part D redesign at +$30B over FY2022-2031.

    The lever is one piece of that redesign — the cap, without the reinsurance
    cut or the manufacturer discount program that offset it — so it must sit
    above CBO's net without being a different quantity altogether. Asserted as a
    band, never as a target: nothing in this module is fitted to it.
    """
    ten_year = _score_10yr(_oop_cap(2000.0))
    assert 30.0 < ten_year < 120.0


# ---------------------------------------------------------------------------
# 3. The three Part D federal channels
# ---------------------------------------------------------------------------


def test_the_federal_share_is_three_named_channels():
    channels = part_d_federal_channels()
    assert set(channels) == {"direct_subsidy", "reinsurance", "low_income_subsidy"}
    assert all(value > 0 for value in channels.values())
    assert part_d_federal_share() == pytest.approx(sum(channels.values()))


def test_the_channels_and_the_non_federal_blocks_account_for_every_dollar():
    """The decomposition partitions MedPAC's $147.0B universe exactly."""
    base = PHARMA_BASELINE
    universe = (
        base["part_d_direct_subsidy_billions_2023"]
        + base["part_d_reinsurance_billions_2023"]
        + base["part_d_low_income_subsidy_billions_2023"]
        + base["part_d_enrollee_premiums_billions_2023"]
        + base["part_d_enrollee_cost_sharing_billions_2023"]
    )
    basic_block = (
        base["part_d_direct_subsidy_billions_2023"]
        + base["part_d_reinsurance_billions_2023"]
        + base["part_d_enrollee_premiums_billions_2023"]
    ) / universe
    premium_share = base["part_d_base_beneficiary_premium_2025"] / (
        base["part_d_direct_subsidy_pmpm_2025"]
        + base["part_d_reinsurance_pmpm_2025"]
        + base["part_d_base_beneficiary_premium_2025"]
    )
    non_federal = (
        basic_block * premium_share
        + base["part_d_enrollee_cost_sharing_billions_2023"] / universe
    )
    assert part_d_federal_share() + non_federal == pytest.approx(1.0)


def test_the_redesign_moves_cost_from_reinsurance_to_the_direct_subsidy():
    """The finding the three channels exist to expose.

    In 2023 reinsurance was over 90% of Medicare's basic-benefit payments. Under
    the 2025 design the direct subsidy is the larger channel by a wide margin,
    while the federal *total* barely moves — the 6% cap on the base beneficiary
    premium raises the direct subsidy by nearly what reinsurance loses.
    """
    base = PHARMA_BASELINE
    universe = (
        base["part_d_direct_subsidy_billions_2023"]
        + base["part_d_reinsurance_billions_2023"]
        + base["part_d_low_income_subsidy_billions_2023"]
        + base["part_d_enrollee_premiums_billions_2023"]
        + base["part_d_enrollee_cost_sharing_billions_2023"]
    )
    reinsurance_2023 = base["part_d_reinsurance_billions_2023"] / universe
    channels = part_d_federal_channels()

    assert channels["reinsurance"] < reinsurance_2023 / 3
    assert channels["direct_subsidy"] > 5 * (
        base["part_d_direct_subsidy_billions_2023"] / universe
    )
    federal_2023 = (
        base["part_d_direct_subsidy_billions_2023"]
        + base["part_d_reinsurance_billions_2023"]
        + base["part_d_low_income_subsidy_billions_2023"]
    ) / universe
    assert abs(part_d_federal_share() - federal_2023) < 0.03


# ---------------------------------------------------------------------------
# 4. Medicare drug price negotiation
# ---------------------------------------------------------------------------


def test_the_ladder_reproduces_every_cms_selection_cycle():
    """Three published cycles, one two-parameter curve, no free constant left."""
    base = PHARMA_BASELINE
    scale, exponent = negotiation_spending_ladder()
    cycles = (
        (5.5, base["negotiation_cycle1_gross_billions"] / base["negotiation_cycle1_drugs"]),
        (18.0, base["negotiation_cycle2_gross_billions"] / base["negotiation_cycle2_drugs"]),
        (33.0, base["negotiation_cycle3_gross_billions"] / base["negotiation_cycle3_drugs"]),
    )
    for rank, observed in cycles:
        assert scale * rank ** -exponent == pytest.approx(observed, rel=0.03)
    # Downward sloping: the marginal molecule gets cheaper, which is the whole
    # point of replacing the old constant per-drug average.
    assert 0.3 < exponent < 1.0


def test_the_negotiated_set_never_exceeds_total_part_d_gross_spending():
    """The consistency check that forced the $220B base to be re-sourced."""
    latest = current_law_negotiated_molecules(2034)
    assert latest == 160
    assert (
        negotiated_gross_spending(latest)
        < PHARMA_BASELINE["medicare_part_d_gross_spending_billions"]
    )


def test_current_law_is_a_cumulative_schedule_not_twenty_drugs():
    """The IRA selects 10 / +15 / +15 / +20 a year, so the set compounds."""
    assert current_law_negotiated_molecules(2025) == 0
    assert current_law_negotiated_molecules(2026) == IRA_SELECTION_SCHEDULE[2026]
    assert current_law_negotiated_molecules(2027) == 25
    assert current_law_negotiated_molecules(2028) == 40
    assert current_law_negotiated_molecules(2029) == 60


def test_current_law_scores_in_cbos_neighbourhood_for_the_negotiation_program():
    """The cross-check that matters, on a policy CBO actually scored.

    CBO put the IRA's negotiation program at about $98.5B over FY2022-2031 (the
    $237B often quoted is the whole drug-pricing title). Running this identity
    over current law's own schedule has to land in that neighbourhood, or the
    ladder and the saving rate are wrong. Asserted as a band; no constant here
    is fitted to it.
    """
    rate = (
        PHARMA_BASELINE["negotiation_cycle1_saving_billions"]
        / PHARMA_BASELINE["negotiation_cycle1_gross_billions"]
    )
    federal = part_d_federal_share()
    through_2031 = sum(
        negotiated_gross_spending(current_law_negotiated_molecules(year)) * rate * federal
        for year in range(2026, 2032)
    )
    assert 50.0 < through_2031 < 200.0


def test_expanding_the_count_without_lifting_the_eligibility_bar_scores_nothing():
    """A statutory cap on selections is not raised by wanting more of them."""
    blocked = DrugPricingPolicy(
        name="More drugs, same eligibility",
        description="50 a year, exclusivity delay intact",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.MEDICARE_NEGOTIATION,
        expand_negotiation=True,
        negotiation_drug_count=50,
        remove_exclusivity_delay=False,
    )
    assert blocked.estimate_cost_effect(0.0) == pytest.approx(0.0)
    assert _score_10yr(create_expand_drug_negotiation()) < 0


def test_negotiation_savings_are_concave_in_the_number_of_molecules():
    """Equal increments to the annual selection rate buy less each time.

    The old identity was linear in drug count, so the twentieth extra molecule a
    year was worth exactly as much as the first. On CMS's own ladder it is not:
    each further block of twenty runs further down the spending curve.
    """

    def saving(count: int) -> float:
        return -DrugPricingPolicy(
            name=f"{count} a year",
            description="expansion",
            policy_type=PolicyType.MANDATORY_SPENDING,
            reform_type=DrugPricingReformType.MEDICARE_NEGOTIATION,
            expand_negotiation=True,
            negotiation_drug_count=count,
            remove_exclusivity_delay=True,
        ).estimate_cost_effect(0.0)

    first_twenty = saving(40) - saving(20)
    second_twenty = saving(60) - saving(40)
    third_twenty = saving(80) - saving(60)

    assert saving(20) == pytest.approx(0.0)
    assert first_twenty > second_twenty > third_twenty > 0


def test_no_expansion_means_no_negotiation_effect():
    unchanged = DrugPricingPolicy(
        name="Current law",
        description="no expansion",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.MEDICARE_NEGOTIATION,
    )
    assert unchanged.estimate_cost_effect(0.0) == 0.0


# ---------------------------------------------------------------------------
# 5. The drug availability response
# ---------------------------------------------------------------------------


def test_the_availability_responses_are_cbos_own_ratios():
    base = PHARMA_BASELINE
    assert negotiation_availability_response() == pytest.approx(
        base["cbo_ira_fewer_drugs_first_decade"] / (base["cbo_thirty_year_new_drugs"] / 3)
    )
    assert reference_pricing_availability_response() == pytest.approx(
        base["cbo_hr3_fewer_drugs_first_decade"] / base["cbo_hr3_first_decade_new_drugs"]
    )
    # CBO's two figures are an order of magnitude apart, which is why the single
    # unsourced 5% that used to serve both was wrong for both.
    assert (
        reference_pricing_availability_response()
        > 10 * negotiation_availability_response()
    )


def test_an_explicit_offset_overrides_both_channels():
    policy = create_reference_pricing()
    default = -policy.estimate_cost_effect(0.0)
    policy.innovation_offset_pct = 0.0
    assert -policy.estimate_cost_effect(0.0) > default


# ---------------------------------------------------------------------------
# 6. International reference pricing
# ---------------------------------------------------------------------------


def test_reference_pricing_saves_less_than_the_whole_medicare_drug_base():
    """Generics, rebates, unmatched molecules and the beneficiary share are all
    outside the saving.

    The pre-L7 identity applied the price cut to every dollar of Part B + Part D
    spending. Brand-only, rebate-netted, coverage-restricted, federal-share
    scoring has to come in strictly below that — and by a wide margin, since the
    haircuts compound.
    """
    base = PHARMA_BASELINE
    policy = create_reference_pricing()
    price_reduction = 1 - (
        policy.reference_price_target_pct / base["brand_price_ratio_to_intl_net"]
    )
    whole_base_saving = (
        base["medicare_part_d_gross_spending_billions"]
        + base["medicare_part_b_drugs_billions"]
    ) * price_reduction

    saving = -policy.estimate_cost_effect(0.0)
    assert 0 < saving < 0.6 * whole_base_saving


def test_reference_pricing_matches_the_brand_net_coverage_federal_share_identity():
    base = PHARMA_BASELINE
    policy = create_reference_pricing()
    price_reduction = 1 - (
        policy.reference_price_target_pct / base["brand_price_ratio_to_intl_net"]
    )
    coverage = (
        base["rand_us_sales_share_in_comparison"]
        * base["rand_brand_share_of_contributing_us_sales"]
        / base["rand_brand_share_of_all_us_sales"]
    )
    part_d_brand_net = base["medicare_part_d_gross_spending_billions"] * (
        base["part_d_brand_share_of_gross"]
        - base["part_d_manufacturer_rebate_share_of_gross"]
    )
    reachable = price_reduction * coverage
    expected = (
        part_d_brand_net * reachable * part_d_federal_share()
        + base["medicare_part_b_drugs_billions"]
        * reachable
        * base["part_b_drug_federal_share"]
    ) * (1 - reference_pricing_availability_response())

    assert -policy.estimate_cost_effect(0.0) == pytest.approx(expected)


def test_the_coverage_restriction_is_rands_own_and_it_binds():
    """RAND's index reaches about 87% of US brand-originator sales, not all."""
    base = PHARMA_BASELINE
    coverage = (
        base["rand_us_sales_share_in_comparison"]
        * base["rand_brand_share_of_contributing_us_sales"]
        / base["rand_brand_share_of_all_us_sales"]
    )
    assert 0.85 < coverage < 0.90


def test_a_reference_target_above_the_net_brand_ratio_saves_nothing():
    """Nothing to claw back if the cap sits above what the US already pays."""
    policy = create_reference_pricing()
    policy.reference_price_target_pct = PHARMA_BASELINE["brand_price_ratio_to_intl_net"]
    assert policy.estimate_cost_effect(0.0) == 0.0


def test_reference_pricing_stays_in_the_published_neighbourhood():
    """A broader policy than H.R. 3 should not score below H.R. 3.

    CBO scored H.R. 3's cap at 120% of the average international market price —
    reaching a limited set of drugs, not the whole Medicare book — at about
    $456B over 2020-2029 (publication 55936). A model of the same cap applied to
    all Medicare brand drugs that came in *below* that would be describing a
    different, smaller policy than the preset says it is scoring.
    """
    saving = -_score_10yr(create_reference_pricing())
    assert saving > 456.0


# ---------------------------------------------------------------------------
# 7. Mandatory manufacturer discounts
# ---------------------------------------------------------------------------


def test_a_manufacturer_discount_is_netted_and_shared_like_every_other_price_cut():
    """The last channel still booking a gross number as a federal saving.

    It used to be ``gross Part D spending x discount``, with no brand
    restriction, no rebate netting and no federal share — the same three errors
    lane L7 removed from the reference-pricing path.
    """
    base = PHARMA_BASELINE
    policy = DrugPricingPolicy(
        name="Manufacturer discount",
        description="10% mandatory discount",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.PART_D_REDESIGN,
        manufacturer_discount_pct=0.10,
    )
    naive = base["medicare_part_d_gross_spending_billions"] * 0.10
    saving = -policy.estimate_cost_effect(0.0)
    assert 0 < saving < 0.5 * naive


# ---------------------------------------------------------------------------
# 8. Provenance and dead constants
# ---------------------------------------------------------------------------


def _transcribed_rows() -> list[dict[str, str]]:
    with TRANSCRIPTION.open(encoding="utf-8") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    return list(csv.DictReader(lines))


def test_every_model_input_matches_the_transcribed_source():
    """PHARMA_BASELINE and the CSV say the same thing, or the test fails.

    Same contract as ``test_pl119_21_sources_match_the_transcribed_csv``: a
    constant may not drift away from the page it was read from.
    """
    rows = _transcribed_rows()
    inputs = [row for row in rows if row["role"] == "model_input"]
    assert inputs, "the transcription lists no model inputs"

    for row in inputs:
        key = row["key"]
        assert key in PHARMA_BASELINE, f"{key} is transcribed but not in PHARMA_BASELINE"
        assert float(row["value"]) == pytest.approx(PHARMA_BASELINE[key]), key
        assert row["source"].strip(), f"{key} has no source"
        assert row["url"].strip(), f"{key} has no url"


def test_every_baseline_constant_is_transcribed():
    """The other direction, which lane W4 added.

    The CSV-to-dict check alone let an unsourced constant sit in
    ``PHARMA_BASELINE`` indefinitely, and two did: an unsourced $220B of gross
    Part D spending that the negotiation ladder contradicts, and an unsourced
    $55B of Part B drug spending. Both are now read off a page, and this test is
    what stops the next one arriving.
    """
    transcribed = {row["key"] for row in _transcribed_rows() if row["role"] == "model_input"}
    assert set(PHARMA_BASELINE) - transcribed == set()


def test_every_transcribed_row_declares_a_role_and_a_page():
    for row in _transcribed_rows():
        assert row["role"] in {"model_input", "external_check", "context"}, row["key"]
        assert row["page"].strip(), row["key"]


def test_enforcement_baseline_no_longer_carries_a_pharma_key():
    """``medicare_insulin_share`` was copy-pasted into ENFORCEMENT_BASELINE."""
    assert "medicare_insulin_share" not in ENFORCEMENT_BASELINE


def test_superseded_incidence_constants_are_gone():
    """Constants that produced a named defect must not come back.

    ``avg_drug_price_ratio_to_intl`` was an all-drug *gross list* ratio applied
    to a net base and ``insulin_avg_cost_per_year`` was a retail insulin price
    booked as a federal outlay (both L7). ``ira_10yr_savings_billions`` was
    CBO's score of the IRA's *entire* drug-pricing title used as if it were the
    negotiation program's, then divided by a drug count; the three constants
    beside it were the hand-written scaling that followed from it; and
    ``part_d_program_federal_share`` was a single 2023 aggregate standing in for
    three channels under a benefit design the IRA replaced in 2025 (all W4).
    """
    for retired in (
        "avg_drug_price_ratio_to_intl",
        "insulin_avg_cost_per_year",
        "medicare_insulin_share",
        "part_d_oop_cap",
        "ira_10yr_savings_billions",
        "ira_negotiated_drugs_count",
        "additional_drug_productivity",
        "exclusivity_delay_savings_pct",
        "total_rx_spending_billions",
        "part_d_program_federal_share",
        "medicare_part_d_spending_billions",
    ):
        assert retired not in PHARMA_BASELINE


def test_no_policy_field_is_declared_without_being_read():
    """A settable field that changes no score is worse than a missing one.

    ``oop_cap`` was in this position before lane L7 deleted it, and it is back
    only because ASPE published the shift it needed — the tests above pin that
    it now moves a score. ``include_part_b`` was the same kind of no-op and is
    gone, with no sourced way to split CMS's third selection cycle between the
    two parts.
    """
    fields = {field.name for field in dataclasses.fields(DrugPricingPolicy)}
    assert "include_part_b" not in fields
    assert "oop_cap" in fields
    assert _oop_cap(2000.0).estimate_cost_effect(0.0) != 0.0


def test_the_unread_shadow_registries_are_gone():
    """``PHARMA_VALIDATION_SCENARIOS`` and ``CBO_PHARMA_ESTIMATES`` asserted a
    provenance their figures did not have.

    Both sat at the foot of ``pharma.py`` carrying numbers that looked like
    validation targets — -$237.0 "CBO (2022)", -$500.0 "Estimate" — and neither
    was read by any code path. The validation layer reads
    ``PHARMA_VALIDATION_SCENARIOS_COMPARE`` from ``validation/scenarios.py``,
    a different object, whose targets come from ``CBO_SCORE_MAP``. Same
    treatment lane L8 gave ``CBO_TRADE_ESTIMATES``.
    """
    assert not hasattr(pharma, "PHARMA_VALIDATION_SCENARIOS")
    assert not hasattr(pharma, "CBO_PHARMA_ESTIMATES")


# ---------------------------------------------------------------------------
# 9. The user-facing caption (Decision 6)
# ---------------------------------------------------------------------------


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


def test_every_moved_preset_explains_its_number():
    """Decision 6: a shipped number that moves ships with its caption.

    Three of the four drug-pricing presets moved in this lane, two of them by
    more than half. Each has to say which mechanism moved it.
    """
    from fiscal_model.ui.tabs.results_summary import pharma_channels_caption

    negotiation = pharma_channels_caption(create_expand_drug_negotiation(), None)
    assert "capitated direct subsidy" in negotiation
    assert "cumulative schedule" in negotiation
    assert "160 molecules by 2034" in negotiation

    reference = pharma_channels_caption(create_reference_pricing(), None)
    assert "capitated direct subsidy" in reference
    assert "RAND's index actually covers" in reference
    assert "no utilisation response is modelled" in reference

    comprehensive = pharma_channels_caption(create_comprehensive_pharma_reform(), None)
    assert "cumulative schedule" in comprehensive
    assert "cost-sharing cap saves nothing" in comprehensive


def test_the_caption_carries_the_channel_shares_the_module_computed():
    """Read off ``part_d_federal_channels``, so it cannot drift from the score."""
    from fiscal_model.ui.tabs.results_summary import pharma_channels_caption

    note = pharma_channels_caption(create_reference_pricing(), None)
    channels = part_d_federal_channels()
    for share in channels.values():
        assert f"{share:.0%}" in note
    assert f"{sum(channels.values()):.0%} in all" in note


def test_a_cost_sharing_cap_claims_no_drug_cost_channel():
    """The insulin preset did not move, and its caption may not imply it did.

    The three channels apportion a reduction in *drug cost*. A cost-sharing cap
    reduces none, which is why the module scores it at the statutory 74.5%
    instead. The caption draws the same line.
    """
    from fiscal_model.ui.tabs.results_summary import pharma_channels_caption

    note = pharma_channels_caption(create_insulin_cap_all(), None)
    assert "cost-sharing cap saves nothing" in note
    assert "74.5%" in note
    assert "direct subsidy" not in note
    assert "reinsurance" not in note


def test_a_non_pharma_policy_renders_no_pharma_note():
    from fiscal_model.policies import TaxPolicy
    from fiscal_model.ui.tabs.results_summary import pharma_channels_caption

    policy = TaxPolicy(
        name="Custom rate",
        description="+2pp above $400,000",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )
    assert pharma_channels_caption(policy, None) == ""


def test_the_headline_block_renders_the_note():
    from components.results import ScoredResult
    from fiscal_model.app_data import CBO_SCORE_MAP
    from fiscal_model.ui.tabs.results_summary import render_headline_block

    policy = create_reference_pricing()
    result = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
        policy, dynamic=False
    )
    data = {"policy": policy, "result": result}
    scored = ScoredResult.from_pipeline(
        result_data=data,
        policy_spec_hash="pharma-channels-note",
        dynamic_scoring=False,
        dynamic_view=None,
        cbo_score_map=CBO_SCORE_MAP,
        baseline_vintage="CBO Feb 2026",
    )
    st = _FakeStreamlit()
    render_headline_block(st, scored, data)
    assert any("Federal share only:" in caption for caption in st.captions), st.captions
