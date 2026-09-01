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
from enum import Enum
from typing import Literal

PolicyTypeLabel = Literal[
    "income_tax",
    "corporate_tax",
    "capital_gains_tax",
    "payroll_tax",
    "spending",
    "tariff",
    "comprehensive",
    "other",
]

#: The policy *shape* the validation stack can build from a score record.
#: Dispatch is on the shape, not on a single hard-coded ``policy_type``.
ValidationShape = Literal[
    "ordinary_rate",
    "capital_gains",
    "corporate_rate",
    "payroll_rate",
    "spending",
]

#: Generic (out-of-sample) dispatch is limited to records whose published
#: target sits on a baseline close enough to the model's own that baseline
#: drift does not dominate the error. Vintage matching is Phase D.
MIN_GENERIC_BASELINE_YEAR = 2020


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
    source_url: str | None = None

    # Policy parameters for replication
    rate_change: float | None = None
    income_threshold: float | None = None
    policy_type: PolicyTypeLabel = "income_tax"

    # Scoring details
    first_year_cost: float | None = None  # First year effect if known
    is_dynamic: bool = False  # Whether this is a dynamic score

    # Context
    baseline_year: int = 2024
    budget_window: str = "FY2025-2034"
    notes: str | None = None
    # When True, the rate change applies to AGI-inclusive income (incl. preferential
    # capital gains / QDIV). Ordinary-bracket rate changes leave this False so the
    # Generic scorer excludes preferential income via ordinary_income_base=True.
    agi_inclusive_base: bool = False

    # -- Validation dispatch metadata -------------------------------------
    # Every record must either be runnable by some validation runner or say,
    # in one line, why it is not. ``tests/test_validation_targets.py`` asserts
    # the accounting closes (no record is silently dropped).
    runnable: bool = True
    not_runnable_reason: str | None = None
    # When set, the record is scored by that scorecard category's specialized
    # (calibrated) runner. Such records are excluded from the Generic
    # out-of-sample dispatch so they are never counted in both tiers.
    specialized_runner: str | None = None

    # -- Extra shape parameters -------------------------------------------
    # The fiscal year the *source* says the policy takes effect. Left None for
    # records that start with the scoring window. Recorded from the source, so
    # it is a pre-registered input, never a knob turned to close a gap.
    effective_start_year: int | None = None
    # The budget baseline vintage the record should be scored on, as a
    # ``BaselineVintage`` value (e.g. "cbo_feb_2024"). None keeps the runner's
    # default (the model's current baseline).
    scoring_vintage: str | None = None
    # Capital gains: whether the reform also eliminates step-up basis at death.
    eliminate_step_up: bool = False
    # Capital gains: per-decedent exclusion under a step-up-elimination reform.
    # None keeps the module default ($1M, the Biden design).
    step_up_exemption: float | None = None
    # Spending: the annual level change the *source itself* states, plus its
    # growth / phase-in / one-time structure. Left None when the published
    # target is a net-of-offsets total from which no annual level can be read
    # off — deriving one from the target would be fitting, not prediction.
    annual_amount_billions: float | None = None
    annual_growth_rate: float = 0.02
    phase_in_years: int = 1
    is_one_time: bool = False
    spending_category: Literal["defense", "nondefense", "mandatory"] = "nondefense"


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
        notes="Static score. JCT estimated dynamic score would reduce cost by ~$400B.",
        runnable=False,
        not_runnable_reason="Comprehensive 2017 package (individual rates, corporate rate, SALT cap, credits); no single rate/threshold shape.",
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
        notes="Individual provisions sunset after 2025.",
        runnable=False,
        not_runnable_reason="Bundled individual package (rates + standard deduction + exemption repeal + CTC); not a single rate change.",
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
        notes="Permanent provision. Gross cost ~$1.4T offset by base broadening.",
        runnable=False,
        not_runnable_reason="Target is net of base broadening on an FY2018-2027 baseline; the rate-only corporate path scores the gross cut.",
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
        # CBO, "Budgetary Outcomes Under Alternative Assumptions About Spending
        # and Revenues" (8 May 2024). Was 59710, which is the February 2024
        # Budget and Economic Outlook -- the baseline the CBO options battery
        # is scored against, not the source of this $4.6T figure.
        source_url="https://www.cbo.gov/publication/60271",
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes="Cost varies significantly depending on baseline assumptions.",
        specialized_runner="TCJA",
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
        notes="FY2025 Budget proposal.",
        specialized_runner="Corporate",
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
        notes="Novel policy - high uncertainty. Wealth threshold, not income.",
        runnable=False,
        not_runnable_reason="Minimum tax on unrealized gains at a $100M wealth threshold; the model has no wealth-base shape.",
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
        policy_type="capital_gains_tax",
        baseline_year=2024,
        notes="Includes taxing unrealized gains at death. High behavioral uncertainty. "
              "Scored on the uncalibrated Generic capital-gains path: SOI auto-populated "
              "realizations and baseline rate above the $1M threshold, the frozen module-"
              "default elasticities (0.8 short-run / 0.4 long-run) and step-up elimination. "
              "It is NOT one of the three calibrated CapitalGains scenarios, which carry "
              "hand-set per-case elasticity and lock-in tuples.",
        eliminate_step_up=True,  # "Tax unrealized gains at death" is part of the proposal as described
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
        policy_type="capital_gains_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        notes="JCT estimate. Reflects behavioral response (deferral). Does not change bracket thresholds. "
              "Validated via the CapitalGains specialized runner.",
        specialized_runner="CapitalGains",
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
        policy_type="capital_gains_tax",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="CRITICAL: With step-up basis, high rates LOSE revenue due to lock-in. "
              "Taxpayers hold until death to avoid tax entirely. "
              "Validated via the CapitalGains specialized runner.",
        specialized_runner="CapitalGains",
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
        policy_type="capital_gains_tax",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="Without step-up, taxpayers cannot avoid tax by holding until death. "
              "Lock-in effect is reduced, allowing higher rates to raise revenue. "
              "Validated via the CapitalGains specialized runner.",
        specialized_runner="CapitalGains",
        eliminate_step_up=True,
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
        policy_type="capital_gains_tax",
        baseline_year=2021,
        budget_window="FY2022-2031",
        notes="Combined effect of rate increase + step-up elimination. "
              "Treasury Green Book estimate (higher than PWBM due to methodology differences). "
              "Scored on the uncalibrated Generic capital-gains path with the same frozen "
              "module-default elasticities as biden_capital_gains_39 — and, being the same "
              "policy shape, it necessarily receives the same prediction even though the two "
              "published targets differ from each other by 42%.",
        eliminate_step_up=True,
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
        notes=(
            "Illustrative estimate. Very high earners have most income above threshold. "
            "AGI-inclusive base: TPC scores this on taxable income that includes the "
            "preferential (LTCG/QDIV) portion, so the Generic scorer must NOT apply the "
            "ordinary-income-base correction. Diagnostic: the uniform ordinary-base "
            "correction worsens this case 7%->30% (the AGI-inclusive tell)."
        ),
        agi_inclusive_base=True,
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
        notes=(
            "Illustrative estimate. Uses marginal income above threshold. "
            "AGI-inclusive base: TPC scores this on taxable income that includes the "
            "preferential (LTCG/QDIV) portion, so the Generic scorer must NOT apply the "
            "ordinary-income-base correction. Diagnostic: the uniform ordinary-base "
            "correction worsens this case 9%->30% (the AGI-inclusive tell)."
        ),
        agi_inclusive_base=True,
    ),

    # -------------------------------------------------------------------------
    # PRESET-BACKED OUT-OF-SAMPLE TARGETS
    #
    # Promoted in Phase A from ``fiscal_model.app_data.CBO_SCORE_MAP``. Each of
    # these presets already shipped with a published number but had no
    # validation runner, so the number was never actually scored. They run on
    # the uncalibrated Generic path (SOI base, ETI 0.25) with **no** target
    # fitting; their pre-registration rows live in
    # ``fiscal_model/validation/preregistered.py``.
    #
    # The fourth CBO_SCORE_MAP orphan named in the Phase A plan, "Biden 2025
    # Proposal" (-$252B), is the *same* Treasury Green Book target already
    # carried here as ``biden_high_income_tax``; it is deliberately not
    # duplicated, which would double-count one prediction.
    # -------------------------------------------------------------------------

    "warren_ultramillionaire_surtax_3pp": CBOScore(
        policy_id="warren_ultramillionaire_surtax_3pp",
        name="Warren Ultra-Millionaire Surtax (3pp >$2M)",
        description="3 percentage point surtax on AGI above $2 million.",
        ten_year_cost=-350.0,
        source=ScoreSource.TPC,
        source_date="2020",
        source_url="https://www.taxpolicycenter.org/",
        rate_change=0.03,
        income_threshold=2_000_000,
        policy_type="income_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        notes=(
            "Promoted from CBO_SCORE_MAP ('3pp surtax on AGI >$2M; TPC-range estimate'). "
            "AGI-inclusive base: the surtax applies to AGI, which contains the "
            "preferential LTCG/QDIV portion, so the ordinary-income-base correction "
            "must NOT be applied. Secondhand provenance: the preset carries a "
            "TPC-range figure and a bare taxpolicycenter.org URL, not a line item "
            "(Phase E)."
        ),
        agi_inclusive_base=True,
    ),

    "top_rate_45": CBOScore(
        policy_id="top_rate_45",
        name="Top Rate to 45% (+8pp above the 37% bracket floor)",
        description="Raise the top marginal ordinary rate from 37% to 45% on income "
                   "above the current 37% bracket floor ($609,350 single, 2025).",
        ten_year_cost=-420.0,
        source=ScoreSource.TPC,
        source_date="2023",
        source_url="https://www.taxpolicycenter.org/",
        rate_change=0.08,
        income_threshold=609_350,
        policy_type="income_tax",
        baseline_year=2023,
        budget_window="FY2024-2033",
        notes=(
            "Promoted from CBO_SCORE_MAP ('Raise top marginal rate from 37% to 45%; "
            "TPC-range estimate'). Ordinary-bracket rate change, so it scores on the "
            "ordinary-income base. The target itself is internally inconsistent with "
            "illustrative_top_rate_5pp in this same database and from the same source "
            "(+5pp above $1M = -$700B), which implies a larger rate increase on a "
            "wider base raising less; treat -$420B as secondhand until a line-item "
            "source replaces it (Phase E)."
        ),
    ),

    "medicare_surcharge_2pp": CBOScore(
        policy_id="medicare_surcharge_2pp",
        name="High-Earner Medicare Surcharge (2pp >$400K)",
        description="2 percentage point Medicare surcharge on wage and investment "
                   "income above $400,000.",
        ten_year_cost=-310.0,
        source=ScoreSource.TREASURY,
        source_date="2024",
        source_url="https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        rate_change=0.02,
        income_threshold=400_000,
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes=(
            "Promoted from CBO_SCORE_MAP ('+2pp Medicare surcharge on investment + wage "
            "income >$400K'). AGI-inclusive base: investment income is explicitly in the "
            "surcharge base, so the ordinary-income-base correction must NOT be applied."
        ),
        agi_inclusive_base=True,
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
        notes="Gross spending ~$550B, partially offset by various provisions.",
        runnable=False,
        not_runnable_reason="Target is net of offsets; the source's $550B gross outlay is a different quantity, so no annual level can be read off it.",
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
        notes="Excludes ~$200B from IRS enforcement (not scored under budget rules).",
        runnable=False,
        not_runnable_reason="Comprehensive package (energy credits, drug pricing, ACA subsidies, corporate minimum); no single shape.",
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
        notes="Would be $3T+ if sunsets made permanent. Key methodological debate.",
        runnable=False,
        not_runnable_reason="Comprehensive bill whose score is dominated by heterogeneous provision sunsets.",
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
        notes="Savings from spending caps vs baseline inflation growth.",
        runnable=False,
        not_runnable_reason="Savings come from discretionary caps relative to baseline growth, not a fixed annual outlay change.",
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
        notes="Affects state/local workers with pensions from non-covered employment.",
        runnable=False,
        not_runnable_reason="WEP/GPO repeal; the model has no covered-vs-noncovered pension benefit module.",
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
        notes="Large savings from strict spending caps and program repeals.",
        runnable=False,
        not_runnable_reason="Comprehensive bill (spending caps + clean-energy credit repeal + loan-forgiveness cancellation).",
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
        notes="Example of offsetting tax cuts with closing loopholes.",
        runnable=False,
        not_runnable_reason="Near-neutral package (CTC + R&D expensing offset by ERTC claim limits); no rate/threshold shape.",
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
        notes="Tax increases on high earners more than offset spending increases.",
        runnable=False,
        not_runnable_reason="Whole-budget re-score against the CBO baseline, not a single provision.",
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
        notes="Authorization vs appropriation: CBO scores mandatory changes only.",
        runnable=False,
        not_runnable_reason="Authorization bill; only $178M of mandatory retirement-benefit changes are scored, below model resolution.",
    ),

    # -------------------------------------------------------------------------
    # 2025 RECONCILIATION AND RECENT PROPOSALS
    # -------------------------------------------------------------------------

    "reconciliation_2025": CBOScore(
        policy_id="reconciliation_2025",
        name="2025 Reconciliation Act (as enacted)",
        description="Combined tax and spending provisions of 2025 reconciliation",
        ten_year_cost=4_800.0,  # CBO preliminary estimate ~$4.8T
        source=ScoreSource.CBO,
        source_date="2025-08",
        source_url="https://www.cbo.gov/publication/62105",
        policy_type="comprehensive",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="Includes TCJA extension, new credits, spending cuts. Estimate may vary.",
        runnable=False,
        not_runnable_reason="Comprehensive enacted package; provision-level targets (JCX-35-25) are Phase D.",
    ),

    "trump_tariffs_2025": CBOScore(
        policy_id="trump_tariffs_2025",
        name="2025 Tariff Actions (combined)",
        description="Tariffs on China, steel/aluminum, autos, and reciprocal tariffs",
        ten_year_cost=-2_700.0,  # Revenue raiser, ~$270B/yr
        source=ScoreSource.CBO,
        source_date="2025-04",
        source_url="https://www.cbo.gov/publication/62105",
        policy_type="tariff",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="Highly uncertain. Depends on trade volume response and retaliation. "
              "CBO Feb 2026 baseline incorporates enacted tariffs.",
        runnable=False,
        not_runnable_reason="Requires the tariff module (import base x pass-through elasticity); not wired into the validation dispatch.",
    ),

    # -------------------------------------------------------------------------
    # INDIVIDUAL TARIFF ESTIMATES (For Granular Validation)
    # -------------------------------------------------------------------------

    "trump_universal_tariff_10": CBOScore(
        policy_id="trump_universal_tariff_10",
        name="Universal 10% Tariff",
        description="10% tariff on all imports with ~70% effective coverage. "
                   "Raises ~$2T revenue but costs consumers ~$1,700/household annually.",
        ten_year_cost=-2000.0,  # Revenue raiser
        source=ScoreSource.TPC,
        source_date="2024-10",
        source_url="https://taxfoundation.org/research/all/federal/trump-tariffs-biden-tariffs/",
        rate_change=0.10,
        policy_type="tariff",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="Tax Foundation/Yale Budget Lab estimate. Revenue offset by consumer costs. "
              "Highly uncertain - depends on trade volume response and pass-through elasticity.",
        runnable=False,
        not_runnable_reason="Requires the tariff module (import base x pass-through elasticity); not wired into the validation dispatch.",
    ),

    "trump_china_tariff_60": CBOScore(
        policy_id="trump_china_tariff_60",
        name="60% China Tariff",
        description="60% tariff on Chinese imports above existing ~20% average tariff rate. "
                   "Affects ~$215B of effective import base.",
        ten_year_cost=-500.0,  # Revenue raiser
        source=ScoreSource.TPC,
        source_date="2024-10",
        source_url="https://taxfoundation.org/research/all/federal/trump-tariffs-biden-tariffs/",
        rate_change=0.60,
        policy_type="tariff",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="Tax Foundation estimate. Import substitution reduces revenue significantly "
              "at this rate. Elasticity effects more pronounced than for universal tariff.",
        runnable=False,
        not_runnable_reason="Requires the tariff module (import base x pass-through elasticity); not wired into the validation dispatch.",
    ),

    "auto_tariff_25": CBOScore(
        policy_id="auto_tariff_25",
        name="25% Auto Tariff",
        description="25% tariff on imported vehicles and parts. "
                   "Effective base ~$133B after USMCA exemptions (~65% of total auto imports).",
        ten_year_cost=-100.0,  # Revenue raiser
        source=ScoreSource.TPC,
        source_date="2024-10",
        rate_change=0.25,
        policy_type="tariff",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="CRFB/TPC estimate. USMCA exempts significant portion of imports. "
              "Retaliation risk from trading partners is high.",
        runnable=False,
        not_runnable_reason="Requires the tariff module (import base x pass-through elasticity); not wired into the validation dispatch.",
    ),

    "steel_aluminum_tariff_25": CBOScore(
        policy_id="steel_aluminum_tariff_25",
        name="25% Steel & Aluminum Tariff",
        description="25% tariff on steel and aluminum imports (~$50B import base).",
        ten_year_cost=-60.0,  # Revenue raiser
        source=ScoreSource.TPC,
        source_date="2024-10",
        rate_change=0.25,
        policy_type="tariff",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="TPC estimate. Narrow sectoral tariff with lower revenue impact than broad tariffs. "
              "Domestic steel/aluminum producers benefit but consuming industries face higher costs.",
        runnable=False,
        not_runnable_reason="Requires the tariff module (import base x pass-through elasticity); not wired into the validation dispatch.",
    ),

    "reciprocal_tariffs_20": CBOScore(
        policy_id="reciprocal_tariffs_20",
        name="Reciprocal Tariffs (~20pp average)",
        description="Match trading partners' tariff rates, resulting in ~20pp average increase. "
                   "Affects ~50% of import base (~$1,600B).",
        ten_year_cost=-1200.0,  # Revenue raiser
        source=ScoreSource.TPC,
        source_date="2024-10",
        rate_change=0.20,
        policy_type="tariff",
        baseline_year=2025,
        budget_window="2026-2035",
        notes="TPC/Yale Budget Lab estimate. Highly uncertain due to complexity of calculating "
              "truly reciprocal rates and unpredictable negotiation outcomes.",
        runnable=False,
        not_runnable_reason="Requires the tariff module (import base x pass-through elasticity); not wired into the validation dispatch.",
    ),

    # -------------------------------------------------------------------------
    # CBO, OPTIONS FOR REDUCING THE DEFICIT: 2025 TO 2034 (December 2024)
    # -------------------------------------------------------------------------
    # Publication 60557; https://www.cbo.gov/publication/60557
    #
    # 76 independently scored single-provision options. The 14 alternatives the
    # *uncalibrated* path can express - drawn from 11 of the options - are entered
    # here as out-of-sample targets; the other 65 options carry a one-line
    # exclusion reason in ``fiscal_model/validation/cbo_options.py``.
    #
    # Baselines (PDF p. 2, "Notes About This Report"): revenue options are
    # measured against CBO's February 2024 baseline (pub. 59710) and spending
    # options against the June 2024 baseline (pub. 60039). Both are scored on
    # ``BaselineVintage.CBO_FEB_2024``; the repository has no June-2024 vintage,
    # and that mismatch is recorded on each spending row of the manifest.
    #
    # Every target is the option's *own* published 10-year total (report pp.
    # 46-75), not the Table 1-1 range, because a range cannot be compared with
    # a model score.

    "cbo_opt45_all_rates_1pp": CBOScore(
        policy_id="cbo_opt45_all_rates_1pp",
        name="CBO Option 45: All Ordinary Rates +1pp",
        description="Raise all tax rates on ordinary income by 1 percentage point",
        ten_year_cost=-1_185.3,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.01,
        income_threshold=0.0,
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 45, alternative 1 (report p. 55). "
              "Estimated by the staff of the Joint Committee on Taxation.",
    ),

    "cbo_opt45_top4_brackets_2pp": CBOScore(
        policy_id="cbo_opt45_top4_brackets_2pp",
        name="CBO Option 45: Top Four Brackets +2pp",
        description="Raise tax rates on ordinary income in the four highest "
                    "brackets by 2 percentage points",
        ten_year_cost=-569.5,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.02,
        # 2025 single-filer floor of the 24% bracket (IRS Rev. Proc. 2024-40).
        # The generic path takes one threshold, so this stands in for a
        # filing-status-specific bracket boundary.
        income_threshold=103_350.0,
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 45, alternative 2 (report p. 55).",
    ),

    "cbo_opt46_agi_surtax_1pp_20k": CBOScore(
        policy_id="cbo_opt46_agi_surtax_1pp_20k",
        name="CBO Option 46: 1pp AGI Surtax Above $20K",
        description="Impose a surtax of 1 percentage point on AGI above $20,000 "
                    "for single filers and $40,000 for joint filers",
        ten_year_cost=-1_440.1,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.01,
        income_threshold=20_000.0,
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        agi_inclusive_base=True,
        notes="CBO Options 2025-2034, option 46, alternative 1 (report p. 56). "
              "Single-filer threshold; the model has no filing-status dimension.",
    ),

    "cbo_opt46_agi_surtax_2pp_100k": CBOScore(
        policy_id="cbo_opt46_agi_surtax_2pp_100k",
        name="CBO Option 46: 2pp AGI Surtax Above $100K",
        description="Impose a surtax of 2 percentage points on AGI above $100,000 "
                    "for single filers and $200,000 for joint filers",
        ten_year_cost=-1_051.0,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.02,
        income_threshold=100_000.0,
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        agi_inclusive_base=True,
        notes="CBO Options 2025-2034, option 46, alternative 2 (report p. 56).",
    ),

    "cbo_opt47_ltcg_qdiv_2pp": CBOScore(
        policy_id="cbo_opt47_ltcg_qdiv_2pp",
        name="CBO Option 47: LTCG and Qualified Dividends +2pp",
        description="Raise the tax rates on long-term capital gains and qualified "
                    "dividends by 2 percentage points",
        ten_year_cost=-103.3,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.02,
        income_threshold=0.0,
        policy_type="capital_gains_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 47 (report p. 57). Applies to every "
              "rate bracket, so the threshold is zero.",
    ),

    "cbo_opt51_gains_at_death": CBOScore(
        policy_id="cbo_opt51_gains_at_death",
        name="CBO Option 51: Tax Accrued Gains at Death",
        description="Include accrued capital gains in the last income tax return "
                    "of decedents (constructive realization at death)",
        ten_year_cost=-536.1,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.0,
        income_threshold=0.0,
        policy_type="capital_gains_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        eliminate_step_up=True,
        step_up_exemption=0.0,
        notes="CBO Options 2025-2034, option 51, alternative 2 (report p. 61). "
              "No rate change and no per-decedent exclusion, so the whole score "
              "runs through the module's gains-at-death channel.",
    ),

    "cbo_opt61_new_payroll_tax_1pct": CBOScore(
        policy_id="cbo_opt61_new_payroll_tax_1pct",
        name="CBO Option 61: New 1% Payroll Tax on All Earnings",
        description="Impose a new payroll tax of 1 percent on all earnings",
        ten_year_cost=-1_281.5,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.01,
        policy_type="payroll_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 61, alternative 1 (report p. 72). "
              "Scored on the Medicare base (all covered earnings, no taxable "
              "maximum), which is this option's base.",
    ),

    "cbo_opt61_new_payroll_tax_2pct": CBOScore(
        policy_id="cbo_opt61_new_payroll_tax_2pct",
        name="CBO Option 61: New 2% Payroll Tax on All Earnings",
        description="Impose a new payroll tax of 2 percent on all earnings",
        ten_year_cost=-2_540.0,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.02,
        policy_type="payroll_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 61, alternative 2 (report p. 72).",
    ),

    "cbo_opt64_corporate_rate_1pp": CBOScore(
        policy_id="cbo_opt64_corporate_rate_1pp",
        name="CBO Option 64: Corporate Rate +1pp",
        description="Increase the corporate income tax rate by 1 percentage point, "
                    "from 21 percent to 22 percent",
        ten_year_cost=-135.7,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.01,
        policy_type="corporate_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 64 (report p. 75).",
    ),

    "cbo_opt37_international_affairs": CBOScore(
        policy_id="cbo_opt37_international_affairs",
        name="CBO Option 37: Cut International Affairs Funding 25%",
        description="Reduce the total international affairs budget by 25 percent",
        ten_year_cost=-187.0,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2026,
        scoring_vintage="cbo_feb_2024",
        annual_amount_billions=-23.0,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        notes="CBO Options 2025-2034, option 37 (report p. 46). Annual level is "
              "CBO's own first-year budget authority; the target is CBO's 10-year "
              "outlay total, so the residual is the budget-authority-to-outlay lag.",
    ),

    "cbo_opt38_national_service": CBOScore(
        policy_id="cbo_opt38_national_service",
        name="CBO Option 38: End National Community Service Funding",
        description="Eliminate federal funding for the Corporation for National and "
                    "Community Service except the National Service Trust",
        ten_year_cost=-10.3,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2026,
        scoring_vintage="cbo_feb_2024",
        annual_amount_billions=-1.3,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        notes="CBO Options 2025-2034, option 38 (report p. 47).",
    ),

    "cbo_opt39_pell_eligibility": CBOScore(
        policy_id="cbo_opt39_pell_eligibility",
        name="CBO Option 39: Tighten Pell Grant Eligibility",
        description="Restrict Pell grant eligibility to students eligible for the "
                    "maximum award",
        ten_year_cost=-22.1,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2026,
        scoring_vintage="cbo_feb_2024",
        annual_amount_billions=-2.5,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        notes="CBO Options 2025-2034, option 39 (report p. 48). Target is the "
              "discretionary outlay total; the separate -$9.2B mandatory effect is "
              "outside this shape.",
    ),

    "cbo_opt42_nondefense_discretionary": CBOScore(
        policy_id="cbo_opt42_nondefense_discretionary",
        name="CBO Option 42: Cut Selected Nondefense Discretionary Spending",
        description="Reduce funding for transportation and education grant programs "
                    "by one-third",
        ten_year_cost=-339.0,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2026,
        scoring_vintage="cbo_feb_2024",
        annual_amount_billions=-41.0,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        notes="CBO Options 2025-2034, option 42 (report p. 51). Annual level is "
              "CBO's first-year spending authority.",
    ),

    "cbo_opt43_state_local_grants": CBOScore(
        policy_id="cbo_opt43_state_local_grants",
        name="CBO Option 43: Cut Certain State and Local Grants",
        description="Reduce new funding for five grant programs by 25 percent in "
                    "2026 and 50 percent thereafter",
        ten_year_cost=-66.7,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2026,
        scoring_vintage="cbo_feb_2024",
        annual_amount_billions=-12.0,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        notes="CBO Options 2025-2034, option 43, total row (report pp. 52-53). "
              "The first-year budget authority is inflated by IIJA advance funding, "
              "which the level shape then carries across the whole window.",
    ),

    # -------------------------------------------------------------------------
    # PHASE D: ENACTED-LAW REPLICATIONS (component-level, out-of-sample)
    # -------------------------------------------------------------------------
    #
    # The bundle records above (``iija_2021``, ``ira_2022``,
    # ``fiscal_responsibility_act_2023``, ``social_security_fairness_2023``,
    # ``tax_relief_workers_2024``, ``ndaa_2025``) carry a *net* total that no
    # single policy shape can construct, and they stay excluded. What follows
    # are new records for the individual components whose own annual level the
    # CBO cost estimate itself states, so a bottom-up prediction is possible
    # without reading anything off the target.
    #
    # One rule sets ``annual_amount_billions`` for all of them, fixed before
    # any of them was scored:
    #
    #   the source's own stated funding or benefit change for the first fiscal
    #   year in which the provision is fully in effect - excluding any year the
    #   source itself describes as carrying retroactive or transition amounts -
    #   grown at the module default 2%/yr.
    #
    # ``effective_start_year`` is the first fiscal year the source's table shows
    # a non-zero effect, so the model window matches the source's own non-zero
    # window.

    "ssfa_wep_gpo_repeal_outlays": CBOScore(
        policy_id="ssfa_wep_gpo_repeal_outlays",
        name="Social Security Fairness Act: WEP/GPO repeal (direct spending)",
        description="Repeal the Windfall Elimination Provision and the Government "
                    "Pension Offset. Off-budget direct spending for OASI and DI "
                    "benefits; no revenue provisions.",
        ten_year_cost=195.65,
        source=ScoreSource.CBO,
        source_date="2024-09",
        source_url="https://www.cbo.gov/system/files/2024-09/hr82.pdf",
        policy_type="spending",
        baseline_year=2024,
        budget_window="FY2024-2034",
        effective_start_year=2025,
        annual_amount_billions=19.67,
        annual_growth_rate=0.02,
        spending_category="mandatory",
        runnable=False,
        not_runnable_reason=(
            "Pre-registered in Phase D; scored from the Phase D scoring commit "
            "onward (see preregistered.py)."
        ),
        notes="CBO cost estimate for H.R. 82, Social Security Fairness Act of 2023 "
              "(9 September 2024), Table 1. Total direct-spending outlays "
              "FY2024-2034 = $195,650M; FY2024 is zero. Annual level = the FY2026 "
              "outlay ($10,730M WEP + $10,270M GPO - $1,330M interaction = "
              "$19,670M): CBO states that benefits owed for months before "
              "enactment 'would be paid retroactively mostly in fiscal year 2025', "
              "so FY2025 ($24,970M) is not a steady-state level. Distinct from the "
              "rounded $196B bundle record 'social_security_fairness_2023'.",
    ),

    "fra_2023_discretionary_caps": CBOScore(
        policy_id="fra_2023_discretionary_caps",
        name="Fiscal Responsibility Act 2023: discretionary caps (outlays)",
        description="Statutory caps on most discretionary funding for 2024 and 2025 "
                    "under section 101(a), plus the lower funding base those caps "
                    "carry forward through 2033.",
        ten_year_cost=-1331.8,
        source=ScoreSource.CBO,
        source_date="2023-05",
        source_url=(
            "https://www.cbo.gov/system/files/2023-05/hr3746_Letter_McCarthy.pdf"
        ),
        policy_type="spending",
        baseline_year=2023,
        budget_window="FY2024-2033",
        effective_start_year=2024,
        annual_amount_billions=-112.3,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        runnable=False,
        not_runnable_reason=(
            "Pre-registered in Phase D; scored from the Phase D scoring commit "
            "onward (see preregistered.py)."
        ),
        notes="CBO, 'CBO's Estimate of the Budgetary Effects of H.R. 3746, the "
              "Fiscal Responsibility Act of 2023' (30 May 2023), discretionary "
              "table (PDF p. 14): total discretionary outlay change under the caps "
              "= -$1,331.8B over FY2024-2033. Annual level = the FY2024 budget "
              "authority reduction CBO states for section 101(a) (-$112.3B); FY2025 "
              "is -$135.9B. This is the caps component only - the bill's -$1.5T "
              "total also bundles the $45B Toxic Exposures Fund appropriation, "
              "student-loan payment resumption, an IRS rescission, administrative "
              "PAYGO and debt service, none of which this shape can express.",
    ),

    "iija_2021_discretionary": CBOScore(
        policy_id="iija_2021_discretionary",
        name="IIJA 2021: discretionary spending component (outlays)",
        description="The discretionary funding provided by the Infrastructure "
                    "Investment and Jobs Act and the outlays that flow from it.",
        ten_year_cost=415.448,
        source=ScoreSource.CBO,
        source_date="2021-08",
        source_url=(
            "https://www.cbo.gov/system/files/2021-08/hr3684_infrastructure.pdf"
        ),
        policy_type="spending",
        baseline_year=2021,
        budget_window="FY2022-2031",
        effective_start_year=2022,
        annual_amount_billions=162.996,
        annual_growth_rate=0.02,
        spending_category="nondefense",
        runnable=False,
        not_runnable_reason=(
            "Pre-registered in Phase D; scored from the Phase D scoring commit "
            "onward (see preregistered.py)."
        ),
        notes="CBO cost estimate for Senate Amendment 2137 to H.R. 3684 (revised "
              "9 August 2021), Table 1: 'Changes in Discretionary Spending' - "
              "budget authority $446,306M, estimated outlays $415,448M over "
              "FY2021-2031. Annual level = the FY2022 budget authority CBO states "
              "($162,996M), the first and only fully-funded year; the authorization "
              "then falls to $70.1B, $68.5B, $68.1B, $66.2B and about $2B/yr. "
              "Deliberately kept in the battery as the sharpest available evidence "
              "for the missing budget-authority-to-outlay spend-out model.",
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

def get_score(policy_id: str) -> CBOScore | None:
    """Get a known score by policy ID."""
    return KNOWN_SCORES.get(policy_id)


def get_scores_by_type(policy_type: str) -> list[CBOScore]:
    """Get all scores of a specific type."""
    return [s for s in KNOWN_SCORES.values() if s.policy_type == policy_type]


def list_available_policies() -> list[str]:
    """List all available policy IDs."""
    return list(KNOWN_SCORES.keys())


def validation_shape(score: CBOScore) -> ValidationShape | None:
    """
    Return the policy shape a score record can be built into, or ``None``.

    This is the dispatch key that replaced the old ``income_tax``-only gate.
    It is a *pure* function of the record's parameters — it deliberately does
    not consult ``runnable`` or ``specialized_runner``, so callers can tell
    "no shape" apart from "deliberately excluded".
    """
    if score.policy_type == "income_tax":
        return "ordinary_rate" if score.rate_change is not None else None
    if score.policy_type == "capital_gains_tax":
        return "capital_gains" if score.rate_change is not None else None
    if score.policy_type == "corporate_tax":
        return "corporate_rate" if score.rate_change is not None else None
    if score.policy_type == "payroll_tax":
        return "payroll_rate" if score.rate_change is not None else None
    if score.policy_type == "spending":
        return "spending" if score.annual_amount_billions is not None else None
    return None


def get_validation_targets() -> list[CBOScore]:
    """
    Get the scores the **Generic (out-of-sample) runner** should score.

    A record qualifies when it is runnable, has a constructible shape, is not
    already covered by a specialized calibrated runner (which would double
    count it across both accuracy tiers), and sits on a baseline no older than
    :data:`MIN_GENERIC_BASELINE_YEAR`.
    """
    return [
        s for s in KNOWN_SCORES.values()
        if s.runnable
        and s.specialized_runner is None
        and validation_shape(s) is not None
        and s.baseline_year >= MIN_GENERIC_BASELINE_YEAR
    ]


def get_specialized_targets() -> list[CBOScore]:
    """Records scored by a specialized (calibrated) runner, not the Generic one."""
    return [s for s in KNOWN_SCORES.values() if s.runnable and s.specialized_runner]


def get_excluded_scores() -> list[CBOScore]:
    """Records deliberately not scored, each carrying a one-line reason."""
    return [s for s in KNOWN_SCORES.values() if not s.runnable]


def describe_target_coverage() -> dict[str, object]:
    """
    Account for every record in :data:`KNOWN_SCORES`.

    ``total`` must always equal ``generic + specialized + excluded``; anything
    in ``unaccounted`` is a record that claims to be runnable but has neither a
    shape nor a specialized runner, i.e. a silently dropped benchmark.
    """
    generic = get_validation_targets()
    specialized = get_specialized_targets()
    excluded = get_excluded_scores()
    accounted = {s.policy_id for s in (*generic, *specialized, *excluded)}
    return {
        "total": len(KNOWN_SCORES),
        "generic": sorted(s.policy_id for s in generic),
        "specialized": sorted(s.policy_id for s in specialized),
        "excluded": sorted(s.policy_id for s in excluded),
        "unaccounted": sorted(set(KNOWN_SCORES) - accounted),
    }


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

