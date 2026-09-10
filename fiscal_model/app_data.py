"""
Application data for the Fiscal Policy Calculator.

Contains:
- CBO_SCORE_MAP: Official CBO/JCT scores for preset policies
- PRESET_POLICIES: Preset policy configurations
- PRESETS_BY_ID: the same preset entries, keyed by stable slug id

``PRESET_POLICIES`` stays keyed by its emoji display label and keeps its
iteration order: the sidebar, the share links, ``CBO_SCORE_MAP`` and the
validation mapping all key on those labels today. The catalog *schema* the
redesign needs — a stable ``preset_id``, ``exclusive_group(s)``/``subsumes``
overlap structure, and the five values ``tags`` — is attached onto each entry
at the bottom of this module from :mod:`fiscal_model.preset_ids`. Nothing
about the labels or their order changes.
"""

# =============================================================================
# CBO SCORE MAPPING - Maps preset policy names to official CBO/JCT scores
# =============================================================================
CBO_SCORE_MAP = {
    # TCJA Extension
    "🏛️ TCJA Full Extension (CBO: $4.6T)": {
        "official_score": 4600.0,
        "source": "CBO",
        "source_date": "May 2024",
        # CBO, "Budgetary Outcomes Under Alternative Assumptions About Spending
        # and Revenues" (8 May 2024). Was 59710, which is the February 2024
        # Budget and Economic Outlook -- the baseline, not this estimate.
        "source_url": "https://www.cbo.gov/publication/60271",
        "notes": "Extend all individual TCJA provisions beyond 2025 sunset",
    },
    "🏛️ TCJA Extension (No SALT Cap)": {
        # H9 did NOT move this target - it stays `model_estimate` and the
        # verdict is in `target_revisions.EXAMINED_NOT_REVISED`. What the pass
        # found is that this entry disagreed with its OWN benchmark: Build
        # quoted \\$6,500B as a list price while `tcja_no_salt_cap` scored
        # against \\$5,700B, and the note claimed a \\$1.9T SALT increment where
        # the scenario assumes ~\\$1.1T. Both published figures for that
        # increment say about \\$1.2T - CRFB's "Extend except SALT cap" row is
        # +\\$1.2T beyond full extension, and CRS R48286's itemized-deduction
        # row is \\$1,244.3B. Aligned to the benchmark's own target so one
        # number is one number; the target itself is unsourced and stays so.
        "official_score": 5700.0,
        "source": "Model estimate (this repository's own decomposition)",
        "source_date": "2024",
        "notes": (
            "TCJA extension + \\$10K SALT cap lapses (~\\$1.1T additional). "
            "No agency scores this package as one row."
        ),
    },
    "🏛️ TCJA Rates Only": {
        # H9 target revision (tcja_rates_only.v2). The carried \\$3,185B - and
        # the \\$3,200B rounding that sat here - was the repository's own
        # decomposition of the fitted \\$4.6T aggregate; the scenario's note
        # said so: "~\\$3.2T calibrated. This is an illustrative scenario."
        # A single published row has existed since May 2024, in the same
        # table, column and window this repository already reads
        # `extend_tcja_amt`'s \\$1,357.1B from: CRS R48286 Table 1, "Reduced
        # Individual Tax Rates", \\$2,158.7B over FY2025-2034, transcribing
        # CBO 60114's JCT row "10%, 12%, 22%, 24%, 32%, 35%, and 37% income
        # tax rate brackets". No summing required.
        "official_score": 2158.7,
        "source": "CRS R48286 Table 1 (transcribing CBO 60114/60271, JCT)",
        "source_date": "2024-11",
        "source_url": (
            "https://www.congress.gov/crs_external_products/R/HTML/"
            "R48286.web.html"
        ),
        "notes": "Extend only individual rate bracket cuts, FY2025-2034",
    },
    # Corporate
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": {
        "official_score": -1347.0,
        "source": "Treasury",
        "source_date": "March 2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "Increase corporate rate from 21% to 28%",
    },
    "🏢 Trump Corporate 15%": {
        # Inside the published range [$595B, $673.1B] the validation ledger
        # carries for this reform (target_revisions.trump_corporate_15.v2):
        # PWBM's Table 1 and Tax Foundation's Table 2, both conventional over
        # FY2025-2034. CRFB's September 2024 post prints the two side by side,
        # which is how this figure reached the app -- and it is the figure the
        # scorecard should have been scoring against all along.
        "official_score": 673.0,
        "source": "Tax Foundation / PWBM (via CRFB)",
        "source_date": "2024",
        "notes": (
            "Reduce corporate rate from 21% to 15%. Published conventional "
            "estimates span $595B (PWBM) to $673B (Tax Foundation)."
        ),
    },
    # Tax Credits
    "👶 Biden CTC Expansion (CBO: $1.6T)": {
        "official_score": 1600.0,
        "source": "JCT",
        "source_date": "2021",
        "notes": "\\$3,600/\\$3,000 per child, fully refundable, monthly payments",
    },
    "👶 CTC Extension (CBO: $600B)": {
        "official_score": 600.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend current \\$2,000 CTC beyond 2025",
    },
    "💼 EITC Childless Expansion (Treasury: $163B)": {
        # Wave 4 target revision (biden_eitc_childless.v2): Treasury FY2025
        # Green Book, Table of Revenue Estimates, "Restore and make permanent
        # the American Rescue Plan expansion of the earned income tax credit
        # for workers without qualifying children", $162,553M over FY2025-2034
        # (report p. 242). The superseded $178B was credited to JCT with no
        # table behind it.
        "official_score": 162.6,
        "source": "Treasury (FY2025 Green Book)",
        "source_date": "2024-03",
        "notes": "Triple EITC for childless workers, expand age range",
    },
    # Estate Tax
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": {
        "official_score": 167.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Maintain doubled exemption (\\$13.6M) beyond 2025",
    },
    "🏠 Biden Estate Reform (-$450B)": {
        "official_score": -450.0,
        # Re-attributed in the Phase E provenance pass. No Biden Green Book
        # (FY2022, FY2024, FY2025) proposes a \\$3.5M exemption or a 45% rate —
        # the FY2025 volume's whole estate section is administrative. The design
        # is the "For the 99.5 Percent Act", which JCT scored at \\$429.6B over
        # FY2021-2031 (for the entire ten-section bill, not the rate alone).
        "source": "JCT (For the 99.5 Percent Act)",
        "source_date": "March 2021",
        "source_url": "https://www.sanders.senate.gov/wp-content/uploads/For-the-99.5-Act-JCT-Score.pdf",
        "notes": "Return to 2009 parameters: \\$3.5M exemption, 45% rate",
    },
    "🏠 Eliminate Estate Tax ($350B)": {
        # H9 target revision (eliminate_estate_tax.v2). The carried \\$350B was
        # never a target - the scenario's source field read "Model estimate" -
        # and the label still quotes it (labels are map keys; H1/H6 own the
        # label rule). Tax Foundation, *Options for Reforming America's Tax
        # Code 3.0* (July 2026), Option 83 "Eliminate the Estate and Gift
        # Tax", table "10-Year Change in the Deficit, 2027-2036", printed
        # p. 105: +\\$407.2B conventional primary deficit on the post-P.L.
        # 119-21 baseline. Adopted over JCT's 2017 rows, which bundle repeal
        # with the exemption doubling, and over CBO/JCT's 2015 Death Tax
        # Repeal Act score, which prices a \\$5.43M-exemption tax.
        "official_score": 407.2,
        "source": "Tax Foundation (Options 3.0, Option 83)",
        "source_date": "2026-07",
        "source_url": (
            "https://taxfoundation.org/tax-reform-guide/option/"
            "eliminate-the-estate-and-gift-tax/"
        ),
        "notes": (
            "Repeal federal estate tax entirely. The published row repeals "
            "the estate **and gift** taxes over CY2027-2036."
        ),
    },
    # Payroll Tax
    "💰 SS Cap to 90% (CBO: -$800B)": {
        "official_score": -800.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Raise SS wage cap from \\$168K to ~\\$305K",
    },
    "💰 SS Donut Hole $250K (-$2.7T)": {
        # H9 target revision (ss_donut_250k.v2). The credited source publishes
        # no dollars for this provision at all: SSA's Office of the Chief
        # Actuary scores E2.5 in percent of taxable payroll (+2.50%) and moves
        # depletion 2034 -> 2057, and the "\\$2.7 trillion over 10 years"
        # traces to a think-tank explainer with no report year, run number or
        # window. CBO, *Options for Reducing the Deficit: 2025 to 2034*
        # (pub. 60557), Option 62 alternative 2, "Subject earnings greater
        # than \\$250,000 to payroll taxes", report p. 73 (PDF p. 79):
        # -\\$1,426.8B over FY2025-2034, on the stub "Decrease (-) in the
        # deficit". Same design, including no benefit credit -- CBO's text
        # says "scheduled benefits would not change under this alternative".
        # The label still quotes -\\$2.7T; labels are map keys and H1/H6 own
        # the label rule, so this is reported rather than renamed.
        "official_score": -1426.8,
        "source": "CBO, Options 2025-2034, Option 62 alternative 2",
        "source_date": "2024-12",
        "source_url": "https://www.cbo.gov/publication/60557",
        "notes": "Apply payroll tax above \\$250K (donut hole), FY2025-2034",
    },
    "💰 Eliminate SS Cap (-$3.2T)": {
        "official_score": -3200.0,
        "source": "SS Trustees",
        "source_date": "2024",
        "notes": "Apply SS tax to all wages (no cap)",
    },
    "💰 Expand NIIT (JCT: -$250B)": {
        "official_score": -250.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Apply 3.8% NIIT to pass-through business income",
    },
    # AMT
    "⚖️ AMT: Extend TCJA Relief ($1.36T)": {
        # Target revised 2026-09-02 (validation/target_revisions.py,
        # extend_tcja_amt.v1 -> .v2). The label used to read \\$450B, a
        # figure traceable to no document and 3.5% from CRS R48286 Table 1's
        # *five*-year column; the ten-year column reads \\$1,357.1B and JCT's
        # own JCX-35-25 row for the same provision reads \\$1,362.8B.
        "official_score": 1357.1,
        "source": "CRS R48286 Table 1 (transcribing CBO 60114/60271)",
        "source_date": "November 2024",
        "source_url": (
            "https://www.congress.gov/crs_external_products/R/HTML/"
            "R48286.web.html"
        ),
        "notes": "Maintain high AMT exemption beyond 2025",
    },
    "⚖️ Repeal Individual AMT ($450B)": {
        "official_score": 450.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Eliminate individual AMT (post-TCJA sunset baseline)",
    },
    "⚖️ Repeal Corporate AMT (-$220B)": {
        # Sign corrected 2026-09-09. This figure read -220.0, where the
        # scorecard target (`scenarios.py`, expected_10yr 220.0), the benchmark
        # source (`benchmark_sources.py`, JCX-18-22 at +$222.2B) and the model
        # itself (+$220.1B) all carry **+**220.0. JCT scores enacting CAMT as a
        # revenue raiser, so repealing it *costs* the deficit that amount. The
        # number is load-bearing rather than cosmetic:
        # `deficit_target.build_catalog` drives the Build page off
        # `official_score` and `BuildOption.raises_revenue` is `score < 0`, so
        # a $220B cost was checkable in Build as a $220B saving.
        #
        # The **label** still reads "-$220B" and is owed the same correction.
        # It is the key of `ui/preset_validation.PRESET_TO_SCORECARD_ID`, and
        # that map and its test have to move in the same commit as the rename;
        # both belong to a sibling lane in this wave, so the rename is handed
        # over rather than taken here. See planning/lanes/HSA_h1_base_rule.md.
        "official_score": 220.0,
        # JCX-18-22 scores CAMT as enacted at \\$222,248M over FY2022-2031. The
        # estimate is JCT's, not CBO's.
        "source": "JCT (JCX-18-22)",
        "source_date": "August 2022",
        "source_url": "https://www.jct.gov/getattachment/efcca154-9fc1-4e72-83c0-d78b9e7372eb/x-18-22.pdf",
        "notes": "Repeal 15% corporate book minimum tax (CAMT)",
    },
    # Premium Tax Credits
    "🏥 Extend ACA Enhanced PTCs ($335B)": {
        # Wave 4 target revision (extend_enhanced_ptc.v2): CBO/JCT, pub. 60437
        # (June 2024) — "making the policy permanent would increase the budget
        # deficit by $335 billion over the 2025-2034 period". The superseded
        # $350B is CBO/JCT's September 2025 re-estimate on a FY2026-2035
        # window, so the figure and its stated vintage disagreed by one window.
        "official_score": 335.0,
        "source": "CBO/JCT (pub. 60437)",
        "source_date": "2024-06",
        "notes": "Extend ACA enhanced premium subsidies beyond 2025",
    },
    "🏥 Repeal ACA Premium Credits (-$1.1T)": {
        "official_score": -1100.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Eliminate all ACA premium tax credits",
    },
    # Tax Expenditures
    "📋 Cap Employer Health Exclusion (-$450B)": {
        "official_score": -450.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Cap exclusion at 28% rate or ~\\$25K",
    },
    "📋 Eliminate Mortgage Deduction (-$300B)": {
        # H9 target revision (eliminate_mortgage.v2), a **range**
        # [-\\$495.0B, -\\$367.9B] whose carried anchor is Tax Foundation's
        # -\\$367.9B (*Options 3.0*, July 2026, Option 25, "10-Year Change in
        # the Deficit, 2027-2036"). The other bound is CRS IF13190 Table 2's
        # "Repeal MID \\$495" over FY2026-2035, computed on the Yale Budget
        # Lab Tax-Simulator. Wave 4 left this row on the premise that the two
        # then-known figures came from one simulator 2.4x apart; a third,
        # independent model resolves that as a BASELINE gap - Yale's \\$1.2T
        # is pre-P.L. 119-21, where the standard deduction lapses and the
        # itemising population roughly doubles. The label still quotes
        # -\\$300B; labels are map keys.
        "official_score": -367.9,
        "source": "Tax Foundation (Options 3.0, Option 25)",
        "source_date": "2026-07",
        "source_url": (
            "https://taxfoundation.org/tax-reform-guide/option/"
            "eliminate-the-home-mortgage-interest-deduction/"
        ),
        "notes": (
            "Repeal mortgage interest deduction. Published range "
            "[-\\$495B, -\\$367.9B]; no agency has scored repeal."
        ),
    },
    "📋 Repeal SALT Cap ($1.17T)": {
        # Wave 4 target revision (repeal_salt_cap.v2): Penn Wharton Budget
        # Model, "Lifting the SALT Cap", Table 3, row "Repeal SALT Cap",
        # -\\$1,169B over FY2025-2034 **against an extended-TCJA baseline**.
        # The same paper scores the same repeal at -\\$197B against current
        # law, so the baseline is part of the target. JCT, the superseded
        # attribution, has never scored a standalone repeal of the cap.
        "official_score": 1169.0,
        "source": "Penn Wharton Budget Model",
        "source_date": "2024-02",
        "notes": (
            "Remove \\$10K cap on state/local tax deduction; scored against a "
            "permanent-cap (extended TCJA) baseline"
        ),
    },
    "📋 Eliminate SALT Deduction (-$1.62T)": {
        # Wave 4 target revision (eliminate_salt.v2): CBO, Options for
        # Reducing the Deficit: 2025 to 2034 (pub. 60557), Option 49, row
        # "Eliminate state and local tax deductions", \\$1,621.0B over
        # FY2025-2034 — the same option the SALT expenditure record's
        # `limitation` block already cites for its lapse date.
        "official_score": -1621.0,
        "source": "CBO (pub. 60557, Option 49)",
        "source_date": "2024-12",
        "notes": "Repeal state/local tax deduction entirely",
    },
    "📋 Cap Charitable Deduction (-$200B)": {
        "official_score": -200.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Limit charitable deduction to 28% rate",
    },
    "📋 Eliminate Step-Up Basis (-$500B)": {
        "official_score": -500.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Tax unrealized gains at death (with exemptions)",
    },
    # Income Tax
    "Biden 2025 Proposal": {
        # Wave 4 Tier 1 revision (biden_high_income_tax.v2): the Green Book row
        # this record already cites prints $245,924M, not $252,000M.
        "official_score": -245.9,
        "source": "Treasury",
        "source_date": "March 2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "Restore 39.6% top rate for income above \\$400K",
    },
    "Warren Ultra-Millionaire Surtax": {
        "official_score": -350.0,
        "source": "TPC",
        "source_date": "2020",
        "source_url": "https://www.taxpolicycenter.org/",
        "notes": "3pp surtax on AGI >\\$2M; TPC-range estimate",
    },
    # "Top Rate to 45%" used to sit here with an "official_score" of -$420B
    # attributed to TPC. The Phase E provenance pass enumerated TPC's entire
    # sitemap and found no table for a 45% ordinary rate at any date, and no
    # CBO or JCT option for an +8pp top-bracket increase either. An official
    # score nobody published should not be quoted in the app, so the entry was
    # removed; the preset itself is unchanged and still scoreable, it simply
    # shows the model's own estimate with no official comparison. See
    # fiscal_model/validation/preregistered.py (top_rate_45.v1, retired).
    "High-Earner Medicare Surcharge 2pp": {
        "official_score": -310.0,
        "source": "Treasury",
        "source_date": "2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "+2pp Medicare surcharge on investment + wage income >\\$400K",
    },
    # International Tax
    "🌍 Biden GILTI Reform (-$374B)": {
        # Wave 4 target revision (biden_gilti_reform.v2): Treasury FY2025 Green
        # Book, "Revise the global minimum tax regime, limit inversions, and
        # make related reforms", $373,919M over FY2025-2034 (report p. 239).
        "official_score": -373.9,
        "source": "Treasury (FY2025 Green Book)",
        "source_date": "2024-03",
        "notes": "Country-by-country GILTI at 21%, eliminate QBAI exemption",
    },
    "🌍 Repeal FDII (-$158B)": {
        # Wave 4 target revision (fdii_repeal.v2): Treasury FY2025 Green Book,
        # "Repeal the deduction for foreign-derived intangible income",
        # $157,993M gross over FY2025-2034 (report p. 239). Treasury's own
        # subtotal nets this against a paired R&D proposal to $0; the module
        # scores repeal without that offset, which is the gross row.
        "official_score": -158.0,
        "source": "Treasury (FY2025 Green Book)",
        "source_date": "2024-03",
        "notes": "Repeal Foreign-Derived Intangible Income deduction",
    },
    "🌍 Pillar Two Adoption (-$80B)": {
        "official_score": -80.0,
        "source": "JCT",
        "source_date": "2023",
        "notes": "Adopt OECD Pillar Two 15% global minimum tax",
    },
    "🌍 Biden International Package (-$632B)": {
        # Wave 4 target revision (biden_full_international.v2): Treasury FY2025
        # Green Book, "Subtotal, Reform International Taxation", $632,200M over
        # FY2025-2034 (report p. 240). The three provisions the module carries
        # sum to $510,232M inside that subtotal, so about a fifth of the target
        # is provisions it does not model — stated, not tuned away.
        "official_score": -632.2,
        "source": "Treasury (FY2025 Green Book)",
        "source_date": "2024-03",
        "notes": "Full package: GILTI reform + FDII repeal + UTPR",
    },
    # IRS Enforcement
    "🔍 IRA Enforcement Funding (-$180B)": {
        # Wave 4 target revision (ira_enforcement.v2): CBO pub. 58390 (Aug
        # 2022) — "revenues will increase by \\$180.4 billion over the
        # 2022-2031 period", explicitly revising CBO's earlier \\$203.7B. The
        # superseded -\\$200B sat 2% below the withdrawn estimate.
        "official_score": -180.4,
        "source": "CBO (pub. 58390)",
        "source_date": "2022-08",
        "notes": "IRA IRS enforcement funding, ~\\$180B of added revenue",
    },
    "🔍 Double IRS Enforcement (-$340B)": {
        "official_score": -340.0,
        "source": "Treasury/Sarin-Summers",
        "source_date": "2021",
        "notes": "Double enforcement budget beyond IRA levels",
    },
    # Pharmaceutical
    "💊 Expand Drug Negotiation (-$500B)": {
        "official_score": -500.0,
        "source": "CBO/Estimate",
        "source_date": "2023",
        "notes": "Negotiate 50 drugs, remove exclusivity delays",
    },
    "💊 Universal Insulin Cap ($11B)": {
        # Target revised 2026-09-02 (validation/target_revisions.py,
        # universal_insulin_cap.v1 -> .v2). A \\$35 monthly cap is a
        # cost-sharing cap: it shifts a patient's liability onto the plan and
        # onto the federal subsidy for it, so it ADDS to the deficit. CBO
        # pub. 57957 scores this policy at +\\$6.566B of outlays and
        # -\\$4.793B of revenues over FY2022-2031. The label used to read
        # -\\$15B, a saving no CBO document produces.
        "official_score": 11.4,
        "source": "CBO (publication 57957, H.R. 6833)",
        "source_date": "March 2022",
        "source_url": "https://www.cbo.gov/publication/57957",
        "notes": "\\$35/month insulin cap for Medicare and private insurance",
    },
    "💊 International Reference Pricing (-$100B)": {
        "official_score": -100.0,
        "source": "RAND/Estimate",
        "source_date": "2021",
        "notes": "Cap Medicare drug prices at 120% of international average",
    },
    # Trade / Tariffs
    "🏭 Trump Universal 10% Tariff (-$2.17T)": {
        # Wave 4 target revision (trump_universal_10.v2): Tax Foundation Fiscal
        # Fact 861, Table 3, "10 Percent Universal Tariff", \\$2,171.1B
        # conventional over 2025-2034 (report p. 4). Yale publishes no
        # standalone ten-year figure for this policy, so that half of the old
        # attribution is dropped. The same table's dynamic tier is \\$1,720.8B.
        "official_score": -2171.1,
        "source": "Tax Foundation (FF861)",
        "source_date": "2025-04",
        "notes": "10% tariff on all imports, ~\\$1,700/household cost",
    },
    "🏭 Trump 60% China Tariff (-$500B)": {
        # H9 target revision (trump_china_60.v2). The credited publisher
        # scores this tariff only inside a bundle, so -\\$500B was obtainable
        # only as a residual. CRFB, "Options to Raise Tariff Revenue"
        # (17 December 2024), table "Tariff Scenarios and Their Net Impact on
        # Revenue", row "60% Import Tariff on Chinese Goods", conventional
        # column: -\\$650B over FY2026-2035. The adjacent row prices the same
        # tariff on top of a 10% universal baseline at -\\$575B, which is what
        # makes the \\$650B row unambiguously this preset's shape. The label
        # still quotes -\\$500B; labels are map keys.
        "official_score": -650.0,
        "source": "CRFB (Options to Raise Tariff Revenue)",
        "source_date": "2024-12",
        "source_url": "https://www.crfb.org/blogs/options-raise-tariff-revenue",
        "notes": (
            "60% tariff on Chinese imports. CRFB notes savings would run "
            "about 15% lower on an FY2025-2034 window."
        ),
    },
    "🏭 25% Auto Tariff (-$386B)": {
        # Wave 4 target revision (auto_tariff_25.v2): Tax Foundation tariff
        # tracker, Table 5, "Section 232 Autos, Heavy Trucks, Buses, and
        # Parts", \\$386.2B conventional over 2026-2035. The superseded
        # -\\$100B was a White House claim stated *per year* — CRFB, its
        # stated source, itemises no auto tariff anywhere.
        "official_score": -386.2,
        "source": "Tax Foundation (tariff tracker)",
        "source_date": "2026-08",
        "notes": "25% tariff on auto imports",
    },
    "🏭 25% Steel/Aluminum Tariff (-$60B)": {
        "official_score": -60.0,
        "source": "Tax Foundation",
        "source_date": "2024",
        "notes": "25% tariff on steel and aluminum imports",
    },
    "🏭 Reciprocal Tariffs (-$1.5T)": {
        # Wave 4 target revision (reciprocal_tariffs.v2) — superseded by a
        # published *range*. CRFB's "Ten-Year Scores of Trump's Tariffs, If
        # Made Permanent" (FY2025-2034) prints three conventional estimates of
        # the same schedule: \\$1.8T (CRFB), \\$1.5T (Tax Foundation), \\$1.4T
        # (Yale Budget Lab). The honest target is [-\\$1,800B, -\\$1,400B]; the
        # anchor carried here is Tax Foundation's, the publisher the other two
        # tariff benchmarks are scored against. The superseded -\\$1,200B was
        # Tax Foundation's *dynamic* score sitting in a conventional column.
        "official_score": -1500.0,
        "source": "CRFB / Tax Foundation / Yale Budget Lab",
        "source_date": "2025-04",
        "notes": "Match trading partners\\' tariff rates (~20pp average increase)",
    },
    # Climate / Energy
    "🌱 Repeal IRA Clean Energy Credits ($783B)": {
        # H9 target revision (repeal_ira_credits.v2). The cited CBO
        # publication does not exist and -\\$783B appears in no CBO or JCT
        # document; every figure near it is a projection of what the credits
        # COST rather than a score of repealing them. William McBride,
        # "Testimony: The Inflation Reduction Act's Green Energy Tax Credits",
        # Tax Foundation, to the House Committee on Oversight and Government
        # Reform, 20 May 2025: "full repeal of the credits would reduce
        # deficits by \\$851 billion over the next decade (2025-2034)".
        # Chosen over JCT's JCX-7-23 (\\$515.1B) on scope: that total is
        # revenue-only and excludes all three clean-vehicle credits, by the
        # document's own footnotes. The label still quotes \\$783B.
        "official_score": -851.0,
        "source": "Tax Foundation (McBride, House Oversight testimony)",
        "source_date": "2025-05",
        "source_url": (
            "https://taxfoundation.org/testimony/"
            "inflation-reduction-act-ira-green-energy-tax-credits/"
        ),
        "notes": "Full repeal of IRA clean energy tax credits, FY2025-2034",
    },
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": {
        "official_score": -1700.0,
        "source": "CBO-style estimate",
        "source_date": "2024",
        "notes": "\\$50/ton CO2 tax with 5% annual escalator",
    },
    "🌱 Repeal EV Credits ($182B)": {
        # Wave 4 target revision (repeal_ev_credits.v2): sec. 30D (\\$77,829M)
        # + sec. 45W (\\$104,516M) = \\$182,345M, exactly the two sections the
        # climate module's stated scope names. Phase E transcribed the sum as
        # \\$182.4B; the rows add to \\$182.3B.
        "official_score": -182.3,
        # Re-attributed in the Phase E provenance pass: the only published
        # score of terminating the clean-vehicle credits is JCT's, not CBO's.
        # JCX-35-25 puts sec. 30D + sec. 45W at \\$182.3B over FY2025-2034
        # (\\$189.8B including the used-vehicle credit, sec. 25E).
        "source": "JCT (JCX-35-25)",
        "source_date": "July 2025",
        "source_url": "https://www.jct.gov/getattachment/eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/x-35-25.pdf",
        "notes": "Repeal \\$7,500 EV tax credit",
    },
}


