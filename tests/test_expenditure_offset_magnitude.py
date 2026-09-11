"""Lane H7's gate — where the tax-expenditure offset's *size* comes from.

`tests/test_offset_sign_contract.py` holds the direction half of the same
contract. This file holds the magnitude half: two of the module's five shares
are read off a document now, three are not and say so, and a rule may not
assert more than the document it names.

See ``planning/lanes/HSD_h7_expenditure_magnitudes.md``.
"""

from __future__ import annotations

import pytest

from fiscal_model.policies import PolicyType
from fiscal_model.tax_expenditure_distributions import load_deduction_distribution
from fiscal_model.tax_expenditures_core import (
    BEHAVIORAL_ELASTICITIES,
    OFFSET_MAGNITUDES,
    CapUnit,
    OffsetMagnitudeKind,
    OffsetMagnitudeRule,
    TaxExpenditurePolicy,
    TaxExpenditureType,
)
from fiscal_model.tax_expenditures_factory import (
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_cap_retirement_contributions,
    create_eliminate_mortgage_deduction,
    create_eliminate_salt_deduction,
    create_eliminate_step_up_basis,
    create_repeal_salt_cap,
)

#: The three magnitudes lane H7 searched for and did not find, with the value
#: each is left at. A lane that sources one of these moves it into
#: ``OFFSET_MAGNITUDES`` and deletes its row here; a lane that *changes* one
#: without sourcing it fails this file.
STILL_UNSOURCED = {
    TaxExpenditureType.EMPLOYER_HEALTH: 0.20,
    TaxExpenditureType.RETIREMENT_CONTRIBUTIONS: 0.30,
    TaxExpenditureType.SALT: 0.05,
}


def test_mortgage_repeal_uses_poterba_and_sinais_own_ratio():
    """$72.4B without behaviour and $61.9B with it, so the erosion is 1 - 61.9/72.4.

    Both are revenue effects of the *same* repeal, which is what makes the
    ratio this module's parameter with no conversion. The assertion is written
    as the arithmetic rather than as 0.145028, so a transcription error in
    either published figure fails here rather than passing as a constant.
    """
    policy = create_eliminate_mortgage_deduction()
    assert policy.resolved_offset_magnitude() == pytest.approx(
        1.0 - 61.9 / 72.4, abs=1e-12
    )
    assert policy.resolved_offset_magnitude() == pytest.approx(0.145028, abs=5e-7)


def test_the_charitable_ceiling_is_derived_and_not_a_constant():
    """The share moves with the cap rate, because the identity is evaluated.

    A 15% ceiling (CBO Option 49's alternative) bites more of the deduction and
    raises the price of giving further, but it also recaptures each forgone
    dollar at a *lower* rate, and the second effect dominates. A constant
    computed once at 28% could not say that.
    """
    at_28 = create_cap_charitable_deduction(cap_rate=0.28).resolved_offset_magnitude()
    at_15 = create_cap_charitable_deduction(cap_rate=0.15).resolved_offset_magnitude()

    assert at_28 == pytest.approx(0.220780, abs=5e-7)
    assert at_15 == pytest.approx(0.114040, abs=5e-7)
    assert at_15 < at_28


def test_the_charitable_share_is_crss_elasticity_times_the_modules_own_base():
    """Recompute the identity here, so the module cannot quietly change inputs.

    ``e = eps * c * sum(A_b (m_b - c)+ / (1 - m_b)) / sum(A_b (m_b - c)+)``.
    """
    distribution = load_deduction_distribution("charitable")
    cap_rate, elasticity = 0.28, 0.5
    static = 0.0
    offset = 0.0
    for bracket in distribution.brackets:
        excess = max(0.0, bracket.marginal_rate - cap_rate)
        if excess <= 0.0:
            continue
        static += bracket.amount_billions * excess
        offset += (
            cap_rate
            * bracket.amount_billions
            * elasticity
            * excess
            / (1.0 - bracket.marginal_rate)
        )

    assert create_cap_charitable_deduction().resolved_offset_magnitude() == pytest.approx(
        offset / static, abs=1e-12
    )


def test_the_shipped_040_inverts_to_an_elasticity_above_crss_whole_band():
    """The finding the lane registered: 0.40 was the right identity, wrong input.

    CRS R40518 Table 3 runs 0.1 low / 0.5 central / 0.79 high. Inverting the
    module's old 0.40 through the same identity puts it near 0.91 — above the
    top of that band, not merely above its centre.
    """
    unit = create_cap_charitable_deduction().resolved_offset_magnitude() / 0.5
    implied = 0.40 / unit

    assert implied == pytest.approx(0.906, abs=0.005)
    assert implied > 0.79


