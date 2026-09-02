# Validation expansion plan — out-of-sample and calibrated accuracy

*Drafted 2026-09-01 from a read-only inventory of the validation stack (file:line refs below are as of `main` @ `fc24f91`).*

## 0. Where we actually stand

The footer's "33 policies validated" is computed live from the scorecard and is accurate — but it describes a narrower thing than it sounds:

*Phase A closed rows 1 and 3 of this table on 2026-09-01 — see §1. The pre-Phase-A state is kept below because it is what the plan was written against.*

| | n | what it is | honest status |
|---|---|---|---|
| **Tier 1 — out-of-sample (Generic)** | **4** → **9** → **23** → **26** → **25** | plain `TaxPolicy` on the SOI base, no tuning; ~8% mean error → **44.8%** (Phase A) → **43.4%** across the CBO Options battery (Phase B) → **52.7%** with the enacted-law components (Phase D) → **52.6%** over 25 cases once Phase E's retirement and re-sourcing merge in | the only genuine test; **now pre-registered and CI-gated** (Phase A). Was: *not gated in CI* (`readiness.py:307` exempted Generic; `cold_holdout.py --max-mean-error` was never called by a workflow) |
| **Tier 2 — calibrated** | 29 | 26 module presets + 3 capital-gains cases; ~5% mean error | low by construction: each module carries one hard-coded annual per benchmark (`payroll.py:377-494`, `estate.py:365-525`, `amt.py`, `credits_factory.py`, `tax_expenditures_factory.py`) |
| Benchmark database (`cbo_scores.py` `KNOWN_SCORES`) | 31 → 34 | | **was: 21 entries stranded** — `get_validation_targets()` kept only `income_tax` + `rate_change is not None` + `baseline_year>=2020`. **Now: shape-based dispatch**; 14 runnable, 20 excluded with an explicit one-line reason, 0 unaccounted |
| Presets with an official score (`CBO_SCORE_MAP`) | 47 | | 21 have a live module *and* an official number but **no `validate_all_*` runner** (international 4, tariffs 5, pharma 3, enforcement 2, climate 3, four surtax presets) |
| Distributional (`cbo_distributions.py`) | 6 → **7** real tables | CBO/JCT published distributions; all mapped and CI-gated | fine; the 4 quintile "benchmarks" in `distributional_validation.py` include two that are *not published tables* (corporate, capital gains) and should not be counted |

Three structural weaknesses a referee would find first:

1. **The honest tier is the ungated one.** Tier 1 has no numeric error ceiling in CI and no pre-registration — nothing records that a target was entered *before* the first scoring run.
2. **Round-number tell.** 17 of the 29 calibrated targets are exact round hundreds (450, 350, −1100, −2700, −3200, …): secondhand summaries, not sourced line items.
3. **Calibrated ≠ validated.** With one constant per benchmark, Tier 2's 5% says nothing about predictive skill. Several modules have ≥3 benchmarks, so *leave-one-out* is mechanically possible and has never been run. — *Run in Phase C (§3): **59.3% mean over 18 derivable cases**, plus 4 declared not cross-validatable. The 5% was measuring bookkeeping.*

Expect Tier 1's mean error to **rise** as n grows — the four current cases are friendly shapes. That is the point: a wider, pre-registered, gated error distribution is worth more than a flattering 8% on four cases. *(Outturn: 4 cases 8% → 9 cases 44.8% (Phase A) → 23 cases 43.4% (Phase B). The rise happened at Phase A; Phase B quadrupled the evidence without moving the mean.)*

## 1. Phase A — free wins (no new modelling; ~1 lane) — ✅ **LANDED** (2026-09-01)

1. ✅ **Widen the target filter.** `get_validation_targets()` now dispatches on the record's *shape* (`validation_shape()`: ordinary rate / capital gains / corporate rate / spending) rather than `policy_type == "income_tax"`. Every `KNOWN_SCORES` record is accounted for: **14 runnable** (9 Generic + 5 specialized) and **20 explicitly excluded**, each with a one-line `not_runnable_reason`. `describe_target_coverage()` + `tests/test_validation_targets.py` assert nothing is silently dropped. The spending branch is implemented and unit-tested but has no live record yet — no current spending target states an annual level the source itself published (deriving one from the target would be fitting); it comes online with the Phase B options battery.
2. ✅ **Promote the orphans into Tier 1.** Added `warren_ultramillionaire_surtax_3pp` (−350), `top_rate_45` (−420), `medicare_surcharge_2pp` (−310) from `CBO_SCORE_MAP`, and revived `biden_capital_gains_39` (−456) and `treasury_capgains_39_plus_stepup_elim` (−322). The plan's fourth `CBO_SCORE_MAP` orphan, "Biden 2025 Proposal" (−252), turned out to be the **same Treasury target already carried as `biden_high_income_tax`**, so it was not duplicated. Tier 1: **4 → 9**.
3. ✅ **Pre-registration manifest.** `fiscal_model/validation/preregistered.py` with `assert_preregistered()`; `tests/test_preregistration.py` asserts every Generic entry has a row, targets match `KNOWN_SCORES`, an edited target is rejected (a changed target must be a new row with `superseded_by`), and commit stamps are real shas.
4. ✅ **Gate it.** `validation-dashboard.yml` runs `python scripts/cold_holdout.py --max-mean-error 60 --min-within-25pct 5` as a blocking step (60 = ceil(44.8 × 1.25) rounded up to 5; 5 = current 6-of-9 minus one case). `readiness.py` no longer exempts Generic: `Error` fails, `Poor` fails unless documented.

