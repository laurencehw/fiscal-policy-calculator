"""
Regression tests that score key policies and verify they match
CBO/JCT estimates within tolerance.

Uses FiscalPolicyScorer(use_real_data=False) for consistency across
environments (avoids dependency on external data files).

Coverage: 26 policies across TCJA, corporate, CTC, AMT, estate,
payroll, PTC, tax expenditures.
"""

import pytest

from fiscal_model.amt import (
    create_extend_tcja_amt_relief,
    create_repeal_corporate_amt,
    create_repeal_individual_amt,
)
from fiscal_model.corporate import (
    create_biden_corporate_rate_only,
    create_republican_corporate_cut,
)
from fiscal_model.credits import create_biden_ctc_2021
from fiscal_model.estate import (
    create_biden_estate_proposal,
    create_eliminate_estate_tax,
    create_tcja_estate_extension,
    create_warren_estate_proposal,
)
from fiscal_model.payroll import (
    create_expand_niit,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
)
from fiscal_model.ptc import create_extend_enhanced_ptc, create_repeal_ptc
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.tax_expenditures import (
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_eliminate_mortgage_deduction,
    create_eliminate_salt_deduction,
    create_eliminate_step_up_basis,
    create_repeal_salt_cap,
)
from fiscal_model.tcja import create_tcja_extension, create_tcja_repeal_salt_cap


@pytest.fixture
def scorer():
    """Create a scorer with fallback data for consistent results."""
    return FiscalPolicyScorer(use_real_data=False)


# =============================================================================
# TCJA
# =============================================================================

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
        assert result.total_10_year_cost > 0

    def test_tcja_extension_annual_costs_grow(self, scorer):
        """Annual costs should generally increase over the 10-year window."""
        policy = create_tcja_extension(extend_all=True)
        result = scorer.score_policy(policy)
        assert result.final_deficit_effect[0] < result.final_deficit_effect[-1]


class TestTCJARepealSALTCapCBORange:
    """TCJA + SALT cap repeal should cost $4,800-6,800B. Estimated: ~$5,700B."""

    def test_tcja_no_salt_cap_range(self, scorer):
        policy = create_tcja_repeal_salt_cap()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 4800 <= total <= 6800, (
            f"TCJA + no SALT cap {total:.0f}B outside range [4800, 6800]"
        )


class TestTCJARatesOnlyCBORange:
    """TCJA rates only should cost $3,000-4,500B. Calibrated: ~$3,185B."""

    def test_tcja_rates_only_range(self, scorer):
        policy = create_tcja_extension(extend_all=False, extend_rate_cuts=True)
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 3000 <= total <= 4500, (
            f"TCJA rates only {total:.0f}B outside range [3000, 4500]"
        )


# =============================================================================
# CORPORATE TAX
# =============================================================================

class TestBidenCorporateRateCBORange:
    """Biden corporate rate increase (21->28%) should raise $1,000-1,800B."""

    def test_biden_corporate_cbo_range(self, scorer):
        policy = create_biden_corporate_rate_only()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -1800 <= total <= -1000, (
            f"Biden corporate {total:.0f}B outside expected range [-1800, -1000]"
        )

    def test_biden_corporate_reduces_deficit(self, scorer):
        policy = create_biden_corporate_rate_only()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost < 0


class TestTrumpCorporateCutRange:
    """Trump corporate cut (21->15%) should cost $1,200-2,200B. Estimated: ~$1,920B."""

    def test_trump_corporate_range(self, scorer):
        policy = create_republican_corporate_cut()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 1200 <= total <= 2200, (
            f"Trump corporate cut {total:.0f}B outside range [1200, 2200]"
        )

    def test_trump_corporate_increases_deficit(self, scorer):
        policy = create_republican_corporate_cut()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0


# =============================================================================
# TAX CREDITS
# =============================================================================

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
        policy = create_biden_ctc_2021()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0


# =============================================================================
# AMT
# =============================================================================

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
        policy = create_repeal_corporate_amt()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0


class TestExtendTCJAAMTReliefCBORange:
    """Extending TCJA AMT relief should cost $300-550B. JCT/CBO: ~$450B."""

    def test_extend_amt_relief_range(self, scorer):
        policy = create_extend_tcja_amt_relief()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 300 <= total <= 550, (
            f"Extend TCJA AMT relief {total:.0f}B outside range [300, 550]"
        )

    def test_extend_amt_relief_increases_deficit(self, scorer):
        policy = create_extend_tcja_amt_relief()
        result = scorer.score_policy(policy)
        assert result.total_10_year_cost > 0


