# Validation expansion plan — out-of-sample and calibrated accuracy

*Drafted 2026-09-01 from a read-only inventory of the validation stack (file:line refs below are as of `main` @ `fc24f91`).*

## 0. Where we actually stand

The footer's "33 policies validated" is computed live from the scorecard and is accurate — but it describes a narrower thing than it sounds:

| | n | what it is | honest status |
|---|---|---|---|
| **Tier 1 — out-of-sample (Generic)** | **4** | plain `TaxPolicy` on the SOI base, no tuning; ~8% mean error | the only genuine test, and it is tiny; *not gated in CI* (`readiness.py:307` exempts Generic; `cold_holdout.py --max-mean-error` is never called by a workflow) |
| **Tier 2 — calibrated** | 29 | 26 module presets + 3 capital-gains cases; ~5% mean error | low by construction: each module carries one hard-coded annual per benchmark (`payroll.py:377-494`, `estate.py:365-525`, `amt.py`, `credits_factory.py`, `tax_expenditures_factory.py`) |
| Benchmark database (`cbo_scores.py` `KNOWN_SCORES`) | 31 | | **21 entries are stranded** — `get_validation_targets()` (`cbo_scores.py:677-691`) keeps only `income_tax` + `rate_change is not None` + `baseline_year>=2020`, so every tariff, spending, comprehensive-bill and `rate_change=None` score is dead data |
| Presets with an official score (`CBO_SCORE_MAP`) | 47 | | 21 have a live module *and* an official number but **no `validate_all_*` runner** (international 4, tariffs 5, pharma 3, enforcement 2, climate 3, four surtax presets) |
| Distributional (`cbo_distributions.py`) | 6 real tables | CBO/JCT published distributions; all mapped and CI-gated | fine; the 4 quintile "benchmarks" in `distributional_validation.py` include two that are *not published tables* (corporate, capital gains) and should not be counted |

Three structural weaknesses a referee would find first:

1. **The honest tier is the ungated one.** Tier 1 has no numeric error ceiling in CI and no pre-registration — nothing records that a target was entered *before* the first scoring run.
2. **Round-number tell.** 17 of the 29 calibrated targets are exact round hundreds (450, 350, −1100, −2700, −3200, …): secondhand summaries, not sourced line items.
3. **Calibrated ≠ validated.** With one constant per benchmark, Tier 2's 5% says nothing about predictive skill. Several modules have ≥3 benchmarks, so *leave-one-out* is mechanically possible and has never been run. — *Run in Phase C (§3): **59.3% mean over 18 derivable cases**, plus 4 declared not cross-validatable. The 5% was measuring bookkeeping.*

Expect Tier 1's mean error to **rise** as n grows — the four current cases are friendly shapes. That is the point: a wider, pre-registered, gated error distribution is worth more than a flattering 8% on four cases.

## 1. Phase A — free wins (no new modelling; ~1 lane)

1. **Widen the target filter.** Replace the `income_tax`-only gate in `get_validation_targets()` with shape-based dispatch: `TaxPolicy`, `CapitalGainsPolicy`, `SpendingPolicy`, `CorporateTaxPolicy` records all become runnable. This alone revives the stranded entries.
2. **Promote the orphans into Tier 1.** Directly constructible today with no tuning: Warren surtax (−350), Top rate 45% (−420), Medicare surcharge 2pp (−310), "Biden 2025" (−252) from `CBO_SCORE_MAP`; `biden_capital_gains_39` (−456) and `treasury_capgains_39_plus_stepup_elim` (−322) from `KNOWN_SCORES`. Tier 1 goes 4 → ~10.
3. **Pre-registration manifest.** `fiscal_model/validation/preregistered.py`: per OOS case, the official target, source URL/date, the commit hash and date at which the record was entered, and the commit of the first scoring run. Analogous to `holdout.py:39-69`, but for Tier 1 and *prospective*. A test asserts every Generic entry has a manifest row.
4. **Gate it.** Add `python scripts/cold_holdout.py --max-mean-error <N>` (and a within-25% floor) to `validation-dashboard.yml`; drop the Generic exemption in `readiness.py:307`. Pick N from the widened battery, not from the current four.

Deliverable: Tier 1 n≈10, pre-registered, CI-gated. Docs/README report "n, mean abs error, share within 15%/25%" rather than a single percentage.

## 2. Phase B — CBO *Options for Reducing the Deficit: 2025–2034* as a pre-registered battery

76 options, each with a published 10-year effect, built on CBO's **2024** baseline (Feb or June 2024 — confirm from the PDF front matter before entering targets), reposted with updates Oct 2025 ([CBO 60557](https://www.cbo.gov/publication/60557), [PDF](https://www.cbo.gov/system/files/2024-12/60557-budget-options.pdf)). Not referenced anywhere in the repo today.

1. Extract the options table to `fiscal_model/data_files/validation/cbo_options_2025_2034.csv` (title, category, 10-yr $, page, option id) with a script and a provenance header.
2. Classify each option by whether the **uncalibrated** path can express it: ordinary-rate changes (raise all rates 1pp; raise top two rates), surtaxes above $Y, LTCG rate changes, SS taxable-maximum changes, discretionary caps, one-time outlays. Expect **15–25 runnable**; the rest are documented as out of scope (structural benefit changes, Medicare payment rules, etc.).
3. Enter each runnable option through the pre-registration manifest *before* scoring. **Vintage-match inside this phase**: `CBO_FEB_2024` is an independently sourced vintage (`baseline.py:28-44`), so score the battery with `FiscalPolicyScorer(baseline=CBOBaseline(start_year=2025, vintage=BaselineVintage.CBO_FEB_2024).generate())` — no new plumbing needed (validation code today only hard-codes the default at `core.py:314, 369`; nothing anywhere selects a vintage). Publish the full error distribution, including the misses.

Deliverable: Tier 1 n≈25–35 with a genuine spread across tax and spending shapes. This is the highest credibility-per-hour item in the repo.

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
| A — filter, orphans, manifest, CI gate | 1 lane, ~half day | ~10 | honest tier becomes gated and prospective |
| B — CBO options battery | 1–2 lanes | ~25–35 | breadth across tax *and* spending shapes |
| C — leave-one-out | 1 lane per 2–3 modules | — | Tier 2 gets a held-out number |
| D — vintage matching, enacted laws, JCX line items | 2 lanes | +5–10 | removes baseline drift; sourced targets |
| E — provenance cleanup, missing runners | 1 lane | — | count that survives a referee |
| F — distributional reach | ongoing | — | |

Recommended order: **A → B (with its own vintage matching) → C → D → E**, with the README/`docs/VALIDATION.md` rewritten after C to report the three numbers separately (OOS pre-registered; calibrated by construction; calibrated LOO). Run `python scripts/cold_holdout.py` after each phase and keep the anti-leakage invariant in `test_cold_holdout.py` (OOS error > calibrated error) — if it ever flips, something leaked.
