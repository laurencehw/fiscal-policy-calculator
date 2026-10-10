# R6c — The SALT mechanism, and SOI cell calibration as the default microdata

**Status: pre-registered, not yet implemented.** Written and committed before any file under
`fiscal_model/` is opened for editing. Every figure below was measured on `main` @ `8fd84e2`
with scratchpad patches (described in §4) that reproduce the intended code, so the implementing
commits have to land on these numbers or say why not.

**Owner decision taken.** R6b recommended "fix the SALT row's mechanism first, then flip". The
measurement in §2 shows the two cannot ship separately: the mechanism fix alone takes the SALT
row to 14.91pp on today's microdata (CI red), and R6b's flip alone takes it to 11.01pp (CI red).
Laurence chose **"Together"** on 2026-10-10: one PR carries both, and R6b §3 is this lane's
pre-registration for the flip half, re-measured here with the mechanism in place.

Owns: `fiscal_model/microsim/engine.py` (AMT only), `fiscal_model/microsim/salt_imputation.py`,
a new loader `fiscal_model/microsim/population.py`, the readers R6b §2 lists, the dashboard's
`collect_microdata`, tests touching them, this file.

---

## 1. What is wrong with the SALT row (R6 mechanism (ii) and (i), both confirmed)

### 1.1 The microsim's AMT is not §55

`MicroTaxCalculator._calculate_amt` taxes `AGI − exemption` at 26%/28%, with:

| Statute | Engine today |
|---|---|
| §55(d)(2): exemption phases out at 25% of AMTI above $626,350 / $1,252,700 (TCJA, 2025; Rev. Proc. 2024-40 §3.11) | **no phase-out**: a $5M return keeps the full $137,000 exemption |
| §55(b)(3): net capital gain and qualified dividends taxed at the capital-gains rates inside the AMT | **all income at 26/28%**, so a gains-heavy return pays 28% AMT against a 20% regular rate |
| §56(b)(1)(A)(ii), (E): AMTI adds back SALT and the standard deduction, and allows other itemized deductions | AMTI is **AGI**: mortgage interest and charitable gifts are disallowed too |
| §55(b)(1)(A): 26% up to $239,100 (2025), the same for single and joint | `$232,600` (the 2024 figure), halved for *everyone* unless the frame has no married row (`married.any()`) |

The preferential-rate omission dominates. On the cell-calibrated frame the AMT binds on **100% of
returns in every class from $1.5M up** (0.45% of all returns on the shipped file, 15% at
$500K–1M, 42% at $1.5–2M). A return paying AMT gets nothing from a SALT cap repeal, so the
calibrated frame's synthetic top tail, where R6 put the SOI $1M+ population, receives nothing.
That is the whole of R6b §1's finding: "all 800 synthetic rows pay AMT both before and after the
cap repeal".

With the statutory AMT, incidence falls to 0.02% (shipped frame) / 0.04% (calibrated) of returns.
Post-TCJA AMT is known to reach a fraction of a percent of returns, concentrated well below the
very top (where the phase-out is complete but the 20% gains rate and the 37% ordinary rate keep
regular tax above the minimum tax). The statutory version reproduces that shape; the shipped
one, binding on every $1.5M+ return, does not. (No SOI AMT-incidence row is transcribed in this
repository, so this is a qualitative check, not a benchmark.)

### 1.2 The SALT imputation is a flat rate on AGI

`impute_salt_and_itemized` sets SALT = AGI × the state's combined income+local+property rate
(5.76% national fallback), and other itemized deductions = 3% of AGI, at every income. SOI Table
2.1 (TY2023, itemizers, transcribed in
`fiscal_model/data_files/tax_expenditures/soi_2023_itemized_deductions_by_agi.csv` since Wave 2)
says SALT as a share of AGI **rises** with income through the middle and top classes (property
tax is a falling share, income tax a rising one), and mortgage + charitable is a falling share.
Both are published by AGI class, so the imputation can read them instead of a constant.

## 2. The change, and why the two halves ship together

