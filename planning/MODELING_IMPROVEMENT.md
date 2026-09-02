# Modeling improvement plan — close the errors by modelling the mechanism

*Written 2026-09-01 against `main` @ `257219b` (Phases A/B/C/E landed: PRs #69, #72, #70, #71).*
*Error budget (§2) and sequencing (§5) re-derived 2026-09-01 against `main` @ `b616144`, after Phase D (enacted-law components, P.L. 119-21 line items) and Phase E provenance landed. Every number below is from `python scripts/cold_holdout.py --json` and `python scripts/run_loo.py --donor-matrix` on that commit, or from a `file:line` in the tree.*

The validation expansion did its job: it replaced a flattering 8% with three honest numbers — **52.6% out-of-sample (n=25)**, **59.3% leave-one-out (n=18 derivable)**, and **250.8% on unfitted module reconstructions (n=20)**, the last of which is itself two populations that must be reported apart: **394.1% across the 12 sectoral presets** and **35.8% across the 8 P.L. 119-21 line items**. This plan spends those numbers. It ranks the work by *error mass × tractability* and says, per lane, which mechanism is missing, what data closes it, which rows should move and in which direction.

> **Wave 1 has landed (2026-09-01/02).** The current numbers are **34.4%
> out-of-sample (n=25, median 16.1%, 12 within 15%, 16 within 25%)**, **61.7%
> leave-one-out (n=18)**, and **82.6% on the 20 unfitted reconstructions** — 12
> sectoral presets at **113.8%** and the 8 P.L. 119-21 line items unchanged at
> **35.8%**. Fitted calibrated stays at 2.7% over 34, and the 7 distributional
> tables at 0.00–5.86pp. **§2's error budget below is the pre-Wave-1 snapshot on
> `b616144` and is kept as the record the lanes were scoped against**; §5.1 has
> the outturn and re-derives the budget. Live numbers always come from
> `python scripts/cold_holdout.py` and `python scripts/run_loo.py --donor-matrix`.

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

### L1 — Capital gains: stock of accrued gains, decomposed elasticity, gains at death
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

### L4 — Estate: a taxable-estate distribution instead of a two-point blend
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

### L6 — Tax expenditures: bases with the right units
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
| **1** ✅ **done** | **L2** spend-out, **L7** pharma, **L5** AMT | `policies_core.py` (SpendingPolicy only) + `validation/core.py`; `pharma.py` + `enforcement.py`; `amt.py` | Tier 1 **52.6%**; sectoral reconstructions **394.1%** (20-row tier **250.8%**); LOO **59.3%** | *Named:* sectoral **→ ~40%**; LOO **→ ~54%**; Tier 1's endpoint re-derived by the lane. *Actual:* Tier 1 **34.4%**, sectoral **113.8%** (20-row tier **82.6%**), LOO **61.7%**. Two of the three named endpoints were missed, both for reasons the lanes pre-registered before opening a file — see §5.1 |
| **2** | **L1** capital gains (3 lanes), **L6** expenditures, **L4** estate | `data/capital_gains.py` + `policies_core.py` (CapitalGainsPolicy) + `scenarios.py`; `tax_expenditures_core.py`; `estate.py` | Tier 1 after wave 1; LOO after wave 1 | LOO **→ ~30%**. Tier 1's “→ ~30%” likewise assumed the 23-case battery and the pre-Phase-E `biden_capital_gains_39` target at 79%; re-derive once wave 1 has restated the baseline |
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
the carried −$15B target still points the wrong way, so its 146.4% is the price
of pointing the right way and cannot be read as accuracy. **Reference pricing
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
  82.6%. The hand arithmetic held to a tenth of a point.
- **L5 missed one registered row: the fitted tier stayed at 2.7% / 33-of-34**
  where the lane predicted ~9% / ~30-of-34. That is a scope change, not a
  modelling surprise — the scorecard flip was not made, for the reason in
  finding 2 — and it is recorded rather than absorbed.

### What Wave 1 did not do

No lane touched `preregistered.py`'s targets, `cold_holdout.py`, `run_loo.py`,
`loo.py`'s leakage guard, `tests/test_preregistration.py`, or any CI threshold.
No per-benchmark constant was added. The one shape input that changed went
through the manifest's `superseded_by` rule in two commits, entry before scoring.

**Reporting change, after Wave 3.** Restate the headline as **three numbers, never collapsed**: (i) out-of-sample pre-registered — n, mean, median, within-15/25; (ii) calibrated leave-one-out — n derivable, mean, and the count declared not cross-validatable; (iii) unfitted module reconstructions — n, mean, median, **split into the sectoral and line-item populations**, because Phase D showed the pooled mean moves on composition alone. The by-construction 2.7% moves to a footnote, because by then several fitted annuals should be *deletable*: a module whose derived error beats its fitted error no longer needs the constant, and deleting it is the cleanest possible evidence the mechanism is real.

## 6. Open owner decisions

**Decided 2026-09-01 (owner accepted the coordinator's recommendation on all six).** The questions are kept below as written; the decisions are:

1. Keep both modes. `derived` is the validation default immediately; `reported` stays the app default per module until that module's derived error is below its fitted error. (Wave 1: L5 AMT implements the switch module-locally.) **Outturn:** implemented; `derived` is the default in the held-out path, `reported` stays the app default because derived does not beat fitted on the carried targets. The *scorecard* half is blocked by `holdout.py`'s locked protocol plus `readiness.py`'s hard fail on a Poor holdout entry, and needs the AMT targets settled first. `AMT_SCORECARD_MODE` is the one line that flips it.
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
