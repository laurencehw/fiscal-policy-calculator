# Model Validation Report

> **Fiscal Policy Calculator — Comparison to Official CBO/JCT Estimates**
>
> Last Updated: September 1, 2026

---

## Executive Summary

The model is benchmarked against **50+ official estimates** from CBO, JCT, Treasury, PWBM, and TPC. Crucially, those benchmarks fall into **two epistemically different tiers**, and reporting them together overstates predictive power. Both are reproducible live: `python scripts/cold_holdout.py`. Tier 1 is additionally **pre-registered** (`fiscal_model/validation/preregistered.py`) and **CI-gated**.

### Tier 1 — Out-of-sample predictions (the genuine test)

Policies scored **bottom-up** — IRS SOI filer counts and incomes via raw rate/threshold auto-population, the modules' own revenue identities, and spending levels stated by the source — with **no fitting to the official target** (and, for capital gains, one frozen elasticity set). This is the only tier that measures predictive accuracy.

> **23 out-of-sample cases, mean abs error 43.4%, 6/23 within 15%, 12/23 within 25%** (median 23.1%).
> There is deliberately no single "validated within X%" number: the distribution has a tight core and a long tail, and collapsing it would hide the tail.

| Case | Official | Model | Err | Source (date) | Baseline the source used | Pre-registered at |
|------|---------:|------:|----:|---------------|--------------------------|-------------------|
| Medicare surcharge 2pp (>$400K) | -$310B | -$315B | 1% | Treasury (2024) | Green Book FY2025 | `6c9bfa2` |
| 1pp all brackets | -$960B | -$935B | 3% | JCT (2023-01) | CBO Feb 2023 | `be7e947` |
| 5pp top rate ($1M+) | -$700B | -$648B | 7% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| 2pp rate cut ($500K+) | +$400B | +$364B | 9% | TPC (2023-06) | CBO Feb 2023 | `be7e947` |
| Tighten Pell grant eligibility | -$22B | -$24B | 10% | CBO Options 2025-2034 #39 (2024-12) | CBO June 2024 (scored on Feb 2024) | `752f0f1`, scored `36d683f` |
| Biden top rate 39.6% ($400K+) | -$252B | -$285B | 13% | Treasury (2024-03) | Green Book FY2025 | `be7e947` |
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
| Biden cap gains 39.6% + gains at death | -$456B | -$817B | 79% | Treasury (2024-03) | Green Book FY2025 | `be7e947`, scored `6c9bfa2` |
| Tax accrued gains at death | -$536B | -$84B | 84% | CBO Options 2025-2034 #51 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| LTCG + qualified dividends +2pp | -$103B | -$206B | 99% | CBO Options 2025-2034 #47 (2024-12) | CBO Feb 2024 (matched) | `752f0f1`, scored `36d683f` |
| Top rate to 45% (+8pp >$609,350) | -$420B | -$916B | 118% | TPC (2023) | unstated (secondhand) | `6c9bfa2` |
| Treasury 39.6% + step-up repeal | -$322B | -$817B | 154% | Treasury (2021-05) | Green Book FY2022 | `d11bf2c`, scored `6c9bfa2` |

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

#### The misses, grouped by cause

Every miss is kept and carries a `known_limitations` note in the scorecard. Five causes account for all of them:

1. **Budget-authority-to-outlay lag (spending, 5 cases, 18-75%).** `SpendingPolicy` turns an annual funding level straight into outlays; CBO spends that authority out over several years. Option 37 saves -$8B of outlays in 2026 against -$23B of budget authority. The four fast-spending programs land at 10-23%; Option 43 (infrastructure and block grants, the slowest spend-out in the battery, -$0.4B of outlays against -$12.0B of authority in 2026, plus a first year inflated by IIJA advance funding) lands at 75%. This is the single most valuable thing the battery has surfaced: the spending shape has no spend-out model at all.
2. **One threshold standing in for a filing-status-specific boundary (2 cases, 26% and 45%).** "The four highest brackets" and "AGI above $20,000 single / $40,000 joint" are boundaries the generic path cannot express; it carries one number. The error is largest at the low threshold (Option 46 alternative 1, 45%), where the mis-assignment covers most of the filing population.
3. **Module revenue identities applied at the margin (3 cases, 47-99%).** The payroll shape scores a new tax on all earnings off the Medicare identity ($400B at 2.9%), which includes the employer share and no income-tax offset, so it over-predicts by ~55% at both 1% and 2%. The corporate shape applies the full statutory-rate delta to the whole base, over-predicting a 1pp step by 47%. The LTCG shape applies +2pp to the entire SOI realizations aggregate including gains that face the 0% rate, and misses by 99%.
4. **Capital-gains behaviour and the stock of gains at death (3 cases, 79-154%).** The two legacy Treasury cases share one shape and two targets 42% apart. Option 51 is the new information: scoring constructive realization at death runs the whole estimate through one module constant — $54B of gains transferred at death — and under-predicts CBO by 84%, because CBO accrues gains on the stock of appreciated assets held by decedents rather than an annual realizations flow.
5. **A single ETI at a large rate change, against a secondhand target (1 case, 118%).** Unchanged from Phase A; see below.

