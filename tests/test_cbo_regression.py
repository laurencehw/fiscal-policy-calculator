"""
Regression tests that score key policies and verify they match
CBO/JCT estimates within tolerance.

Uses FiscalPolicyScorer(use_real_data=False) for consistency across
environments (avoids dependency on external data files).
"""

import pytest

from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.tcja import create_tcja_extension
from fiscal_model.corporate import create_biden_corporate_rate_only
from fiscal_model.credits import create_biden_ctc_2021
from fiscal_model.amt import create_repeal_corporate_amt


@pytest.fixture
def scorer():
    """Create a scorer with fallback data for consistent results."""
    return FiscalPolicyScorer(use_real_data=False)


class TestTCJAExtensionCBORange:
    """TCJA full extension should cost $4,000-5,200B over 10 years."""

    def test_tcja_extension_cbo_range(self, scorer):
        policy = create_tcja_extension(extend_all=True)
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 4000 <= total <= 5200, (
            f"TCJA extension {total:.0f}B outside CBO range [4000, 5200]"
        )

    def test_tcja_extension_is_positive_cost(self, scorer):
        """TCJA extension increases the deficit (positive cost)."""
        policy = create_tcja_extension(extend_all=True)
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0, (
            "TCJA extension should increase the deficit"
        )

    def test_tcja_extension_annual_costs_grow(self, scorer):
        """Annual costs should generally increase over the 10-year window."""
        policy = create_tcja_extension(extend_all=True)
        result = scorer.score_policy(policy)
        # First year cost should be less than last year cost
        assert result.final_deficit_effect[0] < result.final_deficit_effect[-1], (
            "TCJA annual costs should grow over time"
        )


class TestBidenCorporateRateCBORange:
    """Biden corporate rate increase (21->28%) should raise $1,000-1,800B."""

    def test_biden_corporate_cbo_range(self, scorer):
        policy = create_biden_corporate_rate_only()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        # Revenue raiser: total_10_year_cost should be negative (reduces deficit)
        assert -1800 <= total <= -1000, (
            f"Biden corporate {total:.0f}B outside expected range [-1800, -1000]"
        )

    def test_biden_corporate_reduces_deficit(self, scorer):
        """Raising corporate rate should reduce the deficit (negative cost)."""
        policy = create_biden_corporate_rate_only()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost < 0, (
            "Corporate rate increase should reduce the deficit"
        )


class TestBidenCTC2021CBORange:
    """Biden CTC 2021 (ARP-style permanent) should cost $1,200-2,200B."""

    def test_biden_ctc_cbo_range(self, scorer):
        policy = create_biden_ctc_2021()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 1200 <= total <= 2200, (
            f"Biden CTC {total:.0f}B outside expected range [1200, 2200]"
        )

    def test_biden_ctc_increases_deficit(self, scorer):
        """CTC expansion should increase the deficit (positive cost)."""
        policy = create_biden_ctc_2021()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0, (
            "CTC expansion should increase the deficit"
        )


class TestRepealCorporateAMTCBORange:
    """Repealing corporate AMT should cost $150-300B over 10 years."""

    def test_repeal_corporate_amt_cbo_range(self, scorer):
        policy = create_repeal_corporate_amt()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 150 <= total <= 300, (
            f"Repeal corporate AMT {total:.0f}B outside expected range [150, 300]"
        )

    def test_repeal_corporate_amt_increases_deficit(self, scorer):
        """Repealing corporate AMT should increase the deficit."""
        policy = create_repeal_corporate_amt()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0, (
            "Repealing corporate AMT should increase the deficit"
        )
