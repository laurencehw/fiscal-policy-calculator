"""
Regression tests that score key policies and verify they match
CBO/JCT estimates within tolerance.

Uses FiscalPolicyScorer(use_real_data=False) for consistency across
environments (avoids dependency on external data files).

Coverage: TCJA, corporate, CTC, AMT, estate, payroll, tax expenditures.
"""

import pytest

from fiscal_model.amt import create_repeal_corporate_amt
from fiscal_model.corporate import create_biden_corporate_rate_only
from fiscal_model.credits import create_biden_ctc_2021
from fiscal_model.estate import create_biden_estate_proposal, create_tcja_estate_extension
from fiscal_model.payroll import (
    create_ss_donut_hole,
    create_ss_eliminate_cap,
)
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.tax_expenditures import (
    create_cap_employer_health_exclusion,
    create_repeal_salt_cap,
)
from fiscal_model.tcja import create_tcja_extension


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


class TestBidenEstateProposalCBORange:
    """Biden estate reform ($3.5M, 45%) should raise $300-600B. CBO: ~$450B."""

    def test_biden_estate_cbo_range(self, scorer):
        policy = create_biden_estate_proposal()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -600 <= total <= -300, (
            f"Biden estate {total:.0f}B outside expected range [-600, -300]"
        )

    def test_biden_estate_reduces_deficit(self, scorer):
        """Lowering exemption + raising rate should reduce deficit."""
        policy = create_biden_estate_proposal()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost < 0


class TestTCJAEstateExtensionCBORange:
    """Extending TCJA estate exemption should cost $100-250B. CBO: ~$167B."""

    def test_tcja_estate_extension_cbo_range(self, scorer):
        policy = create_tcja_estate_extension()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 100 <= total <= 250, (
            f"TCJA estate extension {total:.0f}B outside expected range [100, 250]"
        )

    def test_tcja_estate_extension_increases_deficit(self, scorer):
        policy = create_tcja_estate_extension()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0


class TestSSDonutHoleCBORange:
    """SS donut hole ($250K+) should raise $1,800-3,500B. Trustees: ~$2,700B."""

    def test_ss_donut_cbo_range(self, scorer):
        policy = create_ss_donut_hole()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -3500 <= total <= -1800, (
            f"SS donut hole {total:.0f}B outside expected range [-3500, -1800]"
        )

    def test_ss_donut_reduces_deficit(self, scorer):
        policy = create_ss_donut_hole()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost < 0


class TestSSEliminateCapCBORange:
    """Eliminate SS wage cap should raise $2,200-4,000B. Trustees: ~$3,200B."""

    def test_ss_eliminate_cap_cbo_range(self, scorer):
        policy = create_ss_eliminate_cap()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -4000 <= total <= -2200, (
            f"SS eliminate cap {total:.0f}B outside expected range [-4000, -2200]"
        )

    def test_ss_eliminate_cap_reduces_deficit(self, scorer):
        policy = create_ss_eliminate_cap()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost < 0


class TestCapEmployerHealthCBORange:
    """Cap employer health exclusion should raise $350-550B. CBO: ~$450B."""

    def test_cap_employer_health_cbo_range(self, scorer):
        policy = create_cap_employer_health_exclusion()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -550 <= total <= -350, (
            f"Cap employer health {total:.0f}B outside expected range [-550, -350]"
        )

    def test_cap_employer_health_reduces_deficit(self, scorer):
        policy = create_cap_employer_health_exclusion()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost < 0


class TestRepealSALTCapCBORange:
    """Repealing SALT cap should cost $800-2,500B. CBO: ~$1,900B."""

    def test_repeal_salt_cap_cbo_range(self, scorer):
        policy = create_repeal_salt_cap()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 800 <= total <= 2500, (
            f"Repeal SALT cap {total:.0f}B outside expected range [800, 2500]"
        )

    def test_repeal_salt_cap_increases_deficit(self, scorer):
        policy = create_repeal_salt_cap()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0