# =============================================================================
# PRESET POLICIES - Preset policy configurations for the UI
# =============================================================================
PRESET_POLICIES = {
    "Custom Policy": {
        "rate_change": -2.0,
        "threshold": 500000,
        "description": "Design your own policy",
        "is_tcja": False,
    },
    "🏛️ TCJA Full Extension (CBO: $4.6T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend all TCJA individual provisions beyond 2025 sunset. Includes rate cuts, doubled standard deduction, SALT cap, pass-through deduction, CTC expansion.",
        "is_tcja": True,
        "tcja_type": "full",
    },
    "🏛️ TCJA Extension (No SALT Cap)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend TCJA but repeal the \\$10K SALT cap (adds ~\\$1.9T to cost). Popular bipartisan proposal.",
        "is_tcja": True,
        "tcja_type": "no_salt",
    },
    "🏛️ TCJA Rates Only": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend only the individual rate bracket cuts, not other TCJA provisions (~\\$3.2T).",
        "is_tcja": True,
        "tcja_type": "rates_only",
    },
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Raise corporate rate from 21% to 28%. CBO estimate: raises ~\\$1.35T over 10 years.",
        "is_tcja": False,
        "is_corporate": True,
        "corporate_type": "biden_28",
    },
    "🏢 Trump Corporate 15%": {
        "rate_change": 0.0,
        "threshold": 0,
        # "~$1.9T" was this model's own output quoted back at the user, and the
        # 2026-09-05 provenance lane retired it as a validation target: the
        # published conventional estimates of the rate change are PWBM's $595B
        # and Tax Foundation's $673B over FY2025-2034. This preset also extends
        # bonus depreciation, which neither figure includes.
        "description": (
            "Lower corporate rate from 21% to 15%, with bonus depreciation "
            "extended. Published estimates of the rate change alone run "
            "\\$595B (PWBM) to \\$673B (Tax Foundation) over ten years."
        ),
        "is_tcja": False,
        "is_corporate": True,
        "corporate_type": "trump_15",
    },
    "👶 Biden CTC Expansion (CBO: $1.6T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Expand CTC to \\$3,600/\\$3,000 per child, fully refundable. Based on 2021 ARP expansion.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": True,
        "credit_type": "biden_ctc_2021",
    },
    "👶 CTC Extension (CBO: $600B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend current \\$2,000 CTC beyond 2025 sunset. Without extension, reverts to \\$1,000.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": True,
        "credit_type": "ctc_extension",
    },
    "💼 EITC Childless Expansion (Treasury: $163B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Triple EITC for childless workers (~\\$1,500 max), expand age range to 19-65+.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": True,
        "credit_type": "biden_eitc_childless",
    },
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Keep ~\\$14M exemption (vs \\$6.4M if TCJA expires). Costs ~\\$167B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": False,
        "is_estate": True,
        "estate_type": "extend_tcja",
    },
    "🏠 Biden Estate Reform (-$450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Lower exemption to \\$3.5M, raise rate to 45%. Raises ~\\$450B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": False,
        "is_estate": True,
        "estate_type": "biden_reform",
    },
    "🏠 Eliminate Estate Tax ($350B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal federal estate tax entirely. Costs ~\\$350B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": False,
        "is_estate": True,
        "estate_type": "eliminate",
    },
    "💰 SS Cap to 90% (CBO: -$800B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Raise Social Security cap to cover 90% of wages (~\\$305K). Raises ~\\$800B.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "cap_90",
    },
    "💰 SS Donut Hole $250K (-$2.7T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Apply SS tax to wages above \\$250K (donut hole). Raises ~\\$2.7T over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "donut_250k",
    },
    "💰 Eliminate SS Cap (-$3.2T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Eliminate Social Security wage cap entirely. Raises ~\\$3.2T over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "eliminate_cap",
    },
    "💰 Expand NIIT (JCT: -$250B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Apply 3.8% NIIT to S-corp/partnership income. Raises ~\\$250B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "expand_niit",
    },
    "⚖️ AMT: Extend TCJA Relief ($1.36T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend TCJA's higher AMT exemptions (\\$88K single, \\$137K MFJ) past 2025. CRS/CBO put the 10-year cost at ~\\$1.36T.",
        "is_tcja": False,
        "is_corporate": False,
        "is_amt": True,
        "amt_type": "extend_tcja",
    },
    "⚖️ Repeal Individual AMT ($450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Fully repeal individual AMT. After TCJA expires, would cost ~\\$450B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_amt": True,
        "amt_type": "repeal_individual",
    },
    "⚖️ Repeal Corporate AMT (-$220B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": (
            "Repeal the 15% corporate book minimum tax (CAMT) enacted by IRA "
            "2022. **Costs** ~\\$220B over 10 years: JCT scored enacting CAMT "
            "as a \\$222.2B revenue raiser (JCX-18-22), so repeal loses that "
            "revenue. **Note the label**: its \"-\\$220B\" is this app's "
            "convention for a \\$220B *deficit reduction*, which is the "
            "opposite of what a repeal does. The official score behind it was "
            "corrected on 2026-09-09; the label is queued for the same fix."
        ),
        "is_tcja": False,
        "is_corporate": False,
        "is_amt": True,
        "amt_type": "repeal_corporate",
    },
    "🏥 Extend ACA Enhanced PTCs ($335B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend enhanced premium tax credits (ARPA/IRA) past 2025. Costs ~\\$335B over FY2025-2034 (CBO/JCT pub. 60437).",
        "is_tcja": False,
        "is_corporate": False,
        "is_ptc": True,
        "ptc_type": "extend_enhanced",
    },
    "🏥 Repeal ACA Premium Credits (-$1.1T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal all ACA premium subsidies. Saves ~\\$1.1T but ~19M lose subsidized coverage.",
        "is_tcja": False,
        "is_corporate": False,
        "is_ptc": True,
        "ptc_type": "repeal",
    },
    "📋 Cap Employer Health Exclusion (-$450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Cap tax exclusion for employer health insurance at \\$50K. Raises ~\\$450B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "cap_employer_health",
    },
    "📋 Repeal SALT Cap ($1.17T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Remove \\$10K cap on state and local tax deduction. Costs ~\\$1.17T over 10 years measured against a permanent-cap baseline (Penn Wharton); ~\\$197B against a baseline where the cap expires.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "repeal_salt_cap",
    },
    "📋 Eliminate Step-Up Basis (-$500B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Tax capital gains at death with \\$1M exemption. Raises ~\\$500B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "eliminate_step_up",
    },
    "📋 Cap Charitable Deduction (-$200B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Limit charitable deduction value to 28% rate. Raises ~\\$200B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "cap_charitable",
    },
    "Biden 2025 Proposal": {
        "rate_change": 2.6,
        "threshold": 400000,
        "description": (
            "+2.6pp on income above \\$400K, restoring the pre-TCJA 39.6% top rate. "
            "Treasury FY2025 Green Book estimate: raises ~\\$252B over 10 years."
        ),
        "is_tcja": False,
        "is_corporate": False,
        "ui_category": "TCJA / Individual",
    },
    "Progressive Millionaire Tax": {
        "rate_change": 5.0,
        "threshold": 1000000,
        # No source document exists for this preset: it has no CBO_SCORE_MAP
        # entry, no scorecard row of any tier, and nothing published scores the
        # reform. The AGI-inclusive base is therefore a **design choice of the
        # preset**, by analogy with the two surtaxes that do carry documents —
        # TPC's Warren surtax on AGI and Treasury's Medicare surcharge on wage
        # and investment income, both stated on total income above a threshold
        # with no bracket schedule named. The description says so, so a reader
        # is not left to assume it was read off a source.
        "agi_inclusive_base": True,
        "description": (
            "5pp surtax on income above \\$1M, scored on the AGI-inclusive "
            "base — capital gains and qualified dividends included. "
            "**No official score**: nothing published scores this reform, so "
            "the model's own estimate is the only number shown, and the "
            "AGI-inclusive base is a design choice of the preset by analogy "
            "with the Warren and Medicare surtaxes rather than a reading of a "
            "source document."
        ),
        "is_tcja": False,
    },
    "Middle Class Tax Cut": {
        "rate_change": -2.0,
        "threshold": 50000,
        "description": "2pp cut for households earning \\$50K+",
        "is_tcja": False,
    },
    "Flat Tax Reform": {
        "rate_change": -5.0,
        "threshold": 0,
        "description": "Lower all rates by 5pp (illustrative)",
        "is_tcja": False,
    },
    "Warren Ultra-Millionaire Surtax": {
        "rate_change": 3.0,
        "threshold": 2_000_000,
        # AGI-inclusive on its own source: the TPC table this preset's
        # CBO_SCORE_MAP row cites scores "3pp surtax on AGI >$2M", and AGI
        # includes realized capital gains and qualified dividends. Scored on
        # the ordinary base until 2026-09-09, which put the app's -$134.6B
        # beside a label quoting TPC's -$350B (61.5%) while the scorecard's own
        # AGI-inclusive row reported 19.0%. A transcription, not a rule.
        "agi_inclusive_base": True,
        "description": (
            "3pp surtax on **AGI** above \\$2M, Warren-style, scored on the "
            "AGI-inclusive base its TPC source uses — realized capital gains "
            "and qualified dividends included. Raises roughly \\$300-400B over "
            "10 years depending on behavioral response."
        ),
        "is_tcja": False,
        "ui_category": "Income Tax",
    },
    "Top Rate to 45%": {
        "rate_change": 8.0,
        "threshold": 609_350,
        "description": (
            "Raise the top marginal rate from 37% to 45% on income above "
            "the current 37% bracket floor (\\$609,350 single, 2025). "
            "Illustrative of the upper end of progressive proposals. "
            "**No official score**: the \\$420B figure this preset used to "
            "quote could not be traced to any TPC, CBO or JCT publication and "
            "was withdrawn in the Phase E provenance pass, so the model's own "
            "estimate is the only number shown."
        ),
        "is_tcja": False,
        "ui_category": "Income Tax",
    },
    "High-Earner Medicare Surcharge 2pp": {
        "rate_change": 2.0,
        "threshold": 400_000,
        # AGI-inclusive on its own source: the Treasury FY2025 Green Book row
        # this preset's CBO_SCORE_MAP entry cites applies the surcharge to
        # "investment + wage income" above $400K, so it reaches the
        # preferentially taxed income an ordinary-bracket rate does not.
        # Scored on the ordinary base until 2026-09-09, which put the app's
        # -$166.5B beside Treasury's -$310B (46.3%) while the scorecard's own
        # AGI-inclusive row reported 1.5%. A transcription, not a rule.
        "agi_inclusive_base": True,
        "description": (
            "+2pp Medicare surcharge on wage **and investment** income above "
            "\\$400K, scored on the AGI-inclusive base Treasury's FY2025 Green "
            "Book row uses. Extends the NIIT's 3.8% surtax logic to a broader "
            "base. Similar in structure to the Biden 2025 Medicare surtax "
            "proposal."
        ),
        "is_tcja": False,
        "ui_category": "Income Tax",
    },
    # International Tax Presets
    "🌍 Biden GILTI Reform (-$374B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Country-by-country GILTI at 21%, eliminate QBAI exemption. Raises ~\\$374B over 10 years (Treasury FY2025 Green Book).",
        "is_tcja": False,
        "is_international": True,
        "international_type": "biden_gilti",
    },
    "🌍 Repeal FDII (-$158B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal Foreign-Derived Intangible Income deduction. Raises ~\\$158B over 10 years (Treasury FY2025 Green Book, before the R&D proposal Treasury pairs it with).",
        "is_tcja": False,
        "is_international": True,
        "international_type": "fdii_repeal",
    },
    "🌍 Pillar Two Adoption (-$80B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Adopt OECD Pillar Two 15% global minimum tax. JCT estimate: raises ~\\$80B.",
        "is_tcja": False,
        "is_international": True,
        "international_type": "pillar_two",
    },
    "🌍 Biden International Package (-$632B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Full Biden international reform: GILTI at 21% per-country + FDII repeal + UTPR. Raises ~\\$632B (Treasury FY2025 Green Book subtotal).",
        "is_tcja": False,
        "is_international": True,
        "international_type": "biden_full",
    },
    # IRS Enforcement Presets
    "🔍 IRA Enforcement Funding (-$180B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "IRA IRS enforcement funding. CBO: raises ~\\$180B of revenue over FY2022-2031 (pub. 58390), about \\$101B net of the \\$79B appropriation.",
        "is_tcja": False,
        "is_enforcement": True,
        "enforcement_type": "ira",
    },
    "🔍 Double IRS Enforcement (-$340B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Double IRS enforcement beyond IRA levels (~\\$16B/year). Raises ~\\$340B with diminishing returns.",
        "is_tcja": False,
        "is_enforcement": True,
        "enforcement_type": "double",
    },
    "🔍 High-Income Enforcement": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": (
            "Targeted enforcement for >\\$400K returns and large partnerships. "
            "\\$5B/year, high ROI. **No official score**: the \\$250B this "
            "preset's label used to quote could not be traced to any CBO, JCT "
            "or Treasury publication and was struck on 2026-09-09. CBO scores "
            "*untargeted* appropriation increases only — \\$20B of funding for "
            "−\\$41B of deficit and \\$40B for −\\$63B (publication 59972, "
            "FY2024-2034) — and nothing published isolates a high-income "
            "dose. The model's own estimate is the only number shown."
        ),
        "is_tcja": False,
        "is_enforcement": True,
        "enforcement_type": "high_income",
    },
    # Pharmaceutical Presets
    "💊 Expand Drug Negotiation (-$500B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Negotiate 50 Medicare drugs (vs IRA's 20), remove exclusivity delays. Saves ~\\$500B.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "expand_negotiation",
    },
    "💊 Universal Insulin Cap ($11B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "\\$35/month insulin cap for Medicare and private insurance. A cost-sharing cap shifts liability onto plans, so CBO scores it as adding ~\\$11B to the deficit over 10 years.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "insulin_cap",
    },
    "💊 International Reference Pricing (-$100B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Cap Medicare drug prices at 120% of OECD international average. Saves ~\\$100B.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "reference_pricing",
    },
    "💊 Comprehensive Drug Reform": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": (
            "Expanded negotiation + insulin cap + manufacturer discounts. "
            "**No official score**: the \\$600B this preset's label used to "
            "quote could not be traced to any CBO, CMS or CRFB publication "
            "and was struck on 2026-09-09. Nothing published scores a "
            "*combined* package of these three; the nearest published figures "
            "are components an order of magnitude smaller (CBO put the IRA's "
            "own negotiation at \\$98.5B over FY2022-2031). The model's own "
            "estimate is the only number shown, and it is a 🟡 reconstruction "
            "of a channel nobody has scored."
        ),
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "comprehensive",
    },
    # Trade / Tariff Presets
    "🏭 Trump Universal 10% Tariff (-$2.17T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "10% tariff on all imports. Raises ~\\$2.17T conventionally (Tax Foundation FF861) but costs ~\\$1,700/household in higher prices.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "universal_10",
    },
    "🏭 Trump 60% China Tariff (-$500B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "60% tariff on all Chinese imports (~\\$430B base). Raises ~\\$500B over 10 years.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "china_60",
    },
    "🏭 25% Auto Tariff (-$386B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "25% tariff on imported vehicles and parts (~\\$380B base). Raises ~\\$386B conventionally (Tax Foundation tariff tracker).",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "auto_25",
    },
    "🏭 25% Steel/Aluminum Tariff (-$60B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "25% tariff on steel and aluminum imports (~\\$50B base).",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "steel_25",
    },
    "🏭 Reciprocal Tariffs (-$1.5T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Match trading partners' tariff rates (~20pp average increase). Published conventional estimates of the announced schedule span \\$1.4-1.8T; the official score shown anchors on Tax Foundation's \\$1.5T.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "reciprocal",
    },
    # Climate / Energy Presets
    "🌱 Repeal IRA Clean Energy Credits ($783B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Full repeal of IRA clean energy tax credits. Saves ~\\$783B over 10 years (CBO March 2024).",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "repeal_ira",
    },
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "\\$50/ton CO2 tax with 5% annual escalator. Raises ~\\$1.7T over 10 years.",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "carbon_50",
    },
    "🌱 Carbon Tax \\$25/ton": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": (
            "\\$25/ton CO2 starter tax with 5% annual escalator. "
            "**No official score is quoted**: the \\$1.0T this preset's label "
            "used to carry matches no published estimate and was struck on "
            "2026-09-09. A real document does exist at a different figure and "
            "a different decade — CBO and JCT's *Options for Reducing the "
            "Deficit: 2023 to 2032* scores \\$25/tonne rising 5% plus "
            "inflation at −\\$865B over FY2023-2032 — and this repository has "
            "no scorecard row for it, so the model's own estimate is the only "
            "number shown."
        ),
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "carbon_25",
    },
    "🌱 Repeal EV Credits ($182B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal the \\$7,500 clean-vehicle credit (sec. 30D) and the commercial clean-vehicle credit (sec. 45W). Saves ~\\$182B over FY2025-2034 (JCT JCX-35-25).",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "repeal_ev",
    },
    "🌱 Extend IRA Credits Beyond 2032": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": (
            "Extend IRA clean energy credits 5 years beyond the 2032 sunset. "
            "**No official score**: the \\$400B this preset's label used to "
            "quote could not be traced to any JCT, CBO, Treasury or PWBM "
            "publication and was struck on 2026-09-09. Every published figure "
            "scores the credits *as enacted* or their *repeal*, never an "
            "incremental five-year extension. The model's own estimate is the "
            "only number shown."
        ),
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "extend_ira",
    },
}


# =============================================================================
# CATALOG SCHEMA - stable ids, exclusivity groups, and values tags
# =============================================================================
# Attached after the literal above so the label keys and their order stay
# exactly as written. Each entry gains:
#   preset_id         stable kebab-case slug, safe for share URLs
#   exclusive_groups  tuple of "pick at most one" group ids (may be empty)
#   exclusive_group   the first of those, or None (plan §5.3 names a singular
#                     field; the plural is authoritative)
#   subsumes          ids this bundle already contains
#   tags              {direction, progressivity, govt_size, base, generational}
#   tag_sources       per-tag provenance (engine / fallback / derived / override)
#
# See fiscal_model/preset_ids.py for the registry and helpers
# (resolve_preset, conflicting_selections, ...) and
# scripts/derive_policy_tags.py for how the tags are derived.
from fiscal_model.preset_ids import attach_catalog_metadata  # noqa: E402

#: The same preset dicts as PRESET_POLICIES, keyed by stable id.
PRESETS_BY_ID: dict[str, dict] = attach_catalog_metadata(PRESET_POLICIES)
