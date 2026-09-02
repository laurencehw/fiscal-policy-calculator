"""
Estate tax window-average calibration and SOI mean-excess taxable-amount tests.
"""

from __future__ import annotations

import pytest

from fiscal_model.estate import (
    BASELINE_ESTATE_DATA,
    EstateTaxPolicy,
    create_biden_estate_proposal,
    create_eliminate_estate_tax,
    create_tcja_estate_extension,
    create_warren_estate_proposal,
    soi_estate_anchor,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer


def test_biden_estate_matches_treasury_window_average():
    scorer = FiscalPolicyScorer(use_real_data=False)
    result = scorer.score_policy(create_biden_estate_proposal())
    assert result.total_10_year_cost == pytest.approx(-450.0, rel=1e-6)


def test_tcja_estate_extension_matches_cbo_window_average():
    scorer = FiscalPolicyScorer(use_real_data=False)
    result = scorer.score_policy(create_tcja_estate_extension())
    assert result.total_10_year_cost == pytest.approx(167.0, rel=1e-6)


def test_warren_and_eliminate_use_flat_window_averages():
    scorer = FiscalPolicyScorer(use_real_data=False)
    warren = scorer.score_policy(create_warren_estate_proposal())
    eliminate = scorer.score_policy(create_eliminate_estate_tax())
    assert warren.total_10_year_cost == pytest.approx(-2600.0, rel=1e-6)
    assert eliminate.total_10_year_cost == pytest.approx(350.0, rel=1e-6)


def test_taxable_amount_tracks_the_soi_mean_excess_ratio():
    """
    Replaces the old two-regime blend test.

    The blend existed to stop a single mid-distribution Pareto underweighting
    the $50M+ tail; the SOI-fitted distribution measures the mean excess
    directly off SOI's own anchor row instead, so the average taxable amount
    is 1.83 times the exemption and no top-tail constant is needed.
    """
    policy = EstateTaxPolicy(
        name="Bottom-up",
        description="Bottom-up",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=3_500_000,
        new_rate=0.45,
    )
    estates, average = policy.estimate_taxable_estates(3_500_000, 2026)
    ratio = soi_estate_anchor().mean_excess_ratio
    assert average == pytest.approx(3_500_000 * ratio)
    assert 1.5 < ratio < 2.2
    assert estates > 0
    # The 2024 fitted anchors it replaces are gone, not merely unused.
    assert "avg_taxable_amount_post_tcja" not in BASELINE_ESTATE_DATA
    assert "taxable_estates_post_tcja" not in BASELINE_ESTATE_DATA
    assert "top_tail_value_share" not in BASELINE_ESTATE_DATA
