# R6b — Making SOI cell calibration the default: pre-registration for an owner decision

**Status: NOT TAKEN.** This file pre-registers what an owner decision to make R6's cell
calibration (`augment_top_tail(by_status=True)` then `calibrate_cells_to_soi`) the default
microdata would move, measured before anyone flips anything. It also records the one opt-in
change this lane did make (§1). Owns: `fiscal_model/microsim/top_tail.py` (opt-in path only),
`tests/test_top_tail_state_draw.py`, this file. Read beside
`planning/lanes/R6_microdata_cell_calibration.md` and `planning/lanes/R7_weighted_group_totals.md`.

**Method.** Every "flip" figure below comes from `scratchpad/flip_patch.py`, which intercepts
every full read of `tax_microdata_2024.csv` (through `load_tax_microdata` or a direct
`pd.read_csv`) and returns the cell-calibrated frame, and points `package_interactions._population`
at that frame instead of its own default augmentation. The validation scripts, a preset/Tailor
sweep, a Build interaction sweep and the R7 distributional sweep were then run under it. The
patch counts its interceptions, so "this surface does not read microdata" is a measurement
(0 interceptions), not an assumption. All figures are on the tree after R7 and §1 below.

---

## 1. Prerequisite done: the California stamp, measured and removed (opt-in path only)

R6 §2 left one suspected contributor to the SALT regression unmeasured: every synthetic
top-tail row on the `by_status` path carried `state_fips = 6`.

**Measurement.** `jct_salt_repeal_2024` on the calibrated frame, with synthetic rows' state
re-drawn from the weighted state mix of the CPS's own high-income rows (no new constants;
R6 §6's stated reference, AGI ≥ $500K, 746 rows, CA 18.4% / TX 8.9% / NY 8.0% of weight), plus
sensitivity at $200K+ and $1M+, an exact expected-value split across states, five seeds, and a
split by filing status:

| Synthetic-row state | SALT row (pp) |
|---|---:|
| all California (R6) | 11.0133 |
| CPS mix at $500K+, sampled, 5 seeds | 11.0133 (all five) |
| CPS mix at $200K+ / $500K+ / $1M+, exact split | 11.0133 / 11.0133 / 11.0133 |
| CPS mix at $500K+, by filing status | 11.0133 |
| all New York / all Texas | 11.0133 / 11.0133 |

**The stamp moves the SALT row by exactly 0.00pp (agreement to 1e-15).** Reason, verified row by
row: **all 800 synthetic rows pay AMT both before and after the cap repeal**, so their reform
tax change is zero whatever SALT rate their state implies (repeal moves the total by
−$29.12B under every stamp; the synthetic rows contribute $0.00B of it). Under the baseline
$10K cap the cap binds for every synthetic row in every state (the lowest imputed rate, Florida's
0.90%, times the $1.5M floor is $13.5K), so baseline tax is state-invariant too. Two R6
statements need correcting: California's imputed SALT rate (6.03% = income + local + property,
the formula `salt_imputation.py` uses) is **not** the highest in the table — New York's is 11.38%
and Illinois's 7.19% — and the stamp is **not** a contributor to 5.86 → 11.01pp.

**What the regression actually is.** On the shipped file the `$1M+` class is CPS rows between
$1M and $2M that itemise and get a SALT benefit (model share 30.6%). Calibration drops the 17 CPS
rows at ≥ $1.5M and replaces them with synthetic rows on which AMT binds, which get nothing, so
the class's share falls to 20.3% and the $500K–1M class's rises to 50.1% (JCT: 27.9% / 38.2%).
That is R6's mechanism (ii); (i) and (iii) are untested.

**The fix shipped anyway, because the stamp is a fabricated attribute.** Opt-in `by_status`
path only: synthetic rows draw `state_fips` from the weighted state distribution of the CPS rows
at ≥ `SYNTHETIC_STATE_REFERENCE_AGI` ($500K) that the synthetic cells do not replace (729 rows;
CA 18.0% of synthetic weight after the draw). States are drawn from the same generator *after*
every AGI draw, so the AGI sample and every calibrated weight are byte-identical to R6's
(asserted). A frame with no `state_fips` column, or no CPS rows above the reference, keeps the
old fallback. **Default path byte-identical** (`augment_top_tail(df, year)` without `by_status`
returns the same frame, asserted in `tests/test_soi_cell_calibration.py`). Idempotent. Nothing
scored reads it today: `state_fips` is read only by `salt_imputation.py`.

## 2. What "make it the default" would have to switch

Grep for every reader of the microdata file. A flip is not one line:

