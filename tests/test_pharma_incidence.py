"""Pharma incidence — who actually bears a drug-pricing change.

Lane L7 of ``planning/MODELING_IMPROVEMENT.md``. These tests pin the two
properties the drug-pricing module used to get wrong, and the transcription the
new parameters come from:

1. A **cost-sharing cap** moves a dollar from a patient to a plan. It cannot be
   a federal saving, and extending it to private insurance cannot make the
   federal saving *larger* — which is what the previous implementation did.
2. A **price cap** binds on brand molecules at net prices, and the federal
   budget gets only its share of the reduction. It cannot be the full US/OECD
   list-price gap applied to every Medicare drug dollar, generics included.

Nothing here asserts a validation benchmark. The two pharma reconstruction rows
are scored by ``fiscal_model/validation/specialized_sectoral.py`` against
targets no constant in this module is fitted to, and one of those targets is
known to carry the wrong sign (CBO publication 57957). Asserting a percentage
error here would turn a benchmark into an answer key.
"""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path

import pytest

from fiscal_model.enforcement import ENFORCEMENT_BASELINE
from fiscal_model.pharma import (
    PHARMA_BASELINE,
    DrugPricingPolicy,
    DrugPricingReformType,
    create_insulin_cap_all,
    create_reference_pricing,
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
    """The bug this lane exists to kill.

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

    Pinned exactly, because it is the whole mechanism: no innovation offset is
    applied to a cost-sharing cap, since it does not change what a manufacturer
    is paid.
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


# ---------------------------------------------------------------------------
# 2. International reference pricing
# ---------------------------------------------------------------------------


def test_reference_pricing_saves_less_than_the_whole_medicare_drug_base():
    """Generics, rebates and the beneficiary share are all outside the saving.

    The old identity applied the price cut to every dollar of Part B + Part D
    spending. Brand-only, rebate-netted, federal-share scoring has to come in
    strictly below that — and by a wide margin, since the three haircuts
    compound.
    """
    base = PHARMA_BASELINE
    policy = create_reference_pricing()
    price_reduction = 1 - (
        policy.reference_price_target_pct / base["brand_price_ratio_to_intl_net"]
    )
    whole_base_saving = (
        base["medicare_part_d_spending_billions"]
        + base["medicare_part_b_drugs_billions"]
    ) * price_reduction

    saving = -policy.estimate_cost_effect(0.0)
    assert 0 < saving < 0.6 * whole_base_saving


def test_reference_pricing_matches_the_brand_net_federal_share_identity():
    base = PHARMA_BASELINE
    policy = create_reference_pricing()
    price_reduction = 1 - (
        policy.reference_price_target_pct / base["brand_price_ratio_to_intl_net"]
    )
    part_d_brand_net = base["medicare_part_d_spending_billions"] * (
        base["part_d_brand_share_of_gross"]
        - base["part_d_manufacturer_rebate_share_of_gross"]
    )
    expected = (
        part_d_brand_net * price_reduction * base["part_d_program_federal_share"]
        + base["medicare_part_b_drugs_billions"]
        * price_reduction
        * base["part_b_drug_federal_share"]
    ) * (1 - policy.innovation_offset_pct)

    assert -policy.estimate_cost_effect(0.0) == pytest.approx(expected)


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
# 3. Provenance and dead constants
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


def test_every_transcribed_row_declares_a_role_and_a_page():
    for row in _transcribed_rows():
        assert row["role"] in {"model_input", "external_check", "context"}, row["key"]
        assert row["page"].strip(), row["key"]


def test_enforcement_baseline_no_longer_carries_a_pharma_key():
    """``medicare_insulin_share`` was copy-pasted into ENFORCEMENT_BASELINE."""
    assert "medicare_insulin_share" not in ENFORCEMENT_BASELINE


def test_superseded_incidence_constants_are_gone():
    """The two constants that produced the incidence bugs must not come back.

    ``avg_drug_price_ratio_to_intl`` was an all-drug *gross list* ratio applied
    to a net base; ``insulin_avg_cost_per_year`` was a retail insulin price
    booked as though the whole of it were a federal outlay.
    """
    for retired in (
        "avg_drug_price_ratio_to_intl",
        "insulin_avg_cost_per_year",
        "medicare_insulin_share",
        "part_d_oop_cap",
    ):
        assert retired not in PHARMA_BASELINE


def test_no_policy_field_is_declared_without_being_read():
    """A settable field that changes no score is worse than a missing one.

    ``oop_cap`` was declared on the dataclass and read by nothing, so a caller
    could set a $2,000 Part D out-of-pocket cap and get a silent no-op. The
    field is gone; restoring it means implementing the mechanism, which needs a
    sourced per-beneficiary shift the way the insulin channel has one.
    """
    fields = {field.name for field in dataclasses.fields(DrugPricingPolicy)}
    assert "oop_cap" not in fields