**Result — the mean rose, as predicted.** Tier 1 is now **9 cases, mean abs error 44.8%, 5/9 within 15%, 6/9 within 25%** (was 4 cases / ~8% / 4-of-4). Three documented tail cases:

| Case | Official | Model | Err | Why it misses |
|---|---:|---:|---:|---|
| Top rate 45% (+8pp) | −420 | −916 | 118% | Single ETI 0.25 understates the response at 8pp **and** the target is secondhand, internally inconsistent with `illustrative_top_rate_5pp` (+5pp/$1M = −700) |
| Biden cap gains 39.6% | −456 | −817 | 79% | Frozen default elasticities (0.8/0.4) with no residual avoidance; official estimates embed far stronger lock-in |
| Treasury 39.6% + step-up | −322 | −817 | 154% | Same shape as the above → same prediction, but the two published targets differ from each other by 42% |

Findings worth carrying forward:

- The anti-leakage invariant still holds comfortably (OOS 44.8% > calibrated 2.7%).
- The `top_rate_45` target fails an internal coherence check against another TPC figure in the same database — Phase E should replace it with a line item or demote it, and the manifest now forces that to be a *new row*.
- The two capital-gains OOS cases are the same policy shape scored against two targets 42% apart, which bounds how well any single model can match both. This is the sharpest available test for Phase C's frozen-elasticity work.

## 2. Phase B — CBO *Options for Reducing the Deficit: 2025–2034* as a pre-registered battery — ✅ **done**