**Honest reading**: the model predicts ordinary and AGI-inclusive *rate* changes at conventional thresholds well (1-21%), fast-spending discretionary funding cuts adequately (10-23%), and everything behavioural — capital-gains realizations, gains at death, payroll incidence — badly. Phase A's 9-case 44.8% and Phase B's 23-case 43.4% are the same story on four times the evidence: widening the battery did not move the mean, it explained it.

**What the tight core shows.** Ordinary-bracket rate changes (JCT 1pp, Biden $400K, CBO Option 45) score on the ordinary-income base (excludes preferential LTCG/QDIV); AGI-inclusive surtaxes (TPC $1M+/$500K+, Warren, the Medicare surcharge, CBO Option 46) score on the full taxable-income base that includes the preferential portion. The classification comes from how each source describes its base, not from which choice fits better — the `cold_holdout.py --ordinary-base` diagnostic shows the correction *worsens* the AGI-inclusive cases (7→30%, 9→30%, 2→29%), which is the tell. For ordinary and AGI-inclusive rate changes in this range, **treat uncalibrated custom policies as directional, ±15-25%.**

**The two Phase A tail cases**, unchanged:

- **Top rate to 45% (118%).** The uncalibrated path applies a single ETI (0.25) with the standard 0.5 factor, so an 8pp top-rate increase erodes by only ~12.5% while published top-rate estimates assume a much larger response at that rate level. The target is also suspect: at -$420B it is *smaller* than this database's own +5pp-above-$1M TPC figure (-$700B), i.e. a bigger rate increase on a wider base raising less. Part of this error is target error, and the provenance is a "TPC-range" figure with a bare homepage URL (Phase E).
- **The two Treasury capital-gains cases (79%, 154%).** Both are "39.6% above $1M plus step-up elimination", so the frozen-elasticity path necessarily produces the same prediction (-$817B) for both — while the two published targets differ from each other by 42% (-$322B vs -$456B, different Green Books three years apart). Treasury, JCT and PWBM all assume far stronger lock-in at a 43.4% top rate; the calibrated `CapitalGains` runner needs case-specific multipliers up to 5.3x to reproduce them. CBO Option 47 now adds a *third* capital-gains data point with no step-up component at all, and it misses by 99% in the opposite direction (over-prediction), which localises the problem to the realizations base rather than only the elasticities.

### Pre-registration

Every Tier 1 case is registered in [`fiscal_model/validation/preregistered.py`](../fiscal_model/validation/preregistered.py) with the official target, the publishing source and date, the budget baseline *that source* was scored against, the commit and date at which the record entered the repository, and the commit of the first scoring run.

The discipline the manifest enforces (`assert_preregistered`, tested in `tests/test_preregistration.py`):

0. **The target is entered in a commit before the commit that first scores it.** Phase B's 14 CBO Options rows were entered in `752f0f1` (`PHASE_B_ENTERED_COMMIT`) and first scored in `36d683f` (`PHASE_B_FIRST_SCORED_COMMIT`), which is the commit that flips them to `runnable=True`. A file cannot contain its own hash, so both are stamped in the immediately following commit — the same convention Phase A used.
1. **A target may never be edited to match a model run.** If an official number genuinely changes, the old row is marked `superseded_by` and a **new row with a new `case_id`** is added. The history stays in the file and in the diff.
2. **No case may be scored out-of-sample without a row.** A Generic scorecard entry with no manifest row fails the test.
3. **Misses are kept.** A row is never removed because the model scores it badly.

Honest boundary, as with [`holdout.py`](../fiscal_model/validation/holdout.py): these are previously published numbers, and Phase A registered targets that already existed in the repository or in `CBO_SCORE_MAP`. What the manifest guarantees is that *from the entry commit onward* the target is frozen and any change is visible — not that nobody had ever seen the number.