| Reader | How it reads | Under a flip |
|---|---|---|
| `credits_microdata._base_population` (derived credits; LOO held-out mode) | `load_tax_microdata` | moves (§3.2) |
| `health.check_health` / `describe_microdata` / dashboard health + SOI block | `load_tax_microdata` | moves (§3.3) |
| `distribution_engine.analyze_policy_microsim` | **direct `pd.read_csv`** — bypasses the loader | moves (§3.1, §3.4) *only if routed* |
| `package_interactions._population` (Build's interaction shares) | direct read **plus its own default `augment_top_tail`** | moves (§3.5) only if routed; must stop double-augmenting |
| `models/comparison.py` TPC-microsim pilot | direct read + optional augmenter | moves if routed (not swept: concurrently edited) |
| `ui/tabs/distribution_analysis.py` calibration caption | `load_tax_microdata` + `calibrate_to_soi(year=2022)` | caption ratios become ~1.0 |
| `ui/app_controller.py` "augmentation preview" | `load_tax_microdata` + **default** `augment_top_tail` | becomes meaningless (default augmentation strips the calibrated synthetic rows and re-adds unweighted-cell ones) — must be removed or rewritten |
| `ui/policy_execution.py`, `microsim/demo.py` | direct read | demo surfaces; move if routed |
| `feasibility.py` | header / `usecols` only | unaffected |

R6 §4 said adoption "would touch `load_tax_microdata` and `credits_microdata.py`". That
understates it: the distributional engine and Build never go through `load_tax_microdata`, so a
loader-only flip would move LOO and the dashboard's coverage block and leave every
distributional table and the SALT row where they are.

## 3. Pre-registered movements (full flip: loader + all direct readers routed)

### 3.1 Distributional benchmarks (7)

| Benchmark | Now (pp) | Flip (pp) | Rating |
|---|---:|---:|---|
| `cbo_tcja_2018` | 0.00 | 0.00 | unchanged (synthetic path) |
| `jct_tcja_2019` | 2.0986 | 2.0986 | unchanged (synthetic) |
| `cbo_arp_2021` (household) | 3.72107 | **3.72120** | good → good; moves in the 4th decimal (R6 said "unchanged", true to 2dp only) |
| `jct_salt_repeal_2024` | 5.8607 | **11.0133** | acceptable → **needs_improvement** |
| `jct_corporate_28_2022` | 2.5125 | 2.5125 | unchanged (synthetic) |
| `cbo_tcja_extension_2026` | 0.74 | 0.74 | unchanged (synthetic) |
| `cbo_pl119_21_2026` | 3.96 | 3.96 | unchanged (synthetic) |

R7's weighting fix does not change any of these (shares only; R7 §5), with or without the flip.

### 3.2 Leave-one-out (moves; R6 §4 said it would not)

`run_loo.py` holds the credits module out in **derived** mode (`CREDIT_HELD_OUT_MODE`), which
reads `_base_population`:

| Case | Official | Now | Flip |
|---|---:|---:|---:|
| `biden_ctc_2021` | 1,600.0 | 1,528.5 (−4.5%) | **1,440.5 (−10.0%)** |
| `ctc_extension` | 600.0 | 714.2 (+19.0%) | **799.6 (+33.3%)** |
| `biden_eitc_childless` | 162.6 | 110.4 (−32.1%) | **176.8 (+8.7%)** |
| Credits module mean | | 18.5% | **17.3%** |
| Suite (n=18) mean / median / within 15% | | 36.5% / 30.2% / 5 | **36.3% / 30.8% / 6** |

Every other module and the capital-gains donor matrix: identical. The CI LOO ceiling (75) is
not approached.

### 3.3 Dashboard health and SOI block

| | Now | Flip |
|---|---|---|
| microdata health | warn (degraded), returns 119.0% / AGI 81.0% | **ok, 100.0% / 100.9%** |
| microsim returns / AGI | 191.1M / $12.38T | **160.6M / $15.43T** |
| per-bracket returns ratios | 2.65 … 0.00 | **1.00 in every bracket**; AGI ratios 1.00 except $0–15K at **4.10** (SOI's negative no-AGI class sits in that bracket's denominator) |
| calibration gate | False (bracket < 60% AGI) | **True** |
| distributional gate | True | **False** (SALT row) |
| `overall` / exit code | warn / **2** (passes CI) | **fail / 1 (fails CI)** |

**This is the decisive line.** `.github/workflows/validation-dashboard.yml` fails the job on exit
1. A flip on today's tree turns the dashboard CI job red through the SALT row, so it cannot merge
without either a SALT mechanism change that brings the row under 10pp or a change to the gate —
and changing a gate to admit a regression is the relaxation this repository's rules forbid.

### 3.4 Distributional tables a user sees (45 tables: 9 microsim presets + 4 Tailor shapes × 3 groupings)

Year-1 microsim totals (quintile view) move because the calibrated frame has the SOI top tail:

| Policy | Now ($B) | Flip ($B) | % with increase / cut |
|---|---:|---:|---|
| Biden 2025 Proposal (= Tailor +2.6pp > $400K) | 14.17 | **33.79** | 1.11 → **1.88** |
| High-Earner Medicare Surcharge 2pp | 10.90 | **25.99** | 1.11 → **1.88** |
| Progressive Millionaire Tax (= Tailor +5pp > $1M) | 2.55 | **26.81** | 0.17 → **0.29** |
| Top Rate to 45% | 21.06 | **69.48** | 0.46 → **0.92** |
| Warren Ultra-Millionaire Surtax | 0.04 | **10.87** | 0.01 → **0.05**; headline **flat → progressive** (all 3 groupings) |
| Middle Class Tax Cut | −101.86 | **−124.68** | cut 28.87 → **37.52** |
| EITC Childless Expansion | −9.63 | **−15.42** | cut 7.64 → **13.24** |
| Repeal SALT Cap | −25.47 | **−29.12** | cut 3.24 → **4.24** |
| Flat Tax Reform | −9.37 | **−7.60** | cut 0.34 → **0.44** |
| Tailor −1pp all / +1pp all | −1.87 / +1.87 | **−1.52 / +1.52** | 0.34 → **0.44** |

Cells moved over the 45 tables: `total_tax_change` 40/45, `share_of_total_change` 52 of 401
rows, headline direction 3/45 (Warren only), `num_returns` 349/401. These are
distributional-tab figures only; no revenue score reads them (§3.6).

### 3.5 Build interaction shares

Only the seven pairs involving `salt-cap-repeal` interact on the microsim; every other pair of the
nine microsim presets is 0.0 either way. Interaction as a share of the named member's standalone:

| Pair | Now | Flip |
|---|---:|---:|
| salt-cap-repeal + top-rate-45 | −45.4% of SALT | **−43.2%** |
| salt-cap-repeal + millionaire-surtax-5pp | −22.4% of SALT | **−18.5%** |
| salt-cap-repeal + top-rate-39-6 | −17.1% of SALT | **−16.9%** |
| salt-cap-repeal + middle-class-rate-cut-2pp | +15.4% of SALT | **+15.1%** |
| salt-cap-repeal + medicare-surcharge-2pp | −13.7% of surcharge | **−14.5%** |
| salt-cap-repeal + across-the-board-rate-cut-5pp | +20.3% of rate cut | **+23.4%** |
| salt-cap-repeal + ultra-millionaire-surtax-3pp | −19.2% of surtax | **−19.2%** |

Build's package totals are list prices and do not move.

### 3.6 Byte-identical under the flip (measured)

- `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json`: sha256 **69f52cf3…a37a9dd**,
  equal to the pre-lane baseline — the 44-row out-of-sample tier, the fitted tier, the
  held-in-place and reconstruction tiers.
- All 52 presets' static ten-year scores and 4 Tailor shapes: identical to the cent; the patch
  intercepted **0** microdata reads while scoring them (credits presets score in `reported`
  mode, `CREDIT_APP_MODE`).
- `run_loo.py --donor-matrix`: identical except the four Credits lines and the three suite lines
  in §3.2.

## 4. Falsification conditions for the flip PR

The flip PR must reproduce §3 to the stated precision. It is falsified (stop, do not merge) if:

1. `cold_holdout.py --json` changes at all;
2. any preset or Tailor static score changes;
3. any distributional benchmark other than `cbo_arp_2021` and `jct_salt_repeal_2024` moves, or
   either of those lands elsewhere than 3.7212 / 11.0133pp;
4. LOO moves outside the Credits module, or the Credits rows land elsewhere than
   1,440.5 / 799.6 / 176.8;
5. the dashboard exits anything other than 1 on an unchanged SALT mechanism (if it exits 0 or 2,
   something other than the calibration changed).

## 5. Recommendation to the owner

Do not flip yet. In order:

1. **Fix the SALT row's mechanism first** — the AMT binding on every synthetic $1.5M+ row
   (R6 (ii)), the flat-rate-on-AGI SALT imputation (i), or the AGI-vs-expanded-income ranking
   (iii) — in a pre-registered lane, and re-measure the SALT row on the calibrated frame. Until
   it is below 10pp a flip fails CI.
2. **Route the direct readers** (`distribution_engine`, `package_interactions`, the pilot)
   through one loader, and delete or rewrite `app_controller`'s augmentation preview.
3. **Carry `household_weight` through calibration** (R6 §6) before a household-universe
   benchmark at the top relies on it; ARP's 4th-decimal movement is that effect.
4. Then flip, with this file's §3 as the pre-registration, and accept the credits LOO movement
   (one row worse, one row better, one sign flip) as found.

The effective sample size cost (57.5k → 36.1k, R6 §3) is unchanged by anything here.
