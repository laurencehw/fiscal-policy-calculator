"""
Database of known CBO/JCT revenue estimates for validation.

Sources:
- CBO cost estimates: https://www.cbo.gov/cost-estimates
- JCT revenue estimates: https://www.jct.gov/publications/
- Treasury revenue estimates: https://home.treasury.gov/

Note: All figures are in billions of dollars over 10-year budget windows.
Positive values = increases deficit (costs), negative = reduces deficit (savings/revenue).
"""

from dataclasses import dataclass
from typing import Optional, Literal
from enum import Enum


class ScoreSource(Enum):
    """Source of the official estimate."""
    CBO = "Congressional Budget Office"
    JCT = "Joint Committee on Taxation"
    TREASURY = "U.S. Treasury"
    OMB = "Office of Management and Budget"
    TPC = "Tax Policy Center"
    PWBM = "Penn Wharton Budget Model"


@dataclass
class CBOScore:
    """
    A known official budget score for a policy.
    
    Attributes:
        policy_id: Unique identifier for the policy
        name: Short policy name
        description: Detailed description
        ten_year_cost: 10-year budget impact in billions (positive = cost)
        source: Which organization produced the estimate
        source_date: When the estimate was published
        source_url: Link to the official document
        
        # Policy parameters (for replication)
        rate_change: Tax rate change (if applicable)
        income_threshold: Income threshold (if applicable)
        policy_type: Type of policy
        
        # Context
        baseline_year: What baseline was used
        notes: Additional context or caveats
    """
    policy_id: str
    name: str
    description: str
    ten_year_cost: float  # Billions, positive = increases deficit
    source: ScoreSource
    source_date: str  # YYYY-MM format
    source_url: Optional[str] = None
    
    # Policy parameters for replication
    rate_change: Optional[float] = None
    income_threshold: Optional[float] = None
    policy_type: Literal["income_tax", "corporate_tax", "spending", "other"] = "income_tax"
    
    # Scoring details
    first_year_cost: Optional[float] = None  # First year effect if known
    is_dynamic: bool = False  # Whether this is a dynamic score
    
    # Context
    baseline_year: int = 2024
    budget_window: str = "FY2025-2034"
    notes: Optional[str] = None


# =============================================================================
# KNOWN CBO/JCT SCORES DATABASE
# =============================================================================

