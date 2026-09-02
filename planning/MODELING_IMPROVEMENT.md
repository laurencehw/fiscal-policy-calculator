# Modeling improvement plan — close the errors by modelling the mechanism

*Written 2026-09-01 against `main` @ `257219b` (Phases A/B/C/E landed: PRs #69, #72, #70, #71).*
*Error budget (§2) and sequencing (§5) re-derived 2026-09-01 against `main` @ `b616144`, after Phase D (enacted-law components, P.L. 119-21 line items) and Phase E provenance landed. Every number below is from `python scripts/cold_holdout.py --json` and `python scripts/run_loo.py --donor-matrix` on that commit, or from a `file:line` in the tree.*

The validation expansion did its job: it replaced a flattering 8% with three honest numbers — **52.6% out-of-sample (n=25)**, **59.3% leave-one-out (n=18 derivable)**, and **250.8% on unfitted module reconstructions (n=20)**, the last of which is itself two populations that must be reported apart: **394.1% across the 12 sectoral presets** and **35.8% across the 8 P.L. 119-21 line items**. This plan spends those numbers. It ranks the work by *error mass × tractability* and says, per lane, which mechanism is missing, what data closes it, which rows should move and in which direction.

> **Waves 1 and 2 have both landed (2026-09-01/02).** The current numbers are
> **31.3% out-of-sample (n=25, median 14.1%, 13 within 15%, 18 within 25%)**,
> **32.3% leave-one-out (n=17 derivable, 5 not cross-validatable)**, and
> **72.1% on the 24 unfitted reconstructions** — 12 sectoral presets at
> **104.8%**, the 8 P.L. 119-21 line items unchanged at **35.8%**, the 3
> capital-gains scenarios Wave 2 unfitted at **39.6%**, and the revised
> `extend_tcja_amt` row at **66.8%**. Fitted calibrated is **2.2% over 30**, or
> 4.2% over 31 with that revised row held in place; the 7 distributional tables
> stay at 0.00–5.86pp. **§2's error budget below is the pre-Wave-1 snapshot on
> `b616144` and is kept as the record the lanes were scoped against**; §5.1 and
> §5.2 carry the two outturns. Live numbers always come from
> `python scripts/cold_holdout.py` and
> `python scripts/run_loo.py --donor-matrix`.

## 1. Principles

1. **Mechanism, not tuning.** A lane succeeds by adding structure that a public-finance referee would recognise (a spend-out profile, a stock of accrued gains, a taxable-estate distribution). It fails the moment it adds a constant that happens to reproduce a target.
2. **The yardstick is frozen.** `scripts/cold_holdout.py`, `scripts/run_loo.py`, `fiscal_model/validation/preregistered.py` and `loo.py`'s leakage guard are not modified by any modelling lane. Targets are not touched (§4).
3. **Pre-register the prediction.** Each lane states, *before* it changes code, which rows it expects to move and roughly how far. A lane that moves rows it did not name has learned something it should write down, not claim.
4. **Regressions count against the lane.** The score is the whole battery. Closing `cbo_opt43` by 55pp while breaking `cbo_opt37` by 20pp is a net 7pp gain, not a win.
5. **Report movement, not attainment.** No lane is allowed to promise "within 15%". Phase E dissolved the old "the two Treasury capital-gains targets disagree by 42%, so 42% is the floor" excuse — the −$456B that produced that gap appears in no Treasury volume. Both targets are now sourced Green Book line items (FY2025 −$288.6B, FY2022 −$322.0B) on designs that genuinely differ, so there is no published-disagreement floor left to hide behind.
6. **Target problems go to the other lane.** Phase E has now done this work and it changed the battery: `top_rate_45` was **retired** (its −$420B is in no TPC, CBO or JCT publication) and `biden_capital_gains_39` was **re-sourced** to the FY2025 Green Book's actual line item, which made it score *worse* (79% → 142%). The remaining target problems — the round-hundred targets, and the mis-signed universal-insulin benchmark (§2.3, L7) — stay provenance work. Reference it; do not redo it.

## 2. Error budget

*Measured on `b616144`, **before Wave 1**. Kept unedited as the record the Wave 1
lanes were scoped and pre-registered against; §5.1 carries the post-Wave-1
re-derivation. Do not quote §2 as current.*

Error mass = Σ|error %| within a tier; share = that mechanism's contribution to the tier mean. Tier 1 total mass **1,315 (25 cases)**; LOO **1,068 (18 derivable)**; unfitted reconstructions **5,016 (20 cases)** — of which **4,729** sits in the 12 sectoral presets and **287** in the 8 P.L. 119-21 line items. Every mass and share below is a sum over the per-case `abs_percent_error` values `cold_holdout.py --json` and `run_loo.py` print; the group masses sum to the tier mass exactly.

### 2.1 Tier 1 — out-of-sample (52.6% mean, 21.1% median, n=25) — *pre-Wave-1*

| Mechanism | Cases | Mass | Share | Tractability |
|---|---|--:|--:|---|
| **Budget-authority → outlay spend-out** | `iija_2021_discretionary` 355.9, `cbo_opt43` 75.5, `cbo_opt38` 23.1, `cbo_opt37` 20.0, `cbo_opt42` 18.0, `cbo_opt39` 10.3, `fra_2023_discretionary_caps` 5.8 | 509 | **38.7%** | **High.** One parameter vector; 14 donor profiles already in the repo's own CSV |
| **Capital gains** — realizations base, lock-in, gains at death | `treasury_capgains_39_plus_stepup_elim` 153.6, `biden_capital_gains_39` 142.3, `cbo_opt47_ltcg_qdiv_2pp` 99.1, `cbo_opt51_gains_at_death` 84.4 | 479 | **36.5%** | Medium. Bounded change; SOI + SCF data must be fetched; 4 OOS + 3 LOO rows test it |
| **Payroll identity at the margin** | `cbo_opt61` 1% 54.1, 2% 55.5 | 110 | 8.3% | Medium. Needs employer-share incidence + income-tax offset, not new data |
| Residual (8 rate cases, 1.5–21.1%) | — | 90 | 6.8% | At the bracket-aggregate ceiling (`VALIDATION_NOTES.md` §5) |
| **Filing-status-specific thresholds** | `cbo_opt46_1pp_20k` 44.7, `cbo_opt45_top4_2pp` 25.8 | 71 | 5.4% | Medium. Needs SOI by filing status; not in scope below |
| **Corporate rate at the margin** | `cbo_opt64` 47.1 | 47 | 3.6% | Low priority; one row |
| **Direct-spending benefit growth rate** | `ssfa_wep_gpo_repeal_outlays` 10.1 | 10 | 0.8% | Low. Explicitly *not* a spend-out case — benefits are outlaid in the year owed; the residual is the model's 2%/yr growth against CBO's ~1.1%/yr |

**Spend-out is now the largest single mass in Tier 1**, and one case is why:
`iija_2021_discretionary` alone carries **356 of the tier's 1,315** — **27% of all
Tier 1 error mass**. Phase D added it as an enacted-law *component*, not a bill
total, under one pre-registered level rule, and it is deliberately not calibrated
away: it is the sharpest evidence in the repository for the missing
budget-authority-to-outlay model that L2 builds. `fra_2023_discretionary_caps`
joins the same row at 5.8% — a small number that *flatters* the shape, because CBO's
early-year and late-year outlay lags there cancel (see
[`docs/VALIDATION.md`](../docs/VALIDATION.md)).

**The ETI row is gone.** Phase E retired `top_rate_45`, taking its 118 of mass out
of the tier along with the only case that was ever attributed to “ETI at a large
rate change”. There is no ETI lane in this plan any more, and none should be
opened on the strength of a target that no publication carries.

**The capital-gains row grew without the model changing.** `biden_capital_gains_39`
moved 79 → 142 purely because Phase E re-sourced its target and corrected its shape
to the source's own definition. That is the correct outcome of a provenance pass,
not a regression — but it means the row's 36.5% share is now measured against a
better target than the one L1 was originally scoped on.

### 2.2 Tier 2 leave-one-out (59.3% mean, 35.6% median, n=18 derivable) — *pre-Wave-1*

*Re-run on `b616144`: unchanged. `run_loo.py` still reports 18 derivable cases, 4 not cross-validatable, aggregate mean 59.3% / median 35.6%, 6/18 within 15%, and the same per-module masses. Phases D and E touched no calibrated module.*

| Module | Cases (LOO error) | Mass | Share | Tractability |
|---|---|--:|--:|---|
| **Capital gains** | `cbo_2pp_all` −120.5, `pwbm_39_with_stepup` −370.5 (sign flip), `pwbm_39_no_stepup` −22.6 | 514 | **48.1%** | Medium — same lane as §2.1 row 1 |
| **Expenditures** | `cap_employer_health` +97.4, `eliminate_salt` +74.9, `cap_charitable` +15.7, `eliminate_mortgage` −5.1, `repeal_salt_cap` +4.0 | 197 | 18.4% | **High.** Two named unit bugs; base field already exists |
| **AMT** | `extend_tcja_amt` +73.2, `repeal_individual_amt` +86.0 | 159 | 14.9% | **High.** Dead code path + missing 2026 ramp |
| **Credits** | `biden_ctc_2021` −64.1, `biden_eitc_childless` −43.1, `ctc_extension` −28.0 | 135 | 12.7% | Medium–low. Needs children/ages from CPS; a rebuild may be required |
| **Estate** | `biden_estate_reform` +45.6, `extend_tcja_exemption` +6.0 | 52 | 4.8% | **High.** One algebraic invariance |
| **Payroll** | −3.7 / +1.3 / +6.3 | 11 | 1.1% | Holds up. Do not touch |

### 2.3 Unfitted module reconstructions (250.8% mean, 43.1% median, n=20) — *pre-Wave-1*

| Mechanism | Cases | Mass | Share | Tractability |
|---|---|--:|--:|---|
| **Pharma incidence** | `universal_insulin_cap` 2868.6, `international_reference_pricing` 1287.9, `expand_drug_negotiation` 25.7 | 4182 | **83.4%** | **Highest.** Two localised bugs; the CBO anchor is already in the file and unread. **But the insulin *target* is mis-signed**: CBO publication 57957 scores a private-market insulin cap at about **+$11.4B** (+$6.566B outlays, −$4.793B revenues, FY2022-2031), i.e. as *adding* to the deficit, against the carried −$15B. The 2868.6% is measured against a benchmark that points the wrong way, so fixing `pharma.py` is necessary but cannot on its own land this row |
| **Tariff pass-through / offsets** | `auto_tariff_25` 152.3, `reciprocal_tariffs` 128.0, `steel_tariff_25` 73.2 | 354 | 7.0% | High. Parameters exist but are wired only to display |
| **Calibration-factor-to-aggregate** (P.L. 119-21 line items) | `pl119_21_salt_cap_40k` 78.2, `qbi_199a` 52.6, `amt_exemption` 47.2, `personal_exemption_termination` 45.3, `rate_extension` 25.5, `standard_deduction` 24.3, `estate_gift_exemption` 7.8, `child_tax_credit` 5.7 | 287 | 5.7% | **Low tractability, highest diagnostic value.** The TCJA module fits **one** calibration factor to CBO's $4.6T aggregate (reproduced to 0.4%) and **no** factor to any component, so it rebuilds JCT's own rows at **35.8% mean**. There is no constant to correct: closing this means giving the module per-provision bases — a rebuild, not a lane |
| **International** | `biden_full_international` 41.0, `pillar_two_adoption` 23.5, `biden_gilti_reform` 17.8, `fdii_repeal` 15.0 | 97 | 1.9% | Medium; two of four are target/scope problems |
| **Enforcement** | `double_enforcement` 82.3 | 82 | 1.6% | Target is not an official score |
| **Climate** | `repeal_ev_credits` 14.2 | 14 | 0.3% | Published figures span an order of magnitude |

**Never quote the 250.8% as one number.** The 12 sectoral rows alone are
**394.1% mean / 57.1% median** (mass 4,729); the 8 P.L. 119-21 rows are
**35.8% mean** (mass 287). They share only the property that no module constant was
fitted to their targets. Phase D moved the tier mean 394.1% → 250.8% purely by
adding the tighter population — nothing improved, and reporting the drop as
improvement would be exactly the error this plan exists to prevent.

## 3. Ranked lanes

Effort in **Opus lanes** (one focused agent session ≈ half a day).

### L1 — Capital gains: stock of accrued gains, decomposed elasticity, gains at death ✅ *shipped, Wave 2 (PR #95) — plus a fifth defect the plan did not name; see §5.2*
**Rank 1** (36.5% of Tier 1 mass + 48.1% of LOO mass). **3 lanes.**

*Mechanism.* Four separable defects, all in the same two files.
- **Base.** `CapitalGainsBaseline` prices realizations off a 3-row aggregate CSV times a hand-written share ladder (`data/capital_gains.py:21-32`) and a statutory proxy (`:95-109`). At threshold 0 it returns 100% of SOI realizations at a 15.5% average rate — including gains that face the **0% bracket**. That single fact is most of `cbo_opt47`'s 99%. Replace with realizations by AGI class × statutory bracket (0/15/20 + NIIT), so a +2pp rate change applies only to gains actually facing the changed rate.
- **Elasticity.** Replace the `short_run 0.8 / long_run 0.4 / transition 3` blend (`policies_core.py:402-406, 442-461`) with an explicit **transitory + permanent** decomposition (Burman & Randolph 1994; Dowd, McClelland & Muthitacharoen 2015, persistent ≈ −0.72, transitory ≈ −1.2; Agersnap & Zidar 2021, −0.3 to −0.5), differing by holding period and by whether the taxpayer faces the top bracket.
- **Lock-in.** Delete `step_up_lock_in_multiplier` (`policies_core.py:411`) and the three per-case tuples in `validation/scenarios.py:63-114`. The 5.3× in `pwbm_39_with_stepup` is an answer key: `run_loo.py --donor-matrix` shows it is the only donor that scores the other two cases, and under frozen defaults its own case flips sign (−370.5%). Lock-in must instead fall out of an accrued-gains stock with a hazard of realization that rises as the rate falls.
- **Gains at death.** `gains_at_death_billions = 54.0` (`policies_core.py:410`) is one constant standing in for CBO's accrual on the **stock** of appreciated assets held by decedents; `estimate_step_up_elimination_revenue` (`:469-484`) multiplies it by an ad-hoc exemption share `min(0.9, 0.4 × $M)`. Model decedent wealth × unrealized-gain share × exemption schedule, indexed to grow with the asset stock.

*Data.* Fetch: IRS SOI *Sales of Capital Assets Reported on Individual Income Tax Returns* (gains by asset type and holding period) and SOI Table 1.4 (gains by AGI class) — irs.gov/statistics; SCF 2022 or Financial Accounts B.101 for the household unrealized-gains stock — federalreserve.gov/econres/scfindex.htm; decedent gains from CBO's Option 51 text and Poterba & Weisbenner (2001). Nothing usable is vendored today (one 3-row CSV).

*Should move.* `cbo_opt47` 99% ↓ (base fix; over-prediction shrinks by roughly the zero-bracket share); `cbo_opt51` 84% ↑ from under- toward the target (stock accrual is larger than a $54B flow); `biden_capital_gains_39` **142%** (was 79% before Phase E re-sourced its target) and `treasury_...` **154%** both ↓. There is no 42% floor to aim at any more — §1.5 — so state the movement, not an attainment band. LOO capital gains 171.2% → target <60% with **one** frozen tuple.

*Tests.* New: base excludes zero-bracket gains; elasticity decomposition reproduces published transitory/permanent split; step-up revenue scales with the stock, not a constant. Guards: 4 Tier 1 rows, 3 LOO rows, `--donor-matrix` must show no single-donor dependence.
*Files.* `fiscal_model/data/capital_gains.py`, `policies_core.py:397-517`, `validation/scenarios.py:63-114`, new `data_files/capital_gains/*`.
*Depends on.* E-provenance for the two Treasury targets (it bounds the attainable error, not the work).

### L2 — Spending: a budget-authority → outlay spend-out model ✅ *shipped, Wave 1 (PRs #85, #88)*
**Rank 2** (38.7% of Tier 1 mass — the largest single mass in the tier since Phase D put IIJA in it — and the highest tractability in the plan). **1 lane.**

*Mechanism.* `SpendingPolicy.get_spending_in_year` (`policies_core.py:568-581`) returns `level × 1.02**t` and the scorer books it as outlays; there is **no spend-out anywhere in the model** (`grep -rn 'spend_out\|outlay_rate' fiscal_model/` returns nothing — scope the grep to `fiscal_model/`, since this plan now names those identifiers itself). Add an outlay vector: `outlays_t = Σ_k s_k · BA_{t−k}`, with `s` a first-year/out-year profile keyed by budget function, and expose `budget_authority` vs `outlays` distinctly on the result.

*Data — already in the repo.* `data_files/validation/cbo_options_2025_2034_alternatives.csv` carries **both** an authority row (`budget_authority` or `spending_authority`) and an `outlays` row for **19 of the 76 options**; only 5 of those are scored, leaving **14 donor profiles** for a leave-one-out fit by function. CBO's own 10-year outlay/BA ratios: #37 0.824, #38 0.798, #39 0.913, #42 0.835, #43 0.693 — the within-window truncation alone is most of the gap. #43's 2026 BA (12.0) also exceeds 2027 (9.3), the IIJA advance-appropriation bulge. Cross-check `s` against OMB Circular A-11 §32 outlay rates.
*Anti-leakage rule.* `s` for a scored case is fitted only on donors from *other* options in the same function. Assert it in a test.

*Should move.* `cbo_opt43_state_local_grants` 75% → ~20%; `cbo_opt37` 20% → <5%; `cbo_opt38` 23% → <10%; `cbo_opt42` 18% → <5%; `cbo_opt39` 10% → ≤10%. **The “Tier 1 mean −4 to −5pp” in the original scoping was computed on the 23-case battery and is now stale in the lane's favour**: `iija_2021_discretionary` (356%, 27% of all Tier 1 mass) and `fra_2023_discretionary_caps` sit in this same mechanism, so the lane must re-derive its expected effect from the 25-case battery before it starts — no new target is asserted here. IIJA is also the one row that tests the *humped* authority path (CBO: $163.0B → $70.1B → $68.5B → ~$2B/yr) rather than a level, which is the harder half of the mechanism. Also removes the `known_limitations` notes at `validation/core.py:176-201`.
*Files.* `policies_core.py:547-581`, `validation/core.py:496-506`, `validation/cbo_options.py`, `scoring_engine.py`.

### L3 — Credits: children (and dependents) from the CPS microdata
**Rank 3** (12.7% of LOO mass; unblocks the ARP distributional gap). **2 lanes** (+1 if the raw-CPS rebuild is in scope).

*Read this first.* All three credit benchmarks set `annual_revenue_change_billions` = target/10 (`credits_factory.py:74, :145, :227`), and `credits_core.py:200-201` short-circuits before the identity at `:203-211`. **The fitted tier cannot move; only the LOO number can.** Three declared policy levers are never read anywhere: `expand_qualifying_age` (`credits_core.py:125`), `include_childless_adults` (`:126`), `take_up_rate_change` (`:129`). `make_fully_refundable` and `remove_phase_out` reach only unreachable flat constants (`:213-218`), and the correct per-unit refundability logic in `calculate_credit_for_income` (`:167-181`) is never called from the revenue path.

*Mechanism.* Compute Δcredit by summing per-unit baseline vs reform credit over the weighted CPS units instead of `Δcredit × units × participation`. The bridge already exists — `policy_to_microsim_reforms` (`distribution_effects.py:785-817`) — but carries only distributional traffic and collapses an EITC schedule reform to one scalar (`:815-817`), which cannot express a childless-only expansion.

*Data.* `microsim/tax_microdata_2024.csv` (7.0 MB, 78,727 rows, 191.1M weighted units) is real CPS ASEC 2024. It has `children` = under-17 headcount (`data_builder.py:280`) **and** `dependent_count` (`:284`), and `dependent_count` is silently dropped by `data/cps_asec.py:48-61` although it differs from `children` on 11.5% of rows — free signal for the EITC qualifying-child base (under 19, or under 24 if a student). **Dependent ages do not survive the build** (only `age_head`, `:308`), so the ARP under-6/6–16 split and any age-17 expansion need a rebuild from raw CPS ASEC 2024 (`pppub24.csv`, `hhpub24.csv`, census.gov) retaining per-dependent `A_AGE`; `data_builder.py:16-42` already reads it.
*Two engine bugs to fix en route.* `engine.py:64` applies a single 21.06% phase-out rate to **all** child counts — the statutory childless rate is 7.65% and `credits_core.py:46` has it right; that is exactly the population `biden_eitc_childless` is about. And engine EITC maxes (`engine.py:58-61`: 632/3995/6604/7430) contradict `credits_core.py:40-81` (632/4213/6960/7830).

*Should move.* LOO credits 45.1% → <20%. ARP distributional children gap ~7pp → <4pp. No Tier 1 row moves.
*Files.* `credits_core.py:190-238`, `credits_factory.py`, `microsim/engine.py:50-64, 264-325`, `data/cps_asec.py:48-61`, `distribution_effects.py:785-817`.

### L4 — Estate: a taxable-estate distribution instead of a two-point blend ✅ *shipped, Wave 2 (PR #93); the growth rate is unresolved, see §5.2*
**Rank 4** (4.8% of LOO mass, but it is an algebraic invariance — cheapest real fix in the plan). **1 lane.**

*Mechanism.* `estimate_taxable_estates` (`estate.py:228-269`) sets, for any exemption `E ≤ $6.4M`, `estates = 19,000 · (6.4M/E)` and `mid_avg = 4M · (E/6.4M)`; the product is **exactly invariant**, and the top-tail blend multiplies both regimes by a constant in that branch, so `estates × avg` is invariant too. Lowering the exemption therefore derives **zero** revenue, and the whole `biden_estate_reform` LOO effect comes from 40%→45%. Replace with a taxable-estate size distribution (Pareto fitted to SOI size classes, or the classes integrated directly) evaluated above the exemption.

*Data.* IRS SOI *Estate Tax Statistics*, Table 1 Parts I & II (returns and net estate tax by size of gross estate) — irs.gov/statistics; already in `VALIDATION_NOTES.md`'s reference list, not in the tree. Kopczuk & Slemrod (2003) for the reported-estate elasticity that should replace `planning_elasticity = 0.15` (`estate.py:105`).
*Should move.* LOO `biden_estate_reform` +45.6% → <15%; `extend_tcja_exemption` +6.0% must not regress. No Tier 1 row.
*Files.* `estate.py:80-107, 228-311`.

### L5 — AMT: a live exemption path and a 2026 sunset ramp ✅ *shipped, Wave 1 (PR #86) — but there was no ramp; see §5.1*
**Rank 5** (14.9% of LOO mass). **1 lane.**

*Mechanism.* Two defects. (i) The exemption-change branch is **dead**: `estimate_static_revenue_effect` computes `baseline_taxpayers` and `policy_taxpayers` from the *same* call `self.estimate_affected_taxpayers(...)` (`amt.py:357, 360`), so it always returns 0, and three expressions above it (`:349-359`) are evaluated and discarded. Compute the baseline count from the current-law schedule and the policy count from the reform schedule. (ii) There is **no ramp**: the identity gives the steady-state post-sunset level (~$73B/yr, matching `revenue_post_tcja_2030 = 75.0`, `amt.py:119`) while the official $450B/10yr prices a window that ramps from the 2026 sunset. Add a year-indexed affected-count and average-liability path.

*Data.* TPC model estimates for AMT taxpayers by year 2026–2034 (taxpolicycenter.org/model-estimates); JCT's TCJA-sunset tables. `AMT_EXEMPTIONS_TCJA` already carries the year keys.
*Should move.* LOO `extend_tcja_amt` +73.2% and `repeal_individual_amt` +86.0% → both <25%. No Tier 1 row.
*Files.* `amt.py:112-145, 275-370`.

### L6 — Tax expenditures: bases with the right units ✅ *shipped, Wave 2 (PR #94) — `cap_employer_health` cannot reach <25%, see §5.2*
**Rank 6** (18.4% of LOO mass; two named unit bugs). **1 lane.**

*Mechanism.* (a) `eliminate_salt` derives against `annual_cost = 25.0` — the **post-cap** expenditure — while `annual_cost_no_cap = 120.0` sits in the same record (`tax_expenditures_core.py:66-67`) and is read only by the repeal-cap branch (`:256`). (b) `cap_employer_health` compares a $50,000 cap on excludable **premiums** against `avg_benefit = 1_600`, the average **tax benefit** (`:237-243`), concluding 0.32% of the base is affected. Fix is not two constants: give each expenditure a benefit distribution by AGI class so a cap is applied to the quantity it caps, and make eliminate/cap/limit rules declare their units.

*Data.* JCT, *Estimates of Federal Tax Expenditures for Fiscal Years 2024–2028*, JCX-48-24 (jct.gov) — distribution tables, not just totals; the repo has a curated snapshot at `assistant/knowledge/jct_tax_expenditures.md`. Employer-premium distribution: MEPS-IC (meps.ahrq.gov) or KFF *Employer Health Benefits Survey*.
*Should move.* LOO `cap_employer_health` +97.4% → <25%; `eliminate_salt` +74.9% → <20%; mortgage/SALT-cap/charitable must not regress. Unblocks CBO Option 56 for a future Tier 1 promotion.
*Files.* `tax_expenditures_core.py:33-100, 215-270`.

### L7 — Pharma: fix the two incidence bugs, then model the Part D channels ✅ *incidence bugs fixed, Wave 1 (PR #87); Part D channels still open*
**Rank 7 by tier weight, but the highest raw error mass in the repo (83.4% of the reconstruction mass) and the smallest diff.** **1 lane.**

*Mechanism.* (a) `_estimate_insulin_savings` (`pharma.py:165-185`) books `(6000 − 420) × 8.4M` — the full retail-minus-cap differential for every user — as a federal outlay reduction, and `extend_to_private=True` sets `medicare_share = 1.0` (`:182-183`), so extending a cap to private insurance *raises* the modelled federal saving 2.5×. Score only the federal share: Part D plan liability net of direct/indirect remuneration rebates, plus reinsurance and low-income-subsidy channels; the private extension contributes ≈0 federally. **`CBO_PHARMA_ESTIMATES["insulin_cap"]["10yr_score"] = -6.4` already sits at `pharma.py:65-69` and is read by no code path.** (b) `_estimate_reference_pricing_savings` (`:187-204`) applies RAND's **gross-list-price** ratio 2.56 to **net** Part B + D spending ($275B) with no rebate adjustment and no branded/generic split (US generics are cheaper than OECD). Apply the ratio to a net-price base and restrict to brand molecules.

*Data.* MedPAC *Report to the Congress: Medicare Payment Policy*, Part D chapter (gross-to-net and rebate share); CMS Part D Drug Spending Dashboard; CBO's IRA drug-pricing estimates. No such field exists in `PHARMA_BASELINE` today (`pharma.py:39-52`), and `part_d_oop_cap` at `:48` is defined and never read.
*Should move.* `international_reference_pricing` 1287.9% → <100%. **Sectoral reconstruction mean 394.1% → ~40%** — that target was set against the 12-row sectoral subset and stays measured there, not against the 20-row tier's 250.8%. Also delete the dead `"medicare_insulin_share": 0.4` copy-paste at `enforcement.py:38`.

*Target caveat — read before scoping the insulin row.* `universal_insulin_cap`'s benchmark has the **wrong sign**. CBO publication 57957 (H.R. 6833) scores a private-market insulin cap at +$6.566B of outlays and −$4.793B of revenues over FY2022-2031, i.e. about **+$11.4B of deficit**, against the carried −$15B of savings. So the 2868.6% is the model error *and* the target error compounded, and the correct federal-share model will not converge on the stored number. This lane fixes the incidence bug; the superseding manifest row is provenance work (§1.6), and until it lands no percentage target should be written for this row at all.
*Caveat.* This changes shipped user-facing preset output, not only a validation number.

### L8 — Tariffs: pass-through, retaliation, and the income/payroll offset
**Rank 8** (7.0% of reconstruction mass). **1 lane.**

*Mechanism.* `estimate_static_revenue_effect` (`trade.py:99-118`) returns **gross customs revenue** with a flat 5% avoidance haircut (`:120-121`). `pass_through_rate = 0.60` (`:87`) and `retaliation_rate = 0.30` (`:89`) exist but feed only display paths (`estimate_consumer_cost` `:123-127`, `estimate_retaliation_cost` `:129-134` → `get_trade_summary` `:140-152`). There is **no income/payroll offset at all** — JCT scores indirect taxes net of a ~25% income-and-payroll offset, and the repo's own knowledge snapshot puts the net figure at 40–50% of gross. Route the import-demand response through the pass-through-adjusted price change, net retaliation's effect on export-linked receipts, and subtract the offset. Also: `create_reciprocal_tariffs` hard-codes a 0.5 coverage literal (`:214`) that belongs in `TRADE_BASELINE`, and `create_steel_tariff_25` (`:199-206`) applies the full 25pp with no netting of Section 232 duties already in force.

*Data.* Yale Budget Lab, *State of U.S. Tariffs* methodology (budgetlab.yale.edu); Amiti, Redding & Weinstein (2019, *JEP*) and Fajgelbaum et al. (2020, *QJE*) on near-complete pass-through; JCT's revenue-offset convention; CBO's tariff estimates for a gross/net check. `CBO_TRADE_ESTIMATES` (`trade.py:58-71`) is defined and unread.
*Should move.* `auto_tariff_25` 152.3%, `reciprocal_tariffs` 128.0%, `steel_tariff_25` 73.2% → all <40%. The two fitted coverage constants (`universal_coverage_rate`, `china_effective_coverage`) should be re-derivable rather than fitted afterwards.
*Depends on.* The `app_data.py` key mismatch (`CBO_SCORE_MAP` "25% Steel & Aluminum Tariff" vs `PRESET_POLICIES` "25% Steel/Aluminum Tariff"; same for reciprocal) — a separate one-file fix, not this lane.

### L9 — International: a base-overlap term
**Rank 9** (1.9% of reconstruction mass; two of the four rows are target problems). **1 lane.**

*Mechanism.* `estimate_static_revenue_effect` (`international.py:136-144`) is a bare four-way sum with no overlap term, so `create_biden_full_international` adds a 21% per-country GILTI to Pillar Two's UTPR on substantially the same undertaxed foreign profits. Add a netting term for the shared base. `_estimate_fdii_reform` repeal is a flat `return base["fdii_cost_billions"]` (`:183`) with no base × rate identity.
*Data.* Treasury Green Book FY2025 line items (the −$700B package is a scope superset covering BEAT/SHIELD, which the module does not implement); JCT's Pillar Two range ($50–120B — the model's −$61B is already inside it, so 23.5% is target imprecision).
*Should move.* `biden_full_international` 41.0% → <25%; `fdii_repeal` 15.0% and `gilti` 17.8% must not regress. Pillar Two should be re-benchmarked against the range, not the midpoint — that is E-provenance work.