class TestRepealIndividualAMTRange:
    """Repealing individual AMT should cost $30-100B. CBO baseline: ~$57B."""

    def test_repeal_individual_amt_range(self, scorer):
        policy = create_repeal_individual_amt()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 30 <= total <= 100, (
            f"Repeal individual AMT {total:.0f}B outside range [30, 100]"
        )


# =============================================================================
# ESTATE TAX
# =============================================================================

class TestBidenEstateProposalCBORange:
    """Biden estate reform ($3.5M, 45%) should raise $300-600B. Treasury: ~$450B."""

    def test_biden_estate_cbo_range(self, scorer):
        policy = create_biden_estate_proposal()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -600 <= total <= -300, (
            f"Biden estate {total:.0f}B outside expected range [-600, -300]"
        )

    def test_biden_estate_reduces_deficit(self, scorer):
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


class TestWarrenEstateRange:
    """Warren estate proposal should raise $2,500-5,500B."""

    def test_warren_estate_range(self, scorer):
        policy = create_warren_estate_proposal()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -5500 <= total <= -2500, (
            f"Warren estate {total:.0f}B outside range [-5500, -2500]"
        )


class TestEliminateEstateTaxRange:
    """Eliminating estate tax should cost $250-500B. Model: ~$350B."""

    def test_eliminate_estate_range(self, scorer):
        policy = create_eliminate_estate_tax()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 250 <= total <= 500, (
            f"Eliminate estate tax {total:.0f}B outside range [250, 500]"
        )


# =============================================================================
# PAYROLL TAX
# =============================================================================

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


class TestSSCap90PercentRange:
    """SS cap to 90% coverage should raise $500-1,000B. CBO: ~$800B."""

    def test_ss_cap_90_range(self, scorer):
        policy = create_ss_cap_90_percent()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -1000 <= total <= -500, (
            f"SS cap 90% {total:.0f}B outside range [-1000, -500]"
        )


class TestExpandNIITRange:
    """Expand NIIT to pass-through should raise $150-350B. JCT: ~$250B."""

    def test_expand_niit_range(self, scorer):
        policy = create_expand_niit()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -350 <= total <= -150, (
            f"Expand NIIT {total:.0f}B outside range [-350, -150]"
        )


# =============================================================================
# PREMIUM TAX CREDITS
# =============================================================================

class TestExtendEnhancedPTCRange:
    """Extend enhanced PTCs should cost $200-500B. CBO 2024: ~$350B."""

    def test_extend_ptc_range(self, scorer):
        policy = create_extend_enhanced_ptc()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert 200 <= total <= 500, (
            f"Extend enhanced PTC {total:.0f}B outside range [200, 500]"
        )


class TestRepealPTCRange:
    """Repeal all PTCs should save $700-1,300B. CBO: ~$1,100B."""

    def test_repeal_ptc_range(self, scorer):
        policy = create_repeal_ptc()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -1300 <= total <= -700, (
            f"Repeal PTC {total:.0f}B outside range [-1300, -700]"
        )


# =============================================================================
# TAX EXPENDITURES
# =============================================================================

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
    """Repealing SALT cap should cost $800-2,500B. JCT: ~$1,100B."""

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


class TestEliminateMortgageDeductionRange:
    """Eliminate mortgage deduction should raise $200-400B. CBO: ~$300B."""

    def test_eliminate_mortgage_range(self, scorer):
        policy = create_eliminate_mortgage_deduction()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -400 <= total <= -200, (
            f"Eliminate mortgage deduction {total:.0f}B outside range [-400, -200]"
        )


class TestEliminateSALTDeductionRange:
    """Eliminate SALT deduction entirely should raise $800-1,500B. JCT: ~$1,200B."""

    def test_eliminate_salt_range(self, scorer):
        policy = create_eliminate_salt_deduction()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -1500 <= total <= -800, (
            f"Eliminate SALT deduction {total:.0f}B outside range [-1500, -800]"
        )


class TestCapCharitableDeductionRange:
    """Cap charitable deduction at 28% should raise $100-250B. Biden: ~$200B."""

    def test_cap_charitable_range(self, scorer):
        policy = create_cap_charitable_deduction()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -250 <= total <= -100, (
            f"Cap charitable deduction {total:.0f}B outside range [-250, -100]"
        )


class TestEliminateStepUpBasisRange:
    """Eliminate step-up in basis should raise $350-600B. Biden: ~$500B."""

    def test_eliminate_step_up_range(self, scorer):
        policy = create_eliminate_step_up_basis()
        result = scorer.score_policy(policy)
        total = result.total_10_year_cost
        assert -600 <= total <= -350, (
            f"Eliminate step-up basis {total:.0f}B outside range [-600, -350]"
        )