def test_a_sourced_rule_only_reaches_the_design_its_document_priced():
    """A rate ceiling's identity says nothing about a dollar cap on the base.

    Same scoping ``OFFSET_DIRECTIONS`` uses, and for the same reason: a rule
    that did not name the design it was read for would assert more than its
    document does. The dollar cap falls back to the unsourced table.
    """
    dollar_cap = TaxExpenditurePolicy(
        name="Cap deductible contributions at $10,000",
        description="a dollar cap on the base, which no document scores this way",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="cap",
        cap_amount=10_000.0,
        cap_unit=CapUnit.BASE_DOLLARS,
    )

    assert dollar_cap.offset_magnitude_rule() is None
    assert dollar_cap.resolved_offset_magnitude() == pytest.approx(
        BEHAVIORAL_ELASTICITIES[TaxExpenditureType.CHARITABLE]
    )


def test_a_mortgage_cap_does_not_inherit_repeals_sourced_erosion():
    """Poterba & Sinai price repeal; nothing in the paper sizes a cap."""
    capped = TaxExpenditurePolicy(
        name="Cap deductible mortgage interest",
        description="a cap, not the repeal the paper prices",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
        action="cap",
        cap_amount=5_000.0,
        cap_unit=CapUnit.BASE_DOLLARS,
    )

    assert capped.offset_magnitude_rule() is None
    assert capped.resolved_offset_magnitude() == pytest.approx(
        BEHAVIORAL_ELASTICITIES[TaxExpenditureType.MORTGAGE_INTEREST]
    )


@pytest.mark.parametrize(
    ("expenditure_type", "value"), sorted(STILL_UNSOURCED.items(), key=lambda kv: kv[0].value)
)
def test_the_three_unsourced_magnitudes_are_left_exactly_where_they_were(
    expenditure_type, value
):
    """Left, with the search recorded — not moved toward a number nobody printed.

    Employer health's offer elasticities price the channel CBO calls the lesser
    one; retirement's single quantified leg reverses outside the window; SALT's
    channel is named and never sized. Each is a carry-over, and changing one of
    these without a document fails here.
    """
    assert BEHAVIORAL_ELASTICITIES[expenditure_type] == pytest.approx(value)


@pytest.mark.parametrize(
    "factory",
    [
        create_cap_employer_health_exclusion,
        create_repeal_salt_cap,
        create_eliminate_salt_deduction,
        create_cap_retirement_contributions,
        create_eliminate_step_up_basis,
    ],
)
def test_no_other_shipped_reform_acquired_a_sourced_magnitude(factory):
    """Five of the eight factories resolve exactly as they did before H7."""
    policy = factory()
    assert policy.offset_magnitude_rule() is None
    assert policy.resolved_offset_magnitude() == pytest.approx(
        BEHAVIORAL_ELASTICITIES.get(
            policy.expenditure_type, policy.behavioral_elasticity
        )
    )


def test_every_sourced_magnitude_names_its_document():
    """The way to change a magnitude is to find a document, never to add a key.

    The same discipline ``test_every_magnify_entry_carries_a_source`` enforces
    for directions. A source string this short cannot carry a figure, a table
    and a page.
    """
    assert OFFSET_MAGNITUDES, "the table must not be emptied"
    for key, rule in OFFSET_MAGNITUDES.items():
        assert len(rule.source) > 200, key
        assert any(
            mark in rule.source
            for mark in ("CRS", "NBER", "CBO", "JCT", "Treasury")
        ), key


def test_a_rule_carries_a_share_or_an_elasticity_and_never_both():
    """The two kinds are different quantities and the record refuses to blur them."""
    with pytest.raises(ValueError):
        OffsetMagnitudeRule(
            kind=OffsetMagnitudeKind.PUBLISHED_SHARE,
            source="x",
            share=0.1,
            price_elasticity=0.5,
        )
    with pytest.raises(ValueError):
        OffsetMagnitudeRule(
            kind=OffsetMagnitudeKind.PRICE_ELASTICITY_ON_BENEFIT_RATE_CEILING,
            source="x",
            share=0.1,
        )
    with pytest.raises(ValueError):
        OffsetMagnitudeRule(kind=OffsetMagnitudeKind.PUBLISHED_SHARE, source="x")


