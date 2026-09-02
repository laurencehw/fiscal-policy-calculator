# Model Validation Report

> **Fiscal Policy Calculator — Comparison to Official CBO/JCT Estimates**
>
> Last Updated: September 1, 2026

---

## Executive Summary

The model is benchmarked against **61 published estimates** from CBO, JCT, Treasury, PWBM, and TPC — plus 7 *illustrations* with no official score at all, which are labelled and reported separately and never counted (`published_entries` vs `total_entries` on the scorecard). Crucially, those benchmarks fall into **two epistemically different tiers**, and reporting them together overstates predictive power. Both are reproducible live: `python scripts/cold_holdout.py`. Tier 1 is additionally **pre-registered** (`fiscal_model/validation/preregistered.py`) and **CI-gated**.

### Tier 1 — Out-of-sample predictions (the genuine test)

Policies scored **bottom-up** — IRS SOI filer counts and incomes via raw rate/threshold auto-population, the modules' own revenue identities, and spending levels stated by the source — with **no fitting to the official target** (and, for capital gains, one frozen elasticity set). This is the only tier that measures predictive accuracy.

> **26 out-of-sample cases, mean abs error 52.7%, 8/26 within 15%, 14/26 within 25%** (median 22.1%).
> There is deliberately no single "validated within X%" number: the distribution has a tight core and a long tail, and collapsing it would hide the tail.

*Phase E changed two of these rows, in opposite directions and for the same reason — somebody opened the document. `top_rate_45` was **retired**: its -$420B is in no TPC, CBO or JCT publication. `biden_capital_gains_39` was **re-sourced** from an unsupported -$456B to the FY2025 Green Book's actual line item, -$288.6B, and its shape corrected to the source's own definition, which made it score worse. Details below and in [`preregistered.py`](../fiscal_model/validation/preregistered.py).*

| Case | Official | Model | Err | Source (date) | Baseline the source used | Pre-registered at |
|------|---------:|------:|----:|---------------|--------------------------|-------------------|
| Medicare surcharge 2pp (>$400K) | -$310B | -$315B | 1% | Treasury (2024) | Green Book FY2025 | `6c9bfa2` |
| 1pp all brackets | -$960B | -$935B | 3% | JCT (2023-01) | CBO Feb 2023 | `be7e947` |
| 5pp top rate ($1M+) | -$700B | -$648B | 7% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| 2pp rate cut ($500K+) | +$400B | +$364B | 9% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| Fiscal Responsibility Act: discretionary caps | -$1,332B | -$1,254B | 6% | CBO, H.R. 3746 letter (2023-05) | CBO May 2023 (no vintage in repo) | `aed5318`, scored `dca3a50` |
| Tighten Pell grant eligibility | -$22B | -$24B | 10% | CBO Options 2025-2034 #39 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Social Security Fairness Act: WEP/GPO repeal | +$196B | +$215B | 10% | CBO, H.R. 82 (2024-09) | CBO June 2024 (no vintage in repo) | `aed5318`, scored `dca3a50` |
| Biden top rate 39.6% ($400K+) | -$252B | -$285B | 13% | Treasury (2024-03) — published row is **-$245.9B** | Green Book FY2025 | `be7e947` |
| AGI surtax 2pp (>$100K single) | -$1,051B | -$882B | 16% | CBO Options 2025-2034 #46 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Cut selected nondefense discretionary | -$339B | -$400B | 18% | CBO Options 2025-2034 #42 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Warren surtax 3pp (AGI >$2M) | -$350B | -$283B | 19% | TPC (2020) | unstated (secondhand) | `6c9bfa2` |
| Cut international affairs 25% | -$187B | -$224B | 20% | CBO Options 2025-2034 #37 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| All ordinary rates +1pp | -$1,185B | -$935B | 21% | CBO Options 2025-2034 #45 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| End national community service funding | -$10B | -$13B | 23% | CBO Options 2025-2034 #38 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Top four ordinary brackets +2pp | -$570B | -$716B | 26% | CBO Options 2025-2034 #45 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| AGI surtax 1pp (>$20K single) | -$1,440B | -$797B | 45% | CBO Options 2025-2034 #46 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Corporate rate +1pp (21% to 22%) | -$136B | -$200B | 47% | CBO Options 2025-2034 #64 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| New 1% payroll tax (all earnings) | -$1,282B | -$1,975B | 54% | CBO Options 2025-2034 #61 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| New 2% payroll tax (all earnings) | -$2,540B | -$3,950B | 56% | CBO Options 2025-2034 #61 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Cut certain state and local grants | -$67B | -$117B | 75% | CBO Options 2025-2034 #43 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Biden capital income at ordinary rates | -$289B | -$699B | 142% | Treasury (2024-03), Green Book FY2025 table row | Green Book FY2025 | `0bcfbc3` (`.v2`, superseding `.v1`) |
| Tax accrued gains at death | -$536B | -$84B | 84% | CBO Options 2025-2034 #51 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| LTCG + qualified dividends +2pp | -$103B | -$206B | 99% | CBO Options 2025-2034 #47 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Treasury 39.6% + step-up repeal | -$322B | -$817B | 154% | Treasury (2021-05) | Green Book FY2022 | `d11bf2c`, scored `6c9bfa2` |
| IIJA 2021: discretionary component | +$415B | +$1,894B | 356% | CBO, S.Amdt. 2137 (2021-08) | CBO July 2021 (no vintage in repo) | `aed5318`, scored `dca3a50` |

