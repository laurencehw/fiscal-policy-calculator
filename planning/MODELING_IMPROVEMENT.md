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

## 5.6 The sign sweep and the corporate follow-through (2026-09-05, PRs #119-#122)

Four PRs, and only two of them touch a model: a **cross-cutting sweep** of the
behavioural-offset sign contract (`model/offset-sign-sweep`, PR #119), a
**research memo** on the published per-point corporate yields with no code
change (`memo/corporate-per-point-yield`, PR #120), a **modelling lane** that
projects the corporate base off the scored vintage (`model/w6-corporate-base-projection`,
PR #121), and a **provenance pass** on the corporate and PTC targets
(`provenance/corporate-ptc-targets`, PR #122). Like Waves 4 and 5, none of this
is in §5's sequencing: it is §6.2's carry-over items 22 and 23 taken with the two
follow-ups they generated. Each lane pre-registered in `planning/lanes/` (or, for
#120, recommended in `planning/memos/`) before touching code and appended an
outturn; those files are the record and this is the summary. **Every figure here
is from `scripts/cold_holdout.py`, `scripts/run_loo.py --donor-matrix`,
`scripts/run_validation_dashboard.py` and `compute_scorecard()` on the merged
tree**, which is not any single lane's before/after — #119 and #122 both moved
`trump_corporate_15`, in opposite directions and for different reasons.

### The tiers, before → after

| tier | n | before (Wave 5) | after (merged) |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 26 | 15.9% mean / 11.4% median / 16 within 15 / 22 within 25 | **15.2% / 11.4% / 16 / 22** |
| Calibrated reference (fitted) | 23 → **21** | 1.6% / 0.1% median / 23 within 15 | **1.7% / 0.1% / 21 within 21** |
| Unfitted reconstructions | 31 → **34** | 56.6% / 29.9% median / 9 within 15 | **57.6% / 34.2% / 9 within 34** |
| Leave-one-out | 18 derivable | 29.6% / 19.1% median / 8 within 15 | **byte-identical output**, on all four branches |
| Distributional | 7 | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 80 → **81** | 73 published | **81 / 75 published** (calibrated 55 / 49) |
| `revised_target_entries` | 15 | — | **16** |
| Calibrated provenance | 30 / 5 / 12 / 7 / 0 | — | **30 / 7 / 12 / 6 / 0** |
| `EXAMINED_NOT_REVISED` | 5 | — | **6** |
| Tier 1 CI gate | — | `20 / 21` | **`20 / 21`**, re-derives to itself |
| Tests | — | 3415 passed, 1 skipped | **3518 passed, 7 skipped** |

**Both calibrated tiers changed population and neither changed accuracy, so the
constant-population readings are not optional here.** The fitted tier's
1.6% → 1.7% is *two rows leaving*, and held in place it reads **23 at 7.7%,
21/23 within 15%** (28 at 8.0% with Wave 4's five held in too; 29 at 10.0% with
the TCJA-AMT row on top). The reconstruction tier's 56.6% → 57.6% is the same two
rows arriving plus one new benchmark: on the **33 rows it held before #122** it
reads **57.4% / 29.9%**, and on the **31 it held before #119** it reads
**56.6% / 29.9%** — *exactly* what it read after Wave 5. So the whole of the
56.6% → 57.4% step is `trump_corporate_15` going 22.3% → **121.6%**, and the
remaining 0.2pp is `biden_corporate_28_fy2022` arriving at 62.9%.

**Tier 1's error mass fell 412.9 → 395.1, and one row is all of it.** Corporate
went 62.3 → **44.5** (15.1% → 11.3% of the tier) and every other row is identical
to the decimal. Grouped by cause the tier is now capital gains 104.5 (26.4%), the
bracket-aggregate ceiling 91.4 (23.1%), budget-authority spend-out and level shape
63.4 (16.0%), the filing-status threshold 62.6 (15.8%), module revenue identities
at the margin 60.1 (15.2%) and the one tax-expenditure cap 13.1 (3.3%). **The tail
re-ordered**: `cbo_opt46_agi_surtax_1pp_20k` at **44.7%** is now the tier's largest
single row, by two-tenths of a point over `cbo_opt64_corporate_rate_1pp` at
**44.5%**, then `treasury_capgains_39_plus_stepup_elim` at 43.3% and
`biden_capital_gains_39` at 31.4%. The AGI-surtax row has not moved through six
waves; it became the largest because corporate fell past it.

### Per-lane, what moved

**PR #119 — the offset-sign sweep (item 22, subsuming item 8).**
`scoring_engine.py` books `deficit_after_behavioral = static_deficit + behavioral`
on the **static revenue** effect, so a same-signed offset erodes and an
opposite-signed one magnifies. Probed twice — at the function (`f(+100)`,
`f(−100)`) and at the score (an increase and a cut of equal size through the
engine) — **7 of 15 implementations were against the contract**:

| tag | classes | size of the error |
|---|---|---|
| `inverted` (3) | `AMTPolicy`, `EstateTaxPolicy`, `PremiumTaxCreditPolicy` | AMT booked **25% more** than its own static in *both* directions; PTC 13% on a repeal, 3% on an extension |
| `abs` (4) | `CorporateTaxPolicy` [`reported`], `TaxCreditPolicy` [fallback], `IRSEnforcementPolicy`, `InternationalTaxPolicy` | corporate 12.5% more on a **cut**, international 15%, credits 3% |

The three inverted modules carry the *identical* comment pair
`# Reduces revenue gain` / `# Reduces revenue loss` above a `return -total_offset`
— one copy-paste in three files, by an author who read `behavioral` as a
quantity the engine subtracts. Six were fixed with `math.copysign`;
`TaxExpenditurePolicy` is kept as a **sourced convention**, cited to CBO 60557
Option 56, whose text has both channels raising revenue. Two shipped presets
moved with a Decision 6 caption: **Trump Corporate 15% +$1,690.6B →
+$1,314.9B** and **Repeal ACA Premium Credits −$966.2B → −$790.5B**; the other 51
score to the cent, and both moved presets' badges dropped (Excellent → Poor,
Excellent → Acceptable). Strict readiness then failed on CI, and the owner chose
**reclassify, don't retune, don't exempt**: `trump_corporate_15` and `repeal_ptc`
became `calibrated_to_target=False` (fitted 23 → 21, reconstructions 31 → 33).

**PR #120 — the corporate memo.** No code. 18 published corporate-rate estimates
across 10 vintages, transcribed with page references and annual paths to
`fiscal_model/data_files/validation/corporate_rate_scores.csv`, printed by
`scripts/corporate_yield_reconciliation.py`. Three claims in `cbo_opt64`'s
`known_limitations` refuted: the split is **JCT vs Treasury OTA**, not CBO vs
Treasury; Treasury's 28% row has bundled a **GILTI step** since FY2023, so it is
not rate-only; and per-point dollars are not comparable across rate levels or
scopes — on the implied marginal base the record is Tax Foundation 55.1%, JCT
55.9%, PWBM 64.4%, Treasury 79.5% and **this model 90.8%**. Nothing supports a
yield rising with the step (JCT's 14-point cut from 35% and its 1-point increase
from 21% imply marginal bases of $963.2B and $963.0B). And **Option 64 carries no
income-and-payroll offset footnote though the facing Option 63 does**, which
refutes the old "largest unmodelled channel" claim outright.

**PR #121 — the corporate base projection (memo §7(i), lane C).** Base =
CBO's February 2024 corporate receipts path (pub. 59710 Table 1-1) ×
**4.80133** base-$/receipts-$, anchored on SOI TY2022 ÷ MTS FY2022, with a §6655
convolution for the fiscal-year phase. `cbo_opt64` **62.3% → 44.5%** against a
registered band of 42 ± 4; **Tier 1 15.9% → 15.2%**, only that row moving;
derived `biden_corporate_28` **−7.81% → +4.04%**, crossing its target in the
direction a rate-only shape scored against a rate-plus-GILTI row should. The
window-average marginal share fell **90.8% → 80.8%**, closing an inconsistency
that is independent of any target: the old flat 4%/yr aging grew the base 3.4×
faster than the receipts it is a share of, so by FY2033 it priced a point against
*more* base than the baseline implies exists. **Every registered figure landed,
including a ten-row year-by-year build the engine reproduced to the third
decimal** — which the lane reads as algebra rather than prescience, because the
mechanism is linear; what was being registered was the *choice*.

**PR #122 — the corporate/PTC provenance pass.** Neither `corporate.py` nor
`ptc.py` was opened and no `model_10yr_billions` moved. `biden_corporate_28` →
`line_item_differs` through the new **`scope_differs`** kind (see finding 2);
`biden_corporate_28_fy2022` registered at **−62.9%**, `calibrated_to_target=False`
and never to be fitted; `cbo_opt64`'s estimator corrected CBO → **JCT** and its
`known_limitations` rewritten (with the §174 anchor inflation **sized** at 11.1%,
an upper bound that takes the row to ~46%, not to CBO); `trump_corporate_15`
superseded to the published range **[+$595.0B, +$673.1B]** with Tax Foundation's
as anchor, 22.3% → **121.6%**, model **$818.7B outside** the range; and
`repeal_ptc` **examined and left**, its origin identified as CBO/JCT pub. 51298
Table 2's **$1,142B** — 3.8% from the carried figure and a *baseline projection
in a repeal-score column*.

### Four findings

**1. A defect that every gate is structurally blind to is not rare — it was in
seven of fifteen modules.** Item 22's own claim was that the sign error is
invisible to every gate the repository has, because each module's calibrated
factories zero the elasticity. Measured, that is exactly right: of the seven, **one**
reached a scorecard row. The rest were reachable only through the app's Tailor and
composer paths, `bill_tracker/auto_scorer.py`'s raw constructions, and two shipped
presets. The gate that now exists is not the parametrised sign test but
`test_every_offset_implementation_is_covered`, which greps the package for
`def estimate_behavioral_offset` and fails if a class is missing from the case
list — because "a module nobody swept" is how all four previously-found instances
got in. It was verified to *fail* rather than assumed to work, and **its first
draft did not catch `enforcement.py`**, because probing only the direction a
module's own constructor can reach lets a clamped module through
(`IRSEnforcementPolicy` returns a static of exactly 0.0 for a funding cut). A
clamp is not a contract, which is why the sign must be probed at the function and
not only at the score.

**2. A provenance label can be right about the number and wrong about the
reform, and the taxonomy had no word for it.** `biden_corporate_28`'s carried
−$1,347.0B is Treasury's printed $1,349,941M rounded — they agree to **0.2%**,
inside `CONFIRMATION_TOLERANCE_PCT` — while the row's own chapter has moved the
GILTI effective rate with the statutory rate since the FY2023 edition and the
factory scored against it sets `gilti_rate_change=0.0`. `line_item` would have
asserted an agreement the documents do not support; `line_item_differs` would
have been rejected by its own test. So `BenchmarkSource` gained **`scope_differs`**
and the invariant became: a `line_item_differs` row carries a figure gap wider
than the tolerance **or** a filled `scope_differs`, never neither, so the label
can never mean "something is wrong here, unspecified". `__post_init__` rejects
`scope_differs` on any other provenance and the test asserts both branches are
live. **The target did not move**, because the GILTI leg's size is never printed
and is not recoverable by differencing editions.

**3. "Identical to main" is only evidence when the check being compared can
distinguish them.** PR #119 passed `check_readiness.py --strict` locally and
failed it on CI. The local run exits 2 on *both* trees, because Python 3.14 fails
the runtime check first and masks everything after it; a byte diff of the output
therefore showed nothing, while on CI's 3.12 `main` passed and the branch did not,
because `trump_corporate_15` had become a Poor row still declared fitted. The
direct query settles it —
`strict_readiness_issues(build_readiness_report())` returned
`[('runtime', None), ('revenue_scorecard', ['trump_corporate_15'])]` before the
reclassification and `[('runtime', None)]` after — and a test now asserts that,
so the next lane does not have to know to run it. This generalises past the sign
sweep: a gate that is already failing for an unrelated reason is not a control.

**4. The statistic that decides an app default can be decided by a row that
measures nothing about the world — and fixing that reversed it twice.** Decision
1 says a module stays on `reported` until its `derived` error is below its
fitted error. Before the sweep, corporate read reported **1.92%** against derived
9.67%. Signing the reported offset took reported to **13.02%** against derived's
unmoved 9.67% — a reversal produced entirely by `trump_corporate_15`, whose
target was provenance `model_estimate`, i.e. the model's own output. PR #121 then
moved derived to 11.78%, still ahead. PR #122 re-measured on **three published**
targets and got **62.75% reported against 76.48% derived** — reported ahead
again, on documents this time. And the merge of the two lanes, which is the only
tree where both apply, gives **reported 62.75% against derived 61.43%**: derived
leads, narrowly, by winning the FY2022 rate-only row and losing a little on the
other two. **`CORPORATE_APP_MODE` is unchanged on `main` at `reported`** — the flip,
PR #124, was closed unmerged by owner decision (§6.2 item 33) — and the lesson is the one PR #121's
own finding 4 states: carry the per-row table beside the mean, never instead of
it, because a mean over three rows can be decided by whichever of them has the
weakest target.

### Where the pre-registrations were wrong

**PR #119, falsification 2 fired.** §5.2 said "PTC — `create_extend_enhanced_ptc`
and `create_repeal_ptc` zero the elasticities". True of the first factory and
**false of the second**: `create_repeal_ptc` sets `coverage_elasticity=0.0` under
the comment *"Not modeling coverage offset"* and never touches
`adverse_selection_factor`, which keeps its dataclass default of 0.1. So the
module's *other* channel was live on a shipped preset and a fitted benchmark the
whole time, and the pre-registration had been written from the factory's comment
rather than from its argument list. **The lesson generalises**: "the factory
zeroes the elasticity" is a claim about *every* elasticity the module has, and a
module with two of them can zero one. Falsification 4 also fired, harmlessly —
`TaxCreditPolicy` was predicted `asymmetric` and the audit gives its two branches
a row each, `correct` and `abs`, because the branch is a property of the
`credit_type` and not of the call.

**PR #121: none of eight fired**, and every registered figure landed to the
decimal. That is not prescience — the mechanism is linear — but two of its
findings were not registered and are worth more than the row: the
`CBOBaseline` corporate path defect (finding 1 below), and the fact that the
§6655 phase factor is **above 1.0** in FY2026 and FY2027 (1.00137, 1.00377)
because CBO's projected receipts *fall* in those years, so a fiscal year
collecting a quarter of the previous, larger tax year collects more than its own.
Every other phase factor in the repository is a fraction and a reviewer's instinct
will be that this is a bug; it is pinned by a test that asserts both signs.

**PR #122's §7 table is stale on its own branch and correct on it.** It records
Decision 1's corporate comparison as 62.75% reported against **76.48%** derived,
which was right before the merge with #121; on merged main derived is **61.43%**,
which is what the test pins and what this section quotes.

### What this round did not do

- **No lane touched** `preregistered.py`, `holdout.py`, `loo.py`, any CI
  threshold, `tests/test_cold_holdout.py`'s anti-leakage invariant, or
  `.github/workflows/`. PR #122 explicitly left `preregistered.py` alone: its
  `source_name` field records the *publisher*, CBO did publish Option 64, and the
  manifest is append-only.
- **No constant was retuned anywhere**, including the two whose rows the sweep
  moved by ~20%. Putting them back would have re-fitted the level to the defect.
- **`CORPORATE_APP_MODE` was not flipped** by either corporate PR, so no shipped
  corporate number moved on either. The two presets that moved did so in #119,
  from the sign fix, and shipped with their caption.
- **A `retire` state for `target_revisions.py` was deliberately not built.** The
  brief allowed for one if no published 15% score existed; two do. A mechanism
  with no user is dead code, `EXAMINED_NOT_REVISED` already covers "opened and
  left", and what the ledger still lacks is a way to say "this target should not
  exist and nothing replaces it" — which nothing in the repository needs today.
  Recorded so the next lane does not re-derive the question.
- **Nothing was done about *why* the corporate rows miss.** `biden_corporate_28`
  at 3.7% is a fitted row measuring a scope mismatch; `biden_corporate_28_fy2022`
  at 62.9% is a fixed base failing to track a vintage; `trump_corporate_15` at
  121.6% is that plus a bundled provision plus a direction asymmetry. The
  remaining 44 points of `cbo_opt64` are credit carryforwards under §38(c) and
  §904(c), CAMT (which begins in TY2023, after the last SOI year on file) and the
  individual-side dividend interaction — each needs a quantity no source this
  module reads publishes, and each would otherwise arrive as a constant that
  landed on CBO by construction. **A lane that asserts a share instead of deriving
  one has failed even if the row lands.**

## 5.7 Wave 7 outturn (2026-09-06, PRs #126-#132)

Seven PRs, and only five of them touch a model: a **target-window memo with its
own minimal implementation** (`memo/fy2022-target-window`, PR #126), a
**modelling lane** giving the generic income-tax path a filing-status dimension
(`model/w7-filing-status-split`, PR #127), a **convention lane** settling the
expenditure offset direction on nine sources
(`model/w7-expenditure-offset-convention`, PR #128), a **measurement lane** on
cold start (`perf/cold-start-measurement`, PR #129, 🔵), a **green-tier fix** to
the baseline's corporate receipts line plus the dashboard's blind spot
(`fix/baseline-corporate-path-and-dashboard-means`, PR #130), a **modelling
lane** replacing `repeal_ptc`'s shape (`model/w7-ptc-repeal-shape`, PR #131), and
a **modelling lane** replacing the decedent ladder (`model/w7-decedent-ladder`,
PR #132). Three blue-tier PRs shipped alongside (#133 Plotly dark mode, #134
Build frozen links, #135 the footer scorecard) and are summarised at the end.

Like Waves 4-6 this is not §5's sequencing: it is §6.2's carry-over items 8, 15,
24, 25, 30 and 31 taken together. Each lane pre-registered in `planning/lanes/`
(or, for #126 and #129, in `planning/memos/`) before touching code and appended
an outturn; those files are the record and this is the summary. **Every figure
here is from `scripts/cold_holdout.py`, `scripts/run_loo.py --donor-matrix`,
`scripts/run_validation_dashboard.py` and `compute_scorecard()` on the merged
tree**, which is emphatically not any single lane's before/after — **#126 and
#132 move the same Treasury row in opposite directions**, so the lane docs' three
Tier 1 figures (14.1%, 15.9%, 15.4%) are each correct on their own branch and
none of them is 15.0%.

### The tiers, before → after

| tier | n | before (post-#122) | after (merged) |
|---|--:|---|---|
| Out-of-sample (Tier 1) | 26 | 15.2% mean / 11.4% median / 16 within 15 / 22 within 25 | **15.0% / 10.6% / 17 / 22** |
| Calibrated reference (fitted) | 21 | 1.7% / 0.0% median / 21 within 21 | **1.7% / 0.0% / 21 within 21** — 1.733% → 1.724%, one row |
| Unfitted reconstructions | 34 | 57.6% / 34.2% median / 9 within 15 / 13 within 25 | **57.9% / 34.2% / 9 / 12** |
| Leave-one-out | 18 derivable | 29.6% / 19.1% median / 8 within 15 | **30.1% / 19.1% / 8** |
| Distributional | 7 | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 81 | 75 published (calibrated 55 / 49) | **unchanged** |
| `revised_target_entries` | 16 | — | **16** |
| Calibrated provenance | 30 / 7 / 12 / 6 / 0 | — | **unchanged** |
| `EXAMINED_NOT_REVISED` | 6 | — | **6** |
| Tier 1 CI gate | `20 / 21` | — | **`20 / 21`**, re-derives to itself |
| Tests | 3518 passed, 7 skipped | — | **3722 passed, 8 skipped** |

**Neither calibrated tier changed population, which makes this the first round in
several where the constant-population reading *is* the headline reading.** The
fitted tier held the same 21 rows and moved 1.733% → 1.724% on
`eliminate_mortgage` alone. The reconstruction tier held the same 34 rows and
moved **57.6% → 57.9%**, all of it `repeal_ptc` going 18.5% → **29.6%** — so for
once the movement is accuracy, and it is a regression. The leave-one-out suite
moved **29.6% → 30.1%** on `Expenditures` 35.7% → **37.5%**, also a registered
regression, and **no donor-matrix entry moved**. Read alongside the previous
round, the pattern is worth naming: PRs #119-#122 moved two tiers on composition
and none on accuracy; Wave 7 moved two on accuracy and none on composition.

**PR #130 also made one of those readings computable rather than asserted.**
`run_validation_dashboard.py` had printed Tier 1 and leave-one-out and *nothing*
about the 55 calibrated rows in between — which is why PR #119 could move both
calibrated tiers and leave the dashboard byte-identical. It now prints a
calibrated block, sourced from `cold_holdout.build_report()` with a test pinning
the two reports together, plus twelve reconstruction sub-populations. The
"held in place" line needed a new field, `declared_calibrated_to_target`, **and
the natural guess is wrong by a factor of three**: folding all 16
`revised_target_entries` rows back into the fitted tier reads **37 at 15.5%**,
but 10 of those are sectoral rows no runner ever declared fitted, so the honest
reading is **27 at 5.6%, 25/27 within 15%**.

**Tier 1's error mass fell 395.1 → 390.7, and the composition of that fall is the
wave.** Scoring the FY2022 row on its own decade returned 24.9 points; the
filing-status split cost 18.1; the decedent distribution cost 2.4. Grouped by
cause the tier is now **the two AGI surtaxes 87.2 (22.3%)**, the bracket-aggregate
ceiling 84.9 (21.7%), capital gains 82.0 (21.0%), budget-authority spend-out and
level shape 63.4 (16.2%), module revenue identities at the margin 60.1 (15.4%)
and the one tax-expenditure cap 13.1 (3.4%). **Two things changed about that
list.** Capital gains is **no longer the largest group**, for the first time in
the plan's history. And the cause "one threshold standing in for a filing-status
pair" is **gone as a cause**, because PR #127 built the mechanism — what is left
on the two Option 46 rows is a base definition and a base growth rate, which is a
different question and gets its own entry.

**The tail re-ordered again**: `cbo_opt46_agi_surtax_1pp_20k` **49.8%**,
`cbo_opt64_corporate_rate_1pp` **44.5%**, `cbo_opt46_agi_surtax_2pp_100k`
**37.4%**, `biden_capital_gains_39` **32.8%**, `cbo_opt45_all_rates_1pp` 22.4%,
`cbo_opt51_gains_at_death` 20.3%, `warren_ultramillionaire_surtax_3pp` 19.0%,
`treasury_capgains_39_plus_stepup_elim.v2` 18.4%.

### Per-lane, what moved

**PR #126 — the FY2022 target window (item 24).** `treasury_capgains_39_plus_stepup_elim`
carries the FY2022 Green Book's combined row at −$322,485M over **FY2022–2031**
(report p. 105 / PDF p. 111), and Tier 1's default window is FY2025–2034. Both of
this shape's channels grow at one constant — `household_net_worth_growth_rate =
0.0580148` — so a window three years later scores mechanically higher.
`CBOScore.scoring_window_first_year` now lets a case be scored on its own decade,
and `_resolve_window_start` in `validation/core.py` moves **the scorer's window
and the policy's start together** (moving only the window truncates the head:
Warren would read −$170.1B, exactly 6/10 of itself). `.v1` superseded, `.v2`
registered at the **same** −$322.0B, entry commit before scoring commit — IIJA
`.v2`'s rule exactly. On its own window the row scores −$369.0B, **14.6%** on
that branch and **18.4%** on merged main, because #132's decedent distribution
raised its death channel from $102.45B to $109.24B.

**PR #127 — the filing-status split (item 25).** `TaxPolicy.affected_income_threshold`
was a scalar and `IRSSOIData` read only Table 1.1, which has no filing-status
dimension, so one status's floor was applied to all four populations — at Option
46 alternative 1 taxing 46.1M joint returns from $20,000 where JCT starts them at
$40,000, **$839.8B of base, 9.2% of the whole**.
`scripts/build_filing_status_data.py` transcribes SOI **Table 1.2**;
`get_bracket_distribution_by_status` takes only its **composition**, so a uniform
threshold reproduces the pooled path to the cent.
`TaxPolicy.threshold_by_filing_status` is a **partial** mapping, and
`FILING_STATUS_THRESHOLD_RULE` says how a source naming two statuses is read for
the other two. `opt46_1pp` 44.7% → **49.8%**, `opt46_2pp` 16.1% → **37.4%**,
`opt45_top4` 17.9% → **12.4%**, `biden_high_income` 12.0% → **9.2%** — every
figure landing exactly on §3's hand-computed prediction, including the mean
rising.

**PR #128 — the expenditure offset convention (item 8).** The module magnified
for every expenditure, every reform and both signs of static, and **no document
supports a rule at that grain**: CBO's Option 49 gives four alternatives over the
same deductions three different behavioural directions, and its charitable option
reverses its verdict for a floor design. `TaxExpenditurePolicy` now carries a
per-reform `direction` with the source sentence attached — **magnify** for Option
56, the 28% charitable ceiling, SALT elimination and SALT-cap repeal; **erode**
for mortgage (Poterba & Sinai's own 85%), step-up, retirement and like-kind.
`eliminate_mortgage` −$330.4B → **−$270.3B**, 10.1% → **9.9%**; **zero presets
moved** and no constant was retuned. `CONVENTION_EXCEPTIONS` is now a set of
**policies** rather than class names, and a new test fails if any class is ever
wholly exempted again. A **sixth** sign defect was found downstream in
`estimate_expenditure_revenue()`, which aggregates in revenue space and was
adding a deficit-space offset.

**PR #130 — the baseline's corporate receipts line (item 30).**
`_load_from_data_sources` set `base_corporate_tax = base_individual_income_tax ×
0.18` and `_project_corporate_tax` grew it at **4.88%/yr** against CBO's own
**1.21%**, neither term taking a vintage — so under `use_real_data=True` all
three vintages started from **$386.62B to the cent** while `use_real_data=False`
returned three different figures, the mode named "real data" being the one with
no vintage in it. February 2024 now **is** publication 59710 Table 1-1, read
through `fiscal_model.corporate`'s own loader; the other two keep the
reconstruction from their own base year; `CORPORATE_RECEIPTS_SOURCING` grades all
three. **Nothing scored moved** — 26 out-of-sample rows, both calibrated tiers,
81 scorecard entries, the donor matrix, 53 presets × 2 modes × static/dynamic and
16 Tailor combinations all byte-identical. Ask's ten-year deficit went
**$30,020.7B → $29,529.1B** and debt/GDP **104.8% → 103.8%**; no Decision 6
caption, argued in advance in §4.3 with the falsification that would have
overturned it.

**PR #131 — the PTC repeal shape (item 31).** `create_repeal_ptc`'s $83.0B/yr is
`1100 / (1.10 × Σ 1.04ᵗ)` — the carried target run backwards through the engine's
growth factor and the offset PR #119 corrected. The static path is now CBO/JCT
publication 51298 Table 2's own annual credit cost (both legs, two vintages
transcribed, February 2026 the default, an untranscribed vintage **raising**
rather than falling back) times (1 − **19.28%**) of offsetting effects from
publication 60437's own itemisation. `repeal_ptc` −$896.9B → **−$774.1B**,
18.5% → **29.6%**. The **Repeal ACA Premium Credits** preset moved with a
Decision 6 caption computed from the scored result; the other 52 score to the
cent.

**PR #132 — the decedent ladder (item 15).** Five point masses, each reading
three published carve-out step functions at that class's *mean* estate, became a
**piecewise-Pareto size distribution of net worth at death** fitted to the
Distributional Financial Accounts' own percentile-group aggregates — every
group's aggregate reproduced to 1e-9, the level untouched at Poterba &
Weisbenner's flow, only the shape changed, with the published wealth breakpoints
of all three ladders forced in as quadrature edges (32× more slices moves the
channel 0.009%). **Seven of eighteen published rows had never been evaluated**,
including the whole $1M–$5M band both Green Book exclusions sit in; six are now
alive. `cbo_opt51_gains_at_death` 19.3% → **20.3%**, `biden_capital_gains_39`
31.4% → **32.8%**, the Treasury row 43.3% → 45.4% on that branch — all inside
their pre-registered bands, all registered as regressions. Two shipped Tailor
figures moved by 2.6% and 1.2%, and the caption shipped anyway.

### Five findings the wave produced

**1. A cancelled error looks like a fit until you remove one of its terms — and
this is now the third time.** `cbo_opt46_agi_surtax_2pp_100k` read **16.1%**, the
healthiest of the four rows the split touched, and it was two errors cancelling a
third. Adding the per-status floors alone gives 37.4%; an AGI base, which is what
CBO's own text specifies, 21.6%; a base grown at CBO's own nominal GDP rather
than frozen at TY2023, **1.0%**. The 1pp row runs 44.7% → 49.8% → 29.4% →
**9.1%**. After the Fiscal Responsibility Act's spend-out (Wave 1) and the
Treasury row's 0.2% (Wave 4), the rule is explicit: **a necessary mechanism is
not therefore sufficient, and a row that worsens when you add one term may have
been carrying two.**

**2. The dispersion hypothesis was testable, was tested, and was wrong.** Item 15
diagnosed the $1M → $5M exclusion step ($82.2B of model death channel against
$33.4B between Treasury's two rows) as the ladder having no within-group
dispersion. Replacing the ladder made the step **bigger, 85.02**, and the
direction is not an accident: `max(0, gain − E)` is convex, so a mean-preserving
spread *raises* the taxable excess — **a sharper schedule makes an exclusion cost
more.** The lever is the **decedent headcount**: `estate_flow_rate` is Poterba &
Weisbenner's *dollar* flow used as a *headcount* rate, giving 408,532 decedents
against roughly 3.09 million NCHS deaths, and about twice the shipped count
reproduces Treasury's step to within two billion. The module already carries an
unused `mortality_weighted_net_worth_share` of 2.65%. And **$33.4B was never the
right comparator**, since the two Treasury rows sit on different windows.

**3. A window is not a vintage, and both FY2022 rows' notes named the wrong
blocker.** Neither reads a baseline *level* —
`CapitalGainsPolicy.estimate_static_revenue_effect` opens with
`_ = baseline_revenue` — so what they needed was a **window**, and a vintage
would have cost an enum member, an assumptions block, base levels, the app's
vintage picker, the `baseline=` share-link contract and the classroom
frozen-link refusal path while moving neither row. The offset itself had been
mis-measured for two waves: **28.7 of 43.3 points, not the ~17 the repository
quoted**, because that figure discounted only the rate channel and the death
channel grows too, non-proportionally (a uniform discount gives $86.5B; the
re-score $65.8B). **The window offset and the ladder finding are the same defect
seen twice.** The same mechanism takes IIJA 18.2% → **0.3%**; #126 publishes the
number and declines to take it, because a lane may not take a second target
decision by implication.

**4. The expenditure module's six fitted constants disagree about whether the
convention exists.** Reconstructing each annual against its own growth rate,
three were fitted so the **static** path hits the target
(`eliminate_mortgage`, `repeal_salt_cap`, `eliminate_salt`) and three so the
**magnified** score does. On the three static-fitted rows the convention was
carried as pure error — 10.1%, 5.0%, 5.1% — while the two magnified-fitted rows
absorbed it. That is why this module's fitted rows were never uniformly near zero
the way the rest of the tier's are, and it is worth knowing before anyone reads
one of its 0.1% rows as agreement. A related lesson from the sixth sign defect:
**a sign contract enforced at the two ends of a pipeline says nothing about the
middle of it** — `estimate_expenditure_revenue()` sits between
`estimate_behavioral_offset` and the engine, where neither looks, and the test
covering it asserted a tautology that passes under either sign.

**5. A cheap count of a registry cannot be exact, and the reason generalises.**
`published_entries` is `len(entries) − model_estimate − unclassified`, and
`entries` is **not** a registry property: a runner appends a row only if its
validator *returns* one, `validate_all_capital_gains` swallows exceptions per
scenario and `core.validate_all` drops a falsy result. So a registry count would
over-report by exactly the number of benchmarks currently failing to score — the
state in which an accurate count matters most. **The only way to know how many
rows the scorecard has is to build the scorecard**, which is why PR #135 pins a
generated artifact and a test recomputes it, rather than counting the registry.

### Where the pre-registrations were wrong

**Almost nowhere, and the two misses are both decimals.** #127's §3 predicted the
median at 10.7%, hand-computed from rounded per-row errors; the runner reports
**10.6%**, the median of unrounded values. #130 predicted end-of-window debt/GDP
at 103.9% and got **103.8%**, because the prediction rounded end-of-window GDP
back out of the published ratio instead of reading it. Everything else landed:
#127's four rows and its whole tier line to the decimal, #131's −$774.1B /
29.62% to the cent, and all twelve of #132's bands including the exclusion step
at 85.02 against a predicted "about 85.0".

**Two corrections to earlier records were made in passing, and both narrow a
claim rather than reverse it.** `W6_corporate_base_projection.md` finding 1 said
the corporate path was "identical for all three vintages"; the three shared one
base level and one first year and then diverged **0.70%** by FY2035, because the
growth rule reads the vintage's assumptions even though the level does not —
stating it precisely put the cause in one line of the loader. And #131 corrected
PR #122's handoff, which read "what the module computes *is* a baseline cost":
half right, since what it computed was a **fitted** annual that happened to total
within 3.9% of one.

### What Wave 7 did not do

- **No target moved.** `preregistered.py`'s targets, `target_revisions.py`,
  `KNOWN_SCORES`, `CBO_SCORE_MAP` and every CI threshold are untouched;
  `revised_target_entries` is still 16 and `EXAMINED_NOT_REVISED` still 6. What
  moved on one row is a *shape input*, through the manifest's supersede rule.
- **No constant was retuned to chase a moved row.** `eliminate_mortgage` stays
  Acceptable, so `scenarios.py` was never opened, and the expenditure module's
  three static-fitted constants were deliberately left as they are.
- **No elasticity magnitude was adopted from a source read for its direction.**
  Poterba & Sinai's own 15% sits beside mortgage's 0.10 and was not taken.
- **The decedent headcount was not touched**, though the measurement of what
  touching it would do is the hand-off.
- **IIJA's `.v3` was not taken**, and the number it would produce is published.
- **`fiscal_model/data/` is still invisible to the lint gate.** `.gitignore`'s
  bare `data/` line makes ruff's gitignore-respecting traversal skip the whole
  package at any depth. #132 found it, fixed its own new code by explicit path,
  and left the gate alone, because widening it is a repo-wide change with an
  unknown blast radius.

### The three blue-tier PRs

**#129 cold-start measurement** (`planning/memos/COLD_START.md`) answered neither
of the two candidates the question offered. Network is ruled out at **0.55s
median**, ~3% of the observed ~20s. Import ordering was real and is fixed —
`app.py` named a `fiscal_model` submodule at module scope, so reaching it
executed `fiscal_model/__init__` (0.98s, and through it `scipy.stats` and
`matplotlib.pyplot`); deferring it took **time to first paint 1.593s → 0.022s**
and modules-at-import 1,901 → 586, pinned by `tests/test_cold_start_ordering.py`,
which fails five ways on the pre-change file. **The largest term was one nobody
had looked for**: the page footer computing the entire 81-row validation
scorecard to print one clause, **8.68s of the landing page's 9.38s first script
run**. Community Cloud sleeps after **12 hours** and does not wake by itself, so
for a slept app no app-side work touches the first visitor at all; that half is
open with a runbook.

**#135 footer scorecard** closed the footer half on a third option neither
candidate in the memo offered: the count is a **generated artifact**
(`scripts/build_validation_headline.py` → `headline_counts.json`), read with
stdlib `json` and pinned by a test that recomputes the scorecard, so the landing
page's first script run went **8.404s → 0.668s** while the clause still prints on
the *first* run. Both understated docstrings were corrected. The **scored**
route is unchanged at ~10.6s, and that is a finding rather than a miss:
instrumented with a stack capture it has exactly one call over half a second,
**6.555s** through `preset_validation.get_validation_badge → _scorecard_index`,
which needs each row's figures rather than a count. Carry-over.

**#133 Plotly dark mode** themed 20 of 21 chart sites through `theme_figure`,
reading the ⚙ toggle's own `dark_mode` flag rather than `st.context.theme` (which
reports the *Streamlit* theme, always light in this deployment, and would have
made the charts disagree with the page). Values are written at **layout** level
because `st.plotly_chart(theme="streamlit")` merges Streamlit's own layout over
any custom template. Light mode is pinned byte-identical two ways and contrast is
measured rather than asserted.

**#134 Build frozen links** closed PR #111's carry-over: `/build?policies=&target=&metric=`
plus the shared `baseline=&engine=&spec=&mode=&frozen=1` lock, decoded and
refused by the same functions the other surfaces use. The package is re-applied
on **every** rerun, every input renders through the disabled-widget proxy, and
the **exports stay live**, because an export is not an edit. Values links freeze
too, since `composer.select_package` is a pure function of tags × vector. The
load-bearing test runs one package frozen and open and compares the scoreboard
metric by metric and the waterfall bar by bar.

---

## 5.8 Waves A and B of the high-stakes plan (2026-09-10, PRs #140-#146)

Seven PRs, and they are not this document's sequencing at all:
[`HIGH_STAKES_ACCURACY.md`](HIGH_STAKES_ACCURACY.md) re-ranks the work by **who
reads the number** and supersedes §6.2's *sequencing*, not its rules. Wave A is
**H1** the base rule (`model/hs-a-h1-base-rule`, PR #142), **H6** badges and
tiers (`ui/hs-a-h6-badges-tiers`, PR #140) and **H13** the payroll captions
(`docs/hs-a-h13-payroll-caption`, PR #141). Wave B is **H2** base growth
(`model/hs-b-h2-base-growth`, PR #144), its follow-on **H2b** the AGI column
(`model/hs-b-h2b-agi-column`, PR #146), **H3a** the corporate range
(`ui/hs-b-h3a-corporate-range`, PR #143) and **H9** provenance
(`provenance/hs-b-h9-targets`, PR #145).

Each lane pre-registered in `planning/lanes/` before touching code and appended
an outturn; those files are the record and this is the summary. **Every figure
here is from `scripts/cold_holdout.py`, `scripts/run_loo.py --donor-matrix`,
`scripts/run_validation_dashboard.py` and a 52-preset sweep on the merged tree.**
As in Wave 7 that is not any single lane's before/after — **H2 and H2b move the
same rows in opposite directions**, so H2's own Tier 1 figure is 15.6% and none
of the seven lane docs reads 14.7%.

### The tiers, before → after

| tier | before (post-Wave-7) | after (merged) |
|---|---|---|
| Out-of-sample (Tier 1) | 26 @ 15.0% / 10.6% median / 17 within 15 / 22 within 25 | **26 @ 14.7% / 12.6% / 15 / 23** |
| Calibrated reference (fitted) | 21 @ 1.73%, 21/21 within 15 | **16 @ 1.51%, 16/16** |
| … fitted, ledger rows held in place | 27 @ 5.6%, 25/27 | **27 @ 11.9%, 22/27** |
| Unfitted reconstructions | 34 @ 57.88% / 34.2% median, 9 within 15 | **39 @ 55.46% / 29.9%, 11 within 15** |
| … *the same 34 rows, on the new targets* | 57.88% | **58.26%** |
| Leave-one-out | 18 derivable @ 30.1% / 19.1%, 8 within 15 | **18 @ 35.7% / 29.1%, 6 within 15** |
| Distributional | 7 @ 0.00-5.86pp | **unchanged** |
| Scorecard rows | 81, 75 published | **81, 77 published** |
| Provenance, both tiers | 51 / 7 / 17 / 6 / 0 | **57 / 8 / 12 / 4 / 0** |
| Provenance, calibrated (55) | 30 / 7 / 12 / 6 / 0 | **36 / 8 / 7 / 4** |
| `revised_target_entries` | 16 | **22** |
| `EXAMINED_NOT_REVISED` | 6 | **14** |
| `retired_target_entries` | 0 | **0** (the state exists; the decision is open) |
| Preset badges | 24 | **44** (16 fitted / 25 reconstruction / 3 out-of-sample) |
| Tier 1 CI gate | `20 / 21` | **`20 / 22`**, plus a new per-class floor |

**Three different things moved those rows and they must not be run together.**
Tier 1 moved on **mechanism**; both calibrated tiers and leave-one-out moved on
**targets**, with not one derivation changing; and the badge and provenance
counts moved on **coverage**. Only the first is a statement about the model.

### Tier 1: the mechanism moved, and the intermediate figure is the honest part

**PR #144 raised the tier mean and the lane reported it.** Every generic run had
returned the same annual ten times — a tax-year-2023 SOI aggregate answering an
FY2026-2035 question on Tailor, Ask, Build and seven presets — and the base now
carries the scored vintage's own nominal-GDP index, window mean **1.355952**.
Ten rows moved, every pre-registered figure landed with a worst miss of **$0.08B**,
and the tier went **15.0% → 15.6%**, which is the plan's own stated
falsification condition. Nothing was tuned to make it fall. **PR #146 then took
it to 14.7%**, below where #144 found it, with 15 within 15% and 23 within 25% —
both better than either branch point — so the plan's H2 condition is satisfied
**by the pair and not by H2 alone**.

**The plan's endpoints for the two Option 46 rows were unreachable as written,
and the reason was measured before either file was opened.** §1.3(c) attributed
W7's 9.1% / 1.0% to "(b) and (c)", where (b) is *"no preset carries
`agi_inclusive_base`"* — a **preset** flag that cannot move a validation row, and
H1's own falsification test was that it did not (`cold_holdout.py --json`
byte-identical across PR #142). W7's middle step is SOI's **AGI column** in place
of its **taxable-income column**, which W7 itself scoped as "a lane of its own".
The measured chain is:

| row | before | +growth (#144) | +AGI column (#146) |
|---|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` | +49.8% | +34.1% | **+7.4%** |
| `cbo_opt46_agi_surtax_2pp_100k` | +37.4% | +17.9% | **−2.9%** |

**Only two of the eight classes moved.** AGI-inclusive surtax **20.7% → 17.6%**
and ordinary rate change **12.0% → 14.8%**, where **all four rows crossed from
under-prediction to over-prediction**. Everything else — capital gains 20.5%,
corporate 44.5%, enacted-law spending 13.4%, discretionary 4.6%, payroll 7.8%,
tax expenditure 13.1% — is byte-identical to Wave 7. The tier's mass fell
**390.7 → 383.3**.

**The tail re-ordered and the top of it changed hands**: `cbo_opt64_corporate_rate_1pp`
**44.5%**, `biden_capital_gains_39` 32.8%, `medicare_surcharge_2pp` 31.8%,
`warren_ultramillionaire_surtax_3pp` 24.8%, `illustrative_1pp_all` 24.5%,
`cbo_opt51_gains_at_death` 20.3%, `illustrative_top_rate_5pp` 20.2%,
`treasury_capgains_39_plus_stepup_elim.v2` 18.4%. Corporate is now the tail on
its own, and **four of the rows that replaced the two Option 46 rows carry
targets nobody published**.

### Tier 2 and leave-one-out: the targets moved and no derivation did

PR #145 judged eighteen calibrated benchmarks one at a time. **Six revised,
twelve examined-and-left, one transcribed-and-confirmed, and all 81
`model_10yr_billions` byte-identical.** Five of the six revisions make their row
worse:

| benchmark | was | is | document | error |
|---|--:|--:|---|---|
| `ss_donut_250k` | −2,700.0 | **−1,426.8** | CBO 60557 Option 62 alt 2, report p. 73 | 0.0% → **89.2%** |
| `tcja_rates_only` | +3,185.0 | **+2,158.7** | CRS R48286 Table 1 | 2.2% → **44.3%** |
| `trump_china_60` | −500.0 | **−650.0** | CRFB, 17 Dec 2024 | 44.3% → 57.2% |
| `eliminate_estate_tax` | +350.0 | **+407.2** | TF *Options 3.0* Option 83 | 0.0% → 14.0% |
| `eliminate_mortgage` | −300.0 | **[−495.0, −367.9]** | TF *Options 3.0* Option 25 (anchor); CRS IF13190 | 9.9% → 26.5% |
| `repeal_ira_credits` | −783.0 | **−851.0** | TF, House Oversight testimony | 0.0% → 8.0% |

**Read the five tier readings together or none of them.** Fitted 1.73% → 1.51%
*while nothing improved*, because the five rows that left averaged **2.42%**,
above the tier's own mean. Reconstructions 57.88% → 55.46% *while nothing
improved*, because the five arrivals average **36.42%** — and on a constant
population the tier gets **worse**, 57.88% → **58.26%**, all 0.38pp of it
`trump_china_60`. **The single honest number for what the new targets did to the
model's measured error is that 0.38pp, against 2.42pp of composition.** The one
reading that is not composition at all: **the 21 rows the fitted tier held before
this wave, scored on the targets it leaves behind, read 9.82%, 18/21 within 15%**
— what five untraceable targets had been worth to the tier's headline.

Leave-one-out is the same mechanism a third time: `run_loo.py --donor-matrix`
differs in **six lines** and every *derived* figure in them is identical
(`ss_donut_250k` still −2,664.0, `eliminate_mortgage` still −257.9). `Payroll`
**3.8% → 32.3%**, `Expenditures` **37.5% → 40.6%**, suite **30.1% → 35.7%**.
Wave 4's PR #107 did exactly this in a different module; *a mean that moves
because a target moved has not measured the model.*

### Five findings the waves produced

**1 — Three defaults for one flag, and the surfaces silently disagreed.**
`ordinary_income_base` was `False` on the dataclass, `True` on Tailor's checkbox,
computed `True` by the composer, and unset (so `False`) from Ask, which is why a
2pp surtax above $400,000 scored **−$166.5B on Tailor and −$314.6B on Ask, on the
same commit**, with the scorecard validating only the second. Two further things
fell out that nobody had asked about. **36 of the 52 presets carry the attribute
and not one of them reads it**, because the specialized modules override the
static path entirely — a field 36 policies carry and none reads will make the
next default flip look dangerous and be inert, *and the reverse trap is the real
one*. And **`DistributionalEngine` does not read the flag at all**, so one policy
object yields a revenue score and a who-pays table on two bases **2.57× apart**;
a test now asserts the divergence exists and fails with instructions when someone
closes it.

**2 — The defect in the AGI rows was a unit mismatch, and naming it that way is
what made it tractable.** `_estimate_from_irs_data` selected returns by an **AGI**
class boundary (SOI publishes size classes on AGI) and then computed
`max(0, avg_TAXABLE_income − T)`, subtracting a threshold from an average of a
different quantity. Read as "the base is a bit low" it invites a fudge factor;
read as "these are two different quantities" it has exactly one fix, and the fix
is **per-source** — which is how three of six rows moved and three did not.
**Composing published pooled ratios would have missed both Option 46 rows in
opposite directions**: marginal AGI over marginal taxable income is 1.3820 and
1.3094 pooled but **1.4052 and 1.2535** inside the filing-status split, because
the joint floor is twice the single floor and joint returns are a different share
of the two populations. W7 finding 3's rule again in a new form: *a ratio measured
on a pooled base is not the ratio that applies to a split one.*

**3 — The classification is not the flattering one, and both lanes declared that
before applying it.** PR #146's rule takes the AGI class's best-scoring row **five
times worse** (Warren 5.2% → 24.8%), and the three rows it *holds* would all get
worse if moved — `medicare_surcharge_2pp` to 68.4%, `illustrative_top_rate_5pp`
to 41.6%, `illustrative_500k_2pp` to 39.2%. Moving all six would read **17.8%**
for the tier against the measured 14.7%. Holding them is therefore also the lower
number, and the lane published the conflict of interest so the *reason* is
visible and can be overturned by a document rather than by a preference.

**4 — Four Tier 1 targets are rules of thumb, and two of them score the same
reform.** `illustrative_1pp_all` and `cbo_opt45_all_rates_1pp` are both "1pp on
every ordinary bracket"; the model scores them at −$1,195.3B and −$1,207.3B (the
gap is the vintage) against targets of **−$960.0B** and **−$1,185.3B**, 23.5%
apart. The first carries no source URL and the note *"Rule of thumb: 1pp ≈
$85-100B/year"*; the second is CBO's own *Options* line item on the window being
scored. **The model cannot agree with both, and Wave B swapped which one it
agrees with**: +4.1% → −24.5% on the rule of thumb, +22.4% → **−1.9%** on the
published option. `illustrative_top_rate_5pp`, `illustrative_500k_2pp` and
`warren_ultramillionaire_surtax_3pp` are the other three. It is the ledger's to
act on and PR #145 deliberately took none of it — but "the tier mean rose" reads
differently once it is known that much of the movement is against figures nobody
published.

**5 — Two claims this repository had been making turned out to be too strong, and
one target is very likely a real figure for the wrong quantity.** *"OCACT
publishes no ten-year dollar amount for any payroll provision"* is true of the
provisions tables and **false of the office**: its 11 July 2023 letter on the
Medicare and Social Security Fair Share Act prints **$3,035.1B** — for a $400,000
donut, so not a line item for either row, but the claim needed narrowing.
*"`eliminate_mortgage`'s two figures come from the same simulator and differ by
2.4×, which is itself the argument against adopting either"* was wrong about the
cause: the gap is a **baseline**, since Yale's $1.2T is scored pre-P.L. 119-21
where the itemising population roughly doubles, and two *independent* models on
one baseline are 35% apart, which is what a range is for. And
**`cap_employer_health`'s −$450B is most likely CBO's 2008 *Budget Options*
Option 9**, JCT-scored at $452.1B — 0.5% away — for a **$17,280/yr** cap against
this benchmark's stated $50,000. That is `extend_tcja_amt`'s shape exactly, the
right number for the wrong quantity, with the difference that **there is nothing
to move it to**: no agency has ever scored a cap at a chosen dollar level.

### Where the pre-registrations were wrong

- **The plan's §1.3(c) endpoints** (9.1% / 1.0%) embedded a step nobody had
  built, and attributed it to a preset flag that cannot move a validation row.
  Corrected in `HSB_h2_base_growth.md` §3.1 **before** any file was opened, and
  the correction held to the decimal. §1.3(c) is amended in place.
- **H1 pre-registered the `repeal_corporate_amt` label rename and could not make
  it**, because the label is a *key* of H6's map and Wave A is file-disjoint: two
  of the wave's own requirements contradicted for that one preset. H1 shipped the
  load-bearing half (the `CBO_SCORE_MAP` sign) plus **a test that asserts the
  remaining inconsistency**, and H6 took the rename with its own handover test
  inverted rather than deleted. The lane's pre-registration had predicted one of
  the two failing tests and missed the other; the full suite found it, *which is
  the argument for running the suite before believing a file-ownership boundary
  holds.*
- **H1's Decision 6 caption was silent on all three presets it exists for**, and
  only rendering it found that: `_ordinary_income_share` short-circuits to 1.0 in
  exactly the state the caption fires for, so the counterfactual came back as "the
  same number" and the guard returned `""`. The tests written first asserted the
  presets moved, which they had. *"The number moved" and "the sentence about the
  number appears" are different claims.*
- **H2's caption was wrong on dynamic runs, in both halves**, and neither the
  lane nor its tests caught it because every caption test ran `dynamic=False`. It
  read `final_deficit_effect`, which on a dynamic run also carries revenue
  feedback, so it both reconstructed a "before" figure the policy never printed
  and disagreed with **the headline directly above it** — by $265.5B, 69.1%, on
  Warren's dynamic run. *A caption that explains a headline must be computed from
  the same quantity as that headline.*

### What these waves did not do

- **Did not retire anything.** The `retire` state is built and tested on
  synthetic rows; owner decision ④ on the two pharma targets is open, with the
  exact one-commit edit written out in `HSB_h9_provenance.md` §8.7.
- **Did not open `corporate.py`.** H3a is presentation; H3b is Wave E.
- **Did not take the four rule-of-thumb Tier 1 targets** (finding 4), which are
  a target decision H9 was not scoped to make.
- **Did not rename the five preset labels quoting superseded figures** (§6.2
  item 43) — labels are `CBO_SCORE_MAP` keys and the wave's own file-disjointness
  forbids it.
- **Did not perform arithmetic on a published figure.** CRFB's own note that its
  tariff figures "would likely be 15 percent less" on this window is carried, not
  applied.


## 5.9 Wave C of the high-stakes plan (2026-09-11, PRs #148-#151)

Four PRs, the third wave of
[`HIGH_STAKES_ACCURACY.md`](HIGH_STAKES_ACCURACY.md): **H4** empirical bands
(`ui/hs-c-h4-bands`, PR #149), **H5** the decedent headcount
(`model/hs-c-h5-decedent-headcount`, PR #151), **H8** tariffs
(`model/hs-c-h8-tariff-feedback`, PR #150), plus the label-figure lane
(`ui/hs-c-label-figures`, PR #148) that discharged §6.2 item 43 and H9's second
carry-over. Each pre-registered in `planning/lanes/` before touching code and
appended an outturn; those files are the record and this is the summary.
**Every figure here is from `scripts/cold_holdout.py --json`,
`scripts/run_loo.py --donor-matrix`, `scripts/run_validation_dashboard.py`,
`scripts/build_validation_headline.py --check` and a 53-preset sweep by stable
id on the merged tree.**

**Two of the four moved no scored number at all**, and the two that did moved
rows in opposite directions — which is why the wave's two tier movements must be
reported separately and not netted.

### The tiers, before → after

| tier | before (post-Wave-B) | after (merged) |
|---|---|---|
| Out-of-sample (Tier 1) | 26 @ 14.7% / 12.6% median / 15 within 15 / 23 within 25 | **26 @ 14.5% / 11.5% / 16 / 22** |
| … error mass | 383.3 | **376.1** |
| Calibrated reference (fitted) | 16 @ 1.5%, 16/16 within 15 | **unchanged** |
| … fitted, ledger rows held in place | 27 @ 11.9%, 22/27 | **unchanged** |
| Unfitted reconstructions | 39 @ 55.5% / 29.9%, 11 within 15 | **39 @ 56.7% / 36.9%, 10 within 15** |
| … *the same 39 rows* | 55.5% | **56.7% — accuracy, not composition** |
| … `Trade` sub-population | 5 @ 34.2% | **5 @ 43.6%** (35.66% on the four with a document) |
| Leave-one-out | 18 @ 35.7% / 29.1% | **unchanged, donor matrix byte-identical** |
| Distributional | 7 @ 0.00-5.86pp | **unchanged** |
| Scorecard rows | 81, 77 published | **unchanged** |
| Provenance, both tiers | 57 / 8 / 12 / 4 / 0 | **unchanged** |
| `revised_target_entries` / `EXAMINED_NOT_REVISED` / retired | 22 / 14 / 0 | **unchanged** |
| Preset badges | 44 (16 fitted / 25 reconstruction / 3 out-of-sample) | **unchanged** |
| Tier 1 CI gate | `20 / 22` + eight class ceilings | **`20 / 22`**, capital-gains ceiling **26 → 24** |

**No target moved in this wave and no constant was retuned.** Both calibrated
tiers and leave-one-out are byte-identical, which each lane registered in advance
as its own falsification test. That is the clean case Wave 5 established and the
opposite of Wave B, where three tiers moved on targets and none on mechanism.

### Tier 1: one class moved, and the tier fell because of a row that got worse

**PR #151 is the only lane that touches Tier 1**, and it moves three of the four
capital-gains rows in two directions at once. `CapitalGainsBaseline._decedent_template`
divided households by `estate_flow_rate` — Poterba & Weisbenner's **dollar** flow
of estates over DFA net worth, dollars over dollars — to get a headcount of
**408,532** against roughly 3.09 million NCHS deaths, while `death_exit_rate()`
has returned `mortality_weighted_net_worth_share` (**2.647%/yr**, NCHS 2022 life
table against DFA net worth by age) and priced the lock-in wedge and the
accrued-gains drift with it since Wave 2. **One module, two death rates, 8.3×
apart.** The count is now the second of those, **3,384,194**; the level is
untouched at $196.2097B in 2025, so the count enters only as a divisor and gains
at death by DFA group are identical to twelve significant figures.

| row | before | after | registered band | verdict |
|---|--:|--:|---|---|
| `cbo_opt51_gains_at_death` | 20.3% | **35.5%** | 35.5 ± 2 | registered regression |
| `biden_capital_gains_39` | 32.8% | **27.0%** | 27.0 ± 2 | in band |
| `treasury_capgains_39_plus_stepup_elim.v2` | 18.4% | **1.8%** | 1.8 ± 2 | in band |
| `cbo_opt47_ltcg_qdiv_2pp` | 10.5% | **10.5%** | unmoved | unmoved to the cent |

Capital gains **20.5% → 18.7%**, mass 82.0 → 74.8; every other class is
byte-identical. Within-25 fell **23 → 22**, which is exactly the CI floor, and
the lane had registered anything below it as a falsification.

**Read the 1.8% the way the lane does and not as accuracy.** The count and the
level come from the **same** PW ratio and only the count was authorised to move;
held against `death_exit_rate`, PW's flow implies **0.372% of the accrued-gains
stock** where the stock's death exit is priced at **2.647%**, a factor of **7.1**,
of which the inter-spousal exclusion is some and nobody has measured how much.
`cbo_opt51` under-predicts, so a larger level would close what this lane opened.
**This is half of a two-sided correction and the lane says so in its own §7.**

### The reconstruction tier moved on accuracy, in the direction the lane registered

**PR #150 is the only lane that touches it**, and the same 39 rows sit in the
tier before and after, so **55.5% → 56.7% is like-for-like**. All of it is
`Trade`, 34.2% → **43.6%**:

| row | target $B | before | after | error | registered |
|---|---:|---:|---:|---:|---:|
| `trump_universal_10` | −2,171.1 | −1,258.5 | **−1,369.8** | 42.03% → **36.91%** | 36.90% |
| `trump_china_60` | −650.0 | −278.4 | **−331.1** | 57.17% → **49.06%** | 49.06% |
| `auto_tariff_25` | −386.2 | −182.2 | **−203.9** | 52.81% → **47.20%** | 47.20% |
| `steel_tariff_25` | −60.0 | −52.9 | **−105.2** | 11.89% → **75.28%** | 75.5% |
| `reciprocal_tariffs` | −1,500.0 | −1,396.8 | **−1,642.0** | 6.88% → **9.47%** | 9.39% |

Four of the five improve; `steel_tariff_25` carries the whole of the net, against
a target that is untraceable and examined-and-left twice, and **on the four rows
that have a document the sub-population improves 39.72% → 35.66%**.
`reciprocal_tariffs` got **worse against its anchor and better against its
range** — `within_published_range` False → **True**, distance $3.2B → **$0.0B**
against [−$1,800B, −$1,400B] — and the row carries both readings, because both
are correct and neither supersedes the other.

### Four findings the wave produced

**1 — The plan's residual cause for the whole trade block was backwards, and the
lane wrote that down before opening a file.** §1.2 row 6 and §3 H8 blamed
`trump_universal_10`'s 42.0% on a missing GDP-feedback channel and registered the
row *improving* to 20 ± 10 once it landed. **Adding a drag moves every trade row
further from its target**: all five targets are *conventional* estimates and the
model already sat below every one of them in magnitude. The 0.60–0.66 vs 40–50%
net/gross comparison was a **denominator mismatch** on top of that — the module
divides by gross duty *after* the import-demand response and the knowledge
snapshot's band divides by gross *before* it, on which the universal preset
already read **0.589**. So the channel is built and **reported beside** the
score, the column structure Tax Foundation FF861 itself publishes, and what moved
the rows is a convention correction the plan never named: **retaliation left the
conventional score**, where it was a category error against every target the
scorecard carries — and the repository already knew, because
`tariff_scoring_methodology.md` tells the Ask assistant that
`include_retaliation=False` "gives a strictly conventional score" while all five
scenarios and all five presets ran with it `True`. `estimate_behavioral_offset`
is now avoidance plus the income-and-payroll offset, **0.7125 of gross in either
direction**, against FF861's implied 0.738.

**2 — "Applied by size class" was refuted in sign, off the two tables the plan
itself names.** §3 H5 asked for the mortality rate graded by estate size so the
implied count at the top would fall toward SOI's 7,194. Read off the DFA's net
worth by age of head and NCHS Table 1's `Lx`, the grading runs the **other way**,
because the wealthy are older and therefore die at a *higher* rate:

| weighting | rate |
|---|--:|
| head-weighted (adult stationary population) | 1.6456% |
| net-worth-weighted (the shipped parameter) | 2.6468% |
| size-graded, at the top of the distribution | **2.8400%** |

Grading takes the implied count above $12.92M to **38,908** where the uniform
swap takes it to **36,262** — both *further* from 7,194, not nearer. Two
corollaries. The SOI comparison **needs a unit before it is a comparison**: SOI
counts *individual* decedents over a *gross-estate* threshold and the model counts
*households* over net worth, so a model count above SOI's is the expected sign and
W7's "1.6× short at the top against 7.6× overall" asymmetry is at least partly
that gap. And **W7's arithmetic prediction was wrong by more than 4×** — it said
about *twice* the count would reproduce Treasury's $1M → $5M exclusion step of
$33.4B, and 8.3× the count takes the step to **$9.40B**, through Treasury's figure
and out the other side.

**3 — The shipped accuracy band was worse than the plan's description of it, and
the largest defect was not on the plan's list.** §3 H4 said the ETI branch
"returns nothing for every calibrated preset". It does not return nothing; it
*falls through*, and `get_band_for_result` fell through to `Generic`, which **is**
the Tier 1 tier — so **31 of 56 surfaces printed "±14.7% across 26 calibrated
runs"** for policies with no Tier 1 row at all, *International Reference Pricing*
drawing a ±14.7% ribbon beside a scorecard row 701.0% from its target. The two
branches it replaced were both **fixed proportions of the point estimate**: 13
rows drew exactly `0.1 / 0.875` = 11.43% of the headline, the identical ribbon for
Flat Tax Reform at +$6,239.4B and the Medicare surcharge at −$426.6B; 27 drew one
of a small set of per-module fractions (38.0% climate and pharma, 45.6%
estate/credits/payroll, 46.8-47.1% TCJA/AMT/PTC/step-up). What replaces them is the policy's own class's Tier
1 spread, keyed by the same routing the CI per-class gate uses
(`fiscal_model/validation/policy_classes.py`, imported by `cold_holdout.py`, which
is byte-identical). **18 of 53 presets get a band; 35 print no band and say why**,
with their own row's error and tier printed beside the absence. **Coverage of the
inner band is computed and printed rather than asserted, and it is not a majority
everywhere** — `ordinary rate change` covers 1 of 4, because a 14.8% mean sits
under a 16.4% median.

**4 — A preset label was printing the model's own output in the slot a published
score occupies.** `🌱 Repeal IRA Clean Energy Credits ($783B)`: −783.0 is
`model_10yr_billions` and the live target is −851.0, positively signed on top.
That is `trump_corporate_15`'s `model_estimate` target (#122) and
`repeal_corporate_amt`'s inverted sign (#119/#140) in a **third** mechanism — the
app quoting itself back at the user in the one place the user cannot see it doing
so. Six labels now quote their row's current published target,
`_LABELS_QUOTING_A_SUPERSEDED_FIGURE` went **5 → 0**, and
`test_a_label_figure_never_contradicts_its_own_official_score` runs against **all
40 figure-carrying labels with no exemptions** for the first time. Two smaller
ones: **the worst stale string was not a label** but
`assistant/knowledge/ssa_trustees_2025.md`, which told the Ask assistant the
$250K donut was "scored by CBO at −$2.7T (model: −$2.4T, error 12%)" — three
errors in one BM25-indexed clause; and **`methodology.py` had that row under the
wrong *tier***, inside "calibrated reference models" at 0.0%, when a calibrated
reference stops being one the moment its target moves and its constant does not
follow.

### Where the pre-registrations were wrong

- **H8's three improvement bands were unreachable by the mechanism the plan
  named**, and the lane's §0 said so before any file was opened (finding 1). What
  it registered instead — the four post-retaliation figures and `steel_tariff_25`
  at 75.5% — landed to two decimal places.
- **Two of H5's three bands were written against pre-#126 readings.**
  `biden_capital_gains_39` could not reach **15 ± 8**: its rate channel alone is
  $359.02B against a $288.6B target, 24.4% over with the death channel set to
  *zero*. And `treasury_capgains…v2` could not *regress* to **22 ± 6**, because
  since PR #126 it is scored on its own FY2022–2031 decade where the model is
  **under** on the rate channel, so shrinking the death channel was always going
  to improve it. The lane registered its own computed bands beside the plan's and
  landed on all three.
- **H4's description of the band it was replacing was wrong in the direction that
  understated the defect** (finding 3), and the correction is in the lane doc
  rather than in the plan, because measuring the shipped surface was the first
  thing the lane did.
- **`steel_tariff_25`'s floor base would have scored 1.7%**, and the lane declared
  and refused it: −$59.0B against the −$60.0B target is a base missing most of
  what Section 232 reaches, and closeness to an untraceable figure is not a reason
  to keep it.

### A process lesson two lanes hit independently

**A piped pytest reports the pipe's exit code, not pytest's.** PR #151 recorded a
run that reported exit 0 from `| tail -25` while pytest had failed, and PR #149
lost a full suite run the same way; PR #119 §7.5 is the same lesson in its first
costume ("identical to main" is only evidence when the check being compared can
distinguish them). The rule every lane now follows: **write pytest's output to a
file and read the file**, and take the exit code from the unpiped command.
`ANTHROPIC_API_KEY` stays unset for the suite (process rule 6) and is used only
for the deliberate smoke run.

### What Wave C did not do

- **Did not move a target, retune a constant, or open the ledger.** Both
  calibrated tiers, leave-one-out and all 81 scorecard provenance fields are
  byte-identical.
- **Did not take the level half of the capital-gains death channel** (finding 2's
  7.1× factor), which is a level nobody may change by implication and is now
  §6.2 item 55.
- **Did not decide the decedent universe.** The crude adult rate reads `cbo_opt51`
  at 32.1% and the class at 17.7%, the all-age rate 28.4% and 16.9% — both
  *better* than the authorised constant, and both refused, because picking the
  best of three is fitting a parameter to a benchmark.
- **Did not register a new Tier 1 row.** Eight classes at n = 1, 1, 2, 3, 4, 4,
  5, 6 is a thin basis for a band and two classes print a single observation;
  registering one here would have been selecting a target after seeing what the
  band needed. That is H10, Wave E.
- **Did not rewrite the `PRESET_POLICY_PACKAGES` totals** — seven of the twelve
  curated packages state a figure that no longer equals the sum of their members
  (§6.2 item 56) — because the only reader is dead code and twelve list prices
  are a decision about figures, not a label fix.


---


## 5.10 Wave D, and the first two lanes of Wave E (2026-09-11, PRs #155-#162)

Seven PRs, merged in the order #155, #157, #158, #160, #161, #162, #159: the
three lanes of Wave D of
[`HIGH_STAKES_ACCURACY.md`](HIGH_STAKES_ACCURACY.md) — **H11** the PTC coverage
response (PR #155), **H7** the five expenditure magnitudes (PR #157), **H12**
the illustrative preset group (PR #158) — the two owner-decision lanes Wave D's
own gates required (**③ and ④** of the ledger, PR #160; the **SALT current-law
baseline**, owner ⑧, PR #161) — and the first two lanes of
[`ROUTE_TO_8_5.md`](ROUTE_TO_8_5.md)'s Wave E, **R2** the Tier 1 targets with no
document (PR #162) and **R1** CBO's own baseline, transcribed (PR #159). Each
pre-registered in `planning/lanes/` before touching code and appended an
outturn; those files are the record and this is the summary. **Every figure here
is from `scripts/cold_holdout.py --json`, `scripts/run_loo.py --donor-matrix`,
`scripts/run_validation_dashboard.py`, `scripts/build_validation_headline.py
--check` and a 53-preset sweep by stable id on the merged tree.**

**The headline is a smaller battery, and it has to be read as one.** Tier 1 goes
**26 rows at 14.5% → 22 rows at 11.6%**, and **most of the fall is a smaller
battery rather than a better model**: R2 withdrew **four** rows for absence of a
document and superseded a fifth onto CBO's own printed option. The count within
25% falls **22 → 19** while the **share** rises **84.6% → 86.4%** — and only the
second of those two is comparable across a battery that changes size, which is
the lesson R2 wrote down and the reason both are quoted here.

### The tiers, before → after

| tier | before (post-Wave-C) | after (merged) |
|---|---|---|
| Out-of-sample (Tier 1) | 26 @ 14.5% / 11.5% median / 16 within 15 / 22 within 25 | **22 @ 11.6% / 8.9% / 18 / 19** |
| … error mass | 376.1 | **255.3** |
| … within-25 as a **share** | 84.6% | **86.4%** |
| … `secondhand` / `model_estimate` targets | 5 / 0 | **0 / 0** |
| Calibrated reference (fitted) | 16 @ 1.5%, 16/16 within 15 | **15 @ 1.6%, 15/15** |
| … fitted, ledger rows held in place | 27 @ 11.9%, 22/27 | **26 @ 12.4%, 21/26** |
| Unfitted reconstructions, **scored** | 39 @ 56.7% / 36.9%, 10 within 15 | **38 @ 37.5% / 30.1%, 11 within 15** |
| … **with the retired rows held in place** | — | **40 @ 55.5% / 33.6%, 11/40** |
| … retired targets | 0 | **2 @ 397.2%** at withdrawal |
| … `Pharma` sub-population | 3 @ 277.8% | **1 @ 39.0%** |
| … `model_estimate` targets inside the tier | 2 | **0** |
| Leave-one-out | 18 @ 35.7% / 29.1%, 6 within 15 | **18 @ 36.5% / 30.2%, 5 within 15** |
| Distributional | 7 @ 0.00-5.86pp | **unchanged** |
| Scorecard rows / published | 81 / 77 | **77 / 73** |
| Provenance, both tiers | 57 / 8 / 12 / 4 / 0 | **58 / 8 / 7 / 4 / 0** |
| `revised_target_entries` / retired | 22 / 0 | **22 / 2** |
| Preset badges | 44 | **42** |
| Presets whose headline moved | — | **13 of 53** |
| Tier 1 CI gate | `20 / 22` + eight class ceilings | **`15 / 19`**, four ceilings re-derived |
| Baseline: FY2026-2035 cumulative deficit | $29,529.09B | **$23,143.30B** (CBO's own printed $23,143.3B) |

**Never quote the reconstruction tier's 37.5% without the 55.5% beside it.** The
first is the tier the dashboard scores; the second is the same tier with the two
targets owner decision ④ withdrew held in their places, and the difference
between them is a deletion, not a model.

### Tier 1: three movements in three directions, and the largest is a withdrawal

No lane moved the tier twice, and the chain is worth keeping because no lane's
own before/after is the merged reading. It is shown in the order the arithmetic
composes rather than the order the branches merged — #159 landed last, and R2's
own §5 published both readings for exactly this reason, so the two orderings
agree on the endpoint to the decimal:

| step | n | mean | median | within 15 | within 25 | mass |
|---|--:|--:|--:|--:|--:|--:|
| post-Wave-C | 26 | 14.5% | 11.5% | 16 | 22 | 376.1 |
| **+ #160**, IIJA on its own decade | 26 | **13.8%** | 10.6% | **17** | 22 | 358.2 |
| **+ #159**, CBO's own baseline | 26 | **14.7%** | 10.6% | 17 | **20** | 381.6 |
| **+ #162**, four withdrawals and a supersession | **22** | **11.6%** | **8.9%** | **18** | **19** | **255.3** |

**#160 took owner decision ③ and applied PR #126's window rule to the second
row it fits.** `iija_2021_discretionary` is superseded to a `.v3` scored on
**FY2022-2031**, the decade CBO's own table covers, at the *unchanged* +$415.4B
target: **+$339.98B / 18.17% → +$414.29B / 0.28%**, Acceptable → Excellent, and
`enacted-law spending` **13.4% → 7.4%**, mass 40.2 → 22.3. The row's own note now
says what the 0.3% is: the authority path outlays **$434.1B in total against
$415.4B, 4.5% high**, while **$19.8B** falls in FY2032 or later, **so 0.3% is
smaller than either term** and reading it as evidence about the spend-out profile
would repeat the error the Treasury row's 0.2% and FRA's old 6% both made.

**#159 is a pre-registered regression and the reason is the cleanest sentence of
the round: the tier got worse because the base got right.** Transcribing CBO's
February 2026 and January 2025 tables moved **eleven** rows, ten of them onto
figures §3.1 had computed before the mechanism existed. CBO's own FY2023 → FY2025
nominal growth is **10.70%** where the hand-entered block implied **8.99%**, and
every row that worsened was already over-predicting. Two classes carry the whole
of it — `agi_inclusive_surtax` **17.6% → 20.4%** and `ordinary_rate_change`
**14.8% → 16.6%** — with `cbo_opt46_agi_surtax_1pp_20k` going 7.4% → **7.9%**,
`cbo_opt46_agi_surtax_2pp_100k` −2.9% → **2.4%**, `biden_high_income_tax` to
**21.9%** and `cbo_opt45_all_rates_1pp` to **1.3%**. The eleventh row moved
through a channel §3.1 did not
enumerate — `cbo_opt56_employer_health_income_only` 13.1% → **12.8%**, because
the cap's indexation proxy reads the vintage's **inflation assumption** rather
than its GDP levels — and the general form of that is worth carrying: **a
baseline has two surfaces a score can read, levels and rates, and a lane that
enumerates one of them will miss rows.**

**#162 then withdrew the rows nobody published.** Four retirements —
`warren_ultramillionaire_surtax_3pp` (TPC's AGI-surtax work is thirteen tables
and **all of them at 10 percent**; the "3pp" is the Ultra-Millionaire Act's
*wealth* rate transplanted onto an income base), `medicare_surcharge_2pp`
(Treasury's proposal is **1.2pp**, and prints **$403,790M**),
`illustrative_top_rate_5pp` and `illustrative_500k_2pp` (both call themselves
"Illustrative" in their own records; the *Options* volumes are deficit-reduction
menus and carry no rate cut at all) — and one supersession,
`illustrative_1pp_all.v1`'s rule-of-thumb −$960.0B → CBO publication **58164**
Option 13 alternative 1's printed **−$1,081.3B**, which takes that row 28.7% →
**14.3%**. Tier 1 `secondhand` targets go **5 → 0**; every one of the 22
survivors is `line_item`.

Per class, and **read the composition before the means**:

| class | n | mean | median | mass | share | ceiling | post-Wave-C |
|---|--:|--:|--:|--:|--:|--:|---|
| capital gains | 4 | **18.7%** | 18.8% | 74.8 | 29.3% | 24 | 18.7% / 74.8 — unmoved |
| ordinary rate change | 4 | **12.9%** | 14.3% | 51.8 | 20.3% | 15 | 14.8% / 59.3 |
| corporate | 1 | **44.5%** | — | 44.5 | 17.4% | 56 | 44.5% / 44.5 — unmoved |
| discretionary spending | 5 | **4.6%** | 2.6% | 23.2 | 9.1% | 6 | 4.6% / 23.2 — unmoved |
| enacted-law spending | 3 | **7.4%** | 9.8% | 22.3 | 8.7% | 10 | 13.4% / 40.2 |
| payroll | 2 | **7.8%** | 7.8% | 15.6 | 6.1% | 10 | 7.8% / 15.6 — unmoved |
| tax expenditure | 1 | **12.8%** | — | 12.8 | 5.0% | 16 | 13.1% / 13.1 |
| AGI-inclusive surtax | 2 | **5.2%** | 5.2% | 10.3 | 4.0% | 7 | 17.6% / 105.4 |

**Capital gains is the largest error mass again, and nothing in it moved.** The
two AGI-surtax rows were the tier's largest group after Wave 7 and are now the
smallest, at n = 2 — because four of their six rows were withdrawn, not because
the class improved. Four of the eight classes are byte-identical across the whole
round. **Three classes are now single or double observations**
(`corporate` and `tax_expenditure` at n = 1, `AGI-inclusive surtax` and
`payroll` at n = 2), which is criterion ① of `ROUTE_TO_8_5.md` moving the wrong
way and is R3's whole reason for existing.

**The CI gate moved six ways and not one of them was a choice.**
`tests/test_ci_workflow.py`'s two one-sided invariants fail a ceiling looser than
`ceil(mean × 1.25)` and a floor above the live within-25 count, so pooled
**20 → 15** and **22 → 19**, `agi_inclusive_surtax` **22 → 7**,
`ordinary_rate_change` **19 → 15** (all four R2's), `enacted_law_spending`
**17 → 10** (#160's) and `tax_expenditure` **17 → 16** (R1's). Re-derived on the
merged tree the pooled ceiling gives 15 again and the floor rule gives 18, which
would **loosen**, so it stays at 19 — met with no slack.
`ordinary_rate_change = 15` is **tighter** than its own re-derivation of 17 and
stays, because the rule is downward only.

### The reconstruction tier fell eighteen points and not one of them is accuracy

The chain, which four separate mechanisms built:

| step | n | mean | median | within 15 |
|---|--:|--:|--:|--:|
| post-Wave-C | 39 | 56.7% | 36.9% | 10 |
| **+ #155**, the same 39 rows | 39 | **56.5%** | 36.9% | 10 |
| **+ #157**, `cap_charitable` reclassified in | 40 | **55.5%** | 33.6% | 11 |
| **+ #160**, two targets withdrawn | **38** | **37.5%** | **30.1%** | **11** |
| … the same 40 rows, retired held in place | 40 | **55.5%** | 33.6% | 11 |

**Only the first step is accuracy**, and it is 0.2pp. **#155** replaced the one
transferred aggregate offset share with a composition priced per person-year:
`repeal_ptc` **−$774.13B → −$840.84B**, **29.62% → 23.56%** against the carried
−$1,100B, with the `PTC` sub-population 19.5% → **16.4%**. The four channels are
published rather than assumed — employment-based **+$155.44B**, the Medicaid/CHIP
mirror **−$31.39B**, BHP/§1332 **−$5.89B**, uninsured **$0.00B**, a net offset of
**+$118.16B** and a share of **12.3211%** against the 19.28% it replaced.

**#157** moved two rows, both registered as regressions before a file was opened,
both by exactly the `(1 ± e_new)/(1 ± e_old)` factor its §3.1 computed:
`cap_charitable` 0.3% → **12.5%** and `eliminate_mortgage` 26.5% → **30.2%**. The
magnitudes are now documents — mortgage **0.10 → 0.145028** (Poterba & Sinai's own
$72.4B against $61.9B) and the charitable 28% benefit-rate ceiling
**0.40 → 0.220780** (the recapture identity at CRS R40518's central ε = 0.5) —
and both movers regress for the same reason stated twice: **the held-out statics
are already short of their targets, so a larger erosion and a smaller
magnification both move the score away from the target.** The symmetric
observation is the useful one: had a sourced magnitude improved both rows, the
suspicion would be that the document had been chosen to fit.

**#160 then took owner decision ④ and withdrew two targets rather than two
rows.** `expand_drug_negotiation`'s −$500B is this repository's own extrapolation
and `international_reference_pricing`'s −$100B is a RAND **price index** used as
a score; both rows keep their scorecard entries, their model figures to six
decimals and their withdrawn figures, and the tier reports them separately at
**2 @ 397.2%**. `Pharma` as a sub-population goes **3 @ 277.8% → 1 @ 39.0%**, and
the reconstruction tier's `model_estimate` target count goes **2 → 0** — so the
sentence *"no row this tier reports is scored against this model's own output"*
is true of it for the first time. **The withdrawal moves the held-in-place
reading by nothing, and that identity is its falsification test**: on #160's own
branch the line reads 39 @ 56.5% before and after, and on the merged tree it is
**40 @ 55.5%**, which is exactly what the tier read the moment before the
retirement. A retirement that moved that figure would have been a retuning
wearing a ledger's clothes.

**The fitted tier lost a row to a fifth mechanism, and its mean went up.**
`test_loo_is_materially_worse_than_by_construction` failed at 1.42% on H7's
branch, and the whole of it was `cap_charitable`:
`create_cap_charitable_deduction`'s annual had been fitted so that
`static × (1 + 0.40)` lands on −$200.0B, so once the 0.40 is sourced **the
constant is fitted to a quantity the module no longer computes.** PR #119's
standing rule applies — reclassify, do not retune, do not exempt — so the row is
`calibrated_to_target=False`, fitted **16 → 15** and reconstructions **39 → 40**,
and the leakage guard `−174.9 × 1.40 / 1.220780 = −200.6` is asserted within 1%
so that "reclassified" cannot become a licence to move the constant. Read the
means the way this file insists: **1.5% → 1.6% is the fitted tier getting worse
while nothing regressed**, because the row it lost was carrying 12.5% against a
tier of near-zeros. **Four live mechanisms move a row out of the fitted tier
became five.**

**Leave-one-out is the price H7 registered**: Expenditures **40.6% → 43.6%**, the
suite **35.7% → 36.5%**, median 29.1% → 30.2%, within-15 6 → **5**. #161 moved
one line of the donor matrix by **$0.2B** and no module mean; every other lane in
the round left it byte-identical.

### The baseline is the largest thing this round moved, and it moves no score

**#159 is the first time this repository's default baseline has been CBO's own
table rather than a reconstruction of it.** February 2026 and January 2025 are
transcribed from `cbo-data`, publication **61882** (*The Budget and Economic
Outlook: 2026 to 2036*, data release 51118), and the falsification condition is
an identity: FY2026-2035 deficits sum to **$23,143.303B** against CBO's own
printed **$23,143.3B**, with every *year* inside $0.05B of `proj_deficit_total`
on both vintages and two window starts.

| figure | before | **after** |
|---|--:|--:|
| cumulative FY2026-2035 deficit | $29,529.09B | **$23,143.30B** |
| mean annual deficit (Build's target strip) | $2,952.91B | **$2,314.33B** |
| end-of-window debt | $49,362.06B | **$53,103.22B** |
| end-of-window nominal GDP | $47,534.59B | **$45,011.50B** |
| end-of-window debt/GDP | 103.84% | **117.98%** |
| deficit share of GDP | 7.31% | **6.05%** |
| January 2025's cumulative deficit | $27,710.57B | **$21,758.26B** |

CBO's own report headlines are reproduced rather than approximated — FY2026
**−$1,852.7B**, FY2027-2036 **−$24,406.0B**, FY2036 **−$3,115.4B** — and CBO's
headline decade is **FY2027-2036** where the app's is FY2026-2035, which is a
different window on one table and not a disagreement. **February 2024 keeps a
reconstructed budget path**, because `cbo-data` publishes no ten-year budget
table for that edition and June 2024 is publication **60039**, a different
document whose FY2025 deficit is $1,937.9B against January 2025's $1,865.3B;
borrowing it would have graded a vintage `transcribed` against a document it does
not name. **That vintage's debt/GDP is now a mixture of CBO's GDP and this
module's debt and should not be quoted** — §6.2 item 71.

### Per-lane, what a user can see

**Thirteen of 53 presets moved**, eleven of them on the headline — each with a
Decision 6 caption computed from the scored result rather than from a literal:

| preset | before | after | | lane |
|---|--:|--:|--:|---|
| 📋 Repeal SALT Cap | +$1,155.56B | **+$740.31B** | −35.93% | #161 |
| 📋 Cap Charitable Deduction | −$200.62B | **−$174.94B** | +12.80% | #157 |
| 🏥 Repeal ACA Premium Credits | −$774.13B | **−$840.84B** | −8.62% | #155 |
| eight generic rate presets | — | — | **+2.97%** each | #159 |

The eight are Flat Tax Reform, Middle Class Tax Cut, Top Rate to 45%,
Progressive Millionaire Tax, Warren Ultra-Millionaire Surtax, High-Earner
Medicare Surcharge 2pp, Custom Policy and Biden 2025 Proposal. The other two of
the thirteen are **Biden Corporate 28% and Trump Corporate 15%, which move in
dynamic mode only** — the dynamic feedback reads the baseline's own levels while
their static headlines are unchanged to the cent, **so no caption fires for
them** and the movement is recorded in R1's outturn instead. The remaining 40
score to the cent in both engine modes.

**Two presets lost their published comparison and kept their number.** R2's
retirements take the `official_score` off **Warren Ultra-Millionaire Surtax**
(−$350.0B) and **High-Earner Medicare Surcharge 2pp** (−$310.0B), following
`top_rate_45`'s Phase E precedent exactly: both still score, both show the
model's own estimate, neither prints a dollar figure in its label, and the badged
set goes **44 → 42** (a badge is exactly a preset carrying a `CBO_SCORE_MAP`
`official_score`, so removing the score removes the badge; H7's reclassification
moved a badge's *tier* rather than its existence). Build's card copy moves
**"45+ scored policies" → "40+"**, because Build's catalog holds 44 options and a
promise the catalog cannot meet is the defect H6 exists to prevent.

**#158 moved no number at all, which was the whole of its brief.** Five presets
— Double IRS Enforcement, Expand Drug Negotiation, Universal Insulin Cap,
International Reference Pricing, Comprehensive Drug Reform — now sit in an
**`Illustrative - unfitted reconstructions`** group that sorts last on Explore
and Build, with the group's note above the picker and each row's own distance
printed beside it. `cold_holdout.py --json`, the dashboard, 52 presets × two
modes, 44 badges, `resolve_preset` for all 52 ids and `check_readiness.py
--strict` are byte-identical, compared by restoring `main`'s files into the tree
rather than by reasoning about what they would print.

### Seven findings, one from each lane

**1 — #155: an aggregate ratio was booking a Medicaid *saving* as a cost, and
only a decomposition could see it.** CBO's $80B of offsetting effects contains
**+$21B of Medicaid and CHIP**, an outlay *increase* under the extension, driven
in CBO's own words by "a reduction in offers of employment-based coverage".
Scaling every channel by one share means a repeal inherits that $21B in the
eroding direction, when the mirror of CBO's own mechanism is a **saving** — worth
**$31.39B in the wrong direction**, 3.7% of the score. **A share is
sign-symmetric in magnitude and therefore cannot be right about a composition
whose channels do not all reverse together.** The second half is a denominator
wrong by 61%, and both halves are printed by CBO: the extension's *marginal*
enrollee receives **$5,370** a year, the *average* subsidized enrollee a repeal
removes costs **$8,671** ($959B over 110.6M person-years). Essentially the whole
of 19.28% → 12.32% is those two numbers divided.

**2 — #157: a behavioural magnitude is a property of the reform, and the
arithmetic forces that grain on its own.** Wave 7 established the *direction*'s
grain on the documents — CBO gives one deduction opposite verdicts under a rate
ceiling and a floor. The magnitude gets there without a document and
counter-intuitively: **tightening the charitable ceiling from 28% to 15% roughly
halves the behavioural share, 0.2208 → 0.1140**, because the recapture rate *is*
the cap rate and that dominates the larger price change. A module-wide constant
would have over-magnified CBO 60557 Option 49's 15% alternative by **94%**, and
the shipped 0.40 by **251%** — and nothing in the repository scores that
alternative today, which is exactly why such a constant would have survived
unnoticed. Two corrections to this plan's own text travel with it: **"nearer 18%"
is not reproducible** (the identity gives **22.1%**, and 18% would need
ε = 0.405, which CRS does not print), and **0.40 was the right identity at
ε = 0.906**, above the top of CRS R40518's own published band of 0.79 — so the
module was not confusing two quantities, it was assuming a giving response 15%
above the literature's high case.

**3 — #158: demoting a group can delete an area, and a new preset area has a
second home nobody enumerated.** `Drug Pricing` held exactly the four demoted
pharma presets, so Explore's policy-area selectbox **loses** an area rather than
emptying one and stays at 14 rather than rising to 15. The sharper half is that
`validation/credibility.py`'s `PRESET_AREA_TO_SCORECARD_CATEGORY` routes an area
to the limitations list and holdout label a result surface prints, and its
invariant fired on a lane whose every instrument was byte-identical — **the
defect was in a declaration rather than in an output**, so nothing a user reads
had moved and the check was still right to fail. **When a lane adds a member to
an enumerated domain the question is not only "what does this change" but "who
else enumerates this domain".** The lane also reproduced H6's own finding inside
a week, shipping an `illustrative_note(with_figure=True)` branch with no caller
and then deleting it: **a helper with a mode parameter should be checked against
its callers before it is committed.**

**4 — #160: both of the brief's predicted movements were wrong, and each is
wrong for a reason about gates rather than about models.** Within-25 was
predicted 22 → 23 and **did not move**, because IIJA was already inside 25% at
18.2% — *improving a row already inside the band moves only the tighter count*,
which makes a count-based floor insensitive to exactly the improvements it exists
to reward. And `model_estimate` provenance was predicted 4 → 2 and **stayed at
4**, because a **withdrawn target still has a provenance**: retiring a target
says nothing about where the withdrawn figure came from. What the retirement does
move is the tier split — `uncalibrated_reconstruction.model_estimate_targets`
**2 → 0** and `retired_targets.model_estimate_targets` **0 → 2**. A smaller
finding with the same shape: the ledger's identity `len(CALIBRATED_TARGETS) ==
2 × len(_LEDGER)` assumed every ledger row is half of a supersession, and **a
retirement has no pair**.

**5 — #161: a preset and its benchmark can deliberately score different
baselines, and the badge is the thing that cannot say so.** P.L. 119-21
sec. 70120's cap path is transcribed from the statute — $40,000 in 2025 rising at
**101 percent** a year to $41,624.16 in 2029, a **30 percent** phasedown above
$500,000 indexed the same way, and **$10,000 flat from 2030** — and the repeal
preset now scores against it: **+$1,155.56B → +$740.31B**. The scorecard row does
**not** move, because PWBM's Table 3 prices repeal against an extended-TCJA world
in which the cap is permanent, and a benchmark that moved onto current law would
stop checking its own document. Both are right, so `HEADLINE_ROW_DIVERGENCE` grew
a third kind, `baseline`, and the caption carries the sentence — but
`salt-cap-repeal` still prints a green **"Unfitted reconstruction, 1.1% from
$1.17T"** beside a headline of **$740.3B**, and **only the full suite could see
it**, because the only check that distinguishes "the app moved" from "the app and
its badge moved together" is the one that scores both. The lane also found that
JCT has scored this mechanism and the repository already carries the score —
`pl119_21_salt_cap_40k`, JCX-35-25 line 20, **+$946,209M** — against which the
new path reads **$723.1B, −23.6%**, whose largest named term is **new itemisers**
(JCX-45-25 puts SALT claimants at **11.8M → 17.8M returns** under the $40,000
cap, so the filers a raised cap pulls into itemising are absent from a TY2023 SOI
base at every income).

**6 — #159: `real_gdp_growth + inflation` is not nominal GDP growth, and
`VINTAGE_SOURCING` was false for two of three vintages.** The reconstruction
added a real rate to a **PCE** price index where CBO publishes `gdp_pct_change`,
the nominal path itself; even on January 2025, whose five assumption series were
genuinely transcribed, the two disagree — 4.31% against CBO's own 4.555% in
FY2025 — so **a vintage can be correctly transcribed on every published
assumption and still produce the wrong nominal path.** The grade itself was
wrong: against CBO's own tables February 2024 deviates by **0.602pp** on real GDP
growth and **1.048pp** on labour force participation, February 2026 by 0.386pp
and 1.700pp, and **February 2026's ten-year Treasury note *fell* 4.5% → 3.9%
where CBO's own table rises 4.10% → 4.38%** — a baseline whose interest-rate path
points the wrong way prices debt service the wrong way, and that direction is now
a test rather than a memory. Two process findings ride with it: **CBO's
timing-adjusted components do not sum to its unadjusted totals** (the
defence/nondefence split misses `proj_outlays_discretionary` by $5-7B in the five
years 1 October falls on a weekend, so the split is taken as a *share* and
apportioned, PR #127's SOI Table 1.2 rule in a second place), and **a sweep that
reports "0 of 106 moved" may be reporting "0 of 106 measured"** — the registered
preset zero came from a harness that scored a dict, so every row raised
identically before and after and the diff was empty the way an empty file diffs
clean. PR #119 §7.5 in a second costume; the replacement fails loudly on a row it
could not score.

**7 — #162: a retirement that *raises* the honest error is the cleanest possible
demonstration that the rule is about documents.** `medicare_surcharge_2pp` had
been reporting **31.8%**; Treasury's proposal is a **1.2pp** increase, and
restated on Treasury's own rate the model reads −$245.2B against −$403.8B,
**39.3% under**. The trap was named in the pre-registration and avoided: the
FY2025 volume's figure sits close to this row's *2pp* output, so adopting it would
have bought a small error with a 1.67× rate mismatch — two errors cancelling, and
the flattering option. Two more that no search could have found: the Warren row's
**name** was wrong, not just its number (the Ultra-Millionaire Tax Act is a
**wealth** tax and the "3pp" is its billionaire rate transplanted onto an income
base, so the reform does not exist), and `medicare_surcharge_2pp`'s −$310.0B
matches the FY2025 Green Book's **child-credit** row to 0.008% — a *cost*, the
opposite sign to the raiser it was scoring, recorded as a coincidence and
explicitly not claimed as provenance. And the pair that survived says something
about the model rather than the targets: **CBO prices the same 1pp reform three
times and gets −$884.0B, −$1,081.3B and −$1,185.3B, 9.6% apart, where the model
gives two of them figures 1.0% apart** — so `illustrative_1pp_all` and
`cbo_opt45_all_rates_1pp` measure the model's **insensitivity to the decade**,
not two independent predictions.

### Where the pre-registrations were wrong

- **#159's preset prediction was a measurement of nothing** (finding 6). It
  registered "no preset moves" and eighteen of 106 preset × mode rows moved; the
  harness had scored a dict and recorded 106 identical errors on both trees.
- **#160's two predicted movements were both wrong** (finding 4), and they were
  mutually inconsistent besides: with `published_entries = total − model_estimate
  − unclassified`, moving `model_estimate` to 2 would have moved published to 79.
- **The plan's H7 bands were unreachable and its baseline was two weeks stale**,
  which the lane recorded in its §0 before opening a file: `eliminate_mortgage`'s
  quoted LOO baseline of 14.0% predates Wave B's range revision and reads 29.9%,
  the Expenditures module reads 40.6% and not 37.5%, and the registered
  *direction* was wrong even against the old point target, because a bigger
  erosion on a static already short of it cannot move toward it. **A plan band
  computed off a number a later wave has moved is worth re-deriving rather than
  inheriting.**
- **#158's arithmetic was wrong and its substance right**: it predicted Explore's
  policy-area count rising 14 → 15 and the count stayed at 14, because an area
  with no members is not offered at all.
- **#155's §3.2 quoted a stale leave-one-out figure** (29.6% where the live suite
  reads 35.7%). The prediction attached to it — "byte-identical" — was correct,
  which is the only reason it cost nothing.
- **#161 deviated from its own arithmetic and reported it rather than smoothing
  it**: §3 held within-class AGI at its SOI level while ageing the SALT amounts,
  and the implementation ages both, because freezing the incomes a phasedown is
  read against while growing the taxes it limits is not a coherent pair. Worth
  **+0.29%** on the repeal leg and **−0.63%** on the eliminate leg; no band
  crossed.

### What this round did not do

- **Did not retune a constant anywhere.** `validation/scenarios.py`'s fitted
  annuals were opened by no lane; `cap_charitable` was reclassified and its
  leakage guard strengthened so that a later lane which retunes it fails a test.
- **Did not adopt the figure that would have flattered the PTC row.** Zeroing the
  employment-based channel — which CBO's own Table 3 argues for, since 3.5M of
  the 6.9M marginal enrollees are above 400% FPL and the February 2026 vintage
  caps §36B eligibility there — gives **−$996.28B and 9.43%** against the carried
  target. It is not taken, because "most" does not license a zero and
  §36B(c)(2)(C) bars only an *affordable* offer;
  `test_the_esi_concentration_is_measured_and_not_taken` asserts the shipped path
  is **not** the one nearer the target.
- **Did not move the `repeal_ptc` target.** −$1,100B stands, PR #122's verdict
  against $1,142B is not reopened, and the June 2024 gross demonstration still
  returns **−$1,143.0B, 0.09%** from CBO's own figure — now a test rather than a
  number in a document.
- **Did not source the other three expenditure magnitudes** (employer health
  0.20, retirement 0.30, SALT 0.05). Each search is recorded in H7 §1 so the next
  lane does not repeat it, and the one that matters is employer health, because
  it is the only one on a Tier 1 row. §6.2 item 66.
- **Did not build a fourth `BaselineVintage`**, and did not let February 2024's
  mixed-grade debt/GDP go unmarked. §6.2 item 71.
- **Did not register a single new Tier 1 row**, in a round that removed four. The
  tier is **22 rows against criterion ①'s 40**, `agi_inclusive_surtax` is down to
  **n = 2**, and two classes remain single observations. Growing it back is R3,
  and R2's own hand-off says the tier now contains **no rate cut and no positive
  target** at all.
- **Did not move `CORPORATE_APP_MODE`.** It is still `reported`, the corporate
  row is still Tier 1's largest at **44.5%** and 17.4% of its mass, and H3a's
  measurement — `derived` inside the published span at +7pp, `reported` outside it
  at every step — is still going stale as §6.2 item 53 warned. That is R5/H3b.


---


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

### 6.2 Carry-over list after Wave 7 (rewritten 2026-09-06) — the single live list

> **Sequencing note (2026-09-06).** [`HIGH_STAKES_ACCURACY.md`](HIGH_STAKES_ACCURACY.md) re-ranks this list by *who reads the number* and supersedes its **sequencing**, not its rules or its contents; items that plan does not schedule stay open here.

**Waves 1–7 of this plan are complete, and Waves A, B and C of the high-stakes
plan have run on top of them** (§5.8, §5.9). PRs #119–#122 closed three of the six items
Wave 5 opened plus answered a fourth, and **Wave 7 (PRs #126–#132) closed seven
more** — items 8 (on direction), 15, 24, 25, 30 and 31, plus the dashboard half
of the sweep's §7.5 finding. **Waves A/B (PRs #140–#146) then closed item 37 —
both halves of it, the base growth and the AGI column — and opened items 43–54
below**, which is the shape of a wave that measured four things it did not
build. Item 37 is struck where it stands. **Wave C (PRs #148–#151) closed item 43
and the headcount half of item 15, and opened items 55–65** — again more than it
closed, and again for the same reason: three of its four lanes measured a shipped
surface before changing it, and two of them found the *plan's own diagnosis*
wrong (§5.9 findings 1 and 2). **Two of those seven closed by being disproved
rather than fixed**, which is why the list below is longer than the items it
lost: the decedent ladder was not the cause of the exclusion-step gap, and the
filing-status split made three of its four rows worse. Wave 7's own new items are
**35–42**. **Wave D and the first two lanes of Wave E (PRs #155–#162, §5.10)
closed items 3, 6, 35, 45 and 49 outright, closed two of item 38's five
magnitudes, and opened items 66–72** — which is, for once, a round that closed
about as many as it opened, because three of its seven lanes were *provenance*
lanes whose whole business is settling questions rather than finding new ones.
Note what the closures cost: items 6, 45 and 49 all closed by **withdrawing a
target**, and a withdrawal is not an answer — the rows are still there, still
scored, still reported beside a held-in-place figure. What follows replaces the Wave 3 edition of this list. None of it is a modelling lane's call to make on its own;
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

**Item 15 below — the five-class decedent ladder — is closed and its finding
reversed; see item 36 for what replaced it. The sentence that followed here is
kept for the record.** *(As written after Wave 5:)* The item is still the
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
3. ~~**The two SALT baselines still contradict each other.**~~ — **CLOSED by
   PR #161 (owner decision ⑧), and the resolution is that they are allowed to
   differ as long as each says which baseline it is.** *(Closed 2026-09-11,
   `planning/lanes/SALT_current_law_baseline.md`.)* `SaltCapBaseline` is the
   baseline-vintage concept the item says the module did not have: three named
   cap paths — `CURRENT_LAW` (the app's default), `PERMANENT_10K` and
   `LAPSED_CAP` — with the first transcribed from IRC §164(b)(6)–(7) as amended
   by **P.L. 119-21 sec. 70120**: $40,000 in 2025 indexed at the statute's own
   **101 percent** to $41,624.16 in 2029, **$10,000 flat from 2030**, and a
   **30 percent** phasedown of the excess over a $500,000 threshold indexed the
   same way, complete at $600,000 in 2025. Each benchmark scores the baseline
   **its own document was measured on** — `repeal_salt_cap` on PWBM's permanent
   cap, `eliminate_salt` on CBO Option 49's lapsed one — so **both scorecard
   rows are unchanged**, which the lane pre-registered, and the app moved
   instead: 📋 Repeal SALT Cap **+$1,155.56B → +$740.31B** with a Decision 6
   caption that names the baseline rather than only the number. Three findings
   travel with the closure. **The Tier 2 ledger refused a no-move
   re-registration and was right to** — its fifth invariant fails a supersession
   that restates its own figure — so the declaration went into
   `scenarios.SALT_SCORING_BASELINES`, inert in one commit and the scoring input
   in the next, and whether Tier 2 should grow the shape-input manifest Tier 1
   has is item 70. **An independent published anchor was in the repository
   already**: `pl119_21_salt_cap_40k` is JCX-35-25 line 20 at **+$946,209M**,
   which is sec. 70120 measured against a lapsed cap, and the new mechanism
   returns **$723.1B, −23.6%** against it. And **`salt-deduction-eliminate` is
   quoted, not scored** — a `SCORE_ONLY_ID_BY_LABEL` entry with no
   `PRESET_POLICIES` row, so Build prints CBO's −$1,621.0B as a list price and
   the engine never runs it; the current-law figure it *would* return is
   **+$337.6B**, a fifth of the quoted one. The residual terms are item 70.
4. **`annual_cost = 25.0` on the mortgage record is a pre-P.L.119-21 level.**
   JCT's JCX-45-25 puts the capped expenditure at $45.5B in FY2025 rising to
   $54.9B in FY2029 (the $40,000 SALT cap took itemising claimants from 11.8M to
   17.8M returns), while Treasury's FY2027 edition gives $23.9B falling to $14.1B
   on the *same* statute — a 2–4× disagreement driven by Treasury's
   comprehensive-income baseline against JCT's normal-tax one. Choosing between
   them is an owner decision with a visible consequence for `eliminate_mortgage`.
   Its sibling `annual_cost_no_limit` stays sourced-but-unwired, for the reason
   above.
5. **The remaining calibrated `secondhand` rows — now seven, and all of them are
   in the calibrated tier.** Fifteen before PR #122, twelve before Wave B, and
   **seven since**, with the five that left doing so by finding a document and
   never by a decision that a figure was good enough. **Wave E did not touch this
   count**: PR #162's `secondhand` reduction, 12 → 7 across both tiers, is
   **Tier 1's own 5 → 0** and nothing else, so the calibrated rows below are
   exactly where Wave B left them. Several have nothing to move *to*. The
   pre-Wave-B twelve, for the record: both Social Security payroll targets
   (OCACT publishes percent-of-payroll and no dollars), `repeal_ira_credits`,
   `trump_china_60`, `cap_charitable`, `eliminate_step_up`, `biden_ctc_2021`,
   `repeal_ptc`, `cap_employer_health`, plus `repeal_individual_amt` and the two
   Wave 4 examined and left (`steel_tariff_25`, `eliminate_mortgage`). Each needs
   the same per-target judgement `PROVENANCE_wave4.md` applied to seventeen, and
   the plan's §5 target of ≤ 6 is **one row short**, the seventh being
   `repeal_individual_amt` — a locked-holdout id with nothing to move to
   (item 2), so the last step is item 1's decision rather than a search.
6. ~~**`expand_drug_negotiation`'s −$500B and `international_reference_pricing`'s
   −$100B are `model_estimate` targets.**~~ — **CLOSED by PR #160 (owner
   decision ④): both targets are retired, the first two retirements the ledger
   has made.** *(Closed 2026-09-11, `planning/lanes/LEDGER_decisions_3_4.md`;
   the same decision is item 49, opened by Wave B and struck there too.)* The
   −$500B was the repository's own extrapolation from a figure
   `W4_pharma_part_d.md` established was never a negotiation score, and the
   −$100B was a **RAND price index** used as a budget score. **Neither row
   moved and neither was deleted**: both keep their scorecard entries, their
   model figures to six decimals and their withdrawn targets, and they report
   separately at **2 @ 397.2%**. The tier reads **37.5% over 38 scored**, which
   **must never be quoted without the 55.5% over 40 printed beneath it** — the
   same rows folded back at the error they carried on the day they were
   withdrawn, because 18 points bought by withdrawal is not a measurement. What
   the retirement genuinely bought: the reconstruction tier's `model_estimate`
   target count went **2 → 0**, so *"no row this tier reports is scored against
   this model's own output"* is true of it for the first time, and `Pharma` as a
   sub-population went **3 @ 277.8% → 1 @ 39.0%**. Two candidates remain named
   and not acted on, `carbon_tax_50` and `eliminate_step_up` — item 69.

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
8. **The expenditure module's behavioural offset — ~~direction~~ CLOSED (PR #128),
   magnitude OPEN.** *(From `W4_option56_excess_share.md` finding 3; updated
   2026-09-05 after PR #119; **direction settled 2026-09-06 by PR #128**,
   `planning/lanes/W7_expenditure_offset_convention.md`.)*

   **The direction half is done, and it did not settle module-wide, because the
   documents do not.** "One direction" was the defect rather than "which
   direction": CBO's Option 49 puts four alternatives over the same deductions in
   one table and its 2022 discussion gives them three different behavioural
   directions, and CBO's charitable option reverses its own verdict for a *floor*
   design. `TaxExpenditurePolicy` now carries a per-**reform** `direction` with
   the source sentence attached — **magnify** for Option 56, the 28% charitable
   benefit-rate ceiling, SALT elimination and SALT-cap repeal; **erode** for
   mortgage (Poterba & Sinai, NBER WP 14253: $72.4B without behaviour against
   $61.9B with, "about 85 percent"), step-up, retirement and like-kind. Four
   magnify on a document, five erode, and exactly one scored row flipped:
   `eliminate_mortgage` −$330.4B → **−$270.3B**, 10.1% → **9.9%**, with zero
   presets moved and no constant retuned. `CONVENTION_EXCEPTIONS` is now a set of
   *policies* rather than class names. The registered price: Expenditures LOO
   **35.7% → 37.5%**, the suite 29.6% → 30.1%, because the old −5.1% was two
   errors cancelling.

   **What is still open is the magnitude, and it is a different item.** All five
   `BEHAVIORAL_ELASTICITIES` values are unsourced — charitable 0.40, employer
   health 0.20, mortgage 0.10, SALT 0.05, retirement 0.30 — and two now have a
   published figure beside them: Poterba & Sinai's own **15%** against mortgage's
   0.10, and charitable's 0.40, which carries the size of a *price elasticity of
   giving* applied to a share of a revenue effect, a different quantity (the
   arithmetic of a 28% ceiling at a 37% marginal rate implies nearer 18%). PR #128
   deliberately adopted neither: reading a paper for its direction and then taking
   its coefficient would be fitting to a document the lane chose, and would move
   `eliminate_mortgage` twice in one PR. **An owner decision, and it owes a
   Decision 6 caption if it moves a shipped number.**

   **Update, 2026-09-11: PR #157 took the magnitude half and sourced two of the
   five.** Mortgage **0.10 → 0.14502762** and the charitable 28% ceiling
   **0.40 → 0.22077987**; both rows moved as registered regressions and the
   preset moved with a caption. **Three remain unsourced with their searches
   recorded — item 38, now the live half of this one.** And the "nearer 18%"
   above is **not reproducible**: the identity gives **22.1%**, and 18% would
   need `ε = 0.405`, which CRS does not print. See §5.10 finding 2.

   *The item as written before PR #128, kept for the record:*
   `TaxExpenditurePolicy.estimate_behavioral_offset` returns an offset with the
   **opposite** sign to `static_effect`, where `TaxPolicy` returns one with the
   same sign and its docstring says why — so the expenditure module *magnifies*
   where the base class erodes. **The item stands exactly as written and its
   context has changed**: it used to be one of four modules whose offset pointed
   the wrong way, and item 22's sweep signed the other six implementations, so
   this is now a deliberate exception rather than a member of a family. It is the
   single entry in `CONVENTION_EXCEPTIONS`, cited in the module's own docstring to
   CBO 60557 Option 56 — a cap makes employers offer less generous coverage
   **and** shifts compensation into taxable wages, and CBO has both channels
   raising revenue, so an offset that adds to the static effect is right *there*.
   It remains unsourced in magnitude on the other five expenditure benchmarks, and
   **its size is now measured rather than estimated: +5.0% of the static effect on
   a SALT elimination and +20% on Option 56.** The decision is still whether the
   same convention is right for `eliminate_salt`, `repeal_salt_cap`,
   `eliminate_mortgage`, `cap_charitable` and `eliminate_step_up`, where nothing
   sources it; choosing it module-wide moves every fitted expenditure row **and**
   the leave-one-out column together. An owner decision, not a lane's.
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
15. ~~**The five-class decedent ladder has no within-group dispersion.**~~ —
    **CLOSED by PR #132, and the hypothesis it rested on is disproved.**
    *(Opened from `W4_gains_at_death.md` §8.4; closed 2026-09-06,
    `planning/lanes/W7_decedent_ladder.md`.)* The ladder is gone — replaced by a
    piecewise-Pareto size distribution of net worth at death fitted to the
    Distributional Financial Accounts' own percentile-group aggregates, reading
    all three published carve-out ladders at each estate's own size and reviving
    **six of the seven published rows the five class means never evaluated**,
    including the whole $1M–$5M band both Green Book exclusions sit in. **The
    $1M → $5M step got bigger, 82.26 → 85.02**, and the direction is not an
    accident: `max(0, gain − E)` is convex in the gain, so a mean-preserving
    spread *raises* the taxable excess at every exclusion level — a sharper
    schedule makes an exclusion cost **more**. Wave 4 read a cliff in the schedule
    and inferred the cliff was the cost; the cliff was real and the cost is
    elsewhere. Three rows moved as pre-registered regressions: `cbo_opt51` 19.3%
    → **20.3%**, `biden_capital_gains_39` 31.4% → **32.8%**, the Treasury row
    43.3% → 45.4% on that branch. **The remaining substance is item 36, the
    decedent headcount.** Also still carried from the same lane and unchanged: the
    rate on the final return is priced on the *pre*-carve-out gain; the 72.3%
    active-business share is an **upper bound**; mortality is uniform in wealth
    where the wealthy are older and die at a higher rate; and the fit refuses
    below the 90th percentile, so Poterba & Weisbenner's $250,000–$500,000 class
    is still never evaluated.
16. **CBO's account-level spendout rates** (pubs 61913, 62256) as an external
    cross-check on L2. Carried from Wave 1, still blocked by cbo.gov 403s —
    **but the blocker is narrower than this item has been saying since PR #159.**
    R1's finding is that the 403 is a property of `cbo.gov` and **not** of
    `github.com/US-CBO`, which publishes the same tables as machine-readable CSV
    under a public-domain dedication, and owner decision ⑩ settled that both CBO
    repositories count as "CBO's own table". `cbo-data`'s `spending_detail` block
    carries **21,769 account-rows** and is one `--source-dir` away
    (`planning/memos/CBO_GITHUB_SURVEY_macro.md`; item 71). Whether it contains
    the *outlay rates* rather than the account levels is the question a lane
    should open with, and nobody has looked.
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

22. ~~**Sweep every module for an inverted or absolute-valued behavioural
    offset.**~~ — **done, PR #119, `planning/lanes/SWEEP_offset_sign.md`.**
    All fifteen implementations were probed at the function (`f(+100)`, `f(−100)`)
    and at the score, and **7 were against the contract**: three **inverted**
    (`AMTPolicy`, `EstateTaxPolicy`, `PremiumTaxCreditPolicy`, all three carrying
    the identical comment pair above a `return -total_offset` — one copy-paste in
    three files) and four **`abs()`-ed** (`CorporateTaxPolicy` in `reported`, the
    `TaxCreditPolicy` fallback branch, `IRSEnforcementPolicy`,
    `InternationalTaxPolicy`). AMT booked 25% more than its own static in both
    directions. Six were signed with `math.copysign`; the expenditure convention
    is item 8 and is left. The item's own claim was confirmed rather than
    disproved: **exactly one of the seven reached a scorecard row**, so the tier
    and the leave-one-out column really were blind to it, and the gate that now
    exists is `test_every_offset_implementation_is_covered` — a grep for
    `def estimate_behavioral_offset` that fails if a class is missing from the
    case list. Two shipped presets moved with a Decision 6 caption
    (Trump Corporate 15% +$1,690.6B → +$1,314.9B; Repeal ACA Premium Credits
    −$966.2B → −$790.5B), and `trump_corporate_15` and `repeal_ptc` were
    **reclassified rather than retuned**. See §5.6 findings 1 and 3.
23. ~~**The corporate module has no leave-one-out row.**~~ — **answered `no`,
    PR #120's memo §7(iii); the substitute shipped in PR #122.** LOO holds out one
    benchmark's fitted constant and asks whether the machinery calibrated on the
    *others* can put it back. The corporate module has **one** fitted constant,
    `BASELINE_TAXABLE_PROFITS_BILLIONS`, and had **two** benchmarks — one of
    which, `trump_corporate_15`, carried provenance `model_estimate`, so
    re-deriving the base from it would reconstruct the constant from itself, which
    is the leakage `LEAKAGE_TOLERANCE` exists to catch. **`loo.py` is not what was
    stopping it**, and `not cross-validatable` is the honest outcome. The honest
    substitute, which PR #122 built, is a **second published target the module is
    not fitted to**: `biden_corporate_28_fy2022`, Treasury's FY2022 Green Book row
    ($857,817M, FY2022-2031, report p. 104) — the only *rate-only* corporate row
    any Green Book prints, so it is the one published corporate target whose scope
    matches the factory's shape. It reports in the reconstruction tier at
    **−62.9%** and is **never to be fitted**, because a second constant fitted here
    would make the pair uninformative. The module now has two published benchmarks
    and one fitted constant and still nothing cross-validating either — a smaller
    gap, honestly stated, not a closed one.
24. ~~**`treasury_capgains_39_plus_stepup_elim` is scored on the wrong window.**~~
    — **CLOSED by PR #126, and the offset it quoted was wrong by 12 points.**
    *(Opened from `W5_preferential_margin.md` §8.3 finding 5; closed 2026-09-06,
    `planning/memos/FY2022_TARGET_WINDOW.md`.)* `CBOScore.scoring_window_first_year`
    now scores a case on the decade its own source published a total over; `.v1`
    superseded, `.v2` registered on **FY2022–2031** at the same −$322.0B, entry
    commit before scoring commit, `iija_2021_discretionary.v2`'s rule exactly.
    **The offset is 28.7 of the row's 43.3 points, not the ~17 this item and every
    doc quoted**: the old figure discounted the *rate* channel only
    (`359.02 × 0.844354 + 102.45 = 405.6`, reproduced to the dollar by
    `scripts/window_offset_capgains.py`), and the death channel both grows with the
    same 5.80% CAGR and does **not** grow proportionally — a uniform discount gives
    $86.5B where the re-score gives $65.8B, because a fixed nominal exclusion is a
    step function whose bite moves faster than the stock. **The window offset and
    item 15's ladder finding are the same defect seen twice.** The control
    (`biden_capital_gains_39`, same shape on its own window) has an offset of
    exactly zero. The row reads 14.6% on that branch and **18.4%** on merged main,
    because PR #132 landed in the same wave. **And this item's own last clause was
    wrong**: "the repository has no 2021 vintage either way" names a blocker that
    was never binding — neither FY2022 row reads a baseline *level*
    (`estimate_static_revenue_effect` opens with `_ = baseline_revenue`), so what
    they needed was a **window**, not a **vintage**. See item 35 for IIJA.
    Related and smaller from the same lane, still open: no receipts lag on the enactment
    year, no smoothing of the TY2023 SOI anchor (a trough), the $1M threshold
    still un-indexed, and the growth rate is a net-worth CAGR rather than CBO's
    own published realizations projection (blocked by cbo.gov 403s, item 16).
25. ~~**The AGI-surtax filing-status threshold row.**~~ — **CLOSED by PR #127:
    the mechanism exists, and three of the four rows it touched got worse.**
    *(Closed 2026-09-06, `planning/lanes/W7_filing_status_split.md`.)*
    `scripts/build_filing_status_data.py` transcribes IRS SOI **Table 1.2** and
    `IRSSOIData.get_bracket_distribution_by_status` takes only its *composition*
    onto the Table 1.1 base, so a uniform threshold reproduces the pooled path to
    the cent; `TaxPolicy.threshold_by_filing_status` is a **partial** mapping and
    `FILING_STATUS_THRESHOLD_RULE` reads a source naming two statuses the way IRC
    §1411(b) is written. `cbo_opt46_agi_surtax_1pp_20k` 44.7% → **49.8%**,
    `cbo_opt46_agi_surtax_2pp_100k` 16.1% → **37.4%**,
    `cbo_opt45_top4_brackets_2pp` 17.9% → **12.4%**, `biden_high_income_tax`
    12.0% → **9.2%** — every figure landing on the lane's hand-computed
    pre-registration, including the tier mean rising. **This item's own
    description was wrong about the direction of the approximation**: it is *not*
    uniformly generous, because the FY2025 Green Book's married-filing-separately
    floor of $225,000 is $175,000 *below* the unmarried $400,000 the model applied,
    so that base had been under-counted and the row improved. **What is left on
    the two Option 46 rows is not a filing-status question at all** — see item 37.
    One hazard the lane names for any future base-splitting work: recomputing
    `preferential_income_share` against the split denominator double-counts the
    correction and is worth eight points on Option 45's row; the shipped code
    holds it at the pooled threshold.
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
28. **~~Two~~ One classroom lock the frozen-link work deliberately did not build.**
    *(New, from PR #111; the Build half **closed by PR #134**, 2026-09-06.)*
    ~~**Build packages are not freezable**~~ — they are now:
    `/build?policies=&target=&metric=` carries the same
    `baseline=&engine=&spec=&mode=&frozen=1` lock the other surfaces use, decoded
    and refused by the same functions with no Build-specific spelling. The package
    is re-applied on **every** rerun (an ordinary `?policies=` link is a starting
    point; a frozen one is the assignment), every input renders through the
    existing disabled-widget proxy, and **the exports stay live**, because an
    export is not an edit and a student has to be able to hand something in.
    `?values=`/`?vector=` links freeze too, since `composer.select_package` is a
    pure function of tags × vector and free text is not what a URL carries; the
    emitted link resolves the philosophy to `policies=` so a re-scored catalog
    cannot recompose an assignment already handed out. Two Build-specific refusals
    were added — a `frozen=1` naming neither policies nor a philosophy, and a
    package this deployment cannot rebuild — both cases of an empty checklist
    under an instructor's banner. Tampering with `policies=` is **captioned, not
    refused**, which is the convention `spec=` already set.
    **Still open: the Data & methodology options are not pinned**, per the owner's
    stated scope (vintage, engine, dynamic, policy); they still move the number,
    which is what the spec-hash caption is for. Blue tier, so held to a UX bar
    rather than an accuracy one.
29. ~~**The cold-start measurement.**~~ — **MADE by PR #129, and it returned
    neither of the two answers the question offered.** *(Closed on its local half
    2026-09-06, `planning/memos/COLD_START.md`; the Cloud half is open below.)*
    Network is ruled out at **0.55s median**, ~3% of the observed ~20s. Import
    ordering was real and is fixed — `app.py` named a `fiscal_model` submodule at
    module scope, so **time to first paint went 1.593s → 0.022s** and
    modules-at-import 1,901 → 586, pinned by `tests/test_cold_start_ordering.py`.
    **The largest term was one nobody had looked for**: the page footer computing
    the entire 81-row validation scorecard to print one clause, **8.68s of the
    landing page's 9.38s first script run**. PR #135 then closed that on a third
    option neither candidate offered — a generated artifact, test-pinned — taking
    the landing first run **8.404s → 0.668s**. **Still open: the Cloud-sleep half,
    and no app-side work touches it.** Community Cloud apps sleep after 12 hours
    and do not wake by themselves; the visitor gets Streamlit's interstitial and
    must click it, so only (b) a warm container or (c) copy around the link
    changes anything. A sleep cannot be forced, so the measurement needs a >12h
    wait; the runbook is memo §4.1. See item 39 for the scored route.
30. ~~**`CBOBaseline`'s corporate receipts path is neither a vintage nor
    distinguishable between vintages.**~~ — **CLOSED by PR #130.**
    *(Closed 2026-09-06, `planning/lanes/FIX_baseline_corporate_path.md`.)*
    February 2024 now **is** CBO publication 59710 Table 1-1, read through
    `fiscal_model.corporate`'s own loader and reproducing its ten printed values
    exactly; the other two vintages keep the reconstruction but start from their
    **own** base year, from one map the loader and the fallback share; and
    `CORPORATE_RECEIPTS_SOURCING` grades all three `published_path` /
    `published_base_level` / `vintage_estimate`, carried in `metadata`, so a line
    this module reconstructed cannot be reported as CBO's. **Nothing scored
    moved** — all 26 out-of-sample rows, both calibrated tiers, all 81 scorecard
    entries, the LOO donor matrix, 53 presets × 2 modes × static/dynamic and 16
    Tailor combinations are byte-identical. What moved is the baseline behind the
    numbers: Ask's ten-year deficit **$30,020.7B → $29,529.1B**, end-of-window
    debt/GDP **104.8% → 103.8%**, Build's mean annual deficit $3,002.07B →
    $2,952.91B. One correction to the record it inherited: the three paths were
    not *identical*, they shared one base level and one first year and diverged
    **0.70%** by FY2035, because the growth rule reads the vintage's assumptions
    though the level does not — and stating that precisely put the cause in one
    line of the loader. **The same override is still live on the individual,
    payroll, other-revenue and spending series**, and `other_revenues` is
    byte-identical across all three vintages for all ten years — the same defect
    with no growth-rule variation to hide it. That half stays with item 16's
    blocker (cbo.gov HTTP 403, re-checked 2026-09-06, no Wayback snapshot of
    either workbook), along with `corporate_profit_premium = 0.01`, still
    unsourced and still governing the two reconstruction vintages, and
    `GDP_RATIOS["corporate_tax_to_income_tax"]`, which now has no reader.

    **Update, 2026-09-11: PR #159 closed that half for two vintages and found
    the blocker was the wrong one.** January 2025 and February 2026 now read
    CBO's own published budget and economic tables from `US-CBO/cbo-data`, so
    the individual, payroll, other-revenue and spending series are transcribed
    rather than overridden and every category matches both loader paths to the
    cent; **February 2024 keeps the reconstruction**, because `cbo-data` ships no
    `ten_year_budget` for that edition. The 403 is `cbo.gov`'s and not CBO's —
    see item 16. What is still open is that vintage's **mixed grade** (item 71),
    the `base_*` levels the transcription does not write (item 71), and
    `corporate_profit_premium = 0.01`, which now governs one vintage rather than
    two.

    *The item as written before PR #130, kept for the record:*
    `CBOBaseline.generate().corporate_income_tax` on `CBO_FEB_2024` grows at
    **4.88%/yr** — *faster* than the flat 4% PR #121 removed, and 3.4× CBO's own
    published **1.44%** — because the corporate line is a base level times
    `real GDP growth + inflation + a corporate profit premium`. Worse, under
    `use_real_data=True`, which is the app's default, it returns the **identical**
    path for all three vintages (402.1 → 614.3), because `base_corporate_tax` is
    set from an IRS-to-individual-income-tax ratio with no vintage in it. So a
    score reported as "on the February 2024 baseline" has a corporate receipts
    line that is neither February 2024's nor distinguishable from February 2026's.
    **Nothing currently reads it for a scored quantity**, which is why PR #121 read
    a transcribed CBO table instead and why this is a defect rather than a bug
    report — but it is a 🟢-tier defect, and it is the reason the distinction
    between "the vintage" and "the repository's reconstruction of the vintage" had
    to be made explicit in that module's docstrings. Not a corporate lane's to fix.
31. ~~**`repeal_ptc`'s *shape* is as much of the mismatch as its target.**~~ —
    **CLOSED by PR #131, as a registered regression.** *(Closed 2026-09-06,
    `planning/lanes/W7_ptc_repeal_shape.md`.)* **The handoff was half right**:
    what the module computed was not a baseline cost but a **fitted** annual that
    happened to total within 3.9% of one — $83.0B/yr is
    `1100 / (1.10 × Σ 1.04ᵗ)`, the carried target run backwards through the
    engine's growth factor and the inverted offset PR #119 corrected. **And it
    looked fine, which is the finding**: 3.9% on a ten-year total while being 21%
    low in FY2026 and 21% high in FY2028, because a smooth 4% ramp cannot see the
    cliff the ARPA/IRA expiry puts in the credit — and the app shows the annual
    profile, the distributional tables and the dynamic feedback off that series.
    The static path is now CBO/JCT publication **51298** Table 2's own annual
    credit cost (both legs, June 2024 and February 2026 transcribed, an
    untranscribed vintage **raising** rather than falling back) times
    (1 − **19.28%**) of offsetting effects from publication **60437**'s own
    itemisation — which also shows the unsourced 10% was in the wrong *place*, as
    CBO's itemisation carries no premium-spiral line at all. `repeal_ptc`
    −$896.9B → **−$774.1B**, 18.5% → **29.6%**, and the whole $326B is three
    published steps. **The refusal to adopt −$1,100B is now demonstrated rather
    than argued**: the same mechanism on the June 2024 vintage and window with no
    offset returns $1,143.0B against that $1,142B — **0.09%**. The target did not
    move and the row stays in `EXAMINED_NOT_REVISED`. Still open from the same
    lane: ~~`MARKETPLACE_DATA`'s uncited "19 million lose coverage" on a surface
    users see (pub. 51298 **Table 1** is now identified but only Table 2 is
    transcribed)~~ — **closed by PR #155**, which transcribed Table 1 for both
    vintages and rebuilt the coverage figures from it, so `MARKETPLACE_DATA` is
    no longer read by any scored or rendered path; its FPL distribution, average
    subsidies and benchmark premium are still uncited and still read by
    `calculate_subsidy`'s callers, which is item 67. Also still open:
    `CBO_PTC_ESTIMATES`' extension reader; `BASELINE_PTC_COSTS`,
    which is now read by nothing; no `cbo_jan_2025` block; and
    `_offset_sign_changed` still firing the sign-sweep caption on this preset with
    a counterfactual computed on a static path that never shipped.
32. **The corporate module's implied marginal base is still 80.8% of the vintage's
    own average base, where JCT reads 55.9%.** *(New, from
    `CORPORATE_PER_POINT_YIELD.md` §4b and `W6_corporate_base_projection.md`'s own
    "what the lane did not do".)* PR #121 took the window average 90.8% → 80.8% and
    removed the impossibility (a marginal base above the average base it is part
    of), but the model is still above every published estimator but Treasury: Tax
    Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury 79.5%. **Twenty of
    `cbo_opt64`'s sixty-two points were a vintage problem; the remaining
    forty-four are not.** They are credit **carryforwards** under §38(c) and
    §904(c) — which CBO's 2018 Option 24, the only volume with a narrative, states
    *is* inside JCT's estimate — **CAMT**, which begins in TY2023, after the last
    SOI year on file, and the individual-side dividend interaction. Each needs a
    quantity no source this module reads publishes (the carryforward stock is in
    the Form 3800 and Form 1118 statistics, which is a data-acquisition item), and
    **a lane that asserts a share instead of deriving one has failed even if the
    row lands.** The number that *would* land it — a total factor of 0.5785
    against JCT's own steady-state 0.590 — is printed by
    `scripts/corporate_yield_reconciliation.py` and was deliberately not approached.
33. **Decision 1's corporate flip: rule says flip, owner kept `reported`.**
    *(Decided 2026-09-05; from `PROVENANCE_corporate_ptc.md` §7, the merge that
    re-pinned it, and PR #124.)* Measured on the merged tree, where both PR #121's
    base projection and PR #122's moved targets apply, the corporate module reads
    **reported 62.75% against derived 61.43%** on three published targets —
    derived leads, narrowly, by winning the FY2022 rate-only row and losing a
    little on the other two. By Decision 1's own words the module was due to
    flip, and the flip was built, pre-registered and opened as **PR #124** (its
    lane doc, `DECISION1_corporate_mode.md`, lives on that branch; every moved
    preset, Tailor and Ask figure landed on its prediction; the revert is one
    constant). **The owner closed it unmerged**, for a reason the rule does not
    see: on this benchmark set the mean cannot discriminate. Derived wins one row
    of three; rows one and two are the *same reform on the same window* with
    published targets 57% apart, so one model number is scored against both and
    "winning" means sitting lower, not tracking a vintage; row three is missed by
    more than 100% in both modes. Flipping would also have left
    `biden_corporate_28` a fitted row scored by a path with nothing fitted in it —
    the repo names three mechanisms for moving a row out of the fitted tier and a
    mode flip would be a fourth with no rule. **`CORPORATE_APP_MODE` stays
    `reported`. Revisit trigger:** a rate-only published 28% score on a vintage
    the repository carries, or a second published Trump-15% figure that narrows
    the range. Two cautions stand: neither figure is small, and the comparison has
    reversed three times in four PRs — twice because a row whose target was the
    model's own output moved. Carry the per-row table beside the mean, never
    instead of it.
34. **A `retire` state for `target_revisions.py` was deliberately not built.**
    *(New, from `PROVENANCE_corporate_ptc.md` §3.)* PR #122's brief allowed for one
    if no published 15% corporate score existed; **two do** (PWBM's −$595B and Tax
    Foundation's −$673.1B), so the row took a range instead and the mechanism would
    have shipped with no user. `EXAMINED_NOT_REVISED` already covers "opened and
    left". What the ledger still lacks is a way to record "**this target should not
    exist and nothing replaces it**" — distinct from both a supersession and an
    examined-and-left — and nothing in the repository needs that today. Recorded so
    the next lane does not re-derive the question rather than because it is due.
35. ~~**IIJA's window: the same mechanism that closed item 24, and it was
    deliberately not applied.**~~ — **CLOSED by PR #160 (owner decision ③): the
    rule is now applied to both rows.** *(Closed 2026-09-11,
    `planning/lanes/LEDGER_decisions_3_4.md`.)* `iija_2021_discretionary.v3`
    carries `scoring_window_first_year = 2022` and is priced on **FY2022–2031**,
    the ten fiscal years CBO's own estimate covers, at the **unchanged**
    +$415.448B target — `treasury_capgains_39_plus_stepup_elim.v2`'s rule
    exactly, a new row rather than an edit, entry commit before scoring commit.
    The row goes **+$339.98B / 18.17% → +$414.29B / 0.28%** and its class,
    enacted-law spending, **13.4% → 7.4%** with mass 40.2 → 22.3. The item's
    prediction of "another 0.7pp" off the tier mean was right: 14.5% → 13.8%
    before R1 and R2 touched it. **Three things the closure established that the
    item did not.** **0.3% is two terms nearly cancelling**: the authority path
    outlays **$434.1B against $415.4B, 4.5% high**, while **$19.8B** falls in
    FY2032 or later, so the residual is smaller than either term and reading it
    as evidence about the spend-out profile would repeat the error the Treasury
    row's 0.2% made. **Within-25 did not move**, 22 → 22, because the row was
    already inside the band at 18.2% — *improving a row already inside a band
    moves only the tighter count*. And **the old figure was stale in four places
    and did not reconcile with its own arithmetic**: `known_limitations`,
    `preregistered.py` and `docs/VALIDATION.md` all said $433.2B, 4.3% high,
    "the profile's 0.973 spend-out sum applied to the full authority", but
    `0.973 × $446.306B = $434.26B`; the measured figures are **$434.1B**,
    **0.9727** and **4.5%**, with a **$19.8B** tail rather than $18.9B. Nothing
    scored reads any of them, which is exactly why a $0.9B drift survived three
    waves. *Original text below.*
    <br>*(As written after Wave 7:)* *(New, from `planning/memos/FY2022_TARGET_WINDOW.md`
    §6 item 4 — **an owner decision**.)* `iija_2021_discretionary` reads **18.2%**
    because **$92.6B** of its authority path outlays in FY2022–2024, before the
    model's FY2025–2034 window opens. On its own FY2022–2031 decade it scores
    **+$414.3B against +$415.4B, 0.3%**. `CBOScore.scoring_window_first_year` now
    exists and the supersede rule is the one PR #126 used, so this is a `.v3` row
    and nothing else — but **a lane may not take a second target decision by
    implication**, which is why the number is published here rather than banked.
    Two things the owner should weigh: the tier mean would fall by another 0.7pp,
    and a rule applied to one row and not the other is worse than a rule applied
    to neither.
36. ~~**The decedent headcount — what item 15 turned out to be.**~~ — **CLOSED by
    PR #151** (`planning/lanes/HSC_h5_decedent_headcount.md`), and **two of the
    three quantitative claims below did not survive it**. The count is now
    `death_exit_rate()`'s own 2.647%/yr — **3,384,194** decedents against 408,532
    — with the $196.2097B level untouched; `cbo_opt51_gains_at_death` **20.3% →
    35.5%** as the registered regression this item predicted,
    `biden_capital_gains_39` 32.8% → 27.0%, the Treasury row 18.4% → 1.8%, the
    class 20.5% → **18.7%**. What did **not** survive: **"about twice the shipped
    count reproduces Treasury's step"** — 8.3× the count takes the $1M → $5M step
    to **$9.40B** against Treasury's $33.4B, through the figure and out the other
    side; and **"start at the top", because grading the rate by estate size runs
    the wrong way** — the wealthy are older, so a size-graded rate is *higher* at
    the top (2.8400% against 2.6468%) and takes the implied top count to 38,908
    where the uniform swap takes it to 36,262, both further from SOI's 7,194. The
    SOI comparison also needs a unit before it is a comparison (individual
    decedents over a gross estate vs households over net worth). The **level**
    half is open as item 55 and points the other way; the universe question is
    item 61. Original text below.
    <br>*(As written after Wave 7:)* *(New, from
    `planning/lanes/W7_decedent_ladder.md` §8.4 and finding 2.)* The shipped count
    is `households × household_share × estate_flow_rate`, where **`estate_flow_rate`
    is Poterba & Weisbenner's *dollar* flow of estates over net worth (0.3195%/yr)
    used as a *headcount* rate** — 408,532 decedents a year against roughly
    **3.09 million** NCHS deaths. Holding gains at death at PW's flow and varying
    only the count: ×1.5 takes the $1M → $5M step 85.02 → 53.11, ×2 → 35.46,
    ×7.56 (≈ NCHS) → 9.94, so **about twice the shipped count reproduces
    Treasury's own step to within two billion**. The candidate replacement is
    already in the tree and unused in this channel:
    **`mortality_weighted_net_worth_share` at 2.65%** in
    `accrued_gains_parameters.csv`, derived from NCHS mortality against DFA net
    worth by age. **Two cautions.** It is a **level** change to the whole channel
    and moves `cbo_opt51_gains_at_death` in the *wrong* direction, so it is an
    owner decision about `estate_flow_rate` rather than a dispersion lane's. And
    it is **not uniform**: the implied count above $12.92M is **4,378** against
    SOI's **7,194** estate-tax returns, short by 1.6× where the total is short by
    7.6×, so a fix that scaled every group equally would overshoot the top while
    correcting the middle. Start there. Related from the same lane: **$33.4B was
    never the right comparator**, because Treasury's two rows sit on different
    windows on different baselines and the model's own death channel is 0.714× as
    large on FY2022–2031 as on FY2025–2034 for the $1M design, so any
    common-window restatement makes the published step larger.
37. ~~**Option 46's AGI base and the generic base's growth rate — what item 25
    turned out to be.**~~ — **CLOSED, both halves, by Waves A/B (PRs #144 and
    #146; see §5.8).** The two Option 46 rows read **7.4%** and **−2.9%**. Both
    of the lane's own predictions were right about *direction* and wrong about
    *size*, and the record below is left standing because the arithmetic that
    corrects it is worth keeping beside it: the AGI step is worth **1.4052** and
    **1.2535** inside the filing-status split rather than the pooled 1.3820 and
    1.3094 this item sized it with, and the growth step alone gave 34.1% and
    17.9% rather than the 9.1% and 1.0% (b) predicted — because those figures
    embedded (a) as well. The five-rows-for-one-reason worry in (a) was right and
    was answered per source: **three of the six moved and three did not**, and
    `medicare_surcharge_2pp`'s base turned out to be **neither SOI column**. The
    original text: *(New, from `planning/lanes/W7_filing_status_split.md`
    finding 1.)* With the filing-status split built, the two Option 46 rows read
    **49.8%** and **37.4%**, and the lane measured the whole of what is left in
    two terms it declined to take. **(a) The AGI base.** Both rows carry
    `agi_inclusive_base=True` and are scored on a *taxable-income* aggregate where
    CBO's own option text says AGI: worth about **−20%** of base, taking the rows
    to 29.4% and 21.6%. SOI publishes both columns and the loader already carries
    both, so the change is small — but `agi_inclusive_base` is also set on
    `medicare_surcharge_2pp` (1.5%), `illustrative_top_rate_5pp` (7.4%),
    `illustrative_500k_2pp` (8.9%) and `warren_ultramillionaire_surtax_3pp`
    (19.0%), **none with a filing-status boundary and three currently under 10%**,
    so a lane taking it would move five rows for one reason. **(b) The base's
    growth.** The generic path holds the SOI aggregate flat at tax year 2023
    across a decade in which CBO's own baseline grows nominal GDP **28.8%**
    (3.878%/yr); adding it takes the two rows to **9.1%** and **1.0%**. It moves
    **every** Generic row in the tier, several a long way. Each is its own lane
    with its own pre-registration, and neither is a filing-status question.
38. **~~The five~~ Two of the five expenditure elasticity magnitudes are
    sourced; three are not.** — **HALF-CLOSED by PR #157**, 2026-09-11,
    `planning/lanes/HSD_h7_expenditure_magnitudes.md`. *(Opened from
    `planning/lanes/W7_expenditure_offset_convention.md` finding 5 — the open half
    of item 8, recorded separately because the direction half is closed.)*

    **Sourced, through a new per-reform `OFFSET_MAGNITUDES` table** —
    `BEHAVIORAL_ELASTICITIES` keeps all five as the documented fallback:
    mortgage repeal **0.10 → 0.14502762**, which is `1 − 61.9/72.4` from Poterba
    & Sinai (NBER WP 14253 §6.1, Table 8, the paper's own "about 85 percent");
    and the charitable 28% benefit-rate ceiling **0.40 → 0.22077987**, the
    module's own recapture identity evaluated at `c = 0.28` on the SOI Table 2.1
    distribution already in the tree, the only new constant being **ε = 0.5 from
    CRS R40518** (band 0.1 / 0.5 / 0.79). **The shipped 0.40 inverts to
    ε = 0.906, above the top of that band**, so the module had been assuming a
    giving response 15% above the literature's high case rather than confusing
    two quantities by a factor. Both rows moved as pre-registered regressions
    (`cap_charitable` 0.3% → **12.5%**, `eliminate_mortgage` 26.5% → **30.2%**),
    Expenditures LOO went **40.6% → 43.6%** and the suite 35.7% → 36.5%, and one
    preset moved with a Decision 6 caption.

    **Still unsourced, each with its search recorded in that lane's §1 so nobody
    repeats it: employer health 0.20, retirement 0.30, SALT 0.05.** That is
    item 66, which also carries the two secondary findings this item used to end
    on. **A related decision the earlier lane surfaced and left alone**: three of
    the module's six fitted constants were fitted so the *static* path hits the
    target and three so the *magnified* score does, so on the three static-fitted
    rows the convention was carried as pure error (10.1%, 5.0%, 5.1%). Re-fitting
    them is what §1.1 forbids; a lane that does it owes a Decision 6 caption —
    and PR #157 demonstrated the alternative, **reclassifying `cap_charitable`
    rather than retuning it** when its constant turned out to be fitted to a
    quantity the module no longer computes (§5.10 finding 2; the fifth mechanism
    for leaving the fitted tier).
39. **`_scorecard_index`'s cost on scored routes.** *(New, from
    `planning/memos/COLD_START.md` §5.4.)* PR #135 took the *landing* page's first
    script run from 8.404s to 0.668s by pinning the footer's count as a generated
    artifact, and the **scored** route is unchanged at ~**10.6s** — which is a
    finding rather than a miss. Instrumented with a stack capture, a scored run
    has exactly one call over half a second: **6.555s** arriving at
    `preset_validation.get_validation_badge → _scorecard_index` from
    `policy_input_tax.render_tax_policy_inputs`. **An artifact of counts cannot
    serve it**, because the per-preset accuracy badge needs each row's model
    figure, official figure, rating and source URL — and pinning model *outputs*
    would be a far larger claim than pinning how many rows exist. What closes it
    is making the scorecard itself fast: ~**93,000** pandas `iterrows` calls under
    the Wave 2 L1 capital-gains path (`data/capital_gains.py`,
    `policies_core.py`). A 🟢-tier performance question, not a UX one, and it also
    removes the 5.8s a cold process pays whenever the artifact is unavailable.
40. **The preset-sweep script reports a window it is not scoring.** *(New, from
    `planning/lanes/W7_ptc_repeal_shape.md` finding 5.)* `SWEEP_offset_sign.md`
    §7.3 and `L8_tariffs.md` §7.5 both describe their 53-preset sweeps as scored on
    the app's **FY2026–FY2035** window; both call `FiscalPolicyScorer()`, whose
    `start_year` defaults to **2025** rather than to `APP_DEFAULT_START_YEAR`, so a
    policy starting in 2026 is scored over **nine** years where the app scores ten.
    It changed no conclusion in either lane — the other 52 presets are unchanged on
    both windows — but the PTC preset's own move reads +14.3% on the sweep's window
    and **+13.7%** on the one a user sees, and **a sweep that reports a window it
    is not scoring is worth fixing before the next lane quotes it.**
41. **`.gitignore`'s bare `data/` line makes ruff skip `fiscal_model/data/`.**
    *(New, from `planning/lanes/W7_decedent_ladder.md` §8.8 item 6 — found, not
    fixed.)* Line 89 of `.gitignore` is a bare `data/`, and ruff's
    gitignore-respecting traversal applies it **at any depth**, so
    `python -m ruff check fiscal_model/ …` — the command CI runs — silently skips
    the whole package, `capital_gains.py` included. Checked by explicit path it
    flagged real findings in that lane's own new code, which were fixed. **Widening
    the gate is a repo-wide change with an unknown blast radius** and is not a
    modelling lane's to make; it needs an owner and its own PR.
42. **The stale `known_limitations` and `notes` text on the FY2022 Treasury row.**
    *(New, from `planning/memos/FY2022_TARGET_WINDOW.md` §6 items 1–3 — a `.py`
    edit belonging to the capital-gains lane, deliberately not taken by the memo
    or by the docs sync.)* Three strings in `fiscal_model/validation/` are now
    superseded by things the repository has since established. (i)
    `validation/core.py`'s `_KNOWN_LIMITATIONS_BY_POLICY_ID` still says the window
    is worth "about 17 of the row's 43 points" and quotes **$405.6B**; it is
    **28.7 of 43.3**. (ii) The record's own `notes` say the row "necessarily
    receives the same prediction" as `biden_capital_gains_39` "being the same
    policy shape" — false since **Wave 4**, which gave the two rows their
    documents' different per-donor exclusions, and doubly false since PR #126 gave
    them different decades. (iii) One comment in
    `test_the_two_green_book_rows_carry_their_own_documents_exclusions` says "the
    exclusion is the only thing that separates them"; the calendar year now
    separates them too. All three pass or are inert; none is a scored quantity.

43. ~~**Five preset labels quote a figure the ledger has superseded, and two more
    were mis-signed.**~~ — **CLOSED by PR #148** (`planning/lanes/HSC_label_figures.md`).
    Six labels were renamed onto their row's current published target and two
    signs corrected, with **zero numbers moving**;
    `_LABELS_QUOTING_A_SUPERSEDED_FIGURE` went **5 → 0** and the invariant now
    runs against all **40** figure-carrying labels with no exemptions. The
    unpredicted part is worth keeping: `🌱 Repeal IRA Clean Energy Credits
    ($783B)` was not quoting a *superseded target* at all — −783.0 is
    `model_10yr_billions`, so the app was printing **its own output** in the slot a
    published score occupies, a third mechanism for the class of defect #119 and
    #122 each found once. Two spillovers became items 56 and 57. Original text
    below.
    <br>*(As written after Wave B:)* *(New, from
    `planning/lanes/HSB_h9_provenance.md` §8.5 and
    `planning/lanes/HSA_h1_base_rule.md` finding 5.)* Labels are `CBO_SCORE_MAP`
    keys, so renaming one under a sibling lane is the collision Wave A's
    file-disjointness exists to prevent, and H9 could not take them:
    `💰 SS Donut Hole $250K (-$2.7T)` now scores against **−$1,426.8B**,
    `🏠 Eliminate Estate Tax ($350B)` against **+$407.2B**,
    `📋 Eliminate Mortgage Deduction (-$300B)` against **[−$495.0B, −$367.9B]**,
    `🏭 Trump 60% China Tariff (-$500B)` against **−$650.0B**, and
    `🌱 Repeal IRA Clean Energy Credits ($783B)` against **−$851.0B**. They are
    declared in `tests/test_target_revisions.py::_LABELS_QUOTING_A_SUPERSEDED_FIGURE`
    with a test that fails if a sixth joins. **Two more are a different defect
    H1's own label invariant found**: `🌱 Repeal IRA Clean Energy Credits ($783B)`
    and `⚡ Repeal EV Credits ($182B)` print a **positive** figure for policies
    whose `CBO_SCORE_MAP` `official_score` and model output are both negative —
    the same class of error as the `repeal_corporate_amt` sign H6 fixed, which
    read a $220B *saving* where JCT, the target and the model all read a $220B
    cost. A rename lane owns `app_data.py`, `preset_ids.py` (adding
    `LEGACY_LABEL_ALIASES` so pasted share links resolve, ids untouched),
    `ui/preset_validation.py` and four tests, in **one** commit.
44. **`AGI_BASE_RULE` belongs on `CBOScore`, not beside it.** *(New, from
    `planning/lanes/HSB_h2b_agi_column.md` §1.6 and §6.7.)* Which SOI column a
    record reads is transcribed from its own source's sentence and currently
    lives in a module-level mapping keyed by the same three policy ids the record
    already carries `agi_inclusive_base` for. It belongs as a field beside that
    flag, so a new record cannot be registered without stating its column — but
    `cbo_scores.py` was H9's file in the same wave, and moving a record's schema
    under a provenance pass is the collision the sequencing prevents. One field,
    one migration, one invariant.
45. ~~**Four Tier 1 targets are rules of thumb with no source URL, and two of them
    score the same reform.**~~ — **CLOSED by PR #162: one superseded, three
    retired, and a fifth row retired beside them.** *(Closed 2026-09-11,
    `planning/lanes/R2_tier1_secondhand_targets.md`.)* The lane bound itself to
    the rule before opening a document — **revise, examine-and-leave, or retire;
    never re-shape a row to fit what the document turns out to say** — and took
    all five of Tier 1's `secondhand` targets in one pass. **Superseded**:
    `illustrative_1pp_all.v1`'s −$960.0B → CBO publication **58164**, *Options
    for Reducing the Deficit: 2023 to 2032, Vol. I*, Option 13 alternative 1,
    **−$1,081.3B** over FY2023–2032 (report p. 72, *"Data source: Staff of the
    Joint Committee on Taxation"*, which is the attribution the rule of thumb had
    claimed without a document) — the row 24.5% → **14.3%** merged. **Retired,
    with the search recorded**: `warren_ultramillionaire_surtax_3pp` (TPC's *AGI
    Surtax Options* is thirteen tables and **every one is a 10 percent
    surtax**, and the Ultra-Millionaire Tax Act is a **wealth** tax on net worth,
    so the reform this row scored has never been proposed by anyone — *no search
    could have found that target*); `medicare_surcharge_2pp` (Treasury prints the
    proposal at **1.2pp** and **$403,790M**); `illustrative_top_rate_5pp` and
    `illustrative_500k_2pp` (both call themselves "Illustrative" in their own
    records, and the *Options* volumes are deficit-**reduction** menus carrying
    no rate cut at all in four editions). **Tier 1 `secondhand` 5 → 0**, and the
    tier is 26 rows → **22** with the gates re-derived 20/22 → **15/19**.
    **The medicare row is the demonstration that the rule is about documents**:
    the model's −$408.6B is **1.2%** from the figure Treasury actually prints, so
    adopting it would have turned the tier's third-worst row into one of its best
    in a line of diff — and it was not adopted, because the model applies 2pp
    where the document applies 1.2pp. Restated on Treasury's own rate the model
    reads **39.3% under**, worse than the 31.8% the row had been reporting, so
    **the retirement raised the tier's honest error while lowering its mean.**
    What is left is item 72 (a `medicare_surcharge_2pp.v2` at −$403.8B on a
    `rate_change=0.012` shape) and R3, which owes this tier the rows it lost.
    *Original text below.*
    <br>*(As written after Wave B:)* *(New, from `planning/lanes/HSB_h2_base_growth.md`
    finding 3 and §7 owner item 2.)* `illustrative_1pp_all` (−$960.0B, note:
    *"Rule of thumb: 1pp ≈ $85-100B/year"*), `illustrative_top_rate_5pp`,
    `illustrative_500k_2pp` (both "Illustrative estimate") and
    `warren_ultramillionaire_surtax_3pp` (a bare `taxpolicycenter.org` domain).
    `illustrative_1pp_all` and `cbo_opt45_all_rates_1pp` are **the same reform**
    against targets **23.5% apart**, so the model cannot agree with both and Wave
    B swapped which one it agrees with (+4.1% → −24.5% on the rule of thumb,
    +22.4% → **−1.9%** on CBO's printed option). Three of the four are now in the
    tier's top eight. This is a **target** decision — revise, examine-and-leave,
    or retire — with `preregistered.py`'s supersede rule and the retired-row
    protocol both already built for it. H9 was in the same wave and deliberately
    took none of it.
46. **`DistributionalEngine` ignores `ordinary_income_base`, so one policy object
    yields a revenue score and a who-pays table about 2.57× apart.** *(New, from
    `planning/lanes/HSA_h1_base_rule.md` finding 11.)* At a $400,000 threshold
    the synthetic table totals $50.0B/yr against the scorer's $19.4B/yr. Nothing
    shipped is wrong today — the seven published distributional benchmarks are
    scored on their own registered universes and the dashboard's distributional
    block is character-identical across H1 — but a user reading a score and a
    table off one run is reading two bases.
    `test_the_distribution_engine_does_not_read_the_income_base` **asserts the
    divergence exists** and fails with instructions when someone closes it.
    Closing it moves who-pays tables, so it is a lane with its own
    pre-registration.
47. **The payroll module stamps a flat annual where both published paths ramp.**
    *(New, from `planning/lanes/HSA_h13_payroll_targets.md` §6.4, and now with a
    document to be fixed against.)* CBO's annual path for the $250,000 donut runs
    **$122.0B in 2026 → $192.0B in 2034** as the taxable maximum grows toward the
    threshold and the hole closes; OCACT's own E2.5 income-rate change ramps the
    same way, 1.85% → 2.50% of payroll. `create_ss_donut_hole` stamps a flat
    **$270B/yr**. Held to CBO's own ten-year total, a flat annual is **17.0% high
    in FY2026 and 25.7% low in FY2034**. That is `create_repeal_ptc`'s defect
    (PR #131) in a second module, and since PR #145 the row has a published path
    to be fixed against. E2.1's path *is* nearly flat, so this belongs to the
    donut alone. It moves a shipped headline and owes a Decision 6 caption.
48. **`get_confidence_context` has no caller in the tree.** *(New, from
    `planning/lanes/HSA_h6_no_headline_without_row.md` §5.3 finding 1.)* The
    plan's §1.3(d) correctly describes a defect on a function nothing renders —
    one definition, zero call sites. H6 keyed it to the tier so wiring it later is
    safe, and says plainly that this is not a shipped improvement. Either wire it
    into the result surface or delete it; a tier-correct string nothing renders is
    not a fix.
49. ~~**Owner decision ④: the two pharma targets.**~~ — **DECIDED and executed
    by PR #160: both retired.** *(Closed 2026-09-11,
    `planning/lanes/LEDGER_decisions_3_4.md`; the mechanism half is item 6, and
    the two figures the item predicted are the two the tier now prints —
    **37.5% over 38 scored** against **55.5% over 40 held in place**, printed one
    line under the other so that quoting the smaller figure requires skipping a
    line.) `test_nothing_is_retired_yet` was **inverted** into
    `test_exactly_the_two_targets_the_owner_withdrew_are_retired`, which pins the
    retired set in both directions and asserts each row states a reason, keeps its
    withdrawn figure and keeps a scorecard entry; a companion asserts the retired
    set is disjoint from `EXAMINED_NOT_REVISED`. **The two further candidates the
    item names are still named and still not acted on** — `carbon_tax_50` and
    `eliminate_step_up` — and are carried as item 69. *Original text below.*
    <br>*(As written after Wave B:)* *(Carried forward from
    `planning/lanes/HSB_h9_provenance.md` §8.7, now with the machinery built.)*
    `expand_drug_negotiation`'s −$500B is this repository's own extrapolation from
    a figure `W4_pharma_part_d.md` finding 2 established was never a negotiation
    score, and `international_reference_pricing`'s −$100B is a **RAND price index**
    used as a score. The lane recommends retiring both, and writes out the exact
    one-commit edit. **The reason it is an owner call rather than a lane's**:
    retiring them takes 93.3% and 701.0% out of the reconstruction tier and leaves
    it at about **36.7%** — 18.5 points of "improvement" bought by deletion, which
    §5 of the high-stakes plan forbids — so the state is built to keep the rows
    visible and print a held-in-place second reading. Two further candidates are
    named and not acted on, `carbon_tax_50` and `eliminate_step_up`.
    `tests/test_target_retirement.py::test_nothing_is_retired_yet` is the guard.
50. **`carbon_tax_25` and CBO Option 73 are an unregistered pair.** *(New, from
    `planning/lanes/HSB_h9_provenance.md` §8.9 and
    `planning/lanes/HSA_h1_base_rule.md` finding 5.)* CBO's Option 73 alternative
    1 scores **$919.3B for $25/ton rising 5%** on this repository's own window,
    with the climate module's exact escalator, and `climate.py` carries a
    `carbon_tax_25` scenario at an unsourced −$1,000B that **is not a scorecard
    row at all**. Registering it changes the scorecard population, which is a
    bigger move than a target or a verdict. The shipped preset's struck label had
    claimed −$1.0T on a window neither CBO's −$865B (FY2023-2032) nor CRFB's $960B
    (FY2026-2035) supports.
51. **`fiscal_model/ui/__init__.py` imports the whole validation package,
    eagerly.** *(New, from `planning/lanes/HSB_h3a_corporate_range.md` finding 2.)*
    Importing *anything* under `fiscal_model.ui` — `styles` as readily as
    `dependencies` — puts all **22** `fiscal_model.validation.*` submodules in
    `sys.modules` through the package `__init__`'s re-export chain, so a module's
    own lazy import is a property of the file and not of its package. Adjacent to
    `planning/memos/COLD_START.md` and item 39, and a different owner from either.
    `test_ui_package_init_is_the_eager_one` records the fact so the AST-level
    purity test cannot be quietly satisfied by the package doing the import
    instead.
52. **Build and Ask produce corporate numbers with no estimator range beside
    them.** *(New, from `planning/lanes/HSB_h3a_corporate_range.md` §6.5.)*
    PR #143 ships the four-house range on every headline corporate run, and two
    surfaces do not get it. `deficit_target.build_catalog` is driven by
    `CBO_SCORE_MAP`'s `official_score`, so a Build package quotes a **list
    price** — `trump_corporate_15`'s own published range [+595.0, +673.1] most
    obviously — and needs a differently-worded sentence, because the surface shows
    a target rather than a score. `assistant/tools.py`'s
    `score_hypothetical_policy` and `benchmarks.candidate_anchors` produce
    corporate answers with no range at all, and `candidate_anchors` in particular
    **interpolates across `KNOWN_SCORES` corporate-rate records**, which is
    exactly where a per-point yield belongs.
53. **H3a's measurement is an input to owner decision ⑤ and should not go stale.**
    *(New, from `planning/lanes/HSB_h3a_corporate_range.md` §6.3 finding 4 and
    §6.4.)* Run through the engine in both modes, **at the +7pp step every shipped
    preset uses `derived` lands *inside* the published span (76.1% marginal share
    against a published 55.1-79.5%) and `reported` lands outside it** (82.3%,
    above all four houses at every step). That is a second, independent metric
    pointing the same way as PR #122's Decision 1 reversal (reported 62.75%
    against derived 61.43%). A shipped range therefore makes the `reported`
    default *more* visibly the outlier, not less: the caption reads "larger than
    any of the four" on every corporate run the app serves for as long as the
    default stands. Neither the lane nor this list decides it —
    `CORPORATE_APP_MODE` is the owner's explicit override — but the question
    should be taken **with both readings side by side**, and H3b (Wave E) moves
    `derived` again.
54. **The leave-one-out CI ceiling is now about twice its live mean.**
    *(New, from the Wave C docs sync; figure refreshed 2026-09-11.)*
    `validation-dashboard.yml` runs
    `run_loo.py --donor-matrix --max-mean-error 75`, and its comment derives 75
    from "the observed aggregate mean (~59%) × 1.25". The live aggregate is
    **36.5%** since PR #157's sourced magnitudes took `Expenditures` 40.6% →
    43.6% (it read 35.7% when this item was written), so the derived ceiling is
    in the mid-40s either way. Tightening needs no reason under the workflow's own rule.
    It was left alone here because this sync's brief scoped the re-derivation to
    the Tier 1 gate and the new per-class floor, and because the suite's mean is
    currently moving on **targets** rather than derivations — the ceiling should be
    re-derived once, deliberately, rather than chased down after every provenance
    pass.
55. **The *level* half of the capital-gains death channel, which points the
    opposite way from the half Wave C took.** *(New, from
    `planning/lanes/HSC_h5_decedent_headcount.md` §7 and §8.7 finding 1.)*
    `gains_at_death_share_of_net_worth` is `estate_flow_rate ×
    gain_share_of_estates` — the **same** Poterba & Weisbenner dollar flow PR #151
    removed from the headcount. Held against the module's own `death_exit_rate`,
    that flow implies **0.372% of the accrued-gains stock** where the stock's
    death exit is priced at **2.647%**, a factor of **7.1**. Some of the gap is
    real and sourced — PW's flow already excludes inter-spousal transfers, the
    convention every realization-at-death proposal uses — and **nobody has
    measured how much**. It matters because it points the other way from H5:
    `cbo_opt51_gains_at_death` **under**-predicts at 35.5%, so a larger level
    would close what the headcount opened. A lane that raises the count without
    the level has registered exactly half of a two-sided correction, and 35.5% is
    the price of the half. It is a **level nobody may change by implication** —
    the same class of decision owner item ⑥ was.
56. **Seven of twelve curated Build packages state a total that no longer equals
    the sum of their members.** *(New, from
    `planning/lanes/HSC_label_figures.md` finding 6.)* Recorded in
    `policy_packages.py`'s docstring and deliberately **not corrected**. The
    outlier is *Carbon Tax + IRA Repeal* at **−917** against members summing to
    **−2,551**: −917 is −1,700 + 783, booking the IRA repeal as *increasing* the
    deficit — the same sign error that lane found on the `ira-clean-energy-repeal`
    label, in a second place. Not fixed because `ui/tabs/package_builder.py` is
    the only reader and is dead code (CLAUDE.md says so), and rewriting twelve
    list prices is a decision about figures that a label lane may not take by
    implication. Whoever takes it should decide first whether the packages are
    revived or deleted.
57. **Two `official_source` fields contradict their own ledger row, and both
    reach the scorecard column and the API.** *(New, from
    `planning/lanes/HSC_label_figures.md` finding 7.)* `scenarios.py` credits
    `trump_china_60` to the **Tax Foundation** where the Wave B revision reads
    **CRFB**, and `repeal_ira_credits` to a **CBO publication the revision's own
    note says does not exist**. Outside the label lane's file boundary, and a
    one-commit provenance fix with a test — a source string that disagrees with
    the ledger is the same defect class as a label quoting a superseded figure,
    one layer down.
58. **The accuracy band is symmetric and the errors are not.** *(New, from
    `planning/lanes/HSC_h4_empirical_bands.md`.)* Five of the six AGI-surtax rows
    over-predict; all four ordinary-rate rows crossed direction in Wave B. A
    signed band would say more than a symmetric one, and building it needs a rule
    for what a two-row class's direction means — with n = 1 in two classes, the
    honest answer may be that it has none. Not a presentation fix: it is a
    question about what the Tier 1 distribution supports.
59. **35 of the 53 shipped presets have no measured out-of-sample accuracy at
    all.** *(New, from `planning/lanes/HSC_h4_empirical_bands.md`.)* PR #149 makes
    that visible rather than papering it — every tariff, pharma, international,
    enforcement and climate preset, plus TCJA, the estate presets, the credits and
    the AMT presets, now prints **no band and the reason**, with its own scorecard
    row's error and tier beside the absence. **No presentation lane closes it**;
    widening the routing would only restore the defect PR #149 removed, which was
    `Generic` — the whole Tier 1 tier — being drawn for policies with no Tier 1
    row. H10 (Wave E) is the only lane that moves the number.
60. **`app_pages/about.py` and `fiscal_model/assistant/tools.py` still quote a
    stale "~5% / ~8%" accuracy pair.** *(New, from
    `planning/lanes/HSC_h4_empirical_bands.md` finding 8.)* The same two figures
    PR #149 removed from the result surfaces — "(~5% mean error)" and "~8% mean
    error" against live readings of **1.5% over 16 fitted rows** and **14.5% over
    26 out-of-sample rows spread 4.6–44.5%** — survive in a page with its own
    voice and in an **LLM system prompt**, where the model repeats them. The
    assistant one matters most and is the one this repository cannot test from
    here: closing it needs a live `scripts/smoke_ask_assistant.py` run. Neither
    should be replaced with a fresher number — a figure typed into a static string
    is stale by the next wave and is still one number over eight classes.
61. **The decedent universe is an open owner question, and two of its three
    candidates score better than the authorised one.** *(New, from
    `planning/lanes/HSC_h5_decedent_headcount.md` §7 and §8.7 finding 3.)* PW's
    flow measures **non-spousal** estates, a universe *smaller* than all deaths,
    while the authorised swap puts 3,384,194 decedents against roughly 3.09
    million NCHS deaths — 9.5% over. Measured and **not taken**: the crude adult
    life-table rate (1.6619%) gives 2,124,898 and reads `cbo_opt51` at **32.1%**
    and the class at **17.7%**; the crude all-age rate (1.2910%) gives 1,650,702
    and reads **28.4%** and **16.9%**. Both are better than the shipped constant
    and both were refused, because picking the best of three is fitting a
    parameter to a benchmark. Two measurements travel with the question. The
    **$1M → $5M exclusion step is now $9.40B against Treasury's own $33.4B**,
    having gone through Treasury's figure and out the other side (it was 82.26 in
    Wave 4 and 85.02 in Wave 7). And the **SOI check needs a unit before it is a
    check**: SOI Table 1 counts *individual* decedents over a *gross-estate*
    threshold and the model counts *households* over net worth, so the implied
    36,262 above $12.92M against SOI's 7,194 is partly a unit gap, and making it a
    real check needs SOI's own gross-estate distribution spliced onto the DFA's
    household one — recorded as unbuilt in `W7_decedent_ladder.md` §8.8.
62. **`FRBUSAdapterLite`'s crowding-out term inverts its sign for a
    revenue-raiser.** *(New, from `planning/lanes/HSC_h8_tariff_feedback.md`
    finding 1.)* `gdp_change[t] *= (1 - crowding_effect)` with a **negative**
    cumulative deficit gives a factor **above 1** applied to a negative GDP
    change, so **lower debt makes the drag larger**. About **12%** of H8's GDP
    channel. Pre-existing, affects **every** revenue-raiser that reaches the
    adapter — not tariffs alone — and outside H8's file boundary, so it was
    carried rather than fixed. It is a sign defect in the same family as PR #119's
    sweep, in a module that sweep did not cover.
63. **`score_policy(dynamic=True)` calls `EconomicModel`, not
    `policy_to_scenario`.** *(New, from `planning/lanes/HSC_h8_tariff_feedback.md`
    finding 2.)* So the tariff's own price-and-volume impulse — `border_pass_through
    × Δτ × base × V`, **$211.5B/yr for the universal preset against $125.9B/yr of
    receipts**, because a tariff withdraws more real income than it collects —
    reaches the multi-model path and **not the dynamic tab**. The dynamic tab
    still multiplies net receipts by the generic tax multiplier. Wiring it needs a
    hook in `economics.py`, which is a green-tier file no presentation lane
    should open.
64. **The Section 232 derivative annex is at HS-10 and this repository reads
    HS-73 whole.** *(New, from `planning/lanes/HSC_h8_tariff_feedback.md`.)* The
    steel base now reaches the derivative chapter — $58.9B → **$108.4B**, and
    **1.84×, not the "roughly triple" this repository stated in three places** —
    but it is declared an **upper bound**: Proclamation 10896 taxes steel
    *content* and the annexes list articles at ten digits, where the loader has a
    two-digit chapter. The floor is one argument away and neither bound is
    sourced at the statute's own granularity. Closing it is a data-acquisition
    step (the HS-10 annex lists), not a modelling one.
65. **`steel_tariff_25`'s target is untraceable, has been examined-and-left
    twice, and now carries the whole of a sub-population's regression.** *(New,
    from `planning/lanes/HSC_h8_tariff_feedback.md`.)* The 25% Section 232 rate
    was in force for ten weeks and no scorekeeper published a ten-year estimate of
    it; `EXAMINED_NOT_REVISED` records the verdict and explicitly **does not
    retire** the row. After PR #150 it reads **75.28%** and is the entire
    difference between `Trade` at 43.6% and the 35.66% its four documented rows
    read. **The floor base would have scored 1.7%** (−$59.0B against −$60.0B) and
    was declared and refused, because closeness to an untraceable figure is not a
    reason to keep a base missing most of what the statute reaches. This needs a
    document or a retirement decision, and neither is a lane's to take.

66. **The three expenditure magnitudes that are still unsourced, and the shared
    docs that describe all five as unsourced.** *(New, from
    `planning/lanes/HSD_h7_expenditure_magnitudes.md` §6.7 — the live half of
    item 38.)* **Employer health 0.20, retirement 0.30, SALT 0.05**, each with
    its search recorded in that lane's §1 so the next lane does not repeat it,
    and **employer health is the one that matters, because it is the only one on
    a Tier 1 row** — CBO Option 56, at **12.8%**. The search there turned up an
    elasticity and it is **attached to the wrong half of the mechanism**: CBO and
    JCT publish employer *offer* price elasticities by firm size (−0.07 for
    1,000+ employees, −0.15 for 100–999, −0.38 for 25–99, −1.14 for smaller
    firms), which price the coverage-**dropping** channel that Option 56's own
    sentence ranks *below* plan switching ("To a lesser extent…"), and nothing
    published sizes the plan-switching channel carrying the rest. So the finding
    is not "there is no elasticity" but the sharper "the available one prices the
    lesser channel", which is why 0.20 was left rather than replaced with
    something that would have carried a citation. Retirement's 0.30 has CBO
    quantifying exactly **one** leg — "$6 billion" of Roth-conversion
    constraints — with the net sign declared to reverse *outside* the window, and
    nothing scored reads it today. SALT's 0.05 has CBO naming the channel and
    pricing nothing; Yale prices something adjacent and not this (the mortgage
    expenditure moving **$323B → $497B** when the SALT limit doubles — a
    different dose, a different expenditure and a *level* rather than a share).

    **Three things travel with the item.** (i) **Two shared docs assert something
    the code now contradicts**: `docs/METHODOLOGY.md` line 376 ("**The magnitudes
    are still unsourced**, all five of them", plus the unreproducible 18%) and
    `docs/VALIDATION.md` line 177 ("**the magnitude is still unsourced**, here and
    on all five entries") were true of five and are true of three — **both are
    corrected by the docs pass that carries this sync**, so they are recorded here
    as closed rather than open. `docs/VALIDATION.md` **line 400's** older claim
    that `TaxExpenditurePolicy` "is the single entry in `CONVENTION_EXCEPTIONS`"
    is a different sentence, falsified by PR #128 when the set became one of
    *policies*, and **still needs a check**. (ii) **Nothing scores a charitable
    *floor*, or CBO Option 49's 15% ceiling**, both of which the module can
    now express with a per-reform magnitude — and finding 3 of §5.10 is the
    argument for registering the 15% alternative as a benchmark, since a
    module-wide constant would have over-magnified it by **94%** and the shipped
    0.40 by **251%**, with nothing in the repository scoring it to notice.
    (iii) **`eliminate_mortgage` is a range row whose model sits outside both
    bounds**, now by **$111.1B** rather than $97.6B, because the sourced erosion
    moved the score further from a range it was already under. Wave B recorded
    the range's own 2.4× as a *baseline* difference rather than a simulator one;
    nothing since has addressed the level.

67. **The PTC repeal's employment-based destination share, and three unpriced
    channels either side of it.** *(New, from
    `planning/lanes/HSD_h11_ptc_coverage.md` §6.6.)* The **ESI channel is the
    largest single term in the score — $155.44B against a net offset of
    $118.16B** — and it is the only one transferred from a population the statute
    excludes from the scored one: CBO's 60437 Table 3 puts **3.5M of the 6.9M**
    marginal enrollees above 400% FPL, where the February 2026 vintage's §36B
    eligibility stops, and report p. 6 says the employment-based decline "would
    affect people with higher incomes". **Zeroing it gives −$996.28B and 9.43%**
    against the carried target, and it was declared and declined, because "most"
    does not license a zero and §36B(c)(2)(C) bars only an *affordable* offer;
    `test_the_esi_concentration_is_measured_and_not_taken` asserts the shipped
    path is not the one nearer the target. Closing it needs **a published
    employer-offer rate for the sub-400%-FPL marketplace population, or a
    published repeal score**, and neither exists today — CBO/JCT publication
    **61734** scores the same policy on the app's own FY2026–2035 window and
    publishes outlays, revenues and the net and **nothing else**, so the
    composition cannot be recomputed on the window the app scores.

    Three smaller ones, and **two of the three point in opposite directions**,
    which is why none may be taken alone. **The Basic Health Program's statutory
    zeroing** under 42 U.S.C. §18051(d)(3) — BHP funding is 95% of the credit, so
    a repeal **zeroes** it rather than reversing 60437's +$17B — an unpriced
    **saving** on 1.0M enrollees. **The un-mirrored Medicaid pickup**, people
    losing the credit near the Medicaid threshold — an unpriced **cost**, the
    other way. And **the $4,350 / $2,971.43 gap**: the ESI channel's booked rate
    is **0.6831** of the per-person tax benefit CBO states on the same page, with
    three candidate explanations nameable (Table 2 makes FY2025 a 0.05% stub, so
    a ten-calendar-year coverage average meets a nine-effective-year budget
    window; $37.7B of the revenue is off-budget Social Security; the $4,350 is
    per *person* where the exclusion accrues per *policy*) and **none separable
    from the document** — the model uses the booked rate, which is CBO's own
    arithmetic, and asserting a mechanism here would repeat an error a previous
    lane had to correct in itself. Separably, `MARKETPLACE_DATA`'s remaining
    uncited constants — the FPL distribution, the average subsidies and the
    benchmark premium — are still read by `calculate_subsidy`'s callers, and the
    **$325B footnote-4 variant** would give a 21.7% aggregate share against
    19.3%, a ±2.4pp uncertainty that sits under every channel amount and is not
    propagated.

68. **The values composer selects a demoted preset into every archetype.**
    *(New, from `planning/lanes/HSD_h12_illustrative_group.md` §5 and finding 4.)*
    Build's checklist starts empty and `apply_preselection` only ever runs from a
    link, so **the real default package is the values composer** — and all five
    archetypes select **`irs-enforcement-double`**, an **82.3%**-off unfitted
    reconstruction carrying about **$61B** of a twelve-policy package. None
    selects any of the four pharma presets, so the one demoted preset that
    reaches a values-built package is the enforcement row rather than the 701%
    one. Measured before any edit and left alone, because `composer.py` was
    outside the lane's files and **excluding it would move five package totals**
    — a scored-number change that a presentation lane may not make by
    implication. Two smaller ones from the same hand-off. **Ask's `list_presets`
    does not mark tier at all**, so the assistant can list these five without
    saying what they are; whether it should is the blue tier's call. And
    `PRESET_POLICY_PACKAGES`'s `official_total` sums are **stale for seven of
    twelve packages** — which is item 56, sighted a second time from a different
    surface, and still not a label lane's to take.

69. **A retired row's preset badge cannot say "withdrawn", and two more
    retirement candidates are named.** *(New, from
    `planning/lanes/LEDGER_decisions_3_4.md` §5.8.)* After PR #160 the badge on
    a retired row still reads **"Unfitted reconstruction, 93.3% from −$500B"**.
    **It is not a false claim** — `_provenance_clause` already appends *"The
    target itself is this model's own estimate, not a published score"* to both
    rows — but **"withdrawn" is the more accurate word**, and the field it needs
    is one line: `_scorecard_index` does not carry `target_retired`, and
    `ui/preset_validation.py` was not that lane's file. Both rows are also in the
    illustrative group PR #158 built, so a user meets them twice with two
    different descriptions of the same fact. Separately, **two further retirement
    candidates are named and not acted on**, `carbon_tax_50` and
    `eliminate_step_up` (`HSB_h9_provenance.md` §8.7) — and the second has the
    stronger case on the documents, since its −$500B is about **2.4×** the
    largest published no-exclusion figure and an exclusion makes a repeal
    *narrower*. Each is its own owner decision on the ledger's terms, and each
    would need the held-in-place line to grow with it.

70. **SALT's four residuals, of which one is a green-tier inconsistency a user
    can see.** *(New, from `planning/lanes/SALT_current_law_baseline.md` §7 —
    the open half of item 3.)* **The revenue score and the who-pays table now
    disagree about what year it is.** `microsim/engine.py` sets
    `self.salt_cap = 10000` and `distribution_effects.py` reads
    `getattr(policy, "salt_cap", 10000)`, so the distributional path prices a
    $10,000-cap world for the same policy object whose revenue score is current
    law — and the lane that found it owns neither file. It is §6.2 item 46's
    shape in a second module (*one policy object, two answers*), and it is the
    one residual here that reaches a shipped surface.

    **The Ask assistant's own corpus still teaches the pre-2025 statute.**
    `assistant/knowledge/key_definitions.md` ("SALT cap: … cap of \$10K enacted
    in TCJA; repeal scored at roughly +\$1.9T over 10 years" and "Repeal of the
    SALT cap adds \$1.9 trillion beyond TCJA extension (JCT 2024)") and
    `state_local_fiscal.md` ("Federal revenue gain: ~\$1.9 trillion over a decade
    (JCT)") are both BM25-indexed and both reachable by a user asking about SALT
    — and this is **worse than the stale strings PR #148 found**, because
    `target_revisions.repeal_salt_cap.v1`'s own reason reads *"The JCT
    attribution is wrong: JCT has never published a standalone score of repealing
    the $10,000 cap"*. The repository rejects the figure **by name** in one file
    and tells the assistant it in another; P.L. 119-21 sec. 70120 does not appear
    in the corpus at all. Both strings are quoted in full in the lane doc, so the
    fix is one commit for whoever owns `assistant/knowledge/`.

    **Two modelling residuals and one schema question.** `SOI_BASE_YEAR = 2023`
    is declared and read by nothing — the module's own comment says amounts "are
    grown from this year to a policy's first year" and they are not; **ageing
    them would raise the uncapped level 9.3%** and move rows in three other
    reforms, so it was deliberately untouched. **New itemisers under a raised cap
    are the largest named term in the −23.6%** against JCT's own sec. 70120 line:
    JCX-45-25 puts SALT claimants at **11.8M → 17.8M returns** under the $40,000
    cap, and SOI's TY2023 itemiser panel observes none of them, so the omission is
    one-directional and makes the model under-count exactly as observed — closing
    it needs a base outside SOI Table 2.1. And the schema question the ledger
    raised: **should Tier 2 grow a shape-input manifest, as `preregistered.py`
    has for Tier 1?** `SALT_SCORING_BASELINES` is this lane's local answer and
    does not generalise; `target_revisions.py` cannot carry a declaration that
    moves no target, and was right to refuse one.

71. **February 2024's debt/GDP is a mixture, and four more CBO datasets are one
    `--source-dir` away.** *(New, from `planning/lanes/R1_baseline_transcription.md`
    §8.)* That vintage's **GDP is CBO's own and its budget lines are this
    module's reconstruction**, because `cbo-data` ships no `ten_year_budget` for
    the February 2024 edition and June 2024 is publication **60039**, *An Update
    to the Budget and Economic Outlook* — a different document, whose FY2025
    deficit is $1,937.9B against January 2025's $1,865.3B, so borrowing it would
    grade a vintage `transcribed` against a document it does not name. **The
    ratio should not be quoted**, and there are two honest remedies, neither a
    lane's: register a **fourth `BaselineVintage`** for June 2024 (the file is
    there, pinned, and its identity checks pass — but it ripples into the URL
    contract, frozen links and the API, so it is a lane of its own), or have the
    surfaces **refuse to render a ratio whose numerator and denominator carry
    different grades**.

    Three smaller ones and a stock of unopened data. **`base_*` budget levels are
    unread for a transcribed vintage**: `generate()` reads CBO's table while
    `CBOBaseline.base_individual_income_tax` and its nine siblings are still the
    reconstruction, left alone because overwriting them forces a base-year
    convention (`_CBO_JAN_2025_BASE_LEVELS` is FY2025 while `_project_*` treats
    its base as `start_year − 1`) that the lane had no reason to settle. **The
    calendar/fiscal anchor**: `_income_base_projection_factor` anchors on a
    **tax** year and reads CBO's **fiscal** table for both ends, exactly as the
    code it replaced read one series for both; CBO publishes
    `calendar_<edition>.csv` beside the fiscal one and **the two differ by about
    1.4% on a level**. That is R7's question — it is about what the base *is* —
    and the size of it is recorded rather than taken. **`scoring_engine.py:345-385`'s
    docstring quotes stale factors**: "February 2024 takes **1.3118** on
    FY2025-2034, the app takes **1.3560** on FY2026-2035", where the live figures
    are **1.3053** and **1.3963**; not that lane's file. And the pinned clone
    already carries `tax_parameters` (R4), `revenue_detail/annual_cy_iit_*` (R7),
    `spending_detail` at **21,769** account-rows (R15b and item 16) and
    `budgetary-feedback-model/input/rules_of_thumb.csv` (R12), with
    `scripts/fetch_cbo_baseline.py`'s pinning, digest-checking and identity-check
    structure reusable for each.

72. **Treasury's 1.2pp row as a possible future Tier 1 target — and the base
    question that comes with it.** *(New, from
    `planning/lanes/R2_tier1_secondhand_targets.md` §6, the live half of item
    45.)* A **`medicare_surcharge_2pp.v2` at −$403.8B on a `rate_change=0.012`
    shape** would be a genuine Treasury line item — FY2025 Green Book, report
    pp. 76–77 for the proposal and p. 242 for **$403,790M**, corroborated by the
    FY2024 edition's $344,371M on its own window — where the retired `.v1` scored
    a 2pp reform against a figure Treasury prints for a **1.2pp** one. **It is a
    new row and not a rate edit**, because re-shaping a row to fit what its
    document turns out to say is exactly what R2 bound itself against, and the
    honest starting point is that on Treasury's own rate the model currently
    reads **−$245.2B against −$403.8B, 39.3% under** — a *worse* row than the
    31.8% the retired one reported. **The base question travels with it and is
    not small**: §1411's statutory base is **wages plus net investment income**,
    which is **neither SOI column** (H2b established that, which is why the row
    did not move in Wave B when the two Option 46 rows did), so registering it
    without settling the base would register a row measuring inexpressibility.
    Two sibling candidates from the same hand-off, both cheaper: a **new TPC case
    scoring a 10pp surtax on AGI above $2M** against T19-0037's **$585.325B** —
    the withdrawn Warren row's own base and threshold at a rate somebody actually
    priced — and an **`illustrative_1pp_all.v3`** with
    `scoring_window_first_year = 2023`, worth most of that row's remaining 14.3%.
    All three belong to **R3**, which owes this tier four rows before the
    per-class bands mean anything again: Tier 1 is **22 rows against criterion
    ①'s 40**, `agi_inclusive_surtax` is down to **n = 2**, and the battery now
    contains **no rate cut and no positive target at all**.
