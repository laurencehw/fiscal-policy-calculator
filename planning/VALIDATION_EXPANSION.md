# Validation expansion plan — out-of-sample and calibrated accuracy

*Drafted 2026-09-01 from a read-only inventory of the validation stack (file:line refs below are as of `main` @ `fc24f91`).*

## 0. Where we actually stand

The footer's "33 policies validated" is computed live from the scorecard and is accurate — but it describes a narrower thing than it sounds:

*Phase A closed rows 1 and 3 of this table on 2026-09-01 — see §1. The pre-Phase-A state is kept below because it is what the plan was written against.*

| | n | what it is | honest status |
|---|---|---|---|
| **Tier 1 — out-of-sample (Generic)** | **4** → **9** → **23** | plain `TaxPolicy` on the SOI base, no tuning; ~8% mean error → **44.8%** (Phase A) → **43.4%** across the CBO Options battery (Phase B) | the only genuine test; **now pre-registered and CI-gated** (Phase A). Was: *not gated in CI* (`readiness.py:307` exempted Generic; `cold_holdout.py --max-mean-error` was never called by a workflow) |
| **Tier 2 — calibrated** | 29 | 26 module presets + 3 capital-gains cases; ~5% mean error | low by construction: each module carries one hard-coded annual per benchmark (`payroll.py:377-494`, `estate.py:365-525`, `amt.py`, `credits_factory.py`, `tax_expenditures_factory.py`) |
| Benchmark database (`cbo_scores.py` `KNOWN_SCORES`) | 31 → 34 | | **was: 21 entries stranded** — `get_validation_targets()` kept only `income_tax` + `rate_change is not None` + `baseline_year>=2020`. **Now: shape-based dispatch**; 14 runnable, 20 excluded with an explicit one-line reason, 0 unaccounted |
| Presets with an official score (`CBO_SCORE_MAP`) | 47 | | 21 have a live module *and* an official number but **no `validate_all_*` runner** (international 4, tariffs 5, pharma 3, enforcement 2, climate 3, four surtax presets) |
| Distributional (`cbo_distributions.py`) | 6 real tables | CBO/JCT published distributions; all mapped and CI-gated | fine; the 4 quintile "benchmarks" in `distributional_validation.py` include two that are *not published tables* (corporate, capital gains) and should not be counted |

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

## 4. Phase D — vintage matching and enacted-law replications

The plumbing exists and is unused: `FiscalPolicyScorer(baseline=CBOBaseline(start_year=…, vintage=BaselineVintage.CBO_FEB_2024).generate())` (`baseline.py:20-24, 216`; `scoring.py:48-61`). Validation code hard-codes the Feb-2026 baseline (`core.py:314, 369`), so a benchmark published on the Jan-2025 baseline is scored on Feb-2026 — baseline drift contaminates every error we report.

1. Score each benchmark on the vintage it was published against. The interpolation problem is confined to benchmarks published on the **Jan-2025** baseline (P.L. 119-21 and its JCT/CBO estimates): `CBO_JAN_2025` is a 0.5-weight interpolation (`baseline.py:76-86`) and needs to become an independently sourced vintage before those targets are scored.
2. **Enacted-law replications as cold predictions**: IIJA 2021 (+256), IRA 2022 (−90), Fiscal Responsibility Act 2023 (−1500), Social Security Fairness Act (+196), P.L. 119-21 — all `SpendingPolicy`/`TaxPolicy`-expressible, all stranded today. Record the prediction first, then look up the CBO score.
3. **P.L. 119-21 provision-level**: JCT's estimate ([JCX-35-25](https://www.jct.gov), present-law baseline) gives line items for TCJA permanence, SALT cap $40K, tips/overtime, CTC $2,200, senior deduction, energy-credit terminations. These become *sourced* calibrated targets (replacing round numbers) and, for provisions the generic path can express, additional Tier 1 cases. CBO's [distributional analysis of P.L. 119-21](https://www.cbo.gov/publication/61367) and [dynamic estimate](https://www.cbo.gov/publication/61486) add a 7th real distributional table and a dynamic-scoring benchmark.

## 5. Phase E — provenance cleanup (may lower the count; raises honesty)

1. Replace the 17 round-hundred calibrated targets with line-item sources (JCX tables, Green Book revenue tables, CBO cost estimates) or mark them `secondhand` in the scorecard and exclude them from the headline count. While auditing: `fiscal_model/tcja.py:20` labels CBO publication 59710 as "CBO Budget Options" — it is the TCJA-extension cost letter behind the $4.6T target, the single most load-bearing calibrated benchmark; fix the citation.
2. Remove non-published "benchmarks" from every count: `TPC_CORPORATE_RATE_INCREASE`, `TPC_CAPITAL_GAINS_INCREASE` (`distributional_validation.py:80,105`), `eliminate_estate_tax`, `trump_corporate_15`, `tcja_no_salt_cap`, `tcja_rates_only` (`scenarios.py`). Keep them as *illustrations*, labelled.
3. Add the runners the 21 module-backed presets lack (`validate_all_international/_trade/_pharma/_enforcement/_climate`) so the calibrated tier reflects the modules that exist — labelled reconstructions, as now.

Net: the calibrated count may move 29 → ~45 while the headline *validated* count is stated as "n pre-registered out-of-sample cases, mean error X, plus n calibrated reconstructions (LOO error Y)". That is the sentence that survives review.

## 6. Phase F — distributional and microsim reach (later)

Distributional validation is the strongest part of the stack (6 real tables, CI-gated, 0.0–2.5pp on TCJA/corporate). Growth here is bounded by what the CPS microsim can represent (no itemized deductions beyond SALT, no pass-through/199A, no PTC eligibility, no explicit HOH). Add CBO 61367 (P.L. 119-21) and TPC's OBBBA tables as targets, then let the misses drive microsim features — `NEXT_STEPS.md` already queues "Sprint 2: Microsimulation hardening — MFJ brackets, SALT, AMT, EITC, NIIT" and "wire one interaction-heavy benchmark through the microsim path"; the ARP children-in-household gap is new and belongs on that list.

## 7. Sequencing and effort

| Phase | Effort | Tier 1 n after | What it buys |
|---|---|---|---|
| A — filter, orphans, manifest, CI gate ✅ | 1 lane, ~half day | **9** (done) | honest tier becomes gated and prospective |
| B — CBO options battery ✅ | 1–2 lanes | **23** (done) | breadth across tax *and* spending shapes |
| C — leave-one-out | 1 lane per 2–3 modules | — | Tier 2 gets a held-out number |
| D — vintage matching, enacted laws, JCX line items | 2 lanes | +5–10 | removes baseline drift; sourced targets |
| E — provenance cleanup, missing runners | 1 lane | — | count that survives a referee |
| F — distributional reach | ongoing | — | |

Recommended order: **A → B (with its own vintage matching) → C → D → E**, with the README/`docs/VALIDATION.md` rewritten after C to report the three numbers separately (OOS pre-registered; calibrated by construction; calibrated LOO). Run `python scripts/cold_holdout.py` after each phase and keep the anti-leakage invariant in `test_cold_holdout.py` (OOS error > calibrated error) — if it ever flips, something leaked.
