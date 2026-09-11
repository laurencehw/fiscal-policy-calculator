# Model Validation Report

> **Fiscal Policy Calculator — Comparison to Official CBO/JCT Estimates**
>
> Last Updated: September 11, 2026 (post-Wave-C: the decedent headcount, the tariff retaliation convention, per-class accuracy bands, and six preset labels onto their rows' live targets — **no target moved and no constant was retuned**)

---

## Executive Summary

The model is benchmarked against **77 published estimates** — from CBO, JCT, Treasury and SSA, plus TPC, PWBM, the Tax Foundation and CRFB where no agency scored the policy — plus 4 *illustrations* with no official score at all, which are labelled and reported separately and never counted (`published_entries` vs `total_entries` on the scorecard). Crucially, those benchmarks fall into **two epistemically different tiers**, and reporting them together overstates predictive power. Both are reproducible live: `python scripts/cold_holdout.py`. Tier 1 is additionally **pre-registered** (`fiscal_model/validation/preregistered.py`) and **CI-gated**.

### Tier 1 — Out-of-sample predictions (the genuine test)

Policies scored **bottom-up** — IRS SOI filer counts and incomes via raw rate/threshold auto-population, the modules' own revenue identities, and spending levels stated by the source — with **no fitting to the official target** (and, for capital gains, one frozen elasticity set). This is the only tier that measures predictive accuracy.

> **44 out-of-sample cases, mean abs error 18.0%, 26/44 within 15%, 35/44 within 25%** (median 12.3%; error mass 793.8). Lane R3 (PR #169) added 22 rows from CBO's 2018, 2020 and 2022 *Options* volumes, each scored on its own volume's decade, with all 22 prior rows byte-identical — the mean rose because the battery grew, not because any score moved; per class it now reads corporate 71.6% (n=4), payroll 18.6% (8), ordinary rate 15.3% (11), capital gains 14.4% (7), AGI surtax 7.2% (4), enacted-law 7.4% (3), tax expenditure 7.1% (2), discretionary 4.6% (5). The 22-row reading before R3 was: **mean abs error 11.8%, 17/22 within 15%, 19/22 within 25%** (median 8.9%; error mass 258.9). The tier is **eight policy classes** and must never be quoted as one number: capital gains 18.7% (n=4), **ordinary rate change 13.8% (4)**, corporate 44.5% (1), discretionary spending 4.6% (5), enacted-law spending 7.4% (3), payroll 7.8% (2), tax-expenditure cap 12.8% (1), AGI-inclusive surtax 5.2% (2) — each carrying its own CI ceiling. **Wave F moved one row and one class and nothing else**: PR #165 gave `cbo_opt45_top4_brackets_2pp` CBO's own year-indexed statutory bracket schedule and it went 14.3% → **17.9%**, a regression registered before the file was opened, which is the whole of 11.6% → 11.8% and of 12.9% → 13.8%.
> **All 22 rows are `line_item`.** The tier's `secondhand` count is **0** and its `model_estimate` count is **0**, which is new in Wave E and is the strongest single statement this repository can make about this tier.
> **The battery got smaller before it got better and the two facts are the same fact**: lane R2 withdrew four rows whose targets are in no publication, so 26 → 22 and 13.8% → 11.3% is a *composition* change and not one cent of model improvement. Lane R1 then took the merged tier to **11.6%** by putting the baseline on CBO's own tables — which moved eleven rows in **both** directions. Read the count beside the mean, always, and read the **share** beside the count: within-25 fell **22 → 19** while its share rose **84.6% → 86.4%**, and only one of those two is comparable across a battery that changes size.
> There is deliberately no single "validated within X%" number: the distribution has a tight core and a long tail, and collapsing it would hide the tail.

*Lane R2 (2026-09-11; `planning/lanes/R2_tier1_secondhand_targets.md`) is the first pass to make this tier **smaller**, and every figure it moved is a target rather than a model. Five rows carried no source URL and between them held **33.4% of the tier's error mass on 19% of its rows** — 23.92% mean against the 21 `line_item` rows' 11.36%. Each was judged on its own document. **`illustrative_1pp_all` was superseded** onto the option its own record already described: CBO publication 58164, *Options for Reducing the Deficit: 2023 to 2032, Volume I*, Option 13 alternative 1, "Raise all tax rates on ordinary income by 1 percentage point", **−$1,081.3B** over FY2023–2032 (report p. 72), *"Data source: Staff of the Joint Committee on Taxation"* — the same reform, the same estimator, the same window and the same vintage the manifest had claimed for a rule of thumb. The prediction did not move a cent, so **24.5% → 10.5% is the target finding its document**. **Four were withdrawn**, each with the search recorded in `preregistered.py` and `benchmark_sources.py`: `warren_ultramillionaire_surtax_3pp` (TPC's *AGI Surtax Options* is thirteen tables and **every one of them is 10 percent**; its sole revenue table, T19-0037 of 23 September 2019, prices 10pp above $2M at $585.325B, above $2.5M at $500.635B and above $2M married / $1M other at $633.897B — **and the row's name is wrong**, because Warren's Ultra-Millionaire Tax Act is a *wealth* tax on net worth, so the 3pp is a wealth rate on an income base and the shape matches no proposal anybody scored); `medicare_surcharge_2pp`; `illustrative_top_rate_5pp` and `illustrative_500k_2pp` (no publication prices a rate change at a $1,000,000 or $500,000 threshold — R2 read the individual-rate option of **all four** CBO *Options* volumes, 2018, 2020, 2022 and 2024, and every alternative in all four is a uniform change at a bracket boundary or an AGI surtax at the standard deduction, the fourth-bracket floor, $20,000/$40,000 or $100,000/$200,000; both records called themselves "Illustrative estimate", and `docs/VALIDATION.md` had carried the first as an open owner decision since Phase E).*

***`medicare_surcharge_2pp` is the one to read in full, because it is the rule's test and not its easy case.*** Treasury's FY2025 Green Book does carry the proposal — and it is a **1.2 percentage point** increase in each of the additional Medicare tax and the NIIT above $400,000, both to 5 percent (report pp. 76–77), whose revenue row prints **$403,790M** over FY2025–2034 (report p. 242). The FY2024 volume prints **$344,371M** for the identical proposal; the FY2023 volume has no such proposal. **−$310.0B is none of them** — the only "310,0xx" anywhere in the FY2025 volume is the **child-credit expansion at −$310,024M**, 0.008% away and a *cost*, the opposite sign to the raiser this row scored. The model's 2pp figure sits **1.2% from Treasury's 1.2pp row**, so adopting the document without also re-shaping the policy would have turned the tier's third-worst row into one of its best in a single line of diff. It was not taken: the static path is linear in the rate, so **restated on the document's own rate the model reads −$245.2B against −$403.8B, 39.3% under** — which is what this row's accuracy actually is, and it is worse than the 31.8% it had been reporting. PR #144 saw the shadow of this and said so at the time: *"a row cannot sit within 1.5% of a published figure on a base held three years stale unless something else over-states by about as much."* A `.v2` at −$403.8B with `rate_change=0.012` is the right row and is the **owner's to register**, because it moves a model output and a provenance lane may not.

*The arithmetic, stated so the shrink cannot be read as an improvement. **Every surviving row's `model_10yr_billions` is byte-identical** and `run_loo.py --donor-matrix` did not move a line. n **26 → 22**, mean **13.8% → 11.3%**, median 10.6% → **8.9%**, within-15 17 → **18**, within-25 **22 → 19** — and the within-25 **share** rose **84.6% → 86.4%**, because three of the four withdrawn rows were themselves inside 25%. Error mass 358.2 → **249.1**. Tier 1 `secondhand` rows: **5 → 0**, against ROUTE §0 criterion ③'s target of ≤ 2. Two classes moved and both shrank rather than improved: AGI-inclusive surtax **17.6% (n=6) → 5.15% (n=2)**, which is now only the two CBO Option 46 rows, and ordinary rate change **14.8% → 11.32%** on `illustrative_1pp_all`'s new target. **The CI gate is re-derived downward on both halves and one of the two moves was already a test failure**: `ceil(11.3 × 1.25) → 15` lowers the ceiling from 20, and the floor must fall from 22 to the live count of **19** because `tests/test_ci_workflow.py::test_no_gate_is_looser_than_the_workflow_rule_derives` already asserts `min_within <= within_25pct`. Per class, `agi_inclusive_surtax` 22 → **7** and `ordinary_rate_change` 19 → **15**, both forced by the same file's one-sided invariants. **R3 is the lane that grows the battery back**, and it should be read as owing this tier four rows.*

*What R2 left for an owner, in one place: a `.v2` for the Medicare surcharge at −$403.8B on a 1.2pp shape; a new TPC case scoring a **10pp** surtax on AGI above $2M against T19-0037's $585.325B, the same base and threshold as the withdrawn row at a rate somebody actually priced; and an `illustrative_1pp_all.v3` carrying `scoring_window_first_year=2023`, since CBO's own 2022 and 2024 editions price one unchanged reform **$104.0B (9.6%) apart** and that gap is most of what is left on the row. Each moves a model output, which is why none was taken here. **And one thing the battery has simply lost**: `illustrative_500k_2pp` was its only rate **cut** and its only positive target, so Tier 1 now tests revenue increases only.*

*Owner decision ③ (2026-09-11) moved this tier **14.5% → 13.8%** on **one row**, and the row it moved was an accounting artefact rather than a model defect. `iija_2021_discretionary.v3` scores the bill on **FY2022–2031**, the ten fiscal years CBO’s own estimate covers, through the `scoring_window_first_year` field PR #126 built and the same `FY2022_TARGET_WINDOW_RULE` — the target is unchanged at +$415.448B and only the shape input moves. **+$340.0B / 18.2% → +$414.3B / 0.3%**, the figure `planning/memos/FY2022_TARGET_WINDOW.md` §6 published *before* the decision was taken. The median fell 11.5% → **10.6%** and within-15 rose 16 → **17**; **within-25 did not move**, because the row was already inside 25%, so the pooled CI floor of 22 is still met with no slack. One class moved — enacted-law spending **13.4% → 7.4%** — and its CI ceiling tightens with it, 17 → `ceil(7.4 × 1.25)` = **10**. Read the 0.3% with the row’s own note attached: two terms nearly cancel under it (a 4.5% over-statement of the total against the $19.8B of FY2032+ tail the window still clips), so it is not evidence about the spend-out profile.*

*Lane R1 (2026-09-11; `planning/lanes/R1_baseline_transcription.md`) moved this tier **11.3% → 11.6%**, and it is the one movement in Wave E that is the model rather than a target. `CBOBaseline` stopped reconstructing each vintage's budget and economic levels from eleven `GDP_RATIOS` applied to FRED's latest nominal GDP plus hand-entered growth rates, and now reads **CBO's own published tables**, transcribed from `US-CBO/cbo-data` @ `284a9566`, pinned by commit and verified by SHA-256 per file. The route is recorded rather than assumed: `cbo.gov` returns HTTP 403 to this environment and the Wayback Machine holds no snapshot of the relevant workbooks, while `github.com/US-CBO` is not blocked and publishes the same tables as machine-readable CSV under a public-domain dedication. **Owner decision ⑩** settled that both CBO repositories count as "CBO's own table" for the `sourced` grade, `cbo-data` preferred.*

*Eleven rows moved and they moved in both directions, because the defect was a **growth rate** rather than a level: CBO's own FY2023 → FY2025 nominal growth is **10.70%** where the hand-entered February 2026 block assumed **8.99%**. Ten rows moved through that channel — `cbo_opt46_agi_surtax_1pp_20k` **49.8% → 7.9%**, `cbo_opt46_agi_surtax_2pp_100k` **37.4% → 2.4%**, `cbo_opt45_all_rates_1pp` **22.4% → 1.3%** and `cbo_opt45_top4_brackets_2pp` **12.4% → 14.3%** against `biden_high_income_tax` **9.2% → 21.9%** and `illustrative_1pp_all` **10.5% → 14.3%**. **A row that improves when the base is wrong is a row that was cancelling two errors**, which is what `biden_high_income_tax`'s old 9.2% turns out to have been. The eleventh row moved through a channel nobody had listed: `cbo_opt56_employer_health_income_only` **13.1% → 12.8%**, because the cap limit's chained-CPI proxy reads `vintage_assumptions(vintage)["inflation"]` — a baseline **assumption**, not a level. It was bisected against the data (disabling only the assumption series restores −605.76; disabling only the GDP levels does not). **A baseline has two surfaces a score can read, and a lane that enumerates one of them will miss rows.**

*What the transcription does and does not cover, because `VINTAGE_SOURCING` now says so **per line** rather than asserting one grade for a whole vintage — which matters, since all three vintages had been graded `sourced` and the grade was **false for two of them** (February 2024 was 0.602pp off CBO's own real-GDP path and 1.048pp off its LFPR; February 2026's ten-year Treasury note **fell** 4.5% → 3.9% where CBO's own table **rises** 4.10% → 4.38%, so a baseline whose interest-rate path points the wrong way was pricing debt service the wrong way). All three vintages' **economic** paths are transcribed. **Two of three budget paths** are: `cbo-data`'s `ten_year_budget` ships `2024-06`, `2025-01` and `2026-02` only, and June 2024 is publication **60039**, *An Update to the Budget and Economic Outlook* — a different document whose FY2025 deficit is $1,937.9B against the January 2025 edition's $1,865.3B, so borrowing it would have graded a vintage `transcribed` against a document it does not name. **February 2024 therefore keeps a reconstructed budget path, and its debt/GDP ratio must not be quoted**: its GDP is CBO's and its debt is this module's reconstruction, so the ratio is a mixture.*

*The app's default February 2026 vintage is CBO publication **61882**, *The Budget and Economic Outlook: 2026 to 2036*, through CBO's 51118 data release. It reproduces that report's own printed headlines — **FY2026 −$1,852.7B** ("$1.9 trillion"), **FY2027–2036 −$24,406.0B** ("$24.4 trillion") and **FY2036 −$3,115.4B** ("$3.1 trillion") — and the app's ten-year figure of **$23,143.3B** is the same table summed over the app's own **FY2026–2035** window against CBO's printed $23,143.3B. **CBO's headline ten-year window is FY2027–2036**, so the two figures are different decades of one table and not a disagreement; `tests/test_cbo_baseline_transcription.py` pins all four. Downstream, Ask's `get_cbo_baseline` reports **$23,143.3B** and **118.0%** end-of-window debt/GDP where it reported $29,529.1B and 103.8%, and Build's target strip a mean annual deficit of **$2,314.33B** on mean window GDP of **$38,255.37B**, 6.05% of GDP. Those are the app's FY2026–2035 window; the bare library default still starts at 2025, so a scorer built with no start year returns **$22,139.6B** and **116.2%** — the same transcribed table over a different decade, not a second figure.*

*Eight shipped presets moved **+2.97%** on the static path and two corporate presets moved in dynamic mode only — **against a registered prediction of zero**, which is the lane's sharpest process finding. The first sweep scored `PRESET_POLICIES[label]`, a dict rather than a `Policy`, so all 106 rows raised and were recorded as errors **identically before and after**: PR #119 §7.5 in a second costume, with the narrower lesson that **a sweep must fail loudly on a row it could not score.***


*Wave C (PR #151; 2026-09-11) moved this tier **14.7% → 14.5%** on **one class**, and the class's own composition changed more than its mean did. `CapitalGainsBaseline._decedent_template` divided households by `estate_flow_rate` — Poterba & Weisbenner's **dollar** flow of estates over DFA net worth, dollars over dollars — to get a headcount of **408,532** decedents against roughly 3.09 million NCHS deaths, while `death_exit_rate()` has returned `mortality_weighted_net_worth_share` (**2.647%/yr**, the NCHS 2022 life table against DFA net worth by age) and priced the lock-in wedge and the accrued-gains drift with it since Wave 2: **one module, two death rates 8.3× apart**. The count is now the second of those, **3,384,194**, and **the level is untouched** at $196.2097B in 2025 — gains at death by DFA group are identical to twelve significant figures, so the count enters only as a divisor and a fixed per-donor exclusion bites 8.3× harder. `cbo_opt51_gains_at_death` **20.3% → 35.5%**, a registered regression; `biden_capital_gains_39` **32.8% → 27.0%**; `treasury_capgains_39_plus_stepup_elim.v2` **18.4% → 1.8%**; `cbo_opt47_ltcg_qdiv_2pp` unmoved to the cent. Capital gains **20.5% → 18.7%**, mass 82.0 → 74.8; every other class byte-identical; within-25 **23 → 22**, exactly the CI floor, which the lane had registered as its own falsification boundary. **Read the 1.8% as half of a two-sided correction and not as accuracy**: the count and the level come from the **same** PW ratio, only the count was authorised to move, and held against `death_exit_rate` that flow implies **0.372% of the accrued-gains stock** where the stock's death exit is priced at **2.647%** — a factor of **7.1**, some of it PW's inter-spousal exclusion and none of it measured. `cbo_opt51` under-predicts, so a larger level would close what this lane opened. **The plan's instruction to grade the rate by estate size was refuted in sign, off the two tables it itself named**: DFA net worth by age against NCHS `Lx` says the wealthy are older and therefore die at a **higher** rate — head-weighted 1.6456%, net-worth-weighted 2.6468%, size-graded at the top **2.8400%** — so grading takes the implied count above $12.92M to 38,908 where the uniform swap takes it to 36,262, both **further** from SOI's 7,194, not nearer. And W7's arithmetic prediction was wrong by more than 4×: it said about *twice* the count would reproduce Treasury's $1M → $5M step of $33.4B, and 8.3× the count takes that step to **$9.40B**, through Treasury's figure and out the other side. The SOI comparison also needs a unit before it is a comparison — SOI counts *individual* decedents over a *gross-estate* threshold and the model counts *households* over net worth. **No other Wave C lane touched this tier**, and no target moved in the wave.*

*Waves A and B of `planning/HIGH_STAKES_ACCURACY.md` (PRs #140-#146; 2026-09-10) took this tier from **15.0% to 14.7%** by way of **15.6%**, and the intermediate figure is the honest part. **PR #144** grew the generic base on the scored vintage: every generic run had returned the same tax-year-2023 SOI annual ten times, across a decade in which CBO's own baseline grows nominal GDP 28.8%, so the base now carries that vintage's own index (window mean **1.355952**). Ten rows moved, every pre-registered figure landed with a worst miss of **$0.08B**, and the tier mean **rose** — which is the plan's own stated falsification condition, fired and reported rather than tuned away, because six rows had been under-predicting by *less* than a decade of the baseline's growth is worth. **PR #146** then gave the AGI-stated rows SOI's **AGI column**. That defect was a **unit mismatch rather than a level**: `_estimate_from_irs_data` selected returns by an **AGI** class boundary (SOI publishes size classes on AGI) and then computed `max(0, avg_TAXABLE_income - T)`, subtracting a threshold from an average of a different quantity. Which column each row reads is now transcribed from its own source's sentence, so **three of the six AGI-inclusive rows moved and three did not**. The two Option 46 rows ran **49.8% -> 34.1% -> 7.4%** and **37.4% -> 17.9% -> -2.9%**; `warren_ultramillionaire_surtax_3pp` went 19.0% -> -5.2% -> **24.8% over**, a registered regression on the class's best-scoring row; `cbo_opt45_all_rates_1pp` 22.4% -> **1.9%**; `biden_high_income_tax` 9.2% -> **18.0%** and `cbo_opt45_top4_brackets_2pp` 12.4% -> **14.9%**, both crossing their targets. **The plan's own 9.1% / 1.0% endpoints for the Option 46 rows were unreachable as written**: its §1.3(c) attributed them to a *preset* flag that cannot move a validation row, and the missing third step was the column — measured, before any file was opened, in `planning/lanes/HSB_h2_base_growth.md` §3.1. **Neither lane took the flattering option.** PR #146's rule leaves `medicare_surcharge_2pp` (31.8%), `illustrative_top_rate_5pp` (20.2%) and `illustrative_500k_2pp` (18.3%) on the taxable column because their own sources say so — and the first of those has a statutory base, wages plus net investment income, that is **neither SOI column**. Moving all six anyway would read **17.8%** for the tier against the measured 14.7%, so holding them is also the lower number, and the lane published that conflict of interest so the reason can be overturned by a document rather than by a preference. Only two classes moved: AGI-inclusive surtax **20.7% -> 17.6%** and ordinary rate change **12.0% -> 14.8%**, where all four rows crossed from under- to over-prediction. Error mass **390.7 -> 383.3**.*

*Wave 7 (PRs #126, #127, #131, #132; 2026-09-06) took this tier from **15.2% to 15.0%** while making **six of its seven moved rows worse**, and the composition is the whole story. The median fell 11.4% → **10.6%**, within-15 rose 16 → **17**, within-25 stayed at **22**. Three lanes moved rows and **all three registered regressions in advance**. **PR #127** built the filing-status split the sources have always required: statutory income-tax boundaries are stated per filing status ("AGI above $20,000 for single filers and $40,000 for joint filers"; four separate amounts in the FY2025 Green Book's top-rate proposal), `TaxPolicy.affected_income_threshold` was a scalar, and `IRSSOIData` read only Table 1.1, which has no filing-status dimension at all — so one status's floor was applied to all four populations, taxing 46.1M joint returns from $20,000 up where JCT starts them at $40,000, **$839.8B of base, 9.2% of the whole**. `scripts/build_filing_status_data.py` transcribes IRS SOI **Table 1.2** and `get_bracket_distribution_by_status` takes only the *composition* from it — each Table 1.1 class total times that status's share of the class — so a uniform threshold reproduces the pooled path to the cent, which is the lane's own control. `cbo_opt46_agi_surtax_1pp_20k` **44.7% → 49.8%**, `cbo_opt46_agi_surtax_2pp_100k` **16.1% → 37.4%**, `cbo_opt45_top4_brackets_2pp` **17.9% → 12.4%**, `biden_high_income_tax` **12.0% → 9.2%**, every one landing exactly on its pre-registered figure. **PR #126** gave `CBOScore` a `scoring_window_first_year` and scored `treasury_capgains_39_plus_stepup_elim` on FY2022–2031, the decade its own document covers, under the `iija_2021_discretionary.v2` rule — target unchanged at −$322.0B, shape input superseded to `.v2`. **PR #132** replaced the five-class decedent ladder with a fitted piecewise-Pareto size distribution and moved three rows a little further out (`cbo_opt51_gains_at_death` 19.3% → **20.3%**, `biden_capital_gains_39` 31.4% → **32.8%**, and the Treasury row 43.3% → 45.4% before the window change). **PR #131** moved no Tier 1 row. Read the mean the way the lanes reported it: **no lane's branch figure is the merged one**, because #126 and #132 move the same Treasury row in opposite directions — #126 alone gave 14.1%, #127 alone 15.9%, #132 alone 15.4%, and the merged tree gives **15.0%** on an error mass of **390.7** against 395.1 after Wave 6.*

*The **CI gate is unchanged at 20 / 21 and re-derives to itself** on the Wave 7 battery: ceiling `ceil(15.0 × 1.25) = 19`, rounded up to the nearest 5 is **20**; floor `22 − 1` = **21**. PR #126's own memo had stated a floor of 22 on its branch, where within-25 read 23; the merged tree reads 22, so the tightening it flagged does not apply and the coordinator has nothing to move.*

*PRs #119–#122 (2026-09-05) took this tier from **15.9% to 15.2%** on **one row**, and left the median, the within-15 count and the within-25 count exactly where Wave 5 left them (11.4%, 16, 22). **PR #121** projected the corporate base off CBO's own February 2024 receipts path (publication 59710 Table 1-1) times a 4.80133 base-$/receipts-$ ratio anchored on SOI TY2022 ÷ MTS FY2022, with a §6655 convolution for the fiscal-year phase, and `cbo_opt64_corporate_rate_1pp` went **62.3% → 44.5%** against a pre-registered band of 42 ± 4. Every other row is identical to the decimal. What the lane closed is an inconsistency independent of any target: the previous path kept SOI's published statutory base but aged it at a flat 4%/yr, so by FY2033 it priced a percentage point of statutory rate against **more base than the entire baseline corporate tax implies exists** (window-average marginal share 90.8%, above 1.0 by FY2034). It is now **80.8%**, flat by construction. Twenty of the row's sixty-two points were a vintage problem; the remaining forty-four are credit carryforwards under §38(c) and §904(c), CAMT, and the individual-side dividend interaction, none of which is in this module's power to close from a published source. **PR #119** (the offset-sign sweep) and **PR #122** (the corporate/PTC provenance pass) moved **no** Tier 1 row — both checked it by diffing `cold_holdout.py --json` against their branch points rather than by reading the summary line — and **PR #120** was a memo that changed no code. The CI gate is unchanged at 20 / 21 and re-derives to itself.*

*Wave 5 (PRs #113, #114, #116) took this tier from **18.0% to 15.9%** and its median from 12.6% to **11.4%**, within-15% 14 → **16** and within-25% 21 → **22** — and it did so while landing **two pre-registered regressions**, which is the reading to keep. **PR #113 payroll** did all of the improvement and more: the two Option 61 rows went **54.1% / 55.5% → 7.5% / 8.1%**, from the tier's 25th and 26th most accurate rows to its **7th and 9th** (the lane doc says 8th and 10th, which held on its own branch before the other two Wave 5 lanes moved rows past them). The plan had scoped them as an employer-share-incidence and income-tax-offset problem; CBO's own option text says the tax "would be paid entirely by employees", so that offset does not exist, and the actual defect was `$400B / 2.9% = $13,793B` — Medicare receipts divided by a rate that does not raise all of them, since the 0.9% Additional Medicare Tax sits on a far smaller base four lines above it in the same dict. The base is now CBO's own February 2024 wage path times the Trustees' covered-earnings ratio, and on that base the lane's hand arithmetic reproduced both rows to the decimal. **PR #114 corporate** was registered as a regression and landed as one: `cbo_opt64_corporate_rate_1pp` **47.1% → 62.3%**, because the derived path prices a percentage point on IRS SOI Table 11's published statutory base ($2,879.1B, TY2022) instead of a fitted $1,900B that is within 3% of the **TY2018** vintage. Two published documents price that point 42% apart — CBO 60557 at $135.7B over the window, Treasury's FY2025 Green Book at $192.8B — with the *larger* rate change carrying the *larger* per-point yield, which no concave-in-rate behavioural response produces; the residual is a disagreement between sources, not a defect this module can close. **PR #116 preferential rate** projected the realizations base with the accrued-gains stock it is a flow off (`R(t) = h·A(t)`, no new constant), taking **CBO Option 47 44.8% → 10.5%** — 34.3 of its 44.8 points closed with nothing else in the rate channel touched — and, as registered, moving the two Green Book rows the other way: `biden_capital_gains_39` **16.7% under → 31.4% over**, `treasury_capgains_39_plus_stepup_elim` **0.2% → 43.3% over**. **The 0.2% was never accuracy** — Wave 4's own lane doc had already recorded it as two errors cancelling — and this lane removed one of the two; about **17 of the 43 points are the window** the row is scored on. The lane also **refuted** the standing qualified-dividends hypothesis: SOI Table 3.5's preferential columns exceed the whole year's realized gains in both vendored years (1.046 and 1.189), so they already contain qualified dividends, and adding a column would have double-counted $313-336B of base. **PR #117** then re-derived the CI gate by the workflow's own rule: 25/20 → **20/21**, both tightening.*

*Wave 4 (PRs #105, #107, #108) took this tier from **31.0% to 18.0%** and its median from 15.1% to **12.6%**, within-15% 13 → **14** and within-25% 19 → **21**, on five rows. **PR #108 did almost all of it**: giving the death channel the six carve-outs a realization-at-death proposal does not tax — spousal, charitable, the §121 residence exclusion, tangible personal property, a family-business deferral, and the per-donor exclusion applied *after* the others — plus a semi-log rate response at death, took the tier to 18.5% on its own and the capital-gains error mass **405.6 → 81.0**, from 50.3% of the tier to 17.3%. `treasury_capgains_39_plus_stepup_elim` 217.5% → **0.2%**, `biden_capital_gains_39` 134.9% → **16.7%**, and `cbo_opt51_gains_at_death` 8.4% → **19.3%, worse and pre-registered as a regression** — its 8.4% had been bought by taxing charitable bequests and small decedents' housing gains that no such regime reaches. **The 0.2% is two errors cancelling and must not be quoted as accuracy**: the mechanism removes 87.2% of that row's death channel where the pre-registered hand path said 92.8%, and the lane's own falsification test fired because the two Green Book rows land on opposite sides of their targets. The diagnosis is not the exclusion ordering (pinned by a test; applying it first moves both the same way) but the **five-class decedent ladder having no within-group dispersion** — moving the exclusion from $1M to $5M costs the model $82.2B of death channel where it costs Treasury $33.4B. **PR #105** took CBO Option 56 **24.0% → 13.1%** by giving the excess share CBO's own chained-CPI indexation instead of evaluating it once at `start_year`; **PR #107** moved `biden_high_income_tax`'s target from a rounded −$252B to the Green Book's own printed −$245.9B (`.v2`), which moved only the error column, 14.1% → **12.0%**. **PR #110** then re-derived the CI gate by the workflow's own rule: 40/18 → **25/20**.*

*Wave 3 (PR #100) added the 26th case and moved the mean 31.3% → **31.0%**, the median 14.1% → **15.1%**, and within-25% 18/25 → **19/26**. **No existing row moved by a cent**: the only change is that CBO Option 56 stopped being a leakage exclusion, because lane L6 had removed the fitted annual its only expressible path used to run through. It enters at **−$529.9B against −$697.0B, 24.0%** — the tier's first tax-expenditure cap, and its residual is a named omission rather than a tuned parameter (below). Wave 3's other three lanes touch no Tier 1 row: L9 international and L8 tariffs have no case in the tier, and L3 credits builds no `TaxCreditPolicy` in it.*

*Wave 2 (PRs #93, #94, #95) moved this tier from 34.4% to **31.3%** and its median from 16.1% to **14.1%**, on the capital-gains rows only — lane L1 replaced the realizations base, the elasticity unit, the lock-in multiplier and the gains-at-death constant. Two rows improved (`cbo_opt51_gains_at_death` 84.4% → **8.4%**, `cbo_opt47_ltcg_qdiv_2pp` 99.1% → **44.8%**), one barely moved (`biden_capital_gains_39` 142.3% → 134.9%) and one got worse (`treasury_capgains_39_plus_stepup_elim` 153.6% → **217.5%**), because the derived lock-in wedge runs the *other* way on a proposal that eliminates step-up. Four rows the lane did not name also moved, all through `preferential_income_share` reading the new SOI bracket base: `cbo_opt45_top4_brackets_2pp` 25.8% → **17.9%**, `illustrative_1pp_all` 2.6% → 4.1%, `cbo_opt45_all_rates_1pp` 21.1% → 22.4%, `biden_high_income_tax` 12.9% → 14.1%. Neither L4 (estate) nor L6 (tax expenditures) touches a Tier 1 row. The lanes' pre-registrations are in [`planning/lanes/`](../planning/lanes/).*

*Wave 1 had earlier moved this tier from 52.6% to 34.4% and its median from 21.1% to 16.1%, on the eight spending rows only. Lane L2 (PR #85) added the budget-authority-to-outlay spend-out model the battery had been diagnosing since Phase D; PR #88 then superseded IIJA's shape input with CBO's own authorization schedule (`.v1` → `.v2`, target unchanged). No tax row moved, and no target was edited. The two lanes' pre-registrations are in [`planning/lanes/L2_spend_out.md`](../planning/lanes/L2_spend_out.md).*

*Phase E had earlier changed two rows, in opposite directions and for the same reason — somebody opened the document. `top_rate_45` was **retired**: its -$420B is in no TPC, CBO or JCT publication. `biden_capital_gains_39` was **re-sourced** from an unsupported -$456B to the FY2025 Green Book's actual line item, -$288.6B, and its shape corrected to the source's own definition, which made it score worse. Details below and in [`preregistered.py`](../fiscal_model/validation/preregistered.py).*

| Case | Official | Model | Err | Source (date) | Baseline the source used | Pre-registered at |
|------|---------:|------:|----:|---------------|--------------------------|-------------------|
| Cut international affairs 25% | -$187B | -$187B | 0.0% | CBO Options 2025-2034 #37 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| IIJA 2021: discretionary component | +$415B | +$414B | 0.3% | CBO, S.Amdt. 2137 (2021-08) | CBO July 2021 (no vintage in repo), scored on its own FY2022-2031 decade | `97cc6a6` (`.v3`, superseding `.v2`), scored `2cde296` |
| All ordinary rates +1pp | -$1,185B | -$1,201B | 1.3% | CBO Options 2025-2034 #45 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Cut selected nondefense discretionary | -$339B | -$333B | 1.7% | CBO Options 2025-2034 #42 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Treasury 39.6% + step-up repeal | -$322B | -$316B | 1.8% | Treasury (2021-05) | Green Book FY2022, scored on its own FY2022-2031 decade | `d11bf2c`, scored `6c9bfa2`; `.v2` window `2d13e60` |
| AGI surtax 2pp (>$100K single) | -$1,051B | -$1,076B | 2.4% | CBO Options 2025-2034 #46 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| End national community service funding | -$10B | -$11B | 2.6% | CBO Options 2025-2034 #38 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| New 1% payroll tax (all earnings) | -$1,282B | -$1,378B | 7.5% | CBO Options 2025-2034 #61 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| AGI surtax 1pp (>$20K single) | -$1,440B | -$1,326B | 7.9% | CBO Options 2025-2034 #46 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Tighten Pell grant eligibility | -$22B | -$20B | 8.1% | CBO Options 2025-2034 #39 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| New 2% payroll tax (all earnings) | -$2,540B | -$2,745B | 8.1% | CBO Options 2025-2034 #61 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Social Security Fairness Act: WEP/GPO repeal | +$196B | +$215B | 9.8% | CBO, H.R. 82 (2024-09) | CBO June 2024 (no vintage in repo) | `aed5318`, scored `dca3a50` |
| LTCG + qualified dividends +2pp | -$103B | -$92B | 10% | CBO Options 2025-2034 #47 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Cut certain state and local grants | -$67B | -$74B | 11% | CBO Options 2025-2034 #43 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Fiscal Responsibility Act: discretionary caps | -$1,332B | -$1,170B | 12% | CBO, H.R. 3746 letter (2023-05) | CBO May 2023 (no vintage in repo) | `aed5318`, scored `dca3a50` |
| Limit the income-tax employer-health exclusion | -$697B | -$608B | 13% | CBO Options 2025-2034 #56, **3rd alternative** (2024-12) | CBO Feb 2024 (matched) | `3738ffc`, scored `d189a26` |
| 1pp all brackets | -$1,081B | -$1,236B | 14% | CBO Options 2023-2032 Vol. I #13 alt 1 (2022-12), JCT estimate | CBO May 2022 (scored on Feb 2024; window not adjusted) | `1ada902` (`.v2`, superseding `.v1`) |
| Top four ordinary brackets +2pp | -$570B | -$671B | 18% | CBO Options 2025-2034 #45 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Biden top rate 39.6% ($400K+) | -$246B | -$300B | 22% | Treasury (2024-03), Green Book FY2025 table row | Green Book FY2025 | `318be6b` (`.v2`, superseding `.v1`), scored `22ccdd2` |
| Biden capital income at ordinary rates | -$289B | -$366B | 27% | Treasury (2024-03), Green Book FY2025 table row | Green Book FY2025 | `0bcfbc3` (`.v2`, superseding `.v1`) |
| Tax accrued gains at death | -$536B | -$346B | 36% | CBO Options 2025-2034 #51 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Corporate rate +1pp (21% to 22%) | -$136B | -$196B | 44% | CBO Options 2025-2034 #64 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |

Live figures: `python scripts/cold_holdout.py`. Rows are the `Generic` category of the scorecard; every one has a row in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py).

#### The CBO Options battery (Phase B)

Fifteen of the 26 cases come from CBO, *Options for Reducing the Deficit: 2025 to 2034* ([publication 60557](https://www.cbo.gov/publication/60557), December 2024; reposted with updates October 2025) — 76 independently scored single-provision options, the largest such published set that exists. They are extracted to `fiscal_model/data_files/validation/cbo_options_2025_2034.csv` (one row per option, from Table 1-1) and `..._alternatives.csv` (one row per reported line in each option's own table) by [`scripts/extract_cbo_options.py`](../scripts/extract_cbo_options.py), and classified in [`fiscal_model/validation/cbo_options.py`](../fiscal_model/validation/cbo_options.py).

**15 runnable alternatives across 12 options; 64 options out of scope, each with a one-line reason.** `tests/test_cbo_options.py` asserts the accounting closes, so no option is silently dropped. Reasons, tallied:

| Why not runnable | n |
|------------------|--:|
| Mandatory program-rule change (benefit formula, eligibility, payment rate). CBO publishes no funding-level *input* distinct from the outlay path being predicted, so feeding the first-year outlay back in would make the "prediction" an aggregation of the target itself. | 27 |
| Revenue base or instrument with no module: excise, VAT, financial transactions, accounting-method timing, filing status, deduction bases, bond and fee schedules, non-covered employment. | 23 |
| Discretionary path that is a ramp, wind-down or declining caseload rather than a level `SpendingPolicy` can express (Options 28-36, 40, 41, 44). | 12 |
| **Leakage.** The module constant that would score it was calibrated to reproduce that same reform from another source: Option 53 (NIIT expansion — the module's $25B/yr is fitted to JCT's estimate of it), Option 62 (Social Security taxable maximum — the covered-wage bands are anchored to reproduce the Trustees' 90%-coverage and $250K-donut annuals). | 2 |

Excluding Option 62 costs the battery its two largest payroll targets, and that is the point: scoring them would have measured bookkeeping, exactly what Tier 2's by-construction number already measures.

**A leakage exclusion is not permanent, and Option 56 is the proof.** It was the third leakage case: the only path that could score a cap on the employer-health exclusion ran through `cap_employer_health`'s fitted annual. Lane L6 (PR #94) removed that dependency — a percentile cap is now the *published* expenditure level (`JCT_TAX_EXPENDITURES["employer_health"]`, $250B/yr) times a **share** read off a premium distribution — so nothing calibrated to a target sits in the path any more, and PR #100 promoted the option. Three things about the promotion are worth stating rather than assuming:

- **One alternative, not three.** CBO's first two alternatives limit the income *and payroll* tax exclusion; the module carries the income-tax expenditure and has no payroll base, so scoring them would be a known base mismatch, not a prediction. 56.3 and 56.6 join `OUT_OF_SCOPE_ALTERNATIVES` per alternative. The third — *"Limit only the income tax exclusion … to the 50th percentile of premiums"* — is the one scored.
- **The target is the deficit row, not the revenue row.** −$697B is CBO's bottom line ($709B of added revenue net of $12B of added mandatory outlays), read from report p. 66 (PDF p. 72). Note for whoever next touches the extractor: in `cbo_options_2025_2034_alternatives.csv` the *revenue sub-rows* of three-line options carry a mechanically negated `savings_*` figure, so 56.2/56.5/56.8 read as negative savings for a revenue increase. The `Decrease (−) in the deficit` rows are right, and this battery reads only those.
- **The shape inputs were fixed by a written rule before the option ran** (`OPTION_56_SHAPE_RULE`): CBO's own stated 2028 limits ($10,000 individual, $24,400 family) and `effective_start_year=2028`, the first fiscal year CBO's table shows a non-zero effect. The premium distribution's *shape* parameter σ is identified from the two percentile values this same option prints — a design input, exactly like the budget-authority level a spending option donates to its own prediction, and a different series from the revenue being predicted. The level is KFF's, not CBO's, and the two disagree: the model's implied 2028 family median is $27,946 against CBO's $24,400, 14.5% high, which is why σ is information rather than a mirror.

The result is **−$605.8B against −$697.0B, 13.1%** since Wave 4 (PR #105), from −$529.9B / 24.0% when the row entered. The named omission the row entered with was **the whole of the improvement, and it was the source's own mechanism rather than a parameter**: CBO's revenue grows ~14%/yr because the dollar limit is indexed to the chained CPI-U while premiums grow faster, so a widening slice of every premium rises above it, and the module now asks the excess share what year it is instead of evaluating it once at `start_year`. Nothing was chosen against −$697B — the indexation is a sentence in the option text, the price leg is the repository's own baseline path, the premium leg is the record's own 4%, and the pre-registered escape hatch (5%/yr premium growth, which would land the row at 0.6%) was declared in advance and **not taken**. The model's revenue path now grows at 8.3%/yr against 4.0% before.

**What is left of the residual is two findings, both named and neither tuned.** About half is a **base omission**: CBO does not cap premiums, it caps "the total amount of contributions for a worker's premiums **and health spending accounts**" (report p. 66 names FSAs, HRAs and HSAs), and the repository's premium distribution has no account dimension — a level *and* a shape error, since account contributions concentrate in the same households whose premiums already exceed the cap. It is now the first line of the row's `known_limitations`, and it is a data gap with a named source (MEPS-IC, KFF), not a mechanism gap. About a fifth is an **unsourced behavioural offset whose sign convention is the reverse of the base class's**: `TaxExpenditurePolicy.estimate_behavioral_offset` returns an offset opposite in sign to `static_effect` where `TaxPolicy` returns one with the same sign, so the expenditure module *magnifies* where the tax module erodes. On this row that is worth +20% (−$504.8B without it, −$605.8B with), and it is directionally right *here* — CBO's text says both behavioural channels increase revenue — but unsourced in magnitude on every expenditure benchmark. Changing it is module-wide and moves every other expenditure row in both the fitted tier and the leave-one-out column, so it is an owner decision on the carry-over list, not a lane's. The validation shape pins `mode="derived"` and `annual_revenue_change_billions=None`; routing it through the module's app default (`reported`) would reproduce the leakage the option was excluded for.

**The remaining out-of-scope alternatives are now sized.** Alternatives 1 and 3 apply the same limits to the same base and differ only in whether the payroll exclusion is limited too: $985B against $709B, so the payroll leg is **$276B, 38.9% of the income-tax leg**. Reaching it needs the joint distribution of premiums and earnings (the OASDI leg stops at the taxable maximum and the HI leg does not), and the repository has both marginals and neither joint.

**Which spending options qualify** is decided mechanically, not case by case. `SpendingPolicy` produces `level × 1.02**t`, so `is_level_budget_authority_path()` requires CBO's *own* published budget-authority path to stay within 25% of that profile from the first effective year. Five options pass (37, 38, 39, 42, 43); twelve fail. The test is applied to CBO's numbers, never the model's.

**Baseline vintage.** The report states its baselines on page 2: revenue options are measured against CBO's **February 2024** baseline (pub. 59710), spending options against the **June 2024** baseline (pub. 60039). The battery is scored on `BaselineVintage.CBO_FEB_2024` through the new `build_scorer_for_vintage()` in `validation/core.py`; the repository has no June-2024 vintage, and that mismatch is written on every spending row of the manifest rather than left implicit.

Worth stating plainly, because it is a negative result: **vintage matching moves none of these 15 scores.** The two baselines really do differ ($61.8T vs $61.5T of projected revenue), but every uncalibrated shape is bottom-up — SOI filer counts, the module's Medicare revenue identity, a source-stated budget-authority level — and none of them reads a level off the baseline. Baseline drift is a real contaminant for shapes that scale off baseline aggregates (Phase D's concern); it is not one here. The plumbing is in place and honoured, and that is what it buys.

**Effective dates are the source's.** A spending option that takes effect in October 2025 is scored from FY2026, not FY2025, so the model is not credited with a year of effect the official estimate never scored. `effective_start_year` is read from CBO's own table, pre-registered before scoring, and never adjusted afterwards.

#### Enacted-law replications (Phase D)

Three of the 26 cases replicate laws that actually passed. They are components,
not bills: the headline score of an enacted law is a *net* of provisions no
single policy shape can construct, and scoring a total you cannot build is not a
prediction. So each case takes the one component whose own annual level the CBO
cost estimate itself states, and the rest of the bill is recorded out of scope
with CBO's component figures.

One rule set every annual level, fixed in the manifest
(`PHASE_D_SPENDING_LEVEL_RULE`) before any of them was scored: *the source's own
stated funding or benefit change for the first fiscal year in which the provision
is fully in effect, excluding any year the source itself describes as carrying
retroactive or transition amounts, grown at the module default 2%/yr.*
`effective_start_year` is the first fiscal year the source's table shows a
non-zero effect, so the model window matches the source's own non-zero window.

| Bill | Expressible component | Shape input the source states | Official | Model | Err | What the residual is |
|------|----------------------|------------------------------:|---------:|------:|----:|----------------------|
| Social Security Fairness Act of 2023 (H.R. 82) | WEP/GPO repeal, direct spending | +$19.67B (FY2026 outlays; FY2025 carries CBO's retroactive catch-up) | +$195.65B | +$214.8B | 10% | **Not a spend-out case, before or after L2.** Benefits are outlaid in the year they are owed, so there is no authority-to-outlay lag; the `mandatory_benefit` profile is 0.977 in year 0 and the row moved 10.1% → 9.8%. The residual is the model's 2%/yr growth against CBO's ~1.1%/yr. A mapping that closed it would be a fitted mapping. |
| Fiscal Responsibility Act of 2023 (H.R. 3746) | Section 101(a) discretionary caps | -$112.3B (FY2024 budget authority; FY2025 is -$135.9B) | -$1,331.8B | -$1,169.5B | 12% | **Pre-registered to get worse, and it did** (5.8% → 12.2%). The old 5.8% was two errors cancelling: the model over-predicted the early years, because it outlaid authority immediately, and under-predicted the late ones, because CBO's caps compound against a falling funding base to -$159.7B by 2033 while a level grown at 2%/yr reaches only ~-$134B. Spend-out removes the first error and leaves the second, so the total error rises while the path gets more right. What remains is the **level shape**, not the lag. |
| IIJA 2021 (S.Amdt. 2137 to H.R. 3684) | Discretionary funding and its outlays | CBO's own authorization schedule: $163.0B (FY2022), then $70.1B, $68.5B, $68.1B, $66.2B, then $2.082B/yr, scored on FY2022-2031 | +$415.4B | +$414.3B | 0.3% | **No longer a window miss either, since owner decision ③ registered `.v3` on the decade CBO's own estimate covers.** What is left is two terms that nearly cancel and neither is behavioural: the `construction_and_capital` path outlays $434.1B in total (4.5% high, which is the profile's 0.9727 spend-out sum applied to the full authority) against $19.8B of that falling in FY2032 or later, outside even this window. 0.3% is smaller than either term. |

**IIJA: three rows, three defects, one unchanged target.** The row that reached 356%
was `iija_2021_discretionary.v1`, whose shape input was a $163.0B level carried
forward at 2%/yr — about $1,894B of budget authority against the $446.3B CBO's
own table provides. Spending the wrong authority out correctly cannot fix a
total built on four times too much of it, which is why L2's spend-out model only
took it to **290.2%**. PR #88 then superseded the shape input under the
manifest's own rule — a **new row**, never an edit — because CBO's estimate
states a schedule and `SpendingPolicy.budget_authority_path` can carry one.
`IIJA_AUTHORIZATION_PATH_RULE` sets every year of it: the five figures CBO
states, plus the remainder of CBO's own $446,306M authority total spread evenly
over the years the estimate describes only as "about $2B/yr". One rule sets every
year, so no year is a knob.

| row | shape input | model | official | err |
|---|---|--:|--:|--:|
| `iija_2021_discretionary.v1` | $163.0B level at 2%/yr | +$1,894.0B → +$1,621.1B after spend-out | +$415.4B | 356% → **290.2%** |
| `iija_2021_discretionary.v2` | the source's own authorization schedule, on the runner's FY2025-2034 decade | +$340.0B | +$415.4B | 18.2% |
| `iija_2021_discretionary.v3` | the same schedule, on the FY2022-2031 decade CBO's own estimate covers | **+$414.3B** | +$415.4B | **0.3%** |

The **target never moved** — same $415.448B, same document, same window, same
vintage note — and `.v1` and `.v2` stay in `preregistered.py` unedited with all
of their figures on the record. Between them the three rows separate the three
defects this case surfaced: the missing spend-out model (`.v1`), the missing
authorization path (`.v2`) and the window (`.v3`). Earlier revisions of this file
argued that spreading the source's stated FY2022-2026 authorization evenly still
yields $1,012.9B, and that IIJA was therefore kept as the sharpest evidence for a
missing mechanism. Both halves are now history: the mechanism exists, and the
case is scored on the schedule the source actually states.

**The window is `.v3`, and it is owner decision ③ rather than a lane's
correction.** `.v2` read 18.2% for an arithmetic reason the row's own
`known_limitations` had stated since Wave 7: **$92.6B of its outlays fall in
FY2022-2024**, before the model's FY2025-2034 window opens, so $340.0B was being
compared against a total covering CBO's own FY2021-2031. What the case needed was
a **window**, not a **vintage** — a discretionary `SpendingPolicy` scores its own
source-stated authority and reads no baseline *level*, so
`CBOScore.scoring_window_first_year`, built in PR #126 for
`treasury_capgains_39_plus_stepup_elim.v2`, scores this bill on its own decade
with no 2021 baseline in the repository. `planning/memos/FY2022_TARGET_WINDOW.md`
§6 **published +$414.3B and 0.3% before the decision was taken**, and explicitly
declined to apply it, because a second Tier 1 target decision may not be taken by
implication; this row is that decision, taken. `effective_start_year` was already
2022, so the policy's own start year and its outlay path do not move — only
where the scorer's window opens does, which is what separates a window from a
vintage and from an effective date.

**0.3% is not evidence about the spend-out profile, and the note on the row says
so.** Two terms nearly cancel underneath it: the path outlays $434.1B in total,
4.5% above CBO's figure, which is simply the profile's 0.9727 spend-out sum
applied to the full $446.3B of authority; and $19.8B of that falls in FY2032 or
later, outside even this window. The honest statement is that the authority path
is CBO's own and the fitted profile reproduces its total to 4.5%. (Earlier
revisions of this file said $433.2B and 4.3%, which did not reconcile with the
0.973 spend-out sum they cited either; the measured total is $434.1B.) CBO's table is
also headed FY2021-2031, eleven fiscal years, and a ten-year window cannot cover
eleven — FY2021 is not a gap, because the bill was signed on 15 November 2021,
inside FY2022, and the record's own `budget_window` has read FY2022-2031 since it
was entered, which is the field `FY2022_TARGET_WINDOW_RULE` reads.

**Three bills were examined and left out of scope, with CBO's component figures
recorded** rather than scored:

| Bill | Official | Why no component is scoreable |
|------|---------:|-------------------------------|
| Inflation Reduction Act 2022 | -$90B | Every component the app can express routes through a module whose constant is calibrated to that same reform — the climate module's IRA-repeal annual is documented as fitted to the -$783B IRA-repeal target, and `repeal_corporate_amt`'s base constant is its own target divided by ten. Scoring it would be leakage, not prediction. |
| Tax Relief for American Families and Workers Act 2024 (H.R. 7024) | +$0.4B | CBO's own table: +$117.5B of deficit in FY2024 netting to +$399M over 2024-2033, because a CTC expansion and R&D expensing are offset by barring new ERTC claims. A percentage error against a $0.4B net of $100B-scale components is uninformative whatever the model does. |
| NDAA FY2025 (S. 4638) | +$0.178B | An authorization bill: CBO scores only $178M of mandatory retirement-benefit changes against $895B authorized. The scored quantity is three orders of magnitude below model resolution, and the $895B is not a budget effect at all. |

#### The misses, grouped by cause

> **Read this section with lane R2's withdrawals in hand.** Four of the rows the group masses below are computed over are no longer in the battery, because their targets are in no publication, and a fifth moved onto CBO publication 58164's own option. The causes are unchanged and the *arithmetic* is stale until the next wave recomputes it; the live figures are `python scripts/cold_holdout.py` (22 cases, mean 11.3%, error mass 249.1) and the per-class block it prints. What R2 removed from this accounting is **109.1 units of mass that was never measuring the model** — it was measuring the distance to four numbers this repository had written down itself.

Every miss is kept and carries a `known_limitations` note in the scorecard. Six causes account for all of them, and **capital gains is no longer the largest**: Wave 7 took 22.5 units out of it and put 21.5 into the AGI surtaxes, so the two CBO Option 46 rows are now the tier's largest group. **The old cause "one threshold standing in for a filing-status-specific boundary" is gone, because the mechanism exists** — PR #127 built the split, both Option 46 rows carry per-status floors, and what is left on them is a **base definition and a base growth rate**, which is a different cause and gets its own entry. Group masses (Σ|error %|, tier total **390.7** over 26 cases, from 395.1 after Wave 6, 412.9 after Wave 5, 468.1 after Wave 4 and 805.8 before it):

1. **Module revenue identities applied at the margin (3 cases, 7.5-44.5%; mass 60.1, 16.0% of the tier).** **Wave 5 split this group in half and PR #121 closed most of what was left.** PR #113 corrected the payroll identity — the base was Medicare receipts divided by 2.9%, a rate that does not raise all of them because the 0.9% Additional Medicare Tax sits on a much smaller base — and priced it instead as CBO's own wage path times the Trustees' covered-earnings ratio; the two rows went **54.1% / 55.5% → 7.5% / 8.1%**, and about two-thirds of what is left is a base-growth gap (the model grows the base at CBO's 3.9%/yr wage rate where CBO's own published revenue row implies 3.45%) with a third in FY2025 alone, where CBO's first-year row is 0.48 of its second-year row against the 0.75 a January start and a fiscal year give. PR #114 then rebuilt the corporate rate identity on IRS SOI Table 11's published statutory base and the row went **47.1% → 62.3%, a pre-registered regression**: the fitted $1,900B base was within 3% of the **TY2018** vintage against SOI's TY2022 $2,879.1B. **PR #121 then found the other half of it**: that base *started* right and *grew* wrong, because it was aged at a flat 4%/yr against CBO's own 1.44%/yr for the same receipts, so the marginal base crossed the average base it is part of by FY2033. Projecting it off the vintage's receipts path took the row to **44.5%** and the window-average marginal share from 90.8% to **80.8%**. The residual that remains is **not** the "42% gap in which the larger rate change carries the larger per-point yield" this document used to assert — PR #120's memo refuted that. Per-point dollars are not comparable across statutory rate levels or scopes: the split is **JCT against Treasury OTA** (every corporate-rate option in every *Options* volume carries "Data source: Staff of the Joint Committee on Taxation") times a **scope** difference (Treasury's 28% row has bundled a GILTI step since the FY2023 edition). On the comparable metric — implied marginal base ÷ receipts/rate — the record reads Tax Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury 79.5%, and **this model 80.8%, still above every published estimator**. Nothing in the record supports a yield rising with the step: JCT's 14-point cut from 35% and its 1-point increase from 21% imply marginal bases of $963.2B and $963.0B. Anchoring on TY2019 instead would score the row at 4.2%; the anchor is fixed as "latest published" precisely so that it cannot be chosen. What is left named-and-not-built is credit **carryforwards** — which CBO's 2018 Option 24, the only volume with a narrative, states *is* inside JCT's estimate — and **CAMT**, which begins in TY2023, after the last SOI year on file; §174 and bonus depreciation inflate the TY2022 anchor by at most **11.1%**, and deflating by that takes the row to about 46%, not to CBO.
2. **The bracket-aggregate ceiling on ordinary and AGI-inclusive rate changes (8 cases, 1.5-22.4%; mass 84.9, 21.7%).** Flat SOI bracket aggregates with a single ETI, against sources whose own estimates rise through the window as bracket creep pushes income upward. **Wave 7 changed this group's membership rather than its cause**: `cbo_opt46_agi_surtax_2pp_100k` left it for cause 5 once PR #127 gave the Option 46 rows their own per-status floors, and `cbo_opt45_top4_brackets_2pp` joined it from the old filing-status cause, improving 17.9% → **12.4%** on the way. `biden_high_income_tax` improved with it, 12.0% → **9.2%**, and for a reason worth keeping: the FY2025 Green Book's **married-filing-separately** floor of $225,000 is $175,000 *below* the unmarried $400,000 the model had been applying, so this base had been **under**-counted — every note in the repository describing the single-threshold approximation as uniformly generous was wrong about one of the four rows carrying it. Wave 4's provenance pass had earlier taken 2.1 units out of the group by moving `biden_high_income_tax` onto the Green Book's own printed row.
3. **Capital-gains behaviour at the top rate and at death (4 cases, 1.8-35.5%; mass 74.8, 19.9% of the tier).** **This was 405.6 units and 50.3% of the tier before Wave 4 and 80.9 after it; Wave 5 put 23.6 units back, on purpose, and Wave 7 took 22.5 out again — 21.3 of them the window and the rest, in the other direction, the decedent distribution.** Wave 2's L1 rebuilt the base, the elasticity unit and the gains-at-death stock; Wave 4's PR #108 built the carve-outs L1 left out — a realization-at-death proposal does not tax **spousal transfers, charitable bequests, the §121 residence exclusion, tangible personal property, or family-owned businesses that elect deferral**, and it applies the per-donor exclusion *after* all of those — plus a semi-log rate response at death. Wave 5's PR #116 then fixed the last stale input in the *rate* channel: the realizations base was IRS SOI tax year 2023, priced unchanged in every year of the window, and it is now grown with the accrued-gains stock it is a flow off (`R(t) = h·A(t)` at the module's own 5.8% net-worth CAGR, no new constant). That closed **34.3 of `cbo_opt47_ltcg_qdiv_2pp`'s 44.8 points, to 10.5%**, and moved the two Green Book rows from under to over, both pre-registered: `biden_capital_gains_39` 16.7% → **31.4%** and `treasury_capgains_39_plus_stepup_elim` 0.2% → **43.3%**. **Read the Treasury row's history in full: 217.5% before Wave 4, then 0.2%, now 43.3% — and the 0.2% was never accuracy.** Wave 4's own lane doc recorded it as two errors cancelling (the mechanism removes 87.2% of that row's death channel where the pre-registered hand path said 92.8%), and a stale base was the second of the two; Wave 5 removed it, so the row now reports its own residual instead of an offset. **Wave 7 measured the window offset properly and it is 28.7 of those 43.3 points, not the “about 17” this document used to state.** The old figure discounted the **rate channel only** — `359.02 × 0.844354 + 102.45 = 405.6`, which `scripts/window_offset_capgains.py` reproduces to the dollar — and missed two things: the death channel grows with the same 5.80% net-worth CAGR, and it does **not** grow proportionally. A uniform discount gives $86.5B where a re-score on FY2022–2031 gives **$65.8B**, because a fixed nominal per-donor exclusion is a step function whose bite moves faster than the stock it is subtracted from — the window offset and the ladder finding are the same defect seen twice. **The measurement is a re-score rather than a discount, and it needs no 2021 baseline**, because `CapitalGainsPolicy.estimate_static_revenue_effect` opens with `_ = baseline_revenue`: what this row needed was a **window**, not a **vintage**. PR #126 shipped it under the manifest's own supersede rule — `.v1` superseded, `.v2` registered on `scoring_window_first_year=2022` with the target unchanged at −$322.0B, entry commit before scoring commit, the `iija_2021_discretionary.v2` precedent exactly. The control is `biden_capital_gains_39`: same shape, same module, same frozen elasticities, an FY2025 target on the FY2025 window, and an offset of **exactly zero to the cent**. The row now reads **18.4%** on merged main — not the memo's 14.6%, because PR #132 landed in the same wave and raised this row's death channel from $102.45B to $109.24B. **And 18.4% is not accuracy either**: it is a net of Treasury booking $66.0B across FY2022–24 where the model books $6.1B (the model's enactment year is a $59.8B transitory revenue *loss* against Treasury's $7.7B gain) against $106.4B of over-prediction across FY2025–2031. What the window change removed is an accounting artefact; what is left is a shape disagreement, which is the point of making the change. **The same mechanism would take `iija_2021_discretionary` 18.2% → 0.3%** — $92.6B of its authority path outlays before the FY2025 window opens — and the memo publishes that number precisely so the decision not to take it is a visible choice: it is a second Tier 1 target decision, needs its own `.v3` row, and belongs to the owner. `cbo_opt51_gains_at_death` moved 19.3% → **20.3%** in Wave 7 (its earlier 8.4% was Wave 4's own registered regression, bought by taxing charitable bequests and small decedents' housing gains that no such regime reaches). Two findings from Wave 5 belong here. First, the **qualified-dividends hypothesis is refuted**: SOI Table 3.5's preferential columns exceed the whole year's realized gains in both vendored years (1.046 and 1.189), so they already contain qualified dividends, and adding a column would have double-counted $313-336B of base — the check ships as `soi_preferential_base_coverage.csv`. Second, inverting Option 47's published annuals for the semi-log coefficient gives 4.17 falling to 1.81 on a *flat* base — a path no scorekeeper's method produces, because it is the projection error being absorbed by the elasticity — against **3.17 / 3.01 / 3.12** on the projected base, either side of JCT's own published working coefficient of 3.1 (CRS R48562 p. 8) and the frozen Dowd–McClelland–Muthitacharoen 3.2727. **The five-class decedent ladder is gone, and replacing it proved that Wave 4 had named the wrong cause.** PR #132 fitted a piecewise-Pareto size distribution of net worth at death to the Distributional Financial Accounts' own percentile-group aggregates — every group's published aggregate reproduced to 1e-9, the level untouched at Poterba & Weisbenner's flow, only the shape changed — and read all three published carve-out ladders at each estate's own size instead of at five class means. **Seven of eighteen published rows had never been evaluated by any scored case**, including the whole \$1M–\$5M band of Poterba & Weisbenner's Table 8, which is where both Green Book per-donor exclusions sit; six are now alive. The three affected rows got worse inside their pre-registered bands (**20.3%**, **32.8%**, and 45.4% for the Treasury row before the window change). **But the \$1M → \$5M step went 82.26 → 85.02 — the wrong way, and the direction is not an accident**: `max(0, gain − E)` is convex in the gain, so a mean-preserving spread *raises* the taxable excess at every exclusion level. A sharper schedule makes an exclusion cost more, not less. Wave 4 read a cliff in the schedule and inferred the cliff was the cost; the cliff was real and the cost is elsewhere. **What moves it is the decedent headcount.** `estate_flow_rate` is Poterba & Weisbenner's **dollar** flow of estates over net worth (0.3195%/yr) used as a **headcount** rate, giving 408,532 decedents a year against roughly 3.09 million NCHS deaths — and holding gains at death fixed while varying only the count, a figure about **twice** the shipped one reproduces Treasury's own step to within two billion. `accrued_gains_parameters.csv` already carries an independently derived `mortality_weighted_net_worth_share` of **2.65%** (NCHS mortality against DFA net worth by age) that this channel does not read. The lane deliberately did not touch it: it is a level change to the whole channel and moves Option 51 in the wrong direction, so it is an owner decision about `estate_flow_rate`. **Two further findings belong with whoever takes it.** The headcount is short by **1.6× at the top** (4,378 implied decedents above \$12.92M of net worth against SOI's 7,194 estate-tax returns above the same threshold) where it is short by 7.6× overall, so a fix that scaled every group equally would overshoot the top while correcting the middle. And **\$33.4B was never the right comparator**: Treasury's two published rows sit on different windows on different baselines, and the model's own death channel is 0.714× as large on FY2022–2031 as on FY2025–2034 for the \$1M design, so any common-window restatement makes Treasury's own step larger. The fit also **refuses below the top decile and says so twice** — the index comes back below one, and the implied median net worth of \$389,500 is 2.02× the SCF's published \$192,700 — so the two groups there keep their old group means, and Poterba & Weisbenner's \$250,000–\$500,000 class is still never evaluated. All four rows are scored with ONE frozen elasticity set — the `CapitalGainsPolicy` dataclass defaults, persistent 0.72 / transitory 1.20 at a 22% reference rate, semi-logarithmic because CRS R48562 defines the elasticity on the tax rate — and `scenarios.py`'s per-case tuples no longer exist. **Wave C (PR #151) then took the decedent headcount the paragraph above hands off, and two of the three claims in that hand-off did not survive it.** The count is now `death_exit_rate()`'s own 2.647%/yr — **3,384,194** decedents against 408,532, the level untouched — and a fixed per-donor exclusion therefore bites 8.3× harder: `cbo_opt51_gains_at_death` **20.3% → 35.5%** (the registered regression this hand-off predicted), `biden_capital_gains_39` **32.8% → 27.0%**, the Treasury row **18.4% → 1.8%**, `cbo_opt47` unmoved to the cent, and the class **20.5% → 18.7%** on a mass of 74.8. What did **not** survive: *"about twice the shipped count reproduces Treasury's step"* — 8.3× the count takes the $1M → $5M step to **$9.40B** against Treasury's $33.4B, through the figure and out the other side; and *"start at the top, because the shortfall is 1.6× there and 7.6× overall"* — grading the rate by estate size runs the **wrong way**, since the wealthy are older and so die at a *higher* rate (size-graded at the top **2.8400%** against the uniform **2.6468%**), taking the implied count above $12.92M to 38,908 where the uniform swap takes it to 36,262, both further from SOI's 7,194. The SOI figure also needs a unit before it is a check: SOI counts *individual* decedents over a *gross-estate* threshold and the model counts *households* over net worth, so a model count above SOI's is the expected sign. **And the headcount was only half of the ratio.** `gains_at_death_share_of_net_worth` is the same Poterba & Weisbenner dollar flow, which against `death_exit_rate` implies **0.372% of the accrued-gains stock** where the stock's death exit is priced at **2.647%** — a factor of **7.1**, unmeasured, and pointing the other way, since `cbo_opt51` under-predicts. Read the Treasury row's **1.8%** in that light and not as accuracy.
4. **Budget-authority-to-outlay lag and the level shape (8 cases, 0-12.2%; mass 45.5, 12.7%).** **This was 509 units and 38.7% of the tier before Wave 1, and it was the plan's rank-2 lane for that reason.** L2 built the spend-out model — `outlays_t = Σ_k s_k · BA_{t−k}`, with `s` fitted by NNLS on the 14 CBO donor options the battery does not score — and PR #88 gave IIJA the authorization schedule CBO's own estimate states. The five CBO Options spending rows now land at 0-11% (Option 43, the slowest spend-out in the battery, went 75% → 11%), the three enacted-law components at 0.3-12%. What is left is *not* spend-out: Option 39 under-predicts (8%) because Pell disburses in two years while the generic grants profile takes six, Option 43's residual is a first-year authority level inflated by IIJA advance funding, FRA's is the level shape, and SSFA's is a growth rate. **IIJA's window mismatch is closed**: Wave 7 measured it exactly and left the decision open, and owner decision ③ took it — `iija_2021_discretionary.v3` scores the bill on FY2022–2031, the decade its own estimate covers, at **+$414.3B against +$415.4B, 0.3%**, where `.v2` read 18.2% because $92.6B of its authority path outlays before the FY2025 window opens. The target never moved and `.v2` is kept; the mechanism is `CBOScore.scoring_window_first_year`, which PR #126 built for the FY2022 Green Book row. Read the 0.3% with its own note attached: two terms nearly cancel under it (a 4.3% over-statement of the total against $18.9B of FY2032+ tail the window still clips), so it is not evidence about the spend-out profile. Account-level rates would close the first of those, and CBO publishes them (publications 61913 and 62256) — from an environment that can reach cbo.gov.
5. ~~**The AGI-inclusive surtax base: measured on taxable income where the source says AGI, and held at a tax year across a decade.**~~ **CLOSED by Waves A/B (PRs #144 and #146), both halves, and the two rows it named are now the tier's *best*-scoring pair at **7.4%** and **-2.9%**.** The three steps the W7 lane measured and declined to take were the filing-status split (built in PR #127, and it made both rows worse), a base grown on the scored vintage's own nominal-GDP path (PR #144) and SOI's **AGI column** in place of its taxable-income column (PR #146). All three are now built. **Two things about the arithmetic are worth keeping.** First, the W7 lane sized the AGI step with *pooled* marginal ratios — 1.3820 at $20,000 and 1.3094 at $100,000 — where inside the filing-status split the same quantities are **1.4052 and 1.2535**, one higher and one lower, because the joint floor is twice the single floor and joint returns are a different share of the two populations; composing the pooled ratios would have missed both rows in opposite directions. *A ratio measured on a pooled base is not the ratio that applies to a split one.* Second, the worry that the change would move five rows for one reason was right and was answered **per source**: `agi_inclusive_base` is set on six records and only three of them say AGI, two say **taxable income** in as many words, and `medicare_surcharge_2pp`'s statutory base — wages plus net investment income — is **neither SOI column**. What is left on the AGI-inclusive class is therefore **target provenance and one base definition**, not a missing mechanism: of its remaining 105.4 points of mass, **70.3 sit on those three held rows**, and the two rows with a published option and a transcribed base read 7.4% and 2.9%.
6. **A tax-expenditure cap missing part of its base and carrying a behavioural offset sourced in direction but not in magnitude (1 case, 13.1%; mass 13.1, 3.4%).** Entered in Wave 3 at 24.0% with a *shape* residual; Wave 4's PR #105 gave the excess share CBO's own chained-CPI indexation and the row fell to **13.1%**. What is left is half a base omission — CBO caps premiums **and** FSA/HRA/HSA contributions and the repository's premium distribution has no account dimension — and about a fifth a behavioural offset whose sign convention is the reverse of `TaxPolicy`'s. Both are named in the row's `known_limitations` and neither is tuned. **PR #128 settled the second half, and it did not settle it module-wide, because the documents do not.** “One direction” was the defect rather than “which direction”: CBO's own Option 49 puts four alternatives over the same deductions in one table and gives them **three different behavioural directions**, and CBO's charitable option reverses its own verdict for a *floor* design, where a taxpayer can bunch gifts to clear the floor and a rate ceiling offers no such move. So `TaxExpenditurePolicy` now carries a per-**reform** `direction`, with `erode` the default and `magnify` only where a source says the response **raises** revenue: **magnify** for Option 56 (“revenues would also increase because fewer workers would enroll in employment-based coverage”, report pp. 66–67), the 28% charitable benefit-rate ceiling, SALT elimination (CBO 58635 alternative 2, this exact reform) and SALT-cap repeal (its mirror, priced by Yale Budget Lab at $323B → $497B as new itemisers claim mortgage interest); **erode** for the mortgage deduction (Poterba & Sinai's own $72.4B without behaviour against $61.9B with, “about 85 percent”), step-up elimination, the retirement-contribution cap and like-kind exchanges. **Four reforms magnify on a document and five erode**, and Option 56 keeps the direction it had. `CONVENTION_EXCEPTIONS` is now a set of *policies* rather than class names — the whole of `TaxExpenditurePolicy` had been exempt, so the sign contract said nothing about any reform it could express — and a new test fails if any class ever has all its cases exempted again. **The magnitude is still unsourced**, here and on all five entries in `BEHAVIORAL_ELASTICITIES`, and two of them now have a published number beside them to be compared against: Poterba & Sinai's **15%** against mortgage's 0.10, and charitable's 0.40, which has the size of a *price elasticity of giving* applied to a share of a revenue effect — a different quantity. Adopting either would be fitting to a paper the lane read for its direction, so neither was taken. **Item 8 is closed on direction and open on magnitude, and the two halves are recorded separately.**

*(A seventh cause, "a single ETI at a large rate change against a secondhand target", left the battery with `top_rate_45` in Phase E.)*

**Honest reading**: the model predicts ordinary and AGI-inclusive *rate* changes at conventional thresholds well (1.5-22.4%), discretionary funding changes well now that authority is spent out (CBO Options rows 0-11%, enacted-law components 10-18%), a **new broad payroll tax** well now that its base is earnings rather than a receipts total divided by the wrong rate (7.5-8.1%), a **preferential-rate change** well now that its realizations base is projected rather than frozen at a tax year (10.5%), and an employer-health cap well now that its excess share is indexed (13.1%). What it still predicts badly is **corporate margins (44.5%)**, the **FY2025 Green Book capital-gains row (32.8%)** and the **Medicare surcharge (31.8%)** — the AGI-inclusive surtax base, the largest cause on this list since Wave 7, was closed by Waves A/B and its two rows now read 7.4% and -2.9% — and each has a documented cause, all four now measured rather than named: an AGI-inclusive base scored on taxable income and frozen at a tax year, worth 20 and 36 points respectively on the two Option 46 rows; a marginal corporate base that is 80.8% of the vintage's own average base where three of the four published estimators read 55-64%, with credit carryforwards and CAMT the unbuilt channels; and, at death, a decedent **headcount** derived from a dollar flow rather than a mortality rate, where doubling the count reproduces Treasury's own exclusion step to within two billion. Phase A's 9-case 44.8% and Phase B's 23-case 43.4% were the same story on more than twice the evidence: widening the battery did not move the mean, it explained it. Phase D then added the one shape that moved it — IIJA's 356% — taking the 25-case mean to 52.6% while the median *fell* to 21.1%. Wave 1 built the mechanism that 356% was evidence for, and the mean fell to 34.4% with the median at 16.1% and within-15 rising 8 → 12. Wave 2 did the same for capital gains and it fell again, to 31.3% / 14.1% / 13 within 15 / 18 within 25. Wave 3 added a case rather than moving one: Option 56 entered at 24.0% and the tier read 31.0% / 15.1% / 13 / 19. Wave 4 did what Wave 2 had left half-done — the death channel's carve-outs and behaviour, Option 56's indexation, and one target moved onto its document — and the tier read 18.0% / 12.6% / 14 / 21. Wave 5 worked three margins and the tier read **15.9%** / **11.4%** / **16 within 15** / **22 within 25** — reached *through* two pre-registered regressions rather than around them, which is the part worth quoting: the payroll correction alone was worth more than the corporate and Green Book regressions cost. PR #121 then took back most of the corporate regression on a second reading of the same row, and the tier read **15.2%** / **11.4%** / **16** / **22** — the first movement in this tier produced by *one* row and nothing else. Waves A and B then took it to **14.7%** / **12.6%** / **15** / **23** — through a lane that *raised* the mean to 15.6% and reported it rather than tuning, and a follow-on that took it below where the first found it. Before them, Wave 7 made **six of its seven moved rows worse** and the tier still fell, to **15.0%** / **10.6%** / **17** / **22**: the filing-status split cost 18.1 points and bought a diagnosis worth 36 more, the decedent distribution cost 2.4 and disproved the hypothesis it was built to test, and scoring the FY2022 row on its own decade returned 24.9. **The mean is the least interesting thing that happened to this tier in Wave 7.** It is what it always claimed to be underneath: a tight rate-and-spending core and a behavioural tail — and every row in the tail is now an argument with a quantity somebody has measured, rather than with a mechanism nobody had built.

**What the tight core shows.** Ordinary-bracket rate changes (JCT 1pp, Biden $400K, CBO Option 45) score on the ordinary-income base (excludes preferential LTCG/QDIV); AGI-inclusive surtaxes (TPC $1M+/$500K+, Warren, the Medicare surcharge, CBO Option 46) score on the full taxable-income base that includes the preferential portion. The classification comes from how each source describes its base, not from which choice fits better — the `cold_holdout.py --ordinary-base` diagnostic shows the correction *worsens* the AGI-inclusive cases (7→30%, 9→30%, 2→29%), which is the tell. For ordinary and AGI-inclusive rate changes in this range, **treat uncalibrated custom policies as directional, ±15-25%.**

**The three cases Phase A flagged, resolved in Phase E by reading the documents.** Phase A's guess was that one of the targets was wrong. The answer was worse than that.

- **Top rate to 45% — retired.** The target could not be sourced at all. TPC's full sitemap was enumerated (11 sub-sitemaps, ~20,600 URLs, ~6,500 model-estimate pages) and contains no table for a 45% ordinary rate at any date: the only "45 percent" pages are the estate-tax top rate and an EITC phase-in rate, none of TPC's 82 `t23-*` tables is a top-rate table, and its top-rate collections are all pre-2010 vintage. CBO and JCT publish no +8pp top-bracket option either, and CBO explicitly warns that "the deficit effects of large rate increases or surtaxes might not be proportional to the estimates shown here." PWBM (May 2025) brackets the plausible range at **$401.6B** for reverting the top bracket to 39.6% and **$222.4B** for a new 39.6% bracket above $1M — which makes -$420B for +8pp above $609,350 implausibly *low*, the opposite direction from the model's -$916B. There is no figure to correct it to, so the case is withdrawn from the battery (`retired=True`, with the search recorded) rather than scored against a number nobody published. The unsourced -$420B is also gone from `CBO_SCORE_MAP`, so the app no longer quotes it.
- **Biden capital gains — re-sourced, and the error went up.** -$456B appears in no Treasury volume. The FY2025 Green Book scores "Reform the taxation of capital income" as a **single combined row of $288,583M** (report p. 242; PDF p. 250) and never splits the rate change from the realization-at-death change, so there is no decomposition -$456B could have been assembled from. The manifest row is superseded (`.v1` → `.v2`), and the *shape* moved to the source's own definition rather than the number being fitted: **taxable** income over $1M (the FY2022 volume says AGI) and a **$5M per-donor** exclusion for gains at death, portable to $10M per couple (report p. 89), where the module default and the FY2022 proposal are $1M per person. The larger exclusion cuts the modelled gains-at-death revenue, so the prediction moves from -$817B to -$699B against a target that also fell — and the error goes **79% → 142%**. That is the correct outcome of a sourcing pass: a better target and a more faithful shape, scored honestly.
- **Treasury 39.6% + step-up repeal (154%) — confirmed.** The FY2022 Green Book row is **$322,485M** (report p. 105; PDF p. 111), 0.15% from the carried -$322B, and the FY2022 narrative (report p. 62) confirms every element of the shape including the +19.6pp incremental rate (footnote 1: "a separate proposal would first increase the top ordinary individual income tax rate to 39.6 percent (43.4 percent including the net investment income tax)"). So the 42% gap Phase A found between this and `biden_capital_gains_39` was **not** two published estimates disagreeing: one was published and one was not. Across four consecutive Green Books the same combined row reads $322,485M (FY2022) → $174,488M (FY2023) → $213,855M (FY2024) → $288,583M (FY2025), which is genuine cross-vintage movement on a design that itself changed (AGI → taxable income; $1M → $5M exclusion).

Two further out-of-sample targets did not survive the same sweep and were left as **open owner decisions**, because the plan that authorised Phase E named only `top_rate_45`. **`planning/ROUTE_TO_8_5.md` §1 R2 is the plan that names them, and lane R2 took both decisions on 2026-09-11.** Both are retired, and so are two more found the same way:

- **5pp top rate ($1M+), -$700B — RETIRED.** No TPC table states it; the record called itself "illustrative". R2 added the half of the search Phase E had not run and found no CBO or JCT option either: the individual-rate option of all four *Options* volumes (2018 pub. 54667 #1, 2020 pub. 56783 #1, 2022 pub. 58164 #13, 2024 pub. 60557 #45) prices uniform changes at bracket boundaries and AGI surtaxes at statutory floors, and nothing at $1,000,000. PWBM's new 39.6% bracket above $1M — a smaller change on the same threshold — is $222.4B over FY2026-2035.
- **Warren surtax 3pp (AGI >$2M), -$350B — RETIRED.** TPC's *AGI Surtax Options* simulation is thirteen tables and **all thirteen are 10 percent**; its only revenue table, T19-0037 (23 September 2019), prices 10pp on AGI over $2M at **$585.325B** over FY2019-2029, $2.5M at $500.635B and $2M married / $1M other at $633.897B. Scaling to 3pp would be *constructing* a target rather than reading one, and CBO's own warning that large surtaxes are not proportional says the scaling would be wrong as well as inadmissible. **The row's name is also wrong**: Warren's Ultra-Millionaire Tax Act is a *wealth* tax on net worth (2% above $50M, 3% above $1B), so its shape matches no proposal anybody scored. T19-0037 does confirm the record's `agi_inclusive_base=True` flag, and Option 1 is the same base at the same threshold on a rate somebody priced — a registrable new case, and an owner's, because it moves a model output.
- **2pp rate cut ($500K+), +$400B — RETIRED.** No publication prices it, and three quarters of the search space cannot contain it by construction: CBO's *Options* volumes are deficit-**reduction** menus and carry no rate cut in any edition. This was the battery's only rate cut and its only positive target.
- **Medicare surcharge 2pp (>$400K), -$310B — RETIRED.** See the lane paragraph above: Treasury's proposal is **1.2pp** and prints **$403,790M**, the FY2024 volume prints $344,371M, and -$310.0B is neither. The model's 2pp score sits 1.2% from the 1.2pp figure, so this is the row that proves R2's rule rather than the row that bends it.

**And one Tier 1 target now has a transcribed row that disagrees with it.** Biden's top-rate proposal is published at **$245,924M** (FY2025 Green Book, report p. 242), against the carried -$252B — 2.5% apart. Pre-registered targets are frozen, so correcting it requires a new manifest row superseding `biden_high_income_tax.v1`; that is an owner decision and the gap is recorded on the scorecard entry meanwhile.

### Pre-registration

Every Tier 1 case is registered in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py) with the official target, the publishing source and date, the budget baseline *that source* was scored against, the commit and date at which the record entered the repository, and the commit of the first scoring run.

The discipline the manifest enforces (`assert_preregistered`, tested in `tests/test_preregistration.py`):

0. **The target is entered in a commit before the commit that first scores it.** Phase B's 14 CBO Options rows were entered in `752f0f1` (`PHASE_B_ENTERED_COMMIT`) and first scored in `36d683f` (`PHASE_B_FIRST_SCORED_COMMIT`), which is the commit that flips them to `runnable=True`. Phase D's three enacted-law rows were entered in `aed5318` (`PHASE_D_ENTERED_COMMIT`) and first scored in `dca3a50` (`PHASE_D_FIRST_SCORED_COMMIT`). A file cannot contain its own hash, so both are stamped in the immediately following commit — the same convention Phase A used.
1. **A target may never be edited to match a model run.** If an official number genuinely changes, the old row is marked `superseded_by` and a **new row with a new `case_id`** is added. The history stays in the file and in the diff.
1a. **A *shape input* moves by the same rule, and the window is one.** `CBOScore.scoring_window_first_year` (PR #126) lets a case be scored on the ten fiscal years its own source published a total over, and setting it is a supersede, not an edit: ledger entry in one commit, first scoring in the next, `.v1` kept with `superseded_by`, target unchanged. **Two rows carry a `.v2` on this rule** — `iija_2021_discretionary.v2`, whose shape input moved to CBO's own authorization schedule, and `treasury_capgains_39_plus_stepup_elim.v2`, scored on **FY2022–2031** because that is what Treasury's FY2022 Green Book row covers. Two design details are pinned by tests: the field moves the **scorer's window and the policy's start together** (moving only the window truncates the head — Warren would read −$170.1B, exactly 6/10 of itself), and `effective_start_year` keeps precedence where a record sets one. **What these rows needed is a window, not a vintage**: `CapitalGainsPolicy.estimate_static_revenue_effect` opens with `_ = baseline_revenue` and neither FY2022 row reads a baseline *level*, so the "the repository has no 2021 vintage" line that both rows' notes used to carry names a blocker that was never the binding one.
2. **No case may be scored out-of-sample without a row.** A Generic scorecard entry with no manifest row fails the test.
3. **Misses are kept.** A row is never removed because the model scores it badly.

Honest boundary, as with [`holdout.py`](../fiscal_model/validation/holdout.py): these are previously published numbers, and Phase A registered targets that already existed in the repository or in `CBO_SCORE_MAP`. What the manifest guarantees is that *from the entry commit onward* the target is frozen and any change is visible — not that nobody had ever seen the number.

**CI gate.** `.github/workflows/validation-dashboard.yml` runs `python scripts/cold_holdout.py --max-mean-error 15 --min-within-25pct 19` as a blocking step. The workflow's own rule sets both: ceiling = ceil(mean x 1.25) to the nearest 5; floor = current count within 25%, minus one. On the post-Wave-B battery (26 cases, mean **14.7%**, **23** within 25%) the rule gives a ceiling of **20** (`ceil(14.7 x 1.25) = 19`, rounded up to the nearest 5 is 20 — the same ceiling Wave 5's 15.9%, Wave 6's 15.2% and Wave 7's 15.0% gave) and a floor of **22** (`23 - 1`), so the floor tightens 21 -> 22 and the ceiling re-derives to itself. PR #126's memo had stated a floor of 22 on its own branch a wave early, where within-25 read 23 and the merged tree read 22; it now holds on the merged tree for a different reason, which is that PR #146 brought `cbo_opt46_agi_surtax_2pp_100k` inside the band. **Live values, re-derived after Wave F and unchanged.** The battery is 22 cases at mean **11.8%** with **19** within 25%, so the ceiling derives to `ceil(11.8 x 1.25) = 15`, which rounds to **15** and re-derives to itself, and the floor derives to `19 - 1 = 18` — which would **loosen** a gate the battery meets with no slack, so it **stays at 19** under the rule's downward-only clause. The workflow has run **15 / 19** since lane R2 (PR #162), and **20 / 21** from Wave 5 (PR #117) before that, from the **25 / 20** Wave 4 derived (PR #110), the **40 / 18** Wave 3 derived, **40 / 17** from Wave 2, **45 / 15** from Wave 1 and **55 / 13** before that. **Read `20 / 22 -> 15 / 19` as a battery that shrank, not a gate that relaxed**: both numbers fell because R2 withdrew four rows whose targets are in no publication, three of them from inside 25%, while the *share* within 25% rose 84.6% -> 86.4% — and only the share is comparable across a battery that changes size. A modelling lane never touches the yardstick, so the coordinator re-derives it in a separate PR once the docs are synced.

**Per-class floor.** Waves A/B added a second blocking step, `python scripts/cold_holdout.py --max-class-mean-error ...`, because **the pooled gate cannot see one class regressing while the others carry the mean** — which is exactly what happened to `medicare_surcharge_2pp` in Wave 7 (1.5% -> 31.8% while the tier fell) and to `warren_ultramillionaire_surtax_3pp` in Wave B. Each of the eight classes above carries its own ceiling at `ceil(class mean x 1.25)` — the pooled rule without its round-up-to-5, which exists to give a pooled mean headroom for one new hard case and is not what a class of one or two rows needs. Live after lane R2 and re-derived unchanged after Wave F: AGI-inclusive surtax **7**, ordinary rate change **15**, capital gains **24**, corporate **56**, enacted-law spending **10**, discretionary spending **6**, payroll **10**, tax expenditure **16**. **`ordinary_rate_change` is now tighter than its own re-derivation for the second wave running** — its class mean is 13.85%, so the rule would allow `ceil(13.85 x 1.25) = 18`, and the downward-only clause forbids taking it; 15 still passes. **Two of the eight moved because a class shrank rather than because it improved** — R2 withdrew three AGI-inclusive rows whose targets were in no publication, leaving the class at n=2 and a ceiling of 7, which is a thin thing to gate and is R3's to refill. Classes are **derived from each case's own `CBOScore` record** — `policy_type`, plus `agi_inclusive_base` for the income-tax split and `cbo_options.runnable_score_ids()` for the spending split — never from a hand-maintained list of policy ids, so a row registered tomorrow is classified the moment it is registered. **The gate fails three ways and the last two matter as much as the first**: a class over its ceiling, a class the battery contains that was given *no* ceiling, and a ceiling naming a class that does not exist. A gate that silently ignored an unlisted class would let a row in a ninth class sail past it, which is the failure mode PR #119's coverage-grep test exists to prevent.

### Tier 2 — Calibrated reference models (reconstructions, not confirmations)

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce the published decomposition**. Phase E added five more module families — international, trade, pharma, IRS enforcement, climate — and those turned out to be a different animal, so the tier now splits in two.

| Metric | Calibrated reference (fitted) | Module reconstruction (not fitted) | Retired target (withdrawn) |
|--------|---:|---:|---:|
| Benchmarks | **15** | **38** | **2** |
| Mean absolute error | **1.6%** | **42.3%** | **397.2%** |
| Median absolute error | 0.0% | 30.1% | 397.2% |
| Within 15% of official | 15/15 | 11/38 | 0/2 |
| Within 25% of official | 15/15 | 15/38 | 0/2 |

**The reconstruction column reads 42.3% only alongside 60.0%, and that is not a
presentational nicety.** Owner decision ④ withdrew two targets (below); on the
**40 rows the tier would otherwise hold**, at the errors those two carried on the
day they were withdrawn, it reads **60.0%, median 33.3%, 11/40 within 15%**. The
18-point fall is a *composition* move produced by a withdrawal, not an
improvement in any model. `cold_holdout.py` and `run_validation_dashboard.py`
print both readings on adjacent lines
(`uncalibrated_reconstruction_retired_held_in_place`), so quoting the smaller one
alone requires skipping a line.

**These are merged-tree readings and they are not either lane's branch figure**,
because two passes landed in the same window and both move this tier's
*composition*: the retirement took reconstructions 39 → 37 on its own branch
(56.5% → 38.1%, held-in-place 39 @ 56.5%), and PR #157 separately reclassified
`cap_charitable` out of the fitted tier, taking fitted 16 → 15 and putting a row
back into the reconstruction count. Neither branch reading is wrong and neither
is the live one; take the live numbers from `run_validation_dashboard.py`.

**Wave C moved the right-hand column on *accuracy*, which is the opposite of the four moves above, and the constant-population reading says so.** The **same 39 rows** sit in the reconstruction tier before and after PR #150, so **55.46% → 56.7% is like-for-like**, and all of it is the `Trade` sub-population going **34.2% → 43.6%**. The lane registered that as worse in advance: the five tariff targets are *conventional* estimates and the module had been netting **retaliation** inside a score measured against them — a category error the repository's own knowledge file already described correctly, while all five scenarios and all five presets ran with `include_retaliation=True`. Four of the five rows improve; `steel_tariff_25` (11.89% → **75.28%**) carries the whole of the net against a target that is untraceable and has been examined-and-left twice, and **on the four trade rows that have a document the sub-population improves 39.72% → 35.66%**. The left-hand column, its held-in-place reading and leave-one-out are **byte-identical across Wave C** — no target moved and no constant was retuned — which each of the wave's four lanes registered in advance as its own falsification test.

**Both columns moved again in H9, and for the fourth time the movement is composition rather than improvement — read the constant-population readings, not the headline.** H9 revised five fitted rows out (`ss_donut_250k`, `tcja_rates_only`, `eliminate_estate_tax`, `repeal_ira_credits`, `eliminate_mortgage`), so the fitted tier went **21 @ 1.73% → 16 @ 1.51%** *because the five that left averaged 2.42%, above the tier's own mean*, and the reconstruction tier went **34 @ 57.88% → 39 @ 55.46%** *because the five arrivals average 36.42%*. **On the same 34 rows the reconstruction tier gets worse, 57.88% → 58.26%**, and the whole 0.38pp of that is `trump_china_60`. The reading that is not composition at all: **the 21 rows the fitted tier held before H9, scored on the targets it leaves behind, read 9.82%** rather than 1.73%. The pre-H9 constant-population readings still stand behind these: the fitted tier is **23 at 7.7%, 21/23 within 15%** with the offset-sign sweep's two reclassified rows held in place, and the reconstruction tier is **57.4% over the 33 rows it held before PR #122** and **56.6% over the 31 it held before PR #119** — the older Wave 4 readings are **28 at 3.0%, 27/28 within 15%** with Wave 4's five revised rows held in place, and the reconstruction tier is **65.7% mean / 40.5% median over the 26 rows it already held** — *worse* than the 61.8% / 38.0% it read before Wave 4, because the pharma rebuild took two rows further from their targets.

The right-hand column grew from 12 to 20 in Phase D, and its mean fell from
394.1% to 250.8% — not because anything improved, but because the eight
P.L. 119-21 line items below are a *tighter* class of unfitted reconstruction
(35.8% mean) than the sectoral modules they were averaged with. Wave 1's L7
lane then took it from 250.8% to 82.6%, and that fall *is* a modelling
improvement: two federal-incidence bugs in `pharma.py` were re-specified from
transcribed MedPAC/ASPE/RAND figures, moving the 12-row sectoral subset from
394.1% to 113.8%. It then reached 21 rows at 76.7% on two *target*
corrections (below): the insulin target stopped pointing the wrong way, taking
that row from 146.4% to 39.0%, and `extend_tcja_amt` arrived from the left-hand
column. Wave 2 then took it to **24 rows at 72.1%**, and that is composition
again, not modelling: L1 deleted the three per-case capital-gains elasticity
tuples, which were the only constants ever fitted to `cbo_2pp_all_brackets`,
`pwbm_39_with_stepup` and `pwbm_39_no_stepup`, so those three rows arrived from
the left-hand column at **39.6%** — better than the tier they joined, which is
why the pooled mean fell. Wave 3 took it to **26 rows at 61.8%**, and that is
*both* things at once, which is exactly why the populations are reported
separately: L8 netted the tariff scores and L9 gave FDII repeal an identity, two
genuine modelling changes pulling in opposite directions, **while** two rows
arrived from the left-hand column at 37.1% and 44.3%. Held to the 24 rows the
tier carried before L8 the mean is 63.6%, not 61.8%. Wave 4 took it to **31 rows
at 56.6%**, and this is the sharpest instance of composition yet: the mean fell
9.2pp while the model got **worse**. Five rows arrived from the left-hand column
at an average of **9.4%** — `repeal_salt_cap` 1.2%, `ira_enforcement` 4.7%,
`extend_enhanced_ptc` 9.3%, `biden_eitc_childless` 9.5%, `eliminate_salt`
22.3% — pulling the pooled figure down, while PR #109's pharma rebuild pushed
two existing rows out (`expand_drug_negotiation` 25.7% → **93.3%**,
`international_reference_pricing` 646.2% → **701.0%**). Held to the 26 rows the
tier already carried the mean is **65.7% / 40.5% median**, against 61.8% / 38.0%
before. The populations are described separately throughout, because the pooled
number moves on composition as readily as on modelling — and here it moved in
the opposite direction to the modelling.

**PR #119 took it to 33 rows at 54.4% and PR #122 to 34 at 57.6%, a fall and a
rise that are both composition again.** The sweep moved `trump_corporate_15`
(then 22.3%) and `repeal_ptc` (18.5%) in from the left-hand column, both better
than this tier's average and worse than the fitted tier's, so the pooled mean
fell while nothing moved. The provenance pass then superseded
`trump_corporate_15`'s target from the model's own +$1,920B to the published
[+$595.0B, +$673.1B] range and the row went to **121.6%**, and registered
`biden_corporate_28_fy2022` at **62.9%**. Held to the 33 rows the tier carried
before that, the mean is **57.4%**; held to the 31 it carried before the sweep,
**56.6%** — exactly what it read after Wave 5. **The rise is the honest
direction**: this is the column a row goes to when nothing is fitted to it, and a
row that stops being scored against the model's own output should be expected to
look worse rather than better.

**Wave 7 then took it to 57.9% on the same 34 rows, and that one is not
composition.** PR #131 replaced `repeal_ptc`'s fitted $83.0B/yr with CBO and
JCT publication 51298 Table 2's own annual credit path net of publication
60437's published 19.28% offsetting share, and the row went **18.5% → 29.6%** —
registered as a regression before the code was opened, with within-25 falling
13 → 12. Because no row entered or left, the 0.33pp is one row and can be read
as one. **It is also the first entry in this column whose target the repository
can now show, rather than argue, is the wrong kind of quantity**: the same
mechanism on the June 2024 vintage and window with no offset returns $1,143.0B
against the $1,142B PR #122 traced to publication 51298 — 0.09%.

The 1.7% on the left is **expected by construction** — those modules carry a constant fitted to each benchmark, so they demonstrate the model's structure and provide auditable, source-linked reconstructions of official scores; they are **not** evidence the model would have predicted them cold. (Earlier revisions of this file quoted 4.4%, then 2.7% over 34, then 2.8% over 33, then 2.2% over 30; the live figures come from `python scripts/cold_holdout.py`, which is the only place they should be read from.)

**The left-hand column has lost thirteen rows, and the losses must be quoted with
it.** Three of them left in Wave 2: `fiscal_model/validation/scenarios.py`'s per-case
behavioural tuples *were* the fit on the three capital-gains benchmarks, so
deleting them made `calibrated_to_target=False` simply true and the runner now
says so. Left in the fitted tier they would have raised its mean to **6.2%**
while nothing had regressed — which is the misreading the flag exists to
prevent. Moved, the fitted mean *fell* 2.8% → **2.2%**, because those rows
were what the tier had been carrying: the worst fitted row used to be
`cbo_2pp_all_brackets` at 19.2% and is now `tcja_no_salt_cap` at **13.9%**.

**Two more left in Wave 3, and they are the cleanest instance of the pattern.**
`trump_universal_10` and `trump_china_60` were reading 1.1% and 6.2% because
`universal_coverage_rate = 0.70` and `china_effective_coverage = 0.50` were
fitted to those two benchmarks and the Trade runner said so on the entry. Lane
L8 re-derived the first from Census import values by partner (**0.7197**, the
non-USMCA share) and **deleted** the second for the incremental-rate identity a
60% China tariff actually implies, so no `TRADE_BASELINE` constant is fitted to
any target. Both rows moved to the reconstruction tier and now read **37.1%**
and **44.3%** on a base that is measured rather than solved for. Removing two
rows that scored 1.1% and 6.2% against a 2.2% mean *lowers* it — one was above
the tier mean and one below — so the fitted tier reads **28 at 2.0%, 28/28
within 15%**. Read every one of these moves as composition, not as improvement.

**Six more left through the revision ledger, five of them in Wave 4.**
`ScorecardSummary.revised_target_entries` is **16**: sixteen calibrated targets have been
corrected through the Tier-2 revision ledger
([`fiscal_model/validation/target_revisions.py`](../fiscal_model/validation/target_revisions.py)),
and a constant fitted to a superseded figure is not fitted to its replacement —
so `scorecard.py` derives `calibrated_to_target` from the ledger and the revised
rows report on the right, where a miss is a finding rather than a regression.
Wave 4's provenance pass moved `biden_eitc_childless`, `eliminate_salt`,
`extend_enhanced_ptc`, `ira_enforcement` and `repeal_salt_cap` out that way,
mechanically; **retuning any of them to close the new gap would have been the
relaxation, and none was touched**.

**Two more left on a fourth mechanism, and it is not the ledger's.** PR #119's
offset-sign sweep reclassified `trump_corporate_15` and `repeal_ptc` to
`calibrated_to_target=False`. Both annuals had been fitted so that
*static × (1 + offset share)* landed on the target — corporate's `abs()`-ed offset
was adding 12.5% of a rate **cut**'s static effect to the deficit, PTC's inverted one
10% of a saving to the saving — so signing the offset took each score to
*static × (1 − offset share)*, a movement of twice the offset. **A constant that
reproduced its target only through a defect is not a calibration to that target**, on the
precedent `readiness.py` cites in its own comment and that Wave 2's L1 set for
`pwbm_39_with_stepup` and Wave 3's L8 for the two Trump tariff rows. Neither was retuned
and neither got a readiness exemption; both carry the finding in their
`known_limitations`, which is what readiness requires before a Poor row is a warning at
all. `calibrated_to_target` is threaded through the corporate and PTC runners with a
default of `True` and a test pins the two-row scope, so the default cannot quietly invert
and empty the tier. Both readings, and never one alone:

| Reading | n | Mean | Median | Within 15% | Off by >15% |
|---|--:|--:|--:|--:|---|
| **As reported** — revised and reclassified rows moved to the reconstruction tier | **21** | **1.7%** | 0.1% | **21/21** | none (worst is `tcja_no_salt_cap`, 13.9%) |
| **Held in place** — the sweep's two kept in the fitted tier | 23 | **7.7%** | 0.1% | 21/23 | `trump_corporate_15` (121.6%), `repeal_ptc` (18.5%) |
| **Held in place** — Wave 4's five also kept in | 28 | **8.0%** | 0.4% | 25/28 | the two above, plus `eliminate_salt` (22.3%) |
| **Held in place, plus the revised TCJA-AMT row** — the n=29 reading earlier revisions quoted at 4.3% | 29 | **10.0%** | 0.4% | 25/29 | the three above, plus `extend_tcja_amt` (66.8%) |

*The `Held in place` row reads **7.7%** where `planning/lanes/SWEEP_offset_sign.md` §7.2
records **3.4%**. Both are correct on the tree they were measured on: the sweep measured
before PR #122 superseded `trump_corporate_15`'s +$1,920B `model_estimate` target with the
published [+$595.0B, +$673.1B] range, which took that row 22.3% → 121.6%. The lane doc's
figure is not restated there; this table is the merged-main reading.*

Six of the fifteen revised rows change tier. `universal_insulin_cap`,
`pillar_two_adoption` and Wave 4's seven international/trade/climate revisions
were already unfitted, so their corrections land entirely inside the
reconstruction column.

#### The behavioural-offset sign contract, and the seven implementations that broke it

`fiscal_model/scoring_engine.py` books a score as
`static_deficit = static_spending − static_revenue`, then
`deficit_after_behavioral = static_deficit + behavioral`. The quantity handed to
`estimate_behavioral_offset` is the **static revenue** effect for that year, not
the deficit effect. So an offset carrying the **same sign as the static revenue
effect erodes** it — a tax increase raises less than its static figure because
the base shrinks, a tax cut loses less because the base grows — and an offset
carrying the **opposite sign magnifies** it, which is backwards in both
directions at once. `TaxPolicy.estimate_behavioral_offset` states this in its
docstring and implements it as `static × ETI × 0.5`, so the final effect is
`static × (1 − ETI·0.5)`.

PR #119 probed all fifteen implementations twice — at the **function**
(`f(+100)` and `f(−100)` on a representative instance, which is the sign rule the
class implements whether or not its own factories ever produce a negative static)
and at the **score** (an increase policy and a cut of equal size through
`FiscalPolicyScorer`, comparing `|final|` against `|static|`). **Seven were
against the contract:**

| Tag | Classes | What it does |
|---|---|---|
| `inverted` (3) | `AMTPolicy`, `EstateTaxPolicy`, `PremiumTaxCreditPolicy` | magnifies in **both** directions — AMT booked **25% more** than its own static either way |
| `abs` (4) | `CorporateTaxPolicy` [`reported`, the app default], `TaxCreditPolicy` [fallback branch], `IRSEnforcementPolicy`, `InternationalTaxPolicy` | erodes whichever direction happens to match and magnifies the other — corporate `reported` booked 12.5% more on a **cut**, international 15%, PTC 13% on a repeal |
| `convention` (1) | `TaxExpenditurePolicy` | opposite-signed **on purpose**, and left that way |

The three inverted modules carry the *identical* comment pair
`# Reduces revenue gain` / `# Reduces revenue loss` above a
`return -total_offset` — one copy-paste in three files, by an author who read
`behavioral` as a quantity the engine *subtracts*. It does not; line 166 adds it.
Six were fixed with `math.copysign` (and, in `credits_core.py`, by dropping an
`abs`); no elasticity value, base, growth rate or target changed.

**`TaxExpenditurePolicy` is deliberately unchanged, and it is now the only one.**
Its source is CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557),
Option 56: a cap on the employer-health exclusion makes employers offer less
generous coverage **and** shifts compensation back into taxable wages, and CBO's
text has both channels raising revenue, so an offset that adds to the static
effect is right *there*. Its size is measured: **+5.0% of the static effect on a
SALT elimination and +20% on Option 56**. Choosing it module-wide moves every
fitted expenditure row and the whole leave-one-out column together, so it is an
owner decision.

*Two claims in the paragraph above have since been superseded and are corrected
here rather than deleted, because the wording is what a later reader would have
trusted.* **(1)** `TaxExpenditurePolicy` is **no longer the single entry** in
`CONVENTION_EXCEPTIONS`: Wave 7's PR #128 replaced the module-wide convention with
a per-reform `direction`, and `CONVENTION_EXCEPTIONS` became a set of *policies*
rather than class names, with a test that fails if any class ever has all its
cases exempted again. **(2)** The magnitudes are **no longer unsourced on all
five**. Wave D's PR #157 sourced two of them one reform at a time: mortgage repeal
**0.10 → 0.14502762**, which is `1 − 61.9/72.4` from Poterba & Sinai, *Income Tax
Provisions Affecting Owner-Occupied Housing* (NBER WP 14253, §6.1 and Table 8 —
the paper's own "about 85 percent"); and the charitable benefit-rate ceiling
**0.40 → 0.22077987**, the module's own identity evaluated at `c = 0.28` on the
existing SOI Table 2.1 distribution, with the only new constant being a central
price elasticity of **ε = 0.5 from CRS R40518** (band 0.1 / 0.5 / 0.79). **Three
remain unsourced with their searches recorded** — employer health 0.20, retirement
0.30 and SALT 0.05 — and `BEHAVIORAL_ELASTICITIES` keeps all five values as the
documented fallback. Employer health is the one that matters, because it is the
only one of the three sitting on a Tier 1 row. Two findings came with the pass:
the shipped 0.40 **inverts to a price elasticity of 0.906, above CRS's own
published high of 0.79**; and a magnitude is a property of the *reform* for a
second reason directions are, since tightening the ceiling 28% → 15% roughly
halves the share, **0.2208 → 0.1140**, because the recapture rate *is* the cap
rate.

**Every gate the repository had was blind to this**, and that is the finding
rather than the fix. Each module's calibrated factories zero the elasticity, so
the fitted tier and the leave-one-out column are structurally blind to the sign;
of the seven, exactly **one** — corporate `reported` — reached a scorecard row.
Two shipped presets reached the others through the app. `tests/test_offset_sign_contract.py`
is now the gate: **92 tests, 86 passing and 6 skipped** — parametrised cases at
±$100B in both directions, three caption tests, two structural ones, and the one
that matters,
`test_every_offset_implementation_is_covered`, which greps the package for
`def estimate_behavioral_offset` and fails if a class is missing from
`build_cases`, because "a module nobody swept" is how all four previously-found
defects got in. It was verified to *fail* rather than assumed to work: putting
`enforcement.py`'s `abs()` back makes it fail, and the **first draft did not catch
it**, because probing only the direction a module's own constructor can reach lets
a clamped module through (`IRSEnforcementPolicy` returns a static of exactly 0.0
for a funding cut, so its `abs()` is unreachable through its own constructor — a
clamp is not a contract). That is why the test probes both signs on every
instance.

The 57.9% on the right is six populations, and they should not be read as one number — and since PR #130 the dashboard prints twelve finer ones of its own (`python scripts/run_validation_dashboard.py`), so a reader has no excuse for the pooled figure. **Fifteen are the sectoral presets** (international, trade, pharma, IRS enforcement, climate) at **82.6% mean / 39.0% median** — twelve of them Phase E's, the two tariff rows L8 unfitted, and `ira_enforcement`, which arrived in Wave 4. They ship in the app with an official figure attached and no module constant is fitted to any of them (thirteen of those targets are published scores; two are model estimates — the provenance column says which). **Quote the constant-population figure beside it**: on the fourteen rows the subset held before Wave 4, it is **88.2% mean**, not 82.6%, because the pharma rebuild took `expand_drug_negotiation` from 25.7% to 93.3% and `international_reference_pricing` from 646.2% to **701.0%**. That is a finding rather than a regression, and the lane says why: its own negotiation ladder condemned an unsourced `medicare_part_d_gross_spending_billions = 220.0` that the reference-pricing leg also reads — current law's 160 cumulative selections carry $256.8B of gross Part D spending by 2034, which does not fit inside a $220B total, and CMS's own sentence puts the total at **$281B**. Keeping the unsourced number because it flattered the prediction is the thing the pre-registration protocol exists to stop. The largest row, international reference pricing at 701%, is measured against a target whose own provenance is `model_estimate`; the next two, double IRS enforcement at 82.3% and the auto tariff at 52.8%, are measured against targets `benchmark_sources.py` records as examined-and-left and as revised respectively. **Eight are the Phase D P.L. 119-21 line items** at **35.8% mean**, a much tighter class, unmoved by Wave 4 and detailed below and in §8 of the same file. **Three are the capital-gains scenarios** at **39.6% mean** (CBO +2pp −14.0%, PWBM with step-up −28.4%, PWBM no step-up +76.5%), which arrived in Wave 2 when the constants fitted to them were deleted; because there is no per-case tuple left, these three numbers are identical to the leave-one-out column below, and `run_loo.py --donor-matrix` now prints three identical rows. **One is `extend_tcja_amt` at 66.8%**, which sits here because its target was revised and the AMT constant reproduces the superseded figure. **Five are Wave 4's provenance arrivals** at **9.4% mean** — the best-scoring population in this column, and the reason the pooled mean fell while the model did not improve. Nothing in any of the five was retuned to close a gap — the plan is explicit that a miss gets reported, not calibrated away — and every row carries a `known_limitations` note naming the structural cause. **Three are the corporate and PTC rows PRs #119 and #122 moved in**, at **67.7% mean** — `trump_corporate_15` at **121.6%**, `biden_corporate_28_fy2022` at **62.9%** and `repeal_ptc` at **18.5%**. This is the worst-scoring population in the column and every bit of it is a target moving rather than a model moving: two of the three came in when a sign fix showed their constants had been compensating for a defect, and the largest moved again when its target stopped being this repository's own output.

**Wave 7 moved this tier on accuracy, which is new, and the document says so plainly.** The tier holds the **same 34 rows** before and after PR #131, so **57.6% → 57.9% is like-for-like** and the whole 0.33pp is `repeal_ptc` going **18.5% → 29.6%** — a pre-registered regression, and the within-25 count fell 13 → 12 with it. The lane replaced a fitted $83.0B/yr — which is `1100 / (1.10 × Σ 1.04^t)`, the carried target run backwards through the engine's growth factor and the inverted offset PR #119 corrected — with CBO and JCT publication 51298 Table 2's own annual credit path (both legs, two vintages transcribed), net of publication 60437's published **19.28%** of offsetting effects. **The old constant looked fine on a ten-year metric and was 21% wrong twice**: $996.5B against CBO's $959B is 3.9%, while being 21% low in FY2026 and 21% high in FY2028, because a smooth 4% ramp cannot see the cliff the ARPA/IRA expiry puts in the credit — and the app shows the annual profile, the distributional tables and the dynamic feedback off that same series. The whole $326B of movement is three published steps and not one dollar of residual: the target understates its own source by $43B, vintage and window are worth $184B, and CBO's own offset share against the module's unsourced 10% is worth $185B. **The refusal to adopt −$1,100B is now demonstrated rather than argued**: run on the June 2024 vintage and window with no offset, the same mechanism returns **$1,143.0B against the $1,142B PR #122 traced, 0.09%** — which is what a model reading a baseline table reproducing a baseline projection looks like, and therefore the sharpest possible case for not treating one as a repeal score. **Quote the earlier constant-population readings beside it, because two composition moves are stacked underneath.** On the **33 rows the tier held before PR #122** it reads **57.4% / 29.9% median**; on the **31 it held before PR #119**, **56.6% / 29.9%**, which is exactly what it read on merged main after Wave 5. So the whole of the 56.6% → 57.4% step is `trump_corporate_15` going 22.3% → 121.6%, and the remaining 0.2pp to 57.6% is the FY2022 corporate benchmark arriving at 62.9%. **The reconstruction mean rose and that is the honest direction**: this tier is where a row goes when nothing is fitted to it, and a row that stops being scored against the model's own output should be expected to look worse, not better.

### Provenance of the targets — what the documents actually say

Phase E's first pass labelled every calibrated target by *inspecting the record*: a deep link meant `line_item`, a round hundred meant `secondhand`. That could tell a rounded headline from a citation. It could not tell whether the row being cited exists. The second pass went and looked, and the transcriptions live in [`fiscal_model/validation/benchmark_sources.py`](../fiscal_model/validation/benchmark_sources.py) — document, table, row, page, date, and the figure that was read, in this repository's sign convention.

| Label | Before (46) | After (46) | Pre-Wave-4 (54) | Pre-H9 (55) | Live (55) | What it means |
|---|--:|--:|--:|--:|--:|---|
| `line_item` | 4 | **9** | 19 | 30 | **36** | The row was found and it says what the target says (within 1.5%). |
| `line_item_differs` | — | **15** | 13 | 7 | **8** | The row was found and it says something **else** — or names a **broader reform**. |
| `secondhand` | 31 | **15** | 15 | 12 | **7** | Searched, not found — and the search is recorded. |
| `model_estimate` | 7 | **7** | 7 | 6 | **4** | No official score exists. Illustrations, never counted. |
| `unclassified` | 4 | **0** | 0 | 0 | **0** | Nothing is left in the "nobody has looked" bucket. |

H9 moved the last column: six targets onto documents and one transcription
(`biden_ctc_2021`) that confirmed its target rather than moving it. Across both
tiers that reads `line_item` 51 → **57**, `line_item_differs` 7 → **8**,
`secondhand` 17 → **12**, `model_estimate` 6 → **4**; published targets
**75 → 77 of 81** and transcribed **36 → 43**. *(Wave E then took both halves of
that pair down by four — published targets read **73 of 77**, `line_item` **58**,
`secondhand` **7**, transcribed **44** — and it is the same four rows in each: the
out-of-sample retirements, so it is a battery losing four unsourced cases rather
than four documents going missing. The whole of the `secondhand` reduction is
Tier 1's own count going **5 → 0**.)* `line_item_differs` may rise only
with a recorded range or scope verdict, and this one is a **range**
(`eliminate_mortgage.v2`).

*The live column now covers **55** calibrated rows, not 54: PR #122 registered
`biden_corporate_28_fy2022`. `line_item` is flat at 30 because two moves cancelled —
`biden_corporate_28` left it for `line_item_differs` and the FY2022 row arrived in it.
`model_estimate` fell 7 → 6 because `trump_corporate_15`'s target became published, so
the repository now scores itself against its own output in six places rather than seven,
and `NON_PUBLISHED_BENCHMARK_IDS` shrank 4 → 3. That set shrinks only by finding a
document, never by deciding a model estimate is good enough — **H9 then took it
3 → 1**, on CRS R48286 Table 1 for `tcja_rates_only` and Tax Foundation
*Options 3.0* Option 83 for `eliminate_estate_tax`, leaving only
`tcja_no_salt_cap`.*

Across both tiers the live breakdown is **57 / 8 / 12 / 4 / 0** over **81** scorecard
rows (**77** published, of which **51** are calibrated) — it read 51 / 7 / 17 / 6 / 0
with 75 published until H9 — and the Generic
tier's own `line_item_differs` count is now **zero** — `biden_high_income_tax`
went through the Tier-1 manifest in Wave 4 rather than the Tier-2 ledger.

So **24 of the 46 calibrated targets the pass covered were read out of a primary document**, against 4 that merely cited one. Of those 24, 15 disagreed with the figure this repository carried. Phase D's eight P.L. 119-21 rows then arrived already transcribed — they *are* their JCT rows, extracted into `pl119_21_jct_line_items.csv` with page references — taking the calibrated tier to **32 `line_item`-family labels across 54 benchmarks, 28 of them actually read** (the remaining 4 cite a document nobody has re-opened and are enumerated in `tests/test_validation_runners.py::CITED_BUT_NOT_TRANSCRIBED`), and the honest calibrated published-target count to **47**. Across both tiers the scorecard then held 80 rows, **73 of them against a published figure**. **PR #122 took those to 81 and 75** (calibrated 55 and **49**), by registering `biden_corporate_28_fy2022` — published from the day it arrived — and by superseding `trump_corporate_15`'s `model_estimate` target with a published range, which moved that row into the published count and took `model_estimate` rows 7 → **6**. `NON_PUBLISHED_BENCHMARK_IDS` shrank 4 → 3, and it shrinks only by finding a document.

Those disagreements have since been resolved by moving the *target* rather than the model, which is why the live column reads **36 / 8** where the transcription pass left **17 / 15**. Two moved in the AMT/insulin pass and one in Wave 3; **Wave 4 (PR #107) moved twelve more and examined four**, **PR #122 moved a sixteenth, examined a fifth, and added the first disagreement of a new kind**, and **H9 moved six more and examined nine** — taking the ledger to **22 revisions** and `EXAMINED_NOT_REVISED` to **14 entries**. **Seven calibrated disagreements remain, and none of them is an open question** — every one carries a written verdict, and the Generic tier now has none at all:

| Row | Carried | Published | Verdict |
|---|--:|--:|---|
| `pillar_two_adoption` | −$80.0B | −$102.6B | Wave 3 **range revision**, [−$102.6B, +$56.5B]; in-range anchor. Model −$61.2B is **inside**, distance $0.0B |
| `reciprocal_tariffs` | −$1,500.0B | −$1,800.0B | Wave 4 **range revision**, [−$1,800B, −$1,400B]; in-range anchor. Model −$1,396.8B sits **$3.2B outside** the nearer bound |
| `biden_estate_reform` | −$450.0B | −$429.6B | Wave 3 **examined-and-left**: JCT's figure totals a ten-section bill the module does not construct |
| `ctc_extension` | +$600.0B | +$735.3B | Wave 4 **examined-and-left**: CRS's figure is a *superset* (it bundles the Credit for Other Dependents), and JCT's +$816.8B scores a $2,200 indexed credit already carried as `pl119_21_child_tax_credit` |
| `double_enforcement` | −$340.0B | −$320.0B | Wave 4 **examined-and-left**: Treasury's figure is 6% away but scores an **$80B** funding increase on a pre-IRA baseline, where this preset stacks ~$160B on top of the IRA's $80B — the gap argues for moving it, the *dose* against |
| `trump_corporate_15` | +$673.1B | +$595.0B | PR #122 **range revision**, [+$595.0B, +$673.1B]; in-range anchor (Tax Foundation). Model +$1,491.8B sits **$818.7B outside** — the range is not doing the work here, the document is |
| `biden_corporate_28` | −$1,347.0B | −$1,349.9B | PR #122 **scope verdict**, the first: the **figures agree to 0.2%** and the *reforms* do not, so the row carries `scope_differs` instead of a figure gap |

Both range rows keep the `line_item_differs` label deliberately, because the anchor is not the transcribed figure and hiding the gap would leave an editorial midpoint looking sourced. `EXAMINED_NOT_REVISED` now holds **six** verdicts — the three above, `repeal_ptc` (§ below), `steel_tariff_25` (the 25% Section 232 rate was in force for ten weeks and no scorekeeper published a ten-year estimate; left unsourced and explicitly **not retired**, because retiring a case to avoid reporting an unsourced target is the failure mode the ledger exists to prevent) and `eliminate_mortgage` (no official repeal score exists, and the two published figures come from the **same simulator and differ by 2.4×**). A benchmark may not be both revised and examined-and-left; `target_revision_problems()` fails if one ever is. Without that state a benchmark nobody has examined looks identical to one that was, and the question gets re-opened every pass.

One access caveat, stated because it shapes several rows: `cbo.gov` returns HTTP 403 to every non-browser client, and `web.archive.org` was unreachable. Where a CBO figure could not be fetched directly it was transcribed from a *published document that quotes the CBO table verbatim* — usually a CRS report, which names the CBO publication in its own source note — and the citation is to what was actually read, never to a PDF nobody opened.

#### `line_item_differs` — the transcription disagrees with the target (each a recorded verdict)

**Five targets are carried unmoved, and every one of them carries a written verdict.** Editing a calibrated target silently converts a 0% row into a miss that says nothing about the model, so the published figure rides alongside on `ScorecardEntry.official_10yr_billions_line_item` and is listed here rather than substituted.

*This table held **thirteen** rows before Wave 4. **Nine are gone** because their targets **were** moved, and one — the reciprocal tariff — **joined** it, because its point target became a range whose anchor is not the transcribed figure. The nine left through the ledger in [`fiscal_model/validation/target_revisions.py`](../fiscal_model/validation/target_revisions.py) rather than by an edit — the old figure stays on the record as a `superseded_by` row, the new one carries document, table, row, page and date, and `target_revision_problems()` fails if the ledger and the registries the app reads ever disagree. Two more (the universal insulin cap and TCJA AMT relief) had left the same way earlier. All are `line_item` confirmations now, and the disagreements they recorded live in the ledger. See the [revised targets](#revised-targets--where-the-disagreement-went) below.*

| Benchmark | Carried | Published | Δ | The document, and why they differ |
|---|--:|--:|--:|---|
| Reciprocal tariffs (~20pp) | -$1,500B | **-$1,800B** | +20.0% | CRFB, *"How Much Will Trump's New Tariffs Raise?"*, FY2025-2034. **Wave 4 superseded the point with the range those estimates bracket**, [-$1,800B, -$1,400B]: CRFB, Tax Foundation and Yale score the *same* announced schedule on the *same* window **29% apart** ($1.8T / $1.5T / $1.4T conventional). The carried -$1,500B is Tax Foundation's, chosen because Tax Foundation publishes the repository's other two tariff benchmarks — an in-range anchor, not a selection among the three. The row keeps this label because the anchor is not the transcribed figure. The model's -$1,396.8B sits **$3.2B outside** the nearer bound; its 6.9% against the anchor is a distance from one modeller's point, not a measurement of accuracy. One caveat the range does not close: the published estimates apply a 10% floor rising to 50% by halving each partner's bilateral-deficit-to-imports ratio (with sectoral exemptions), where the module applies a flat ~20pp to half of goods imports. |
| Pillar Two adoption | -$80B | **-$102.6B** | +22.0% | JCX-22-23 Table 2, Scenario 4. The conditioning matters more than the gap: under Scenario 2 — the rest of the world enacts, as it has — JCT scores US adoption at **-$56.5B of receipts**, the opposite sign. **Wave 3 superseded the target with the range those two scenarios bracket**; the row keeps this label because the gap to the nearest published *scenario* is real. The model's -$61.2B is **inside** the range, distance $0.0B. |
| CTC extension | $600B | **$735.3B** | -18.4% | CRS R48286 Table 1. **Wave 4 examined it and deliberately left it** (`EXAMINED_NOT_REVISED`): CRS states its figure *"include[s] the budgetary impact of the Credit for other dependents"*, which `credits.py` does not score — a **superset**, not a substitute. The other candidate, JCT JCX-35-25's **+$816.8B**, scores a **$2,200 indexed** credit against this benchmark's **$2,000 flat** one, and is already carried here as `pl119_21_child_tax_credit`, so adopting it would score one JCT row as two benchmarks. Both sit *above* the module's design rather than bracketing it, so a range would assert a containment neither publisher supports. For the record: the fitted $600.0B is 0.00% / -18.4% / -26.5% against the three figures, and the held-out structural path's $714.2B is +19.0% / -2.9% / -12.6% — **the structural path is twice as close to JCT's row as the fitted constant while scoring worse against the carried target**, which is an argument for the L3 rebuild rather than for moving this target. What would move it is a published score of a $2,000 flat extension without the other-dependents credit; none exists. |
| Double IRS enforcement | -$340B | **-$320.0B** | -6.2% | Treasury, *American Families Plan Tax Compliance Agenda* p. 18. **Wave 4 examined it and deliberately left it**: the *gap* argues for moving it and the **dose** argues against. That $320B is the yield on an **$80B** increase in the IRS budget, scored in 2021 on a **pre-IRA** baseline; this preset scores ~$160B of additional funding stacked *on top of* the IRA's $80B — twice the dose, on a baseline that already contains the dose Treasury scored. Treasury's $700B headline is not a candidate either: $460B of it is bank information reporting the module does not implement. |
| Trump corporate 15% | $1,920B | **[+$595.0B, +$673.1B]** | +185.7% vs the anchor | PWBM, *The 2024 Trump Campaign Policy Proposals* (26 Aug 2024) Table 1, -$595B FY2025-2034; Tax Foundation, Watson & York (17 Jul 2024, upd. 23 Oct 2024) Table 2, -$673.1B 2025-2034; CRFB's 6 Sept 2024 post prints both side by side. **PR #122 superseded a `model_estimate` with the range those two bracket** — +$1,920.0B was never a target, the scenario's own note read "No official score; expected estimate derived from model", and the module reproduced it only because `estimate_behavioral_offset` returned `abs(static)`. The **anchor rule is about the documents, not the model**: Tax Foundation's is a standalone analysis of this one reform with its own revenue table, PWBM's a stacked row inside a whole-campaign package that carries interaction with the rest of it; anchoring on the bound nearer the model would have been selection and a midpoint the editorial invention ranges exist to prevent. The model is **$818.7B outside** the range, where `pillar_two_adoption` is inside and `reciprocal_tariffs` $3.2B out — so unlike those two, the range is not doing the work here. About a third of the residual is bonus depreciation, which neither published figure includes (rate leg alone +77.9%). The app's own score map had been carrying **673.0** all along, credited to CRFB; only its attribution moved, to "Tax Foundation / PWBM (via CRFB)", while `PRESET_POLICIES`' description had been telling users "Estimated cost: ~$1.9T over 10 years" — this model's output quoted back at them, contradicting the app's own score map — and now states the published range and the bonus-depreciation scope. |
| Biden corporate 28% | -$1,347B | **-$1,349.9B** | **0.2% — a scope gap, not a figure gap** | Treasury FY2025 Green Book, report p. 239 (PDF p. 247), $1,349,941M. **The figures agree; the reforms do not.** From the FY2023 edition onward the row's own chapter moves the GILTI effective rate with the statutory rate, while `create_biden_corporate_rate_only` sets `gilti_rate_change=0.0`. `line_item` would have asserted an agreement the documents do not support and `test_line_item_differs_carries_the_published_figure` would have rejected the row (0.2% is inside `CONFIRMATION_TOLERANCE_PCT`), so `BenchmarkSource` gained **`scope_differs`**: one sentence naming the mechanism, with the invariant that a `line_item_differs` row must carry a figure gap wider than the tolerance **or** a filled `scope_differs`, never neither, so the label can never mean "something is wrong here, unspecified". `__post_init__` rejects `scope_differs` on any other provenance — a *confirmed* line item that also declares a scope difference is confirming something the module does not build — and the test asserts both branches are live so neither can rot. **The target did not move**: the GILTI leg's size is never printed and is not recoverable by differencing editions. |
| Estate reform ($3.5M, 45%) | -$450B | **-$429.6B** | -4.7% | JCT letter of 24 March 2021 on the "For the 99.5 Percent Act", letter p. 5, row *"Total, For the 99.5 Percent Act"*. **No Biden Green Book ever proposed a $3.5M exemption or a 45% rate** — the "Treasury estimate" attribution was wrong and is corrected. **Wave 3 examined it and deliberately left it**: JCT totals graduated 50/55/65% brackets, grantor-trust step-up denial, valuation-discount limits, 10-year minimum GRATs and GST changes, where `estate.py` constructs an exemption change to $3.5M and a *single* 45% rate — not even the whole rate section. Adopting -$429.6B as a point target would convert a bookkeeping 0.00% into a 4.75% that measures the eight sections the module does not model. Both modes, both figures: `reported` -$450.0B (+0.00% vs carried, -4.75% vs published), `derived` -$457.2B (-1.60% / -6.43%). What would change the verdict is a JCT or Treasury score of an exemption-and-rate change alone; none exists. |

**The nine that left this table**, with the model figure unchanged in every case and only the error column moving — **six of the nine got worse**, which is the shape a correct provenance pass has: if every revision improved its row, the suspicion would be that the documents were chosen to fit rather than read. Those same six are the six of Wave 4's thirteen revisions that worsened a row.

| Benchmark | Was | Is | Document | Err before -> after |
|---|--:|--:|---|---|
| Eliminate SALT deduction | -$1,200B | **-$1,621.0B** | CBO pub. 60557, Option 49, row *"Eliminate state and local tax deductions"*, report p. 59 | 5.0% -> **22.3%** |
| Biden GILTI reform | -$280B | **-$373.9B** | FY2025 Green Book, report p. 239 | 17.8% -> **38.4%** |
| Repeal FDII | -$200B | **-$158.0B** (the gross row) | FY2025 Green Book, $157,993M, report p. 239 | 44.7% -> **29.9%** |
| Biden international package | -$700B | **-$632.2B** | FY2025 Green Book, *"Subtotal, Reform International Taxation"*, $632,200M, p. 240 | 49.5% -> **44.1%** |
| EITC childless expansion | +$178B | **+$162.6B** | FY2025 Green Book, $162,553M, p. 242 | **0.0%** -> **9.5%** |
| IRA enforcement funding | -$200B | **-$180.4B** | CBO pub. 58390 (Aug 2022), letter p. 1 — the $203.7B the old target sat 2% below had been **withdrawn** | 5.5% -> **4.7%** |
| Repeal EV credits | -$200B | **-$182.3B** | JCT JCX-35-25, secs. 30D + 45W, p. 3 | 14.2% -> **25.3%** |
| Extend enhanced PTCs | +$350B | **+$335.0B** | CBO/JCT pub. 60437 (June 2024), letter p. 1 — the carried figure was a *September 2025* re-estimate on a different window | 4.6% -> **9.3%** |
| Trump universal 10% tariff | -$2,000B | **-$2,171.1B** | Tax Foundation FF861, Table 3, conventional column, report p. 4 | 37.1% -> **42.0%** |

Three more targets were revised without having been in this table — `repeal_salt_cap`, which was unsourced rather than contradicted (+$1,100B -> PWBM Table 3's **+$1,169.0B**, error 5.1% -> **1.2%**), and the two tariff rows whose old targets were not merely unsourced but the *wrong kind of number*: **`auto_tariff_25`** -$100B -> **-$386.2B** (Tax Foundation tariff tracker Table 5) — the -$100B traces to a **per-year** claim ("about $100 billion with the auto tariffs alone", 30 March 2025) carried as a decade figure, wrong by a factor of ten and in the direction that flattered the model; error 82.2% -> **52.8%**. And **`reciprocal_tariffs`** -$1,200B -> the range above — -$1,200B is **exactly Tax Foundation's dynamic score**, sitting in a scorecard whose every other target is conventional. That was a **tier** error, not a magnitude error, and no amount of scaling would have found it.

**And one out-of-sample row moved too**, through the Tier-1 manifest rather than the Tier-2 ledger: **Biden top rate 39.6%**, -$252B -> **-$245.9B** (`biden_high_income_tax.v2`; FY2025 Green Book, $245,924M, report p. 242). Nothing in the model reads the target — the prediction is the same -$216.5B it was — so only the error moved, 14.1% -> **12.0%**. The FY2024 Green Book prints $235,263M for the same row on its own window, which is the check that the row is stable across vintages rather than a one-off.

#### Revised targets — where the disagreement went

**Twenty-two** calibrated targets have been **corrected**, not carried — three before Wave 4, twelve in it, one in the corporate/PTC pass and **six in H9** (`planning/lanes/HSB_h9_provenance.md`, the pass over the eighteen calibrated targets that were not `line_item`). Errors in this table are
**signed** — negative means the model scores below the target — where every other
table on this page reports absolute percent error. All twenty-two went through
[`fiscal_model/validation/target_revisions.py`](../fiscal_model/validation/target_revisions.py),
the calibrated tier's mirror of `preregistered.py`'s supersede rule: entered in
one commit and first scored in the next, so "the target moved before the model
was allowed to see it" is checkable from `git log`. **No constant was retuned**,
which is the whole point — a module still fitted to the superseded figure now
reads as a miss, and that miss is the finding. Eleven of the twenty-two rows left the
fitted tier as a mechanical consequence — six before H9 and five in it.

| Benchmark | Superseded | Live target | Model | Err vs live (signed) | Document |
|---|--:|--:|--:|--:|---|
| Universal insulin cap | -$15B | **+$11.4B** | +$7.0B | **-39.0%** | CBO pub. **57957** (H.R. 6833), table p. 1 — "Secs. 2 and 3, Cost-Sharing for Certain Insulin Products": outlays 6,566, revenues -4,793, FY2022-2031. A $35 monthly cap is a *cost-sharing* cap: it moves liability onto the plan and onto the federal subsidy for it, so it adds to the deficit. -$15B is traceable to no CBO document. |
| Extend TCJA AMT relief | $450B | **$1,357.1B** | $450.5B reported / $855.3B derived | **-66.8%** reported, **-37.0%** derived | CRS **R48286** Table 1, transcribing CBO 60114/60271 — "Increased Alternative Minimum Tax Exemption", FY2025-FY2034. The adjacent FY2025-FY2029 column prints $466.2B, so the carried $450B was 3.5% from the five-year cost and 66.8% from the ten-year one: a five-year figure in a ten-year column. Corroborated by JCT's **JCX-35-25** at $1,362.810B for P.L. 119-21's AMT provision (0.4% away, and already a benchmark here). |
| Pillar Two adoption | -$80B (point) | **range [-$102.6B, +$56.5B]** | -$61.2B | **inside the range**, distance to the nearest bound **$0.0B** (23.5% against the carried midpoint) | JCT **JCX-22-23** Table 2, report p. 10 — **Scenario 4** (rest of the world does not enact; US enacts, no US UTPR) +$102.6B of receipts, **Scenario 2** (rest of the world enacts; US enacts, no US UTPR) -$56.5B. |
| Eliminate SALT deduction | -$1,200B | **-$1,621.0B** | -$1,260.3B | **-22.3%** | CBO pub. **60557**, Option 49 *"Eliminate or Limit Itemized Deductions"*, row *"Eliminate state and local tax deductions"*, report p. 59 (PDF p. 65). |
| Repeal SALT cap | +$1,100B | **+$1,169.0B** | +$1,155.6B | **-1.2%** | PWBM, Novak, *"Lifting the SALT Cap"*, **Table 3** (against extended TCJA, FY25-34), row *"Repeal SALT Cap"*. The rounding hid the **baseline**: PWBM's Table 1 gives -$197B on current law, Table 2 -$1,116B on FY2024-2033 and Table 3 -$1,169B on this repository's own window — **5.7× apart on the baseline alone**. The baseline now travels with the target in both `benchmark_sources.py` and the scenario's notes. |
| Biden GILTI reform | -$280B | **-$373.9B** | -$230.3B | **-38.4%** | FY2025 Green Book, *"Revise the global minimum tax regime, limit inversions, and make related reforms"*, report p. 239 (PDF p. 247). |
| Repeal FDII | -$200B | **-$158.0B** (the gross row) | -$110.7B | **-29.9%** | FY2025 Green Book, *"Repeal the deduction for foreign-derived intangible income"*, $157,993M, report p. 239. Treasury pairs FDII repeal one-for-one with an R&D-support offset and prints an explicit subtotal of $0; the module scores the gross repeal, so the gross row is the comparable one. |
| Biden international package | -$700B | **-$632.2B** | -$353.7B | **-44.1%** | FY2025 Green Book, *"Subtotal, Reform International Taxation"*, $632,200M, report p. 240 (PDF p. 248). |
| EITC childless expansion | +$178B | **+$162.6B** | +$178.0B | **+9.5%** | FY2025 Green Book, *"Restore and make permanent the American Rescue Plan expansion of the earned income tax credit for workers without qualifying children"*, $162,553M, report p. 242. |
| IRA enforcement funding | -$200B | **-$180.4B** | -$188.9B | **+4.7%** | CBO pub. **58390** (Aug 2022), letter p. 1: *"revenues will increase by $180.4 billion over the 2022-2031 period"*. The carried -$200B sat 2% below $203.7B — a figure CBO had **withdrawn**. |
| Repeal EV credits | -$200B | **-$182.3B** | -$228.4B | **-25.3%** | JCT **JCX-35-25**, sec. 30D ($77,829M) + sec. 45W ($104,516M), p. 3 (PDF p. 5). The source had been mislabelled CBO. |
| Extend enhanced PTCs | +$350B | **+$335.0B** | +$366.2B | **+9.3%** | CBO/JCT pub. **60437** (June 2024), letter p. 1. The carried $350B is CBO/JCT's *September 2025* re-estimate on the FY2026-2035 window: the number and its stated vintage were one budget window apart. |
| Trump universal 10% tariff | -$2,000B | **-$2,171.1B** | -$1,258.5B | **-42.0%** | Tax Foundation **FF861**, Table 3 *"Conventional Revenue Estimates"*, row *"10 Percent Universal Tariff"*, report p. 4. |
| 25% auto tariff | -$100B | **-$386.2B** | -$182.2B | **-52.8%** | Tax Foundation tariff tracker, **Table 5**, *"Section 232 Autos, Heavy Trucks, Buses, and Parts"*, conventional column, 2026-2035. The carried -$100B traces to a **per-year** claim of 30 March 2025 — *"We're going to raise about $100 billion with the auto tariffs alone"* — carried as a decade figure, wrong by a factor of ten **and in the direction that flattered the model**: it made a module scoring -$182.2B look 82% out when the published conventional estimate is -$386.2B. Superseded by a *point* rather than a range because the second published figure (Yale, $600-650B) scores the tariff *as announced*, before the trade-deal carve-outs the tracker's as-in-force row reflects. |
| Trump corporate 15% | +$1,920B (point) | **range [+$595.0B, +$673.1B]**, anchor +$673.1B | **+$1,545.2B** | **$872.1B outside** the nearer bound (**129.6%** against the anchor; it was $818.7B and 121.6% until PR #166 moved the scorecard onto `derived`) | Tax Foundation, Watson & York, Table 2 (anchor), and PWBM, *"The 2024 Trump Campaign Policy Proposals"* Table 1 (+$595B), printed side by side in CRFB (6 September 2024). The superseded figure was **this model's own output** — the scenario's note read "No official score; expected estimate derived from model". A third of the residual is scope: `create_republican_corporate_cut` sets `extend_bonus_depreciation=True` and neither published figure includes it, so the rate leg alone reads +$1,197.6B (+77.9%). |
| SS donut hole $250K | -$2,700B | **-$1,426.8B** | -$2,700.0B | **-89.2%** | CBO pub. **60557**, Option 62 alternative 2, *"Subject earnings greater than $250,000 to payroll taxes"*, report p. 73 (PDF p. 79), stub *"Decrease (-) in the deficit"*, FY2025-2034. Same design in CBO's own words, including no benefit credit: *"The current-law taxable maximum would still be used for calculating benefits, so scheduled benefits would not change under this alternative."* The superseded -$2.7T is credited to the Trustees, who publish no dollars for E2.5 at any horizon. |
| TCJA rates only | +$3,185B | **+$2,158.7B** | +$3,114.7B | **+44.3%** | CRS **R48286** Table 1, *"Reduced Individual Tax Rates"*, FY2025-2034 — the same table, column and window this page already reads `extend_tcja_amt`'s $1,357.1B from, transcribing CBO 60114's JCT row *"10%, 12%, 22%, 24%, 32%, 35%, and 37% income tax rate brackets"*. The superseded figure was the repository's own decomposition; the scenario's note called it "illustrative". |
| Eliminate estate tax | +$350B | **+$407.2B** | +$350.0B | **-14.0%** | Tax Foundation, *Options for Reforming America's Tax Code 3.0* (July 2026), Option 83 *"Eliminate the Estate and Gift Tax"*, printed p. 105, CY2027-2036, post-P.L. 119-21 baseline. The superseded figure's source field read "Model estimate". JCT's 2017 rows bundle repeal with the exemption doubling and are not candidates. |
| Repeal IRA clean energy credits | -$783B | **-$851.0B** | -$783.0B | **+8.0%** | William McBride, Tax Foundation testimony to the House Committee on Oversight and Government Reform (20 May 2025): *"full repeal of the credits would reduce deficits by $851 billion over the next decade (2025-2034)"*. The cited CBO publication does not exist. JCT's JCX-7-23 ($515.1B) was declined on scope, not distance: its own footnotes make it revenue-only and exclude all three clean-vehicle credits. |
| Trump 60% China tariff | -$500B | **-$650.0B** | -$278.4B | **+57.2%** | CRFB, *"Options to Raise Tariff Revenue"* (17 December 2024), row *"60% Import Tariff on Chinese Goods"*, conventional column, FY2026-2035. The adjacent row prices the same tariff on top of a 10% universal baseline at -$575B, which is what makes this row unambiguously the preset's shape. The superseded -$500B was obtainable only as a residual from a Tax Foundation bundle. |
| Eliminate mortgage deduction | -$300B (point) | **range [-$495.0B, -$367.9B]**, anchor -$367.9B | -$270.3B | **$97.6B outside** the nearer bound (26.5% against the anchor) | Tax Foundation *Options 3.0* Option 25 (anchor, CY2027-2036) and CRS **IF13190** Table 2, *"Repeal MID $495"* (FY2026-2035, on the Yale Budget Lab Tax-Simulator). Wave 4 left this row because its two known figures came "from the same simulator"; a third, independent model resolves the 2.4x as a **baseline** gap — Yale's ~$1.2T is pre-P.L. 119-21, where the standard deduction lapses. |
| Reciprocal tariffs (~20pp) | -$1,200B (point) | **range [-$1,800B, -$1,400B]**, anchor -$1,500B | -$1,396.8B | **$3.2B outside** the nearer bound (6.9% against the anchor) | CRFB, *"How Much Will Trump's New Tariffs Raise?"*, table *"Ten-Year Scores of Trump's Tariffs, If Made Permanent"*, FY2025-2034: CRFB **$1.8T**, Tax Foundation **$1.5T**, Yale Budget Lab **$1.4T**, all conventional, all the same window, **29% apart**. The superseded -$1,200B is *exactly* Tax Foundation's **dynamic** score, sitting in a scorecard whose every other target is conventional — a **tier** error, not a magnitude error, and one no rescaling would have found. |

**A range revision asserts something a point revision does not, and Wave 3 added
the machinery to say so — Wave 4 used it a second time.** -$80B is the midpoint of the "$50-120B" range
`international.py` documents in its own header; JCT publishes no such figure.
Choosing one of its five scenarios instead would mean choosing the *rest of the
world's* behaviour, which is not part of the US policy being scored — and the
scenario whose conditioning matches the module's own QDMTT mechanism is also the
one it scores best against, which is exactly the selection the ledger exists to
prevent. Scenarios 1 (the US does not act) and 5 (the US adds a UTPR, which this
benchmark's factory does not set) are different policies and bound nothing here;
they are recorded only so the chosen bounds cannot be mistaken for a selection.
So `CalibratedTarget` gained `published_low_10yr_billions` /
`published_high_10yr_billions`, `is_range`, `contains()` and
`distance_to_range()`; for a range row the consistency check asks
**containment** instead of equality; and `ScorecardEntry` and
`/validation/scorecard` expose `published_range_low_billions`,
`published_range_high_billions`, `within_published_range` and
`distance_to_published_range_billions`. **Nothing moved in the registries or the
app**, because -$80B is inside the published range. What changed is that the row
now says the gap is *not closable by any point*, and that its 23.5% is a
distance from an editorial midpoint rather than a measurement of accuracy.

**The opposite verdict is now recordable too.** `EXAMINED_NOT_REVISED` in the
same module states "somebody opened the document and decided against", with the
reason — without it, a benchmark nobody has examined looks identical to one that
was, and the question gets re-opened every pass. `biden_estate_reform` was its
first entry; Wave 4 added four more and PR #122 a sixth, so the registry now holds **six**:

| Row | What was found | Why it was left |
|---|---|---|
| `biden_estate_reform` | JCT letter, 24 Mar 2021, -$429.6B | Totals a ten-section bill against the module's exemption-and-single-rate construction |
| `ctc_extension` | CRS R48286 $735.3B; JCT JCX-35-25 +$816.8B | The first is a **superset** (bundles the Credit for Other Dependents); the second scores a $2,200 indexed credit and is already carried as `pl119_21_child_tax_credit` |
| `double_enforcement` | Treasury AFP Compliance Agenda p. 18, $320B | 6% away, but it is the yield on an **$80B** funding increase on a pre-IRA baseline; this preset stacks ~$160B on top of the IRA's $80B |
| `steel_tariff_25` | Nothing, and now the negative result has a cause | The 25% Section 232 rate was in force **12 March - 3 June 2025**, ten weeks; no scorekeeper published a ten-year estimate of that regime. The nearest figures score the 50% rate with copper folded in, or derivative-rule changes. Left unsourced and **explicitly not retired** — retiring a case to avoid reporting an unsourced target is the failure mode the ledger exists to prevent |
| `repeal_ptc` | CBO/JCT pub. 51298 (June 2024) Table 2: $966B of PTC outlays + $176B of revenue reductions = **$1,142B**, FY2025-2034 — **3.8% from the carried -$1,100B** | It is a **baseline projection sitting in a repeal-score column**, the same class this benchmark already refuses for JCX-48-24 and that `repeal_individual_amt` refuses TPC's T25-0049 for. A projection of what a credit costs carries no coverage response and no interaction with Medicaid, employer coverage or taxable wages. Adopting it would make the row **worse**, 18.5% → 21.5%, and no scored repeal exists to move to: CBO/JCT pub. **61734** (Sept 2025), the most recent marketplace menu, contains no option eliminating the credit, and the 2018/2020/2022/2025 Options volumes carry none either. **The shape is as much of the mismatch as the target**: `create_repeal_ptc` sets `coverage_elasticity=0.0` under the comment "Not modeling coverage offset", so what the module computes *is* a baseline cost — an owner decision about `ptc.py`, which a provenance lane may not open |
| `eliminate_mortgage` | CRS IF13190 $495B; Yale "close to $1.2 trillion" | The two ten-year repeal figures come from the **same simulator and differ by 2.4×**, and CRS labels its own *"not considered official for revenue scoring purposes"*. That disagreement is itself the argument against adopting either |

A benchmark may not be both revised and
examined-and-left, and `target_revision_problems()` fails if one ever is. **Nor
may it be both examined-and-left and retired**, which is the third pairing the
same check forbids: owner decision ④ withdrew `expand_drug_negotiation` and
`international_reference_pricing`, so the two verdicts Wave B had written for
them left this registry with them. The table above is PR #122's snapshot; the
live count is **12** (Wave B added nine and `eliminate_mortgage` left when a
third document contradicted its Wave 4 verdict, taking it to 14; the two
retirements take it to 12). Read it from the registry, not from this line:
`python -c "from fiscal_model.validation.target_revisions import EXAMINED_NOT_REVISED as e; print(len(e))"`.

**One constant was sourced without being wired.** `eliminate_mortgage`'s
`annual_cost_no_limit = 100.0` traces to Treasury OTA's *Tax Expenditures*
(FY2019 edition, law as of 1 July 2017), Table 1 row 59: $1,003,230M over
FY2018-2027 = **$100.32B/yr**, corroborated by JCX-59-23's $100.6B for FY2027.
It stays deliberately unread, and the source is *why*: what it is the "no limit"
level *of* is the pre-TCJA regime as a whole — the smaller standard deduction
and the uncapped SALT deduction, which together set how many filers itemise —
not IRC §163(h)(3)(F). The acquisition-debt limit alone is worth about **$4B/yr**
(JCX-35-25 scores its extension at +$39,532M over FY2025-2034), so wiring the
constant to the $750,000 cap would still be wrong by an order of magnitude and
would move the row from -5.1% to about +244%. Sourcing it changed the *reason*
it stays unread, not the decision. A live handoff comes with it: the record's
`annual_cost = 25.0` is a **pre-P.L.119-21** level, and JCT ($45.5B rising to
$54.9B) and Treasury ($23.9B falling to $14.1B) disagree about its replacement
by 2-4× on the same statute, driven by Treasury's comprehensive-income baseline
against JCT's normal-tax one.

**One contradiction is stated rather than resolved.** `repeal_salt_cap` is now
explicitly priced against a permanent $10,000 cap (PWBM Table 3's extended-TCJA
world), while its twin `eliminate_salt` is priced on CBO Option 49's world where
the cap has lapsed. Reconciling them needs a baseline-vintage concept the
expenditure module does not have, and `eliminate_salt`'s CBO baseline is in any
case no longer current law after P.L. 119-21 — whose sec. 70120 replaced the
$10,000 cap with $40,000 for 2025-2029, reverting in 2030, and whose JCT row
(+$946.2B) is already carried separately as `pl119_21_salt_cap_40k`. Both
records now say which baseline they are on, which is the most a provenance lane
can do.

The insulin correction empties `KNOWN_TARGET_SIGN_INVERSIONS` in
`tests/test_validation_runners.py`, and the emptiness is the assertion: **no
scorecard row now disagrees with its own target about what a policy does.**

**`repeal_individual_amt` was searched again and not moved.** It keeps an
unsourced $450B, because there is nothing to move it to: TPC publishes no
"repeal the individual AMT" estimate at any date, JCT and CBO publish no
post-2025 repeal score, and the nearest primary figure — JCX-46-17 p. 3,
-$695.5B over FY2018-2027 — is a *pre-TCJA* baseline and a different decade. The
one published quantity that fits the policy, **TPC T25-0049's AMT-revenue column
($948.9B over 2026-2035)**, is deliberately not adopted for two independent
reasons: it is a baseline projection rather than a scored repeal (the rule
`benchmark_sources.py` already applies to `repeal_ptc`), and it is `amt.py`'s own
input, so adopting it would manufacture a 0% row out of exactly the leakage
pattern `loo.py` guards against. Two things stay on the record for the owner:
$450B is traceable to nothing, and it is internally incoherent with the
transcribed $1,357.1B, since a *full repeal* cannot cost less than extending the
exemption on the same baseline. Closing it needs either a published score that
does not yet exist, or an owner decision to re-register `holdout.py`'s locked
`revenue-scorecard-post-lock-2026-05-02` protocol — which has no
re-registration path, so adding one would mean editing the gate itself.

#### The range-target rule

Four rows now carry a **published range** rather than a point — `pillar_two_adoption`
(Wave 3), `reciprocal_tariffs` (Wave 4), `trump_corporate_15` (PR #122) and
`eliminate_mortgage` (H9) — and each was decided ad hoc before this rule was
written down. `CalibratedTarget.distance_to_range()` already implements the
arithmetic; the rule is what stops the fifth re-opening the question.

1. **When a range.** Two or more standing estimators scored the *same* reform on
   the *same* window and disagree, or one body published several scenarios and no
   single figure. Then any point the repository carries is an **editorial
   midpoint**, and a point target would assert something no document contains.
2. **The error is the distance to the nearest bound**, in dollars, and it is
   `0.0` when the model's score is inside. Containment is the pass condition:
   read `within_published_range` and `distance_to_published_range_billions`.
3. **The percentage against the anchor is not a measurement of accuracy.** It is
   a distance from one modeller's point. `pillar_two_adoption` reports 23.5%
   while sitting **inside** its bounds; `reciprocal_tariffs` reports 6.9% while
   sitting **$3.2B outside**. Neither percentage means what a percentage means on
   a point row, and every surface that prints one must say so.
4. **The anchor is chosen on the documents, never on the model.** A standalone
   analysis of the one reform beats a stacked row inside a package that carries
   interaction with the rest of it; a publisher this repository already scores
   its neighbours against beats one it does not; a body's own model beats a
   transcription of somebody else's that its author declines to call official.
   Choosing the bound nearer the model is selection and is forbidden — PR #122
   anchored `trump_corporate_15` on the **farther** bound for exactly this
   reason, and H9's `eliminate_mortgage` landed on the nearer one from the same
   rule. The rule is the constant; which bound it picks is not.
5. **A range row stays `line_item_differs`**, and its `published_10yr_billions`
   carries the bound the anchor is *not*, so the spread sits on the row rather
   than only in the ledger. `test_a_range_revision_publishes_its_bounds_and_keeps_the_gap_visible`
   enforces it.
6. **A range is not a way to pass.** `trump_corporate_15` sits $818.7B outside its
   bounds and reports 121.6%. The range did not soften that; the document did.

#### Illustrations (no official score)

**Four** scorecard rows have no published figure behind them at all — PR #122 took `trump_corporate_15` off this list by finding two, and H9 took `eliminate_estate_tax` and `tcja_rates_only` off it by finding one each; the list shrinks only that way, never by deciding a model estimate is good enough. They are kept — deleting them would hide model behaviour a user can still trigger from the app — but they are **excluded from every count and every accuracy statistic**, they have their own table in the Validation tab, and the delta column there is labelled as self-comparison.

| Row | "Official" | Model | Δ | What the source string actually says |
|---|--:|--:|--:|---|
| TCJA extension, no SALT cap | $5,700B | $6,494B | +13.9% | The repository's own decomposition of the full-extension benchmark. CRFB's "Extend except SALT cap" row ($5.1T, FY2026-2035) is a published single figure and is **not** adopted: it pairs with CRFB's own $3.9T base where this repository scores the base extension against CBO's $4.6T, so most of the resulting error would be the base gap. Both publications agree on the increment actually at issue — CRFB +$1.2T, CRS R48286's itemized-deduction row $1,244.3B — against the ~$1.1T assumed here. |
| Expand drug negotiation | -$500B | **-$34B** | **+93.3%** | CBO scored the IRA's 20 drugs (-$237B); 50 drugs is an extrapolation, and since Wave 4 the module prices the expansion through a negotiation ladder that bites in only 6 of the 10 years, because an annual *selection cap* has nothing to raise until 2029. |
| International reference pricing | -$100B | **-$801B** | **-701%** | A RAND price statistic, not a budget score. CBO scored H.R. 3's *narrower* cap — 120% of the average international market price on a limited set of drugs — at about $456B, so a model of capping **all** Medicare drug prices belongs above that figure, not below $200B. |
| Carbon tax $50/ton | -$1,700B | -$1,715B | -0.9% | `climate.py` documents its behavioural factor as calibrated to yield ~$1.7T; the target restates that. Nothing published scores $50/ton with a **5% escalator**; the two totals near the design use a **2% real** one (Treasury OTA WP-115's $2,221B over CY2019-2028 at $49/ton, and Rhodium/Columbia SIPA's $1,682-1,781B of 2016 dollars over CY2020-2029 at $50/ton). The carried figure falls inside that second range and **that is not evidence** — different window, different units, different escalator. |

The other two the expansion plan names (§5.2) are distributional: `TPC_CORPORATE_RATE_INCREASE` and `TPC_CAPITAL_GAINS_INCREASE` are reasoned from an incidence assumption plus a concentration statistic, not copied from a TPC table. They now carry `is_published=False` and sit in `ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS`; `PUBLISHED_DISTRIBUTIONAL_BENCHMARKS` is the set anything may count. **The published distributional quintile set is 2, not 4.**

#### What stayed secondhand, and why

**Seven** calibrated targets remain searched and not found (twelve before H9, fifteen before Wave 4). Each carries a `searched` record naming the documents checked, so nobody repeats the work. The survivors are `ss_eliminate_cap`, `cap_charitable`, `cap_employer_health`, `eliminate_step_up`, `repeal_individual_amt`, `repeal_ptc` and `steel_tariff_25`, and **every one of them now carries a written verdict** in `target_revisions.EXAMINED_NOT_REVISED`. The three that matter most:

- **`ss_eliminate_cap` (-$3.2T)** is credited to the Social Security Trustees. **`ss_donut_250k`'s target moved in H9** — to CBO Option 62 alternative 2's **-$1,426.8B**, 47% below the figure it carried — so it is no longer on this list; the paragraph below is kept because it is the record of *why* it moved. OCACT *does* score both provisions (E2.5 and E2.1) — and **publishes no dollar figures for them at all**, only percent-of-taxable-payroll (+2.50% and +2.55% of payroll) and trust-fund depletion dates. The widely repeated "$2.7 trillion over 10 years" traces to a think-tank explainer with no report year and no run number. CBO's published figures for the same designs are roughly half: $1,222.6B (2018 volume) and $1,426.8B (2024 volume, Option 62). These two are set out in full in [The two OCACT payroll targets, said out loud](#the-two-ocact-payroll-targets-said-out-loud) below — provision text, run numbers, what a published ten-year dollar figure would be, and the held-out scores now printed beside the shipped ones.
- **`cap_charitable` (-$200B)** is a **charitable-only 28% benefit-rate cap**, and no official score of that design exists in any volume or any year. Every official rate cap covers all itemized deductions (CBO's 2017-2026 Option 8, $171.5B) and every official charitable-only option is a floor or a cash-only rule (Option 50's $347.7B / $324.3B). The one non-official ten-year figure for the exact design — CRFB's 2013 "Impose a 28% limit on the value of the deduction | $75" over 2014-2023 — is **not adopted**, because CRFB prints beneath it that its scores "are rough estimates" "chiefly estimated from a 2011 CBO analysis based on 2006 data".
- **`cap_employer_health` (-$450B)** is described as a "$50K cap", and H9 found what the figure most likely **is**. CBO's *Budget Options, Volume 1: Health Care* (December 2008), Option 9, p. 24, is the only published option that states the cap in dollars — "$1,440 a month for family coverage or $565 a month for individual coverage" — and JCT scores it at **$452.1B over FY2009-2018**, 0.5% away. But $1,440 a month is $17,280 a year against the $50,000 this benchmark describes, so it is the right number for a cap a third the size, a decade early: `extend_tcja_amt`'s shape, with nothing to move it to. No agency has ever scored a cap set at a chosen dollar level.

Live counts: `python -c "from fiscal_model.validation import compute_scorecard; print(compute_scorecard().calibrated_provenance_breakdown)"`.

#### Retired targets — the first two withdrawals, and the second reading they come with

A supersession says *the target moved here*. An `EXAMINED_NOT_REVISED` verdict
says *somebody opened the document and kept the carried figure*. **Retirement**
says the third thing — *this figure is not a score of anything, and no published
score of this policy exists to put in its place*. PR #145 built the state,
tested it on synthetic rows and applied it to nothing, because withdrawing a
target is an owner's decision. **Owner decision ④ took it, for exactly two
benchmarks:**

| benchmark | withdrawn target | model | error it carried | what it was |
|---|--:|--:|--:|---|
| `expand_drug_negotiation` | -$500.0B | -$33.5B | **93.3%** | this repository's extrapolation from $237B — a figure `W4_pharma_part_d.md` established was never a negotiation score but CBO's total for the whole drug-pricing title. CBO's December 2024 *Options* volume contains no drug-negotiation option at all, and "at least 50 drugs" appears nowhere in the FY2025 Budget. |
| `international_reference_pricing` | -$100.0B | -$801.0B | **701.0%** | a derivation from a RAND price index, which is a price statistic. CBO *did* score reference pricing — H.R. 3 Title I at -$455,927M (publication 55936) — but on a selected cohort and a **pre-IRA** baseline, so adopting it would double-count the IRA's own -$98.5B. |

**What "retired" means here, precisely.** The row is **not deleted and never
will be**. It keeps its scorecard entry, its model figure and the withdrawn
figure in `official_10yr_billions`, so it still prints; `calibrated_to_target` is
forced `False`, exactly as a revision does;
`ScorecardSummary.retired_target_entries` counts it; `check_readiness.py`
**lists** it by id
(`retired_target_policy_ids`) rather than blocking on its rating, because
blocking on a row that has no target would make deleting it the cheapest route
back to green. Both verdicts state what was searched **and what would bring the
target back** — a published post-IRA score of a negotiation expansion, or a
ten-year federal score of a Medicare-wide international reference price.

**The two readings, and why there are two.** Withdrawing 93.3% and 701.0% from a
40-row tier averaging 60.0% leaves 38 rows at **42.3%** — *nearly 18 points of
"improvement" bought by withdrawing two rows*, which is precisely what
`planning/HIGH_STAKES_ACCURACY.md` §5's **"no removing a case to go green"**
forbids. So the tier is reported twice, on adjacent lines:

```
  reconstructions:     n=38  mean 42.3% | median 30.1% | within 15%: 11/38
  ... retired held in: n=40  mean 60.0% | median 33.3% | within 15%: 11/40
  retired targets:     n=2   mean 397.2% at withdrawal  (expand_drug_negotiation, international_reference_pricing)
```

Neither figure is the tier on its own. Nothing about provenance changed:
both rows were `model_estimate` before the withdrawal and still are, because
provenance describes where the *withdrawn figure* came from, so
`published_entries` stays at **77/81** and `model_estimate_entries` at **4**.
`NON_PUBLISHED_BENCHMARK_IDS` is unchanged — it shrinks only by finding a
document, never by withdrawing a target.

**Two further candidates are named and not acted on**, `carbon_tax_50` (whose
target restates `climate.py`'s own calibration) and `eliminate_step_up` (whose
target is above an upper bound). Each would need the same signature.
`tests/test_target_retirement.py` pins the retired set to exactly these two, so a
third cannot arrive without someone editing that line and saying why.

#### The two OCACT payroll targets, said out loud

`ss_donut_250k` (-$2,700.0B) and `ss_eliminate_cap` (-$3,200.0B) are two of the app's six largest headline figures, two of the rows the scorecard reports at **0.0%**, and both are `secondhand`. This section says what they are. **No target moved and no constant was retuned to write it** (lane `planning/lanes/HSA_h13_payroll_targets.md`); the revisions, if any, are H9's.

**What OCACT actually publishes.** SSA's Office of the Chief Actuary scores both designs, on the intermediate assumptions of the **2025 Trustees Report**, in memoranda dated **6 January 2026** ([provisions affecting payroll taxes](https://www.ssa.gov/oact/solvency/provisions_tr2025/payrolltax.html); [run 415](https://www.ssa.gov/oact/solvency/provisions_tr2025/charts/chart_run415.pdf), [run 418](https://www.ssa.gov/oact/solvency/provisions_tr2025/charts/chart_run418.pdf), [category summary](https://www.ssa.gov/oact/solvency/provisions_tr2025/payrolltax_summary.pdf)). The undated `provisions/` path now says the category is being moved to a 2026 Trustees basis and is "not yet available", and points here:

| | `ss_eliminate_cap` | `ss_donut_250k` |
|---|---|---|
| Provision | **E2.1** — "Eliminate the taxable maximum in years 2026 and later, and apply full 12.4 percent payroll tax rate to all earnings. Do not provide benefit credit for earnings above the current-law taxable maximum." | **E2.5** — "Apply 12.4 percent payroll tax rate on earnings above $250,000 starting in 2026, and tax all earnings once the current-law taxable maximum exceeds $250,000. Do not provide benefit credit for additional earnings taxed." |
| OCACT run | 415 | 418 |
| Change in long-range actuarial balance | **+2.55% of payroll** | **+2.50% of payroll** |
| Change in annual balance, 75th year | +2.60% of payroll | +2.60% of payroll |
| Share of the shortfall eliminated | 67% long-range / 54% in the 75th year | 65% / 54% |
| Reserve depletion | 2034 → **2059** | 2034 → **2057** |
| Ten-year dollars | **none published** | **none published** |

That last row is the finding, and it is checkable three ways. OCACT's *Detailed Single Year Tables* for these runs are cost rate, income rate, annual balance and trust-fund ratio, every column **expressed as a percentage of current-law taxable payroll**, year by year to 2100. The only `$` anywhere in run 418's table is inside the words "$250,000" in the provision text. And across the **whole six-page category summary** for provisions affecting payroll taxes — every E1, E2 and E3 provision, not just these two — the words "billion" and "trillion" **do not appear once**, and every `$` figure in it is a threshold inside a provision description. There is no dollar amount at any horizon, so "-$3.2T / -$2.7T (Social Security Trustees)" is a conversion the cited source never performed.

**Where the dollars do come from.** The Peter G. Peterson Foundation's explainer *[Social Security Reform: Options to Raise Revenues](https://www.pgpf.org/article/social-security-reform-options-to-raise-revenues/)* (last updated 7 March 2025) writes, of the $250,000 design, "According to the Trustees' projection, that option would raise **$2.7 trillion over 10 years**" — no report year, no run number, and no window. That is the repository's figure exactly. Two things about it are worth recording. First, the same page's cap-elimination sentence reads "**$3.4 trillion** over 10 years (2026 to 2035) — or close 48 percent of the 75-year funding gap", which is neither the repository's -$3.2T nor the 2025-basis E2.1 (67%); so the explainer's numbers are keyed to an older Trustees edition it does not name. Second, both PGPF sentences describe variants that **do** credit the newly taxed earnings toward benefits ("part of benefit calculation"), where E2.1 and E2.5 explicitly do not. The -$3.2T matches nothing OCACT or PGPF prints, and its origin is still unlocated.

**Published ten-year dollar scores for the same two designs do exist**, and when this section was written neither was registered. **H9 has since adopted the first and refused the second** — see [New in H9](#new-in-h9--the-eighteen-targets-that-were-not-line_item) below; the two bullets are kept as written because they are the record of the hand-off:

- **The $250,000 donut.** CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557), **Option 62 alternative 2**, "Subject earnings greater than $250,000 to payroll taxes": **$1,426.8B over FY2025-2034**, report p. 73 / PDF p. 79, already transcribed with its annual path to [`cbo_options_2025_2034_alternatives.csv`](../fiscal_model/data_files/validation/cbo_options_2025_2034_alternatives.csv). That is **47% below** the carried -$2.7T, on this repository's own window, for the identical donut. The 2018 volume's $1,222.6B is the same design a decade earlier.
- **Cap elimination.** Tax Foundation, Alex Durante, *[Uncapping the Payroll Tax Would Be the Largest Tax Increase in Decades](https://taxfoundation.org/blog/save-social-security-payroll-tax-cap-proposal/)* (24 June 2026), scoring the Moreno-Warren proposal — "apply the payroll tax to all earnings above the cap, with no corresponding changes to benefits", which is E2.1's design: "It would raise **$3.2 trillion from 2027 through 2036 on a conventional basis** and $1.5 trillion after accounting for the negative economic effects." **This one is a trap dressed as a confirmation.** It agrees with the carried figure at the one significant figure it is stated to, on a window two years later, from an estimator this repository already names as the publisher of five other benchmark targets — and the repository's own number is a constant chosen to produce -$3.2T, so registering it would manufacture a row that reads about 0% and means nothing. It also post-dates the target by roughly a year, so it cannot be its provenance.

**Both published paths ramp; the module's does not.** OCACT's own E2.5 income-rate path rises **1.85% of payroll in 2026 to 2.50% by 2034** as the taxable maximum grows toward $250,000 and the hole closes, and CBO's annual path for the same donut rises **$122.0B in 2026 to $192.0B in 2034**. `create_ss_donut_hole` stamps a flat $270B a year, documented as a "window-average". E2.1's path *is* nearly flat (2.40% → 2.51%), so the shape problem belongs to the donut alone. This is `create_repeal_ptc`'s defect in a second module (PR #131): a fitted annual that reproduces a ten-year total while being wrong in every year of it. Sized on CBO's own path — hold its $1,426.8B ten-year total and a flat annual is $142.68B — the flat shape is **17.0% high in FY2026 and 25.7% low in FY2034**.

**What the model does with these targets, and what it returns without them.** `payroll.py`'s `BASELINE_WAGE_DATA` states its own arithmetic in the comments — `wages_above_cap_billions = 2_581.0  # 320 / 0.124` and `wages_250k_plus_billions = 2_177.0  # 270 / 0.124` — and the two factories stamp $320B and $270B a year. The target divided by ten, divided by the statutory rate, is the base; the base times the rate, times ten, is the score. **A `secondhand` target reproduced by a constant fitted to it is bookkeeping, not evidence**, and 0.0% is the arithmetic of that, not a measurement of agreement. The honest figures are the held-out ones, and they are good ones — `run_loo.py` withholds each case's own covered-wage anchor and refits it from the other two anchors' Pareto slope:

| Case | Carried target | By construction | Held out | Error vs by-construction |
|---|--:|--:|--:|--:|
| `ss_donut_250k` | **-1,426.8** (H9; was -2,700.0) | -2,700.0 | **-2,664.0** | **1.3%** |
| `ss_eliminate_cap` | -3,200.0 | -3,200.0 | **-3,319.5** | **3.7%** |

The donut's two columns stopped being the same number on 2026-09-09, which is why the caption on the results surface now carries both: `_PAYROLL_FITTED_TARGETS` pins `by_construction_10yr` and `carried_target_10yr` separately, and `test_pinned_targets_match_the_loo_suite` is what caught the divergence rather than letting the app go on calling -$2,700.0B "the carried target".

Those two figures now print on the results surface beside the shipped number (`payroll_fitted_target_caption` in `fiscal_model/ui/tabs/results_summary.py`), pinned rather than recomputed on a page render, with a drift test in `tests/test_payroll_target_caption.py` that fails if either stops matching the suite. They are still not an independent measurement of either reform: two of the three anchors the refit reads are themselves fitted, which is also why `validation/cbo_options.py` excludes CBO Option 62 from the Tier 1 battery for **leakage** rather than for missing machinery.

#### New in H9 — the eighteen targets that were not `line_item`

Lane `planning/lanes/HSB_h9_provenance.md` applied `PROVENANCE_wave4.md`'s per-target judgement to the **12 `secondhand` and 6 `model_estimate`** calibrated rows — the ones a Build package inherits the provenance of, because `deficit_target.build_catalog` quotes `CBO_SCORE_MAP.official_score` as a list price rather than model output. Each ended in exactly one of four states. **Every `model_10yr_billions` in the 81-row scorecard is byte-identical and every leave-one-out derivation is unchanged**; no constant was retuned and nothing was retired.

**Six revised** (five points and one range), **twelve examined-and-left** (nine new verdicts, two restated, and `biden_ctc_2021` **transcribed** without moving):

| Benchmark | Was | Is | Document | Err before → after |
|---|--:|--:|---|---|
| `ss_donut_250k` | -$2,700.0B | **-$1,426.8B** | CBO pub. **60557**, Option 62 alternative 2, "Subject earnings greater than $250,000 to payroll taxes", report p. 73 (PDF p. 79) | 0.0% → **89.2%** |
| `tcja_rates_only` | +$3,185.0B | **+$2,158.7B** | CRS **R48286** Table 1, "Reduced Individual Tax Rates", transcribing CBO 60114's JCT row "10%, 12%, 22%, 24%, 32%, 35%, and 37% income tax rate brackets" | 2.2% → **44.3%** |
| `eliminate_estate_tax` | +$350.0B | **+$407.2B** | Tax Foundation, *Options for Reforming America's Tax Code 3.0* (July 2026), Option 83, printed p. 105 | 0.0% → **14.0%** |
| `repeal_ira_credits` | -$783.0B | **-$851.0B** | William McBride, Tax Foundation testimony to the House Committee on Oversight and Government Reform, 20 May 2025 | 0.0% → **8.0%** |
| `trump_china_60` | -$500.0B | **-$650.0B** | CRFB, *Options to Raise Tariff Revenue* (17 Dec 2024), row "60% Import Tariff on Chinese Goods", conventional | 44.3% → **57.2%** |
| `eliminate_mortgage` | -$300.0B | **range [-$495.0B, -$367.9B]**, anchor -$367.9B | Tax Foundation *Options 3.0* Option 25 (anchor); CRS **IF13190** Table 2 "Repeal MID $495" (the other bound) | 9.9% → **26.5%** |

**Five of the six make their row worse and one makes it far worse.** That is the shape a correct provenance pass has; if every revision improved its row the suspicion would be that the documents were chosen to fit. The exception is worth naming rather than glossing: `repeal_ira_credits` goes 0.0% → 8.0%, and an **agency** figure existed that would have put it at 52.0% — JCT's JCX-7-23, Title III of H.R. 2811, NET TOTAL $515,078M. It was declined on scope, on two things printed on that document: footnote [1], "Estimates of outlay effects presently unavailable", on eleven of its lines, and items 11 and 12 reading "Presently Unavailable", which puts all three clean-vehicle credits outside the total. An acknowledged-incomplete total is a lower bound, and adopting a lower bound as a point target would measure the missing lines. It is recorded in that row's `alternatives`.

**The Social Security donut is the largest single move the ledger has made, and H13's section above is the record of why.** CBO scores the identical design — *"The second alternative would apply the 12.4 percent payroll tax to earnings over \$250,000 in addition to earnings below the maximum taxable amount under current law… the gap between the two would shrink"*, and *"The current-law taxable maximum would still be used for calculating benefits, so scheduled benefits would not change under this alternative"*, which is OCACT E2.5's "do not provide benefit credit" — at **47% below** the figure the app had been printing. The 0.0% it replaces was `payroll.py`'s own arithmetic in its own comment (`2_177.0  # 270 / 0.124`). Two wedges are stated rather than adjusted: CBO's table note says an income-and-payroll-tax offset has been applied and the module has no such channel, and footnote *a* about added benefit outlays is attached to **alternative 1 only**, so the wedge that separates `ss_cap_90_pct`'s revenue and deficit lines does not exist here.

**`ss_eliminate_cap` was left, and the ledger's own arithmetic is why.** Tax Foundation's June 2026 *Uncapping the Payroll Tax* scores this design — "no corresponding changes to benefits" — at "\$3.2 trillion from 2027 through 2036 on a conventional basis". That is **-\$3,200.0B to the digit the document states**, which is exactly the carried figure, so `target_revision_problems` rejects it: *"superseded without changing the figure; a revision that restates the old target is noise."* Recording it as a **confirmation** instead would assert that a constant documented as the "window-average of Trustees \$3.2T over 10yr" had been validated by a document published eighteen months later, on a window this repository does not use, at one significant figure — the failure `repeal_individual_amt` refuses TPC T25-0049 for.

**One claim this repository had been making needed narrowing.** "OCACT publishes no ten-year dollar amount for any payroll provision" is true of the *provisions* tables and false of the office: OCACT's letter on the Medicare and Social Security Fair Share Act (11 July 2023, to Sen. Whitehouse and Rep. Boyle), Table 1b.n, prints "Total 2023-2032" = **\$3,035.1B in nominal dollars** — for a **\$400,000** donut with no benefit credit and, unlike CBO, no income-tax offset. A different threshold, so a line item for neither payroll row, but the sentence is corrected in `benchmark_sources.py`.

**`eliminate_mortgage` re-opened a Wave 4 verdict, because a document contradicted its premise.** That verdict rested on the two ten-year figures then known coming "from the same simulator and differ[ing] by 2.4×". Tax Foundation's July 2026 guide supplies a third from an independent general-equilibrium model, and the 2.4× resolves as a **baseline** gap: Yale's "close to \$1.2 trillion" is scored against **pre-P.L. 119-21** current law, where TCJA's larger standard deduction lapses and the itemising population roughly doubles, while CRS's \$495B and Tax Foundation's \$367.9B are both post-OBBBA. Two independent models, one baseline, **35% apart** — which is what the range rule above is for. The model's -$270.3B sits **$97.6B outside** the nearer bound, so the 26.5% this row reports against the anchor is a distance from one modeller's point rather than a measurement of accuracy; read `within_published_range` (False) and `distance_to_published_range_billions` (97.6) instead.

**Counts.** Provenance across both tiers goes `line_item` 51 → **57**, `line_item_differs` 7 → **8**, `secondhand` 17 → **12**, `model_estimate` 6 → **4**; in the calibrated tier alone, 30 → **36**, 7 → **8**, 12 → **7**, 6 → **4**. Published targets **75 → 77 of 81**, transcribed **36 → 43**, `revised_target_entries` **16 → 22**. `line_item_differs` rising is permitted only with a recorded range or scope verdict, and here it is a recorded **range** verdict.

**Both tiers moved and neither move is accuracy — read all five readings or none.**

| | Before | After |
|---|---|---|
| Fitted | 21 @ **1.73%**, 21/21 within 15 | **16 @ 1.51%**, 16/16 |
| Fitted, ledger rows held in place | 27 @ 5.6% | **27 @ 11.9%**, 22/27 |
| *The 21 rows the fitted tier held, on the new targets* | 1.73% | **9.82%**, 18/21 |
| Reconstructions | 34 @ **57.88%** (median 34.18), 9/34 | **39 @ 55.46%** (median 29.94), 11/39 — and **39 @ 56.7%** (median 36.9), 10/39 after Wave C's PR #150 moved the five trade rows |
| *The same 34 rows, on the new targets* | 57.88% | **58.26%** |
| Leave-one-out suite | 30.1% / 19.1%, 8/18 | **35.7% / 29.1%**, 6/18 |

The fitted mean falls because the five rows that left it averaged **2.42%**, above the tier's own mean. The reconstruction mean falls because the five arrivals average **36.42%**; on a constant population the tier gets **worse**, 57.88% → **58.26%**, and the whole 0.38pp is `trump_china_60`. **The one reading that is not composition is the third**: the 21 rows the fitted tier held before this pass, scored on the targets it leaves behind, read **9.82%** rather than 1.73% — that is what five untraceable targets were worth to the tier's headline. Leave-one-out moved for the same reason and no other: six lines of `run_loo.py --donor-matrix` differ and every *derived* figure in them is identical, exactly as PR #107.

**Retirement now exists as a state, and owner decision ④ has since applied it to exactly the two rows this pass recommended** (see [Retired targets](#retired-targets--the-first-two-withdrawals-and-the-second-reading-they-come-with)). `CalibratedTarget` gained `retired` / `retired_reason` — the third thing, distinct from a supersession (which has a replacement) and an examined-and-left verdict (which keeps the carried figure as a target). It is built so it cannot be used to go green: the row **keeps its scorecard entry and its model figure**, `ScorecardSummary.retired_target_entries` counts it, `check_readiness.py` lists it, and it leaves the reconstruction mean **only alongside a second reading** that folds it back at the error it carried when withdrawn. Both print on adjacent lines. The two pharma illustrations were the recommendation, and the arithmetic this pass predicted is what landed: on the retirement's own branch **39 @ 56.5% → 37 @ 38.1%** with **2 @ 397.2%** retired, and **40 @ 55.5% → 38 @ 37.5%** on the merged tree, where PR #157 moved `cap_charitable` into the count in the same window — 18 points of "improvement" bought by withdrawal. (The figures quoted here while the decision was open were 39 @ 55.46% → 37 @ 36.99% on the pre-Wave-C tier; PR #150's tariff rows moved the tier underneath them.) The decision was the owner's, not a lane's.

**Five preset labels quoted a superseded figure and were not renamed by this pass**, because labels are `CBO_SCORE_MAP` keys owned by a different lane. **The 2026-09-11 label-figure lane renamed all five**, reading each figure from the ledger: `💰 SS Donut Hole $250K (-$2.7T)` → **(-$1.43T)**, `🏠 Eliminate Estate Tax ($350B)` → **($407B)**, `📋 Eliminate Mortgage Deduction (-$300B)` → **(-$368B)** (the range's anchor, on the convention `🏭 Reciprocal Tariffs (-$1.5T)` already sets), `🏭 Trump 60% China Tariff (-$500B)` → **(-$650B)**, `🌱 Repeal IRA Clean Energy Credits ($783B)` → **(-$851B)**. The last of those was quoting `model_10yr_billions` rather than any target, and with the wrong sign. `_LABELS_QUOTING_A_SUPERSEDED_FIGURE` is now empty and the test asserts the emptiness; stable ids did not move and every old spelling still resolves. The figures themselves moved with H9, so a Build package containing any of them already showed a different total before the rename.

#### New in Phase D — P.L. 119-21 provision line items (the first sourced block)

This is the **first sourced line-item block in the calibrated tier**. Every other
calibrated target here is a rounded headline figure or a model estimate; these
eight are individual rows of a published JCT table, transcribed with page
references into
[`fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`](../fiscal_model/data_files/validation/pl119_21_jct_line_items.csv)
by [`scripts/extract_pl119_21_line_items.py`](../scripts/extract_pl119_21_line_items.py),
which verifies every transcribed total against the PDF text (34 of 34 found
verbatim).

**Source.** Joint Committee on Taxation, **JCX-35-25** (1 July 2025), estimated
revenue effects of the tax provisions in Title VII of the Senate substitute,
against a present-law baseline. JCT published no separate "as enacted" document
for the tax title, and the House passed the Senate substitute unamended, so
JCX-35-25's Title VII text *is* the text enacted as P.L. 119-21 on 4 July 2025.
(JCX-34-25 scores the same provisions on a *current policy* baseline; JCX-36-25
and JCX-37-25 are distributional.) Cross-check: JCX-35-25's net total,
-$4,474,972M, matches the "$4.5 trillion decrease in revenues" in CBO's companion
estimate, [publication 61570](https://www.cbo.gov/publication/61570), which
scores the law against CBO's **January 2025** baseline — the vintage these
provisions are scored on, and the reason that vintage was sourced from CBO's own
tables in Phase D (see below).

**Nothing is fitted to these rows.** `TCJAExtensionPolicy` carries a single
calibration factor fitted to CBO's $4.6T *aggregate*; no constant anywhere is
fitted to an individual JCT provision. So all eight report
`calibrated_to_target=False` and sit in the unfitted-reconstruction tier. The
question they answer is: can a module tuned on one aggregate also decompose?

| Provision (JCX-35-25 item) | JCT | Model | Error | Rating |
|---|---:|---:|---:|---|
| Extension of reduced rates (1) | +$2,193.4B | +$2,752.8B | 25.5% | Poor |
| Increased standard deduction (2) | +$1,424.7B | +$1,078.9B | -24.3% | Poor |
| Termination of personal exemptions (3) | -$1,807.1B | -$989.0B | 45.3% | Poor |
| Increased child tax credit (4) | +$816.8B | +$863.3B | 5.7% | Good |
| Section 199A deduction (5) | +$736.5B | +$1,123.9B | 52.6% | Poor |
| Estate and gift exemption (6) | +$211.7B | +$195.2B | -7.8% | Good |
| AMT exemption (7) | +$1,362.8B | +$719.3B | -47.2% | Poor |
| SALT limitation (20) | -$946.2B | -$1,685.8B | -78.2% | Poor |
| **Mean absolute error** | | | **35.8%** | 2/8 within 15% |

**Scoring window.** The scorer's baseline window is JCT's own — **FY2025-2034** —
and the policy takes effect in FY2026, so `Policy.is_active()` leaves FY2025 at
zero, which is what JCT prints for most of these rows. An earlier revision of
this branch built the scorer at 2026, which silently replaced JCT's zero-effect
2025 column with a tenth year of effect in 2035 and inflated every row; the
correction moved the block's mean from 41.8% to 35.8% and made three rows
*worse*, so it is a window fix rather than a fit.

**The headline finding: the module reproduces the aggregate to 0.4% and its own
components to 36%.** Every error carries a structural reason in
`known_limitations`, and nothing was retuned. The largest, SALT at 78%, is a
declared design mismatch rather than calibration drift: P.L. 119-21 sets a
$40,000 cap phasing down above $500,000 of income and reverting to $10,000 after
2029, while the module's SALT component represents the flat $10,000 cap, which
raises far more revenue. The largest *understatement*, AMT at 47%, is the mirror
image: P.L. 119-21 also lowers the phaseout thresholds and raises the phaseout
rate, both of which raise revenue relative to a plain extension, and the module
carries one aggregate annual with no phaseout structure at all.

**Twenty further provisions are recorded `out_of_scope` with a reason and never
scored** — tips, overtime, car-loan interest, Trump accounts, full expensing,
section 174, section 163(j), the foreign tax credit, the FDII/GILTI successor
deduction, BEAT, and every energy-credit termination. Two of those reasons are
worth stating:

- **The energy-credit terminations are excluded for leakage, not for a missing
  feature.** The climate module *could* score them, and must not: its IRA-repeal
  annual is documented as calibrated to reproduce the -$783B IRA-repeal target,
  so an energy-credit repeal scored through it would be a constant meeting the
  same reform that set it. That is the third instance of this pattern, after
  Phase B's Options 53, 56 and 62 — of which **Option 56 is no longer one**,
  because lane L6 removed the fitted annual its only path ran through and PR #100
  promoted it into Tier 1. A leakage exclusion lapses when the leak is closed.
- **The senior deduction has no JCT line of its own.** JCT nets it inside item 3
  ("Termination of deduction for personal exemptions *other than temporary senior
  deduction*"), so there is no row to score it against. Recorded rather than
  invented.

**Baseline vintage.** `BaselineVintage.CBO_JAN_2025` was a 0.5/0.5 interpolation
between the February 2024 and February 2026 assumption sets, and carried no base
levels at all — it fell through to the February 2026 fallback. Phase D replaced
it with figures transcribed from CBO, *The Budget and Economic Outlook: 2025 to
2035* ([publication 61172](https://www.cbo.gov/publication/61172)) and its
supplemental data (publication 60870): the economic forecast for calendar
2025-2034, and FY2025 base levels from baseline tables B-1 and B-4. One number is
derived rather than transcribed and says so — CBO's abbreviated January 2025
report publishes no defense/nondefense split of discretionary *outlays*, so the
$1,847.9B total is divided in the Table B-5 budget-authority ratio (47.25 /
52.75). The interpolation is kept and kept callable as
`interpolated_jan_2025_assumptions()`, the documented fallback, and
`VINTAGE_SOURCING` records which of the two is in force so a report cannot
overstate the provenance. `tests/test_baseline_vintage.py` pins that the vintage
is `sourced`. Sanity check: the generated FY2025 deficit is $1,868B against CBO's
own $1,865B.

Consistent with Phase B's finding, **vintage matching does not move these eight
scores either** — `TCJAExtensionPolicy` builds its path from component annuals
and never reads a level off the baseline. The value is in the manifest being
true, not in the number changing.

#### New in Phase E — sectoral module reconstructions

Every target below is read live from `CBO_SCORE_MAP`; none is restated in the validation layer. Rows marked **(fitted)** carry a module constant calibrated to the figure, so their low error is bookkeeping.

| Family | Policy | Official | Model | Error | Rating | Provenance |
|---|---|---:|---:|---:|---|---|
| International | Biden GILTI reform | **-$373.9B** | -$230B | **38.4%** | Poor | line_item (**target revised** from -$280B) |
| International | Repeal FDII | **-$158.0B** | -$111B | **29.9%** | Poor | line_item (**target revised** from -$200B to the gross row) |
| International | Pillar Two adoption | -$80B | -$61B | 23.5% | Poor | line_item_differs (-$102.6B); **target is the range [-$102.6B, +$56.5B]**, model inside it, distance $0.0B |
| International | Biden international package | **-$632.2B** | -$354B | **44.1%** | Poor | line_item (**target revised** from -$700B) |
| Trade | Universal 10% tariff | **-$2,171.1B** | -$1,380B | **36.4%** | Poor | line_item (**target revised** from -$2,000B); unfitted since L8; retaliation left the score in PR #150; offset on JCT's own year path since PR #164 |
| Trade | 60% China tariff | **-$650B** | -$334B | **48.7%** | Poor | line_item (**target revised** to CRFB's -$650B in PR #145); unfitted since L8 |
| Trade | 25% auto tariff | **-$386.2B** | **-$576B** | **49.2%** | Poor | line_item (**target revised** from -$100B, a per-year claim in a ten-year column). **PR #164 moved the base to CBO's own HS-10 vehicle and parts lists and the USMCA carve-out to US content only** ($41.0B, not the ~$186B a whole-value 48.42% removed), so the row crossed its target: 47.2% under → 49.2% **over** |
| Trade | 25% steel/aluminium tariff | -$60B | **-$215B** | **258.1%** | Poor | secondhand (**examined and left twice**: the 25% rate lasted ten weeks and nobody scored it). **This movement measures nothing about the score** — PR #164 replaced two whole HS chapters with CBO's own HS-10 Section 232 annex ($108.4B → **$219.4B**) and the target it is measured against is a repository artefact. A test asserts the score stays above $200B so it cannot drift toward it |
| Trade | Reciprocal tariffs (~20pp) | -$1,500B | -$1,655B | **10.3%** | Acceptable | line_item_differs; **target is the range [-$1,800B, -$1,400B]**, model **inside it, distance $0.0B** — so the 10.3% is a distance from one modeller's point rather than a measurement of accuracy |
| Pharma | Expand drug negotiation | -$500B | **-$34B** | **93.3%** | Poor | model_estimate; **moved 25.7% → 93.3% in Wave 4, by design** (see below) |
| Pharma | Universal insulin cap | **+$11.4B** | **+$7B** | 39.0% | Poor | line_item (CBO 57957; target revised from -$15B) |
| Pharma | International reference pricing | -$100B | **-$801B** | **701.0%** | Poor | model_estimate; **moved 646.2% → 701.0% in Wave 4, by design** (see below) |
| Enforcement | IRA enforcement funding | **-$180.4B** | -$189B | **4.7%** | Good | line_item (**target revised** from -$200B, which sat 2% below a figure CBO had withdrawn); **unfitted since Wave 4** |
| Enforcement | Double IRS enforcement | -$340B | -$60B | 82.3% | Poor | line_item_differs (-$320.0B, on half the funding); **examined and left** |
| Climate | Repeal IRA clean-energy credits **(fitted)** | -$783B | -$783B | 0.0% | Excellent | secondhand (**cited CBO document not located**) |
| Climate | Carbon tax $50/ton **(fitted)** | -$1,700B | -$1,715B | 0.9% | Excellent | model_estimate |
| Climate | Repeal EV credits | **-$182.3B** | -$228B | **25.3%** | Poor | line_item (**target revised** from -$200B; JCX-35-25 secs. 30D + 45W, and the source had been mislabelled CBO) |

**Two pharma rows got worse in Wave 4 and the lane reports it rather than
smoothing it.** PR #109 built the three federal Part D channels the 2023
aggregate had been standing in for (direct subsidy 0.3727, reinsurance 0.1047,
low-income subsidy 0.2986, federal total **0.7760** against the aggregate's
0.7626), a negotiation ladder fitted to all three published CMS cycles (scale
16.614, exponent 0.6316, reproducing $56.2B / $41B / $27B to within 2.1%), and a
RAND-sourced coverage restriction. Two of those three landed within $3B of the
pre-registered prediction. What the pre-registration did not anticipate is that
the lane's **own** ladder condemned a constant the reference-pricing leg also
reads: `medicare_part_d_gross_spending_billions = 220.0` was unsourced, and
current law's 160 cumulative selections carry **$256.8B** of gross Part D
spending by 2034, which does not fit inside a $220B total. CMS's own sentence —
$56.2B is "about 20 percent of total Part D gross spending in 2023" — puts the
total at **$281B**. The re-source is forced by the lane's mechanism rather than
chosen, and a test now pins the contradiction so it cannot come back. **The
alternative was to keep an unsourced number because it flattered the prediction,
which is the thing the pre-registration protocol exists to stop.** The
negotiation row's own slip is smaller and separate: the hand calculation ran the
selection-cap expansion across the whole window, and the code cannot, because an
expansion of the *annual* cap has nothing to raise until 2029 — before then the
statute names the count outright (10, then up to 15, then up to 15), so the
expansion bites in 6 of 10 years. Neither target moved in that lane, and the -$500B question it
left open has since been answered: owner decision ④ **retired** it, and the
reference-pricing target with it. The insulin row is unchanged to the cent.

**A correction behind the numbers that moved no benchmark.** `CBOBaseline`'s
corporate receipts line was set to 18% of the latest IRS SOI individual income
tax and grown at **4.88%/yr** against CBO's own **1.21%/yr** over the same
window, and neither term took a vintage — so under `use_real_data=True`, the
app's default, all three vintages started from **$386.62B to the cent** while
`use_real_data=False` returned three different, vintage-specific figures, the
two modes disagreeing by 8.6% on February 2026 and 35.5% on January 2025.
PR #130 made February 2024 **be** CBO publication 59710 Table 1-1 (read through
`fiscal_model.corporate`'s own loader, reproducing CBO's ten printed values
exactly), gave the other two vintages their own base year, and added
`CORPORATE_RECEIPTS_SOURCING` grading all three `published_path` /
`published_base_level` / `vintage_estimate` so a line this module reconstructed
cannot be reported as CBO's. **No benchmark reads that series** — the battery
is built on `CBO_FEB_2024` with `baseline_profits_billions` at its default — so
all 26 out-of-sample rows (22 since Wave E), both calibrated tiers, all 81 scorecard entries (77 since Wave E), the
LOO donor matrix, 53 presets and 16 Tailor combinations are byte-identical. What
moved is the baseline the app reports *about* the projection: the Ask tool's
ten-year deficit **$30,020.7B → $29,529.1B**, end-of-window debt/GDP
**104.8% → 103.8%**, Build's mean annual baseline deficit $3,002.07B →
$2,952.91B. The deficit moves further than the revenue does because of the
interest feedback — February 2026 gains $433.3B of revenue and loses $491.6B of
deficit, the $58.3B being interest not paid on debt not issued. The same
override is still live on the individual, payroll, other-revenue and spending
series, and `other_revenues` is byte-identical across all three vintages for all
ten years — the same defect with no growth-rule variation to hide it. Closing it
needs each vintage's own published tables, and cbo.gov returns HTTP 403 to this
environment (re-checked 2026-09-06, with no Wayback snapshot of either
workbook).

**Scope note**: Distributional validation is currently benchmarked mainly against published TPC tables rather than a broader CBO distributional set. Payroll / estate scenarios remain higher-error checkpoints; the Biden CTC revenue residual from double-counting growth on window-average annuals is closed (see [VALIDATION_NOTES.md](VALIDATION_NOTES.md)).

**Calibration / holdout note**: The live scorecard and API credibility blocks distinguish specialized calibrated benchmark paths, generic parameterized paths, and the locked post-change holdout protocol (`revenue-scorecard-post-lock-2026-05-02`). Holdout labels are future regression checkpoints, not retroactive historical out-of-sample claims.

### Tier 2 (leave-one-out) — the same modules, held out

The 1.7% above is a bookkeeping number: each calibrated module carries **one hard-coded annual per benchmark**, so it reproduces its own targets because it was told the answer. Leave-one-out asks the question that number cannot: *holding out one benchmark, can the module's structural machinery — calibrated on the others — rebuild it?* Live figures: `python scripts/run_loo.py` (add `--donor-matrix` for the capital-gains diagnostic).

| Module | Kind | n derivable | Mean abs error | Cases (LOO error) |
|---|---|---|---|---|
| **Payroll** | structural | 3 | **3.8%** | eliminate cap −3.7%; $250K donut +1.3%; 90% coverage +6.3% |
| **Estate** | structural | 2 | **10.4%** | extend TCJA exemption +19.2%; Biden $3.5M/45% −1.6% |
| **AMT** | structural | 2 | **73.9%** | extend TCJA relief -37.0%; repeal individual AMT +110.9% |
| **Credits** | structural (CPS ASEC per-unit) | 3 | **18.5%** | Biden CTC 2021 −4.5%; CTC extension +19.0%; childless EITC −32.1% |
| **Expenditures** | bottom-up | 5 | **37.5%** | mortgage **+14.0%**; SALT-cap repeal −33.5%; SALT elimination +33.5%; charitable cap +13.1%; employer-health cap +93.2% |
| **Capital gains** | structural (frozen elasticities) | 3 | **39.6%** | CBO +2pp −14.0%; PWBM with step-up −28.4%; PWBM no step-up +76.5% |

| Aggregate — derivable cases only | Value |
|---|---|
| Cases in aggregate | 18 |
| Not cross-validatable | 4 (reported alongside, never folded in) |
| Mean absolute error | **30.1%** |
| Median absolute error | 19.1% |
| Within 15% of official | 8/18 (44%) |
| CI ceiling (`--max-loo-mean-error`) | 75% |

**Wave 4 moved this suite 28.4% → 29.6% and every bit of the move is a *target*
movement, not a derivation one.** `run_loo.py --donor-matrix` differs from
pre-Wave-4 main in **exactly five lines**, and every derived figure in them is
identical: PR #107 moved three of the targets the suite scores against, and none
of the module machinery. `biden_eitc_childless` −38.0% → **−32.1%** (derivation
unchanged at 110.4), `repeal_salt_cap` −29.4% → **−33.5%** (777.0),
`eliminate_salt` +10.2% → **+33.5%** (−1,077.9). Per module that is `Credits`
20.5% → **18.5%** and `Expenditures` 30.2% → **35.7%**; Payroll, Estate, AMT and
Capital Gains are untouched, no donor-matrix entry moved, and `loo.py`'s leakage
guard was not touched and does not fire on any revised row — the revisions
removed the last constant that was a target restated, they did not create one.
Median and within-15% moved with the mean (16.5% → 19.1%, 9/18 → 8/18), for the
same reason.

**Wave 7 then moved the suite for the first time since, and this one *is* the
model — in the wrong direction, registered in advance.** PR #128 gave
`TaxExpenditurePolicy` a per-reform offset `direction` read off nine published
sources, and the one scored reform whose direction flipped is the mortgage
interest deduction (Poterba & Sinai, NBER WP 14253: $72.4B with no behavioural
response against $61.9B with portfolio adjustment, "about 85 percent").
`eliminate_mortgage`'s held-out score went −$315.3B (**−5.1%**) → −$257.9B
(**+14.0%**), `Expenditures` **35.7% → 37.5%** and the suite **29.6% → 30.1%**;
the median stayed at 19.1% and within-15 at 8/18. **The old −5.1% was two errors
cancelling**, which is why the lane registered the move as a regression rather
than defending the number: the held-out annual is JCT's $25.0B against the
fitted $26.2B, a static path **4.5% low**, and magnifying it by 10% put the
score **5.1% high**. Signing it correctly gives the base error *plus* the offset
instead of *netted against* it. Same shape as the Fiscal Responsibility Act's
spend-out finding in Wave 1: the flattering number was never evidence. The
leakage guard is untouched, `eliminate_step_up` is still excluded by it with the
same message, and no donor-matrix entry moved.

**And the module's six fitted constants turn out to disagree about whether the
convention exists at all**, which nobody had predicted and which anyone reading
a 0.1% row in this module should know. Reconstructing each annual against its
own growth rate over ten years, three were fitted so that the **static** path
hits the target (`eliminate_mortgage`, `repeal_salt_cap`, `eliminate_salt`) and
three so that the **magnified** score does (`cap_employer_health`,
`cap_charitable`, and neither for `eliminate_step_up`, which is 4.7% off). On
the three static-fitted rows the convention was therefore carried as **pure
error** — 10.1%, 5.0% and 5.1% — while the two magnified-fitted rows absorbed
it. That is why this module's fitted rows were never uniformly near zero the way
the rest of the tier's are. **Nothing was retuned**: re-fitting those three is
what the plan's own §1.1 forbids, and it would move `eliminate_mortgage` a
second time for a second reason in one PR.

**Wave 5 left the suite byte-identical**, and pointed at what it does not cover.
All three lanes worked at the Tier 1 margin: the payroll and capital-gains
factories that feed this suite pin their own annuals and elasticities, and the
corporate lane never enters it — because **there is no `Corporate` row in the
table above**. The suite holds Payroll, Estate, AMT, Credits, Expenditures and
Capital Gains, and the one module whose base constant was self-documented as
calibrated to its benchmark has never been cross-validated, which is exactly the
population `run_loo.py` exists to catch (PR #114 finding 5). Adding it means
editing `loo.py`, which no modelling lane may do; it is recorded as a carry-over
in `planning/MODELING_IMPROVEMENT.md` §6.2 rather than done.


**Wave 2 moved three modules and the case count.** `CapitalGains` **171.2% →
39.6%**: one frozen literature set replaced three hand-set tuples, the semi-log
form put the revenue-maximizing rate at 30.6% so a 43.4% rate *loses* revenue
while step-up survives — PWBM's own finding, reached with no multiplier, where
the old net-of-tax form gave a 370% sign flip. `Estate` **25.8% → 10.4%**: a
SOI-fitted Pareto size distribution replaced a two-point blend whose
count-times-average product was *exactly invariant* in the exemption, so
`biden_estate_reform` went +45.6% → −1.6% while `extend_tcja_exemption` got
*worse*, +6.0% → +19.2%, because its old 6% was a four-times-too-high level
cancelling against a zero exemption response. `Expenditures` **39.4% → 28.8%**:
declared cap units and SOI benefit distributions took `cap_employer_health`
97.4% → 93.2% (the row cannot reach its target — a $50,000 premium cap is above
the entire distribution; CBO's own 75th-percentile family premium is $31,300,
and the carried −$450B corresponds to a cap near $26,400) and `cap_charitable`
15.7% → 13.1%.

**Part of the Wave 2 suite improvement was a case leaving the denominator, and
Wave 3 put it back.** `eliminate_salt` was scoring +74.9% and was **excluded**
after L6 made `annual_cost_no_cap = 120.0` load-bearing and `loo.py`'s untouched
leakage guard saw that $120.0B is exactly the carried −$1,200B target over ten —
"the base constant is the answer key restated". PR #100 replaced that constant
with its **computation**: `uncapped_salt_expenditure_billions()` returns IRS SOI
Table 2.1's total (unlimited) SALT deduction, priced AGI class by AGI class at
the IRC §1 married-joint schedule as adjusted for 2025 (Rev. Proc. 2024-40) —
**$89.55B**. The guard stopped firing on its own; no per-case edit was made and
the guard itself was not touched. Two consequences, both of them predicted by L6
and both landing to the tenth:

- **`eliminate_salt` re-entered at +10.2%**, so the module cross-validates on
  five benchmarks again.
- **`repeal_salt_cap` moved +4.0% → −29.4%.** Its old +4.0% was never evidence
  of anything: it is `−(120.0 − 25.0)`, the same leaked constant under a
  different benchmark, and the guard missed it only because its target is
  $1,100B rather than $1,200B. Trading a flattering leaked number for an honest
  −29.4% is the trade the provenance lane exists to make.

The check that the derivation is not made up: the identical computation on SOI's
*limited* column returns **$25.0B** against the record's own `annual_cost = 25.0`
— two numbers with no common ancestor agreeing to a tenth of a percent. Both are
pinned in `tests/test_tax_expenditure_units.py`. The module mean moved
**28.8% (n=4) → 30.2% (n=5)**, and that *rise* is the honest reading.

**Wave 3's other LOO move was the credits module, 45.1% → 20.5%.** Lane L3
replaced `Δcredit × units × participation` with two parameter sets — the
counterfactual schedule and the reform schedule — each run through
`MicroTaxCalculator` on CPS ASEC tax units and differenced on final tax
liability. That prices the non-refundable leg's tax limit, the refundable leg's
earnings phase-in and the qualifying-age expansions the per-unit identity had no
place to put: `biden_ctc_2021` **−64.1% → −4.5%**, `ctc_extension` **−28.0% →
+19.0%**, `biden_eitc_childless` **−43.1% → −38.0%**. The dominant single
correction is not a parameter but a *counterfactual*: IRC §24's $2,000 reverts
to $1,000 after 2025, so a ten-year window opening in 2025 is scored against
current law for one year and the pre-TCJA regime for nine. Against a fixed
$2,000 baseline the ARP credit costs $883B; against the counterfactual the
statute specifies, $1,528B — more than 40 percentage points of that row.
`ctc_extension` moved *away* from its carried $600B target and *toward* the only
published line item for a comparable provision: JCT's JCX-35-25 row for
P.L. 119-21's child credit is **+$816.8B**, against which the fitted constant
reads −26.5% and the structural path **−12.6%**. Same shape as L5's AMT finding
and L6's SALT finding, and visible only because the carried target and the
document disagree.

**Before Wave 2 the LOO mean had moved twice, and neither move was the model.**
Wave 1's L5 lane took it 59.3% → 61.7% by replacing the AMT module's flat
steady-state identity (~$73B/yr) with TPC T25-0049's published year-indexed
path, which *raises* the derived score — see §6 of
[VALIDATION_NOTES.md](VALIDATION_NOTES.md) for why the plan's "missing 2026
ramp" hypothesis was wrong — so both AMT rows moved further from their carried
$450B targets (+73.2% → +90.1%, +86.0% → +110.9%). Correcting
`extend_tcja_amt`'s target to the published $1,357.1B then took it back to
58.7%: the held-out derivation is **unchanged at $855.3B** and only the figure
it is measured against moved, so that row reads **-37.0%** instead of +90.1% and
the AMT module reads 73.9% instead of 100.5%. Wave 2's 58.7% → **32.3%** is the
first move that *is* the model — three modules rebuilt — with the case-count
caveat above attached. Wave 3's 32.3% → **28.4%** is two more modules and one
constant: the credits rebuild is model, the SALT derivation is provenance, and
they pull in opposite directions. Wave 3's 28.4% → Wave 4's **29.6%** is
provenance alone: three targets moved and no derivation did. Wave 7's
**29.6% → 30.1%** is the reverse of that and the first move here that is the
model getting worse on purpose: one reform's offset direction was read off its
source, and the row it moved had been reading well because two errors cancelled. The AMT module is
unchanged to the decimal through all of it.

**Read the five numbers separately and never collapse them**: Tier 1 out-of-sample (**11.8%** mean / 8.9% median, n=**22** pre-registered; 17/22 within 15%, 19/22 within 25%, and itself eight policy classes running 4.6% to 44.5%), Tier 2 by construction (**1.6%**, n=15 fitted — or **12.4% over 26** with the rows a target revision moved out held in place, which is the reading `run_validation_dashboard.py` computes since PR #130; a row moved out by *reclassification* rather than by a revision is deliberately not folded back), Tier 2 unfitted reconstructions (**37.5%** mean / 30.1% median, n=38, none fitted to their target — **and never without the 40 @ 55.5% beside it**, which is the same tier with the two targets owner decision ④ withdrew put back at the error they carried), the **2 retired targets at 397.2%**, and Tier 2 leave-one-out (**36.5%** / 30.2% median, n=18 derivable, 5/18 within 15%). **Tier 1's n is now a number to read as carefully as its mean**: it fell 26 → 22 in Wave E because four targets were found to be in no publication, so 14.5% → 11.6% is mostly a smaller battery — the **share** within 25% rose 84.6% → 86.4% while the **count** fell 22 → 19, and a smaller battery is a weaker test however well it scores. **Three of those four moved in Waves A/B and only the first moved on the model**: PR #145 revised six calibrated targets and left all 81 `model_10yr_billions` byte-identical, so the fitted tier fell 1.73% -> 1.51% because the five rows that left averaged **2.42%**, the reconstruction tier fell 57.88% -> 55.46% because the five arrivals average **36.42%** — and **on a constant population it got worse, 57.88% -> 58.26%**, all 0.38pp of it `trump_china_60`. The single honest number for what the new targets did to the model's measured error is that **0.38pp, against 2.42pp of composition**; and the one reading that is not composition at all is that **the 21 rows the fitted tier held before Wave B, scored on the targets it leaves behind, read 9.82%, 18/21 within 15%**. Leave-one-out is the same mechanism a third time: `--donor-matrix` differs in six lines, every *derived* figure in them is identical, and `Payroll` 3.8% -> **32.3%** and `Expenditures` 37.5% -> **40.6%** are two targets moving underneath unchanged machinery. The last two are the honest statement of how much of the calibrated tier is structure and how much is a stored constant. **Both Tier 2 tiers changed population again in Wave 4, and both means fell while nothing improved, so the constant-population comparisons belong next to them**: the reconstruction tier reads **65.7% / 40.5% over the 26 rows it already held** (against 61.8% / 38.0% before — it got *worse*), and its sectoral subset **88.2% over the 14 it held** (against 81.0%). The leave-one-out suite is the reverse case: it *rose* 28.4% → 29.6% without a single derivation moving. **Wave 5 moved none of these three**: its lanes all worked at the Tier 1 margin, so the fitted 23 stayed at 1.6%, the 31 reconstructions at 56.6% / 29.9% and `run_loo.py --donor-matrix` was byte-identical — 0 of 23 and 0 of 31 scorecard rows changed, a falsification test each lane registered in advance. **PRs #119-#122 moved the two calibrated tiers by composition and the leave-one-out suite not at all**: `--donor-matrix` was still byte-identical, checked independently on all four branches. **Wave 7 broke both of those streaks, in opposite directions and each for a stated reason.** PR #131 moved the reconstruction tier **57.6% → 57.9% on accuracy** — the same 34 rows either side, one of them a registered regression — and PR #128 moved the leave-one-out suite **29.6% → 30.1%**, also registered, on `Expenditures` **35.7% → 37.5%**: giving the expenditure module a per-reform offset direction took `eliminate_mortgage`'s held-out score from −$315.3B (−5.1%) to −$257.9B (+14.0%), because the old −5.1% was two errors cancelling — the held-out annual is JCT's $25.0B against the fitted $26.2B, a static path 4.5% low, and magnifying it by 10% put the score 5.1% high. **No donor-matrix entry moved**, so every per-module figure below except `Expenditures` is the one Wave 4 left. What Wave 5 added to this list was a **gap in the leave-one-out suite itself** — it holds Payroll, Estate, AMT, Credits, Expenditures and CapitalGains and has **no `Corporate` row at all**, so the one module whose base constant was self-documented as calibrated has never been cross-validated. **PR #120's memo answered that, and the answer is `no`, with `loo.py` not the thing stopping it**: the module has one fitted constant and had two benchmarks, one of them its own output, so re-deriving the base from it would reconstruct the constant from itself — the leakage `LEAKAGE_TOLERANCE` exists to catch, and `not cross-validatable` is the honest outcome. **PR #122 shipped the substitute the memo named**: `biden_corporate_28_fy2022`, a second *published* target the module is not fitted to and never will be. The module now has two published benchmarks and one fitted constant, and still nothing cross-validating either — which is a smaller gap, honestly stated, rather than a closed one.

And read all four alongside the provenance split above, because a percentage error is only as meaningful as the target it is measured against: **5 of the 54 calibrated targets still disagree with the document they cite**, down from 13, and every one of the 5 now carries a written verdict (two range revisions with in-range anchors, three examined-and-left). **15 have been corrected** rather than carried — two of them to a *range* rather than a point. None disagrees in sign any more.

Four cases are **not cross-validatable** and carry a reason rather than a manufactured number: `expand_niit` (the module's only NIIT benchmark — nothing to calibrate the mechanism on), `eliminate_estate_tax` (the target is not a published score), and `repeal_corporate_amt` and `eliminate_step_up` (the base constant *is* the published target restated; a leakage guard in `loo.py` catches this mechanically). `eliminate_salt` was a fifth between Wave 2 and Wave 3 and is derivable again, for the reason above. `eliminate_estate_tax`'s exclusion is now carried on **one** ground rather than two: it used to cite both an unpublished target *and* machinery that "reproduces differences but not revenue levels", and the second is no longer true — L4's model puts 2026 estate revenue at **$47.6B** against CBO's carried ~$50B, where the old machinery implied $195.9B. See [VALIDATION_NOTES.md](VALIDATION_NOTES.md) §6 for the per-module classification and what each error diagnoses.

---

## Validation Results by Policy Category

### 1. Income Tax Policies (Generic / out-of-sample path)

These rows are the **uncalibrated** bottom-up Generic scorer (`create_policy_from_score` → IRS SOI auto-pop). They are *not* hand-tuned reconstructions.

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| Medicare surcharge 2pp (>$400K) | -$310B | -$315B | 2% | Excellent | Treasury |
| 1pp all brackets | -$960B | -$935B | 3% | Excellent | JCT |
| 5pp top rate ($1M+) | -$700B | -$648B | 7% | Excellent | TPC |
| 2pp rate cut ($500K+) | +$400B | +$364B | 9% | Good | TPC |
| Biden $400K+ (2.6pp) | -$252B | -$284B | 13% | Acceptable | Treasury |
| Warren surtax 3pp (AGI >$2M) | -$350B | -$284B | 19% | Acceptable | TPC |
| Biden cap gains 39.6% + gains at death | -$456B | -$817B | 79% | Poor | Treasury |
| Top rate to 45% (+8pp) | -$420B | -$916B | 118% | Poor | TPC |
| Treasury 39.6% + step-up repeal | -$322B | -$817B | 154% | Poor | Treasury |

The three `Poor` rows are documented misses, not omissions — see the Tier 1 tail discussion above.

**Methodology Notes**:
- Uses IRS SOI data for taxpayer counts and income distributions
- Dispatch is on the record's *shape* (ordinary rate / capital gains / corporate rate / spending), not on a single `policy_type`; every `KNOWN_SCORES` record is either runnable or carries an explicit `runnable=False` reason
- Capital-gains cases use ONE frozen elasticity set (module defaults, short-run 0.8 / long-run 0.4), never the per-case tuples in `scenarios.py`
- Ordinary-bracket changes default to `ordinary_income_base=True` (exclude LTCG/QDIV)
- All-brackets (`threshold=0`) scored from total SOI taxable income, not `baseline × Δrate/0.18`
- Elasticity of Taxable Income (ETI) = 0.25 (Saez et al. 2012)
- Behavioral offset = ETI × 0.5 × static effect (signed; erodes magnitude)

Earlier docs that showed Biden at ~1% / −$250B used a hand-tuned path — that is **not** the Generic prediction.

---

### 2. TCJA Extension

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Full TCJA Extension** | **$4,600B** | **$4,582B** | **0.4%** | **Excellent** | CBO |
| TCJA without SALT cap | $5,700B | $5,738B | 0.7% | Excellent | Estimated |
| TCJA rates only | $3,185B | $3,200B | 0.5% | Excellent | Model |

**Component Breakdown (Full Extension)**:

| Component | 10-Year Cost | Notes |
|-----------|--------------|-------|
| Rate cuts | +$1,800B | All bracket reductions |
| Standard deduction | +$720B | Doubled from pre-TCJA |
| Pass-through (199A) | +$700B | 20% QBI deduction |
| Child Tax Credit | +$550B | $2K vs $1K baseline |
| AMT relief | +$450B | Higher exemptions |
| Estate exemption | +$167B | $14M vs $6.4M |
| **Subtotal (costs)** | **+$4,387B** | |
| SALT cap | -$1,100B | $10K cap on deduction |
| Personal exemption elimination | -$650B | Offset to std deduction |
| **Subtotal (offsets)** | **-$1,750B** | |
| **Calibration adjustment** | **+$1,963B** | To match CBO total |
| **Total** | **$4,600B** | |

**Key Insight**: CBO's baseline assumes TCJA expires after 2025. "Extension" is scored as a cost relative to that current-law baseline.

---

### 3. Corporate Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Biden 21% to 28%** (fitted) | **-$1,347B** | **-$1,293B** | **4.0%** | **Excellent** | Treasury FY2025 Green Book, `line_item_differs` (**scope**) |
| Biden 21% to 28%, FY2022 window (**not fitted**) | -$858B | -$1,293B | 50.7% | Poor | Treasury FY2022 Green Book p. 104 |
| Trump 21% to 15% (**not fitted**) | [+$595B, +$673B] | +$1,545B | 129.6% | Poor | PWBM Table 1 / Tax Foundation Table 2 (via CRFB) |
| TCJA corporate repeal | -$1,400B | -$1,350B | 3.6% | Excellent | JCT |

Three things about that table are the point of PR #122 and should be read together.
**First, the fitted row's 3.7% is measuring a scope mismatch as well as a fit.** Treasury's
*"Raise the corporate income tax rate to 28 percent"* row prints $1,349,941M and -$1,347B is
that figure rounded — the numbers agree. But from the **FY2023** edition onward the row's
own chapter says the GILTI effective rate moves with the statutory rate (*"The effective
global intangible low-taxed income (GILTI) rate would increase to 14 percent under the
proposal"*), while `create_biden_corporate_rate_only`, the factory scored against it, sets
`gilti_rate_change=0.0` and its own docstring says "No international changes - just rate".
**The target did not move, because there is nothing to move it to**: the GILTI leg's size is
never printed and is not recoverable by differencing editions (FY2022 excludes it; FY2023 is
on a Build Back Better baseline with a 20% GILTI rate; FY2024 and FY2025 route 21% → 14%
*through* the corporate row while a separate $373,919M international row takes 14% → 21%).
So the row became `line_item_differs` and `BenchmarkSource` grew **`scope_differs`** to say
why — see the label note below.

**Second, the FY2022 row is the module's answer to "can corporate be cross-validated?", and
the answer was no.** Leave-one-out holds out one benchmark's fitted constant and asks whether
the machinery calibrated on the *others* can put it back; corporate has one fitted constant
(`BASELINE_TAXABLE_PROFITS_BILLIONS`) and had two benchmarks, one of which was the model's own
output — so re-deriving the base from it would reconstruct the constant from itself. The
honest substitute is a **second published target the module is not fitted to**, and the FY2022
Green Book row is the only rate-only corporate row any Green Book prints: the word GILTI does
not appear in its two-sentence Proposal section, so its scope matches the factory's shape,
which is exactly what the FY2025 row does not. It was verified from Treasury's own PDF —
$857,817M, five-year subtotal $405,537M, annual path 51,127 / 86,182 / 88,059 / 89,385 /
91,784 / 92,065 / 90,730 / 89,357 / 88,798 / 90,330 ($M), digit-for-digit what
`corporate_rate_scores.csv` carries. Its per-point yield is **36% below** the FY2025 row's
($122.55B against $192.85B), which a vintage-anchored base could reproduce and a fixed base
cannot — **and since PR #166 that is a statement about `reported`, not about the app.** It read
"the module's answer to '21% → 28%' is the same -$1,397.2B whichever decade is asked about", which
is true of `reported`, whose rate channel prices against a fitted aggregate the engine grows from
the *policy's own* start year so a window shift cancels exactly, and **false of `derived`**, which
reads a fiscal-year-indexed path and answers **-$1,292.62B** on the validation window against
**-$1,310.92B** on the app's — $18.30B, entirely the decade. `CORPORATE_APP_MODE` is now `derived`,
so the vintage sensitivity this row was registered to expose is live rather than hypothetical. It is **never to be fitted** — a second constant fitted here would make the pair
uninformative — and its window offset is stated rather than adjusted (the target is
FY2022-2031 on a 2021 baseline and this repository carries no 2021 vintage, so it scores on the
corporate runner's FY2025-2034 window; in `reported` mode the rate channel is a flat annual, so
the offset changes which years the same number is stamped on and nothing else). **It is
deliberately not in `KNOWN_SCORES`, and that is a finding**: `assistant/benchmarks.py`'s
`candidate_anchors` turns every `KNOWN_SCORES` record with `policy_type="corporate_tax"` and
a non-zero `rate_change` into an interpolation anchor for the shipped Ask assistant, so adding
it would have put a 2021-vintage figure into the set a 2026 user's "what would +4pp raise?"
interpolates across, and quietly lowered the answer.

**Third, the Trump row's 129.6% is a distance from a document where 22.3% was a distance from
this model's own output, and about a third of it is scope.** *(It read 121.6% until PR #166 moved
the app and the scorecard onto `derived`; the figures below are `reported`'s and are kept because
the decomposition was measured on them.)*
`create_republican_corporate_cut` sets `extend_bonus_depreciation=True` and neither published
figure includes bonus depreciation — PWBM prints the business provisions separately at
-$623B — so the module's bonus-depreciation leg is **+$294.2B** of its +$1,491.8B and the
**rate leg alone reads +$1,197.6B, or +77.9%** against the anchor. It is not adjusted away:
summing two rows of PWBM's table would be constructing a target rather than reading one. Most
of the rest is a direction asymmetry the memo found — Tax Foundation's *Options 2.0* is the
only document pricing both directions in one edition and one model, 21%→28% at $126.6B per
point against 21%→15% at $163.2B, so a point of cut costs 29% more than a point of increase
yields, and `corporate.py` prices both at the same per-point rate.

**`cbo_opt64`'s estimator was corrected in the same pass**: it is a **JCT** estimate that CBO
publishes (every corporate-rate option in every *Options* volume carries "Data source: Staff
of the Joint Committee on Taxation" verbatim), so `ScoreSource.CBO` → `ScoreSource.JCT`.
Nothing in the scoring path reads `source` and no row moved. `preregistered.py` was **not**
touched: its `source_name` field is documented as "the source that published it", CBO did
publish it, and the manifest is append-only.

**Methodology Notes**:
- Corporate elasticity = 0.25
- Pass-through effects modeled (S-corps reclassify income)
- GILTI/FDII international provisions included

---

### 4. Tax Credits

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Biden CTC 2021 (permanent)** | **$1,600B** | **$1,600B** | **0.0%** | **Excellent** | CBO |
| CTC extension | $600B | $600B | 0.0% | Excellent | CBO |
| **Biden EITC childless** | **$178B** | **$180B** | **0.9%** | **Excellent** | Treasury |

**Methodology Notes**:
- Refundable credits treated as outlays
- Phase-in and phase-out modeled explicitly
- Labor supply effects included (elasticity 0.1-0.3)

---

### 5. Estate Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| Extend TCJA exemption | $167B | $184B | 10.2% | Good | CBO |
| **Biden reform ($3.5M, 45%)** | **-$450B** | **-$450B** | **0.0%** | **Excellent** | Treasury |
| Eliminate estate tax | $350B | $385B | 10.0% | Good | Model |

**Current Law Context**:
- TCJA exemption: ~$14M per person (through 2025)
- Post-sunset: ~$6.4M per person
- Rate: 40%
- Taxable estates: ~7,000/year under TCJA, ~19,000 after sunset

---

### 6. Payroll Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **SS cap to 90%** | **-$800B** | **-$800B** | **0.0%** | **Excellent** | CBO |
| **SS donut hole $250K** | **-$2,700B** | **-$2,700B** | **0.0%** | **Excellent** | Trustees |
| **Eliminate SS cap** | **-$3,200B** | **-$3,200B** | **0.0%** | **Excellent** | Trustees |
| **Expand NIIT** | **-$250B** | **-$220B** | **12.1%** | **Acceptable** | JCT |

**Methodology Notes**:
- Current law: 12.4% on wages up to $176K (2025)
- Model assumes 4%/year wage growth
- Systematic underestimate likely due to wage concentration assumptions
- Labor supply elasticity = 0.15

**Why 12% Error?** Payroll tax estimates depend heavily on the distribution of wages above the cap. Official estimates use detailed SSA data; our model uses Census-based approximations.

---

### 7. Alternative Minimum Tax

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Extend TCJA AMT relief** | **$450B** | **$451B** | **0.1%** | **Excellent** | JCT/CBO |
| **Repeal individual AMT** | **$450B** | **$451B** | **0.1%** | **Excellent** | CBO |
| **Repeal corporate AMT** | **$220B** | **$220B** | **0.0%** | **Excellent** | CBO |

**Key Parameters**:

| Parameter | TCJA (through 2025) | Post-Sunset (2026+) |
|-----------|---------------------|---------------------|
| Single exemption | $88,100 | ~$60,000 |
| MFJ exemption | $137,000 | ~$93,000 |
| Affected taxpayers | ~200,000 | ~7.3 million |
| Revenue | ~$5B/year | ~$60-75B/year |

Corporate AMT (CAMT): 15% book minimum tax on $1B+ corporations, ~$22B/year

---

### 8. Premium Tax Credits (ACA)

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Extend enhanced PTCs** | **$350B** | **$366B** | **4.6%** | **Excellent** | CBO |
| **Repeal all PTCs** | **-$1,100B** | **-$1,096B** | **0.3%** | **Excellent** | CBO |

**Key Parameters**:
- Enhanced PTCs (ARPA/IRA): 100%+ FPL eligible, 0-8.5% premium cap
- Original ACA: 100-400% FPL only
- ~22M marketplace enrollees, ~19M receiving PTCs
- Healthcare cost growth: 4%/year

---

### 9. Tax Expenditures

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| **Cap employer health** | **-$450B** | **-$450B** | **0.1%** | **Excellent** | CBO |
| Eliminate mortgage deduction | -$300B | -$330B | 10.1% | Good | CBO |
| **Repeal SALT cap** | **$1,100B** | **$1,156B** | **5.1%** | **Excellent** | JCT |
| Eliminate SALT deduction | -$1,200B | -$1,260B | 5.0% | Excellent | JCT |
| **Cap charitable at 28%** | **-$200B** | **-$201B** | **0.3%** | **Excellent** | Obama/Biden |
| **Eliminate step-up basis** | **-$500B** | **-$523B** | **4.7%** | **Excellent** | Biden |

**Major Tax Expenditures (JCT 2024 annual estimates)**:

| Expenditure | Annual Cost |
|-------------|-------------|
| 401(k) and DC plans | ~$251B |
| Capital gains/dividends | ~$225B |
| Employer health insurance | ~$250B |
| Defined benefit pensions | ~$122B |
| Charitable contributions | ~$70B |
| SALT (with $10K cap) | ~$25B |
| Mortgage interest | ~$25B |

---

### 10. Capital Gains

| Policy | Official Score | Model Score | Error | Rating | Source |
|--------|----------------|-------------|-------|--------|--------|
| CBO +2pp all brackets | -$70B | -$83B | 19% | Acceptable | JCT |
| PWBM 39.6% (with step-up) | +$33B | +$30B | 9% | Good | PWBM |
| **PWBM 39.6% (no step-up)** | **-$113B** | **-$113B** | **0%** | **Excellent** | PWBM |

**Critical Insight: Step-Up Basis**

The Penn Wharton analysis demonstrates a fundamental asymmetry:
- **With step-up**: 39.6% rate *loses* $33B (lock-in effect dominates)
- **Without step-up**: Same rate *raises* $113B (can't avoid by holding)

**Time-Varying Elasticity** (CBO/JCT methodology):
- Years 1-3: elasticity = 0.8 (short-run timing effects)
- Years 4+: elasticity = 0.4 (long-run permanent response)
- PWBM no-step-up validation applies a 1.5x residual avoidance multiplier to capture remaining threshold timing and business-form shifting after constructive realization at death.

---

### 11. Sectoral modules — international, trade, pharma, enforcement, climate (Phase E)

Seventeen presets across five modules, wired into the scorecard by
`fiscal_model/validation/specialized_sectoral.py`. The full row-by-row table
lives in the [Tier 2 section](#tier-2--calibrated-reference-models-reconstructions-not-confirmations)
above, because these entries are not comparable to the nine older suites: only
**two** of the seventeen still carry a module constant fitted to their
benchmark — L8 unfitted the two tariff rows and Wave 4's revision unfitted
`ira_enforcement` — and the other fifteen are
compared to a published figure nothing was fit to. Per-family diagnosis is in
[VALIDATION_NOTES.md](VALIDATION_NOTES.md) §7.

| Family | n | Fitted | Mean abs error | Worst case |
|--------|---:|---:|---:|--------|
| International | 4 | 0 | **34.0%** | Biden package **44.1%** (the module's UTPR returns $15B against Treasury's own $136.3B row) |
| Trade | 5 | **0** | **80.5%** | 25% steel/aluminium **258.1%** — a *registered regression* against an untraceable target; on the four rows that have a document the family reads **35.7%** |
| Pharma | 3 | 0 | **277.8%** | International reference pricing **701.0%** (RAND index on all brand spending; still no utilisation or launch-delay response) |
| Enforcement | 2 | **0** | 43.5% | Double IRS enforcement 82.3% (unfitted ROI and decay constants) |
| Climate | 3 | 2 | 8.7% | Repeal EV credits **25.3%**, against JCT's published -$182.3B |

Only **two** of the seventeen still carry a module constant fitted to their
benchmark — Wave 4's revision of `ira_enforcement`'s target unfitted a third.
**Quote the constant-population reading beside the unfitted subset's mean**: on
the fourteen rows it held before Wave 4 it is **88.2%**, because the pharma
rebuild moved two rows away from their targets.

**Trade moved twice, for opposite reasons, and only the second is about the
model.** In Wave 4 and Wave B its *targets* moved onto published documents. In
Wave C (PR #150) the **score** moved: `estimate_behavioral_offset` stopped
netting **retaliation**, which is in none of the five targets — all of them
conventional estimates — and the family went **34.2% → 43.6%**, registered as
worse in advance. Four of the five rows improve (`trump_universal_10`
42.03% → **36.91%**, `trump_china_60` 57.17% → **49.06%**, `auto_tariff_25`
52.81% → **47.20%**, `reciprocal_tariffs` 6.88% → **9.47%** while moving *inside*
its published range, distance $3.2B → **$0.0B**), and `steel_tariff_25` carries
the whole of the net at 11.89% → **75.28%** because its base now reaches the
Section 232 derivative chapter (1.84×, declared an upper bound) while its target
remains untraceable. **On the four rows that have a document the family improves
39.72% → 35.66%.** Two `TRADE_BASELINE` shape assumptions were also retired:
`reciprocal_coverage_rate = 0.50` is gone for EO 14257's own bilateral-deficit
formula, which reproduces all sixteen published Annex I rates within 0.80pp.

---

## Distributional Validation

### The seven published CBO/JCT tables

`fiscal_model/validation/cbo_distributions.py` carries seven real published
distributional tables, all mapped through
`fiscal_model/validation/benchmark_runners.py` and gated in CI. Live figures:
`python scripts/run_validation_dashboard.py`.

| Benchmark | Source | Grouping | Universe (registered → scored) | Mean abs share error | Rating |
|---|---|---|---|---:|---|
| TCJA, calendar 2018 | CBO 54796 | decile | household → **tax_unit** | 0.00pp | excellent |
| TCJA conference agreement, 2019 | JCT JCX-68-17 | AGI class | tax_unit | 2.10pp | good |
| ARP refundable credits, 2021 | CBO 56952 | quintile | **household** | **3.72pp** | good |
| SALT cap repeal, 2024 | JCT JCX-4-24 | AGI class | tax_unit | 5.86pp | good |
| Corporate 21% → 28%, 2022 | JCT JCX-32-21 | AGI class | tax_unit | 2.51pp | good |
| TCJA extension, 2026 | CBO 60007 | decile | household → **tax_unit** | 0.74pp | excellent |
| **P.L. 119-21, 2026-2034 average** | **CBO 61367** | **decile** | household → **tax_unit** | **3.96pp** | **good** |

The seven tables span **0.00-5.86pp**, from 0.00-7.77pp before Wave 4.

**Read the first and sixth rows with care.**
`distribution_effects.calculate_tcja_effect` builds its decile tiers *out of*
CBO 54796 and CBO 60007 — its own docstring says so — so 0.00pp and 0.74pp
against those two tables is bookkeeping, not skill, in exactly the way Tier 2's
by-construction 1.7% is.

**The `Universe (registered → scored)` column is new in Wave 4 (PR #104), and it
is the point of that lane rather than decoration.** Each benchmark is now
registered on the universe **its source ranks** — CBO ranks households, JCT
ranks tax units — and the surfaces report the universe the row was **actually
scored on**, not the one it declares. Three of the four CBO tables cannot honour
their own registration: `policy_to_microsim_reforms` returns an empty dict for
every `TCJAExtensionPolicy` and for the corporate policy, so `cbo_tcja_2018`,
`cbo_tcja_extension_2026` and `cbo_pl119_21_2026` take the synthetic bracket
path, which aggregates IRS *return* counts and has no household layer to rank.
Their registration is a statement about the document — correct, sourced, and
inert. **That is now visible in a field a reader can check rather than latent**,
and it says something sharper about the two circular rows above: they are *also*
scored on a population CBO does not use. Giving `TCJAExtensionPolicy` a microsim
path would move all three at once, and it is the obvious next lane — the only
way to find out what those tables say when they are not reading CBO's own shares
back.

**The ARP row is the one that moved, 7.77pp → 3.72pp**, and it moved because it
is now scored on CBO's own universe. The engine gained a household layer built
to CBO's published methodology: **size-adjusted household income before
transfers and taxes** (income ÷ √household size), quintiles containing equal
numbers of *people* rather than equal numbers of households. As built, that is
132.39M households and 320.89M people — 29.88M / 27.62M / 24.99M / 24.59M /
25.31M households holding 64.17M / 64.18M / 64.18M / 64.17M / 64.19M people,
equal to within a tenth of a percent across a 21% spread in household counts,
which is CBO's own description reproduced rather than asserted, and pinned by a
test in both directions.

Row by row against CBO, before and after: lowest quintile 53.4% → **28.6%**
against CBO's 34.0%, second 20.0% → 24.7% (28.0%), middle 14.1% → 23.5%
(20.0%), fourth 11.9% → 17.8% (12.0%), highest 0.6% → **5.4%** (6.0%). The
fourth quintile is the one row that got *worse*, 0.13pp → 5.77pp — and its 0.13
was a coincidence of two universes rather than agreement, the same shape L3
found in the 4.76pp it replaced. Six of the seven tables are unmoved **to the
hundredth**, including SALT-cap repeal, the other benchmark that routes through
the microsim and the lane's real control.

**The lane also fixed a dollar column that was wrong by a factor of three, and
no gate in the repository could see it.** `_combine_distributional_results`
reported a merged component's per-group average as the *mean* of the
components' averages where the bundle is their *sum*. `compare_distribution`
scores shares, and the shares came from a correctly dollar-weighted merge, so
the bug was invisible while the ARP row's rendered dollars read -$892 against
CBO's -$2,800. Fixed, with a test that a household getting $1,400 and $3,000 got
$4,400. The averages now read **-$4,503 / -$4,211 / -$4,435 / -$3,404 /
-$1,013** against CBO's -$2,800 / -$3,150 / -$2,450 / -$1,620 / -$920 — the
right order of magnitude everywhere and about 40% high in the middle. That
residual is a **level** disagreement rather than a distributional one: the
model's ARP bundle costs more than CBO's, this benchmark scores shares, and
nothing in the lane touches it. A level 40% high with shares within 3.7pp is a
different kind of error from either one alone, and it is worth its own look.

Three measurements of the ARP row, in the order they happened: **4.76** (rebate
synthetic, credits on the microsim) → **6.29** (statutory CTC/EITC corrections,
rebate still synthetic) → **7.77** (all three on the microsim, Wave 3) →
**3.72** (all three on the microsim, scored on CBO's household universe, Wave
4). The 4.76 → 7.77 rise was the honest number at the time: the old 4.76 was
ranking one component by IRS return counts and the other two by CPS tax units,
and the two rankings partly cancelled. What Wave 4 changed is not the scoring of
the components but the population they are ranked in.

### P.L. 119-21 (CBO 61367, August 2025) — added in Phase D

The seventh table is the first one the engine's TCJA decile shares were **not**
taken from, which makes it the first genuinely held-out distributional number the
suite has produced for that shape. Source: CBO, *Distributional Effects of Public
Law 119-21*, 11 August 2025
([publication 61367](https://www.cbo.gov/publication/61367)), Figures 1 and 2
from the letter's own supplemental data file. Average **annual** change in
household resources over 2026-2034, by household income decile, relative to CBO's
January 2025 baseline, in 2025 dollars.

**Scope, and it matters.** CBO decomposes the effect into four columns; only the
first is inside the distributional engine:

| decile | taxes + cash transfers | in-kind transfers | state responses | other | **net** |
|---|---:|---:|---:|---:|---:|
| Lowest | +119 | -1,485 | +8 | +144 | **-1,214** |
| 2nd | +271 | -843 | +7 | +173 | **-392** |
| 3rd | +447 | -610 | +7 | +179 | **+23** |
| 4th | +674 | -491 | +7 | +189 | **+379** |
| 5th | +992 | -406 | +7 | +205 | **+797** |
| 6th | +1,333 | -347 | +7 | +219 | **+1,211** |
| 7th | +1,759 | -332 | +8 | +238 | **+1,673** |
| 8th | +2,312 | -371 | +9 | +263 | **+2,213** |
| 9th | +3,375 | -478 | +10 | +301 | **+3,208** |
| Highest | +14,708 | -1,637 | +13 | +538 | **+13,622** |

The benchmark is registered with the **taxes-and-cash-transfers column only**.
The CPS microsimulation models neither in-kind transfers (Medicaid, SNAP) nor
states' fiscal responses, and those are what drive the law's regressive *net*
result: the bottom decile loses $1,485/yr of in-kind transfers against a $119/yr
tax gain. Comparing a tax-only model with CBO's net column would not be a
validation, it would be a category error — so **this benchmark does not test the
headline regressivity of P.L. 119-21**, and the net column is recorded in the
benchmark's own notes so nobody mistakes one for the other.

**Result: 3.96pp mean absolute share error across the ten deciles, rated good.**
The error is concentrated at the top:

| decile | model share | CBO share | error |
|---|---:|---:|---:|
| 1-6 | 0.5% - 7.3% | 0.5% - 5.1% | 0.0 - 2.4pp |
| 7 | 9.2% | 6.8% | 2.4pp |
| 8 | 12.6% | 8.9% | 3.7pp |
| 9 | 18.0% | 13.0% | 5.0pp |
| **10** | **36.8%** | **56.6%** | **19.8pp** |

The engine's TCJA decile tiers — taken from CBO's 2018 and 2026 TCJA tables —
put 36.8% of the benefit in the top decile. CBO's own P.L. 119-21 table puts
56.6% there. The gap is the model's, not the benchmark's: P.L. 119-21 is more
top-weighted than a plain TCJA extension (a $40,000 SALT cap, a permanent 199A
deduction and a $15M estate exemption all skew upward), and a fixed tier table
copied from an earlier law cannot know that. This is the first evidence the
distributional suite has produced that those tiers do not travel.

### vs. TPC TCJA Analysis (2017)

Comparison of distributional shares with Tax Policy Center TCJA Conference Agreement analysis.

| Quintile | Model Share | TPC Share | Error | Status |
|----------|-------------|-----------|-------|--------|
| Lowest | 2.0% | 1.0% | 100% | Note 1 |
| Second | 5.0% | 4.0% | 25% | OK |
| **Middle** | **10.0%** | **10.0%** | **0%** | Excellent |
| Fourth | 18.0% | 17.0% | 5.9% | Good |
| Top | 65.0% | 68.0% | 4.4% | Good |

**Note 1**: Bottom quintile has very small absolute share; 100% error is only 1 percentage point.

**Overall Score: GOOD** - Model correctly captures that TCJA benefits skew heavily toward high-income taxpayers (65-68% to top quintile).

### Corporate Tax Incidence

Validation of 75/25 capital/labor incidence assumption:

| Source | Capital Share | Labor Share |
|--------|--------------|-------------|
| CBO | 75% | 25% |
| TPC | 75% | 25% |
| JCT | 75% | 25% |
| **Model** | **75%** | **25%** |

Capital income distribution matches Federal Reserve SCF data within 5%.

---

## Accuracy Rating Scale

| Rating | % Error | Interpretation |
|--------|---------|----------------|
| **Excellent** | <=5% | Model closely matches official estimates |
| **Good** | 5-10% | Model is reasonably accurate |
| **Acceptable** | 10-20% | Model provides directional guidance |
| **Poor** | >20% | Significant deviation - investigate methodology |

---

## Known Systematic Biases

### Underestimates
1. **Payroll tax revenue** (12% systematic): Model uses Census wage data; SSA has more detailed high-earner information
2. **Estate tax revenue** (10%): Wealth concentration at top is higher than model assumes

### Overestimates
1. **Tax credit costs** (9%): Take-up rates may be lower than 100%
2. **Capital gains revenue** (19% for all-bracket changes): JCT uses higher implied elasticity than academic literature

### Well-Calibrated
1. **TCJA extension** (0.4%): Explicitly calibrated to CBO
2. **AMT policies** (0.1%): Based on IRS/JCT taxpayer counts
3. **Tax expenditure caps** (0.1-5%): JCT baseline data embedded

---

## Data Sources

### Official Estimates
| Source | Used For | URL |
|--------|----------|-----|
| CBO | Budget projections, policy scores | [cbo.gov/cost-estimates](https://www.cbo.gov/cost-estimates) |
| JCT | Tax revenue estimates | [jct.gov/publications](https://www.jct.gov/publications/) |
| Treasury | Administration proposals | [treasury.gov](https://home.treasury.gov/) |
| TPC | Distributional analysis | [taxpolicycenter.org](https://www.taxpolicycenter.org/) |
| PWBM | Dynamic scoring, capital gains | [budgetmodel.wharton.upenn.edu](https://budgetmodel.wharton.upenn.edu/) |
| SSA Trustees | Payroll tax projections | [ssa.gov/oact/tr](https://www.ssa.gov/oact/tr/) |

### Model Data
| Data | Source | Vintage |
|------|--------|---------|
| Taxpayer counts | IRS SOI Table 1.1 | 2021-2022 |
| Income distributions | IRS SOI | 2021-2022 |
| Capital gains realizations | IRS SOI / CBO projections | 2022 |
| Wage distributions | Census CPS | 2023 |
| CBO baseline | CBO Budget Projections | February 2026 |

---

## Running Validation

### Quick Validation

```python
from fiscal_model.validation import compare_to_cbo
results = compare_to_cbo()
```

### Full Validation Suite

```python
from fiscal_model.validation.compare import (
    validate_all_tcja,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_payroll,
    validate_all_amt,
    validate_all_ptc,
    validate_all_expenditures,
    validate_all_capital_gains,
)

# Run all validation
tcja_results = validate_all_tcja(verbose=True)
corporate_results = validate_all_corporate(verbose=True)
credit_results = validate_all_credits(verbose=True)
estate_results = validate_all_estate(verbose=True)
payroll_results = validate_all_payroll(verbose=True)
amt_results = validate_all_amt(verbose=True)
ptc_results = validate_all_ptc(verbose=True)
expenditure_results = validate_all_expenditures(verbose=True)
capgains_results = validate_all_capital_gains(verbose=True)
```

### Manuscript Appendix Export

Use the appendix generator when you want a markdown artifact with benchmark provenance, follow-up checkpoints, and explicit evidence boundaries:

```bash
python scripts/generate_validation_appendix.py --output docs/validation_appendix_generated.md
```

Add `--include-core-database` if you want the broader legacy `validate_all()` score database as well as the curated cross-category suites.

### Custom Policy Validation

```python
from fiscal_model.validation.compare import quick_validate

# Validate a custom policy against an expected value
result = quick_validate(
    rate_change=0.026,           # +2.6pp
    income_threshold=400_000,    # $400K+
    expected_10yr=-252.0,        # -$252B (Treasury estimate)
    policy_name="Biden High-Income Tax"
)

print(result.get_summary())
# Biden High-Income Tax (Generic OOS): Official $-252B vs Model $-284B (~13%)
```

---

## Interpretation Guidelines

### When Model and Official Differ

1. **Check baseline assumptions**: CBO baseline assumes current law (TCJA expires). Model allows flexible baselines.

2. **Review behavioral parameters**: ETI, capital gains elasticity, labor supply elasticity all affect estimates. Official scorers may use different values.

3. **Consider data vintage**: IRS SOI data has 2-year lag. Economic conditions may have changed.

4. **Note policy complexity**: Multi-provision policies (like TCJA) require calibration factors that may not transfer to custom variants.

### Appropriate Use Cases

| Use Case | Reliability | Notes |
|----------|-------------|-------|
| Directional analysis | High | Model correctly identifies revenue/cost direction |
| Order of magnitude | High | Within factor of 2 for most policies |
| Precise scoring | Medium | 5-15% error typical; use for planning, not official scoring |
| Distributional | Medium | Validated mainly against TPC; broader CBO-style distributional benchmarking is still pending |
| Dynamic effects | Lower | FRB/US-calibrated, but macro uncertainty high |

---

## Comparison to Other Models

| Feature | This Model | CBO | JCT | TPC | PWBM |
|---------|------------|-----|-----|-----|------|
| Static scoring | Yes | Yes | Yes | Yes | Yes |
| Behavioral response | ETI-based | Detailed | Detailed | Detailed | Detailed |
| Dynamic macro | FRB/US-lite | Full FRB/US | Partial | Limited | OLG |
| Distributional | Quintiles/deciles | Limited | 10 groups | 5 quintiles | Limited |
| Open source | Yes | No | No | Partial | Partial |
| Real-time updates | Yes | Annual | Annual | Project | Project |

---

## CBO Methodology Reference

Key methodological points from CBO scoring practice:

### Sunsets Matter
- Temporary provisions (sunsets) significantly reduce 10-year scores
- Example: Build Back Better scored at $367B vs $3T+ if permanent
- **Implication**: Always check if provisions are temporary

### Timing Shifts
- Tax payment timing can alter 10-year scores
- Revenue timing affects scores even if total unchanged
- Example: Build It in America Act - increases deficits early, decreases later

### Authorization vs Appropriation
- Authorization bills set policy but don't spend money
- CBO scores only mandatory spending changes
- Example: NDAA authorizes $895B but CBO scores only $178M mandatory

### Pay-Fors
- New spending often offset by delayed/cancelled provisions
- Watch for offsetting provisions that may not be permanent
- Example: Medicare drug rebate delays used repeatedly as "pay-fors"

### IRS Enforcement
- IRS enforcement revenue typically not scored under budget rules
- Example: IRA expected ~$200B from enforcement but not in CBO score

---

## Future Validation Work

1. **2023 IRS SOI data**: Update taxpayer counts when available
2. **Next CBO baseline refresh**: Incorporate new projections as they are published
3. **Additional policies**: Expand validation database
4. **Distributional validation**: More TPC benchmarks
5. **Dynamic scoring**: Compare to CBO/JCT dynamic estimates

---

## References

1. Congressional Budget Office. (2024). *The Budget and Economic Outlook: 2024 to 2034*.
2. Joint Committee on Taxation. (2024). *Overview of the Federal Tax System*.
3. Saez, E., Slemrod, J., & Giertz, S. H. (2012). The elasticity of taxable income with respect to marginal tax rates. *Journal of Economic Literature*, 50(1), 3-50.
4. Penn Wharton Budget Model. (2021). *Revenue Effects of President Biden's Capital Gains Tax Increase*.
5. Tax Policy Center. (2024). *Distributional Analysis of Major Tax Proposals*.

---

*This validation report is maintained alongside the validation suite and refreshed as new official estimates are incorporated.*
