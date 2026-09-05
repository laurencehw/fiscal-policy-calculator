# Modeling improvement plan — close the errors by modelling the mechanism

*Written 2026-09-01 against `main` @ `257219b` (Phases A/B/C/E landed: PRs #69, #72, #70, #71).*
*Error budget (§2) and sequencing (§5) re-derived 2026-09-01 against `main` @ `b616144`, after Phase D (enacted-law components, P.L. 119-21 line items) and Phase E provenance landed. Every number below is from `python scripts/cold_holdout.py --json` and `python scripts/run_loo.py --donor-matrix` on that commit, or from a `file:line` in the tree.*

The validation expansion did its job: it replaced a flattering 8% with three honest numbers — **52.6% out-of-sample (n=25)**, **59.3% leave-one-out (n=18 derivable)**, and **250.8% on unfitted module reconstructions (n=20)**, the last of which is itself two populations that must be reported apart: **394.1% across the 12 sectoral presets** and **35.8% across the 8 P.L. 119-21 line items**. This plan spends those numbers. It ranks the work by *error mass × tractability* and says, per lane, which mechanism is missing, what data closes it, which rows should move and in which direction.

> **Waves 1, 2, 3 and 4 have all landed (2026-09-01 to 2026-09-05). The plan is
> complete; §6.2 is the carry-over list.** The current numbers are
> **18.0% out-of-sample (n=26, median 12.6%, 14 within 15%, 21 within 25%)**,
> **29.6% leave-one-out (n=18 derivable, 4 not cross-validatable)**, and
> **56.6% on the 31 unfitted reconstructions** — 15 sectoral presets at
> **82.6%**, the 8 P.L. 119-21 line items unchanged at **35.8%**, the 3
> capital-gains scenarios Wave 2 unfitted at **39.6%**, the revised
> `extend_tcja_amt` row at **66.8%**, and Wave 4's 5 provenance arrivals at
> **9.4%**. Fitted calibrated is **1.6% over 23**, or **3.0% over 28** with Wave
> 4's five revised rows held in place (5.2% over 29 with the TCJA-AMT row too);
> the 7 distributional tables now span **0.00–5.86pp**, the ARP row having fallen
> 7.77 → **3.72** when Wave 4 scored it on CBO's own household universe.
> **Two of those tiers changed population in Wave 4 and both means fell for
> reasons that are not improvements**, so quote the like-for-like readings beside
> them: reconstructions **65.7% / 40.5%** over the 26 rows they already held —
> *worse* than 61.8% / 38.0% — and the sectoral subset **88.2%** over the 14.
> Leave-one-out is the mirror case: it *rose* 28.4% → 29.6% with **no derivation
> moving**, because three of its targets did. **§2's error budget below is the
> pre-Wave-1 snapshot on `b616144` and is kept as the record the lanes were
> scoped against**; §§5.1, 5.2, 5.3 and 5.4 carry the four outturns. Live numbers
> always come from `python scripts/cold_holdout.py` and
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
| **Payroll identity at the margin** | `cbo_opt61` 1% 54.1, 2% 55.5 | 110 | 8.3% | Medium. ~~Needs employer-share incidence + income-tax offset, not new data~~ — **this scoping was wrong on the merits**; see §5.5 finding 1. Shipped Wave 5 (PR #113): 7.5% / 8.1% |
| Residual (8 rate cases, 1.5–21.1%) | — | 90 | 6.8% | At the bracket-aggregate ceiling (`VALIDATION_NOTES.md` §5) |
| **Filing-status-specific thresholds** | `cbo_opt46_1pp_20k` 44.7, `cbo_opt45_top4_2pp` 25.8 | 71 | 5.4% | Medium. Needs SOI by filing status; not in scope below |
| **Corporate rate at the margin** | `cbo_opt64` 47.1 | 47 | 3.6% | ~~Low priority; one row~~ — taken Wave 5 (PR #114) and **registered as a regression to 62.3%**, because the fitted base was a TY2018 vintage and two documents price the point 42% apart; see §5.5 |
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

### L3 — Credits: children (and dependents) from the CPS microdata ✅ *shipped, Wave 3 (PR #101) — the <20% target was missed by half a point and the ARP distributional target outright; see §5.3*
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

### L8 — Tariffs: pass-through, retaliation, and the income/payroll offset ✅ *shipped, Wave 3 (PR #99) — two of the three named rows landed under 40%; see §5.3*
**Rank 8** (7.0% of reconstruction mass). **1 lane.**

*Mechanism.* `estimate_static_revenue_effect` (`trade.py:99-118`) returns **gross customs revenue** with a flat 5% avoidance haircut (`:120-121`). `pass_through_rate = 0.60` (`:87`) and `retaliation_rate = 0.30` (`:89`) exist but feed only display paths (`estimate_consumer_cost` `:123-127`, `estimate_retaliation_cost` `:129-134` → `get_trade_summary` `:140-152`). There is **no income/payroll offset at all** — JCT scores indirect taxes net of a ~25% income-and-payroll offset, and the repo's own knowledge snapshot puts the net figure at 40–50% of gross. Route the import-demand response through the pass-through-adjusted price change, net retaliation's effect on export-linked receipts, and subtract the offset. Also: `create_reciprocal_tariffs` hard-codes a 0.5 coverage literal (`:214`) that belongs in `TRADE_BASELINE`, and `create_steel_tariff_25` (`:199-206`) applies the full 25pp with no netting of Section 232 duties already in force.

*Data.* Yale Budget Lab, *State of U.S. Tariffs* methodology (budgetlab.yale.edu); Amiti, Redding & Weinstein (2019, *JEP*) and Fajgelbaum et al. (2020, *QJE*) on near-complete pass-through; JCT's revenue-offset convention; CBO's tariff estimates for a gross/net check. `CBO_TRADE_ESTIMATES` (`trade.py:58-71`) is defined and unread.
*Should move.* `auto_tariff_25` 152.3%, `reciprocal_tariffs` 128.0%, `steel_tariff_25` 73.2% → all <40%. The two fitted coverage constants (`universal_coverage_rate`, `china_effective_coverage`) should be re-derivable rather than fitted afterwards.
*Depends on.* The `app_data.py` key mismatch (`CBO_SCORE_MAP` "25% Steel & Aluminum Tariff" vs `PRESET_POLICIES` "25% Steel/Aluminum Tariff"; same for reciprocal) — a separate one-file fix, not this lane.

### L9 — International: a base-overlap term ✅ *shipped, Wave 3 (PR #98) — the overlap the plan named is not in the code, and two rows got worse by design; see §5.3*
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
| **3** ✅ **done** | **L3** credits/microsim (PR #101), **L8** tariffs (PR #99), **L9** international (PR #98) | `credits_*` + `microsim/*` + `cps_asec.py`; `trade.py`; `international.py` | LOO **32.3% over 17**; reconstructions **72.1% over 24** (12-row sectoral 104.8%) | *Named:* LOO **→ ~25%**; reconstructions **→ ~30%**. *Actual:* LOO **28.4% over 18** (29.5% like-for-like over 17), reconstructions **61.8% over 26** (63.6% like-for-like over 24; 12-row sectoral **87.8%**), fitted **2.0% over 28**, Tier 1 **31.0% over 26** after PR #100 promoted CBO Option 56. Neither named endpoint was hit; both misses were pre-registered before a file was opened, and one of them — the reconstruction tier — is where a lane deliberately moved *away* from a target it judged wrong. See §5.3 |

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

## 5.3 Wave 3 outturn (2026-09-02)

Three modelling lanes on disjoint files — L9 (`model/l9-international`, PR #98),
L8 (`model/l8-tariffs`, PR #99), L3 (`model/l3-credits`, PR #101) — plus a
target-provenance lane that ran alongside them (`provenance/wave3-targets`,
PR #100) and the coordinator's gate re-derivation (PR #102). Each modelling lane
pre-registered its expected movement in `planning/lanes/` before touching code;
those files carry the per-row detail and are the record, not this summary. Every
figure here is from `python scripts/cold_holdout.py`, `python scripts/run_loo.py
--donor-matrix` and `python scripts/run_validation_dashboard.py` on the merged
tree.

### The tiers, before → after

| tier | n | before | after |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 25 → **26** | 31.3% mean / 14.1% median / 13 within 15 / 18 within 25 | **31.0% / 15.1% / 13 / 19** |
| Calibrated reference (fitted) | 30 → **28** | 2.2% / 0.2% median / 30 within 15 | **2.0% / 0.1% / 28 within 15** |
| Unfitted reconstructions | 24 → **26** | 72.1% / 40.0% median / 5 within 15 | **61.8% / 38.0% / 5 within 15** |
|  — sectoral subset | 12 → **14** | 104.8% / 40.0% median | **81.0% / 38.0%** |
| Leave-one-out | 17 → **18** derivable | 32.3% / 19.2% median / 8 within 15 | **28.4% / 16.5% / 9** |
|  — `Credits` | 3 | 45.1% | **20.5%** |
|  — `Expenditures` | 4 → **5** | 28.8% | **30.2%** |
| Not cross-validatable | 5 → **4** | — | `eliminate_salt` left |
| Scorecard rows | 79 → **80** | 72 published | **73 published** |
| `revised_target_entries` | 2 → **3** | — | `pillar_two_adoption`, as a **range** |
| Distributional | 7 | 0.00–5.86pp | **0.00–7.77pp** (ARP 4.76 → **7.77**) |

**Three of those tiers changed population, so the like-for-like readings are
printed beside them and neither may be dropped.** On the 24 rows the
reconstruction tier held before L8 it reads **63.6%**, not 61.8%; on the 12
sectoral rows it held, **87.8%**, not 81.0%; and the leave-one-out suite would
read **29.5% over 17** had `eliminate_salt` not been readmitted. A mean that
moves because the population moved has not improved — §2.3's own rule.

Tier 1's error mass rose **781.8 → 805.8** because a case was *added*, not
because a row got worse: no existing Tier 1 row moved by a cent in Wave 3.

### Per-case, the rows that moved

| Row | official | before | after | error |
|---|--:|--:|--:|--:|
| `cbo_opt56_employer_health_income_only` (Tier 1, **new**) | −697.0 | — | **−529.9** | — → **24.0%** |
| `fdii_repeal` (Tier 2b) | −200.0 | −170.00 | **−110.70** | 15.0% → **44.65%** |
| `biden_full_international` (Tier 2b) | −700.0 | −413.00 | **−353.71** | 41.0% → **49.47%** |
| `trump_universal_10` (fitted → Tier 2b) | −2,000.0 | −2,021.6 | **−1,258.5** | 1.1% → **37.1%** |
| `trump_china_60` (fitted → Tier 2b) | −500.0 | −531.1 | **−278.4** | 6.2% → **44.3%** |
| `auto_tariff_25` (Tier 2b) | −100.0 | −252.3 | **−182.2** | 152.3% → **82.2%** |
| `steel_tariff_25` (Tier 2b) | −60.0 | −103.9 | **−52.9** | 73.2% → **11.9%** |
| `reciprocal_tariffs` (Tier 2b) | −1,200.0 | −2,736.0 | **−1,396.8** | 128.0% → **16.4%** |
| `biden_ctc_2021` (LOO) | 1,600.0 | 574.1 | **1,528.5** | −64.1% → **−4.5%** |
| `ctc_extension` (LOO) | 600.0 | 432.0 | **714.2** | −28.0% → **+19.0%** |
| `biden_eitc_childless` (LOO) | 178.0 | 101.2 | **110.4** | −43.1% → **−38.0%** |
| `eliminate_salt` (LOO, **readmitted**) | −1,200.0 | *excluded* | **−1,077.9** | — → **+10.2%** |
| `repeal_salt_cap` (LOO) | 1,100.0 | 1,144.0 | **777.0** | +4.0% → **−29.4%** |
| ARP refundable credits (distributional) | — | 4.76pp | **7.77pp** | worse, and the better configuration |

### Five findings the wave produced

**1 — L9: the double count the plan named does not exist, and the package's
residual is a level.** §3 L9 expected `create_biden_full_international` to add a
per-country GILTI to Pillar Two's UTPR on the same undertaxed foreign profits.
It does not: `_estimate_utpr` reads profits of **foreign-parented** groups and
`_estimate_gilti_reform` reads the CFC income of **US-parented** groups. Those
bases are disjoint, so the new `_estimate_base_overlap()` term nets **exactly
zero** for all five shipped factories — pinned by
`test_no_shipped_factory_books_an_overlap` — and moves no benchmark row. What it
did establish is algebra worth keeping: with an 80% foreign tax credit, a
per-country GILTI at 21% claims `0.21·Y − 0.8·T` where a 15% top-up claims at
most `0.15·Y − T`, a difference of `0.06·Y + 0.2·T` that is positive for every
positive profit, so **a 21% per-country GILTI subsumes a 15% minimum tax in
every jurisdiction** and a policy carrying both raises the larger, never the sum.
At the 2026 statutory 13.125% the SOI CbCR distribution puts
`shared_claim_share` at **0.9916**, not 1 — a constant would have got the 21%
case right and this one wrong. The package's real residual is a **level**: the
module's UTPR returns $15B against Treasury's own **$136,313M** row and JCT's
implied **$133.9B**, two published figures agreeing within 2% while the module is
9× under both. Re-basing it needs OECD CbCR aggregates by ultimate-parent
jurisdiction; `oecd.org` returns HTTP 403 and the only reachable figure sits
*inside* the benchmark, so deriving from it would be circular.

**2 — L9: the FDII identity moves the model toward the document and away from
the target, and the lane registered that before it started.** The same function's
two branches disagreed by 59% about what the FDII deduction costs — a flat $20B/yr
for repeal against `(new − current) × base` on a $160B base, i.e. $12.6B/yr, for
a rate change. Repeal now uses the identity, on Treasury OTA's published
**$130,230M** over FY2025-2034. The carried −$200B is 54% above Treasury's own
cost for the provision, and `benchmark_sources.py` already recorded that it
matches neither the gross row nor the net score, so the row goes **15.0% →
44.65%** while getting more right. Third instance of this shape after L5's AMT
and L6's SALT.

**3 — L3: the credits rebuild, and a counterfactual worth more than any
parameter.** Replacing `Δcredit × units × participation` with two statutory
parameter sets run through `MicroTaxCalculator` over CPS ASEC tax units and
differenced on final liability took the module **45.1% → 20.5%**. The plan asked
for <20% and the lane pre-registered that it would not get there, for a reason in
the benchmarks rather than the model: two of the three targets are round hundreds
with a one-line provenance, and a structural path on real CPS units has no reason
to land on a round hundred. The largest single correction inside the wave is not
a parameter at all — IRC §24's $2,000 reverts to $1,000 after 2025, so a window
opening in 2025 is scored against current law for one year and the pre-TCJA
regime for nine; against a fixed $2,000 baseline the ARP credit costs $883B,
against the counterfactual the statute specifies **$1,528B**, and that one point
is more than 40 percentage points of `biden_ctc_2021`. Three dead levers
(`expand_qualifying_age`, `include_childless_adults`, `take_up_rate_change`) had
no reader because the identity had nowhere to put an eligibility expansion and
the microdata carried only an under-17 headcount; both had to exist first. And
the engine had been counting the EITC's **qualifying children** with the CTC's
under-17 column — **79.7M against 65.0M**, a 23% undercount of the population the
credit is scaled on. **Decision 4 is done**: `scripts/fetch_cps_asec.py` fetches
the 148 MB March 2024 ASEC archive by script (SHA-256 verified) into a cache
outside the repository, `data_builder.py` adds five dependent age bands, and
every one of the twenty pre-existing columns comes back byte-identical with the
SOI ratios (119% / 81%) unmoved. **Decision 5 is done**: the three tautological
credit benchmarks now carry a per-case declaration that the annual is the target
over ten.

**4 — L3: the ARP distributional benchmark got worse, and the 4.76pp it replaced
was two universes partly cancelling.** The plan said the residual was
"children-in-household distribution for the Recovery Rebate — a microsim-level
detail", so the lane put the rebate on return-level data (per-person $1,400,
phasing $75k–$80k / $150k–$160k, IRC §6428B). Three measurements in order:
**4.76** (rebate synthetic) → **6.29** (statutory CTC/EITC corrections, rebate
still synthetic) → **7.77** (all three on the microsim). Running one of three
components on IRS return counts and the other two on CPS tax units had the two
rankings pulling opposite ways. The gap is a **universe mismatch**: CBO's
quintiles are ~130M households, the model's 191M CPS tax units, and its bottom
quintile is **38.2M units with a mean AGI of $0**, so under full refundability
the model puts 53% of the bundle's dollars there against CBO's 34%. Two things
say the worse configuration is the right one: the quintile dollar averages move
from about a third of CBO's to close to them, and the bundle totals **$485B**,
within 10% of the three provisions' actual cost, where the mixed path could not
be summed at all. Reverting would buy 3pp by keeping one component in a different
universe. **The tax-unit-versus-household universe is a distributional-pipeline
lane, not a credits one.**

**5 — L8: gross → net, a sign defect, and Decision 6 discharged.**
`estimate_static_revenue_effect` returned gross customs duty with a 5% avoidance
haircut and stopped; CBO, JCT and Treasury all score an indirect tax net of a
~25% income-and-payroll offset. Adding it, converting retaliation's export loss
to receipts at `MARGINAL_REVENUE_RATE`, applying the duty tax-inclusively and
replacing every `TRADE_BASELINE` level with a 2024 Census measurement took the
three unfitted rows from a summed 353.5 points of error to **110.5**, and net/gross
to **0.599–0.655** — above the knowledge snapshot's 40–50% band, which is the
right side to miss on given there is no GDP-feedback channel. **The two fitted
coverage constants are gone**: `universal_coverage_rate` is now the Census
non-USMCA share (0.7197) and `china_effective_coverage` was deleted for an
incremental-rate identity, so both rows left the fitted tier and read 37.1% and
44.3% honestly. **The lane also found a sign defect in its own diff**:
`estimate_behavioral_offset` returned an unsigned positive number, so a 5pp
tariff *cut* on a $1,000B base scored $711B of deficit against a $553B gross
revenue loss — the income and payroll bases shrunk by a tax that had just been
reduced. Signed, the same cut scores $394B. The bug pre-dated the lane; the lane
made it ~6× larger and fixed it. No shipped preset moves on the sign fix, because
all five are increases. **Decision 6 is discharged**: every tariff preset moved
28–49% and the caption ships in the same PR, computed from the scored result so
it cannot drift:

> Net of offsets: $1,922.6B of gross customs duty becomes $1,258.5B of net
> receipts — a 0.65 net/gross ratio — after duty avoidance, the 25%
> income-and-payroll offset CBO, JCT and Treasury apply to any indirect tax and
> the receipts lost to retaliation. Import demand responds to the whole tariff
> (near-complete border pass-through). GDP feedback is not in this number.

### PR #100 — five targets, five judgements

Not a modelling lane; recorded here because four of the five change what a number
in this file means.

1. **CBO Option 56 promoted into Tier 1** at −$529.9B against −$697.0B (24.0%).
   A leakage exclusion is not permanent: L6 removed the fitted annual its only
   path ran through. Only CBO's third alternative is scored; 56.3 and 56.6 need a
   payroll base the module does not have. The residual is the year-indexed excess
   share, now measured inside the battery.
2. **Pillar Two re-benchmarked as a published range**, [−$102.6B, +$56.5B]
   (JCX-22-23 Table 2, Scenarios 4 and 2). The model's −$61.2B is **inside** it,
   distance to the nearest bound $0.0B, so its 23.5% against the −$80B midpoint
   is a distance from an editorial figure and not accuracy. The ledger gained
   range semantics; nothing moved in the registries or the app.
3. **The SALT constant replaced by its computation.** `annual_cost_no_cap = 120.0`
   was exactly the `eliminate_salt` target over ten; it is now **$89.55B** from
   SOI Table 2.1 at the statutory schedule, checked by the identical computation
   on the *limited* column returning $25.0B against the record's own 25.0.
   `loo.py` needed no per-case edit.
4. **The estate target examined and deliberately not moved**, with both errors on
   the record (`reported` −$450.0B: +0.00% carried / −4.75% published; `derived`
   −$457.2B: −1.60% / −6.43%) and a new `EXAMINED_NOT_REVISED` state so the
   question is not re-opened every pass.
5. **The Treasury FY2022 flag confirmed, not superseded.** The Table of Revenue
   Estimates prints exactly two rows under the relevant heading and none of them
   names transfers, gifts, death or realization, so −$322.0B is the combined
   figure. L1's substantive point stands and is a *model* finding: the death
   channel alone under a $1M exclusion exceeds the whole target, and it carries
   no behavioural response.

### Where the pre-registrations were wrong

Kept because §1.3 requires it.

- **L9 predicted the sectoral median at ≈41.8% and it came in at 47.06%** — an
  indexing slip in the hand arithmetic, which took the 5th and 6th of twelve
  sorted errors instead of the 6th and 7th. Every other L9 figure landed to two
  decimal places.
- **L8 registered the fitted tier as "55 rows at 15.4% → 53 at ≈15.8%"** and had
  both the population and the direction wrong. The fitted tier was 30 rows at
  2.2%: the 55 came from counting every scorecard entry with
  `calibrated_to_target=True`, which sweeps in the out-of-sample Generic rows
  that carry the flag by default. On the right population the two departing rows
  scored 1.1% and 6.2% against a 2.2% mean, so removing them **lowers** it. Any
  tier arithmetic done outside `cold_holdout.py` has to split the specialized
  entries the way that script does.
- **L3 predicted `biden_ctc_2021` at about −28% and it landed at −4.5%** — missed
  on the good side, and the cause is the counterfactual in finding 3 rather than
  the mechanism. **L3 predicted the ARP distributional benchmark at 2.0–4.5pp and
  it landed at 7.77pp** — missed outright and in the wrong direction, which is
  finding 4.

### What Wave 3 did not do

No lane touched `preregistered.py`'s targets from a modelling branch,
`cold_holdout.py`, `run_loo.py`, `loo.py`'s leakage guard,
`tests/test_preregistration.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`'s figures or any
CI threshold; PR #100 used the two supersede mechanisms and PR #102 re-derived
the gate by the workflow's own published rule (ceiling `ceil(31.0 × 1.25) = 39 →
40`, unchanged; floor `19 − 1 = 18`, a tightening). No per-benchmark constant was
added and two were deleted. **Every Wave 3 module keeps `reported` as the app
default under Decision 1**, and the numbers that decided it are on the record:
credits **0.0% reported against 20.5% derived** — read with Decision 5 in hand,
since the three fitted annuals *are* their targets over ten, so the comparison is
not one the derived path could win; expenditures unchanged in `reported` mode
with the SOI derivation feeding only the held-out path; international and trade
carry no mode switch, and the tariff presets moved because the *score* changed,
not because a default did. `CREDIT_APP_MODE` was the one line that would have
changed what a user sees, and it did not change.

## 5.4 Wave 4 outturn (2026-09-05)

Six lanes on disjoint files — distributional households (`model/w4-distributional-households`, PR #104),
Option 56's excess share (`model/w4-option56-excess-share`, PR #105), AMT
phase-outs (`model/w4-amt-phaseouts`, PR #106), gains at death
(`model/w4-gains-at-death`, PR #108) and pharma Part D (`model/w4-pharma-part-d`,
PR #109) — plus a target-provenance lane (`provenance/wave4-targets`, PR #107)
and the coordinator's gate re-derivation (PR #110). **Wave 4 is not in §5's
sequencing; it is six of §6.2's carry-over items taken in parallel.** Each lane
pre-registered its expected movement in `planning/lanes/` before touching code,
and each appended an outturn; those files carry the per-row detail and are the
record, not this summary. Every figure here is from `python
scripts/cold_holdout.py`, `python scripts/run_loo.py --donor-matrix` and `python
scripts/run_validation_dashboard.py` on the **merged** tree — which is not the
same as any lane's own before/after, because several lanes touch the same tiers.

### The tiers, before → after

| tier | n | before | after |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 26 | 31.0% mean / 15.1% median / 13 within 15 / 19 within 25 | **18.0% / 12.6% / 14 / 21** |
| Calibrated reference (fitted) | 28 → **23** | 2.0% / 0.1% median / 28 within 15 | **1.6% / 0.1% / 23 within 15** |
|  — *rows held in place* | — | 29 @ 4.3%, 28/29 | **28 @ 3.0%, 27/28** (`eliminate_salt` 22.3%); 29 @ 5.2%, 27/29 with the TCJA-AMT row too |
| Unfitted reconstructions | 26 → **31** | 61.8% / 38.0% median / 5 within 15 | **56.6% / 29.9% / 9 within 15** |
|  — *the same 26 rows* | 26 | 61.8% / 38.0% | **65.7% / 40.5%** — *worse* |
|  — sectoral subset | 14 → **15** | 81.0% / 38.0% median | **82.6% / 39.0%**; **88.2%** on the constant 14 |
|  — P.L. 119-21 line items | 8 | 35.8% | **35.8%**, unmoved |
|  — capital-gains scenarios | 3 | 39.6% | **39.6%**, unmoved |
|  — TCJA AMT relief | 1 | 66.8% | **66.8%**, unmoved |
|  — *Wave 4 arrivals* | **5** | — | **9.4%** |
| Leave-one-out | 18 derivable | 28.4% / 16.5% median / 9 within 15 | **29.6% / 19.1% / 8** |
|  — `Credits` | 3 | 20.5% | **18.5%** |
|  — `Expenditures` | 5 | 30.2% | **35.7%** |
| Not cross-validatable | 4 | — | **4**, unchanged |
| Scorecard rows | 80 | 73 published | **80 / 73**, unchanged |
| `revised_target_entries` | 3 → **15** | — | 12 Tier-2 revisions, one of them a **range** |
| `line_item_differs` (calibrated) | 13 → **5** | — | every remaining row carries a written verdict |
| Provenance (calibrated) | — | 19 / 13 / 15 / 7 / 0 | **30 / 5 / 12 / 7 / 0** |
| Distributional | 7 | 0.00–7.77pp | **0.00–5.86pp** (ARP 7.77 → **3.72**) |
| Tests | — | — | **3322 passed, 1 skipped** on the merged tree |

**Two of those tiers changed population and both means fell for reasons that are
not improvements, so the like-for-like readings are printed beside them and
neither may be dropped.** The fitted tier lost five rows *mechanically* when
PR #107 moved their targets, and held in place it reads 28 @ 3.0%. The
reconstruction tier gained those same five at an average of 9.4% and its printed
mean fell 5.2pp — but on the 26 rows it already held it reads **65.7%**, *worse*
than 61.8%, because PR #109's pharma rebuild moved two rows away from their
targets. Leave-one-out is the mirror case: it **rose** 28.4% → 29.6% with **no
derivation moving at all**, because three of its targets did. A mean that moves
because the population moved has not improved, and a mean that moves because a
target moved has not measured the model — §2.3's own rule, twice over.

Tier 1's error mass fell **805.8 → 468.1**, and capital gains went from 405.6 of
it (50.3%) to **80.9** (17.3%). The two payroll rows are now the tier's largest
single mass at 109.6 (23.4%).

### Per-lane, what moved

- **PR #108 gains at death** did almost all of Tier 1's move, on its own taking
  the tier 31.0% → 18.5%. Six carve-outs transcribed from the Green Books'
  own text — spousal, charitable, §121 residence, tangible personal property, a
  family-owned-business deferral, and the per-donor exclusion applied *after* the
  others — plus a semi-log rate response at death. Predicted bands and actuals:
  `cbo_opt51_gains_at_death` registered 12–28% and landed **19.3%**;
  `biden_capital_gains_39` registered 5–30% and landed **16.7%**;
  `treasury_capgains_39_plus_stepup_elim` registered 0–28% and landed **0.2%**;
  Tier 1 registered 16–23% and landed 18.5%. The hand path computed before any
  module code changed predicted death channels of ≈−431, −238 and −278 and the
  model returned **−432.8, −240.5 and −322.7**.
- **PR #105 Option 56** landed on its number and missed two counts: −$605.8B
  against −$697.0B, **13.1%**, where §3 said "about 13%, approximately −$606B".
  The slip is arithmetic — §3 predicted the median and both within-N counts
  unchanged "because 24% and 13% are both outside 15%", and 13.1% is not.
- **PR #104 distributional households** landed every registered row: ARP
  registered 1.5–6.0pp (point 3.5) and landed **3.72**, its lowest quintile
  registered 26–40% and landed 28.6%, its highest registered 1–6% and landed
  5.4%, and the six control tables were registered unmoved to the hundredth and
  were. The one miss was the derived file's size (**8.57 MB, +10.9%**, against a
  registered "close to 7.0 MB").
- **PR #106 AMT phase-outs** moved no benchmark, by design, and every registered
  row landed. The one miss was a magnitude hedged too low: a $100,000 MFJ
  threshold cut was registered as "low-single-digit $B/yr" and returns **$9.09B
  in 2026, $92.7B over ten**.
- **PR #109 pharma Part D** is the lane whose prediction failed, and it failed in
  the direction the lane had ruled out: **every aggregate got worse**. The two
  pre-registered mechanisms landed within $3B of the pre-registered figure; a
  fifth change nobody pre-registered was larger than the three that were.
- **PR #107 provenance** moved thirteen targets and **no model figure at all** —
  every `model_10yr_billions` byte-identical, every LOO derivation unchanged, no
  constant retuned, no threshold touched. **Six of the thirteen got worse.**

### Three findings the wave produced

**1 — A row can land on its target for the wrong reason, and the only defence is
the pre-registered decomposition.** `treasury_capgains_39_plus_stepup_elim`
reads **0.2%** and that is **two errors cancelling**. The lane predicted 7.2%
retention of the death channel and the model delivered 12.8%; the row landed
because a death channel nearly twice the hand path's size closed a gap the hand
path had left open in the other direction. The honest statement is the retention
ratio — the mechanism removes **87.2%** of that row's death channel where the
pre-registration said 92.8% — and it is only sayable because the lane wrote the
ratio down first. **Nothing in this repository may quote that 0.2% as accuracy.**

**2 — A lane's own mechanism can condemn a constant in a different leg, and the
protocol's whole value is what happens next.** PR #109's negotiation ladder
implies that current law's 160 cumulative selections carry **$256.8B** of gross
Part D spending by 2034, which does not fit inside the unsourced
`medicare_part_d_gross_spending_billions = 220.0` that the *reference-pricing*
leg also reads. CMS's own sentence puts the total at **$281B**. Taking the
sourced number pushed international reference pricing from an ≈−$660B prediction
to **−$801.0B**, i.e. 646.2% → **701.0%** — past where it started. The
alternative was to keep an unsourced number because it flattered the prediction,
and the lane took the $281B and reported the miss. `expand_drug_negotiation` went
25.7% → **93.3%** for a separate, smaller reason: an expansion of the *annual
selection cap* has nothing to raise until 2029, so it bites in 6 of 10 years.

**3 — A falsification test can fire and still be pointing at the wrong thing.**
The gains-at-death lane registered "the two Green Book rows landing on opposite
sides of their targets" as evidence of a bug in the exclusion ordering. They do
land on opposite sides. The ordering is not the cause, and the evidence is
arithmetic: the ordering is pinned by a test, applying the exclusion first would
raise **both** scores, and the residual is **monotone in the exclusion**. The
cause is the **five-class decedent ladder**, which has no within-group
dispersion — after carve-outs, gain per decedent is $9.71M / $1.89M / $0.92M /
$79K across the classes, so a $1M exclusion leaves two classes in tax and a $5M
exclusion leaves one, knocking 3,677 decedents × $0.89M out in a single step.
Moving the exclusion $1M → $5M costs the model **$82.2B** of death channel where
it costs Treasury **$33.4B**. That is a dispersion defect and it is now item 26
below.

Two smaller findings worth keeping: **PR #105** found that CBO caps premiums
*and* health spending accounts (FSA/HRA/HSA), which the repository's premium
distribution cannot represent, and that `TaxExpenditurePolicy`'s behavioural
offset carries the **reverse sign convention** to `TaxPolicy`'s — magnifying
where the base class erodes, worth +20% on this row and unsourced in magnitude on
every expenditure benchmark. **PR #104** found a per-household dollar column
wrong by a factor of three that no gate in the repository could see, because the
error metric scores shares and the shares came from a correctly weighted merge.

### Where the pre-registrations were wrong

| lane | what it said | what happened |
|---|---|---|
| pharma | reference pricing ≈−$660B (≈560%), negotiation ≈−$64B (≈87%), sectoral ≈79%, reconstruction ≈61% | **−$801.0B (701.0%)**, **−$33.5B (93.3%)**, sectoral 89.8%, reconstruction 66.5% — the omission is §5.6 of that lane, and it is the whole of the miss |
| Option 56 | median and both within-N counts unchanged | 13.1% crosses the 15% line, so within-15 went 13 → **14** and the median 15.1% → 13.6% |
| gains at death | the two Green Book rows on opposite sides ⇒ exclusion-ordering bug | they are, and the cause is the decedent ladder's dispersion (finding 3) |
| distributional | derived file "close to 7.0 MB, well under 8" | **8.57 MB, +10.9%** |
| AMT | a $100,000 MFJ threshold cut is "low-single-digit $B/yr" | **$9.09B in 2026**; the band was written from the claw-back's average value rather than its value where the threshold sits |
| provenance | none — the lane pre-registered no model movement, and none occurred | — |

### What Wave 4 did not do

No lane touched `preregistered.py` from a modelling branch, `cold_holdout.py`,
`run_loo.py`, `loo.py`'s leakage guard, `tests/test_preregistration.py` or any CI
threshold; PR #107 used the two supersede mechanisms and PR #110 re-derived the
gate by the workflow's own published rule (ceiling `ceil(18.0 × 1.25) = 23`,
rounded up to the nearest 5 = **25**; floor `21 − 1 = **20**`, a tightening on
both). **Every Wave 4 module keeps `reported` as the app default under
Decision 1** — the AMT lane's numbers are unchanged at 22.3% reported against
54.2% derived, and `AMT_SCORECARD_MODE`'s blocker is still
`repeal_individual_amt`'s locked-protocol entry, a gate no lane may edit. The
shipped numbers that moved are the three drug-pricing presets, by design and with
a Decision 6 caption in the same PR. `repeal_individual_amt`'s $450B stays
(item 2 below), the twelve remaining calibrated `secondhand` rows are untouched,
and nothing was done about *why* the international rows miss — those are items
9, 10 and 11.

## 5.5 Wave 5 outturn (2026-09-05)

Three modelling lanes on disjoint files — payroll at the margin
(`model/w5-payroll-margin`, PR #113), corporate at the margin
(`model/w5-corporate-margin`, PR #114) and the preferential rate
(`model/w5-preferential-margin`, PR #116) — plus two blue-tier PRs (frozen
classroom links, #111; the app's default scoring window, #115) and the
coordinator's gate re-derivation (#117). **Like Wave 4, Wave 5 is not in §5's
sequencing**: it is three of §6.2's carry-over items taken in parallel. Each lane
pre-registered its expected movement in `planning/lanes/` before touching code
and appended an outturn; those files carry the per-row detail and are the record,
not this summary. Every figure here is from `python scripts/cold_holdout.py`,
`python scripts/run_loo.py --donor-matrix` and `python
scripts/run_validation_dashboard.py` on the **merged** tree — which is not any
lane's own before/after, because all three moved the same battery against the
same 18.0% base.

### The tiers, before → after

| tier | n | before | after |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 26 | 18.0% mean / 12.6% median / 14 within 15 / 21 within 25 | **15.9% / 11.4% / 16 / 22** |
| Calibrated reference (fitted) | 23 | 1.6% / 0.1% median / 23 within 15 | **1.6% / 0.1% / 23**, unmoved — 0 rows changed |
| Unfitted reconstructions | 31 | 56.6% / 29.9% median / 9 within 15 | **56.6% / 29.9% / 9**, unmoved — 0 rows changed |
| Leave-one-out | 18 derivable | 29.6% / 19.1% median / 8 within 15 | **byte-identical output** |
| Distributional | 7 | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 80 | 73 published | **80 / 73**, unchanged |
| `revised_target_entries` | 15 | — | **15**, unchanged — no target moved |
| Tier 1 CI gate | — | `25 / 20` | **`20 / 21`** (PR #117) |
| Tests | — | 3322 passed, 1 skipped | **3415 passed, 1 skipped** on the merged tree |

**Wave 5 is the first wave in which only Tier 1 moved, and that is the point.**
Waves 2, 3 and 4 each had to be read with a constant-population caveat attached,
because rows entered or left a calibrated tier. Here nothing did: no target
moved, no constant was retuned, and **0 of 23 fitted rows and 0 of 31
reconstruction rows changed**, with `run_loo.py --donor-matrix` byte-identical.
Each lane registered that as a falsification test in advance and each passed it.
So the Tier 1 movement is the model, with no composition to net out — which also
means it is the wave with the fewest hiding places, and two of its five moved
rows moved the wrong way on purpose.

Tier 1's error mass fell **468.1 → 412.9**. The composition changed more than the
total: payroll went 109.6 → **15.6** (from the largest single mass to 3.8% of the
tier), capital gains 80.9 → **104.5** (17.3% → 25.3%, the largest again), and
corporate 47.1 → **62.3** (15.1%). Grouped by cause, the tier is now capital
gains 104.5 (25.3%), the bracket-aggregate ceiling 91.4 (22.1%), module revenue
identities at the margin 77.9 (18.9%), budget-authority spend-out and level shape
63.4 (15.4%), the filing-status threshold 62.6 (15.2%) and the one
tax-expenditure cap 13.1 (3.2%).

### Per-lane, what moved

- **PR #113 payroll** is the whole of the improvement and more. The two CBO
  Option 61 rows went **54.1% / 55.5% → 7.5% / 8.1%** — 25th and 26th most
  accurate of 26 to **7th and 9th** on the merged tree (the lane doc says 8th
  and 10th, which held on its own branch before the other two lanes moved rows
  past them) — and the outturn matched §3's hand arithmetic
  to the decimal (−$1,378.2B and −$2,745.0B, both computed before a file was
  opened). All seven falsification tests fired and none against the lane; every
  Tier 1 row other than the two named is identical to the dollar, and the
  donor-matrix output and the 53-preset sweep are byte-identical.
- **PR #114 corporate** is a **pre-registered regression that landed to the
  decimal**: `cbo_opt64_corporate_rate_1pp` **47.1% → 62.3%**, with all fifteen
  registered rows landing as registered and the whole
  `run_validation_dashboard.py` output differing from the branch point by **one
  line**. `biden_corporate_28` and `trump_corporate_15` are unmoved in the
  shipped `reported` mode; in `derived` they read 7.81% and 11.53% against
  reported's 3.73% and 0.11%, so Decision 1 keeps `CORPORATE_APP_MODE` at
  `reported` (1.92% against 9.67%) and nothing a user sees changed.
- **PR #116 preferential rate** landed every registered figure exactly, including
  the registered regression, because both legs of the score are linear in the
  base and the stock ratio is a ratio: `cbo_opt47_ltcg_qdiv_2pp` **44.8% →
  10.5%** (registered 8–14%), `biden_capital_gains_39` **16.7% → 31.4%**
  (registered 28–35%), `treasury_capgains_39_plus_stepup_elim` **0.2% → 43.3%**
  (registered 40–47%), `cbo_opt51_gains_at_death` unchanged to the dollar. The
  death channel is unchanged to the cent on every row, which is the test that the
  projection did not leak into Wave 4's work.
- **PR #115 window** moved no scorecard number at all — five scripts compared
  structurally before and after, all identical — and two pharma presets by one
  calendar year, correctly.

### Four findings the wave produced

**1 — A plan's scoping can be wrong on the merits, and the source says so in two
sentences.** §2.1 of this file scoped the payroll rows as "employer-share
incidence + income-tax offset". CBO's own option text says *"The new tax would be
paid entirely by employees"*, and its *Other Considerations* paragraph exists to
explain that an employer-side tax would raise **less**. Adding the offset the
plan named would have moved the model *further* from the target, for a reason the
source explicitly rules out. The employer-share rule is built anyway — the module
could not otherwise represent Medicare — and evaluates to exactly zero here.
Reading the option before writing the mechanism is what that lane did
differently, and the plan's §2.1 row is wrong on the merits rather than merely
out of date.

**2 — Three modules have now been found with an inverted or absolute-valued
behavioural offset, and every gate in the repository was blind to all three.**
`trade.py` (Wave 3, L8), `payroll.py` (W5-A finding 3) and `corporate.py` (W5-B
finding 4). The mechanism is the same each time: the engine computes
`deficit = −revenue + behavioural`, so an offset returned with the wrong sign (or
wrapped in `abs()`) **magnifies** the score where it should erode it — a payroll
tax increase that raises 17.5% more than it levies, a shipped corporate rate cut
that books a first-year deficit effect of **+$159.75B** on a static −$142B. None
of the three was found by a test. They cannot be, as things stand: **each
module's calibrated factories zero the elasticity**, so the fitted tier and the
leave-one-out column are structurally blind to the sign, and the only surfaces
that reach the bug are the uncalibrated Tier 1 shapes and the demo-grade bill
tracker. Two of fourteen modules were found by a lane that happened to be reading
the file; the third by a lane that was looking for something else. **The
remaining modules have not been swept**, and `tax_expenditures`' reverse
convention (W4-3a finding 3) is a fourth instance of the same family. This is
item 1 of §6.2.

**3 — A fitted constant can be a right quantity that stopped being updated, and
linearity hides it perfectly.** `corporate.py`'s $1,900B base is within 3% of
SOI's **TY2018** income subject to tax ($1,956.7B); the TY2022 figure is
$2,879.1B. Nobody chose a wrong concept. Because the module is linear in the
base, the staleness was invisible against a target calibrated at the same vintage
— and it was two errors, not one: a base 34% too small and a flat 12.5% offset
well below what the published semi-elasticity implies at 7pp, which nearly cancel
at 7pp and do not at 1pp. Correcting *one* would have looked like a regression on
both rows. The general lesson is a vintage audit rather than a corporate one.

**4 — A row that agrees with its target can be hiding a stale input, and removing
the offsetting error is progress that looks like damage.**
`treasury_capgains_39_plus_stepup_elim` read **0.2%** after Wave 4 and Wave 4's
own lane doc already recorded that as two errors cancelling. The second of the
two was a realizations base frozen at IRS SOI tax year 2023 and priced unchanged
in every year of a ten-year window. W5-C removed it and the row reads **43.3%**,
which is not a worse model but an honest one — and about **17 of those 43 points
are the window the row is scored on** (target FY2022–2031, model FY2025–2034, no
`effective_start_year` on the record). Two more results from that lane are worth
keeping. The **qualified-dividends hypothesis is refuted**, and by arithmetic
already in the tree: SOI Table 3.5's preferential columns *exceed* the whole
year's realized gains in both vendored years (1.046 and 1.189), so they contain
qualified dividends by construction, and adding a column would have moved the row
from 45% under to about 28% under *by being wrong twice*. And **CBO's own path
says the frozen elasticity was never the problem**: inverting Option 47's
published annuals gives a semi-log coefficient of 4.17 falling to 1.81 on a flat
base — the projection error being absorbed by the elasticity year after year —
against **3.17 / 3.01 / 3.12** on the projected base, either side of JCT's own
published 3.1 and the frozen DMM 3.2727.

### Where the pre-registrations were wrong

| lane | what it said | what happened |
|---|---|---|
| payroll | −$1,378.2B / +7.5% and −$2,745.0B / +8.1%, every aggregate | **exact**, to the decimal, on both rows and every aggregate |
| corporate | fifteen rows including the 62.3% regression and the 1.92%/9.67% Decision 1 means | **exact**, all fifteen; the dashboard differs from the branch point by one line |
| preferential rate | three bands, three channel figures, five Tailor rows | **all inside**; and the lane says plainly that this is algebra rather than prediction — both legs are linear in the base, so the figures were always going to reproduce if the implementation was correct |
| preferential rate (Wave 2's §2.6) | growing the realizations base would take `cbo_opt47` "from ~30% to ~150%" | it cannot: the row was at 55% of its target and the largest factor applied in any year is 1.86. It went to **90% of target**. The rule being defended — "stocks are indexed, flows are not" — was right about estate and payroll and wrong about this flow |
| corporate (CI) | `ceil(18.6 × 1.25)` → 25 and `21 − 1` → 20, unchanged | correct for that lane alone; on the **merged** battery the rule gives **20 / 21**, which is PR #117 |

**The honest reading of three exact outturns is not that the lanes were prescient
but that the mechanisms are algebraic**, and the lanes say so themselves. What
was really being registered was the *choice* — which base, which rate, on which
rows and at what cost — and the test of a choice is the finding it produces, not
the decimal it reproduces.

### What Wave 5 did not do

No lane touched `preregistered.py`, `holdout.py`, `loo.py`,
`target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`, `benchmark_sources.py`,
any CI threshold or `tests/test_cold_holdout.py`; PR #117 re-derived the gate by
the workflow's own published rule, which a modelling lane may never do.
**Every Wave 5 module keeps `reported` as the app default under Decision 1** —
corporate 1.92% reported against 9.67% derived, and payroll and capital gains
shipped no mode flag at all. The only shipped numbers that moved are the four
Tailor capital-gains rows (Decision 6 caption in the same PR) and the two pharma
presets PR #115's window carried forward a year. Left undone and recorded:
the corporate module's missing leave-one-out row and its `abs()` offset (both
pinned by tests so the next person makes a decision rather than an edit);
payroll's two unsourced flat-share "elasticities" and its unexplained
base-growth gap; the capital-gains receipts lag, the un-indexed $1M threshold and
the FY2022 window; corporate's R&D, depreciation, CAMT and credit-carryforward
channels; and the engine's want of a general `Policy.scores_by_year()` now that
two classes have had to opt out of the year-indexed path.

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

### 6.1 Open owner decisions after Wave 2 (added 2026-09-02) — *superseded by §6.2*

Six questions the wave surfaced or left standing. None is a modelling lane's
call; all six are recorded here so no lane has to rediscover them.

**Wave 3 closed two of the six and left four standing.** Item 3 (the SALT
constants) is **closed**: PR #100 replaced `annual_cost_no_cap = 120.0` with the
SOI computation, `eliminate_salt` is derivable again at +10.2% and
`repeal_salt_cap` reads an honest −29.4%. Item 6 (promote Option 56) is
**closed**, and not the way it recommended: the option was promoted *before* the
year-indexed excess share landed, because L6 had already removed the leakage the
exclusion was for and the 24.0% residual is a documented out-of-sample miss
rather than a blocker; the year-indexed share and the two payroll alternatives
carry forward. Items 1, 2, 4 and 5 are unchanged and are restated in §6.2, which
is the single live list.

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

### 6.2 Carry-over list after Wave 5 (rewritten 2026-09-05) — the single live list

**Waves 1–5 of this plan are complete.** What follows replaces the Wave 3
edition of this list. None of it is a modelling lane's call to make on its own;
sequencing is the owner's. Each item names the artefact it lives in so nobody has
to rediscover it.

**Wave 5 closed three of §2.1's own rows and opened six items.** Struck, with
where the work landed:

- ~~**Payroll identity at the margin** (§2.1 row 3, 110 units, 8.3% of the
  pre-Wave-1 tier)~~ — **PR #113**, `planning/lanes/W5_payroll_margin.md`. The
  two Option 61 rows **54.1% / 55.5% → 7.5% / 8.1%**. Note that §2.1's own
  tractability note — "needs employer-share incidence + income-tax offset" — was
  **wrong on the merits**, not merely out of date: CBO's option text says the tax
  is paid entirely by employees, so the offset it named does not exist and adding
  it would have moved the model further away. The real defect was a base built as
  Medicare receipts ÷ 2.9%. See §5.5 finding 1.
- ~~**Corporate rate at the margin** (§2.1 row 6, 47 units, "low priority; one
  row")~~ — **PR #114**, `planning/lanes/W5_corporate_margin.md`. Taken, and the
  row went **47.1% → 62.3%** as a pre-registered regression: the base is now IRS
  SOI Table 11's published statutory figure and the fitted constant it replaced
  was a **TY2018 vintage**. What is left is CBO 60557 and Treasury's FY2025 Green
  Book pricing a percentage point 42% apart, which is not this module's to close.
  The lane's two live findings became items 22 and 23 below.
- ~~**The preferential-rate base** (`cbo_opt47_ltcg_qdiv_2pp`, the residual L1 and
  Wave 4 both left behind)~~ — **PR #116**,
  `planning/lanes/W5_preferential_margin.md`. **44.8% → 10.5%** by projecting the
  realizations base with the accrued-gains stock it is a flow off; the
  qualified-dividends hypothesis was **refuted** rather than adopted. The
  registered cost was the two Green Book rows crossing their targets (16.7% →
  31.4%, 0.2% → 43.3%), and the window half of the second became item 24.

**Item 15 below — the five-class decedent ladder — is unchanged and is still the
first place a later capital-gains lane should look.** Wave 5 touched the rate
channel only; the death channel is unchanged to the cent on every row.

**Wave 4 closed nine items and half-closed a tenth.** Struck, with where the work
landed: the household/tax-unit distributional universe (**PR #104**; ARP
7.77 → 3.72pp, benchmarks registered on the universe their source ranks, surfaces
reporting the universe *scored*); the death-channel behavioural response and its
carve-outs (**PR #108**; Tier 1 31.0% → 18.5% on that PR alone); Option 56's
year-indexed excess share (**PR #105**; 24.0% → 13.1%); L7's Part D channels
(**PR #109**; three federal channels, a negotiation ladder, a RAND base — and two
reconstruction rows got worse, which the lane reports); L5's phase-out thresholds
(**PR #106**; statutory §55(d)(2) from eleven Revenue Procedures, no benchmark
moved by design); the twelve remaining `line_item_differs` rows (**PR #107**;
nine revised, three examined-and-left, `line_item_differs` 13 → 5 with a written
verdict on every survivor); `repeal_salt_cap`'s unsourced $1,100B (**PR #107**;
PWBM Table 3's +$1,169.0B, on this repository's own window); `ctc_extension`
against JCT's +$816.8B (**PR #107**; answered "no", recorded in
`EXAMINED_NOT_REVISED` — CRS's figure is a superset and JCT's scores a different
credit already carried here); and the dead `PHARMA_VALIDATION_SCENARIOS`
registry (**PR #109**). The half-closed one is the mortgage record's
`annual_cost_no_limit` — **sourced** to Treasury OTA's FY2019 *Tax Expenditures*
Table 1 row 59 ($100.32B/yr) and still deliberately **unwired**, because the
source shows what it is the "no limit" level *of* is the pre-TCJA regime as a
whole rather than IRC §163(h)(3)(F); the open half is now its sibling
`annual_cost = 25.0`, a pre-P.L.119-21 level on which JCT and Treasury disagree
by 2–4×.

**Yardstick and protocol**

1. **Re-lock the holdout protocol, or keep the warning convention?** Carried
   unchanged. `pwbm_39_with_stepup` is a locked id in
   `revenue-scorecard-post-lock-2026-05-02` and rates Poor with the direction
   right, so `check_readiness.py`'s `holdout_protocol` check reports **WARN**
   under the documented-miss convention rather than failing. The protocol was
   locked over a scorecard in which that entry carried a fitted 5.3× multiplier
   that no longer exists. **The entry stays in the battery either way.** This is
   also the one line blocking Decision 1's scorecard half for AMT, and it is what
   blocks item 2.

**Targets that are wrong, unsourced, or contradicted**

2. **`repeal_individual_amt`'s $450B.** Carried unchanged through three passes.
   No published post-2025 repeal score exists; TPC T25-0049's $948.9B is a
   baseline projection *and* `amt.py`'s own input, so adopting it would
   manufacture a 0% row out of the leakage `loo.py` guards against. Internally
   incoherent with the transcribed $1,357.1B, since a full repeal cannot cost
   less than extending the exemption on the same baseline. Closing it needs a
   published score or an owner decision on item 1.
3. **The two SALT baselines still contradict each other.** `PROVENANCE_wave4.md`
   §3 states rather than resolves it: `repeal_salt_cap` is now explicitly priced
   against a permanent $10,000 cap (PWBM Table 3's extended-TCJA world) while
   `eliminate_salt` is priced on CBO Option 49's world where the cap has lapsed.
   Reconciling them needs a baseline-vintage concept the expenditure module does
   not have — and `eliminate_salt`'s CBO baseline is in any case no longer
   current law after P.L. 119-21 sec. 70120.
4. **`annual_cost = 25.0` on the mortgage record is a pre-P.L.119-21 level.**
   JCT's JCX-45-25 puts the capped expenditure at $45.5B in FY2025 rising to
   $54.9B in FY2029 (the $40,000 SALT cap took itemising claimants from 11.8M to
   17.8M returns), while Treasury's FY2027 edition gives $23.9B falling to $14.1B
   on the *same* statute — a 2–4× disagreement driven by Treasury's
   comprehensive-income baseline against JCT's normal-tax one. Choosing between
   them is an owner decision with a visible consequence for `eliminate_mortgage`.
   Its sibling `annual_cost_no_limit` stays sourced-but-unwired, for the reason
   above.
5. **The twelve remaining calibrated `secondhand` rows.** Down from fifteen.
   Several have nothing to move *to*: both Social Security payroll targets
   (OCACT publishes percent-of-payroll and no dollars), `repeal_ira_credits`,
   `trump_china_60`, `cap_charitable`, `eliminate_step_up`, `biden_ctc_2021`,
   `repeal_ptc`, `cap_employer_health`, plus `repeal_individual_amt` and the two
   Wave 4 examined and left (`steel_tariff_25`, `eliminate_mortgage`). Each needs
   the same per-target judgement `PROVENANCE_wave4.md` applied to seventeen.
6. **`expand_drug_negotiation`'s −$500B and `international_reference_pricing`'s
   −$100B are `model_estimate` targets** and the two worst rows in the
   reconstruction tier. Neither is in `target_revisions.py`; whether either
   should be **retired** for want of a document is an owner decision on the
   ledger's own terms. `W4_pharma_part_d.md` §5 says so explicitly.

**Mechanisms named and not built**

7. **Option 56's two payroll alternatives and its FSA/HRA/HSA base.** Two halves
   of the same gap. CBO does not cap premiums, it caps "premiums **and** health
   spending accounts"; the repository's premium distribution has no account
   dimension, and account contributions concentrate in the same households whose
   premiums already exceed the cap — a level *and* a shape error, with a named
   source (MEPS-IC, KFF). Separately, alternatives 56.3 and 56.6 stay out of
   scope until the module has a payroll base: CBO's own table sizes that leg at
   **$276B, 38.9% of the income-tax leg**, and reaching it needs the joint
   distribution of premiums and earnings, which the repository does not have
   (`employer_health_premium_distribution.csv` has no earnings dimension,
   `tax_microdata_2024.csv` has no premium column). *(New framing from
   `W4_option56_excess_share.md` findings 2 and 4.)*
8. **The expenditure module's behavioural sign convention.** *(New, from
   `W4_option56_excess_share.md` finding 3.)*
   `TaxExpenditurePolicy.estimate_behavioral_offset` returns an offset with the
   **opposite** sign to `static_effect`, where `TaxPolicy` returns one with the
   same sign and its docstring says why — so the expenditure module *magnifies*
   where the base class erodes. On Option 56 it is worth **+20%** and is
   directionally right (CBO's text says both channels increase revenue), but it
   is unsourced in magnitude on every expenditure benchmark. Changing it is
   module-wide: it moves every fitted expenditure row **and** the leave-one-out
   column together. An owner decision, not a lane's. **Wave 5 found the same
   family of defect in two more modules** — see item 22, which subsumes this one
   into a sweep.
9. **Re-base the UTPR on JCT Equation 2** (OECD CbCR aggregates by
   ultimate-parent jurisdiction). The single largest remaining item in
   `international.py`: the module's $15B against Treasury's $136,313M and JCT's
   implied $133.9B. Blocked by `oecd.org` HTTP 403s; deriving the base from
   Treasury's own row would be circular because that row sits inside the
   benchmark. **This is what a later international lane should open with** — and
   `biden_full_international` now reads **44.1%** against its own document.
10. **GILTI's two self-declared calibration constants**
    (`gilti_cbc_revenue_multiplier = 1.20`, `gilti_ftc_offset_rate = 0.40`).
    Treasury OTA prices the whole CFC active-income preference at $383,830M over
    FY2025-2034 against the module's implied $271B for the identity that would
    replace both — but the tax expenditure also covers §245A exclusions a GILTI
    rate change does not recover, so the swap is not one-for-one.
    `biden_gilti_reform` now reads **38.4%** against the Green Book's own row.
11. **A GDP-feedback channel for tariffs.** The single largest remaining piece in
    `trade.py`, and why net/gross sits at 0.60–0.66 rather than the published
    40–50% band. The retaliation channel is also a reduced form returning 2.5×
    less than FF861 for the same policy, `reciprocal_coverage_rate = 0.50` is the
    one shape assumption left that is not a measurement, and `min_volume_factor =
    0.20` now binds above ~55pp rather than ~95pp because the elasticity roughly
    doubled. One design gap the reciprocal **range** does not close: the
    published estimates apply a 10% floor rising to 50% by halving each partner's
    bilateral-deficit-to-imports ratio, with sectoral exemptions, where the module
    applies a flat ~20pp to half of goods imports.
12. **Pharma's utilisation response, Part B/D split and cost-sharing re-split.**
    *(New, from `W4_pharma_part_d.md` §5.9.)* The module still applies a price
    index to spending with no utilisation or launch-delay response, still carries
    one Part B base beside a now-three-channel Part D, and still splits
    cost-sharing on shares the Part D redesign has superseded. These are the
    named residuals behind a 701.0% row.
13. **§55(b)(1)'s 26/28% AMT bracket.** *(New, from `W4_amt_phaseouts.md`.)* The
    module reduces each statutory triple to a flat exemption-equivalent and
    prices the base at a single rate; the second AMT bracket is not represented.
    Wave 4 transcribed the exemption and the phase-out; the rate schedule is the
    remaining statutory element.
14. **The estate growth lever.** SOI-fitted **6.81%/yr** reproduces history and
    projects to figures no published estimate supports; the shipped **3.82%**
    (nominal GDP) projects sensibly and backcasts badly. Moves both estate LOO
    rows across −32% to +67%.
15. **The five-class decedent ladder has no within-group dispersion.** *(New,
    from `W4_gains_at_death.md` §8.4.)* After the carve-outs, gain per decedent is
    $9.71M / $1.89M / $0.92M / $79K across the classes, so the per-donor exclusion
    is a **step function** on a schedule with no spread: moving it $1M → $5M costs
    the model **$82.2B** of death channel where it costs Treasury **$33.4B**.
    That is the whole of why the two Green Book rows land on opposite sides of
    their targets, and it is the first place a later capital-gains lane should
    look. Related and smaller, from the same lane: the decedent **headcount** is
    unchanged and is the coarsest thing in the channel; the rate on the final
    return is priced on the class's *pre*-carve-out gain; the 72.3%
    active-business share is an **upper bound**; and the realizations base is
    still not projected across the window.
16. **CBO's account-level spendout rates** (pubs 61913, 62256) as an external
    cross-check on L2. Carried from Wave 1, still blocked by cbo.gov 403s.
17. **Give `TCJAExtensionPolicy` a microsim path.** *(New, from
    `W4_distributional_households.md` finding 1.)* Three of the four CBO
    distributional benchmarks are registered on `household` and scored on
    `tax_unit`, because `policy_to_microsim_reforms` returns an empty dict for
    every `TCJAExtensionPolicy` and for the corporate policy. Two of those three
    are also the **circular** rows. Building the path would move all three at
    once, and it is the only way to find out what those tables say when they are
    not reading CBO's own shares back.
18. **The ARP bundle's dollar *level* is about 40% high.** *(New, from
    `W4_distributional_households.md` finding 2.)* With the merge bug fixed the
    per-household averages read −$4,503 / −$4,211 / −$4,435 / −$3,404 / −$1,013
    against CBO's −$2,800 / −$3,150 / −$2,450 / −$1,620 / −$920 — the right order
    of magnitude everywhere and high in the middle. The benchmark scores *shares*,
    so nothing gates it; a level 40% high with shares within 3.7pp is a different
    kind of error from either one alone.

**Housekeeping with a data-file or gate consequence**

19. **The alternatives CSV's revenue sub-rows carry an extraction sign artifact.**
    Only the deficit rows are read, so nothing is wrong today; fixing it means
    re-running `scripts/extract_cbo_options.py`, which rewrites a pre-registered
    data file and needs its own commit pair.
20. **The four capital-gains `known_limitations` notes** in `preregistered.py`
    still describe the pre-Wave-2 mechanism, and the two step-up rows' notes now
    also predate Wave 4's carve-outs. Refreshing them touches no target, but it is
    a `preregistered.py` edit and no modelling lane may open that file.
21. **The derived microdata file grew 10.9%** (7,727,496 → 8,569,294 bytes)
    because `household_weight` repeats a nine-character float on every tax unit
    rather than once per household. Cosmetic, cheap, and the one thing PR #104's
    pre-registration got wrong.

**New after Wave 5**

22. **Sweep every module for an inverted or absolute-valued behavioural offset.**
    *(New, from `W5_payroll_margin.md` finding 3 and `W5_corporate_margin.md`
    finding 4; item 8 above is a fourth instance of the same family.)* **Three
    modules have now been found with the defect and none of them by a test.**
    `trade.py` (Wave 3, L8), `payroll.py` (W5-A) and `corporate.py` (W5-B), plus
    `tax_expenditures.py`'s reverse convention (W4-3a). The engine computes
    `deficit = −revenue + behavioural`, so an offset returned with the wrong sign
    — or wrapped in `abs()`, which `corporate.py` does — **magnifies** a score
    where it should erode it: a payroll tax increase raising 17.5% more than it
    levies, and the shipped `create_republican_corporate_cut` preset booking a
    first-year deficit effect of **+$159.75B** on a static −$142B. **This is
    invisible to every gate the repository has**, because each module's
    calibrated factories zero the elasticity, so the fitted tier and the
    leave-one-out column are structurally blind to the sign; only the
    uncalibrated Tier 1 shapes and the demo-grade bill-tracker auto-scorer reach
    it. Two were found by a lane that happened to be reading the file and one by
    a lane looking for something else — **the remaining ten modules have not been
    swept**. `corporate.py`'s bug is deliberately *kept* in `reported` mode and
    pinned by a test in both behaviours, because `trump_corporate_15`'s shipped
    number scores through it and Decision 1 forbids moving a shipped number in a
    lane that ships no caption for it. This is the wave's sharpest finding and
    should be the next item taken.
23. **The corporate module has no leave-one-out row.** *(New, from
    `W5_corporate_margin.md` finding 5.)* `run_loo.py` holds Payroll, Estate,
    AMT, Credits, Expenditures and CapitalGains. The one module whose base
    constant was **self-documented as calibrated** to its own benchmark — and
    which turned out to be a stale TY2018 vintage — has never been
    cross-validated, which is precisely the population `loo.py` exists to catch.
    Adding it is a `loo.py` edit and **no modelling lane may make one**, so the
    lane recorded it and stopped. Depends on nothing; blocked only on whose job
    it is.
24. **`treasury_capgains_39_plus_stepup_elim` is scored on the wrong window, and
    the projection is what makes that bite.** *(New, from
    `W5_preferential_margin.md` §8.3 finding 5.)* The target is the FY2022 Green
    Book's FY2022–2031 row on a 2021 baseline; the manifest states no
    `effective_start_year`, so the model scores FY2025–2034. Running the same
    channel on the target's own window returns **$405.6B against $461.5B** —
    about **17 of the row's 43 points**. That is a *manifest* question, not a
    modelling one: moving it is a shape input under the supersede rule (a new
    `.v2` row, never an edit), and the repository has no 2021 vintage either way.
    Related and smaller from the same lane: no receipts lag on the enactment
    year, no smoothing of the TY2023 SOI anchor (a trough), the $1M threshold
    still un-indexed, and the growth rate is a net-worth CAGR rather than CBO's
    own published realizations projection (blocked by cbo.gov 403s, item 16).
25. **The AGI-surtax filing-status threshold row is now the tier's
    second-largest, at 44.7%, and nothing in Wave 5 touched it.** A $20,000
    single / $40,000 joint boundary applied as one floor to every return, at the
    bottom of the filing population where a single-threshold approximation is
    worst — joint filers between $20,000 and $40,000 are taxed in the model and
    exempt in JCT's estimate, and the model *still* under-predicts, because SOI
    aggregate AGI above the floor understates JCT's base. Together with
    `cbo_opt45_top4_brackets_2pp` at 17.9% this is **62.6 units, 15.2% of the
    tier**. Closing it needs SOI by filing status, which is why §2.1 scoped it
    "medium, not in scope below"; it has now outlasted five waves.
26. **Payroll's two flat-share "elasticities" and its unexplained base-growth
    gap.** *(New, from `W5_payroll_margin.md` findings 4 and 5.)*
    `labor_supply_elasticity = 0.1` and `tax_avoidance_elasticity = 0.15`
    multiply `|static|` rather than a net-of-tax share, so a 0.1pp tax and a 10pp
    tax erode by the same 17.5%; both are unsourced and both are left in place
    for the OASDI branches, where every factory zeroes them. Separately,
    two-thirds of what is left of the Option 61 residual is a base-growth gap the
    option text does not explain — the model prices the base off CBO's own
    February 2024 wage path at 3.9%/yr while the base implied by CBO's published
    revenue row grows **3.45%/yr** — and a third is FY2025 alone, where CBO's
    first-year row is 0.48 of its second-year row against the 0.75 a January
    effective date and a fiscal year give. **Neither is closable from the
    published record that lane could reach.**
27. **The engine has two year-indexed policy classes and no general concept.**
    *(New, from `W5_payroll_margin.md` finding 6.)* `TaxExpenditurePolicy` opted
    out of `_score_growth_tax_policy_year` in Wave 4 (a cap's bite is a function
    of the year) and `PayrollTaxPolicy` in Wave 5 (the base is a path), each as
    six lines of `isinstance` in the scoring engine. A third will make it a
    pattern worth naming — `Policy.scores_by_year()`, say — rather than a third
    special case.
28. **Two classroom locks the frozen-link work deliberately did not build.**
    *(New, from PR #111.)* **Build packages are not freezable**: `frozen=1` is
    honoured on `/explore` and `/tailor` only, the two surfaces producing one
    `ScoredResult`, and freezing a package would mean disabling the checklist
    inside `ui/tabs/deficit_target.py`, which also owns the target slider and the
    exports — so `frozen=1` on `/build` does nothing rather than claiming a lock
    it is not holding. And the **Data & methodology options are not pinned**, per
    the owner's stated scope (vintage, engine, dynamic, policy); they still move
    the number, which is what the spec-hash caption is for. Blue tier, so held to
    a UX bar rather than an accuracy one.
29. **The cold-start measurement in `planning/redesign/FOLLOWUPS.md` is still
    open.** Carried, and still marked partially done rather than ticked: PR #82
    shipped option (a), painting the chrome before any data load, and what
    remains is Streamlit Cloud's container sleep, which needs either (b) a warm
    container or (c) an explanation in the copy around the link. **The
    measurement that decides between them has not been made**, and nothing in
    Waves 4 or 5 made it — if most of the remaining wait is import time there is
    more of (a) to do; if it is cold container scheduling, only (b) helps. It is
    the one open blue-tier item that is a measurement rather than a build.
