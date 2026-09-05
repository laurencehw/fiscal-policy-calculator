# Model Validation Report

> **Fiscal Policy Calculator — Comparison to Official CBO/JCT Estimates**
>
> Last Updated: September 2, 2026 (post-Wave-2: PRs #93 estate distribution, #94 tax-expenditure cap units, #95 capital-gains base/elasticity/lock-in/gains-at-death)

---

## Executive Summary

The model is benchmarked against **73 published estimates** — from CBO, JCT, Treasury and SSA, plus TPC, PWBM, the Tax Foundation and CRFB where no agency scored the policy — plus 7 *illustrations* with no official score at all, which are labelled and reported separately and never counted (`published_entries` vs `total_entries` on the scorecard). Crucially, those benchmarks fall into **two epistemically different tiers**, and reporting them together overstates predictive power. Both are reproducible live: `python scripts/cold_holdout.py`. Tier 1 is additionally **pre-registered** (`fiscal_model/validation/preregistered.py`) and **CI-gated**.

### Tier 1 — Out-of-sample predictions (the genuine test)

Policies scored **bottom-up** — IRS SOI filer counts and incomes via raw rate/threshold auto-population, the modules' own revenue identities, and spending levels stated by the source — with **no fitting to the official target** (and, for capital gains, one frozen elasticity set). This is the only tier that measures predictive accuracy.

> **26 out-of-sample cases, mean abs error 18.0%, 14/26 within 15%, 21/26 within 25%** (median 12.6%).
> There is deliberately no single "validated within X%" number: the distribution has a tight core and a long tail, and collapsing it would hide the tail.

*Wave 4 (PRs #105, #107, #108) took this tier from **31.0% to 18.0%** and its median from 15.1% to **12.6%**, within-15% 13 → **14** and within-25% 19 → **21**, on five rows. **PR #108 did almost all of it**: giving the death channel the six carve-outs a realization-at-death proposal does not tax — spousal, charitable, the §121 residence exclusion, tangible personal property, a family-business deferral, and the per-donor exclusion applied *after* the others — plus a semi-log rate response at death, took the tier to 18.5% on its own and the capital-gains error mass **405.6 → 81.0**, from 50.3% of the tier to 17.3%. `treasury_capgains_39_plus_stepup_elim` 217.5% → **0.2%**, `biden_capital_gains_39` 134.9% → **16.7%**, and `cbo_opt51_gains_at_death` 8.4% → **19.3%, worse and pre-registered as a regression** — its 8.4% had been bought by taxing charitable bequests and small decedents' housing gains that no such regime reaches. **The 0.2% is two errors cancelling and must not be quoted as accuracy**: the mechanism removes 87.2% of that row's death channel where the pre-registered hand path said 92.8%, and the lane's own falsification test fired because the two Green Book rows land on opposite sides of their targets. The diagnosis is not the exclusion ordering (pinned by a test; applying it first moves both the same way) but the **five-class decedent ladder having no within-group dispersion** — moving the exclusion from $1M to $5M costs the model $82.2B of death channel where it costs Treasury $33.4B. **PR #105** took CBO Option 56 **24.0% → 13.1%** by giving the excess share CBO's own chained-CPI indexation instead of evaluating it once at `start_year`; **PR #107** moved `biden_high_income_tax`'s target from a rounded −$252B to the Green Book's own printed −$245.9B (`.v2`), which moved only the error column, 14.1% → **12.0%**. **PR #110** then re-derived the CI gate by the workflow's own rule: 40/18 → **25/20**.*

*Wave 3 (PR #100) added the 26th case and moved the mean 31.3% → **31.0%**, the median 14.1% → **15.1%**, and within-25% 18/25 → **19/26**. **No existing row moved by a cent**: the only change is that CBO Option 56 stopped being a leakage exclusion, because lane L6 had removed the fitted annual its only expressible path used to run through. It enters at **−$529.9B against −$697.0B, 24.0%** — the tier's first tax-expenditure cap, and its residual is a named omission rather than a tuned parameter (below). Wave 3's other three lanes touch no Tier 1 row: L9 international and L8 tariffs have no case in the tier, and L3 credits builds no `TaxCreditPolicy` in it.*

*Wave 2 (PRs #93, #94, #95) moved this tier from 34.4% to **31.3%** and its median from 16.1% to **14.1%**, on the capital-gains rows only — lane L1 replaced the realizations base, the elasticity unit, the lock-in multiplier and the gains-at-death constant. Two rows improved (`cbo_opt51_gains_at_death` 84.4% → **8.4%**, `cbo_opt47_ltcg_qdiv_2pp` 99.1% → **44.8%**), one barely moved (`biden_capital_gains_39` 142.3% → 134.9%) and one got worse (`treasury_capgains_39_plus_stepup_elim` 153.6% → **217.5%**), because the derived lock-in wedge runs the *other* way on a proposal that eliminates step-up. Four rows the lane did not name also moved, all through `preferential_income_share` reading the new SOI bracket base: `cbo_opt45_top4_brackets_2pp` 25.8% → **17.9%**, `illustrative_1pp_all` 2.6% → 4.1%, `cbo_opt45_all_rates_1pp` 21.1% → 22.4%, `biden_high_income_tax` 12.9% → 14.1%. Neither L4 (estate) nor L6 (tax expenditures) touches a Tier 1 row. The lanes' pre-registrations are in [`planning/lanes/`](../planning/lanes/).*

*Wave 1 had earlier moved this tier from 52.6% to 34.4% and its median from 21.1% to 16.1%, on the eight spending rows only. Lane L2 (PR #85) added the budget-authority-to-outlay spend-out model the battery had been diagnosing since Phase D; PR #88 then superseded IIJA's shape input with CBO's own authorization schedule (`.v1` → `.v2`, target unchanged). No tax row moved, and no target was edited. The two lanes' pre-registrations are in [`planning/lanes/L2_spend_out.md`](../planning/lanes/L2_spend_out.md).*

*Phase E had earlier changed two rows, in opposite directions and for the same reason — somebody opened the document. `top_rate_45` was **retired**: its -$420B is in no TPC, CBO or JCT publication. `biden_capital_gains_39` was **re-sourced** from an unsupported -$456B to the FY2025 Green Book's actual line item, -$288.6B, and its shape corrected to the source's own definition, which made it score worse. Details below and in [`preregistered.py`](../fiscal_model/validation/preregistered.py).*

| Case | Official | Model | Err | Source (date) | Baseline the source used | Pre-registered at |
|------|---------:|------:|----:|---------------|--------------------------|-------------------|
| Cut international affairs 25% | -$187B | -$187B | 0% | CBO Options 2025-2034 #37 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Treasury 39.6% + step-up repeal | -$322B | -$323B | 0.2% | Treasury (2021-05) | Green Book FY2022 | `d11bf2c`, scored `6c9bfa2` |
| Medicare surcharge 2pp (>$400K) | -$310B | -$315B | 2% | Treasury (2024) | Green Book FY2025 | `6c9bfa2` |
| Cut selected nondefense discretionary | -$339B | -$333B | 2% | CBO Options 2025-2034 #42 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| End national community service funding | -$10B | -$11B | 3% | CBO Options 2025-2034 #38 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| 1pp all brackets | -$960B | -$920B | 4% | JCT (2023-01) | CBO Feb 2023 | `be7e947` |
| 5pp top rate ($1M+) | -$700B | -$648B | 7% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| Tighten Pell grant eligibility | -$22B | -$20B | 8% | CBO Options 2025-2034 #39 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| 2pp rate cut ($500K+) | +$400B | +$364B | 9% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| Social Security Fairness Act: WEP/GPO repeal | +$196B | +$215B | 10% | CBO, H.R. 82 (2024-09) | CBO June 2024 (no vintage in repo) | `aed5318`, scored `dca3a50` |
| Cut certain state and local grants | -$67B | -$74B | 11% | CBO Options 2025-2034 #43 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Biden top rate 39.6% ($400K+) | -$246B | -$217B | 12% | Treasury (2024-03), Green Book FY2025 table row | Green Book FY2025 | `318be6b` (`.v2`, superseding `.v1`), scored `22ccdd2` |
| Fiscal Responsibility Act: discretionary caps | -$1,332B | -$1,170B | 12% | CBO, H.R. 3746 letter (2023-05) | CBO May 2023 (no vintage in repo) | `aed5318`, scored `dca3a50` |
| Limit the income-tax employer-health exclusion | -$697B | -$606B | 13% | CBO Options 2025-2034 #56, **3rd alternative** (2024-12) | CBO Feb 2024 (matched) | `3738ffc`, scored `d189a26` |
| AGI surtax 2pp (>$100K single) | -$1,051B | -$882B | 16% | CBO Options 2025-2034 #46 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Biden capital income at ordinary rates | -$289B | -$240B | 17% | Treasury (2024-03), Green Book FY2025 table row | Green Book FY2025 | `0bcfbc3` (`.v2`, superseding `.v1`) |
| Top four ordinary brackets +2pp | -$570B | -$672B | 18% | CBO Options 2025-2034 #45 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| IIJA 2021: discretionary component | +$415B | +$340B | 18% | CBO, S.Amdt. 2137 (2021-08) | CBO July 2021 (no vintage in repo) | `1a68118` (`.v2`, superseding `.v1`), scored `327a69b` |
| Warren surtax 3pp (AGI >$2M) | -$350B | -$284B | 19% | TPC (2020) | unstated (secondhand) | `6c9bfa2` |
| Tax accrued gains at death | -$536B | -$433B | 19% | CBO Options 2025-2034 #51 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| All ordinary rates +1pp | -$1,185B | -$920B | 22% | CBO Options 2025-2034 #45 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| AGI surtax 1pp (>$20K single) | -$1,440B | -$797B | 45% | CBO Options 2025-2034 #46 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| LTCG + qualified dividends +2pp | -$103B | -$57B | 45% | CBO Options 2025-2034 #47 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Corporate rate +1pp (21% to 22%) | -$136B | -$200B | 47% | CBO Options 2025-2034 #64 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| New 1% payroll tax (all earnings) | -$1,282B | -$1,975B | 54% | CBO Options 2025-2034 #61 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| New 2% payroll tax (all earnings) | -$2,540B | -$3,950B | 56% | CBO Options 2025-2034 #61 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |

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
| IIJA 2021 (S.Amdt. 2137 to H.R. 3684) | Discretionary funding and its outlays | CBO's own authorization schedule: $163.0B (FY2022), then $70.1B, $68.5B, $68.1B, $66.2B, then $2.082B/yr | +$415.4B | +$340.0B | 18% | **A window miss — no longer a spend-out or a level-shape miss.** The `construction_and_capital` path outlays $433.2B in total against CBO's $415.4B (4.3% high, which is the profile's 0.973 spend-out sum applied to the full authority), but **$92.6B of that falls in FY2022-2024**, before the model's FY2025-2034 window opens, against a published figure covering FY2021-2031. |

**IIJA: two rows, two defects, one unchanged target.** The row that reached 356%
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
| `iija_2021_discretionary.v2` | the source's own authorization schedule | **+$340.0B** | +$415.4B | **18.2%** |

The **target never moved** — same $415.448B, same document, same window, same
vintage note — and `.v1` stays in `preregistered.py` unedited with both its
figures on the record. Between them the two rows separate the two defects this
case surfaced: the missing spend-out model (`.v1`) and the missing authorization
path (`.v2`). Earlier revisions of this file argued that spreading the source's
stated FY2022-2026 authorization evenly still yields $1,012.9B, and that IIJA was
therefore kept as the sharpest evidence for a missing mechanism. Both halves are
now history: the mechanism exists, and the case is scored on the schedule the
source actually states.

**Three bills were examined and left out of scope, with CBO's component figures
recorded** rather than scored:

| Bill | Official | Why no component is scoreable |
|------|---------:|-------------------------------|
| Inflation Reduction Act 2022 | -$90B | Every component the app can express routes through a module whose constant is calibrated to that same reform — the climate module's IRA-repeal annual is documented as fitted to the -$783B IRA-repeal target, and `repeal_corporate_amt`'s base constant is its own target divided by ten. Scoring it would be leakage, not prediction. |
| Tax Relief for American Families and Workers Act 2024 (H.R. 7024) | +$0.4B | CBO's own table: +$117.5B of deficit in FY2024 netting to +$399M over 2024-2033, because a CTC expansion and R&D expensing are offset by barring new ERTC claims. A percentage error against a $0.4B net of $100B-scale components is uninformative whatever the model does. |
| NDAA FY2025 (S. 4638) | +$0.178B | An authorization bill: CBO scores only $178M of mandatory retirement-benefit changes against $895B authorized. The scored quantity is three orders of magnitude below model resolution, and the $895B is not a budget effect at all. |

#### The misses, grouped by cause

Every miss is kept and carries a `known_limitations` note in the scorecard. Six causes account for all of them, and **after Wave 4 the largest is no longer capital gains — it is the module revenue identities applied at the margin**. Group masses (Σ|error %|, tier total **468.1** over 26 cases, from 805.8 before Wave 4):

1. **Module revenue identities applied at the margin (3 cases, 47-56%; mass 156.7, 33.5% of the tier).** Unmoved in absolute terms and now the tier's largest single group by default, because everything around it shrank. The payroll shape scores a new tax on all earnings off the Medicare identity ($400B at 2.9%), which includes the employer share and carries no income-tax offset, so it over-predicts by ~55% at both 1% and 2%. The corporate shape applies the full statutory-rate delta to the whole base, over-predicting a 1pp step by 47%.
2. **The bracket-aggregate ceiling on ordinary and AGI-inclusive rate changes (8 cases, 1-22%; mass 91.4, 19.5%).** Flat SOI bracket aggregates with a single ETI, against sources whose own estimates rise through the window as bracket creep pushes income upward. Wave 4's provenance pass took 2.1 units out of it by moving `biden_high_income_tax` onto the Green Book's own printed row.
3. **Capital-gains behaviour at the top rate and at death (4 cases, 0.2-45%; mass 80.9, 17.3%).** **This was 405.6 units and 50.3% of the tier before Wave 4, and it was the plan's rank-1 lane for that reason.** Wave 2's L1 had rebuilt the base, the elasticity unit and the gains-at-death stock; Wave 4's PR #108 built the thing L1 left out. A realization-at-death proposal does not tax **spousal transfers, charitable bequests, the §121 residence exclusion, tangible personal property, or family-owned businesses that elect deferral**, and it applies the per-donor exclusion *after* all of those; the module now transcribes all six from the Green Books' own text, and applies a semi-log rate response at death (`exp(−2.2660 × 0.196)` = 0.641 on the decedents a rate change reaches, exactly 1.0 on Option 51, which changes no rate). `treasury_capgains_39_plus_stepup_elim` 217.5% → **0.2%**, `biden_capital_gains_39` 134.9% → **16.7%**, `cbo_opt51_gains_at_death` 8.4% → **19.3%** (worse and pre-registered as a regression — its 8.4% was two errors cancelling, an unreached base counted in full), `cbo_opt47_ltcg_qdiv_2pp` unmoved at **44.8%**, since it keeps step-up and the death channel never runs. **The 0.2% is also two errors cancelling and must not be read as accuracy**: the mechanism removes 87.2% of that row's death channel where the pre-registered hand path said 92.8%. The two Green Book rows land on opposite sides of their targets — a pre-registered falsification test that fired, and whose diagnosis is *not* the one it was written to catch. The exclusion ordering is pinned by a test and applying it first would raise both scores; the residual is monotone in the exclusion; and after the carve-outs, gain per decedent is \$9.71M in `TopPt1`, \$1.89M in `RemainingTop1`, \$0.92M in `Next9` and \$79K in `Next40`, so a \$1M exclusion leaves two classes in tax and a \$5M exclusion leaves **one**. The cause is the **five-class ladder having no within-group dispersion**, which costs the model \$82.2B of death channel between those two exclusions where it costs Treasury \$33.4B. That is the next lane. Option 47's own residual is unchanged and separate: the frozen Dowd–McClelland–Muthitacharoen persistent elasticity is well below the 1.5-2.0 JCT's own path implies at a 2pp change. All four rows are scored with ONE frozen elasticity set — the `CapitalGainsPolicy` dataclass defaults, persistent 0.72 / transitory 1.20 at a 22% reference rate, semi-logarithmic because CRS R48562 defines the elasticity on the tax rate — and `scenarios.py`'s per-case tuples no longer exist.
4. **Budget-authority-to-outlay lag and the level shape (8 cases, 0-18%; mass 63.3, 13.5%).** **This was 509 units and 38.7% of the tier before Wave 1, and it was the plan's rank-2 lane for that reason.** L2 built the spend-out model — `outlays_t = Σ_k s_k · BA_{t−k}`, with `s` fitted by NNLS on the 14 CBO donor options the battery does not score — and PR #88 gave IIJA the authorization schedule CBO's own estimate states. The five CBO Options spending rows now land at 0-11% (Option 43, the slowest spend-out in the battery, went 75% → 11%), the three enacted-law components at 10-18%. What is left is *not* spend-out: Option 39 under-predicts (8%) because Pell disburses in two years while the generic grants profile takes six, Option 43's residual is a first-year authority level inflated by IIJA advance funding, FRA's is the level shape, IIJA's is a window mismatch, and SSFA's is a growth rate. Account-level rates would close the first of those, and CBO publishes them (publications 61913 and 62256) — from an environment that can reach cbo.gov.
5. **One threshold standing in for a filing-status-specific boundary (2 cases, 18% and 45%; mass 62.6, 13.4%).** "The four highest brackets" and "AGI above \$20,000 single / \$40,000 joint" are boundaries the generic path cannot express; it carries one number. The error is largest at the low threshold (Option 46 alternative 1, 45%), where the mis-assignment covers most of the filing population.
6. **A tax-expenditure cap missing part of its base and carrying an unsourced behavioural offset (1 case, 13%; mass 13.1, 2.8%).** Entered in Wave 3 at 24.0% with a *shape* residual; Wave 4's PR #105 gave the excess share CBO's own chained-CPI indexation and the row fell to **13.1%**. What is left is half a base omission — CBO caps premiums **and** FSA/HRA/HSA contributions and the repository's premium distribution has no account dimension — and about a fifth an unsourced behavioural offset whose sign convention is the reverse of `TaxPolicy`'s. Both are named in the row's `known_limitations` and neither is tuned.

*(A seventh cause, "a single ETI at a large rate change against a secondhand target", left the battery with `top_rate_45` in Phase E.)*

**Honest reading**: the model predicts ordinary and AGI-inclusive *rate* changes at conventional thresholds well (1-22%), discretionary funding changes well now that authority is spent out (CBO Options rows 0-11%, enacted-law components 10-18%), **gains at death** well now that they are accrued on a stock and the statutory carve-outs are priced (0.2-19%, with the 0.2% carrying its own two-errors-cancelling caveat), and an employer-health cap well now that its excess share is indexed (13%). What it still predicts badly is a preferential-rate change at a small step (45%), a filing-status-specific threshold (45%), corporate margins (47%) and payroll incidence (54-56%) — and that last pair is now the tier's largest error mass. Phase A's 9-case 44.8% and Phase B's 23-case 43.4% were the same story on more than twice the evidence: widening the battery did not move the mean, it explained it. Phase D then added the one shape that moved it — IIJA's 356% — taking the 25-case mean to 52.6% while the median *fell* to 21.1%. Wave 1 built the mechanism that 356% was evidence for, and the mean fell to 34.4% with the median at 16.1% and within-15 rising 8 → 12. Wave 2 did the same for capital gains and it fell again, to 31.3% / 14.1% / 13 within 15 / 18 within 25. Wave 3 added a case rather than moving one: Option 56 entered at 24.0% and the tier read 31.0% / 15.1% / 13 / 19. Wave 4 did what Wave 2 had left half-done — the death channel's carve-outs and behaviour, Option 56's indexation, and one target moved onto its document — and the tier reads **18.0%** / **12.6%** / **14 within 15** / **21 within 25**. The tier is now what it always claimed to be underneath: a tight rate-and-spending core and a behavioural tail — and the tail is three rows shorter and much better named than it was.

**What the tight core shows.** Ordinary-bracket rate changes (JCT 1pp, Biden $400K, CBO Option 45) score on the ordinary-income base (excludes preferential LTCG/QDIV); AGI-inclusive surtaxes (TPC $1M+/$500K+, Warren, the Medicare surcharge, CBO Option 46) score on the full taxable-income base that includes the preferential portion. The classification comes from how each source describes its base, not from which choice fits better — the `cold_holdout.py --ordinary-base` diagnostic shows the correction *worsens* the AGI-inclusive cases (7→30%, 9→30%, 2→29%), which is the tell. For ordinary and AGI-inclusive rate changes in this range, **treat uncalibrated custom policies as directional, ±15-25%.**

**The three cases Phase A flagged, resolved in Phase E by reading the documents.** Phase A's guess was that one of the targets was wrong. The answer was worse than that.

- **Top rate to 45% — retired.** The target could not be sourced at all. TPC's full sitemap was enumerated (11 sub-sitemaps, ~20,600 URLs, ~6,500 model-estimate pages) and contains no table for a 45% ordinary rate at any date: the only "45 percent" pages are the estate-tax top rate and an EITC phase-in rate, none of TPC's 82 `t23-*` tables is a top-rate table, and its top-rate collections are all pre-2010 vintage. CBO and JCT publish no +8pp top-bracket option either, and CBO explicitly warns that "the deficit effects of large rate increases or surtaxes might not be proportional to the estimates shown here." PWBM (May 2025) brackets the plausible range at **$401.6B** for reverting the top bracket to 39.6% and **$222.4B** for a new 39.6% bracket above $1M — which makes -$420B for +8pp above $609,350 implausibly *low*, the opposite direction from the model's -$916B. There is no figure to correct it to, so the case is withdrawn from the battery (`retired=True`, with the search recorded) rather than scored against a number nobody published. The unsourced -$420B is also gone from `CBO_SCORE_MAP`, so the app no longer quotes it.
- **Biden capital gains — re-sourced, and the error went up.** -$456B appears in no Treasury volume. The FY2025 Green Book scores "Reform the taxation of capital income" as a **single combined row of $288,583M** (report p. 242; PDF p. 250) and never splits the rate change from the realization-at-death change, so there is no decomposition -$456B could have been assembled from. The manifest row is superseded (`.v1` → `.v2`), and the *shape* moved to the source's own definition rather than the number being fitted: **taxable** income over $1M (the FY2022 volume says AGI) and a **$5M per-donor** exclusion for gains at death, portable to $10M per couple (report p. 89), where the module default and the FY2022 proposal are $1M per person. The larger exclusion cuts the modelled gains-at-death revenue, so the prediction moves from -$817B to -$699B against a target that also fell — and the error goes **79% → 142%**. That is the correct outcome of a sourcing pass: a better target and a more faithful shape, scored honestly.
- **Treasury 39.6% + step-up repeal (154%) — confirmed.** The FY2022 Green Book row is **$322,485M** (report p. 105; PDF p. 111), 0.15% from the carried -$322B, and the FY2022 narrative (report p. 62) confirms every element of the shape including the +19.6pp incremental rate (footnote 1: "a separate proposal would first increase the top ordinary individual income tax rate to 39.6 percent (43.4 percent including the net investment income tax)"). So the 42% gap Phase A found between this and `biden_capital_gains_39` was **not** two published estimates disagreeing: one was published and one was not. Across four consecutive Green Books the same combined row reads $322,485M (FY2022) → $174,488M (FY2023) → $213,855M (FY2024) → $288,583M (FY2025), which is genuine cross-vintage movement on a design that itself changed (AGI → taxable income; $1M → $5M exclusion).

Two further out-of-sample targets did not survive the same sweep and are **open owner decisions**, listed here rather than acted on because the plan named only `top_rate_45`:

- **5pp top rate ($1M+), -$700B.** No TPC table states it; the record calls itself "illustrative". PWBM scores a new 39.6% bracket above $1M — a smaller change on the same threshold — at $222.4B over FY2026-2035.
- **Warren surtax 3pp (AGI >$2M), -$350B.** TPC's only AGI-surtax revenue table, T19-0037 (23 September 2019), scores a **10pp** surtax on AGI over $2M at $585.3B over 2019-2029, i.e. roughly $58.5B per percentage point. A 3pp version is on the order of **$175B**, about half the carried target. (T19-0037 does confirm the record's `agi_inclusive_base=True` flag: the surtax applies to AGI in excess of the threshold.)

**And one Tier 1 target now has a transcribed row that disagrees with it.** Biden's top-rate proposal is published at **$245,924M** (FY2025 Green Book, report p. 242), against the carried -$252B — 2.5% apart. Pre-registered targets are frozen, so correcting it requires a new manifest row superseding `biden_high_income_tax.v1`; that is an owner decision and the gap is recorded on the scorecard entry meanwhile.

### Pre-registration

Every Tier 1 case is registered in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py) with the official target, the publishing source and date, the budget baseline *that source* was scored against, the commit and date at which the record entered the repository, and the commit of the first scoring run.

The discipline the manifest enforces (`assert_preregistered`, tested in `tests/test_preregistration.py`):

0. **The target is entered in a commit before the commit that first scores it.** Phase B's 14 CBO Options rows were entered in `752f0f1` (`PHASE_B_ENTERED_COMMIT`) and first scored in `36d683f` (`PHASE_B_FIRST_SCORED_COMMIT`), which is the commit that flips them to `runnable=True`. Phase D's three enacted-law rows were entered in `aed5318` (`PHASE_D_ENTERED_COMMIT`) and first scored in `dca3a50` (`PHASE_D_FIRST_SCORED_COMMIT`). A file cannot contain its own hash, so both are stamped in the immediately following commit — the same convention Phase A used.
1. **A target may never be edited to match a model run.** If an official number genuinely changes, the old row is marked `superseded_by` and a **new row with a new `case_id`** is added. The history stays in the file and in the diff.
2. **No case may be scored out-of-sample without a row.** A Generic scorecard entry with no manifest row fails the test.
3. **Misses are kept.** A row is never removed because the model scores it badly.

Honest boundary, as with [`holdout.py`](../fiscal_model/validation/holdout.py): these are previously published numbers, and Phase A registered targets that already existed in the repository or in `CBO_SCORE_MAP`. What the manifest guarantees is that *from the entry commit onward* the target is frozen and any change is visible — not that nobody had ever seen the number.

**CI gate.** `.github/workflows/validation-dashboard.yml` runs `python scripts/cold_holdout.py --max-mean-error 25 --min-within-25pct 20` as a blocking step. The workflow's own rule sets both: ceiling = ceil(mean x 1.25) to the nearest 5; floor = current count within 25%, minus one. On the post-Wave-4 battery (26 cases, mean 18.0%, 21 within 25%) the rule gives a ceiling of **25** (18.0 × 1.25 = 22.5, ceil 23, rounded up to the nearest 5) and a floor of **20**. The workflow was tightened to **25 / 20** after Wave 4 (PR #110), from the **40 / 18** Wave 3 had derived, the **40 / 17** Wave 2 had derived, the **45 / 15** Wave 1 had derived and the **55 / 13** before that; a modelling lane never touches the yardstick, so the coordinator re-derives it in a separate PR once the docs are synced. Strict readiness (`scripts/check_readiness.py --strict`) no longer exempts Generic entries: an `Error` rating fails, and a `Poor` rating fails unless it carries a documented `known_limitations` note.

### Tier 2 — Calibrated reference models (reconstructions, not confirmations)

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce the published decomposition**. Phase E added five more module families — international, trade, pharma, IRS enforcement, climate — and those turned out to be a different animal, so the tier now splits in two.

| Metric | Calibrated reference (fitted) | Module reconstruction (not fitted) |
|--------|---:|---:|
| Benchmarks | **23** | **31** |
| Mean absolute error | **1.6%** | **56.6%** |
| Median absolute error | 0.1% | 29.9% |
| Within 15% of official | 23/23 | 9/31 |
| Within 25% of official | 23/23 | 12/31 |

**Both columns moved in Wave 4 for composition reasons and neither move is an improvement. The constant-population readings are the ones to quote:** the fitted tier is **28 at 3.0%, 27/28 within 15%** with Wave 4's five revised rows held in place, and the reconstruction tier is **65.7% mean / 40.5% median over the 26 rows it already held** — *worse* than the 61.8% / 38.0% it read before Wave 4, because the pharma rebuild took two rows further from their targets.

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

The 1.6% on the left is **expected by construction** — those modules carry a constant fitted to each benchmark, so they demonstrate the model's structure and provide auditable, source-linked reconstructions of official scores; they are **not** evidence the model would have predicted them cold. (Earlier revisions of this file quoted 4.4%, then 2.7% over 34, then 2.8% over 33, then 2.2% over 30; the live figures come from `python scripts/cold_holdout.py`, which is the only place they should be read from.)

**The left-hand column has lost eleven rows, and the losses must be quoted with
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
`ScorecardSummary.revised_target_entries` is **15**: fifteen calibrated targets have been
corrected through the Tier-2 revision ledger
([`fiscal_model/validation/target_revisions.py`](../fiscal_model/validation/target_revisions.py)),
and a constant fitted to a superseded figure is not fitted to its replacement —
so `scorecard.py` derives `calibrated_to_target` from the ledger and the revised
rows report on the right, where a miss is a finding rather than a regression.
Wave 4's provenance pass moved `biden_eitc_childless`, `eliminate_salt`,
`extend_enhanced_ptc`, `ira_enforcement` and `repeal_salt_cap` out that way,
mechanically; **retuning any of them to close the new gap would have been the
relaxation, and none was touched**. Both readings, and never one alone:

| Reading | n | Mean | Median | Within 15% | Off by >15% |
|---|--:|--:|--:|--:|---|
| **As reported** — revised rows moved to the reconstruction tier | **23** | **1.6%** | 0.1% | **23/23** | none (worst is `tcja_no_salt_cap`, 13.9%) |
| **Held in place** — Wave 4's five kept in the fitted tier | 28 | **3.0%** | 0.2% | 27/28 | `eliminate_salt` (22.3%) |
| **Held in place, plus the revised TCJA-AMT row** — the n=29 reading earlier revisions quoted at 4.3% | 29 | **5.2%** | 0.3% | 27/29 | `eliminate_salt` (22.3%), `extend_tcja_amt` (66.8%) |

Six of the fifteen revised rows change tier. `universal_insulin_cap`,
`pillar_two_adoption` and Wave 4's seven international/trade/climate revisions
were already unfitted, so their corrections land entirely inside the
reconstruction column.

The 56.6% on the right is five populations, and they should not be read as one number. **Fifteen are the sectoral presets** (international, trade, pharma, IRS enforcement, climate) at **82.6% mean / 39.0% median** — twelve of them Phase E's, the two tariff rows L8 unfitted, and `ira_enforcement`, which arrived in Wave 4. They ship in the app with an official figure attached and no module constant is fitted to any of them (thirteen of those targets are published scores; two are model estimates — the provenance column says which). **Quote the constant-population figure beside it**: on the fourteen rows the subset held before Wave 4, it is **88.2% mean**, not 82.6%, because the pharma rebuild took `expand_drug_negotiation` from 25.7% to 93.3% and `international_reference_pricing` from 646.2% to **701.0%**. That is a finding rather than a regression, and the lane says why: its own negotiation ladder condemned an unsourced `medicare_part_d_gross_spending_billions = 220.0` that the reference-pricing leg also reads — current law's 160 cumulative selections carry $256.8B of gross Part D spending by 2034, which does not fit inside a $220B total, and CMS's own sentence puts the total at **$281B**. Keeping the unsourced number because it flattered the prediction is the thing the pre-registration protocol exists to stop. The largest row, international reference pricing at 701%, is measured against a target whose own provenance is `model_estimate`; the next two, double IRS enforcement at 82.3% and the auto tariff at 52.8%, are measured against targets `benchmark_sources.py` records as examined-and-left and as revised respectively. **Eight are the Phase D P.L. 119-21 line items** at **35.8% mean**, a much tighter class, unmoved by Wave 4 and detailed below and in §8 of the same file. **Three are the capital-gains scenarios** at **39.6% mean** (CBO +2pp −14.0%, PWBM with step-up −28.4%, PWBM no step-up +76.5%), which arrived in Wave 2 when the constants fitted to them were deleted; because there is no per-case tuple left, these three numbers are identical to the leave-one-out column below, and `run_loo.py --donor-matrix` now prints three identical rows. **One is `extend_tcja_amt` at 66.8%**, which sits here because its target was revised and the AMT constant reproduces the superseded figure. **Five are Wave 4's provenance arrivals** at **9.4% mean** — the best-scoring population in this column, and the reason the pooled mean fell while the model did not improve. Nothing in any of the five was retuned to close a gap — the plan is explicit that a miss gets reported, not calibrated away — and every row carries a `known_limitations` note naming the structural cause.

### Provenance of the targets — what the documents actually say

Phase E's first pass labelled every calibrated target by *inspecting the record*: a deep link meant `line_item`, a round hundred meant `secondhand`. That could tell a rounded headline from a citation. It could not tell whether the row being cited exists. The second pass went and looked, and the transcriptions live in [`fiscal_model/validation/benchmark_sources.py`](../fiscal_model/validation/benchmark_sources.py) — document, table, row, page, date, and the figure that was read, in this repository's sign convention.

| Label | Before (46) | After (46) | Pre-Wave-4 (54) | Live (54) | What it means |
|---|--:|--:|--:|--:|---|
| `line_item` | 4 | **9** | 19 | **30** | The row was found and it says what the target says (within 1.5%). |
| `line_item_differs` | — | **15** | 13 | **5** | The row was found and it says something **else**. |
| `secondhand` | 31 | **15** | 15 | **12** | Searched, not found — and the search is recorded. |
| `model_estimate` | 7 | **7** | 7 | **7** | No official score exists. Illustrations, never counted. |
| `unclassified` | 4 | **0** | 0 | **0** | Nothing is left in the "nobody has looked" bucket. |

Across both tiers the live breakdown is **51 / 5 / 17 / 7 / 0**, and the Generic
tier's own `line_item_differs` count is now **zero** — `biden_high_income_tax`
went through the Tier-1 manifest in Wave 4 rather than the Tier-2 ledger.

So **24 of the 46 calibrated targets the pass covered were read out of a primary document**, against 4 that merely cited one. Of those 24, 15 disagreed with the figure this repository carried. Phase D's eight P.L. 119-21 rows then arrived already transcribed — they *are* their JCT rows, extracted into `pl119_21_jct_line_items.csv` with page references — taking the calibrated tier to **32 `line_item`-family labels across 54 benchmarks, 28 of them actually read** (the remaining 4 cite a document nobody has re-opened and are enumerated in `tests/test_validation_runners.py::CITED_BUT_NOT_TRANSCRIBED`), and the honest calibrated published-target count to **47**. Across both tiers the scorecard holds 80 rows, **73 of them against a published figure**.

Those disagreements have since been resolved by moving the *target* rather than the model, which is why the live column reads **30 / 5** where the transcription pass left **17 / 15**. Two moved in the AMT/insulin pass and one in Wave 3; **Wave 4 (PR #107) moved twelve more and examined four**, closing the list. **Five calibrated disagreements remain, and none of them is an open question** — every one carries a written verdict, and the Generic tier now has none at all:

| Row | Carried | Published | Verdict |
|---|--:|--:|---|
| `pillar_two_adoption` | −$80.0B | −$102.6B | Wave 3 **range revision**, [−$102.6B, +$56.5B]; in-range anchor. Model −$61.2B is **inside**, distance $0.0B |
| `reciprocal_tariffs` | −$1,500.0B | −$1,800.0B | Wave 4 **range revision**, [−$1,800B, −$1,400B]; in-range anchor. Model −$1,396.8B sits **$3.2B outside** the nearer bound |
| `biden_estate_reform` | −$450.0B | −$429.6B | Wave 3 **examined-and-left**: JCT's figure totals a ten-section bill the module does not construct |
| `ctc_extension` | +$600.0B | +$735.3B | Wave 4 **examined-and-left**: CRS's figure is a *superset* (it bundles the Credit for Other Dependents), and JCT's +$816.8B scores a $2,200 indexed credit already carried as `pl119_21_child_tax_credit` |
| `double_enforcement` | −$340.0B | −$320.0B | Wave 4 **examined-and-left**: Treasury's figure is 6% away but scores an **$80B** funding increase on a pre-IRA baseline, where this preset stacks ~$160B on top of the IRA's $80B — the gap argues for moving it, the *dose* against |

Both range rows keep the `line_item_differs` label deliberately, because the anchor is not the transcribed figure and hiding the gap would leave an editorial midpoint looking sourced. `EXAMINED_NOT_REVISED` now holds **five** verdicts — the three above plus `steel_tariff_25` (the 25% Section 232 rate was in force for ten weeks and no scorekeeper published a ten-year estimate; left unsourced and explicitly **not retired**, because retiring a case to avoid reporting an unsourced target is the failure mode the ledger exists to prevent) and `eliminate_mortgage` (no official repeal score exists, and the two published figures come from the **same simulator and differ by 2.4×**). A benchmark may not be both revised and examined-and-left; `target_revision_problems()` fails if one ever is. Without that state a benchmark nobody has examined looks identical to one that was, and the question gets re-opened every pass.

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

**Fifteen** calibrated targets have been **corrected**, not carried — three before Wave 4 and twelve in it. Errors in this table are
**signed** — negative means the model scores below the target — where every other
table on this page reports absolute percent error. All fifteen went through
[`fiscal_model/validation/target_revisions.py`](../fiscal_model/validation/target_revisions.py),
the calibrated tier's mirror of `preregistered.py`'s supersede rule: entered in
one commit and first scored in the next, so "the target moved before the model
was allowed to see it" is checkable from `git log`. **No constant was retuned**,
which is the whole point — a module still fitted to the superseded figure now
reads as a miss, and that miss is the finding. Six of the fifteen rows left the
fitted tier as a mechanical consequence.

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
first entry; Wave 4 added four more, and the registry now holds **five**:

| Row | What was found | Why it was left |
|---|---|---|
| `biden_estate_reform` | JCT letter, 24 Mar 2021, -$429.6B | Totals a ten-section bill against the module's exemption-and-single-rate construction |
| `ctc_extension` | CRS R48286 $735.3B; JCT JCX-35-25 +$816.8B | The first is a **superset** (bundles the Credit for Other Dependents); the second scores a $2,200 indexed credit and is already carried as `pl119_21_child_tax_credit` |
| `double_enforcement` | Treasury AFP Compliance Agenda p. 18, $320B | 6% away, but it is the yield on an **$80B** funding increase on a pre-IRA baseline; this preset stacks ~$160B on top of the IRA's $80B |
| `steel_tariff_25` | Nothing, and now the negative result has a cause | The 25% Section 232 rate was in force **12 March - 3 June 2025**, ten weeks; no scorekeeper published a ten-year estimate of that regime. The nearest figures score the 50% rate with copper folded in, or derivative-rule changes. Left unsourced and **explicitly not retired** — retiring a case to avoid reporting an unsourced target is the failure mode the ledger exists to prevent |
| `eliminate_mortgage` | CRS IF13190 $495B; Yale "close to $1.2 trillion" | The two ten-year repeal figures come from the **same simulator and differ by 2.4×**, and CRS labels its own *"not considered official for revenue scoring purposes"*. That disagreement is itself the argument against adopting either |

A benchmark may not be both revised and
examined-and-left, and `target_revision_problems()` fails if one ever is.

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

#### Illustrations (no official score)

Seven scorecard rows have no published figure behind them at all. They are kept — deleting them would hide model behaviour a user can still trigger from the app — but they are **excluded from every count and every accuracy statistic**, they have their own table in the Validation tab, and the delta column there is labelled as self-comparison.

| Row | "Official" | Model | Δ | What the source string actually says |
|---|--:|--:|--:|---|
| TCJA extension, no SALT cap | $5,700B | $6,494B | +13.9% | The repository's own decomposition of the full-extension benchmark. |
| TCJA rates only | $3,185B | $3,115B | -2.2% | An illustrative slice of the same benchmark. |
| Trump corporate 15% | $1,920B | $1,918B | -0.1% | "No official score; expected estimate derived from model." |
| Eliminate estate tax | $350B | $350B | 0.0% | The source field reads "Model estimate". |
| Expand drug negotiation | -$500B | **-$34B** | **+93.3%** | CBO scored the IRA's 20 drugs (-$237B); 50 drugs is an extrapolation, and since Wave 4 the module prices the expansion through a negotiation ladder that bites in only 6 of the 10 years, because an annual *selection cap* has nothing to raise until 2029. |
| International reference pricing | -$100B | **-$801B** | **-701%** | A RAND price statistic, not a budget score. CBO scored H.R. 3's *narrower* cap — 120% of the average international market price on a limited set of drugs — at about $456B, so a model of capping **all** Medicare drug prices belongs above that figure, not below $200B. |
| Carbon tax $50/ton | -$1,700B | -$1,715B | -0.9% | `climate.py` documents its behavioural factor as calibrated to yield ~$1.7T; the target restates that. |

The other two the expansion plan names (§5.2) are distributional: `TPC_CORPORATE_RATE_INCREASE` and `TPC_CAPITAL_GAINS_INCREASE` are reasoned from an incidence assumption plus a concentration statistic, not copied from a TPC table. They now carry `is_published=False` and sit in `ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS`; `PUBLISHED_DISTRIBUTIONAL_BENCHMARKS` is the set anything may count. **The published distributional quintile set is 2, not 4.**

#### What stayed secondhand, and why

Twelve calibrated targets remain searched and not found (fifteen before Wave 4). Each carries a `searched` record naming the documents checked, so nobody repeats the work. The four that matter most:

- **`ss_donut_250k` (-$2.7T) and `ss_eliminate_cap` (-$3.2T)** are credited to the Social Security Trustees. OCACT *does* score both provisions (E2.5 and E2.1) — and **publishes no dollar figures for them at all**, only percent-of-taxable-payroll (+2.50% and +2.55% of payroll) and trust-fund depletion dates. The widely repeated "$2.7 trillion over 10 years" traces to a think-tank explainer with no report year and no run number. CBO's published figures for the same designs are roughly half: $1,222.6B (2018 volume) and $1,426.8B (2024 volume, Option 62).
- **`repeal_ira_credits` (-$783B)** cites "CBO, budgetary effects of the energy-related tax provisions of P.L. 117-169 (upward revision)". No CBO publication matching that description was located. JCT's original score is -$205.2B (JCX-18-22, Subtitle D) and its score of the enacted terminations is $499.1B (JCX-35-25). The -$783B most likely comes from CRFB reading CBO's 2024 baseline ("closer to $800 billion" through 2033) — a projection of what the credits will *cost*, which is a different quantity from a scored repeal.
- **`cap_employer_health` (-$450B)** is described as a "$50K cap". No agency has ever scored a dollar cap on the exclusion: every published option caps at a *percentile of premiums*, which in dollars is far below $50,000 (CBO's 2013 volume: $6,420 individual / $15,620 family). The -$450B sits inside the spread of CBO's four volumes but corresponds to no alternative in any of them.

Live counts: `python -c "from fiscal_model.validation import compute_scorecard; print(compute_scorecard().calibrated_provenance_breakdown)"`.

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
| Trade | Universal 10% tariff | **-$2,171.1B** | -$1,259B | **42.0%** | Poor | line_item (**target revised** from -$2,000B); unfitted since L8 |
| Trade | 60% China tariff | -$500B | -$278B | **44.3%** | Poor | secondhand; unfitted since L8 |
| Trade | 25% auto tariff | **-$386.2B** | -$182B | **52.8%** | Poor | line_item (**target revised** from -$100B, a per-year claim in a ten-year column) |
| Trade | 25% steel/aluminium tariff | -$60B | -$53B | **11.9%** | Acceptable | secondhand (**examined and left**: the 25% rate lasted ten weeks and nobody scored it) |
| Trade | Reciprocal tariffs (~20pp) | -$1,500B | -$1,397B | **6.9%** | Good | line_item_differs; **target is the range [-$1,800B, -$1,400B]**, model $3.2B outside the nearer bound |
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
expansion bites in 6 of 10 years. Neither target moved; whether -$500B should be
retired for want of a document is an owner decision on the ledger's own terms,
and it is a carry-over. The insulin row is unchanged to the cent.

**Scope note**: Distributional validation is currently benchmarked mainly against published TPC tables rather than a broader CBO distributional set. Payroll / estate scenarios remain higher-error checkpoints; the Biden CTC revenue residual from double-counting growth on window-average annuals is closed (see [VALIDATION_NOTES.md](VALIDATION_NOTES.md)).

**Calibration / holdout note**: The live scorecard and API credibility blocks distinguish specialized calibrated benchmark paths, generic parameterized paths, and the locked post-change holdout protocol (`revenue-scorecard-post-lock-2026-05-02`). Holdout labels are future regression checkpoints, not retroactive historical out-of-sample claims.

### Tier 2 (leave-one-out) — the same modules, held out

The 1.6% above is a bookkeeping number: each calibrated module carries **one hard-coded annual per benchmark**, so it reproduces its own targets because it was told the answer. Leave-one-out asks the question that number cannot: *holding out one benchmark, can the module's structural machinery — calibrated on the others — rebuild it?* Live figures: `python scripts/run_loo.py` (add `--donor-matrix` for the capital-gains diagnostic).

| Module | Kind | n derivable | Mean abs error | Cases (LOO error) |
|---|---|---|---|---|
| **Payroll** | structural | 3 | **3.8%** | eliminate cap −3.7%; $250K donut +1.3%; 90% coverage +6.3% |
| **Estate** | structural | 2 | **10.4%** | extend TCJA exemption +19.2%; Biden $3.5M/45% −1.6% |
| **AMT** | structural | 2 | **73.9%** | extend TCJA relief -37.0%; repeal individual AMT +110.9% |
| **Credits** | structural (CPS ASEC per-unit) | 3 | **18.5%** | Biden CTC 2021 −4.5%; CTC extension +19.0%; childless EITC −32.1% |
| **Expenditures** | bottom-up | 5 | **35.7%** | mortgage −5.1%; SALT-cap repeal −33.5%; SALT elimination +33.5%; charitable cap +13.1%; employer-health cap +93.2% |
| **Capital gains** | structural (frozen elasticities) | 3 | **39.6%** | CBO +2pp −14.0%; PWBM with step-up −28.4%; PWBM no step-up +76.5% |

| Aggregate — derivable cases only | Value |
|---|---|
| Cases in aggregate | 18 |
| Not cross-validatable | 4 (reported alongside, never folded in) |
| Mean absolute error | **29.6%** |
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
provenance alone: three targets moved and no derivation did. The AMT module is
unchanged to the decimal through all of it.

**Read the four numbers separately and never collapse them**: Tier 1 out-of-sample (**18.0%** mean, n=26 pre-registered; 14/26 within 15%, 21/26 within 25%), Tier 2 by construction (**1.6%**, n=23 fitted — or **3.0% over 28** with Wave 4's five revised rows held in place, or 5.2% over 29 with the TCJA-AMT row held in too), Tier 2 unfitted reconstructions (**56.6%** mean / 29.9% median, n=31 — 15 sectoral presets at 82.6%, 8 Phase D P.L. 119-21 line items at 35.8%, 3 capital-gains scenarios at 39.6%, the revised TCJA-AMT-relief row at 66.8% and Wave 4's five provenance arrivals at 9.4%, none fitted to their target), Tier 2 leave-one-out (**29.6%**, n=18 derivable). The last two are the honest statement of how much of the calibrated tier is structure and how much is a stored constant. **Both Tier 2 tiers changed population again in Wave 4, and both means fell while nothing improved, so the constant-population comparisons belong next to them**: the reconstruction tier reads **65.7% / 40.5% over the 26 rows it already held** (against 61.8% / 38.0% before — it got *worse*), and its sectoral subset **88.2% over the 14 it held** (against 81.0%). The leave-one-out suite is the reverse case: it *rose* 28.4% → 29.6% without a single derivation moving.

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
| **Biden 21% to 28%** | **-$1,347B** | **-$1,397B** | **3.7%** | **Excellent** | Treasury |
| Trump 21% to 15% | $1,920B | $1,920B | 0.0% | Excellent | Model |
| TCJA corporate repeal | -$1,400B | -$1,350B | 3.6% | Excellent | JCT |

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
| Trade | 5 | **0** | **31.6%** | 25% auto tariff **52.8%**, now measured against Tax Foundation's published -$386.2B rather than a per-year claim |
| Pharma | 3 | 0 | **277.8%** | International reference pricing **701.0%** (RAND index on all brand spending; still no utilisation or launch-delay response) |
| Enforcement | 2 | **0** | 43.5% | Double IRS enforcement 82.3% (unfitted ROI and decay constants) |
| Climate | 3 | 2 | 8.7% | Repeal EV credits **25.3%**, against JCT's published -$182.3B |

All seventeen average **73.0%**; the fifteen unfitted average **82.6%**. Only
**two** of the seventeen still carry a module constant fitted to their
benchmark — Wave 4's revision of `ira_enforcement`'s target unfitted a third.
**Quote the constant-population reading beside the 82.6%**: on the fourteen
rows the unfitted subset held before Wave 4 it is **88.2%**, because the pharma
rebuild moved two rows away from their targets. The Trade family improved for
the opposite reason — its targets moved onto published documents — and neither
movement is a change in the modules' predictive accuracy on a constant
population.

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
by-construction 1.6% is.

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
