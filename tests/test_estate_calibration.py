"""
Estate tax window-average calibration and two-regime taxable-amount tests.
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


def test_two_regime_avg_exceeds_mid_only_avg():
    """Ultra-high tail blend must raise average taxable amount vs mid-only."""
    policy = EstateTaxPolicy(
        name="Bottom-up",
        description="Bottom-up",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=3_500_000,
        new_rate=0.45,
    )
    _n, blended = policy.estimate_taxable_estates(3_500_000)
    post_tcja_exemption = 6_400_000
    mid_only = BASELINE_ESTATE_DATA["avg_taxable_amount_post_tcja"] * (
        3_500_000 / post_tcja_exemption
    )
    assert blended > mid_only
    assert blended > mid_only * 1.5  # top-tail value share is material