def test_a_price_elasticity_is_taken_as_a_magnitude():
    """A source quoting -0.5 and one quoting 0.5 mean the same response.

    The sign of the *offset* is ``OFFSET_DIRECTIONS``'s job, and a negative
    elasticity leaking into the magnitude would silently flip it.
    """
    distribution = load_deduction_distribution("charitable")
    assert distribution.benefit_rate_ceiling_offset_share(
        0.28, -0.5
    ) == pytest.approx(distribution.benefit_rate_ceiling_offset_share(0.28, 0.5))


def test_a_ceiling_above_every_bracket_offsets_nothing():
    """No filer is above the cap, so there is no static effect and no response."""
    distribution = load_deduction_distribution("charitable")
    assert distribution.benefit_rate_ceiling_offset_share(0.99, 0.5) == 0.0


def test_the_two_movers_are_the_only_reforms_whose_offset_changed():
    """The lane's own falsification condition, as an assertion.

    Every factory's offset on a $100B static is pinned. The two sourced ones
    carry their published shares; the other six carry exactly what they carried
    before H7 opened a file.
    """
    expected = {
        "create_cap_employer_health_exclusion": -20.0,
        "create_repeal_salt_cap": -5.0,
        "create_eliminate_salt_deduction": -5.0,
        "create_cap_retirement_contributions": 30.0,
        "create_eliminate_step_up_basis": 0.0,
        "create_cap_charitable_deduction": -22.077987,
        "create_eliminate_mortgage_deduction": 14.502762,
    }
    factories = {
        "create_cap_employer_health_exclusion": create_cap_employer_health_exclusion,
        "create_repeal_salt_cap": create_repeal_salt_cap,
        "create_eliminate_salt_deduction": create_eliminate_salt_deduction,
        "create_cap_retirement_contributions": create_cap_retirement_contributions,
        "create_eliminate_step_up_basis": create_eliminate_step_up_basis,
        "create_cap_charitable_deduction": create_cap_charitable_deduction,
        "create_eliminate_mortgage_deduction": create_eliminate_mortgage_deduction,
    }
    for name, factory in factories.items():
        offset = factory().estimate_behavioral_offset(100.0)
        assert offset == pytest.approx(expected[name], abs=5e-5), name


# ---------------------------------------------------------------------------
# The Decision 6 caption
# ---------------------------------------------------------------------------


def test_the_caption_carries_the_scored_figures_and_its_document():
    """Computed from the result, so it cannot drift from the number above it."""
    from fiscal_model.scoring import FiscalPolicyScorer
    from fiscal_model.ui.tabs.results_summary import (
        expenditure_offset_magnitude_caption,
    )

    scorer = FiscalPolicyScorer(use_real_data=False)
    policy = create_cap_charitable_deduction()
    result = scorer.score_policy(policy, dynamic=False)
    note = expenditure_offset_magnitude_caption(policy, result)

    assert "22.1%" in note  # the share the module now applies
    assert "40%" in note  # what it applied before
    assert "28%" in note  # the ceiling the share is derived at
    assert "R40518" in note
    assert "0.5" in note


def test_the_caption_agrees_with_itself_in_both_engine_modes():
    """The headline is the conventional score, so the caption must not move.

    PR #144's review found a caption reading ``final_deficit_effect``, which on
    a dynamic run also carries revenue feedback and so disagreed with the
    headline directly above it. This one is computed from static plus
    behavioural, which is the headline in both modes.
    """
    from fiscal_model.scoring import FiscalPolicyScorer
    from fiscal_model.ui.tabs.results_summary import (
        expenditure_offset_magnitude_caption,
    )

    scorer = FiscalPolicyScorer(use_real_data=False)
    policy = create_cap_charitable_deduction()
    static_note = expenditure_offset_magnitude_caption(
        policy, scorer.score_policy(policy, dynamic=False)
    )
    dynamic_note = expenditure_offset_magnitude_caption(
        policy, scorer.score_policy(policy, dynamic=True)
    )

    assert static_note == dynamic_note
    assert static_note


def test_the_caption_stays_silent_on_every_other_preset():
    """A note that appears everywhere explains nothing.

    Exactly one shipped preset moved, so exactly one carries this caption.
    """
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.preset_handler import create_policy_from_preset
    from fiscal_model.scoring import FiscalPolicyScorer
    from fiscal_model.ui.tabs.results_summary import (
        expenditure_offset_magnitude_caption,
    )

    scorer = FiscalPolicyScorer(use_real_data=False)
    captioned = []
    for label, data in PRESET_POLICIES.items():
        policy = create_policy_from_preset(data)
        if policy is None:
            continue
        result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
        if expenditure_offset_magnitude_caption(policy, result):
            captioned.append(label)

    assert len(captioned) == 1, captioned
    assert "Cap Charitable Deduction" in captioned[0]
