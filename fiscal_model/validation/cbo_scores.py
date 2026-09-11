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
    "tax_expenditure",
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
    "tax_expenditure",
]

#: Generic (out-of-sample) dispatch is limited to records whose published
#: target sits on a baseline close enough to the model's own that baseline
#: drift does not dominate the error. Vintage matching is Phase D.
#:
#: **A record that states its own window is exempt, and the exemption is
#: narrower than it looks.** This constant guards against one thing: scoring a
#: target published for one decade over a different decade, so that what the
#: error measures is nominal growth between the two. ``scoring_window_first_year``
#: (PR #126) is the field that removes exactly that, by opening the model's
#: window in the first year of the decade the target's own document covers. So
#: the year floor applies to records that take the runner's default window, and
#: a record that names its own decade is admitted however old its baseline is -
#: which is a narrowing of the guard's scope to the case it was written for, not
#: a loosening of its value. Lane R3's 2018-volume rows are the seven this
#: admits; the vintage mismatch that remains is *stated* on each manifest row
#: rather than absorbed, as it is for ``biden_corporate_28_fy2022`` and the
#: Options-2024 spending rows.
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
    # The first fiscal year of the ten-year window the *source* published its
    # total over. None keeps the runner's own window
    # (``DEFAULT_VALIDATION_START_YEAR``); set, the runner opens its window in
    # that year, so the model scores the same ten fiscal years the target
    # covers. A **window** is not a **vintage**: no shape that carries one today
    # reads a baseline level, so this needs no historical baseline to work.
    # Transcribed from the source's own table exactly like
    # ``annual_authority_path_billions`` - a pre-registered shape input, never a
    # knob turned to close a gap, and moving one goes through the manifest's
    # supersede rule (see ``preregistered.FY2022_TARGET_WINDOW_RULE``).
    scoring_window_first_year: int | None = None
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
    # Spending: the source's own year-by-year budget authority, for a proposal
    # whose authority is a *schedule* rather than a level - a multi-year
    # authorization that ends, say. When set it replaces
    # ``annual_amount_billions`` x growth as the shape's authority path. Like
    # the level, it is transcribed from the source's own table and is a
    # pre-registered shape input, never a knob turned to close a gap.
    annual_authority_path_billions: tuple[float, ...] | None = None
    annual_growth_rate: float = 0.02
    phase_in_years: int = 1
    is_one_time: bool = False
    spending_category: Literal["defense", "nondefense", "mandatory"] = "nondefense"
    # Tax expenditure: the reform's own design, as the source states it. The
    # key indexes ``TAX_EXPENDITURE_DATA_KEYS``; a cap is read in dollars of
    # the *excluded or deducted quantity*, and ``expenditure_caps_by_tier``
    # carries a design that sets a different limit per coverage tier — which is
    # how every published version of the employer-health option is written.
    # These are shape inputs transcribed from the source, never fitted: the
    # uncalibrated path scores such a record in the module's *derived* mode, so
    # the fitted per-benchmark annual is never read.
    expenditure_key: str | None = None
    expenditure_action: Literal[
        "eliminate", "cap", "phase_out", "convert", "expand"
    ] = "cap"
    expenditure_cap_amount: float | None = None
    expenditure_caps_by_tier: dict[str, float] | None = None
    # Income tax: the per-filing-status thresholds the *source itself* prints,
    # keyed by ``fiscal_model.data.irs_soi.FILING_STATUSES``. A partial mapping
    # is the natural shape - any status left out takes ``income_threshold`` -
    # so a source that names two amounts is recorded as the two amounts it
    # names. Like every other entry in this block these are transcribed shape
    # inputs, never fitted: see ``FILING_STATUS_THRESHOLD_RULE`` in
    # ``validation/core.py`` for the rule covering statuses a source does not
    # name, and ``planning/lanes/W7_filing_status_split.md`` for the lane.
    income_threshold_by_filing_status: dict[str, float] | None = None
    # Income tax: which statutory ordinary-income bracket (1-7) this record's
    # threshold is the *floor of*, where its own source says the boundary is a
    # bracket rather than an amount the source chose. Set, the runner reads the
    # four per-status floors from CBO's own published parameter schedule for
    # each year being scored, on this record's own ``scoring_vintage``; unset,
    # the threshold above is used as it always has been.
    #
    # This is the index and not the dollars, because a bracket boundary is one
    # thing stated in four places and re-indexed annually - and because the
    # amounts are CBO's to publish, not this record's to transcribe. It is a
    # pre-registered shape input like every other entry in this block, read off
    # the source's own words under ``STATUTORY_BRACKET_SCHEDULE_RULE`` in
    # ``validation/core.py``, never from a dollar figure that happens to match
    # one. See ``planning/lanes/R4_parameter_schedule.md``.
    statutory_bracket_index: int | None = None
    # Whether this record may serve as an interpolation anchor for the Ask
    # assistant's capability gate (``assistant/benchmarks.py``).
    #
    # **This field exists because PR #122 named the trap and lane R3 walked
    # into it.** ``candidate_anchors`` turns every ``KNOWN_SCORES`` record with
    # a matching ``policy_type`` and a non-zero ``rate_change`` into an anchor,
    # so registering a validation benchmark is also, silently, an edit to a
    # shipped user-facing answer. PR #122 kept ``biden_corporate_28_fy2022``
    # out of ``KNOWN_SCORES`` altogether for exactly this reason - "adding it
    # would have put a 2021-vintage figure into the set a 2026 user's 'what
    # would +4pp raise?' interpolates across" - but a record that has to be
    # *scored* cannot be kept out, so the exclusion has to be a field.
    #
    # It was not hypothetical: registering lane R3's three older corporate rows
    # moved the assistant's own acceptance case, a 21% -> 25% corporate rate,
    # from **-$741.35B to -$542.80B**, because CBO's 2018 and 2020 editions
    # price a point of rate a third lower than its 2024 one. That is a
    # user-facing number moving on a lane that opened no module.
    #
    # The rule: a benchmark published for a decade this deployment does not
    # serve is a valid *validation target* and not a valid *anchor for a
    # question asked today*. Default True, so no pre-existing record changes.
    assistant_anchor_eligible: bool = True


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
        # Wave 4 Tier 1 revision (preregistered.py, biden_high_income_tax.v1 ->
        # .v2). The Green Book row this record cites — "Increase the top
        # marginal income tax rate for high-income earners" (report p. 242;
        # PDF p. 250) — prints $245,924 million over FY2025-2034, not
        # $252,000 million. Nothing in the model reads the target.
        ten_year_cost=-245.9,  # Raises ~$246B (reduces deficit)
        source=ScoreSource.TREASURY,
        source_date="2024-03",
        source_url="https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        rate_change=0.026,  # 37% → 39.6% = +2.6pp
        # All four amounts are printed in the proposal itself (report p. 78;
        # PDF p. 86): "The top marginal tax rate would apply to taxable income
        # over $450,000 for married individuals filing a joint return and
        # surviving spouses, $400,000 for unmarried individuals (other than
        # surviving spouses and head of household filers), $425,000 for head of
        # household filers, and $225,000 for married individuals filing a
        # separate return." Note the direction: the separate-return floor is
        # BELOW the unmarried one, so recording it enlarges the base.
        income_threshold=400000,
        income_threshold_by_filing_status={
            "joint": 450_000.0,
            "head_of_household": 425_000.0,
            "separate": 225_000.0,
        },
        policy_type="income_tax",
        first_year_cost=-22.0,  # ~$22B/year
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes=(
            "Treasury Green Book FY2025, Table of Revenue Estimates, row "
            "'Increase the top marginal income tax rate for high-income "
            "earners' — which Treasury prints as its own line, so the earlier "
            "'combined with other provisions' caveat was wrong about the table."
        )
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
        name="Biden Capital Gains at Ordinary Rates (FY2025 Green Book)",
        description="Reform the taxation of capital income: tax long-term capital "
                   "gains and qualified dividends at ordinary rates for taxpayers "
                   "with taxable income over $1M, and treat transfers by gift or "
                   "at death as realization events with a $5M per-donor exclusion.",
        # Re-sourced in Phase E. The previous -456.0 appears in no Treasury
        # volume; the FY2025 Green Book's combined "Reform the taxation of
        # capital income" row is $288,583M (report p. 242; PDF p. 250).
        # Treasury never splits the rate change from the realization-at-death
        # change, so this single row is the whole proposal.
        ten_year_cost=-288.6,
        source=ScoreSource.TREASURY,
        source_date="2024-03",
        source_url="https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        rate_change=0.196,  # 23.8% → 43.4% (footnote 18: the 39.6% top rate is assumed in place)
        income_threshold=1000000,
        policy_type="capital_gains_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        notes="Re-sourced in Phase E to the FY2025 Green Book line item; the prior "
              "-$456B target was unsourced and internally inconsistent with the "
              "FY2022 row carried as treasury_capgains_39_plus_stepup_elim (the two "
              "differed by 42%). The shape now matches the source's own definition: "
              "**taxable** income over $1M (FY2022 said AGI) and a **$5M per-donor** "
              "exclusion for gains at death (FY2022 said $1M per person). Nothing was "
              "tuned; only the published definition was copied in. "
              "Scored on the uncalibrated Generic capital-gains path: SOI auto-populated "
              "realizations and baseline rate above the $1M threshold, the frozen module-"
              "default elasticities (0.8 short-run / 0.4 long-run) and step-up elimination. "
              "It is NOT one of the three calibrated CapitalGains scenarios, which carry "
              "hand-set per-case elasticity and lock-in tuples.",
        eliminate_step_up=True,  # "realization events" at gift/death is half the proposal
        step_up_exemption=5_000_000.0,  # FY2025 Green Book, report p. 89
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
        notes="Combined effect of rate increase + step-up elimination, and the "
              "'combined' is confirmed rather than assumed: the FY2022 Green Book's "
              "Table of Revenue Estimates carries ONE row for 'Reform the taxation of "
              "capital income' ($322,485M over FY2022-2031) and no separate "
              "realization-at-death line anywhere in the table, even though the "
              "narrative section states the rate change and the transfers-at-death "
              "change as two proposals under one heading (report p. 105; PDF p. 111; "
              "re-read 2026-09-02). "
              "Treasury Green Book estimate (higher than PWBM due to methodology differences). "
              "Scored on the uncalibrated Generic capital-gains path with the same frozen "
              "module-default elasticities as biden_capital_gains_39. It no longer receives "
              "the same prediction as that row: Wave 4 gave each row its own volume's "
              "per-donor exclusion ($1M here against the FY2025 volume's $5M), and PR #126 "
              "moved this row onto its own document's FY2022-2031 decade "
              "(scoring_window_first_year below), so the two differ in both the death "
              "channel and the window.",
        eliminate_step_up=True,
        # The window this row's own document published its total over, and the
        # decade the model is therefore scored on. Same fiscal years on both
        # sides; the target is unchanged. See treasury_capgains_39_plus_stepup
        # _elim.v2 in preregistered.py and planning/memos/FY2022_TARGET_WINDOW.md.
        scoring_window_first_year=2022,
    ),

    # -------------------------------------------------------------------------
    # ILLUSTRATIVE POLICIES (For Model Testing)
    # -------------------------------------------------------------------------

    "illustrative_1pp_all": CBOScore(
        policy_id="illustrative_1pp_all",
        name="1pp Rate Increase (All Brackets)",
        description="Illustrative: 1 percentage point income tax increase "
                   "across all brackets.",
        # Lane R2: -$1,081.3B, CBO pub. 58164 Option 13 alternative 1. The
        # -$960B this replaces was a rule of thumb ("1pp ≈ $85-100B/year") in
        # no JCT document. See illustrative_1pp_all.v2 in preregistered.py.
        ten_year_cost=-1_081.3,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        rate_change=0.01,
        income_threshold=0,
        # Same reform and same words as cbo_opt45_all_rates_1pp in a different
        # Options volume - "Raise all tax rates on ordinary income by 1
        # percentage point" - so the boundary is bracket 1's $0 floor, and this
        # row is the schedule path's second byte-identity check. It names no
        # scoring_vintage, so it reads the schedule of the vintage it is scored
        # on, which is the module default; bracket 1 is $0 on all three.
        statutory_bracket_index=1,
        policy_type="income_tax",
        first_year_cost=-72.4,
        baseline_year=2022,
        budget_window="FY2023-2032",
        notes=(
            "CBO, Options for Reducing the Deficit: 2023 to 2032, Volume I: "
            "Larger Reductions (December 2022, publication 58164), Option 13 - "
            "Revenues, 'Increase Individual Income Tax Rates', first "
            "alternative: 'Raise all tax rates on ordinary income by "
            "1 percentage point', -$1,081.3B over FY2023-2032 (report p. 72; "
            "PDF p. 76). 'Data source: Staff of the Joint Committee on "
            "Taxation', which is why the source stays JCT. Ordinary-income "
            "base, in CBO's own words for the alternative: 'in 2023, the top "
            "rate of 37 percent would increase to 38 percent, and in 2026, "
            "the top rate of 39.6 percent would increase to 40.6 percent'."
        ),
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
            "RETIRED in lane R2. -$700B for a +5pp top rate above $1,000,000 is "
            "in no publication. Phase E enumerated TPC's whole sitemap and R2 "
            "added the individual-rate option of all four CBO Options volumes "
            "(2018 pub. 54667 Option 1, 2020 pub. 56783 Option 1, 2022 "
            "pub. 58164 Option 13, 2024 pub. 60557 Option 45): every "
            "alternative in all four is a uniform change at a bracket boundary "
            "or an AGI surtax at the standard deduction, the fourth-bracket "
            "floor, $20,000/$40,000 or $100,000/$200,000. No scorekeeper "
            "prices a rate change at a $1,000,000 threshold. The record called "
            "itself 'Illustrative estimate', which is this repository "
            "describing its own synthetic figure, and docs/VALIDATION.md has "
            "carried it as an open owner decision since Phase E. Withdrawn "
            "rather than corrected: the nearest published quantities are "
            "PWBM's new 39.6% bracket above $1M at $222.4B (FY2026-2035) and "
            "TPC T19-0037 Option 3's 10pp AGI surtax above $2M married / $1M "
            "other at $633.897B, and neither is this reform. The record is "
            "kept so the withdrawal is visible and a future line item can "
            "revive it; see preregistered.py for the full search. "
            "AGI-inclusive base: the record's own note said TPC scores this on "
            "taxable income including the preferential (LTCG/QDIV) portion, "
            "and PR #146 left it on the taxable column for that reason."
        ),
        agi_inclusive_base=True,
        runnable=False,
        not_runnable_reason=(
            "RETIRED (lane R2): the -$700B target is traceable to no published "
            "document; withdrawn from Tier 1 rather than scored against a "
            "number nobody published."
        ),
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
            "RETIRED in lane R2. +$400B for a 2pp rate CUT above $500,000 is in "
            "no publication, and three quarters of the search space cannot "
            "contain it by construction: CBO's Options volumes are "
            "deficit-REDUCTION menus and carry no rate cut at all, in any of "
            "the four editions. JCT scores cuts only as estimates of enacted "
            "or introduced bills, none of which is a 2pp cut at a $500,000 "
            "floor, and Phase E's full TPC sitemap enumeration found nothing. "
            "The record called itself 'Illustrative estimate'. This was the "
            "battery's only rate cut and its only positive target, so Tier 1 "
            "now tests increases only - a real cost of the retirement, "
            "recorded rather than glossed, with the replacement named in "
            "preregistered.py (R3's leg_rev_* series). AGI-inclusive base on "
            "the taxable column, which PR #146 left in place because the "
            "record says taxable income in as many words."
        ),
        agi_inclusive_base=True,
        runnable=False,
        not_runnable_reason=(
            "RETIRED (lane R2): the +$400B target is traceable to no published "
            "document, and no scorekeeper publishes a ten-year estimate of a "
            "rate cut at a $500,000 threshold."
        ),
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
            "RETIRED in lane R2. TPC's *AGI Surtax Options* simulation is "
            "thirteen tables (T19-0037 through T19-0050), every one of them a "
            "10 percent surtax, with exactly one revenue table among them: "
            "T19-0037 (23 September 2019) prices 10pp on AGI above $2,000,000 "
            "unindexed at $585.325B over FY2019-2029, $2.5M at $500.635B, and "
            "$2M married / $1M other at $633.897B. There is no 3pp row, and no "
            "CBO Options volume prices a surtax at a $2M threshold in any of "
            "its four editions. Scaling to 3pp would be constructing a target "
            "rather than reading one, and CBO warns the effects of large "
            "surtaxes 'might not be proportional to the estimates shown here'. "
            "The row's NAME is also wrong: Warren's Ultra-Millionaire Tax Act "
            "is a wealth tax on net worth (2% above $50M, 3% above $1B), so "
            "the 3pp is a wealth rate on an income base and this shape matches "
            "no proposal anybody scored. T19-0037 Option 1 is the same base at "
            "the same threshold on a different rate, so a 10pp case against "
            "$585.325B is registrable - an owner decision, because it moves a "
            "model output. AGI-inclusive base confirmed correct by TPC's own "
            "definition; it is the magnitude that was unsupported."
        ),
        agi_inclusive_base=True,
        runnable=False,
        not_runnable_reason=(
            "RETIRED (lane R2): the -$350B target is traceable to no published "
            "document - TPC's only AGI-surtax revenue table prices 10pp, not "
            "3pp - and the reform itself matches no scored proposal."
        ),
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
            "RETIRED in Phase E. Phase A promoted this from CBO_SCORE_MAP ('Raise top "
            "marginal rate from 37% to 45%; TPC-range estimate') and flagged that the "
            "target is internally inconsistent with illustrative_top_rate_5pp from the "
            "same claimed source (+5pp above $1M = -$700B). The sourcing pass "
            "enumerated TPC's entire sitemap and found no table for a 45% ordinary "
            "rate at any date, and no CBO or JCT option for an +8pp top-bracket "
            "increase either. -$420B is not a published figure, so the case is "
            "withdrawn from the out-of-sample battery rather than scored against a "
            "number nobody published. The record is kept so the withdrawal is visible "
            "and so a future line item can revive it; see "
            "fiscal_model/validation/preregistered.py for the retirement reason and "
            "docs/VALIDATION.md for the PWBM figures that bracket the plausible range."
        ),
        runnable=False,
        not_runnable_reason=(
            "RETIRED (Phase E): the -$420B target is traceable to no published "
            "document; withdrawn from Tier 1 rather than scored against an "
            "unsourced number."
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
            "RETIRED in lane R2, and this is the row that proves the rule "
            "rather than the easy case for it. Treasury's FY2025 Green Book "
            "carries the proposal this record names and it is a 1.2 PERCENTAGE "
            "POINT increase, not 2pp: 'The proposal would increase the "
            "additional Medicare tax rate by 1.2 percentage points for "
            "taxpayers with more than $400,000 of earnings' and the same 1.2pp "
            "on the NIIT, both to 5 percent (report pp. 76-77; PDF pp. 84-85). "
            "Its revenue row prints $403,790M over FY2025-2034 (report p. 242; "
            "PDF p. 250); the FY2024 volume prints $344,371M for the identical "
            "proposal; the FY2023 volume has no such proposal. -$310.0B is "
            "none of them. The only '310,0xx' in the FY2025 volume is the "
            "child-credit expansion at -$310,024M, which is a cost and the "
            "opposite sign. The model's 2pp score sits 1.2% from Treasury's "
            "1.2pp figure, so adopting it would have turned this row into one "
            "of the tier's best by pairing 1.67x the rate with too little "
            "base - two errors cancelling. Restated on the document's own "
            "rate the model reads -$245.2B against -$403.8B, 39.3% UNDER, "
            "which is what this row's accuracy is. A .v2 at -$403.8B with "
            "rate_change=0.012 is the right row and is the owner's to "
            "register, because it moves a model output. Base note kept: the "
            "statutory base is wages plus net investment income, which is "
            "neither SOI column (PR #146)."
        ),
        agi_inclusive_base=True,
        runnable=False,
        not_runnable_reason=(
            "RETIRED (lane R2): -$310B appears in no Green Book row for this "
            "proposal across three volumes, and Treasury's own figure scores a "
            "1.2pp change where this record is 2pp."
        ),
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
        # Was publication 59434, which is CBO's estimate of H.R. 3938 (the Build
        # It in America Act) — a different bill entirely. The right document is
        # CBO's 9 September 2024 estimate of H.R. 82, whose WEP/GPO repeal
        # component is transcribed at $195.65B in the pre-registration manifest
        # (``ssfa_wep_gpo_repeal_outlays.v1``); the $196B here is that figure
        # rounded.
        source_date="2024-09",
        source_url="https://www.cbo.gov/system/files/2024-09/hr82.pdf",
        policy_type="spending",
        baseline_year=2023,
        budget_window="FY2024-2034",
        notes=(
            "Affects state/local workers with pensions from non-covered "
            "employment. The transcribed component figure is $195.65B; this "
            "record carries it rounded."
        ),
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
        notes="UNSOURCED (Phase E). Attributed to CRFB here and in CBO_SCORE_MAP, but "
              "CRFB publishes no standalone 25% auto-tariff figure - four of its "
              "tariff-revenue posts were checked and none itemises autos. The two "
              "primary estimates that do exist are 4-6.5x larger: Yale Budget Lab "
              "$600-650B over 2026-35 and Tax Foundation $386.2B conventional over "
              "2026-2035, neither of which applies this record's USMCA carve-out. "
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
        notes="UNSOURCED (Phase E). This record says TPC and CBO_SCORE_MAP said Tax "
              "Foundation; neither publishes a 25%-rate steel-and-aluminium ten-year "
              "estimate. Tax Foundation's only Section 232 metals figure is $341.4B "
              "conventional over 2026-2035 at the post-2025 50% rates and includes "
              "copper. The app also carried a second, four-times-smaller figure "
              "(-$15B) on the preset label; the labels were reconciled on -$60B in "
              "Phase E so the preset at least shows one number, but the number itself "
              "has no document behind it. Narrow sectoral tariff with lower revenue "
              "impact than broad tariffs; domestic producers benefit but consuming "
              "industries face higher costs.",
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
        # "Raise ALL tax rates on ordinary income" - the boundary is the floor
        # of the lowest statutory bracket, which is $0 in every year of every
        # vintage. Declared rather than left off, because it takes the schedule
        # path end to end and must return this record's existing figure to the
        # cent. See STATUTORY_BRACKET_SCHEDULE_RULE.
        statutory_bracket_index=1,
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
        # 2025 floor of the 24% bracket - the lowest of "the four highest
        # brackets" (24, 32, 35 and 37 percent) the option raises - from IRS
        # Rev. Proc. 2024-40 section 2.01, tables 1-4. Joint returns and
        # surviving spouses use the section 1(j)(2)(A) schedule and start at
        # $206,700; heads of households (1(j)(2)(B)), unmarried individuals
        # (1(j)(2)(C)) and married filing separately (1(j)(2)(D)) all start at
        # $103,350, which is why only the joint amount is stated here.
        income_threshold=103_350.0,
        income_threshold_by_filing_status={"joint": 206_700.0},
        # "in the four highest brackets" - of seven, so the boundary is the
        # floor of bracket 4, and the two amounts above are its CY2025 values.
        # With the index declared, those amounts stop being the applied floors
        # and become the fallback plus the anchor the preferential-income share
        # is measured at: the floors actually applied are CBO's own, per year
        # and per status, on this record's cbo_feb_2024 vintage, whose current
        # law reverts to the 28/33/35/39.6 schedule in CY2026.
        statutory_bracket_index=4,
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes="CBO Options 2025-2034, option 45, alternative 2 (report p. 55). "
              "Bracket floors from IRS Rev. Proc. 2024-40 section 2.01. The "
              "option's own text states that 'the scheduled changes to the "
              "underlying tax brackets and rates would still take effect in "
              "2026', which the model's single fixed threshold cannot express.",
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
        # The option's own alternative label: "a surtax of 1 percentage point
        # would be imposed on AGI above $20,000 for single filers and $40,000
        # for joint filers" (report p. 56). CBO names two amounts; heads of
        # households and married-filing-separately take the single amount under
        # FILING_STATUS_THRESHOLD_RULE.
        income_threshold=20_000.0,
        income_threshold_by_filing_status={"joint": 40_000.0},
        policy_type="income_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        agi_inclusive_base=True,
        notes="CBO Options 2025-2034, option 46, alternative 1 (report p. 56). "
              "Thresholds are the option's own; the base is still taxable "
              "income rather than AGI and is not grown across the window.",
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
        # "a surtax of 2 percentage points would be imposed on AGI above
        # $100,000 for single filers and $200,000 for joint filers"
        # (report p. 56), read under the same rule as alternative 1.
        income_threshold=100_000.0,
        income_threshold_by_filing_status={"joint": 200_000.0},
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
        # JCT, not CBO. Every corporate-rate option in every *Options for
        # Reducing the Deficit* volume carries "Data source: Staff of the
        # Joint Committee on Taxation" verbatim - CBO publishes them, JCT
        # estimates them. Corrected 2026-09-05 by the corporate provenance
        # lane, because "CBO vs Treasury" is the wrong framing for this row's
        # residual and "JCT vs Treasury OTA" is the right one. Nothing in the
        # scoring path reads `source`, so no number moved.
        source=ScoreSource.JCT,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        rate_change=0.01,
        policy_type="corporate_tax",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2025,
        scoring_vintage="cbo_feb_2024",
        notes=(
            "CBO Options 2025-2034, option 64 (report p. 75; PDF p. 81), "
            "estimated by the staff of the Joint Committee on Taxation. "
            "CBO's own Table 1-1 prints 136.0 where the option page and this "
            "target carry 135.7 - CBO's rounding, not a second estimate."
        ),
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

    # -- Option 56: employment-based health benefits ------------------------
    # Excluded from the Phase B battery as leakage — the only path that could
    # score it was the fitted ``cap_employer_health`` annual. Lane L6 built the
    # premium-distribution mechanism that scores a *percentile* cap from the
    # published expenditure level and a distribution of the quantity the cap
    # actually caps, so the option is now expressible without reading any
    # constant fitted to a target.
    "cbo_opt56_employer_health_income_only": CBOScore(
        policy_id="cbo_opt56_employer_health_income_only",
        name="CBO Option 56: Limit the Income-Tax Exclusion for Employer Health Benefits",
        description="Limit only the income tax exclusion for employment-based health "
                    "insurance to the 50th percentile of premiums",
        ten_year_cost=-697.0,
        source=ScoreSource.CBO,
        source_date="2024-12",
        source_url="https://www.cbo.gov/publication/60557",
        policy_type="tax_expenditure",
        baseline_year=2024,
        budget_window="FY2025-2034",
        effective_start_year=2028,
        scoring_vintage="cbo_feb_2024",
        expenditure_key="employer_health",
        expenditure_action="cap",
        expenditure_cap_amount=10_000.0,
        expenditure_caps_by_tier={"single": 10_000.0, "family": 24_400.0},
        notes="CBO Options 2025-2034, option 56, third alternative (report p. 66; "
              "PDF p. 72), 'Decrease (-) in the deficit' row: -$697B over FY2025-2034. "
              "The option takes effect in January 2028 and CBO prints zeros for "
              "2025-2027, so the model window starts there too. The cap dollars are "
              "CBO's own stated design — the 50th percentile of 2026 premiums indexed "
              "to 2028, $10,000 individual and $24,400 family. This is the only one of "
              "the option's three alternatives the module can express: the other two "
              "limit the payroll-tax exclusion as well, and the expenditure module has "
              "no payroll base.",
    ),

    # -------------------------------------------------------------------------
    # LANE R3: THE OTHER THREE *OPTIONS FOR REDUCING THE DEFICIT* VOLUMES
    # -------------------------------------------------------------------------
    #
    # CBO publishes this compendium every two years, and the battery above uses
    # only the 2024 edition. Three earlier editions price the *same* reforms on
    # *different* baselines over *different* decades:
    #
    #   2018  Options for Reducing the Deficit: 2019 to 2028, pub. 54667,
    #         FY2019-2028, CBO April 2018 baseline
    #   2020  Options for Reducing the Deficit: 2021 to 2030, pub. 56783,
    #         FY2021-2030, CBO September 2020 baseline
    #   2022  Options for Reducing the Deficit: 2023 to 2032, pub. 58164
    #         (Volume I) and 58163 (Volume II), FY2023-2032, CBO May 2022
    #         baseline
    #
    # Every figure below is transcribed to
    # ``fiscal_model/data_files/validation/cbo_options_multi_volume*.csv`` by
    # ``scripts/extract_cbo_options_multi_volume.py``, which reads CBO's own
    # workbooks for the 2020 and 2022 volumes (by sheet and row, with the label
    # cell asserted) and re-verifies every 2018 figure against its stated report
    # page in the PDF. The selection rule, fixed before any of these records was
    # written, is :data:`~fiscal_model.validation.preregistered.R3_SELECTION_RULE`,
    # and the verdict for all 100 revenue options in the three volumes - runnable
    # or a one-line reason - is in the options CSV beside it.
    #
    # TWO THINGS EVERY RECORD BELOW CARRIES, AND WHY.
    #
    # ``scoring_window_first_year`` is the first fiscal year of the decade the
    # option's *own* volume published. Without it these rows would measure
    # nominal growth between decades rather than the model: lane R2 found CBO
    # pricing one unchanged 1pp reform at -$884.0B, -$1,081.3B and -$1,185.3B in
    # three consecutive editions, 9.6% apart per two years, and told this lane to
    # read the other volumes "the same way before registering them".
    #
    # ``scoring_vintage="cbo_feb_2024"`` is a STATED MISMATCH, not a match. The
    # repository carries no April-2018, September-2020 or May-2022 baseline;
    # February 2024 is the oldest it has, hence the nearest to all three. The
    # mismatch is recorded on each manifest row exactly as it is for
    # ``biden_corporate_28_fy2022`` and for the Options-2024 spending rows.
    #
    # A WINDOW IS NOT A VINTAGE. No shape here reads a budget level off the
    # baseline object, which is what makes scoring an FY2019 decade on a
    # FY2024-vintage baseline meaningful rather than a category error; the one
    # thing that *is* year-indexed and vintage-bound is the statutory parameter
    # schedule, which covers CY2021-CY2034 on this vintage, so the 2018 volume's
    # two bracket rows have CY2019 and CY2020 clamped to CY2021. That is said out
    # loud by the loader, recorded in each row's known_limitations, and is why
    # their written fallback amounts are CBO's own CY2021 figures - the amount
    # written is the amount actually applied in every year of the window.

    "cbo2019_opt1_all_rates_1pp": CBOScore(
        policy_id="cbo2019_opt1_all_rates_1pp",
        name="CBO 2018 Option 1: All Ordinary Rates +1pp",
        description="Raise all tax rates on ordinary income by 1 percentage point",
        ten_year_cost=-905.4,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.01,
        income_threshold=0.0,
        statutory_bracket_index=1,
        policy_type="income_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 1, first "
              "alternative (report p. 204): 'Raise all tax rates on ordinary "
              "income by 1 percentage point', +$905.4B over FY2019-2028. "
              "'Source: Staff of the Joint Committee on Taxation.' The option "
              "takes effect in January 2019. Bracket 1's floor is $0 in every "
              "year of every vintage, so the schedule path returns the same "
              "threshold the record is written with.",
    ),

    "cbo2019_opt1_top4_brackets_1pp": CBOScore(
        policy_id="cbo2019_opt1_top4_brackets_1pp",
        name="CBO 2018 Option 1: Top Four Brackets +1pp",
        description="Raise ordinary income tax rates in the four highest brackets "
                    "by 1 percentage point",
        ten_year_cost=-222.9,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.01,
        # CBO's own CY2021 bracket-4 floors, from the transcribed parameter
        # schedule (publication 53724, cbo_feb_2024 vintage). CY2021 rather than
        # the option's CY2019 because the schedule this repository carries begins
        # in CY2021 and the loader clamps earlier years to it - so these are the
        # amounts the run actually applies, in every year of the window.
        income_threshold=86_375.0,
        # Only the two statuses whose amount differs from the single
        # floor above; separate and single take it under
        # FILING_STATUS_THRESHOLD_RULE, which is the same number.
        income_threshold_by_filing_status={
            "joint": 172_750.0,
            "head_of_household": 86_350.0,
        },
        statutory_bracket_index=4,
        policy_type="income_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 1, second "
              "alternative (report p. 204): 'Raise all tax rates on ordinary "
              "income in the top four brackets (24 percent and over from 2018 "
              "through 2025, and 28 percent and over after 2025) by 1 "
              "percentage point', +$222.9B over FY2019-2028.",
    ),

    "cbo2019_opt1_top2_brackets_1pp": CBOScore(
        policy_id="cbo2019_opt1_top2_brackets_1pp",
        name="CBO 2018 Option 1: Top Two Brackets +1pp",
        description="Raise ordinary income tax rates in the two highest brackets "
                    "by 1 percentage point",
        ten_year_cost=-123.4,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.01,
        income_threshold=209_425.0,
        income_threshold_by_filing_status={
            "joint": 418_850.0,
            "head_of_household": 209_400.0,
        },
        statutory_bracket_index=6,
        policy_type="income_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 1, third "
              "alternative (report p. 204): 'Raise all tax rates on ordinary "
              "income in the top two brackets (35 percent and over) by 1 "
              "percentage point', +$123.4B over FY2019-2028. 'The two highest "
              "brackets' of seven is the floor of bracket 6; the amounts are "
              "CBO's own CY2021 figures, which the schedule clamp makes the "
              "amounts actually applied.",
    ),

    "cbo2019_opt2_ltcg_qdiv_2pp": CBOScore(
        policy_id="cbo2019_opt2_ltcg_qdiv_2pp",
        name="CBO 2018 Option 2: LTCG and Qualified Dividends +2pp",
        description="Raise the tax rates on long-term capital gains and qualified "
                    "dividends by 2 percentage points",
        ten_year_cost=-69.6,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.02,
        income_threshold=0.0,
        policy_type="capital_gains_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 2, first "
              "alternative (report p. 207): 'Raise rates on long-term capital "
              "gains and dividends by 2 percentage points', +$69.6B over "
              "FY2019-2028. Applies to every rate bracket, so the threshold is "
              "zero. The option's other two alternatives ALSO realign the "
              "preferential-rate brackets with the ordinary brackets, which "
              "CapitalGainsPolicy cannot express; they are recorded as "
              "not-registered in the alternatives CSV.",
    ),

    "cbo2019_opt18_hi_payroll_1pp": CBOScore(
        policy_id="cbo2019_opt18_hi_payroll_1pp",
        name="CBO 2018 Option 18: Medicare HI Payroll Rate +1pp",
        description="Increase the basic Hospital Insurance payroll tax on total "
                    "earnings by 1 percentage point",
        ten_year_cost=-898.3,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.01,
        policy_type="payroll_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 18, first "
              "alternative (report p. 251): +$898.3B over FY2019-2028. Scored "
              "on the same shape as CBO 2024 Option 61 because CBO states the "
              "same base for both: 'Unlike the payroll tax for Social "
              "Security, which applies to earnings up to an annual maximum, "
              "the 2.9 percent HI tax is levied on total earnings.' A 1pp "
              "increase in the basic HI rate on total earnings and a new 1 "
              "percent tax on all covered earnings are the same base times the "
              "same rate; what differs is which trust fund receives it, which "
              "no revenue estimate turns on.",
    ),

    "cbo2019_opt18_hi_payroll_2pp": CBOScore(
        policy_id="cbo2019_opt18_hi_payroll_2pp",
        name="CBO 2018 Option 18: Medicare HI Payroll Rate +2pp",
        description="Increase the basic Hospital Insurance payroll tax on total "
                    "earnings by 2 percentage points",
        ten_year_cost=-1_786.5,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.02,
        policy_type="payroll_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 18, second "
              "alternative (report p. 251): +$1,786.5B over FY2019-2028.",
    ),

    "cbo2019_opt24_corporate_rate_1pp": CBOScore(
        policy_id="cbo2019_opt24_corporate_rate_1pp",
        name="CBO 2018 Option 24: Corporate Rate +1pp",
        description="Increase the corporate income tax rate by 1 percentage point, "
                    "from 21 percent to 22 percent",
        ten_year_cost=-96.3,
        source=ScoreSource.JCT,
        source_date="2018-12",
        source_url="https://www.cbo.gov/publication/54667",
        rate_change=0.01,
        policy_type="corporate_tax",
        baseline_year=2018,
        budget_window="FY2019-2028",
        effective_start_year=2019,
        scoring_window_first_year=2019,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2019-2028 (pub. 54667), revenue option 24 (report "
              "p. 266): +$96.3B over FY2019-2028, 'Source: Staff of the Joint "
              "Committee on Taxation.' The second of four editions of one "
              "reform - $96.3B (FY2019-2028), $99.3B (FY2021-2030), $129.3B "
              "(FY2023-2032), $135.7B (FY2025-2034) - which is what gives the "
              "corporate class more than one observation for the first time.",
    ),

    "cbo2021_opt1_all_rates_1pp": CBOScore(
        policy_id="cbo2021_opt1_all_rates_1pp",
        name="CBO 2020 Option 1: All Ordinary Rates +1pp",
        description="Raise all tax rates on ordinary income by 1 percentage point",
        ten_year_cost=-884.0,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.01,
        income_threshold=0.0,
        statutory_bracket_index=1,
        policy_type="income_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 1, first "
              "alternative (report p. 204): +$884.0B over FY2021-2030, 'Data "
              "source: Staff of the Joint Committee on Taxation.'",
    ),

    "cbo2021_opt1_top4_brackets_1pp": CBOScore(
        policy_id="cbo2021_opt1_top4_brackets_1pp",
        name="CBO 2020 Option 1: Top Four Brackets +1pp",
        description="Raise all tax rates on ordinary income in the top four "
                    "brackets by 1 percentage point",
        ten_year_cost=-203.3,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.01,
        income_threshold=86_375.0,
        # Only the two statuses whose amount differs from the single
        # floor above; separate and single take it under
        # FILING_STATUS_THRESHOLD_RULE, which is the same number.
        income_threshold_by_filing_status={
            "joint": 172_750.0,
            "head_of_household": 86_350.0,
        },
        statutory_bracket_index=4,
        policy_type="income_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 1, second "
              "alternative (report p. 204): +$203.3B over FY2021-2030. The "
              "amounts are CBO's own CY2021 bracket-4 floors from the "
              "transcribed parameter schedule - the option's own first "
              "calendar year.",
    ),

    "cbo2021_opt1_top2_brackets_1pp": CBOScore(
        policy_id="cbo2021_opt1_top2_brackets_1pp",
        name="CBO 2020 Option 1: Top Two Brackets +1pp",
        description="Raise all tax rates on ordinary income in the top two "
                    "brackets by 1 percentage point",
        ten_year_cost=-113.8,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.01,
        income_threshold=209_425.0,
        income_threshold_by_filing_status={
            "joint": 418_850.0,
            "head_of_household": 209_400.0,
        },
        statutory_bracket_index=6,
        policy_type="income_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 1, third "
              "alternative (report p. 204): +$113.8B over FY2021-2030. The "
              "smallest target in the battery, and the only row that prices "
              "the top two brackets alone.",
    ),

    "cbo2021_opt2_ltcg_qdiv_2pp": CBOScore(
        policy_id="cbo2021_opt2_ltcg_qdiv_2pp",
        name="CBO 2020 Option 2: LTCG and Qualified Dividends +2pp",
        description="Raise the tax rates on long-term capital gains and qualified "
                    "dividends by 2 percentage points",
        ten_year_cost=-75.2,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.02,
        income_threshold=0.0,
        policy_type="capital_gains_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 2 (report "
              "p. 207): +$75.2B over FY2021-2030. Unlike the 2018 edition, "
              "this one does not realign the preferential brackets, so the "
              "option is the rate change alone.",
    ),

    "cbo2021_opt15_hi_payroll_1pp": CBOScore(
        policy_id="cbo2021_opt15_hi_payroll_1pp",
        name="CBO 2020 Option 15: Medicare HI Payroll Rate +1pp",
        description="Increase the basic Hospital Insurance payroll tax on total "
                    "earnings by 1 percentage point",
        ten_year_cost=-877.5,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.01,
        policy_type="payroll_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 15, first "
              "alternative (report p. 285): +$877.5B over FY2021-2030. Same "
              "base as CBO 2024 Option 61 and as the 2018 edition's option 18: "
              "the HI tax on total earnings, with no taxable maximum.",
    ),

    "cbo2021_opt15_hi_payroll_2pp": CBOScore(
        policy_id="cbo2021_opt15_hi_payroll_2pp",
        name="CBO 2020 Option 15: Medicare HI Payroll Rate +2pp",
        description="Increase the basic Hospital Insurance payroll tax on total "
                    "earnings by 2 percentage points",
        ten_year_cost=-1_736.3,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.02,
        policy_type="payroll_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 15, second "
              "alternative (report p. 285): +$1,736.3B over FY2021-2030.",
    ),

    "cbo2021_opt19_corporate_rate_1pp": CBOScore(
        policy_id="cbo2021_opt19_corporate_rate_1pp",
        name="CBO 2020 Option 19: Corporate Rate +1pp",
        description="Increase the corporate income tax rate by 1 percentage point, "
                    "from 21 percent to 22 percent",
        ten_year_cost=-99.3,
        source=ScoreSource.JCT,
        source_date="2020-12",
        source_url="https://www.cbo.gov/publication/56783",
        rate_change=0.01,
        policy_type="corporate_tax",
        baseline_year=2020,
        budget_window="FY2021-2030",
        effective_start_year=2021,
        scoring_window_first_year=2021,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2021-2030 (pub. 56783), revenue option 19 (report "
              "p. 293): +$99.3B over FY2021-2030, 'Data source: Staff of the "
              "Joint Committee on Taxation.'",
    ),

    "cbo2023_opt13_top4_brackets_2pp": CBOScore(
        policy_id="cbo2023_opt13_top4_brackets_2pp",
        name="CBO 2022 Option 13: Top Four Brackets +2pp",
        description="Raise tax rates on ordinary income in the four highest "
                    "brackets by 2 percentage points",
        ten_year_cost=-501.9,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        rate_change=0.02,
        income_threshold=95_375.0,
        income_threshold_by_filing_status={
            "joint": 190_750.0,
            "head_of_household": 95_350.0,
        },
        statutory_bracket_index=4,
        policy_type="income_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume I (pub. 58164), option 13, second "
              "alternative (report p. 72): -$501.9B over FY2023-2032. The same "
              "reform cbo_opt45_top4_brackets_2pp scores on the 2024 volume's "
              "decade, so the pair measures the model's sensitivity to the "
              "decade and not two independent predictions. Amounts are CBO's "
              "own CY2023 bracket-4 floors.",
    ),

    "cbo2023_opt13_agi_surtax_1pp_stdded": CBOScore(
        policy_id="cbo2023_opt13_agi_surtax_1pp_stdded",
        name="CBO 2022 Option 13: 1pp AGI Surtax Above the Standard Deduction",
        description="Impose a surtax of 1 percentage point on AGI above the "
                    "standard deduction and exemption",
        ten_year_cost=-1_329.1,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        rate_change=0.01,
        # CBO states this boundary as a FORMULA, not as an amount and not as a
        # bracket index, so STATUTORY_BRACKET_SCHEDULE_RULE does not reach it:
        # the amounts below are the sum of CBO's own published standard
        # deduction and personal exemption for CY2023, the option's own first
        # calendar year, on the vintage this row is scored on. The personal
        # exemption is $0 in CY2023 (suspended by the 2017 act), so the sum is
        # the standard deduction. Held fixed across the window, exactly as CBO's
        # own fixed dollar amounts are in Option 46 - a stated limitation, not a
        # choice of boundary.
        income_threshold=13_850.0,
        income_threshold_by_filing_status={
            "joint": 27_700.0,
            "head_of_household": 20_800.0,
        },
        policy_type="income_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        agi_inclusive_base=True,
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume I (pub. 58164), option 13, third "
              "alternative (report p. 72): -$1,329.1B over FY2023-2032. The "
              "largest revenue raiser in the individual-rate option of any of "
              "the four volumes, and the only AGI surtax outside the 2024 "
              "edition. CBO's own words put it on AGI - 'a surtax of 1 "
              "percentage point on AGI above the standard deduction and "
              "exemption' - which is what AGI_BASE_RULE reads.",
    ),

    "cbo2023_opt13_agi_surtax_2pp_bracket4": CBOScore(
        policy_id="cbo2023_opt13_agi_surtax_2pp_bracket4",
        name="CBO 2022 Option 13: 2pp AGI Surtax Above the Fourth Bracket",
        description="Impose a surtax of 2 percentage points on AGI above the sum "
                    "of the standard deduction, exemptions, and the threshold of "
                    "the fourth ordinary income tax bracket",
        ten_year_cost=-773.8,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        rate_change=0.02,
        # CY2023 standard deduction + personal exemption ($0) + bracket-4 floor,
        # each read from CBO's own transcribed parameter schedule. Read the
        # comment on the row above for why this is an amount rather than a
        # bracket index.
        income_threshold=109_225.0,
        income_threshold_by_filing_status={
            "joint": 218_450.0,
            "head_of_household": 116_150.0,
        },
        policy_type="income_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        agi_inclusive_base=True,
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume I (pub. 58164), option 13, fourth "
              "alternative (report p. 72): -$773.8B over FY2023-2032. This is "
              "the one published surtax whose boundary is stated as a sum of "
              "three statutory parameters rather than as a dollar amount, and "
              "it is registered because all three are parameters CBO itself "
              "publishes for the option's own first calendar year.",
    ),

    "cbo2023_opt15_new_payroll_1pct": CBOScore(
        policy_id="cbo2023_opt15_new_payroll_1pct",
        name="CBO 2022 Option 15: New 1% Payroll Tax on Earnings",
        description="Impose a new payroll tax of 1 percent on earnings",
        ten_year_cost=-1_135.7,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        rate_change=0.01,
        policy_type="payroll_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume I (pub. 58164), option 15, first "
              "alternative (report p. 76): -$1,135.7B over FY2023-2032. The "
              "same reform as CBO 2024 Option 61 alternative 1 on the previous "
              "decade.",
    ),

    "cbo2023_opt15_new_payroll_2pct": CBOScore(
        policy_id="cbo2023_opt15_new_payroll_2pct",
        name="CBO 2022 Option 15: New 2% Payroll Tax on Earnings",
        description="Impose a new payroll tax of 2 percent on earnings",
        ten_year_cost=-2_252.7,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        rate_change=0.02,
        policy_type="payroll_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume I (pub. 58164), option 15, second "
              "alternative (report p. 76): -$2,252.7B over FY2023-2032.",
    ),

    "cbo2023_opt6_employer_health_income_only": CBOScore(
        policy_id="cbo2023_opt6_employer_health_income_only",
        name="CBO 2022 Option 6: Limit the Income-Tax Exclusion for Employer Health Benefits",
        description="Limit only the income tax exclusion for employment-based "
                    "health insurance to the 50th percentile of premiums",
        ten_year_cost=-651.4,
        source=ScoreSource.CBO,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58164",
        policy_type="tax_expenditure",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2026,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        expenditure_key="employer_health",
        expenditure_action="cap",
        expenditure_cap_amount=8_900.0,
        expenditure_caps_by_tier={"single": 8_900.0, "family": 21_600.0},
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume I (pub. 58164), option 6, third "
              "alternative (report p. 30), 'Decrease (-) in the Deficit' row: "
              "-$651.4B over FY2023-2032. The cap dollars are CBO's own stated "
              "design - 'contributions that exceeded $8,900 a year for "
              "individual coverage and $21,600 a year for family coverage "
              "would be included in employees' taxable income', the 50th "
              "percentile of 2024 premiums indexed to 2026 - and the option "
              "takes effect in January 2026, which CBO's zeros for 2023-2025 "
              "confirm. As in the 2024 edition, this is the only one of the "
              "option's three alternatives the module can express: the other "
              "two limit the payroll-tax exclusion as well.",
    ),

    "cbo2023_opt37_ltcg_qdiv_2pp": CBOScore(
        policy_id="cbo2023_opt37_ltcg_qdiv_2pp",
        name="CBO 2022 Option 37: LTCG and Qualified Dividends +2pp",
        description="Raise the tax rates on long-term capital gains and qualified "
                    "dividends by 2 percentage points",
        ten_year_cost=-102.1,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58163",
        rate_change=0.02,
        income_threshold=0.0,
        policy_type="capital_gains_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume II (pub. 58163), revenue option 37 "
              "(report p. 89): -$102.1B over FY2023-2032. Applies to every "
              "rate bracket, so the threshold is zero. Its 2024 sibling "
              "(cbo_opt47_ltcg_qdiv_2pp) carries -$103.3B on the next decade: "
              "CBO's own two editions differ by 1.2% for one unchanged reform, "
              "where the individual-rate option's differ by 9.6%.",
    ),

    "cbo2023_opt50_corporate_rate_1pp": CBOScore(
        policy_id="cbo2023_opt50_corporate_rate_1pp",
        name="CBO 2022 Option 50: Corporate Rate +1pp",
        description="Increase the corporate income tax rate by 1 percentage point, "
                    "from 21 percent to 22 percent",
        ten_year_cost=-129.3,
        source=ScoreSource.JCT,
        source_date="2022-12",
        source_url="https://www.cbo.gov/publication/58163",
        rate_change=0.01,
        policy_type="corporate_tax",
        baseline_year=2022,
        budget_window="FY2023-2032",
        effective_start_year=2023,
        scoring_window_first_year=2023,
        scoring_vintage="cbo_feb_2024",
        # Lane R3: a target published for a decade this deployment does not
        # serve is not an anchor for a question asked today. See the field's
        # own comment on CBOScore.
        assistant_anchor_eligible=False,
        notes="CBO Options 2023-2032 Volume II (pub. 58163), revenue option 50 "
              "(report p. 115): -$129.3B over FY2023-2032, 'Data source: Staff "
              "of the Joint Committee on Taxation.' CORPORATE_PER_POINT_YIELD.md "
              "showed JCT's per-point yield is flat in the rate; these four "
              "editions show what it does in TIME, which the memo could not.",
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
        # Scored on the ten fiscal years CBO's own estimate covers, which
        # ``budget_window`` above has stated since this record was entered.
        # ``iija_2021_discretionary.v3`` in ``preregistered.py``, under
        # ``FY2022_TARGET_WINDOW_RULE``: the target does not move, only the
        # decade it is compared on. ``effective_start_year`` already equalled
        # the window's first year, so the policy's own start does not move
        # either - the whole change is where the scorer's window opens, and
        # therefore whether the $92.6B this path outlays in FY2022-2024 is
        # inside it.
        scoring_window_first_year=2022,
        annual_amount_billions=162.996,
        # The source's own authorization schedule, FY2022-2031. Five figures
        # are stated in CBO's table ($163.0B, $70.1B, $68.5B, $68.1B, $66.2B);
        # the last five years are the remainder of CBO's stated $446,306M
        # budget-authority total spread evenly, which is the "about $2B/yr"
        # the record's own notes already describe. See
        # ``IIJA_AUTHORIZATION_PATH_RULE`` in ``preregistered.py``: one rule
        # sets every year, and no year was chosen by the error it produced.
        annual_authority_path_billions=(
            162.996, 70.1, 68.5, 68.1, 66.2, 2.082, 2.082, 2.082, 2.082, 2.082,
        ),
        annual_growth_rate=0.02,
        spending_category="nondefense",
        notes="CBO cost estimate for Senate Amendment 2137 to H.R. 3684 (revised "
              "9 August 2021), Table 1: 'Changes in Discretionary Spending' - "
              "budget authority $446,306M, estimated outlays $415,448M over "
              "FY2021-2031. Annual level = the FY2022 budget authority CBO states "
              "($162,996M), the first and only fully-funded year; the authorization "
              "then falls to $70.1B, $68.5B, $68.1B, $66.2B and about $2B/yr - "
              "the schedule ``annual_authority_path_billions`` now carries, "
              "registered as 'iija_2021_discretionary.v2'. The level shape that "
              "read only the first year is 'iija_2021_discretionary.v1', "
              "superseded because the source states a schedule and SpendingPolicy "
              "can now express one. Scored on FY2022-2031, the decade this "
              "estimate's own total covers, as 'iija_2021_discretionary.v3'; "
              "v2 scored the same schedule on the runner's FY2025-2034 decade "
              "and left $92.6B of its outlays outside the window.",
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
    if score.policy_type == "tax_expenditure":
        return "tax_expenditure" if score.expenditure_key is not None else None
    return None


def get_validation_targets() -> list[CBOScore]:
    """
    Get the scores the **Generic (out-of-sample) runner** should score.

    A record qualifies when it is runnable, has a constructible shape, is not
    already covered by a specialized calibrated runner (which would double
    count it across both accuracy tiers), and either sits on a baseline no
    older than :data:`MIN_GENERIC_BASELINE_YEAR` **or** states the decade its
    own source published (``scoring_window_first_year``) - see that constant
    for why the second clause is a narrowing rather than a loosening.
    """
    return [
        s for s in KNOWN_SCORES.values()
        if s.runnable
        and s.specialized_runner is None
        and validation_shape(s) is not None
        and (
            s.baseline_year >= MIN_GENERIC_BASELINE_YEAR
            or s.scoring_window_first_year is not None
        )
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