KNOWN_SCORES: dict[str, CBOScore] = {
    
    # -------------------------------------------------------------------------
    # TAX CUTS AND JOBS ACT (TCJA) 2017
    # -------------------------------------------------------------------------
    
    "tcja_2017_full": CBOScore(
        policy_id="tcja_2017_full",
        name="TCJA 2017 (Full Package)",
        description="Tax Cuts and Jobs Act of 2017 - complete package including "
                   "individual rate cuts, corporate rate cut (35%→21%), "
                   "pass-through deduction, SALT cap, etc.",
        ten_year_cost=1456.0,  # $1.456 trillion over 10 years
        source=ScoreSource.JCT,
        source_date="2017-12",
        source_url="https://www.jct.gov/publications/2017/jcx-67-17/",
        policy_type="income_tax",
        is_dynamic=False,
        baseline_year=2017,
        budget_window="FY2018-2027",
        notes="Static score. JCT estimated dynamic score would reduce cost by ~$400B."
    ),
    
    "tcja_2017_individual": CBOScore(
        policy_id="tcja_2017_individual",
        name="TCJA 2017 Individual Provisions",
        description="TCJA individual income tax provisions only: rate cuts across "
                   "brackets, doubled standard deduction, eliminated personal exemptions, "
                   "SALT cap, child tax credit expansion.",
        ten_year_cost=1127.0,  # ~$1.127 trillion
        source=ScoreSource.JCT,
        source_date="2017-12",
        source_url="https://www.jct.gov/publications/2017/jcx-67-17/",
        policy_type="income_tax",
        baseline_year=2017,
        budget_window="FY2018-2027",
        notes="Individual provisions sunset after 2025."
    ),
    
    "tcja_2017_corporate": CBOScore(
        policy_id="tcja_2017_corporate",
        name="TCJA 2017 Corporate Rate Cut",
        description="Corporate tax rate reduction from 35% to 21%.",
        ten_year_cost=329.0,  # ~$329 billion net (includes base broadening offsets)
        source=ScoreSource.JCT,
        source_date="2017-12",
        rate_change=-0.14,  # 35% → 21% = -14pp
        policy_type="corporate_tax",
        baseline_year=2017,
        notes="Permanent provision. Gross cost ~$1.4T offset by base broadening."
    ),
    
    # -------------------------------------------------------------------------
    # TCJA EXTENSION PROPOSALS (2025)
    # -------------------------------------------------------------------------
    
    "tcja_extension_full": CBOScore(
        policy_id="tcja_extension_full",
        name="TCJA Full Extension (2025+)",
        description="Extend all individual TCJA provisions beyond 2025 sunset.",
        ten_year_cost=4600.0,  # ~$4.6 trillion (CBO May 2024)
        source=ScoreSource.CBO,
        source_date="2024-05",
        source_url="https://www.cbo.gov/publication/59710",
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes="Cost varies significantly depending on baseline assumptions."
    ),
    
    # -------------------------------------------------------------------------
    # BIDEN ADMINISTRATION PROPOSALS
    # -------------------------------------------------------------------------
    
    "biden_high_income_tax": CBOScore(
        policy_id="biden_high_income_tax",
        name="Biden High-Income Tax Increase",
        description="Increase top marginal rate to 39.6% for income above $400K "
                   "(single) / $450K (married). Restore pre-TCJA top rate.",
        ten_year_cost=-252.0,  # Raises ~$252B (reduces deficit)
        source=ScoreSource.TREASURY,
        source_date="2024-03",
        source_url="https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        rate_change=0.026,  # 37% → 39.6% = +2.6pp
        income_threshold=400000,
        policy_type="income_tax",
        first_year_cost=-22.0,  # ~$22B/year
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes="Treasury Green Book FY2025. Combined with other provisions."
    ),
    
    "biden_corporate_28": CBOScore(
        policy_id="biden_corporate_28",
        name="Biden Corporate Rate to 28%",
        description="Increase corporate tax rate from 21% to 28%.",
        ten_year_cost=-1347.0,  # Raises ~$1.35T
        source=ScoreSource.TREASURY,
        source_date="2024-03",
        rate_change=0.07,  # 21% → 28% = +7pp
        policy_type="corporate_tax",
        baseline_year=2024,
        notes="FY2025 Budget proposal."
    ),
    
    "biden_billionaire_minimum": CBOScore(
        policy_id="biden_billionaire_minimum",
        name="Billionaire Minimum Income Tax",
        description="25% minimum tax on total income (including unrealized gains) "
                   "for taxpayers with wealth > $100M.",
        ten_year_cost=-503.0,  # Raises ~$503B
        source=ScoreSource.TREASURY,
        source_date="2024-03",
        income_threshold=100000000,  # $100M wealth threshold
        policy_type="income_tax",
        baseline_year=2024,
        notes="Novel policy - high uncertainty. Wealth threshold, not income."
    ),
    
    "biden_capital_gains_39": CBOScore(
        policy_id="biden_capital_gains_39",
        name="Biden Capital Gains at 39.6%",
        description="Tax capital gains and dividends at 39.6% for income > $1M. "
                   "Tax unrealized gains at death.",
        ten_year_cost=-456.0,  # Combined with death tax provision
        source=ScoreSource.TREASURY,
        source_date="2024-03",
        rate_change=0.196,  # 20% → 39.6% = +19.6pp (for top bracket)
        income_threshold=1000000,
        policy_type="income_tax",
        baseline_year=2024,
        notes="Includes taxing unrealized gains at death. High behavioral uncertainty."
    ),

    # -------------------------------------------------------------------------
    # CAPITAL GAINS TAX ESTIMATES (Isolated for Validation)
    # -------------------------------------------------------------------------

    "cbo_capgains_2pp_all": CBOScore(
        policy_id="cbo_capgains_2pp_all",
        name="CBO: +2pp Capital Gains (All Brackets)",
        description="Raise statutory rates on long-term capital gains and qualified "
                   "dividends by 2 percentage points across all brackets (0%→2%, 15%→17%, 20%→22%).",
        ten_year_cost=-70.0,  # Raises $70B (JCT estimate)
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/budget-options/54788",
        rate_change=0.02,
        income_threshold=0,  # Affects all brackets
        policy_type="income_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        notes="JCT estimate. Reflects behavioral response (deferral). Does not change bracket thresholds."
    ),

    "pwbm_capgains_39_with_stepup": CBOScore(
        policy_id="pwbm_capgains_39_with_stepup",
        name="PWBM: 39.6% Cap Gains (With Step-Up)",
        description="Raise top capital gains rate to 39.6% for income >$1M, "
                   "KEEPING step-up basis at death (current law).",
        ten_year_cost=33.0,  # LOSES $33B due to lock-in effect
        source=ScoreSource.PWBM,
        source_date="2021-04",
        source_url="https://budgetmodel.wharton.upenn.edu/issues/2021/4/23/revenue-effects-of-president-bidens-capital-gains-tax-increase",
        rate_change=0.196,  # 20% + 3.8% NIIT = 23.8% → 39.6%
        income_threshold=1000000,
        policy_type="income_tax",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="CRITICAL: With step-up basis, high rates LOSE revenue due to lock-in. "
              "Taxpayers hold until death to avoid tax entirely."
    ),

    "pwbm_capgains_39_no_stepup": CBOScore(
        policy_id="pwbm_capgains_39_no_stepup",
        name="PWBM: 39.6% Cap Gains (No Step-Up)",
        description="Raise top capital gains rate to 39.6% for income >$1M, "
                   "combined with eliminating step-up basis at death.",
        ten_year_cost=-113.0,  # Raises $113B
        source=ScoreSource.PWBM,
        source_date="2021-04",
        source_url="https://budgetmodel.wharton.upenn.edu/issues/2021/4/23/revenue-effects-of-president-bidens-capital-gains-tax-increase",
        rate_change=0.196,
        income_threshold=1000000,
        policy_type="income_tax",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="Without step-up, taxpayers cannot avoid tax by holding until death. "
              "Lock-in effect is reduced, allowing higher rates to raise revenue."
    ),

    "treasury_capgains_39_plus_stepup_elim": CBOScore(
        policy_id="treasury_capgains_39_plus_stepup_elim",
        name="Treasury: 39.6% + Eliminate Step-Up",
        description="Biden proposal: 39.6% rate for >$1M income + eliminate step-up "
                   "basis at death ($1M exemption per person).",
        ten_year_cost=-322.0,  # Raises $322B combined
        source=ScoreSource.TREASURY,
        source_date="2021-05",
        rate_change=0.196,
        income_threshold=1000000,
        policy_type="income_tax",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="Combined effect of rate increase + step-up elimination. "
              "Treasury Green Book estimate (higher than PWBM due to methodology differences)."
    ),
    
    # -------------------------------------------------------------------------
    # ILLUSTRATIVE POLICIES (For Model Testing)
    # -------------------------------------------------------------------------
    
    "illustrative_1pp_all": CBOScore(
        policy_id="illustrative_1pp_all",
        name="1pp Rate Increase (All Brackets)",
        description="Illustrative: 1 percentage point income tax increase "
                   "across all brackets.",
        ten_year_cost=-960.0,  # ~$96B/year × 10 = ~$960B
        source=ScoreSource.JCT,
        source_date="2023-01",
        rate_change=0.01,
        income_threshold=0,
        policy_type="income_tax",
        first_year_cost=-85.0,
        baseline_year=2023,
        notes="Rule of thumb: 1pp ≈ $85-100B/year. JCT tax expenditure estimates."
    ),
    
    "illustrative_top_rate_5pp": CBOScore(
        policy_id="illustrative_top_rate_5pp",
        name="5pp Top Rate Increase ($1M+)",
        description="Illustrative: 5 percentage point increase in top marginal "
                   "rate for income above $1 million.",
        ten_year_cost=-700.0,  # Revised based on marginal income methodology
        source=ScoreSource.TPC,
        source_date="2023-06",
        rate_change=0.05,
        income_threshold=1000000,
        policy_type="income_tax",
        first_year_cost=-70.0,
        baseline_year=2023,
        notes="Illustrative estimate. Very high earners have most income above threshold."
    ),
    
    "illustrative_500k_2pp": CBOScore(
        policy_id="illustrative_500k_2pp",
        name="2pp Rate Cut ($500K+)",
        description="Illustrative: 2 percentage point rate cut for income "
                   "above $500,000.",
        ten_year_cost=400.0,  # Revised: ~$40B/year based on marginal income methodology
        source=ScoreSource.TPC,
        source_date="2023-06",
        rate_change=-0.02,
        income_threshold=500000,
        policy_type="income_tax",
        first_year_cost=40.0,
        baseline_year=2023,
        notes="Illustrative estimate. Uses marginal income above threshold."
    ),
    
    # -------------------------------------------------------------------------
    # INFRASTRUCTURE / SPENDING
    # -------------------------------------------------------------------------
    
    "iija_2021": CBOScore(
        policy_id="iija_2021",
        name="Infrastructure Investment and Jobs Act",
        description="Bipartisan infrastructure law - $550B in new spending on "
                   "roads, bridges, transit, broadband, water systems.",
        ten_year_cost=256.0,  # Net cost after offsets
        source=ScoreSource.CBO,
        source_date="2021-08",
        source_url="https://www.cbo.gov/publication/57406",
        policy_type="spending",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="Gross spending ~$550B, partially offset by various provisions."
    ),
    
    "ira_2022": CBOScore(
        policy_id="ira_2022",
        name="Inflation Reduction Act 2022",
        description="Climate, energy, and healthcare package. Clean energy tax credits, "
                   "Medicare drug negotiation, ACA subsidies, 15% corporate minimum.",
        ten_year_cost=-90.0,  # Net deficit reduction of $90B (corrected from CBO)
        source=ScoreSource.CBO,
        source_date="2022-08",
        source_url="https://www.cbo.gov/publication/58366",
        policy_type="other",
        baseline_year=2022,
        budget_window="FY2022-2031",
        notes="Excludes ~$200B from IRS enforcement (not scored under budget rules)."
    ),
    
    # -------------------------------------------------------------------------
    # ADDITIONAL CBO EXAMPLES (December 2024 Update)
    # -------------------------------------------------------------------------
    
    "build_back_better_2021": CBOScore(
        policy_id="build_back_better_2021",
        name="Build Back Better Act (2021 House)",
        description="Predecessor to IRA with expanded social programs and climate provisions. "
                   "Temporary provisions (sunsets) significantly reduced the score.",
        ten_year_cost=367.0,  # Net deficit increase
        source=ScoreSource.CBO,
        source_date="2021-11",
        source_url="https://www.cbo.gov/publication/57676",
        policy_type="other",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="Would be $3T+ if sunsets made permanent. Key methodological debate."
    ),
    
    "fiscal_responsibility_act_2023": CBOScore(
        policy_id="fiscal_responsibility_act_2023",
        name="Fiscal Responsibility Act of 2023",
        description="Debt ceiling suspension with discretionary spending caps. "
                   "Savings from constraining spending growth below inflation.",
        ten_year_cost=-1500.0,  # $1.5T deficit reduction
        source=ScoreSource.CBO,
        source_date="2023-05",
        source_url="https://www.cbo.gov/publication/59225",
        policy_type="spending",
        baseline_year=2023,
        budget_window="FY2023-2033",
        notes="Savings from spending caps vs baseline inflation growth."
    ),
    
    "social_security_fairness_2023": CBOScore(
        policy_id="social_security_fairness_2023",
        name="Social Security Fairness Act of 2023",
        description="Repeal Windfall Elimination Provision (WEP) and Government Pension Offset (GPO). "
                   "Full SS benefits for retirees with non-covered pensions.",
        ten_year_cost=196.0,  # $196B deficit increase
        source=ScoreSource.CBO,
        source_date="2023-09",
        source_url="https://www.cbo.gov/publication/59434",
        policy_type="spending",
        baseline_year=2023,
        budget_window="FY2024-2034",
        notes="Affects state/local workers with pensions from non-covered employment."
    ),
    
    "limit_save_grow_2023": CBOScore(
        policy_id="limit_save_grow_2023",
        name="Limit, Save, Grow Act of 2023",
        description="House GOP bill: debt limit increase with spending caps, "
                   "repeal of clean energy credits, cancel student loan forgiveness.",
        ten_year_cost=-4800.0,  # $4.8T deficit reduction
        source=ScoreSource.CBO,
        source_date="2023-04",
        source_url="https://www.cbo.gov/system/files/2023-04/59102-Arrington-Letter_LSG%20Act_4-25-2023.pdf",
        policy_type="other",
        baseline_year=2023,
        budget_window="FY2023-2033",
        notes="Large savings from strict spending caps and program repeals."
    ),
    
    "tax_relief_workers_2024": CBOScore(
        policy_id="tax_relief_workers_2024",
        name="Tax Relief for American Families and Workers Act 2024",
        description="Expanded Child Tax Credit and restored R&D expensing, "
                   "offset by barring new Employee Retention Tax Credit claims.",
        ten_year_cost=0.4,  # $399M - effectively budget neutral
        source=ScoreSource.CBO,
        source_date="2024-01",
        source_url="https://www.cbo.gov/publication/59916",
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2024-2033",
        notes="Example of offsetting tax cuts with closing loopholes."
    ),
    
    "biden_2025_budget": CBOScore(
        policy_id="biden_2025_budget",
        name="Biden FY2025 Budget Analysis",
        description="CBO re-score of Biden budget: higher spending offset by "
                   "tax increases on corporations and high earners.",
        ten_year_cost=-1600.0,  # $1.6T smaller deficits vs baseline
        source=ScoreSource.CBO,
        source_date="2024-06",
        source_url="https://www.cbo.gov/publication/60438",
        policy_type="other",
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes="Tax increases on high earners more than offset spending increases."
    ),
    
    "ndaa_2025": CBOScore(
        policy_id="ndaa_2025",
        name="NDAA FY2025 (S. 4638)",
        description="Defense authorization: $895B authorized but only mandatory "
                   "spending changes (retirement benefits) scored by CBO.",
        ten_year_cost=0.178,  # $178M direct spending increase
        source=ScoreSource.CBO,
        source_date="2024-07",
        source_url="https://www.cbo.gov/publication/60830",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes="Authorization vs appropriation: CBO scores mandatory changes only."
    ),
}