Live figures: `python scripts/cold_holdout.py`. Rows are the `Generic` category of the scorecard; every one has a row in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py).

#### The CBO Options battery (Phase B)

Fourteen of the 23 cases come from CBO, *Options for Reducing the Deficit: 2025 to 2034* ([publication 60557](https://www.cbo.gov/publication/60557), December 2024; reposted with updates October 2025) — 76 independently scored single-provision options, the largest such published set that exists. They are extracted to `fiscal_model/data_files/validation/cbo_options_2025_2034.csv` (one row per option, from Table 1-1) and `..._alternatives.csv` (one row per reported line in each option's own table) by [`scripts/extract_cbo_options.py`](../scripts/extract_cbo_options.py), and classified in [`fiscal_model/validation/cbo_options.py`](../fiscal_model/validation/cbo_options.py).

**14 runnable alternatives across 11 options; 65 options out of scope, each with a one-line reason.** `tests/test_cbo_options.py` asserts the accounting closes, so no option is silently dropped. Reasons, tallied:

| Why not runnable | n |
|------------------|--:|
| Mandatory program-rule change (benefit formula, eligibility, payment rate). CBO publishes no funding-level *input* distinct from the outlay path being predicted, so feeding the first-year outlay back in would make the "prediction" an aggregation of the target itself. | 27 |
| Revenue base or instrument with no module: excise, VAT, financial transactions, accounting-method timing, filing status, deduction bases, bond and fee schedules, non-covered employment. | 23 |
| Discretionary path that is a ramp, wind-down or declining caseload rather than a level `SpendingPolicy` can express (Options 28-36, 40, 41, 44). | 12 |
| **Leakage.** The module constant that would score it was calibrated to reproduce that same reform from another source: Option 53 (NIIT expansion — the module's $25B/yr is fitted to JCT's estimate of it), Option 56 (employer health — the tax-expenditure annual), Option 62 (Social Security taxable maximum — the covered-wage bands are anchored to reproduce the Trustees' 90%-coverage and $250K-donut annuals). | 3 |

Excluding Option 62 costs the battery its two largest payroll targets, and that is the point: scoring them would have measured bookkeeping, exactly what Tier 2's by-construction number already measures.

**Which spending options qualify** is decided mechanically, not case by case. `SpendingPolicy` produces `level × 1.02**t`, so `is_level_budget_authority_path()` requires CBO's *own* published budget-authority path to stay within 25% of that profile from the first effective year. Five options pass (37, 38, 39, 42, 43); twelve fail. The test is applied to CBO's numbers, never the model's.

**Baseline vintage.** The report states its baselines on page 2: revenue options are measured against CBO's **February 2024** baseline (pub. 59710), spending options against the **June 2024** baseline (pub. 60039). The battery is scored on `BaselineVintage.CBO_FEB_2024` through the new `build_scorer_for_vintage()` in `validation/core.py`; the repository has no June-2024 vintage, and that mismatch is written on every spending row of the manifest rather than left implicit.

Worth stating plainly, because it is a negative result: **vintage matching moves none of these 14 scores.** The two baselines really do differ ($61.8T vs $61.5T of projected revenue), but every uncalibrated shape is bottom-up — SOI filer counts, the module's Medicare revenue identity, a source-stated budget-authority level — and none of them reads a level off the baseline. Baseline drift is a real contaminant for shapes that scale off baseline aggregates (Phase D's concern); it is not one here. The plumbing is in place and honoured, and that is what it buys.

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

| Bill | Expressible component | Level the source states | Official | Model | Err | Spend-out attribution |
|------|----------------------|------------------------:|---------:|------:|----:|-----------------------|
| Social Security Fairness Act of 2023 (H.R. 82) | WEP/GPO repeal, direct spending | +$19.67B (FY2026 outlays; FY2025 carries CBO's retroactive catch-up) | +$195.65B | +$215.4B | 10% | **Not a spend-out case.** Benefits are outlaid in the year they are owed, so there is no authority-to-outlay lag — which is why it is the most accurate of the three. The residual is the model's 2%/yr growth against CBO's ~1.1%/yr. |
| Fiscal Responsibility Act of 2023 (H.R. 3746) | Section 101(a) discretionary caps | -$112.3B (FY2024 budget authority; FY2025 is -$135.9B) | -$1,331.8B | -$1,254.2B | 6% | **A spend-out case in both directions.** CBO outlays -$64.1B in 2024 and -$106.7B in 2025 against authority reductions of -$112.3B and -$135.9B, so the model over-predicts early and under-predicts late (CBO reaches -$159.7B by 2033 against the model's ~-$134B). The two errors largely cancel, so the small total error *flatters* the shape. |
| IIJA 2021 (S.Amdt. 2137 to H.R. 3684) | Discretionary funding and its outlays | +$163.0B (FY2022 budget authority) | +$415.4B | +$1,894.0B | 356% | **Entirely spend-out.** CBO's authority falls $163.0B → $70.1B → $68.5B → $68.1B → $66.2B → ~$2B/yr, producing a humped outlay path peaking at $70.0B in FY2026. `SpendingPolicy` outlays authority 1:1 in the year provided and carries the level forward. |

The IIJA miss is not an artifact of picking the first-year level: spreading the
source's stated FY2022-2026 authorization ($435.9B) evenly over those five years
still yields $1,012.9B against a published $415.4B, because the level shape has
no way to *end* an authorization or to lag an outlay. It is kept in the battery
rather than excluded precisely because it is the sharpest evidence for the
missing spend-out model. No spend-out model was built in Phase D; it belongs to
the modelling plan.

**Three bills were examined and left out of scope, with CBO's component figures
recorded** rather than scored:

| Bill | Official | Why no component is scoreable |
|------|---------:|-------------------------------|
| Inflation Reduction Act 2022 | -$90B | Every component the app can express routes through a module whose constant is calibrated to that same reform — the climate module's IRA-repeal annual is documented as fitted to the -$783B IRA-repeal target, and `repeal_corporate_amt`'s base constant is its own target divided by ten. Scoring it would be leakage, not prediction. |
| Tax Relief for American Families and Workers Act 2024 (H.R. 7024) | +$0.4B | CBO's own table: +$117.5B of deficit in FY2024 netting to +$399M over 2024-2033, because a CTC expansion and R&D expensing are offset by barring new ERTC claims. A percentage error against a $0.4B net of $100B-scale components is uninformative whatever the model does. |
| NDAA FY2025 (S. 4638) | +$0.178B | An authorization bill: CBO scores only $178M of mandatory retirement-benefit changes against $895B authorized. The scored quantity is three orders of magnitude below model resolution, and the $895B is not a budget effect at all. |

#### The misses, grouped by cause

Every miss is kept and carries a `known_limitations` note in the scorecard. Five causes account for all of them:

1. **Budget-authority-to-outlay lag (spending, 7 cases, 6-356%).** `SpendingPolicy` turns an annual funding level straight into outlays; CBO spends that authority out over several years. Option 37 saves -$8B of outlays in 2026 against -$23B of budget authority. The four fast-spending programs land at 10-23%; Option 43 (infrastructure and block grants, the slowest spend-out in the battery, -$0.4B of outlays against -$12.0B of authority in 2026, plus a first year inflated by IIJA advance funding) lands at 75%. Phase D's two enacted-law spending cases bracket the same failure from both ends: the Fiscal Responsibility Act's caps come out at 6% *because* the early over-prediction and the late under-prediction cancel, while IIJA — the most front-loaded appropriation in the set — misses by 356%. This is the single most valuable thing the battery has surfaced: the spending shape has no spend-out model at all.
2. **One threshold standing in for a filing-status-specific boundary (2 cases, 26% and 45%).** "The four highest brackets" and "AGI above $20,000 single / $40,000 joint" are boundaries the generic path cannot express; it carries one number. The error is largest at the low threshold (Option 46 alternative 1, 45%), where the mis-assignment covers most of the filing population.
3. **Module revenue identities applied at the margin (3 cases, 47-99%).** The payroll shape scores a new tax on all earnings off the Medicare identity ($400B at 2.9%), which includes the employer share and no income-tax offset, so it over-predicts by ~55% at both 1% and 2%. The corporate shape applies the full statutory-rate delta to the whole base, over-predicting a 1pp step by 47%. The LTCG shape applies +2pp to the entire SOI realizations aggregate including gains that face the 0% rate, and misses by 99%.
4. **Capital-gains behaviour and the stock of gains at death (3 cases, 79-154%).** The two legacy Treasury cases share one shape and two targets 42% apart. Option 51 is the new information: scoring constructive realization at death runs the whole estimate through one module constant — $54B of gains transferred at death — and under-predicts CBO by 84%, because CBO accrues gains on the stock of appreciated assets held by decedents rather than an annual realizations flow.
5. **A single ETI at a large rate change, against a secondhand target (1 case, 118%).** Unchanged from Phase A; see below.

**Honest reading**: the model predicts ordinary and AGI-inclusive *rate* changes at conventional thresholds well (1-21%), fast-spending discretionary funding cuts adequately (10-23%), and everything behavioural — capital-gains realizations, gains at death, payroll incidence — badly. Phase A's 9-case 44.8% and Phase B's 23-case 43.4% are the same story on four times the evidence: widening the battery did not move the mean, it explained it.

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

**CI gate.** `.github/workflows/validation-dashboard.yml` runs `python scripts/cold_holdout.py --max-mean-error 55 --min-within-25pct 11` as a blocking step (re-derived in Phase B from 60/5 by the workflow's own rule: ceiling = ceil(mean x 1.25) to the nearest 5; floor = current count within 25%, minus one). **Phase D left both thresholds unchanged**: widening the battery to 26 cases raised the mean to 52.7%, still under the 55 ceiling, and the count within 25% rose from 12 to 14, above the floor of 11. Loosening a gate that still passes would be tightening-in-reverse, so nothing moved, and strict readiness (`scripts/check_readiness.py --strict`) no longer exempts Generic entries: an `Error` rating fails, and a `Poor` rating fails unless it carries a documented `known_limitations` note.

### Tier 2 — Calibrated reference models (reconstructions, not confirmations)

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce the published decomposition**. Phase E added five more module families — international, trade, pharma, IRS enforcement, climate — and those turned out to be a different animal, so the tier now splits in two.

| Metric | Calibrated reference (fitted) | Module reconstruction (not fitted) |
|--------|---:|---:|
| Benchmarks | **34** | **20** |
| Mean absolute error | **2.7%** | **250.8%** |
| Median absolute error | 0.2% | 43.1% |
| Within 15% of official | 33/34 | 4/20 |
| Within 25% of official | 34/34 | 7/20 |

The right-hand column grew from 12 to 20 in Phase D, and its mean fell from
394.1% to 250.8% — not because anything improved, but because the eight
P.L. 119-21 line items below are a *tighter* class of unfitted reconstruction
(35.8% mean) than the sectoral modules they were averaged with. The two
populations are described separately for that reason.

The 2.7% on the left is **expected by construction** — those modules carry a constant fitted to each benchmark, so they demonstrate the model's structure and provide auditable, source-linked reconstructions of official scores; they are **not** evidence the model would have predicted them cold. (Earlier revisions of this file quoted 4.4%; the live figure from `python scripts/cold_holdout.py` is 2.7%, and that command is now the only place this number should be read from.)

The 250.8% on the right is two populations, and they should not be read as one number. **Twelve are the Phase E sectoral presets** (international, trade, pharma, IRS enforcement, climate) at **394.1% mean / 57.1% median**: they ship in the app with an official figure attached and no module constant was ever fitted to any of them (ten of those targets are published scores; two are model estimates — the provenance column says which). Two of them, the universal insulin cap and international reference pricing, are off by three and one orders of magnitude respectively and diagnose real incidence bugs in `pharma.py`; see [VALIDATION_NOTES.md](VALIDATION_NOTES.md) §7. **Eight are the Phase D P.L. 119-21 line items** at **35.8% mean**, a much tighter class, detailed below and in §8 of the same file. Nothing in either group was retuned to close a gap — the plan is explicit that a miss gets reported, not calibrated away — and every row carries a `known_limitations` note naming the structural cause.

### Provenance of the targets — what the documents actually say

Phase E's first pass labelled every calibrated target by *inspecting the record*: a deep link meant `line_item`, a round hundred meant `secondhand`. That could tell a rounded headline from a citation. It could not tell whether the row being cited exists. The second pass went and looked, and the transcriptions live in [`fiscal_model/validation/benchmark_sources.py`](../fiscal_model/validation/benchmark_sources.py) — document, table, row, page, date, and the figure that was read, in this repository's sign convention.

| Label | Before | After | What it means |
|---|--:|--:|---|
| `line_item` | 4 | **9** | The row was found and it says what the target says (within 1.5%). |
| `line_item_differs` | — | **15** | The row was found and it says something **else**. |
| `secondhand` | 31 | **15** | Searched, not found — and the search is recorded. |
| `model_estimate` | 7 | **7** | No official score exists. Illustrations, never counted. |
| `unclassified` | 4 | **0** | Nothing is left in the "nobody has looked" bucket. |

So **24 of the 46 calibrated targets have now been read out of a primary document**, against 4 that merely cited one. Of those 24, **15 disagree with the figure this repository carries.**

One access caveat, stated because it shapes several rows: `cbo.gov` returns HTTP 403 to every non-browser client, and `web.archive.org` was unreachable. Where a CBO figure could not be fetched directly it was transcribed from a *published document that quotes the CBO table verbatim* — usually a CRS report, which names the CBO publication in its own source note — and the citation is to what was actually read, never to a PDF nobody opened.

#### `line_item_differs` — the transcription disagrees with the target (owner decisions)

**No target was moved.** Every calibrated target has a module constant fitted to it, so editing one silently converts a 0% row into a miss that says nothing about the model; retuning is a modelling decision and out of scope for a sourcing pass. The published figure rides alongside on `ScorecardEntry.official_10yr_billions_line_item` and is listed here.

| Benchmark | Carried | Published | Δ | The document, and why they differ |
|---|--:|--:|--:|---|
| Universal insulin cap | -$15B | **+$11.4B** | sign flip | CBO pub 57957 (H.R. 6833): +$6.566B of outlays and -$4.793B of revenues, FY2022-2031. CBO scores a private-market insulin cap as *adding* to the deficit. The benchmark points the wrong way — the target half of the same incidence error `pharma.py` carries on the model side. |
| Extend TCJA AMT relief | $450B | **$1,357.1B** | -66.8% | CRS R48286 Table 1 (transcribing CBO pub 60114). The **five**-year figure is $466.2B — the carried target looks like a five-year number sitting in a ten-year column. |
| Repeal FDII | -$200B | **-$158.0B** gross, **$0** net | -26.6% | FY2025 Green Book p. 239. Treasury pairs FDII repeal one-for-one with an R&D-support offset and prints an explicit subtotal of **$0**; the module scores the gross repeal. |
| Eliminate SALT deduction | -$1,200B | **-$1,621.0B** | +26.0% | CBO Option 49 alternative 2 (report p. 59). The clean match to the policy label, on a window in which the $10,000 cap has lapsed. |
| Biden GILTI reform | -$280B | **-$373.9B** | +25.1% | FY2025 Green Book p. 239. (The repository's row *title* is the FY2022 one, which scores $533.5B.) |
| Pillar Two adoption | -$80B | **-$102.6B** | +22.0% | JCX-22-23 Table 2, Scenario 4. The conditioning matters more than the gap: under Scenario 2 — the rest of the world enacts, as it has — JCT scores US adoption at **-$56.5B of receipts**, the opposite sign. |
| CTC extension | $600B | **$735.3B** | -18.4% | CRS R48286 Table 1. Partly definitional: the published figure bundles the Credit for Other Dependents, which the module does not score. |
| IRA enforcement funding | -$200B | **-$180.4B** | -10.9% | CBO pub 58390. CBO revised $203.7B down to $180.4B; the *net* effect is ~$101B after the $79B appropriation, and CBO says $46B of that is enforcement, not the $80B the module assumes. |
| Biden international package | -$700B | **-$632.2B** | -10.7% | FY2025 Green Book p. 240 subtotal. The three provisions the module implements sum to $510.2B, and the "BEAT replacement" in its description is an FY2022 row that no longer exists. |
| Repeal EV credits | -$200B | **-$182.4B** | -9.6% | JCX-35-25: secs. 30D + 45W over FY2025-2034 ($189.8B including sec. 25E). The source was mislabelled CBO. |
| EITC childless expansion | $178B | **$162.6B** | +9.5% | FY2025 Green Book p. 242 (includes the refundable outlay effect). |
| Trump universal 10% tariff | -$2,000B | **-$2,171.1B** | +7.9% | Tax Foundation FF861 Table 3, conventional. Dynamic is $1,721B; with retaliation $1,443B. The bare Yale link was not a citation — Yale publishes no standalone figure for this policy. |
| Double IRS enforcement | -$340B | **-$320.0B** | -6.2% | Treasury, American Families Plan Tax Compliance Agenda p. 18. $320B is the yield on **$80B** of funding; the module scores roughly $160B of funding against it. |
| Estate reform ($3.5M, 45%) | -$450B | **-$429.6B** | -4.7% | JCT letter of 24 March 2021 on the "For the 99.5 Percent Act". **No Biden Green Book ever proposed a $3.5M exemption or a 45% rate** — the "Treasury estimate" attribution was wrong and is corrected. The $429.6B also covers the whole ten-section bill, so it is an upper bound on the exemption-and-rate change alone. |
| Extend enhanced PTCs | $350B | **$335.0B** | +4.5% | CBO pub 60437 (June 2024), FY2025-2034. The carried $350B is CBO/JCT's *September 2025* re-estimate on the FY2026-2035 window: the number and its stated vintage are one budget window apart. |

Plus one out-of-sample row, where the target is frozen by pre-registration: **Biden top rate 39.6%**, carried -$252B against a published **-$245.9B** (2.5%).

#### Illustrations (no official score)

Seven scorecard rows have no published figure behind them at all. They are kept — deleting them would hide model behaviour a user can still trigger from the app — but they are **excluded from every count and every accuracy statistic**, they have their own table in the Validation tab, and the delta column there is labelled as self-comparison.

| Row | "Official" | Model | Δ | What the source string actually says |
|---|--:|--:|--:|---|
| TCJA extension, no SALT cap | $5,700B | $6,494B | +13.9% | The repository's own decomposition of the full-extension benchmark. |
| TCJA rates only | $3,185B | $3,115B | -2.2% | An illustrative slice of the same benchmark. |
| Trump corporate 15% | $1,920B | $1,918B | -0.1% | "No official score; expected estimate derived from model." |
| Eliminate estate tax | $350B | $350B | 0.0% | The source field reads "Model estimate". |
| Expand drug negotiation | -$500B | -$372B | +25.7% | CBO scored the IRA's 20 drugs (-$237B); 50 drugs is an extrapolation. |
| International reference pricing | -$100B | -$1,388B | -1,288% | A RAND price statistic, not a budget score. |
| Carbon tax $50/ton | -$1,700B | -$1,715B | -0.9% | `climate.py` documents its behavioural factor as calibrated to yield ~$1.7T; the target restates that. |

The other two the expansion plan names (§5.2) are distributional: `TPC_CORPORATE_RATE_INCREASE` and `TPC_CAPITAL_GAINS_INCREASE` are reasoned from an incidence assumption plus a concentration statistic, not copied from a TPC table. They now carry `is_published=False` and sit in `ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS`; `PUBLISHED_DISTRIBUTIONAL_BENCHMARKS` is the set anything may count. **The published distributional quintile set is 2, not 4.**

#### What stayed secondhand, and why

Fifteen calibrated targets were searched and not found. Each carries a `searched` record naming the documents checked, so nobody repeats the work. The four that matter most:

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
  Phase B's Options 53, 56 and 62.
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
| International | Biden GILTI reform | -$280B | -$230B | 17.8% | Acceptable | line_item_differs (-$373.9B) |
| International | Repeal FDII | -$200B | -$170B | 15.0% | Acceptable | line_item_differs (-$158.0B gross, $0 net) |
| International | Pillar Two adoption | -$80B | -$61B | 23.5% | Poor | line_item_differs (-$102.6B) |
| International | Biden international package | -$700B | -$413B | 41.0% | Poor | line_item_differs (-$632.2B) |
| Trade | Universal 10% tariff **(fitted)** | -$2,000B | -$2,022B | 1.1% | Excellent | line_item_differs (-$2,171.1B) |
| Trade | 60% China tariff **(fitted)** | -$500B | -$531B | 6.2% | Good | secondhand |
| Trade | 25% auto tariff | -$100B | -$252B | 152.3% | Poor | secondhand (**CRFB publishes no such figure**) |
| Trade | 25% steel/aluminium tariff | -$60B | -$104B | 73.2% | Poor | secondhand (**unsourced at either value**) |
| Trade | Reciprocal tariffs (~20pp) | -$1,200B | -$2,736B | 128.0% | Poor | secondhand (**unsourced; Yale's design is 13pp**) |
| Pharma | Expand drug negotiation | -$500B | -$372B | 25.7% | Poor | model_estimate |
| Pharma | Universal insulin cap | -$15B | -$445B | 2,868.6% | Poor | line_item_differs (**+$11.4B — sign flip**) |
| Pharma | International reference pricing | -$100B | -$1,388B | 1,287.9% | Poor | model_estimate |
| Enforcement | IRA enforcement funding **(fitted)** | -$200B | -$189B | 5.5% | Good | line_item_differs (-$180.4B) |
| Enforcement | Double IRS enforcement | -$340B | -$60B | 82.3% | Poor | line_item_differs (-$320.0B, on half the funding) |
| Climate | Repeal IRA clean-energy credits **(fitted)** | -$783B | -$783B | 0.0% | Excellent | secondhand (**cited CBO document not located**) |
| Climate | Carbon tax $50/ton **(fitted)** | -$1,700B | -$1,715B | 0.9% | Excellent | model_estimate |
| Climate | Repeal EV credits | -$200B | -$228B | 14.2% | Acceptable | line_item_differs (-$182.4B, JCT not CBO) |

**Scope note**: Distributional validation is currently benchmarked mainly against published TPC tables rather than a broader CBO distributional set. Payroll / estate scenarios remain higher-error checkpoints; the Biden CTC revenue residual from double-counting growth on window-average annuals is closed (see [VALIDATION_NOTES.md](VALIDATION_NOTES.md)).

**Calibration / holdout note**: The live scorecard and API credibility blocks distinguish specialized calibrated benchmark paths, generic parameterized paths, and the locked post-change holdout protocol (`revenue-scorecard-post-lock-2026-05-02`). Holdout labels are future regression checkpoints, not retroactive historical out-of-sample claims.

### Tier 2 (leave-one-out) — the same modules, held out

The 4.4% above is a bookkeeping number: each calibrated module carries **one hard-coded annual per benchmark**, so it reproduces its own targets because it was told the answer. Leave-one-out asks the question that number cannot: *holding out one benchmark, can the module's structural machinery — calibrated on the others — rebuild it?* Live figures: `python scripts/run_loo.py` (add `--donor-matrix` for the capital-gains diagnostic).

| Module | Kind | n derivable | Mean abs error | Cases (LOO error) |
|---|---|---|---|---|
| **Payroll** | structural | 3 | **3.8%** | eliminate cap −3.7%; $250K donut +1.3%; 90% coverage +6.3% |
| **Estate** | structural | 2 | **25.8%** | extend TCJA exemption +6.0%; Biden $3.5M/45% +45.6% |
| **AMT** | structural | 2 | **79.6%** | extend TCJA relief +73.2%; repeal individual AMT +86.0% |
| **Credits** | structural | 3 | **45.1%** | Biden CTC 2021 −64.1%; CTC extension −28.0%; childless EITC −43.1% |
| **Expenditures** | bottom-up | 5 | **39.4%** | mortgage −5.1%; SALT-cap repeal +4.0%; charitable cap +15.7%; SALT repeal +74.9%; employer-health cap +97.4% |
| **Capital gains** | structural (frozen elasticities) | 3 | **171.2%** | PWBM no step-up −22.6%; CBO +2pp −120.5%; PWBM with step-up −370.5% |

| Aggregate — derivable cases only | Value |
|---|---|
| Cases in aggregate | 18 |
| Not cross-validatable | 4 (reported alongside, never folded in) |
| Mean absolute error | **59.3%** |
| Median absolute error | 35.6% |
| Within 15% of official | 6/18 (33%) |
| CI ceiling (`--max-loo-mean-error`) | 75% |

**Read the four numbers separately and never collapse them**: Tier 1 out-of-sample (52.7% mean, n=26 pre-registered; 8/26 within 15%, 14/26 within 25%), Tier 2 by construction (2.7%, n=34 fitted), Tier 2 unfitted reconstructions (250.8% mean / 43.1% median, n=20 — 12 Phase E sectoral presets at 394.1% plus 8 Phase D P.L. 119-21 line items at 35.8%, none fitted to their target), Tier 2 leave-one-out (59.3%, n=18 derivable). The last two are the honest statement of how much of the calibrated tier is structure and how much is a stored constant.

And read all four alongside the provenance split above, because a percentage error is only as meaningful as the target it is measured against: **15 of the 54 calibrated targets are now known to disagree with the document they cite**, one of them in sign.

Four cases are **not cross-validatable** and carry a reason rather than a manufactured number: `expand_niit` (the module's only NIIT benchmark — nothing to calibrate the mechanism on), `eliminate_estate_tax` (the target is a model estimate, not a published score, and the machinery reproduces differences but not revenue *levels*), `repeal_corporate_amt` and `eliminate_step_up` (the base constant *is* the published target restated; a leakage guard in `loo.py` catches this mechanically). See [VALIDATION_NOTES.md](VALIDATION_NOTES.md) §6 for the per-module classification and what each error diagnoses.

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
five of the seventeen carry a module constant fitted to their benchmark, and
the other twelve are being compared to their published figure for the first
time. Per-family diagnosis is in [VALIDATION_NOTES.md](VALIDATION_NOTES.md) §7.

| Family | n | Fitted | Mean abs error | Worst case |
|--------|---:|---:|---:|--------|
| International | 4 | 0 | 24.3% | Biden package 41.0% (module implements 3 of the package's provisions) |
| Trade | 5 | 2 | 72.2% | Reciprocal tariffs 128.0% (flat 20pp on half of imports, no retaliation netted) |
| Pharma | 3 | 0 | 1,394.1% | Universal insulin cap 2,868.6% (federal-incidence bug in `pharma.py`) |
| Enforcement | 2 | 1 | 43.9% | Double IRS enforcement 82.3% (unfitted ROI and decay constants) |
| Climate | 3 | 2 | 5.0% | Repeal EV credits 14.2% |

---

## Distributional Validation

### The seven published CBO/JCT tables

`fiscal_model/validation/cbo_distributions.py` carries seven real published
distributional tables, all mapped through
`fiscal_model/validation/benchmark_runners.py` and gated in CI. Live figures:
`python scripts/run_validation_dashboard.py`.

| Benchmark | Source | Grouping | Mean abs share error | Rating |
|---|---|---|---:|---|
| TCJA, calendar 2018 | CBO 54796 | decile | 0.00pp | excellent |
| TCJA conference agreement, 2019 | JCT JCX-68-17 | AGI class | 2.10pp | good |
| ARP refundable credits, 2021 | CBO 56952 | quintile | 4.76pp | good |
| SALT cap repeal, 2024 | JCT JCX-4-24 | AGI class | 5.86pp | acceptable |
| Corporate 21% → 28%, 2022 | JCT JCX-32-21 | AGI class | 2.51pp | good |
| TCJA extension, 2026 | CBO 60007 | decile | 0.74pp | excellent |
| **P.L. 119-21, 2026-2034 average** | **CBO 61367** | **decile** | **3.96pp** | **good** |

**Read the first and sixth rows with care.**
`distribution_effects.calculate_tcja_effect` builds its decile tiers *out of*
CBO 54796 and CBO 60007 — its own docstring says so — so 0.00pp and 0.74pp
against those two tables is bookkeeping, not skill, in exactly the way Tier 2's
by-construction 2.7% is.

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