**CI gate.** `.github/workflows/validation-dashboard.yml` runs `python scripts/cold_holdout.py --max-mean-error 55 --min-within-25pct 11` as a blocking step (re-derived in Phase B from 60/5 by the workflow's own rule: ceiling = ceil(mean x 1.25) to the nearest 5; floor = current count within 25%, minus one), and strict readiness (`scripts/check_readiness.py --strict`) no longer exempts Generic entries: an `Error` rating fails, and a `Poor` rating fails unless it carries a documented `known_limitations` note.

### Tier 2 — Calibrated reference models (reconstructions, not confirmations)

The specialized modules (TCJA, Corporate, Estate, Credits, AMT, Payroll, PTC, Capital Gains, Tax Expenditures) are parameterized so their components **reproduce the published decomposition**. Phase E added five more module families — international, trade, pharma, IRS enforcement, climate — and those turned out to be a different animal, so the tier now splits in two.

| Metric | Calibrated reference (fitted) | Module reconstruction (not fitted) |
|--------|---:|---:|
| Benchmarks | **34** | **12** |
| Mean absolute error | **2.7%** | **394.1%** |
| Median absolute error | 0.2% | 57.1% |
| Within 15% of official | 33/34 | 2/12 |
| Within 25% of official | 34/34 | 4/12 |
| Direction match rate | 34/34 | 12/12 |

The 2.7% on the left is **expected by construction** — those modules carry a constant fitted to each benchmark, so they demonstrate the model's structure and provide auditable, source-linked reconstructions of official scores; they are **not** evidence the model would have predicted them cold. (Earlier revisions of this file quoted 4.4%; the live figure from `python scripts/cold_holdout.py` is 2.7%, and that command is now the only place this number should be read from.)

The 394% on the right is the Phase E finding. Twelve presets ship in the app with an official figure attached, and no module constant was ever fitted to any of them (ten of those targets are published scores; two are model estimates — the provenance column says which). Nothing was retuned to close the gap — the plan is explicit that a miss gets reported, not calibrated away — so each of those rows carries a `known_limitations` note naming the structural cause. Two of them (universal insulin cap, international reference pricing) are off by three and one orders of magnitude respectively and diagnose real incidence bugs in `pharma.py`; see [VALIDATION_NOTES.md](VALIDATION_NOTES.md) §7.

**Provenance of the targets** (`python -c "from fiscal_model.validation import compute_scorecard; print(compute_scorecard().calibrated_provenance_breakdown)"`): of the 46 calibrated-tier benchmarks, **4 are `line_item`** (a specific row in a cited document), **31 are `secondhand`** (a rounded headline figure attributed to an agency but not to a table), **7 are `model_estimate`** (no published score exists at all), and **4 are `unclassified`** (not unambiguously placeable from the record's own source and URL — promoting one needs someone to find the table). The honest headline is therefore **39 calibrated benchmarks against a published figure**, with the 7 model estimates reported separately as labelled illustrations rather than folded into the count.

The six non-published "benchmarks" the expansion plan names (§5.2) are those illustrations: `tcja_no_salt_cap`, `tcja_rates_only`, `trump_corporate_15`, `eliminate_estate_tax` in the revenue scorecard, plus `TPC_CORPORATE_RATE_INCREASE` and `TPC_CAPITAL_GAINS_INCREASE` in the distributional set. They are kept and labelled, never counted.

#### New in Phase E — sectoral module reconstructions

Every target below is read live from `CBO_SCORE_MAP`; none is restated in the validation layer. Rows marked **(fitted)** carry a module constant calibrated to the figure, so their low error is bookkeeping.

| Family | Policy | Official | Model | Error | Rating | Provenance |
|---|---|---:|---:|---:|---|---|
| International | Biden GILTI reform | -$280B | -$230B | 17.8% | Acceptable | secondhand |
| International | Repeal FDII | -$200B | -$170B | 15.0% | Acceptable | secondhand |
| International | Pillar Two adoption | -$80B | -$61B | 23.5% | Poor | secondhand |
| International | Biden international package | -$700B | -$413B | 41.0% | Poor | secondhand |
| Trade | Universal 10% tariff **(fitted)** | -$2,000B | -$2,022B | 1.1% | Excellent | secondhand |
| Trade | 60% China tariff **(fitted)** | -$500B | -$531B | 6.2% | Good | secondhand |
| Trade | 25% auto tariff | -$100B | -$252B | 152.3% | Poor | secondhand |
| Trade | 25% steel & aluminium tariff | -$60B | -$104B | 73.2% | Poor | secondhand |
| Trade | Reciprocal tariffs (~20pp) | -$1,200B | -$2,736B | 128.0% | Poor | secondhand |
| Pharma | Expand drug negotiation | -$500B | -$372B | 25.7% | Poor | model_estimate |
| Pharma | Universal insulin cap | -$15B | -$445B | 2,868.6% | Poor | secondhand |
| Pharma | International reference pricing | -$100B | -$1,388B | 1,287.9% | Poor | model_estimate |
| Enforcement | IRA enforcement funding **(fitted)** | -$200B | -$189B | 5.5% | Good | secondhand |
| Enforcement | Double IRS enforcement | -$340B | -$60B | 82.3% | Poor | secondhand |
| Climate | Repeal IRA clean-energy credits **(fitted)** | -$783B | -$783B | 0.0% | Excellent | secondhand |
| Climate | Carbon tax $50/ton **(fitted)** | -$1,700B | -$1,715B | 0.9% | Excellent | model_estimate |
| Climate | Repeal EV credits | -$200B | -$228B | 14.2% | Acceptable | secondhand |

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

**Read the four numbers separately and never collapse them**: Tier 1 out-of-sample (44.8% mean, n=9 pre-registered; 5/9 within 15%, 6/9 within 25%), Tier 2 by construction (2.7%, n=34 fitted), Tier 2 module reconstructions (394.1% mean / 57.1% median, n=12, published targets no module was fitted to), Tier 2 leave-one-out (59.3%, n=18 derivable). The last two are the honest statement of how much of the calibrated tier is structure and how much is a stored constant.

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