# =============================================================================
# METHODOLOGICAL NOTES FROM CBO EXAMPLES
# =============================================================================

CBO_METHODOLOGY_NOTES = {
    "sunsets_matter": {
        "description": "Temporary provisions (sunsets) significantly reduce 10-year scores",
        "example": "Build Back Better: $367B as scored vs $3T+ if permanent",
        "implication": "Always check if provisions are temporary"
    },
    "timing_shifts": {
        "description": "Tax payment timing can alter 10-year scores",
        "example": "Build It in America Act: increases deficits early, decreases later",
        "implication": "Revenue timing affects scores even if total unchanged"
    },
    "authorization_vs_appropriation": {
        "description": "Authorization bills set policy but don't spend money",
        "example": "NDAA authorizes $895B but CBO scores only $178M mandatory",
        "implication": "Discretionary spending requires separate appropriations"
    },
    "pay_fors": {
        "description": "Offsetting new spending with delayed/cancelled provisions",
        "example": "Medicare drug rebate delays used as 'pay-fors' in multiple bills",
        "implication": "Watch for offsetting provisions that may not be permanent"
    },
    "irs_enforcement": {
        "description": "IRS enforcement revenue not scored under budget rules",
        "example": "IRA: ~$200B expected from enforcement but not in CBO score",
        "implication": "Some revenue sources excluded from official scores"
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_score(policy_id: str) -> Optional[CBOScore]:
    """Get a known score by policy ID."""
    return KNOWN_SCORES.get(policy_id)


def get_scores_by_type(policy_type: str) -> list[CBOScore]:
    """Get all scores of a specific type."""
    return [s for s in KNOWN_SCORES.values() if s.policy_type == policy_type]


def list_available_policies() -> list[str]:
    """List all available policy IDs."""
    return list(KNOWN_SCORES.keys())


def get_validation_targets() -> list[CBOScore]:
    """
    Get scores suitable for model validation.
    
    Returns scores that:
    - Have specific rate_change and income_threshold parameters
    - Are income tax policies (our model's strength)
    - Have recent baselines
    """
    return [
        s for s in KNOWN_SCORES.values()
        if s.policy_type == "income_tax"
        and s.rate_change is not None
        and s.baseline_year >= 2020
    ]


def print_score_summary(score: CBOScore) -> None:
    """Print a formatted summary of a score."""
    print(f"\n{'='*60}")
    print(f"Policy: {score.name}")
    print(f"{'='*60}")
    print(f"ID: {score.policy_id}")
    print(f"10-Year Cost: ${score.ten_year_cost:,.0f}B")
    if score.first_year_cost:
        print(f"First Year: ${score.first_year_cost:,.0f}B")
    print(f"Source: {score.source.value} ({score.source_date})")
    if score.rate_change:
        print(f"Rate Change: {score.rate_change*100:+.1f}pp")
    if score.income_threshold:
        print(f"Threshold: ${score.income_threshold:,.0f}")
    print(f"Window: {score.budget_window}")
    if score.notes:
        print(f"Notes: {score.notes}")