## 4. What not to do

- **No new per-benchmark constants.** A lane that sets `annual_revenue_change_billions`, or adds a module constant keyed to a benchmark id, has failed regardless of the error it closes.
- **No per-case elasticities.** One frozen, literature-sourced value per mechanism, cited in the docstring. `validation/scenarios.py`'s three capital-gains tuples get **deleted**, not extended, and the 5.3× lock-in multiplier does not survive in any form.
- **No edits to targets** in `KNOWN_SCORES`, `CBO_SCORE_MAP`, or `preregistered.py` from a modelling lane. A target that looks wrong goes to Phase E-provenance and, if it changes, through the manifest's `superseded_by` rule (new `case_id`, old row kept).
- **No touching the yardstick**: `scripts/cold_holdout.py`, `scripts/run_loo.py`, `loo.py`'s `LEAKAGE_TOLERANCE` guard, `tests/test_preregistration.py`.
- **No loosening CI thresholds** except by the workflow's own published rule (`validation-dashboard.yml:64-67`), and only downward. Removing a case from the battery to go green is the failure mode pre-registration exists to forbid.
- **No fitting a spend-out profile, elasticity, or distribution on the case being scored.** Donors come from other cases; assert it in a test.

## 5. Sequencing

Three waves. Files are disjoint within a wave, so lanes run in parallel.

