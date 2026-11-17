"""Marginal-credit factor: calibrated to rate-only houses, JCT held out.

The derived path already books *average* credit realization inside
``BASE_PER_DOLLAR_OF_RECEIPTS``. A statutory rate change also unlocks (or, on a
cut, locks) IRC §38(c) general-business-credit carryforwards — CBO 2018 Option
24 is the only *Options* narrative that names the channel. Form 3800 publishes
the stock and the cap, not the constrained *tax* share (R5; SOI's
excess-position tables stop at TY2010), so the factor is not identified from
those columns.

It is the ratio of the mean implied marginal share of three published
**rate-only** houses that are **not** in the out-of-sample battery (Tax
Foundation 2024, PWBM 2024, Treasury FY2022 rate-only) to the mechanical +1pp
share. The four JCT Options +1pp rows are held out. The 0.5785 that would
reproduce Option 64 and JCT's own 0.590 are forbidden as calibration targets
(``planning/memos/CORPORATE_PER_POINT_YIELD.md`` §6).
"""

from __future__ import annotations

import math

import pytest

from fiscal_model.corporate import (
    BASE_PER_DOLLAR_OF_RECEIPTS,
    BASELINE_TAXABLE_PROFITS_BILLIONS,
    CURRENT_CORPORATE_RATE,
    PROFIT_SHIFTING_SEMI_ELASTICITY,
    RATE_ONLY_CALIBRATION_MEAN_SHARE,
    RATE_ONLY_CALIBRATION_SHARES,
    RATE_ONLY_HOLDOUT_POLICY_IDS,
    SECTION_38C_ALLOWED_SHARE_OF_REGULAR_TAX,
    credit_absorption_bounds,
    credit_carryforward_item,
    credit_realization_ratio,
    marginal_credit_factor,
    mechanical_plus_one_pp_share,
    window_marginal_share,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.policy_classes import classify_policy

# Forbidden numbers from the yield memo §6: reproducing Option 64, and JCT's
# own steady-state share against the February 2024 baseline.
_FORBIDDEN_SHARES = (0.5785, 0.590)


def test_the_calibration_set_is_disjoint_from_the_holdout():
    """A share taken from a holdout row is overfitting, not calibration."""
    holdout = set(RATE_ONLY_HOLDOUT_POLICY_IDS)
    assert holdout <= set(KNOWN_SCORES)
    for policy_id in holdout:
        assert classify_policy(policy_id) == "corporate"
    for key in RATE_ONLY_CALIBRATION_SHARES:
        assert key not in holdout
        assert "opt" not in key
        assert "cbo" not in key


def test_the_calibration_mean_is_the_three_rate_only_houses():
    shares = RATE_ONLY_CALIBRATION_SHARES
    assert set(shares) == {
        "tax_foundation_fy2025_2034",
        "pwbm_fy2025_2034",
        "treasury_fy2022_rate_only",
    }
    assert shares["tax_foundation_fy2025_2034"] == pytest.approx(0.5511, abs=0.0002)
    assert shares["pwbm_fy2025_2034"] == pytest.approx(0.6437, abs=0.0002)
    assert shares["treasury_fy2022_rate_only"] == pytest.approx(0.6673, abs=0.0002)
    assert RATE_ONLY_CALIBRATION_MEAN_SHARE == pytest.approx(
        sum(shares.values()) / 3.0, rel=1e-12
    )
    assert RATE_ONLY_CALIBRATION_MEAN_SHARE == pytest.approx(0.6207, abs=0.0001)


def test_the_plus_one_pp_share_matches_the_calibration_mean():
    """The factor exists to land this identity, not a holdout row."""
    mechanical = mechanical_plus_one_pp_share()
    factor = marginal_credit_factor()
    derived = window_marginal_share(0.01, credit_factor=factor)
    assert mechanical == pytest.approx(0.8084, abs=0.0002)
    assert factor == pytest.approx(
        RATE_ONLY_CALIBRATION_MEAN_SHARE / mechanical, rel=1e-12
    )
    assert derived == pytest.approx(RATE_ONLY_CALIBRATION_MEAN_SHARE, rel=1e-12)
    assert derived == pytest.approx(0.6207, abs=0.0001)


def test_the_factor_is_not_the_forbidden_jct_shares():
    """Memo §6: 0.5785 reproduces Option 64; 0.590 is JCT read backwards."""
    derived = window_marginal_share(0.01, credit_factor=marginal_credit_factor())
    for forbidden in _FORBIDDEN_SHARES:
        assert abs(derived - forbidden) > 0.01, forbidden
        assert abs(marginal_credit_factor() - forbidden) > 0.01, forbidden


def test_the_fitted_aggregate_and_the_semi_elasticity_were_not_retuned():
    assert BASELINE_TAXABLE_PROFITS_BILLIONS == 1900.0
    assert PROFIT_SHIFTING_SEMI_ELASTICITY == 0.8
    assert BASE_PER_DOLLAR_OF_RECEIPTS == pytest.approx(4.80133, abs=1e-5)
    assert CURRENT_CORPORATE_RATE == 0.21


def test_extra_absorption_sits_between_average_gbc_and_the_statutory_cap():
    """The implied extra §38(c) take is a check, not an identification.

    Average credit substitution is already in the receipts identity (~29%).
    Scaling the credit-realized base by γ adds ``realization × (1 − γ)`` of
    extra absorption of pre-credit tax. That quantity has to sit between the
    average GBC claim rate (already in the receipts) and the statutory 75%
    cap, or the factor is doing something Form 3800 cannot support.
    """
    bounds = credit_absorption_bounds()
    extra = bounds["extra_absorption_of_precredit_tax"]
    from fiscal_model.corporate import soi_row

    statutory_tax = float(soi_row(2022)["income_tax_thousands"]) / 1e6
    average_gbc_rate = bounds["section_38c_claimed_billions"] / statutory_tax
    assert extra == pytest.approx(
        credit_realization_ratio() * (1.0 - marginal_credit_factor()), rel=1e-12
    )
    assert average_gbc_rate < extra < SECTION_38C_ALLOWED_SHARE_OF_REGULAR_TAX
    assert 0.10 < extra < 0.25
    assert bounds["gbc_filers_share_of_statutory_tax"] == pytest.approx(0.883, abs=0.002)
    assert bounds["section_38c_part_i_unused_billions"] == pytest.approx(91.20, abs=0.05)


def test_form_3800_part_ii_limitation_lines_are_transcribed():
    """The cap and the unused Part I stock, not a share to multiply."""
    line7 = credit_carryforward_item("form_3800_part_ii_line_7_regular_tax")
    line11 = credit_carryforward_item("form_3800_part_ii_line_11_net_income_tax")
    line16 = credit_carryforward_item("form_3800_part_ii_line_16_section38c_limitation")
    line17 = credit_carryforward_item("form_3800_part_ii_line_17_allowed_part_i")
    line6 = credit_carryforward_item("form_3800_part_i_line_6_total")
    assert line7 == pytest.approx(533.589, abs=0.001)
    assert line11 == pytest.approx(427.642, abs=0.001)
    assert line16 == pytest.approx(320.869, abs=0.001)
    assert line17 == pytest.approx(48.297, abs=0.001)
    assert line6 - line17 == pytest.approx(91.201, abs=0.001)
    # The statutory 75% cap is an upper bound on line 16 / regular tax of
    # GBC filers, not an identity: the $25,000 floor and TMT sit in the
    # greater-of. The transcribed limitation is below 75% of line 7.
    assert line16 / line7 < SECTION_38C_ALLOWED_SHARE_OF_REGULAR_TAX


def test_plus_seven_pp_share_is_inside_the_published_span():
    """H3a's second Decision 1 metric, after the factor.

    Four houses converted to +7pp span 55.1–79.5% of the average base.
    Mechanical derived sat at 76.1%; with the factor it sits at 58.5%, still
    inside, still below Treasury's bundled 79.5%.
    """
    share = window_marginal_share(0.07, credit_factor=marginal_credit_factor())
    assert 0.551 < share < 0.795
    assert share == pytest.approx(0.5845, abs=0.001)


def test_the_factor_is_constant_across_vintages():
    """A realization ratio, not a receipts-path property: one γ, four Outlooks."""
    factor = marginal_credit_factor()
    for vintage, start in (
        ("cbo_apr_2018", 2019),
        ("cbo_sep_2020", 2021),
        ("cbo_may_2022", 2023),
        ("cbo_feb_2024", 2025),
    ):
        mechanical = window_marginal_share(
            0.01, vintage=vintage, start_year=start, credit_factor=1.0
        )
        derived = window_marginal_share(
            0.01, vintage=vintage, start_year=start, credit_factor=factor
        )
        assert derived / mechanical == pytest.approx(factor, rel=1e-9)


def test_the_cbo_loss_firm_haircut_is_still_not_the_factor():
    """0.80 and 0.85 are CBO's unpublished loss-firm haircuts, not this γ."""
    factor = marginal_credit_factor()
    assert abs(factor - 0.80) > 0.02
    assert abs(factor - 0.85) > 0.05
    assert math.isfinite(factor)