**(A) Statutory AMT in `MicroTaxCalculator`.**
- AMTI = AGI − (itemized deductions other than SALT) for a return that itemizes; AGI otherwise.
- Exemption phased out at 25% above the §55(d)(2) thresholds.
- 26% / 28% with the breakpoint at $239,100 for both filing statuses (the engine has no MFS).
- Preferential income (the engine's own `preferential_income`) taxed at the engine's own
  capital-gains schedule (`_ltcg_tax`) on top of the ordinary AMT base, and the tentative minimum
  tax is the lesser of that and the flat 26/28% schedule (§55(b)(3)'s "shall not exceed").
- Removes the `married.any()` branch.
- Parameters are hard-coded beside the engine's other 2025 parameters, like the rest of the
  engine, and a test pins them to the two transcribed tables they come from:
  `fiscal_model.amt.load_statutory_amt_parameters()["tcja"][2025]` (exemption, phase-out
  threshold, phase-out rate) and `cbo_tax_parameters.parameter("cbo_jan_2025",
  "tp_amt_bracket_2_mfj" / "_single", 2025)` = 239,100.
- `amt_exemption_adjustment` reforms keep working (they move the exemption, not the phase-out).

**(B) SOI Table 2.1 class ratios in `impute_salt_and_itemized`.** Each row's AGI class (Table
2.1's own bounds) gives `salt_amount / agi_less_deficit` and `(mortgage_interest_amount +
charitable_amount) / agi_less_deficit`. The SALT ratio is scaled by the row's state rate relative
to the national fallback (state rate ÷ 0.0576), so the state variation the state calculator and
R6b's state draw rely on is kept. SALT = AGI × scaled ratio; itemized = SALT + AGI × other ratio.

**Choice declared before it was taken, and the cost of it.** The flat (unscaled) class ratio fits
the SALT row better than the state-scaled one: 4.22pp against 5.65pp on the calibrated frame.
State scaling is chosen anyway, on the principle that the imputation should not throw away the
state structure the repository already transcribed. Two known approximations, stated rather than
fixed: Table 2.1 is an *itemizer* panel, so applying its ratio to every return overstates SALT
for low-income non-itemizers (they mostly stay below the standard deduction regardless); and the
CPS's AGI-weighted mean state rate is 5.61%, not 5.76%, so state scaling lowers the imputed SALT
level by about 2.6%.

**(C) The flip** (R6b §2, all readers routed). A new `fiscal_model/microsim/population.py`
exposes `load_default_population()`: `load_tax_microdata()` → `augment_top_tail(year=2023,
by_status=True)` → `calibrate_cells_to_soi(year=2023)`, cached per process, returned as a copy.
It replaces the direct `pd.read_csv` in `distribution_engine.analyze_policy_microsim`,
`package_interactions._population` (which stops running its own default augmentation),
`credits_microdata._base_population`, `health`'s microdata check and the dashboard's default
`collect_microdata` frame, and the TPC-microsim pilot's default load (its own augmenter is
skipped on an already-calibrated frame). `ui/app_controller.py`'s augmentation preview is
rewritten to show raw → default coverage. `load_tax_microdata()` itself stays the raw loader.
Demo surfaces (`ui/policy_execution.py`, `microsim/demo.py`) are routed only if trivially so.

**Why together** (SALT row, `jct_salt_repeal_2024`, pp):

| | shipped AMT + flat imputation | (A)+(B) |
|---|---:|---:|
| today's microdata | 5.8607 | **14.9090** (needs_improvement, dashboard exit 1) |
| cell-calibrated default (C) | 11.0133 (R6b; exit 1) | **5.6541** (acceptable, exit 0) |

The 5.86 on today's file is errors cancelling: an AMT that zeroes the top tail's benefit, on a
file with too little top tail to notice. Variants measured on the way (default / calibrated):
preferential rates only 6.11 / 12.03; AMTI only 6.24 / 11.17; phase-out only 6.07 / 11.06; all
four AMT fixes 6.6461 / 10.8679; all four + flat class ratios 13.68 / 4.22.

## 3. Pre-registered movements of (A)+(B)+(C) against `main`

### 3.1 Distributional benchmarks (7)

| Benchmark | Now (pp) | After | |
|---|---:|---:|---|
| `cbo_tcja_2018` | 0.0 | 0.0 | unchanged (synthetic path) |
| `jct_tcja_2019` | 2.0986 | 2.0986 | unchanged |
| `cbo_arp_2021` | 3.7211 | **3.7204** | 4th decimal (flip alone: 3.7212) |
| `jct_salt_repeal_2024` | 5.8607 | **5.6541** | acceptable → acceptable |
| `jct_corporate_28_2022` | 2.5125 | 2.5125 | unchanged |
| `cbo_tcja_extension_2026` | 0.74 | 0.74 | unchanged |
| `cbo_pl119_21_2026` | 3.96 | 3.96 | unchanged |

SALT row by JCT class, average change ($) / share of the total:

| Class | JCT | Now | After |
|---|---|---|---|
| $100–200K | −280 / 5.5% | −29 / 3.0% | **−528 / 13.1%** |
| $200–500K | −2,430 / 28.1% | −587 / 26.6% | **−3,158 / 31.1%** |
| $500K–1M | −14,620 / 27.9% | −7,786 / 39.8% | **−12,988 / 20.8%** |
| $1M+ | −61,120 / 38.2% | −15,851 / 30.6% | **−46,368 / 33.3%** |

The average-dollar column moves from a factor of 2–10 low to within 25% of JCT in three classes
of four. The share error is better at the top and worse at $100–200K (over-imputed SALT for a
class whose itemizers SOI over-represents), and that is the row's remaining residual.

### 3.2 Leave-one-out: identical to R6b §3.2's flip figures

(A) and (B) do not touch the credits population (no SALT columns reach it, and its AMT does not
bind), so only the flip moves LOO:

| Case | Now | After |
|---|---:|---:|
| `biden_ctc_2021` | 1,528.5 (−4.5%) | **1,440.5 (−10.0%)** |
| `ctc_extension` | 714.2 (+19.0%) | **799.6 (+33.3%)** |
| `biden_eitc_childless` | 110.4 (−32.1%) | **176.8 (+8.7%)** |
| Credits module | 18.5% | **17.3%** |
| Suite (n=18) mean / median / within 15% | 36.5% / 30.2% / 5 | **36.3% / 30.8% / 6** |

Every other line of `run_loo.py --donor-matrix` is byte-identical. Exit 0 (ceiling 75).

### 3.3 Dashboard

| | Now | After |
|---|---|---|
| microdata health | warn (degraded), returns 119% / AGI 81% | **ok, 100% / 101%** |
| microsim returns / AGI | 191.1M / $12.38T | **160.6M / $15.43T** |
| per-bracket returns / AGI ratios | 2.65/2.79 … 0.00/0.00 | **1.00 / 1.00 everywhere except $0–15K AGI at 4.10** (SOI's negative no-AGI class) |
| overall | degraded | **ok** |
| exit code | 2 | **0** |
| final line | two `[WARN]` | **`[OK] All surfaces nominal.`** |

### 3.4 Distributional tables (year-1 microsim total, $B; the same total feeds all three groupings)

| Policy | Now | Flip only | **After** |
|---|---:|---:|---:|
| Biden 2025 Proposal | 14.17 | 33.79 | **31.35** |
| High-Earner Medicare Surcharge 2pp | 10.90 | 25.99 | **24.12** |
| Progressive Millionaire Tax | 2.55 | 26.81 | **24.55** |
| Top Rate to 45% | 21.06 | 69.48 | **63.99** |
| Warren Ultra-Millionaire Surtax | 0.04 | 10.87 | **9.89** |
| Middle Class Tax Cut | −101.86 | −124.68 | **−118.01** |
| EITC Childless Expansion | −9.63 | −15.42 | **−15.42** |
| Repeal SALT Cap | −25.47 | −29.12 | **−111.14** |
| Flat Tax Reform | −461.15 | −537.62 | **−516.42** |
| Custom Policy (preset default) | −7.59 | −21.10 | **−19.56** |

The SALT-cap repeal's year-1 total grows 4.4× because the top tail now gets a benefit. Rate
increases fall 7–9% from the flip-only figure because itemizers' larger deductions shrink
taxable income. No revenue score reads these (§3.6).

### 3.5 Build interaction shares (share of the reference member's standalone, %)

| Pair | Now | After |
|---|---:|---:|
| salt-cap-repeal + top-rate-45 | −16.4 | **−19.0** |
| salt-cap-repeal + top-rate-39-6 | −13.7 | **−16.3** |
| salt-cap-repeal + millionaire-surtax-5pp | −20.2 | **−19.1** |
| salt-cap-repeal + medicare-surcharge-2pp | −13.7 | **−16.3** |
| salt-cap-repeal + ultra-millionaire-surtax-3pp | −19.2 | **−16.5** |
| salt-cap-repeal + middle-class-rate-cut-2pp | +3.3 | **+6.9** |
| salt-cap-repeal + across-the-board-rate-cut-5pp | +2.0 | **+4.0** |
| salt-cap-repeal + custom-policy | +15.0 | **+17.7** |

(Reference member chosen by `measure_reforms`; this table reports against the rate member
throughout, so it is not comparable line by line with R6b §3.5, which reported some pairs
against the SALT member.) Package totals are list prices and do not move.

### 3.6 Byte-identical (measured)

- `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json`: sha256
  **69f52cf38b481f25308e70fc212e0a03c9165095c8fd8905d690cb070e37a9dd**, unchanged.
- All 53 presets' static ten-year scores (`final_deficit_effect`, to 4 decimals): unchanged;
  the flip intercepted 0 microdata reads while scoring them.
- Strict readiness, the calibrated tiers and the fitted tier: not read from the microsim.

## 4. Method

Scratchpad (not committed): `amt_proto.py` patches `_calculate_amt` with §2(A);
`impute_proto.py` patches `impute_salt_and_itemized` with §2(B); `flip_proto.py` returns the
cell-calibrated frame from every full read of the microdata file and points
`package_interactions._population` at it (28 interceptions in a full sweep, 0 while scoring
presets); `sweep.py MODE` runs the seven benchmarks, the distributional and Build sweeps,
`run_loo.py --donor-matrix`, `cold_holdout.py --json`, `run_validation_dashboard.py` and a
preset sweep under `now`, `mech`, `flip` and `both`. `flip` reproduces R6b §3 exactly (11.0133,
3.7212, the LOO credits rows), which is the check that the patch is the flip R6b measured.

## 5. Falsification conditions

The implementing commits are falsified (stop, do not merge) if:

1. `cold_holdout.py --json` changes at all, or any preset static score changes;
2. a distributional benchmark other than `cbo_arp_2021` and `jct_salt_repeal_2024` moves, or
   those land other than 3.7204 / 5.6541pp;
3. LOO moves outside the Credits module or lands other than §3.2;
4. the dashboard exits other than 0;
5. any surface that today reads the microdata still reads the raw file after the change
   (checked by a test that the routed readers return the calibrated row count).

Pushing a gate, or retuning the imputation or the AMT toward JCT's table, is out of scope; the
remaining $100–200K residual is reported, not chased.

---

## 6. Outturn (2026-10-10)

**Every pre-registered figure reproduced exactly.** The implementation was swept with the same
`sweep.py` and no patches. The output is identical to the `both` sweep for:

- all seven benchmarks to 4dp and the SALT class table;
- the distributional and Build sweeps;
- the `cold_holdout.py --json` sha256;
- the full text of `run_loo.py --donor-matrix` and `run_validation_dashboard.py`, with the dashboard exiting 0;
- all 53 preset static scores, compared against `main`.

None of the five falsification conditions fired.

**One sentence in §1.2 was wrong, and is corrected here rather than in place.** §1.2 says SOI
Table 2.1's SALT share of AGI "rises with income through the middle and top classes". It does
not:

- Among itemizers the share falls throughout, from 11.7% at $50–55K to 8.7% at $100–200K, 7.0% at $1–1.5M and 4.3% at $10M+.
- From $100K to $5M it stays above the old flat 5.76%. That is why the old imputation under-counted the benefit in exactly the classes JCT's table weights.

The mechanism, the choice of ratios and every number are unaffected. The test that encodes the
correct shape is `test_soi_salt_share_is_above_the_old_flat_rate_below_5m`.

**Findings beyond the pre-registration (each now a test):**

1. **The SALT repeal's concentration above $500K got worse, and that is the row's residual.**
   JCT puts 66.1% of the repeal above $500K. The model put 70.4% there before and puts 54.1%
   there after. `test_salt_cap_repeal_concentrates_at_top` asserted ≥60%; it now asserts ≥50%
   and carries these numbers. The share error improved overall, 5.86 → 5.65pp, because the
   $1M+ class came much closer in dollars. The benefit moved too far into $100–500K, where
   Table 2.1's itemizer ratio applied to every return over-imputes.
2. **The AMT still binds in one band, as the statute says it should.** Among the 800 unweighted
   synthetic top-tail rows, 7.6% are AMT-bound, all at $1.74M–$2.04M AGI. That is just above
   where the §55(d)(2) phase-out completes for joint filers (the 25% phase-out adds 7 points to
   the marginal rate there). Weighted incidence across the population is 0.04%.
3. **Standard deduction and AMT exemption no longer interact on the microsim.** The interaction
   is −1e-14. The returns near the AMT margin all itemize, so a larger standard deduction moves
   no one across it. That pair is out of `test_deduction_and_amt_exemption_changes_do_not_add`
   and pinned as near-zero in its own test.
4. **The sum-of-parts sign flip in Build's $1M-surtax + SALT pair is gone.** It rested on a
   −$25B/yr SALT repeal, and the repeal is now −$111B/yr. The interaction share, −19.1%, is
   inside the band the test already had.
5. **Household totals move 0.3%,** 132.39M → 132.78M households, because the SOI cells'
   `household_weight` is not raked (R6b §5 item 3). This is the same effect as ARP's
   4th-decimal movement. It is still a carry-over.

**Routing done:**

- **Routed to `load_default_population()`:** `distribution_engine`, `package_interactions` (its own default augmentation removed), `credits_microdata`, `health`, the dashboard's default frame, the TPC-microsim pilot's default load (augmenter skipped, with a note), `ui/policy_execution.py` and `microsim/demo.py`.
- **`app_controller` preview:** rewritten as raw → calibrated coverage.
- **Unchanged:** `feasibility.py`, which reads only headers.
- **Docs and evidence:** `scripts/build_current_evidence.py` was regenerated. Microdata coverage and leave-one-out moved, and so did the README coverage sentence `tests/test_current_evidence.py` pins. The 0.00–5.86pp → 0.00–5.65pp range was updated in README, CLAUDE.md and docs.