| Wave | Lanes | Files touched | Starting point (b616144) | Expected after |
|---|---|---|---|---|
| **1** ✅ **done** | **L2** spend-out, **L7** pharma, **L5** AMT | `policies_core.py` (SpendingPolicy only) + `validation/core.py`; `pharma.py` + `enforcement.py`; `amt.py` | Tier 1 **52.6%**; sectoral reconstructions **394.1%** (20-row tier **250.8%**); LOO **59.3%** | *Named:* sectoral **→ ~40%**; LOO **→ ~54%**; Tier 1's endpoint re-derived by the lane. *Actual:* Tier 1 **34.4%**, sectoral **113.8%** (20-row tier **82.6%**), LOO **61.7%**. Two of the three named endpoints were missed, both for reasons the lanes pre-registered before opening a file — see §5.1. Post-wave target corrections (PR #90) then moved sectoral to 104.8%, the tier to 21 rows at 76.7% and LOO to 58.7%, none of it a model change |
| **2** ✅ **done** | **L1** capital gains (PR #95), **L6** expenditures (PR #94), **L4** estate (PR #93) | `data/capital_gains.py` + `policies_core.py` (CapitalGainsPolicy) + `scenarios.py`; `tax_expenditures_core.py`; `estate.py` | Tier 1 **34.4%**; LOO **58.7%**; fitted **2.8% over 33**; reconstructions **76.7% over 21** | *Named:* LOO **→ ~30%**; Tier 1's endpoint re-derived by each lane. *Actual:* Tier 1 **31.3%**, LOO **32.3% over 17 derivable** (31.7% like-for-like over 18), fitted **2.2% over 30**, reconstructions **72.1% over 24**. The wave's one named endpoint was hit; three of the ten per-row bands were missed, each pre-registered before a file was opened — see §5.2 |
| **3** | **L3** credits/microsim, **L8** tariffs, **L9** international | `credits_*` + `microsim/*` + `cps_asec.py`; `trade.py`; `international.py` | LOO after wave 2; reconstructions after wave 1 | LOO **→ ~25%**; reconstructions **→ ~30%** |

**On the two blanked endpoints.** Phases D and E changed *what is in* Tier 1, not
how well the model scores it, so the old wave-1 and wave-2 Tier 1 targets no longer
have a denominator. They are left un-restated on purpose rather than rescaled by
eye — inventing a number here is the same failure as fitting one. Each lane
pre-registers its own expected movement (§1.3) before it opens a file.

Conflict note: L1 and L2 both open `policies_core.py` but different classes — land L2 first. L8 waits on the `app_data.py` key reconciliation. L3's third lane is contingent on the raw-CPS decision (§6.4).

## 5.1 Wave 1 outturn (2026-09-01/02)

Three lanes on disjoint files — L2 (`model/l2-spend-out`, PR #85), L5
(`model/l5-amt`, PR #86), L7 (`model/l7-pharma`, PR #87) — plus an L2 follow-up
(`model/l2-followups`, PR #88) that closed the two items L2 had put out of its
own scope. Each pre-registered its expected movement in `planning/lanes/` before
touching code; those files carry the per-row detail and are the record, not this
summary.

### The tiers, before → after

| tier | n | before | after |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 25 | 52.6% mean / 21.1% median / 8 within 15 / 14 within 25 | **34.4% / 16.1% / 12 / 16** |
| Calibrated reference (fitted) | 34 | 2.7% / 0.2% median / 33 within 15 | **unchanged, to the decimal** |
| Unfitted reconstructions | 20 | 250.8% / 43.1% median | **82.6% / 43.1%** |
|  — 12 sectoral presets | 12 | 394.1% / 57.1% median | **113.8% / 57.1%** |
|  — 8 P.L. 119-21 line items | 8 | 35.8% | **unchanged** |
| Leave-one-out | 18 | 59.3% / 35.6% median / 6 within 15 | **61.7% / 35.6% / 6** |
| Distributional | 7 | 0.00–5.86pp | **unchanged** |

*This table is Wave 1's outturn and is kept as that record. Two Tier-2 figures
moved again on 2026-09-02, when the provenance lane (PR #90) corrected the
`universal_insulin_cap` and `extend_tcja_amt` **targets** without touching a
model constant: the reconstruction tier became **21 rows at 76.7%** (sectoral
subset 104.8%), the fitted tier **33 at 2.8%** — the revised row moving out,
since a constant fitted to a superseded figure is not fitted to its replacement —
and leave-one-out **58.7% / 32.5%**, with `extend_tcja_amt`'s held-out derivation
unchanged at $855.3B. Tier 1 and the distributional tables are untouched. Live
numbers: `python scripts/cold_holdout.py`, `python scripts/run_loo.py`.*

Tier 1 error mass fell **1,315 → 859.5**. The ranking inverted: spend-out was
38.7% of the tier and is now **7.4%** (63.4 units), while capital gains is now
**55.8%** (479.4 units) — so **L1 is the whole of Wave 2's argument**, where
before it shared the top of the table. Masses below are Σ|error %| over each
group's cases and sum to 859.5 exactly.

| Mechanism | Cases | Mass | Share |
|---|--:|--:|--:|
| Capital gains — realizations base, lock-in, gains at death | 4 | 479.4 | **55.8%** |
| Module revenue identities at the margin (payroll ×2, corporate) | 3 | 156.7 | 18.2% |
| Bracket-aggregate ceiling on rate changes | 8 | 89.5 | 10.4% |
| Filing-status-specific thresholds | 2 | 70.5 | 8.2% |
| Spending: spend-out, level shape, window, growth rate | 8 | 63.4 | 7.4% |

### Three findings the wave produced

**1 — L2: the primary spend-out source Decision 2 named does not exist.**
Owner Decision 2 named **OMB Circular A-11 §32 outlay rates** as primary, with
CBO's donor options as the check. A-11 §32 is *"Personnel Compensation,
Benefits, and Related Costs"* and carries no outlay rates; **A-11 publishes no
numeric outlay-rate table in any section** — §80 requires only consistency with
"Presidential policy spendout rates" and §81 has *agencies* enter their own
account-level rates into MAX, unpublished. This is a finding about the decision,
not a fetch failure. **Decision 2's own fallback clause therefore governs: the
CBO donor options in the repository's own
`cbo_options_2025_2034_alternatives.csv` are the shipped primary source.** CBO
*does* publish account-level spendout rates — publications **61913** and
**62256** — and those are the open external cross-check, blocked because
`cbo.gov` returns HTTP 403 to this environment on every URL and
`web.archive.org` was unreachable. Both the CSV header and
`scripts/fit_outlay_rates.py`'s docstring record all of this, so the data file
cannot be read as claiming a provenance it does not have. **Still open**, and it
needs an environment that can reach cbo.gov.

**2 — L5: the plan's own "missing 2026 ramp" hypothesis was wrong.**
§3 L5 above and `VALIDATION_NOTES.md` §6 both attributed AMT's LOO overshoot to
a missing phase-in: *"a LOO derivation that phased the ramp in would close most
of this."* TPC Table T25-0049 contradicts it. The sunset is a **cliff** — AMT
payers go **0.2M in 2025 to 7.6M in 2026** — and the post-sunset path then
*grows*, **$71.6B in 2026 to $124.2B in 2035**. The module's flat ~$73B/yr was
the window's **early-year** level, not its average, so a correctly year-indexed
path scores **higher**, not lower. The derived rows moved **away** from their
carried targets exactly as the lane pre-registered: LOO `extend_tcja_amt`
+73.2% → **+90.1%** (band: +85 to +95), `repeal_individual_amt` +86.0% →
**+110.9%** (band: +105 to +115). Against the **published** line item those
targets disagree with — $1,357.1B, CRS R48286 Table 1 transcribing CBO pub.
60114 — the extension moved the other way, **−66.8% → −37.0%**: the structural
path is about 1.8× closer to the document than the fitted constant, which is
only possible because the carried target and the document disagree. The app
default stays **`reported`** under Decision 1's own rule (derived does not beat
fitted on the carried benchmarks), and Decision 1's *scorecard* half stays
blocked by a locked holdout protocol, not by the model. `VALIDATION_NOTES.md` §6
has been **corrected rather than deleted**: it states what was believed and what
the data showed.

**3 — L7: pharma now scores federal incidence, and one target is the thing left
pointing the wrong way.** Both bugs are repaired and neither repair was fitted
to a benchmark. **Insulin −$445.3B → +$7.0B**, a deficit *increase*, agreeing in
sign with CBO publication 57957's **+$11.4B** for the same policy (39% away);
the carried −$15B target still pointed the wrong way at the time, so its 146.4%
was the price of pointing the right way and could not be read as accuracy.
*(Since: the provenance lane moved that target to CBO's +$11.4B on 2026-09-02,
PR #90, so the row now reads **−39.0%** and it is an accuracy statement. The
model side did not move.)* **Reference pricing
−$1,387.9B → −$746.2B** against a −$100B target whose provenance is
`model_estimate` — a RAND price statistic, not a budget score — while CBO scored
H.R. 3's *narrower* international-reference cap at about **$456B**, which is
where a broader policy should sit. **What remains unrepaired, stated plainly:**
RAND's index is computed on presentations sold in both markets and the module
applies it to **all brand spending**; and **no utilisation, launch-delay or
availability response** is modelled on either row. The family mean is **272.8%**,
down from 1,394.1%.

### Where the pre-registrations were wrong

Kept because §1.3 requires it, and because two of them are the informative part.

- **L2 named IIJA at ~200% after spend-out; it landed at 290.2%.** The
  pre-registration assumed the window would truncate authority at *both* ends.
  It truncates only the tail: the convolution is a property of the policy, so a
  policy starting in 2022 spends its 2022-2024 authority into the window's head.
  Truncating the head too would have discarded authority the model's own shape
  claims to provide — worth about 90 points of flattery. Kept, and written down.
- **L2's follow-up then took IIJA to 18.2% by superseding its shape input**, a
  manifest decision the modelling lane was correctly forbidden to make: a new
  row (`.v2`), never an edit, carrying CBO's own authorization schedule with the
  target unchanged at +$415.4B. `.v1` stays on the record at 356% before
  spend-out and 290.2% after. The residual is a **window** mismatch — $92.6B of
  the path's outlays fall in FY2022-2024, before the model's window opens.
- **L7 missed both of §3 L7's named targets, and said so before starting.**
  Reference pricing to <100% is unreachable against a target that is not a score
  of the policy, and the sectoral mean to ~40% has a **47.7% floor** from the
  nine rows other lanes own. Predicted ≈114% and ≈83%; returned 113.8% and
  82.6%. The hand arithmetic held to a tenth of a point. *(Both figures moved
  again on the insulin target correction — 104.8% and 21 rows at 76.7% — which is
  a target movement, not a modelling one, and does not bear on the
  pre-registration.)*
- **L5 missed one registered row: the fitted tier stayed at 2.7% / 33-of-34**
  where the lane predicted ~9% / ~30-of-34. That is a scope change, not a
  modelling surprise — the scorecard flip was not made, for the reason in
  finding 2 — and it is recorded rather than absorbed. *(The fitted tier did move
  afterwards, to 33 rows at 2.8%, when `extend_tcja_amt`'s target was corrected
  and the row left the tier. That is the target moving, not the flip L5
  predicted.)*

### What Wave 1 did not do

No lane touched `preregistered.py`'s targets, `cold_holdout.py`, `run_loo.py`,
`loo.py`'s leakage guard, `tests/test_preregistration.py`, or any CI threshold.
No per-benchmark constant was added. The one shape input that changed went
through the manifest's `superseded_by` rule in two commits, entry before scoring.

**Reporting change, after Wave 3.** Restate the headline as **three numbers, never collapsed**: (i) out-of-sample pre-registered — n, mean, median, within-15/25; (ii) calibrated leave-one-out — n derivable, mean, and the count declared not cross-validatable; (iii) unfitted module reconstructions — n, mean, median, **split into the sectoral and line-item populations**, because Phase D showed the pooled mean moves on composition alone. The by-construction 2.7% moves to a footnote, because by then several fitted annuals should be *deletable*: a module whose derived error beats its fitted error no longer needs the constant, and deleting it is the cleanest possible evidence the mechanism is real.

## 5.2 Wave 2 outturn (2026-09-02)

Three lanes on disjoint files — L4 (`model/l4-estate`, PR #93), L6
(`model/l6-tax-expenditures`, PR #94), L1 (`model/l1-capital-gains`, PR #95).
Each pre-registered its expected movement in `planning/lanes/` before touching
code; those files carry the per-row detail and are the record, not this summary.
Every figure here is from `python scripts/cold_holdout.py` and
`python scripts/run_loo.py --donor-matrix` on the merged tree.

### The tiers, before → after

| tier | n | before | after |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 25 | 34.4% mean / 16.1% median / 12 within 15 / 16 within 25 | **31.3% / 14.1% / 13 / 18** |
| Calibrated reference (fitted) | 33 → **30** | 2.8% / 0.3% median / 32 within 15 | **2.2% / 0.2% / 30 within 15** |
| Unfitted reconstructions | 21 → **24** | 76.7% / 41.0% median | **72.1% / 40.0% median** |
| Leave-one-out | 18 → **17** derivable | 58.7% / 32.5% median / 6 within 15 | **32.3% / 19.2% / 8** |
|  — `CapitalGains` | 3 | 171.2% | **39.6%** |
|  — `Estate` | 2 | 25.8% | **10.4%** |
|  — `Expenditures` | 5 → **4** | 39.4% | **28.8%** |
| Not cross-validatable | 4 → **5** | — | `eliminate_salt` joined |
| Distributional | 7 | 0.00–5.86pp | **unchanged** |

Tier 1 error mass fell **859.5 → 781.8**. The capital-gains group fell
**479.4 → 405.6** and is still the tier's largest at **51.9%**, but it is no
longer one mechanism: gains at death is now 8.4%, and the two step-up-elimination
rows carry 352.4 of the group's 405.6 between them.

**Two composition changes travel with these numbers and neither may be
dropped.** (i) The three capital-gains scenarios moved from the *fitted* tier to
the *reconstruction* tier, because deleting `fiscal_model/validation/scenarios.py`'s per-case
behavioural tuples removed the only constants that had ever been fitted to those
targets — `calibrated_to_target=False` is now simply true of them. The fitted
mean *fell* 2.8% → 2.2% while nothing regressed; left in place those rows would
have raised it to 6.2%. (ii) `eliminate_salt` left the LOO derivable set when L6
made `annual_cost_no_cap = 120.0` load-bearing and `loo.py`'s untouched leakage
guard saw that $120.0B is exactly the carried target over ten. Counting it at
its derived +20.4%, the suite reads **31.7% over 18**; the printed 32.3% over 17
is the honest figure, and the module now cross-validates on four expenditure
benchmarks where it used to claim five.

### Per-case, the rows that moved

| Row | official | before | after | error |
|---|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` (Tier 1) | −536.1 | −83.7 | **−581.2** | 84.4% → **8.4%** |
| `cbo_opt47_ltcg_qdiv_2pp` (Tier 1) | −103.3 | −205.7 | **−57.1** | 99.1% → **44.8%** |
| `biden_capital_gains_39` (Tier 1) | −288.6 | −699.4 | **−678.1** | 142.3% → **134.9%** |
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −322.0 | −816.6 | **−1022.3** | 153.6% → **217.5%** |
| `cbo_opt45_top4_brackets_2pp` (Tier 1, unnamed) | −569.5 | −716.4 | **−671.6** | 25.8% → **17.9%** |
| `illustrative_1pp_all` (Tier 1, unnamed) | −960.0 | −935.4 | −920.3 | 2.6% → 4.1% |
| `cbo_opt45_all_rates_1pp` (Tier 1, unnamed) | −1185.3 | −935.4 | −920.3 | 21.1% → 22.4% |
| `biden_high_income_tax` (Tier 1, unnamed) | −252.0 | −284.5 | −216.5 | 12.9% → 14.1% |
| `cbo_2pp_all_brackets` (LOO) | −70.0 | −154.3 | **−79.8** | −120.5% → **−14.0%** |
| `pwbm_39_with_stepup` (LOO) | +33.0 | −89.3 | **+23.6** | −370.5% → **−28.4%**, sign restored |
| `pwbm_39_no_stepup` (LOO) | −113.0 | −138.6 | **−26.6** | −22.6% → **+76.5%** |
| `biden_estate_reform` (LOO) | −450.0 | −244.9 | **−457.2** | +45.6% → **−1.6%** |
| `extend_tcja_exemption` (LOO) | +167.0 | +176.9 | **+199.0** | +6.0% → **+19.2%** |
| `cap_employer_health` (LOO) | −450.0 | −11.5 | **−30.5** | +97.4% → **+93.2%** |
| `cap_charitable` (LOO) | −200.0 | −168.5 | **−173.8** | +15.7% → **+13.1%** |
| `eliminate_salt` (LOO) | −1200.0 | −300.9 | **−1444.4** | +74.9% → **excluded** (−10.9% against the published −$1,621.0B) |

### Four findings the wave produced

**1 — L1: a fifth defect sat under the plan's four, and it was a unit error.**
`estimate_behavioral_offset` applied `R₁ = R₀·((1−τ₁)/(1−τ₀))^ε` — an
elasticity with respect to the **net-of-tax rate** — using ε values the
realization literature reports with respect to the **tax rate**. CRS R48562
(2025) states the definition twice and gives the semi-log form behind it,
`R = B·exp(−b·t)`, so `ε(t) = b·t`. Applying one as the other understates the
response by roughly `(1−τ)/τ`: at τ = 23.8% the frozen ε = 0.8 was an
**effective tax-rate elasticity of 0.25**, a third of anything in CRS's Table 4,
and that single error was most of why every rate-change row over-predicted.
Decision 3's frozen Dowd–McClelland–Muthitacharoen persistent 0.72 at CRS's 22%
reference rate gives **b = 3.273** against **JCT's own 3.1** — agreement within
6%, the cross-check that this is a unit fix and not a tuning knob — and a
revenue-maximizing rate of 30.6%. That reproduces PWBM's own finding directly:
43.4% sits past the peak, so a rate rise loses revenue while step-up survives,
and `pwbm_39_with_stepup` scores **+$23.6B against PWBM's +$33.0B with no
multiplier at all**. The 5.3× lock-in multiplier, the residual-avoidance
multiplier and all three scenario tuples are deleted, and Tailor's
capital-gains form lost its lock-in slider along with them.

*What L1 left undone, and it is the whole residual on the two Treasury rows:*
**the death channel has no behavioural response.** Biden's proposal carves out
transfers to a spouse and to charity, preserves the §121 residence exclusion,
excludes tangible personal property, defers family-business gains until sale and
offers a 15-year installment election; Treasury's score prices all of it and
this module prices only the per-decedent exclusion. **And the realizations base
is not projected across the window** — it is held at its observed SOI level
under the lane's pre-registered stocks-are-indexed / flows-are-not rule.
*Provenance flag, for the other lane:* Treasury's FY2022 Green Book carries a
**separate** line for realization at death, yet
`treasury_capgains_39_plus_stepup_elim` describes its −$322.0B as the
*combined* figure — and the model's death channel alone under a $1M exclusion
exceeds that whole target.

**2 — L4: the estate row that got worse is the informative one.** SOI *Estate
Tax Statistics* Table 1's size distribution (pooled α = 1.73843 from seven local
estimates across filing years 2010, 2013 and 2024) replaces a two-point blend
whose count-times-average product was **exactly invariant** in the exemption —
a defect that was user-facing, not merely a validation artefact:
`create_estate_exemption_change(3.5e6)` used to score **$0.0B** and now returns
**+$35.4B/yr**. `extend_tcja_exemption` nonetheless missed its band (+19.2%
against +5 to +15), and the reason is that **the object that grows is the
distribution, not revenue** — revenue at a fixed exemption grows at α times the
distribution's rate, real bracket creep — so the pre-registration's growth
semantics were wrong. **The pre-registered configuration scores better on both
rows (at 3.0%: +8.7% and −6.9%) and was not shipped**, which is the strongest
available evidence that the choice was made on structure rather than on the
error it produces. **Growth is unresolved**: fitting level and growth jointly to
SOI's three filing years returns **6.81%/yr** and reproduces SOI's history to
within 8% everywhere, but projected forward gives `extend` +66.9% and `biden`
+40.3%, which no published estate estimate is consistent with; the module ships
the app's own nominal GDP rate (**3.82%**) and therefore over-states what was
actually collected from 2009 decedents by 109% and from 2012 decedents by 56%.
Deliberate, and pinned by a test so a data refresh cannot turn it into an
accident. Also unmodelled: **portability / DSUE** (declared and never read, so
the effective per-couple exemption can be twice what the module prices) and the
**graduated rate schedule** (every rate is a single top rate scaled
proportionally, which is why the Biden target stays an upper bound). Not a
benchmark but a large gap: `create_warren_estate_proposal` carries a fitted
**−$2,600B** and derives **−$663.6B** — PWBM's figure scores a package with a
separate wealth tax, so the two are not estimates of the same policy.

**3 — L6: the SALT constant is the finding, and the employer-health miss was
pre-registered.** Benefit distributions by AGI class come from **IRS SOI Table
2.1** because `jct.gov` returns HTTP 403 to this environment on every URL — SOI
is the administrative source JCT's own distribution tables are built from and,
decisively, separates *total* from *limited* SALT. Making `eliminate` read
`annual_cost_no_cap = 120.0` took the derived score to −$1,444.4B, **−10.9%
against the published CBO Option 49 line item of −$1,621.0B** where the *fitted*
constant is −22.3% — and then tripped the untouched leakage guard, because
$120.0B is exactly the carried −$1,200B target over ten. The lane hands the
provenance lane the check it did not have: pricing SOI's **limited** SALT
deduction at the statutory schedule gives **$25.0B/yr** against the record's own
`annual_cost = 25.0` — two numbers with no common ancestor agreeing to a tenth
of a percent — and the same computation on the **unlimited** deduction gives
**$89.6B/yr**, 25% below the record's $120.0B. `repeal_salt_cap`'s +4.0% is
`−(120.0 − 25.0)` and should be read as leaked too. Separately,
`cap_employer_health` moved only 97.4% → **93.2%**, exactly as pre-registered:
**a $50,000 cap is above the entire distribution of employer premiums** (CBO's
own 75th percentile of family premiums is **$31,300**), so the corrected
mechanism now prices the mismatch `benchmark_sources.py` describes in words —
the carried −$450B corresponds to a cap near **$26,400**, and no correct model
of a $50,000 cap will reach it. **CBO Option 56 is now scorable**: **+2.5%** in
the option's own first year (2028: $60.5B against CBO's $59B), −32.6% over
2028–2034 as shipped and **−12.8%** with the excess share recomputed each year.
A year-indexed excess share is the next structure this module needs; the option
is a credible Tier 1 candidate and this wave did not promote it.

**4 — Every Wave 2 module keeps `reported` as the app default, and the readiness
protocol now warns where it used to fail.** Under Decision 1's own rule, derived
did not beat fitted on any module's carried targets — estate 0.0% reported
against 19.2% / −1.6% / +34.7% derived; expenditures **4.2% reported against
26.0% derived** — so `ESTATE_APP_MODE`, `ESTATE_SCORECARD_MODE` and the
expenditure equivalents all stay `reported`, and **no shipped preset moved**.
Read that comparison with the caution L5 established: most of those targets are
reproduced by a constant fitted to them, so their sub-1% errors measure
bookkeeping, and on the one expenditure row where the carried target and the
document disagree, the derived path is twice as close to the document.
Separately, `check_readiness.py`'s `holdout_protocol` check went PASS →
**WARN**: `pwbm_39_with_stepup` is a locked holdout id that now rates Poor with
the direction right, and `_scorecard_checks` already carried the repository's
rule for exactly this case — *a Poor entry with a documented `known_limitations`
note is a warning, which is how a documented out-of-sample miss kept rather than
tuned away is recorded* — with `_is_documented_benchmark_warning` exempting a
documented miss on a benchmark a module is **not** fitted to while refusing to
exempt one it is. Both rules now apply to the holdout check on the same terms;
an undocumented Poor holdout entry, an `Error`, a direction mismatch, or a
documented Poor entry the module *is* still fitted to all continue to hard-fail,
and the entry stays in the battery. **Whether to re-lock the protocol instead of
relying on that convention is an open owner decision** (§6.1).

### Where the pre-registrations were wrong

Kept because §1.3 requires it, and because the misses are the informative part.

- **L1 missed three of its ten registered bands.** Tier 1's mean landed at
  **31.3%** against a registered 18–26%, and the two Treasury rows moved the
  wrong way — §4 predicted the rate channel would turn *negative* at 43.4%, and
  it does not, because both proposals **eliminate** step-up, which divides `b`
  by the 1.44× wedge and leaves the rate channel firmly positive (+$25.7B/yr on
  the $638.6B base above $1M). The pre-registration got the mechanism right and
  the sign of its interaction with step-up elimination wrong, which is worth
  more than the band it missed.
- **L1's own falsification test fired, and it was written too tightly.** §4.1
  said any movement in a Tier-1 row the lane did not name would falsify it; four
  moved, all through `preferential_income_share` reading the same rebuilt
  baseline, for a net **−4.4 units** of mass. The new measurement is strictly
  better sourced; the test, not the fix, was wrong.
- **L4 missed `extend_tcja_exemption` (+19.2% against +5 to +15) and the 7/18
  within-15 that depended on it**, for the growth-semantics reason in finding 2.
  Its §2.3 level anchor also became a record of the plan rather than of the
  code: the shipped module anchors on SOI's own FY2024 row and uses CBO's $50B
  as the external *check*, which it passes at $47.6B.
- **L6 predicted every point it named to the decimal** — employer health
  +93.2% against +91 to +95, SALT +20.4% against +18 to +23, charitable +13.1%
  against +11 to +15, and all three derived annuals exact — and missed only the
  **case count**: it did not foresee that making the no-cap constant
  load-bearing would trip the leakage guard.

### What Wave 2 did not do

No lane touched `preregistered.py`'s targets, `cold_holdout.py`, `run_loo.py`,
`loo.py`'s `LEAKAGE_TOLERANCE` or its guard, `tests/test_preregistration.py`, or
any CI threshold. No per-benchmark constant was added — L4 deleted eight, and L1
deleted the lock-in multiplier, the avoidance multiplier and three scenario
tuples. The CI gate was re-derived afterwards by the workflow's own published
rule, in a separate PR (#96): `--max-mean-error 45 --min-within-25pct 15` →
**`--max-mean-error 40 --min-within-25pct 17`** (ceiling = ceil(31.3 × 1.25)
rounded up to the nearest 5 = 40; floor = 18 within 25%, minus one = 17).

## 6. Open owner decisions

**Decided 2026-09-01 (owner accepted the coordinator's recommendation on all six).** The questions are kept below as written; the decisions are:

1. Keep both modes. `derived` is the validation default immediately; `reported` stays the app default per module until that module's derived error is below its fitted error. (Wave 1: L5 AMT implements the switch module-locally.) **Outturn:** implemented; `derived` is the default in the held-out path, `reported` stays the app default. Re-measured against the corrected targets (PR #90, 2026-09-02) it stays there: across the three AMT benchmarks **reported means 22.3% and derived 54.2%**, so the rule's own condition is not met. Read past the mean before calling that a win for the fitted path — both rows derived loses are targets a constant was fitted to, so their ~0% is bookkeeping, and **the one AMT benchmark whose target no constant was fitted to (`extend_tcja_amt`, now $1,357.1B) is the one derived wins**, 37.0% against 66.8%. The *scorecard* half stays blocked, and its blocker has changed character: it used to be "the AMT targets have not been checked" and is now "`repeal_individual_amt`'s target does not exist" — no published post-2025 repeal score, and TPC T25-0049's $948.9B is both a baseline projection and `amt.py`'s own input. Unblocking it needs a published score or an owner decision to re-register `holdout.py`'s locked protocol. `AMT_SCORECARD_MODE` is still the one line that flips it.
2. OMB Circular A-11 §32 outlay rates are the primary spend-out source; CBO's donor options are the check. (L2.) **Outturn: the named source does not exist** — A-11 §32 is personnel compensation and A-11 publishes no outlay-rate table in any section, so the decision's own fallback governed and CBO's donor options shipped as primary. CBO's account-level rates (pubs 61913, 62256) are the open cross-check, blocked by cbo.gov 403s. See §5.1 finding 1.
3. Freeze Dowd–McClelland–Muthitacharoen (2015): persistent −0.72, transitory −1.2, cited. (Wave 2, L1.)
4. Fetch the raw CPS ASEC extract by script at build time; never vendor it. (Wave 3, L3.)
5. Move the three tautological credit benchmarks to documented-exclusion status, like `repeal_corporate_amt`. (Wave 3, L3, with the LOO number carrying the honesty meanwhile.)
6. The tariff gross→net change lands with its UI note in the same PR as L8. (Wave 3.)

Wave 1 launched 2026-09-01 as three lanes on disjoint files — L2 (`model/l2-spend-out`), L5 (`model/l5-amt`), L7 (`model/l7-pharma`) — each pre-registering its expected movement in `planning/lanes/` before touching code.

1. **Reported vs derived mode.** Should the calibrated modules keep their fitted annuals as a `reported` mode alongside a `derived` mode? Recommendation: yes — `derived` becomes the default in validation immediately, `reported` stays the app default per module until that module's derived error is below its fitted error. The alternative (delete the annuals now) makes the app worse before it makes it better.
2. **Spend-out source.** Fit `s` by function from the 13 donor options in CBO's own report, or take OMB Circular A-11 §32 outlay rates as primary with CBO as the check? The donor route is self-contained and testable; the A-11 route is externally verifiable and immune to the "you fitted it on the battery" objection.
3. **Which capital-gains elasticities to freeze.** Dowd–McClelland–Muthitacharoen (2015) (persistent −0.72 / transitory −1.2) or Agersnap–Zidar (2021) (−0.3 to −0.5)? They imply materially different revenue-maximizing rates and pull the two Treasury targets in opposite directions. One value, frozen, cited — but which.
4. **Raw CPS ASEC rebuild.** Adding `pppub24.csv` / `hhpub24.csv` to the pipeline is what unblocks dependent ages (CTC under-6, age-17). Given the repo policy on large files, does the raw extract get vendored, fetched by script at build time, or does the derived microdata simply gain the extra columns?
5. **Do the three credit benchmarks stay in the fitted tier?** Their annuals are the targets divided by ten, so `x/10 × 10 == x` is all they test. Move them to a documented-exclusion status like `repeal_corporate_amt`, or leave them and rely on the LOO number to carry the honesty.
6. **Tariff presets change for users.** L8 turns gross customs revenue into a net score — the shipped preset numbers move by 40–50%. Does that need a UI note, and does it land with L8 or with a separate app change?

### 6.1 Open owner decisions after Wave 2 (added 2026-09-02)

Six questions the wave surfaced or left standing. None is a modelling lane's
call; all six are recorded here so no lane has to rediscover them.

1. **Re-lock the holdout protocol, or keep the warning convention?**
   `pwbm_39_with_stepup` is a locked id in
   `revenue-scorecard-post-lock-2026-05-02` and now rates Poor with the
   direction right, so `check_readiness.py`'s `holdout_protocol` check reports
   **WARN** under the repository's existing documented-miss convention rather
   than failing. The protocol was locked over a scorecard in which that entry
   carried its own fitted 5.3× multiplier, which no longer exists. Either
   re-register the protocol against the current battery, or accept the warning
   convention as the standing rule. **The entry stays in the battery either
   way** — removing it to go green is the failure mode the protocol exists to
   prevent.
2. **`repeal_individual_amt`'s target.** Still $450B and still unsourced: no
   published post-2025 repeal score exists, and TPC T25-0049's $948.9B is a
   baseline projection *and* `amt.py`'s own input, so adopting it would
   manufacture a 0% row out of the leakage `loo.py` guards against. This is the
   one line blocking Decision 1's scorecard half.
3. **The SALT constants — provenance and modelling together.**
   `annual_cost_no_cap = 120.0` is unsourced, is exactly the carried target over
   ten, and is now load-bearing. SOI × the statutory schedule puts the uncapped
   SALT deduction at **$89.6B/yr**, 25% below it, while reproducing the *capped*
   level ($25.0B) to a tenth of a percent. Replacing 120.0 with 89.6 makes
   `eliminate_salt` derivable again at 10.2% but takes `repeal_salt_cap` from
   +4.0% to −29.4%, so it is a joint decision about both rows — and about
   whether the record's no-cap level embeds an undocumented itemisation
   response.
4. **Treasury FY2022: combined row or rate-only row?** The Green Book carries a
   *separate* line for treating transfers at death as realization events, yet
   `treasury_capgains_39_plus_stepup_elim` describes its −$322.0B as the
   combined rate-plus-realization figure — and the model's death channel alone
   under a $1M exclusion is larger than that whole target. A manifest question,
   and it moves under the `superseded_by` rule if it moves at all.
5. **The estate growth lever.** SOI-fitted **6.81%/yr** reproduces history and
   projects to figures no published estate estimate supports; the shipped
   **3.82%** (nominal GDP) projects sensibly and backcasts badly (+109% on 2009
   decedents, +56% on 2012). The module ships the second and pins it with a
   test. Which one the repository wants is an owner call, and it moves both
   estate LOO rows across a range of −32% to +67%.
6. **Promote CBO Option 56 to Tier 1.** Now expressible, and **+2.5%** in the
   option's own first year, but −32.6% over the window because the excess share
   is evaluated once at `start_year`. The recommendation is to land the
   year-indexed excess share first, then promote all three alternatives
   together.

*Also noted, and not a decision:* the four capital-gains rows'
`known_limitations` notes in `preregistered.py` still describe the pre-Wave-2
mechanism — the $54B flow constant, the 0.8/0.4 net-of-tax elasticities and the
5.3× multiplier — none of which exists any more. Refreshing them touches no
target, but it is a `preregistered.py` edit and a modelling lane may not open
that file.