76 options, each with a published 10-year effect ([CBO 60557](https://www.cbo.gov/publication/60557), December 2024; reposted Oct 2025).

1. ✅ Extracted by `scripts/extract_cbo_options.py` (pdfplumber, provenance header) to `fiscal_model/data_files/validation/cbo_options_2025_2034.csv` (one row per option, from Table 1-1, both sign conventions) and `..._alternatives.csv` (one row per reported line in each option's own table — necessary because Table 1-1 reports a *range* whenever an option has several alternatives, and a range cannot be compared with a model score).
2. ✅ Classified in `fiscal_model/validation/cbo_options.py`: **14 runnable alternatives across 11 options; 65 options out of scope**, each with a one-line reason, asserted complete by `tests/test_cbo_options.py`. Slightly under the 15–25 expected, and the shortfall is informative — see the tally below.
3. ✅ Pre-registered in a commit *before* the commit that first scored them (`PHASE_B_ENTERED_COMMIT` / `PHASE_B_FIRST_SCORED_COMMIT` in `preregistered.py`). Vintage-matched on `CBO_FEB_2024` through a new `build_scorer_for_vintage()` in `validation/core.py`; records that name no vintage keep the previous default.

**Baseline the report states** (PDF p. 2): revenue options are measured against CBO's **February 2024** baseline (pub. 59710), spending options against the **June 2024** baseline (pub. 60039). The repo has no June-2024 vintage, so spending rows are scored on Feb 2024 and the mismatch is written on each manifest row.

**Result — Tier 1 is now 23 cases, mean abs error 43.4% (median 23.1%), 6/23 within 15%, 12/23 within 25%** (was 9 / 44.8% / 6-of-9). The mean did not move; the battery *explained* it. CI thresholds re-derived by the workflow's own rule: `--max-mean-error 60 → 55`, `--min-within-25pct 5 → 11`.

Out-of-scope tally:

| Why not runnable | n |
|---|--:|
| Mandatory program-rule change; no funding-level input distinct from the outlay path being predicted | 27 |
| Revenue base or instrument with no module (excise, VAT, FTT, accounting-method timing, filing status, deduction bases, fees) | 23 |
| Discretionary path is a ramp, wind-down or declining caseload, not a level `SpendingPolicy` can express | 12 |
| **Leakage** — the module constant that would score it is calibrated to reproduce that same reform (Options 53, 56, 62) | 3 |

Findings worth carrying forward:

- **The spending shape has no spend-out model.** All five spending cases over-predict because `SpendingPolicy` turns a budget-authority level straight into outlays. Fast-spending programs land at 10–23%; Option 43 (infrastructure and block grants) at 75%. A spend-out rate parameter is the single highest-value fix the battery identified.
- **Option 62 had to be excluded for leakage**, which cost the battery its two largest payroll targets. The payroll module's covered-wage bands are anchored to reproduce the Trustees' 90%-coverage and $250K-donut annuals — i.e. exactly the two alternatives CBO publishes. Phase E should make that dependency explicit in the module docstring.
- **Vintage matching changes none of the 14 scores.** The plumbing works and the two baselines differ ($61.8T vs $61.5T of revenue), but every uncalibrated shape is bottom-up and none reads a level off the baseline. Phase D's baseline-drift concern applies to shapes that scale off baseline aggregates, not to Tier 1 as currently implemented.
- **CBO Option 47 is a third capital-gains data point** with no step-up component, and it over-predicts by 99% — the opposite direction from the two Treasury cases. That localises part of the capital-gains problem to the realizations *base* (the SOI aggregate includes gains facing the 0% rate) rather than only to the elasticities.
- **The corporate shape is 47% off at 1pp** while the calibrated runner reproduces 21%→28% to 3.7%. That is the sharpest available evidence that the calibrated corporate tier is a reconstruction, not a predictor.

## 3. Phase C — leave-one-out for the calibrated modules (turn Tier 2 into a held-out number) — ✅ **done**

Modules with ≥3 benchmarks: payroll (4), tax expenditures (6), credits (3), estate (3), AMT (3), capital gains (3).

1. ✅ For each module, hold out one benchmark, keep the others' calibration, and **re-derive the held-out case bottom-up from the module's structural machinery** (covered-wage bands for payroll; exemption/rate machinery for estate; base tables for expenditures). Where a module's annuals are independent constants (tax expenditures), LOO is only meaningful if the held-out case is rebuilt from the JCX base — do that or exclude the module from the LOO claim.
2. ✅ **Capital gains is the sharpest test**: three cases currently carry three *different* hand-set elasticity/lock-in tuples (`scenarios.py:46-91`). Freeze one elasticity set and score the two orphaned cap-gains targets (Phase A.2) with it — this converts the module's most-tuned parameter into a prediction.
3. ✅ Report a **"Tier 2 (LOO)"** error next to the by-construction number; keep both. Add the LOO run to `run_validation_dashboard.py` with its own ceiling.

**Observed** (`fiscal_model/validation/loo.py`, `python scripts/run_loo.py`):

| Module | Kind | n derivable | not x-val | Mean abs LOO error |
|---|---|---|---|---|
| Payroll | structural (SSA covered-wage bands) | 3 | 1 | **3.8%** |
| Estate | structural (exemption/rate machinery) | 2 | 1 | **25.8%** |
| AMT | structural (taxpayers × avg liability) | 2 | 1 | **79.6%** |
| Credits | structural (per-unit credit identity) | 3 | 0 | **45.1%** |
| Expenditures | bottom-up (JCX-48-24 base table) | 5 | 1 | **39.4%** |
| Capital gains | structural (frozen elasticities) | 3 | 0 | **171.2%** |
| **Aggregate** | | **18** | **4** | **59.3% mean / 35.6% median / 6-of-18 within 15%** |

Against the by-construction 4.4%. CI ceiling `--max-loo-mean-error 75` (observed × 1.25, rounded to 5), wired as its own step in `validation-dashboard.yml` and as a section in `run_validation_dashboard.py`.

Capital-gains answer key (`run_loo.py --donor-matrix`): the `pwbm_39_with_stepup` tuple — 0.8/0.4 with the **5.3× lock-in multiplier** — is the only donor that scores the other two cases tolerably (mean |error| 29.7%, vs 104.8% and 333.2%). Under the frozen literature defaults its own case flips sign (−370.5%): the lock-in multiplier alone produces PWBM's revenue-loss result.

Four cases are declared **not cross-validatable** with a reason rather than given a manufactured number: `expand_niit` (only NIIT benchmark), `eliminate_estate_tax` (target is a model estimate, and the machinery has no revenue *level*), `repeal_corporate_amt` and `eliminate_step_up` (base constant = target/10; caught by a mechanical leakage guard). Two findings for Phase E: `eliminate_salt`'s bottom-up path uses the *post-cap* SALT base instead of `annual_cost_no_cap`, and `cap_employer_health`'s uncalibrated cap rule compares a premium cap against an average *tax benefit* (unit mismatch) — neither affects a scored preset, both block derivation. Details in `docs/VALIDATION_NOTES.md` §6.

Deliverable: a defensible held-out error for ~19 currently circular entries, or an honest statement of which modules cannot be cross-validated and why. — delivered as 18 held-out cases + 4 documented exclusions.

## 4. Phase D — vintage matching and enacted-law replications — ✅ **done**

1. ✅ **The Jan-2025 vintage is sourced, not interpolated.** `CBO_JAN_2025` was a 0.5/0.5 interpolation between the Feb-2024 and Feb-2026 assumption sets and carried **no base levels at all** — it silently fell through to the Feb-2026 hardcoded fallback, so "scored on the January 2025 baseline" was not a true sentence. It now carries the calendar-2025-2034 economic forecast and FY2025 base levels transcribed from CBO, *The Budget and Economic Outlook: 2025 to 2035* ([publication 61172](https://www.cbo.gov/publication/61172)) and its data file (publication 60870), tables B-1 and B-4. One number is derived and labelled: CBO's abbreviated report publishes no defense/nondefense split of discretionary *outlays*, so the $1,847.9B total is split in the Table B-5 budget-authority ratio (47.25 / 52.75). The interpolation is kept and callable as `interpolated_jan_2025_assumptions()`, the documented fallback; `VINTAGE_SOURCING` records which is in force and `tests/test_baseline_vintage.py` pins `sourced`. Sanity: generated FY2025 deficit $1,868B against CBO's $1,865B.
2. ✅ **Enacted-law replications as pre-registered cold predictions.** Three *components* were scored — never a bill total, because the headline score of an enacted law is a net of provisions no single shape can construct. One rule, fixed in the manifest before any of them ran (`PHASE_D_SPENDING_LEVEL_RULE`), set every annual level: the source's own stated funding or benefit change for the first fiscal year the provision is fully in effect, excluding a year the source itself calls retroactive, grown at the module default 2%/yr.

   | Bill | Component | Official | Model | Err | Spend-out? |
   |---|---|---:|---:|---:|---|
   | Social Security Fairness Act 2023 | WEP/GPO repeal, direct spending | +195.65 | +215.4 | 10% | no — benefits are outlaid when owed |
   | Fiscal Responsibility Act 2023 | §101(a) discretionary caps | −1,331.8 | −1,254.2 | 6% | yes, in both directions; the errors cancel |
   | IIJA 2021 | discretionary funding | +415.4 | +1,894.0 | 356% | entirely |

   IRA 2022, Tax Relief for American Families and Workers 2024 and NDAA FY2025 are recorded `out_of_scope` with CBO's component figures: the IRA because every expressible component routes through a module constant calibrated to that same reform (leakage), H.R. 7024 because a $0.4B net of $100B-scale components makes a percentage error meaningless (CBO's own table shows +$117.5B in FY2024 alone), and the NDAA because CBO scores $178M of mandatory changes against $895B authorized.

   Entered in `aed5318`, first scored in `dca3a50`. **Tier 1: 23 → 26 cases, mean 43.4% → 52.7% (median 22.1%), 8/26 within 15%, 14/26 within 25%.** CI thresholds unchanged at `--max-mean-error 55 --min-within-25pct 11`: the widened battery still passes both, and loosening a gate that passes would be tightening in reverse. Anti-leakage invariant holds (52.7% out-of-sample against 2.7% fitted-calibrated).
3. ✅ **P.L. 119-21 provision line items — the first sourced line-item block in the calibrated tier.** JCT published no separate "as enacted" estimate of the tax title; the House passed the Senate substitute unamended, so **JCX-35-25** (1 July 2025, present-law baseline) scores the enacted text. (JCX-34-25 is the same provisions on a current-policy baseline; JCX-36-25/37-25 are distributional.) Thirty-five rows are transcribed with page references into `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv` by `scripts/extract_pl119_21_line_items.py`, which verifies every printed total against the PDF (34/34 found verbatim). JCX-35-25's net total (−$4,474,972M) cross-checks against CBO [publication 61570](https://www.cbo.gov/publication/61570)'s "$4.5 trillion decrease in revenues".

   Eight provisions have a module path, all through `create_tcja_extension`'s component flags, scored on the newly-sourced Jan-2025 vintage over **JCT's own FY2025-2034 window** (the policy takes effect in FY2026, so `Policy.is_active()` leaves FY2025 at the zero JCT prints). **Mean absolute error 35.8%**, 2/8 within 15% — against 0.4% on the aggregate the module's single calibration factor is fitted to. That gap is the finding. All eight are `calibrated_to_target=False`, so they sit in the unfitted-reconstruction tier (12 → 20 entries, 394.1% → 250.8% mean) and never touch the fitted-calibrated mean.

   | Provision | JCT | Model | Err |
   |---|---:|---:|---:|
   | reduced rates | +2,193.4 | +2,752.8 | 25.5% |
   | standard deduction | +1,424.7 | +1,078.9 | −24.3% |
   | personal exemption repeal | −1,807.1 | −989.0 | 45.3% |
   | child tax credit | +816.8 | +863.3 | 5.7% |
   | section 199A | +736.5 | +1,123.9 | 52.6% |
   | estate/gift exemption | +211.7 | +195.2 | −7.8% |
   | AMT exemption | +1,362.8 | +719.3 | −47.2% |
   | SALT limitation | −946.2 | −1,685.8 | −78.2% |

   Twenty further provisions are `out_of_scope` with a reason and never scored. Two are worth naming: **the energy-credit terminations (+$542.7B) are excluded for leakage, not a missing feature** — `climate.py`'s IRA-repeal annual is documented as fitted to the −$783B IRA-repeal target, the third instance of this pattern after Options 53, 56 and 62 — and **the senior deduction has no JCT line item at all**: JCT nets it inside the personal-exemption row, whose printed label says so. The plan asked for it; it cannot be transcribed, and that is recorded rather than approximated.

   Calibrated tier **46 → 54** benchmarks (39 → 47 against a published figure); `line_item` provenance **4 → 12**.
4. ✅ **CBO's distributional analysis of P.L. 119-21 is the 7th real table.** [Publication 61367](https://www.cbo.gov/publication/61367) (11 Aug 2025), Figures 1 and 2, mapped through the existing engine. Registered with CBO's **"federal taxes and cash transfers" column only**: the microsim models neither in-kind transfers nor states' fiscal responses, and those drive the law's regressive *net* result (the bottom decile loses $1,485/yr of Medicaid and SNAP against a $119/yr tax gain). Comparing a tax-only model with CBO's net column would be a category error, so the net column is recorded in the benchmark's notes and is explicitly not what the benchmark tests. **Result: 3.96pp mean absolute share error, rated good — but the top decile is 19.8pp off (36.8% modelled against CBO's 56.6%).** That number matters more than it looks: `distribution_effects.calculate_tcja_effect` builds its decile tiers *out of* CBO 54796 and CBO 60007, so the 0.00pp against `cbo_tcja_2018` is bookkeeping. CBO 61367 is the first distributional table those tiers were not taken from, and the first evidence that they do not travel to a more top-weighted law.

**Findings worth carrying forward:**

- **Vintage matching still moves nothing.** Phase B found it for the bottom-up Tier-1 shapes; Phase D confirms it for the *calibrated* line items too, because `TCJAExtensionPolicy` builds its path from component annuals and never reads a level off the baseline. The value of the vintage work is a manifest that is true, not a number that changed. Baseline drift remains a real contaminant only for shapes that scale off baseline aggregates — and neither tier currently has one.
- **Leakage is now a category, not an accident.** Four exclusions across two phases (Options 53, 56, 62; the P.L. 119-21 energy terminations) share one rule: *a module whose constant was fitted to reform X cannot predict reform X under another name.* Worth stating as a repository-level invariant rather than re-deriving each time.
- **The spend-out gap is the highest-value missing feature, and now has a magnitude.** Seven spending cases, errors 6% to 356%, all one cause. IIJA quantifies the ceiling: $163.0B of front-loaded budget authority produces a $415.4B outlay total that a level shape scores at $1,894B. Spreading the stated five-year authorization evenly still gives $1,013B, so this is not a level-choice artifact.
- **The distributional decile tiers are copied from two CBO TCJA tables.** That makes two of the seven distributional benchmarks circular and should be stated wherever the suite's mean error is quoted. CBO 61367 is the held-out number.

## 5. Phase E — provenance cleanup (may lower the count; raises honesty) — ✅ **done**

*Items 1 and 3 landed 2026-09-01 (`validation/phase-e-runners`); item 2 and the transcription work item 1 explicitly deferred landed the same day on `validation/phase-e-provenance` — see §5b.*

1. ✅ **Provenance flags on every calibrated entry.** `fiscal_model/validation/provenance.py` assigns each benchmark one of `line_item` / `secondhand` / `model_estimate` / `unclassified`, either declared by the runner or inferred from the record's own `official_source`, `benchmark_url` and target roundness — never guessed. No target value changed. Across the 46 calibrated-tier benchmarks: **4 `line_item`, 31 `secondhand`, 7 `model_estimate`, 4 `unclassified`**; the 31 secondhand include exactly the 17 round hundred-scale targets this item named. The headline calibrated count is now stated as **39 against a published figure**, with the 7 model estimates reported separately. `ScorecardSummary` exposes `provenance_breakdown`, `calibrated_provenance_breakdown`, `calibrated_published_entries` and `calibrated_model_estimate_entries`; `/validation/scorecard` serves them. Promoting a `secondhand` target to `line_item` still requires someone to open the document and transcribe the row — deliberately left as work, not asserted. ✅ **Citation fixed — and the plan's own description of it was wrong.** `fiscal_model/tcja.py` labelled publication 59710 "CBO Budget Options"; the plan called it the TCJA-extension cost letter. Both are wrong. **59710 is CBO's February 2024 *Budget and Economic Outlook: 2024 to 2034*** — the baseline Phase B's options battery is scored against. The $4.6T figure comes from **CBO, *Budgetary Outcomes Under Alternative Assumptions About Spending and Revenues*, 8 May 2024, [publication 60271](https://www.cbo.gov/publication/60271)** (JCT's $3.3T of primary deficit plus $467B of debt service). The wrong publication number was attached to the repo's single most load-bearing calibrated benchmark in four places — `tcja.py`, `app_data.py`, the `tcja_extension_full` record in `cbo_scores.py`, and the `tcja_overview` knowledge snapshot — and all four now point at 60271. A test pins the URL so it cannot drift back.
2. ✅ Remove non-published "benchmarks" from every count: `TPC_CORPORATE_RATE_INCREASE`, `TPC_CAPITAL_GAINS_INCREASE` (`distributional_validation.py:80,105`), `eliminate_estate_tax`, `trump_corporate_15`, `tcja_no_salt_cap`, `tcja_rates_only` (`scenarios.py`). Keep them as *illustrations*, labelled. — *Closed in §5b.* Was partly done: all six are enumerated in `provenance.NON_PUBLISHED_BENCHMARK_IDS` / `NON_PUBLISHED_DISTRIBUTIONAL_BENCHMARKS`, the four revenue ones are labelled `model_estimate` and excluded from `calibrated_published_entries`, and a test pins that. The two distributional ones are still counted inside `distributional_validation.py`'s own quintile set; excluding them there is the remaining work.
3. ✅ **Sectoral runners added.** `validate_all_international` (4), `validate_all_trade` (5), `validate_all_pharma` (3), `validate_all_enforcement` (2), `validate_all_climate` (3) in `fiscal_model/validation/specialized_sectoral.py`, wired into `DEFAULT_RUNNERS`. **17 new entries; calibrated tier 29 → 46.** Targets are read live from `CBO_SCORE_MAP` rather than restated, so validation and the app cannot disagree.

**The result is the phase's real finding, and it is not flattering.** Only **5 of the 17** new entries carry a module constant fitted to their benchmark. Scored honestly, the calibrated tier is two populations:

| | n | Mean abs error | Median | Within 15% |
|---|---:|---:|---:|---:|
| Fitted calibrated references | **34** | **2.7%** | 0.2% | 33/34 |
| Unfitted module reconstructions | **12** | **394.1%** | 57.1% | 2/12 |

Nothing was retuned to close a gap; every `Poor` carries a `known_limitations` note naming the structural cause. Highlights (full detail in `docs/VALIDATION_NOTES.md` §7):

- **`pharma.py` has two incidence bugs**, not calibration drift. The universal insulin cap scores at -$445B against -$15B (2,869%) because `_estimate_insulin_savings` credits the whole patient-side cost of insulin to the federal budget for all 8.4M users, and `extend_to_private=True` *raises* the modelled federal saving. International reference pricing scores -$1,388B against -$100B (1,288%) by applying the full US/OECD price-ratio cut to all Medicare drug spending, ignoring Part D rebates.
- **Tariffs miss because the module scores gross customs revenue.** The three unfitted tariff cases (auto 152%, steel 73%, reciprocal 128%) net only an import-demand response; the published figures are net of retaliation and GDP feedback, which the repo's own knowledge snapshot puts at 40–50% of gross.
- **Two `CBO_SCORE_MAP` / `PRESET_POLICIES` key mismatches** ("25% Steel & Aluminum Tariff" vs "25% Steel/Aluminum Tariff"; "Reciprocal Tariffs (~20pp)" vs "Reciprocal Tariffs") mean those two presets show **no official score in the app at all**, and the steel figures in the two dictionaries differ 4x (-$60B vs -$15B). Left for an `app_data.py` change.
- **Pillar Two's 23.5% "error" is target imprecision**: -$80B is the midpoint of a $50–120B range the module itself documents, and the model's -$61B is inside it.
- Several near-zero rows are pure bookkeeping and are now labelled as such — the IRA-repeal annual *is* the -$783B target restated, and `climate.py` documents the carbon-tax behavioural factor as calibrated to produce ~$1.7T.

**Tooling consequences.** `scripts/cold_holdout.py` reports a third tier (`uncalibrated_reconstruction`) so the anti-leakage invariant compares out-of-sample against the *fitted* set — folding the reconstructions in would have flipped it (44.8% vs a 104.8% "calibrated" mean) for entirely the wrong reason. `readiness.py --strict` treats a documented `Poor` on an unfitted reconstruction like a documented out-of-sample miss (warning, not blocker), keyed on a new `calibrated_to_target` flag; a documented `Poor` on a *fitted* benchmark stays strict-blocking, because there it really is a regression.

Net: the calibrated count moved **29 → 46** (39 against published figures, 7 illustrations), while the headline *validated* count is stated as "9 pre-registered out-of-sample cases, mean 44.8%, plus 34 fitted calibrated reconstructions (2.7% by construction, 59.3% leave-one-out) and 12 unfitted module reconstructions at 394.1%". That is the sentence that survives review.

## 5b. Phase E, second pass — the transcription (2026-09-01, `validation/phase-e-provenance`)

Item 1 above labelled targets by *inspecting the record*: a deep link meant `line_item`, a round hundred meant `secondhand`. It closed with an honest admission — "promoting a `secondhand` target to `line_item` still requires someone to open the document and transcribe the row — deliberately left as work, not asserted." This pass did that work, for all 35 targets that were `secondhand` or `unclassified`.

**Provenance tally, before → after** (46 calibrated benchmarks):

| | line_item | line_item_differs | secondhand | model_estimate | unclassified |
|---|--:|--:|--:|--:|--:|
| After item 1 (inferred) | 4 | — | 31 | 7 | 4 |
| After transcription | **9** | **15** | **15** | **7** | **0** |

A fourth label was needed. `line_item_differs` is the case the old scheme could not express: the document was found, the row was read, and it says something else. **24 of 46 targets have now been read out of a primary document, and 15 of those disagree with the figure the repository carries** — one of them in sign. No target was moved: every calibrated target has a module constant fitted to it, so editing one silently converts a 0% row into a miss that says nothing about the model. The published figure rides on `ScorecardEntry.official_10yr_billions_line_item` and every disagreement is tabulated in `docs/VALIDATION.md` as an owner decision.

Transcriptions live in `fiscal_model/validation/benchmark_sources.py` — document, table, row, page, date, figure — and that module is now the *single* source of provenance. The sectoral registries used to restate a `provenance` string of their own; 13 of those 17 were wrong the moment this pass ran, so the literals are gone and `provenance_for()` is the one answer.

**The five findings that outrank the label counts:**

1. **The universal insulin cap benchmark has the wrong sign.** CBO (pub. 57957, H.R. 6833) scores a $35 cap extended to private plans at **+$6.566B of outlays and −$4.793B of revenues** — about **+$11.4B added to the deficit**, not a $15B saving. §5's own finding that `pharma.py` has an incidence bug turns out to have a mirror image on the target side, so the row's 2,869% "error" is measured against a benchmark pointing the wrong way.
2. **`extend_tcja_amt` looks like a five-year figure in a ten-year column.** Published ten-year cost $1,357.1B; published five-year cost $466.2B; carried target $450B.
3. **The estate benchmark was attributed to an agency that never made it.** No Biden Green Book proposes a $3.5M exemption or a 45% rate. The design is the "For the 99.5 Percent Act", scored by JCT at $429.6B — for the whole ten-section bill.
4. **Neither Social Security payroll target has a dollar source.** OCACT scores E2.1 and E2.5 and publishes only percent-of-taxable-payroll (+2.55%, +2.50%) and depletion dates. The "$2.7 trillion" traces to a think-tank explainer with no run number. CBO's figures for the same designs are roughly half.
5. **`repeal_ira_credits` cites a CBO document that does not appear to exist.** The −$783B most plausibly comes from CRFB reading CBO's baseline — a projection of what the credits will cost, not a scored repeal — and the climate module's annual is that target restated, so the 0.0% error was never evidence of anything.

**Item 2 is now fully done.** The two illustrative distributional benchmarks carry `is_published=False` and are split into `ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS`; `PUBLISHED_DISTRIBUTIONAL_BENCHMARKS` is 2, not 4. On the revenue side the headline count moved from `total_entries` to `published_entries` everywhere it is quoted — the app footer and welcome blurb (`validated_policy_count()`), the Validation tab's summary cards and per-policy table, `/validation/scorecard`, README, `docs/VALIDATION.md`, this plan. **61 published benchmarks, not 68 rows.** The 7 illustrations get their own labelled table in the Validation tab with the delta column named as self-comparison.

**Out-of-sample (the plan's §1 leftovers).** Phase A flagged three targets. Reading the documents resolved all three, and not as expected:

- **`top_rate_45` retired.** TPC's full sitemap (~20,600 URLs, ~6,500 model-estimate pages) contains no 45%-ordinary-rate table at any date; CBO and JCT publish no +8pp top-bracket option. PWBM brackets the range at $401.6B / $222.4B, making −$420B implausibly *low*. Withdrawn with the search recorded (`retired=True`, a new manifest field that `manifest_problems()` refuses to accept without a reason), and the unsourced figure deleted from `CBO_SCORE_MAP` so the app stops quoting it.
- **`biden_capital_gains_39` re-sourced, and it scores worse.** −$456B is in no Treasury volume; the FY2025 Green Book's combined row is $288,583M. Superseded `.v1` → `.v2`, with the *shape* moved to the source's definition (taxable income over $1M; $5M per-donor exclusion, not $1M). Error **79% → 142%**.
- **`treasury_capgains_39_plus_stepup_elim` confirmed** at $322,485M (0.15%), shape and all. So the 42% gap between the two was never two published estimates disagreeing — one of them was never published.

Two more Tier 1 targets failed the same sweep and are recorded as open owner decisions rather than acted on, because the plan named only the first: `illustrative_top_rate_5pp` (−$700B, no TPC table) and `warren_ultramillionaire_surtax_3pp` (−$350B against TPC's own T19-0037, which implies ~$175B for 3pp). And `biden_high_income_tax` now has a transcribed row that disagrees with it (−$245.9B vs −$252B); pre-registered targets are frozen, so correcting it needs a new manifest row.

**Tier 1: 23 → 22 cases, mean 43.4% → 42.9%** (median 23.1% → 22.1%; 6/22 within 15%, 12/22 within 25%). The retirement removed a 118% miss and the re-sourcing added a 142% one, which very nearly cancel. Both CI thresholds re-derived by the workflow's own rule and both unchanged at the time: `--max-mean-error 55 --min-within-25pct 11`.

### 5c. Post-merge with Phase D (2026-09-01)

Phase D landed on `main` while this branch was in review, so the two passes are
composed rather than sequential and the live numbers are neither branch's.
`origin/main` was merged in (a merge, not a rebase: the manifest stamps the
commit that entered each target and the commit that first scored it, and a
rebase would rewrite exactly those hashes).

- ✅ **Rebase/merge onto `main` done.** Five conflicts — `CLAUDE.md`,
  `README.md`, `docs/VALIDATION.md`, `preregistered.py`,
  `planning/VALIDATION_EXPANSION.md` — resolved by keeping both sides'
  substance: Phase D's three enacted-law rows, eight P.L. 119-21 line items,
  Jan-2025 vintage and 7th distributional table alongside Phase E's retirement,
  supersession, `line_item_differs` label and published/illustrative split.
- ✅ **Social Security Fairness mis-citation fixed.** §5b reported it; it is now
  corrected. `social_security_fairness_2023` cited publication 59434 (CBO's
  estimate of H.R. 3938, a different bill) and now cites CBO's 9 September 2024
  estimate of H.R. 82, with the unrounded $195.65B component figure recorded
  beside the rounded $196B target. A test pins the URL.
- ✅ **Phase D's benchmarks sourced.** The eight P.L. 119-21 rows get
  `BenchmarkSource` records (JCT's own provision label, PDF page, chapter,
  figure in this repository's sign convention), cross-checked against the CSV
  the runner reads its targets from; the runner stops restating a `provenance`
  literal. The three enacted-law components stay `line_item` on the strength of
  their deep links and join `CITED_BUT_NOT_TRANSCRIBED` — all three cbo.gov
  links still return HTTP 403.

**Post-merge tally (every figure re-derived, not carried over):**

| | n | Mean | Median | Within 15% | Within 25% |
|---|--:|--:|--:|--:|--:|
| Tier 1 — out-of-sample | **25** | **52.6%** | **21.1%** | 8/25 | 14/25 |
| Tier 2 — fitted calibrated | 34 | 2.7% | 0.2% | 33/34 | 34/34 |
| Tier 2 — unfitted reconstructions | 20 | 250.8% | 43.1% | 4/20 | 7/20 |
| — of which Phase E sectoral | 12 | 394.1% | 57.1% | 2/12 | — |
| — of which Phase D P.L. 119-21 | 8 | 35.8% | 35.4% | 2/8 | — |
| Tier 2 — leave-one-out | 18 | 59.3% | 35.6% | 6/18 | — |

Calibrated tier **54**, provenance **17 `line_item` / 15 `line_item_differs` /
15 `secondhand` / 7 `model_estimate` / 0 `unclassified`**, of which 28 were
actually read out of a document and 4 are the cited-but-unread backlog;
**47 calibrated benchmarks against a published figure**. Across both tiers: 79
scorecard rows, **72 published**, 7 illustrations. Distributional: **7 CBO/JCT
tables, 0.00–5.86pp**, two of them circular by construction.

**CI thresholds re-derived by the workflow's own rule, and they part company.**
The rule gives a ceiling of ceil(52.6 × 1.25) rounded up to 5 = **70** and a
floor of 14 − 1 = **13**. The ceiling stays at **55**: raising it is loosening a
gate that passes, which the workflow demands a reason for and there is none.
The floor moves **11 → 13**, the tightening the rule anticipates as the battery
grows — Phase D's "unchanged" left it one derivation behind its own rule.
Anti-leakage invariant holds (52.6% out-of-sample against 2.7% fitted).

**Item 3's leftover fixed.** The two `CBO_SCORE_MAP` / `PRESET_POLICIES` key mismatches §5 identified are reconciled, so the steel/aluminium and reciprocal tariff presets show an official score in the app for the first time. The two `SCORE_ONLY_ALIAS_ID_BY_LABEL` aliases that papered over the share-link half of the problem are gone, and a test pins the general rule: no `CBO_SCORE_MAP` label may resolve to a preset id under a different spelling. **Which steel figure is right is still unknown** — neither −$60B nor −$15B is traceable, and Tax Foundation's only Section 232 metals estimate is at 50% and includes copper — so the reconciliation picked the one that is at least dimensionally a decade figure and recorded the rest.

**Left open, deliberately.** Four calibrated entries are still labelled `line_item` on the strength of a deep link nobody has re-read (`tcja_full_extension`, `cbo_2pp_all_brackets`, and the two PWBM cases); `cbo.gov` returns 403 to every non-browser client, which is also why several CBO figures here are transcribed from CRS reports quoting the CBO table verbatim. `ScorecardEntry.transcribed` is deliberately stricter than the `line_item` label so that backlog is visible and countable, and `tests/test_validation_runners.py::CITED_BUT_NOT_TRANSCRIBED` enumerates it — the set may shrink, never grow.

## 6. Phase F — distributional and microsim reach (later)

Distributional validation is the strongest part of the stack (**7 real tables** after Phase D, CI-gated, 0.0–5.9pp). Growth here is bounded by what the CPS microsim can represent (no itemized deductions beyond SALT, no pass-through/199A, no PTC eligibility, no explicit HOH, **and no in-kind transfers at all** — the reason CBO 61367 could only be registered on its taxes-and-cash-transfers column). ✅ **CBO 61367 (P.L. 119-21) added in Phase D at 3.96pp**, with a 19.8pp top-decile miss that is the first held-out evidence the engine's TCJA decile tiers — copied from CBO 54796 and 60007 — do not travel to a more top-weighted law. Still to add: TPC's OBBBA tables, and CBO's [dynamic estimate of P.L. 119-21](https://www.cbo.gov/publication/61486) as a dynamic-scoring benchmark. Then let the misses drive microsim features — `NEXT_STEPS.md` already queues "Sprint 2: Microsimulation hardening — MFJ brackets, SALT, AMT, EITC, NIIT" and "wire one interaction-heavy benchmark through the microsim path"; the ARP children-in-household gap is new and belongs on that list.

## 7. Sequencing and effort

| Phase | Effort | Tier 1 n after | What it buys |
|---|---|---|---|
| A — filter, orphans, manifest, CI gate ✅ | 1 lane, ~half day | **9** (done) | honest tier becomes gated and prospective |
| B — CBO options battery ✅ | 1–2 lanes | **23** (done) | breadth across tax *and* spending shapes |
| C — leave-one-out | 1 lane per 2–3 modules | — | Tier 2 gets a held-out number |
| D — vintage matching, enacted laws, JCX line items ✅ | 2 lanes | **+3** (done) | sourced Jan-2025 vintage; first line-item block (calibrated 46 → 54); 7th distributional table |
| E — provenance cleanup, missing runners ✅ | 2 lanes | **−1** (one retired, one re-sourced) | count that survives a referee (calibrated 29 → 46; 12 honestly reported as unfitted; 24 targets transcribed, 15 of them disagreeing with their source; headline rows → **published benchmarks**) |
| F — distributional reach | ongoing | — | |

Recommended order: **A → B (with its own vintage matching) → C → D → E** (run as A → B → C → E → D), with the README/`docs/VALIDATION.md` rewritten after C to report the three numbers separately (OOS pre-registered; calibrated by construction; calibrated LOO). Run `python scripts/cold_holdout.py` after each phase and keep the anti-leakage invariant in `test_cold_holdout.py` (OOS error > calibrated error) — if it ever flips, something leaked.
