# Wave 6 lane — project the corporate base off the vintage, not off 4%/yr

*Pre-registered 2026-09-05 against `main` @ `35e20cc`, in this lane's first
commit, before any module was touched. Outturn appended at the end, in the last
commit.*

Scope: the one mechanism recommended by `planning/memos/CORPORATE_PER_POINT_YIELD.md`
§7(i) — **Lane C, project the corporate base off the scored vintage** — which is
the modelling half of that memo's recommendation. The target-side half (§7(ii))
is a provenance lane running concurrently and this lane touches none of its
files. Under `planning/MODELING_IMPROVEMENT.md` §1's principles (§1.3
pre-register before any code, §1.5 no promise of attainment), §4's prohibitions,
and owner Decisions 1 and 6.

The row this lane may move is `cbo_opt64_corporate_rate_1pp`, which Wave 5 B
left at **62.3%** as a pre-registered regression and which is the largest single
row in Tier 1. The memo says why it is 62.3% and not 47.1%: W5-B replaced a
stale fitted base with SOI's published one and kept the module's flat 4%/yr
aging, so the base now *starts* right and *grows* wrong. Against CBO's own
February 2024 corporate receipts — which grow at **1.44%/yr** over FY2026-2034,
and 1.21%/yr over the full FY2025-2034 —
a base compounding at 4% reaches **101.6% of the average base the baseline
implies exists** by FY2034 (memo §4, table 4). No marginal base can exceed the
average base it is part of. That is an internal inconsistency, independent of
any target, and it is what this lane closes.

## 1. Starting numbers

All from the branch point, `35e20cc`.

### The battery — `python scripts/cold_holdout.py --json`

| tier | n | mean | median | within 15 | within 25 |
|---|--:|--:|--:|--:|--:|
| Out-of-sample (Tier 1) | 26 | **15.9%** | 11.4% | 16 | 22 |
| Calibrated reference (fitted) | 21 | **1.7%** | 0.0% | 21 | 21 |
| Unfitted reconstructions | 33 | **54.4%** | 28.4% | 9 | 14 |

Tier 1 error mass is **412.9** units over 26 cases. `cbo_opt64` carries **62.3**
of it, **15.1%** — the largest single row, ahead of `cbo_opt46_agi_surtax_1pp_20k`
at 44.7.

### The three rows this module owns

| Row | Tier | Official | Model | Err | Provenance |
|---|---|--:|--:|--:|---|
| `cbo_opt64_corporate_rate_1pp` | out-of-sample | −135.7 | **−220.28** | **62.30%** | `line_item` (CBO 60557 option 64; the memo shows the *estimator* is JCT) |
| `biden_corporate_28` | calibrated, fitted | −1,347.0 | −1,397.21 | **3.73%** | `line_item` (Green Book FY2025; the memo shows the row is rate **plus GILTI**) |
| `trump_corporate_15` | calibrated, **unfitted** | +1,920.0 | +1,491.76 | **22.30%** | **`model_estimate`** — the target is the model's own output |

`trump_corporate_15` left the fitted tier in PR #119, when signing the reported
offset moved it 0.1% → 22.3% and the sweep reclassified it rather than retuning
the constant that had been compensating for the sign. Both calibrated rows score
through `CORPORATE_APP_MODE = reported`, so this lane — which touches `derived`
only — must leave both where they are.

### Both benchmarks, both modes — `validate_all_corporate(mode=...)`

| Benchmark | Target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `biden_corporate_28` | −$1,347.0B | −$1,397.21B | −3.73% | −$1,452.14B | −7.81% |
| `trump_corporate_15` | +$1,920.0B | +$1,491.76B | −22.30% | +$1,698.57B | −11.53% |
| **Mean abs** | | | **13.02%** | | **9.67%** |

Derived already ranks ahead of reported on Decision 1's rule, and has since
PR #119 — because signing the reported offset moved the `model_estimate` row
22 points, not because derived got better. **This lane does not flip
`CORPORATE_APP_MODE`.** The owner re-measures Decision 1 after this lane and the
concurrent provenance lane both land; a second corporate benchmark is being
re-sourced and a third registered, which changes the population the comparison
is taken over.

### Leave-one-out — `python scripts/run_loo.py --donor-matrix`

Aggregate **29.6% mean / 19.1% median over 18 derivable cases**, 8/18 within
15%, 4 not cross-validatable. Modules: Payroll, Estate, AMT, Credits,
Expenditures, CapitalGains. **There is still no Corporate row**, before or after
this lane — that is `MODELING_IMPROVEMENT.md` §6.2 item 23, a `loo.py` edit, and
no modelling lane may make one.

### The shipped surfaces

All 51 scoring `PRESET_POLICIES` entries and the Tailor corporate rows are
captured at the branch point. The corporate ones:

| Surface | Now |
|---|--:|
| 🏢 Biden Corporate 28% | −1,397.21 |
| 🏢 Trump Corporate 15% | +1,491.76 |
| Tailor corporate −6pp / −2pp / +1pp / +2pp / +5pp / +7pp | +1,197.61 / +399.20 / −199.60 / −399.20 / −998.01 / −1,397.21 |

Every one of them scores `reported`.

## 2. The mechanism

### What the derived path does today

`fiscal_model/corporate.py`, `derived` mode, in one line:

```
Δτ × [SOI income subject to tax, TY2022 = 2,879.10] × 1.04^(t−2022)
     × [credit realization = 0.708526]     # SOI after ÷ before credits
     × [IRC §6655 phase: 0.75, then 0.99038]
```

The `1.04^(t−2022)` is `CORPORATE_BASE_GROWTH`, chosen in W5-B to be the
*engine's* own corporate growth constant so that the module carried one growth
assumption rather than two. It is not sourced to anything about corporate
profits; it is an internal consistency choice, and it is 2.8× CBO's own
projected growth in corporate receipts.

### What it will do

```
Δτ × [CBO projected corporate receipts, FY t] × [base per dollar of receipts]
     × [IRC §6655 phase, computed on the path]
```

**The base series.** CBO's own projected **corporate income tax receipts**, by
fiscal year, transcribed to
`fiscal_model/data_files/corporate/cbo_corporate_receipts.csv` from *The Budget
and Economic Outlook: 2024 to 2034* (February 2024), publication 59710, Table
1-1, FY2025–2034:

```
FY    2025   2026   2027   2028   2029   2030   2031   2032   2033   2034
     494.1  491.4  484.1  490.7  500.9  510.6  518.7  519.2  533.4  550.8   Σ 5,094.0
```

That is the vintage the CBO Options battery is scored on
(`CBO_OPTIONS_REVENUE_BASELINE` = `BaselineVintage.CBO_FEB_2024`), the vintage
CBO's December 2024 Options volume names for its revenue options, and the
vintage `cbo_opt64`'s target is priced against. It is the same publication the
payroll lane's wage path comes from, and the same shape of input: **a published
CBO path read from disk, not a level read off the repository's baseline
object.** Outside the tabulated window the nearest observed growth rate is
continued, exactly as `payroll.covered_earnings()` does.

**Why a receipts path and not a profits path.** `receipts(t) / τ` is the base
which, taxed at the statutory rate, reproduces the receipts the vintage
projects. It already nets credits, net operating losses and profit shifting —
which is what makes it the right denominator and the right *numerator* here,
because those are exactly the things that stand between a statutory rate and a
dollar of revenue. A pre-tax profits path (NIPA, or CBO's own economic
projections) would need every one of them re-applied on top, each with its own
assumption. The memo's §3 defines this quantity and calls it the average base;
its §5 counterfactual is computed on it.

**The anchor, and why SOI stays load-bearing.** The level is not
`receipts(t)/0.21`. It is SOI's own published measurement of the same quantity,
re-based to the vintage's path:

```
BASE_PER_DOLLAR_OF_RECEIPTS
    = [SOI income subject to tax, TY2022 × SOI credit realization, TY2022]
      ÷ [Treasury actual net corporate receipts, FY2022]
    = (2,879.101 × 0.708526) / 424.865
    = 2,039.92 / 424.865
    = 4.80133
```

against `1/0.21 = 4.76190` — **0.83% apart**. One ratio, measured once, on the
last completed year both source documents cover, and never on a projection year
— the same construction and the same rule as `payroll.COVERED_EARNINGS_TO_WAGES`.
The 0.83% is the whole content of the anchor: two published series, built from
different data by different agencies, measure the credit-realized statutory
corporate base for the same year and agree to within 1%. That agreement is what
makes replacing `SOI base × 1.04^t` with `receipts path × 4.80133` a **change of
vintage rather than a change of concept**, and it is a test rather than a
remark. The actual-receipts series is transcribed to
`fiscal_model/data_files/corporate/treasury_mts_corporate_receipts.csv` from
Treasury's Monthly Treasury Statement Table 4 via the Fiscal Data API
(`/v1/accounting/mts/mts_table_4`, line code 130, September month-end
year-to-date), FY2015–FY2025 — the same source the memo's §9 names.

Note what drops out: the `credit_realization_ratio` no longer multiplies the
base *twice*. It is inside the anchor (SOI's base is credit-realized there) and
inside the path (receipts are credit-realized by definition). Applying it again
would be the double-count the memo warns about in a different guise.
`credit_realization_ratio()` and `section_904_realization_ratio()` stay in the
module as the anchor's own construction and its cross-check.

**IRC §6655 stops being closed-form.** Today the settlement convolution
`FY_t = 0.75·L_t + 0.25·L_{t−1}` collapses to a constant `0.75 + 0.25/(1+g)`
because `L` grows at a constant `g`. On a path it does not, so the phase factor
becomes the convolution itself:

```
phase(t) = 0.75                                        for t = start_year
phase(t) = 0.75 + 0.25 × B(t−1)/B(t)                   for t > start_year
```

which degenerates to the old closed form when the base grows at a constant rate.
It stays expressed as a phase factor so the behavioural offset is timed with it.

**The engine.** `CorporateTaxPolicy` gets `uses_projected_base()` — true in
`derived` mode — and `_score_growth_tax_policy_year` passes `year=year` and sets
`growth_rate = 0.0` for it, exactly as it already does for
`PayrollTaxPolicy.uses_covered_earnings_base()`. The rate channel then carries
its own path. The four non-rate channels (GILTI/FDII, R&D, bonus depreciation,
book minimum) are **unchanged constants** and keep growing at
`CORPORATE_BASE_GROWTH` inside the module, so nothing about them moves except
where the engine applies their growth.

**What does not change.** `PROFIT_SHIFTING_SEMI_ELASTICITY = 0.8` (Heckemeyer &
Overesch), `corporate_elasticity = 0.25`, `BASELINE_TAXABLE_PROFITS_BILLIONS =
1900.0`, `ESTIMATED_PAYMENT_SAME_FY_SHARE = 0.75`, every factory, every
non-rate constant, and the whole of `reported` mode.

### The vintage question, answered honestly

The brief for this lane says the base should "move with the vintage the policy
is scored on". Two things are true and they pull apart:

1. **The published path is one vintage's.** Only February 2024's *annual*
   corporate receipts path could be sourced here. `cbo.gov` returns HTTP 403 to
   this environment on every URL, and the Wayback Machine has **no snapshot** of
   `51118-2025-01-budgetprojections.xlsx` or `51118-2026-02-budgetprojections.xlsx`
   (checked, `archived_snapshots: {}`). The memo's §3 carries 10-year *totals*
   for the January 2025 and February 2026 vintages (4,766.7 and 4,976.7) but no
   annual paths, and inventing a shape for them would be exactly the failure
   §1.1 names. The CSV therefore carries a `vintage` column with one block, and
   adding a second is a data edit rather than a code edit. **That is a
   carry-over, and it is written as one in §6.**
2. **Reading the repository's own baseline object instead would be worse than
   what it replaces**, which is a finding this lane records rather than a choice
   it defends. `CBOBaseline.generate().corporate_income_tax` is a base level
   times a growth rule, not CBO's published table: on `CBO_FEB_2024` it grows at
   **4.88%/yr** against CBO's own 1.4%, and under `use_real_data=True` it
   returns the **same** path for all three vintages (402.1 → 614.3), because
   corporate receipts are derived from an IRS-to-individual-tax ratio that has
   no vintage in it. Reading the object would make the derived score neither
   CBO's nor vintage-dependent.

So what moves with the vintage here is the **window**: FY2025–2034 and
FY2026–2035 read different years of the published path, and the first year of
the window carries §6655's 0.75. And the derived score continues to be
**independent of the baseline object**, which is the property
`validation/cbo_options.py` states for every uncalibrated shape and which
`tests/test_corporate_derived.py::test_derived_reads_no_baseline_level` pins.
The memo's §7(i) expected that claim to need re-scoping; on this construction it
does not, because a transcribed CBO table is an input like SOI's, not a level
read off the scorer.

### The thing this lane may not do

**It may not assert a marginal-realization ratio.** The memo's §6 prints the
number that would land the row — a total factor of **0.5785**, against JCT's own
steady-state share of 0.590 — and forbids it, because JCT's 0.59 is its answer
read backwards and is not separable from the behavioural term the module already
applies. The factor this lane ships is **4.80133 base-dollars per receipts
dollar, which is `1.0083/τ`**: a 0.83% wedge between two published measurements
of one year's base, not a share of anything. After it, the model still prices
**about 80% of the vintage's own average base** per point — Treasury's
neighbourhood, above JCT's 55.9% — and the row still reads 44.5%. A lane that
had asserted a share would have landed it.

## 3. The prediction

Hand arithmetic on the published inputs, computed before the module was opened.

### Rows I expect to move

| Row | Now | Predicted |
|---|--:|---|
| Tier 1 `cbo_opt64_corporate_rate_1pp` | −220.28, **62.30%** | **−196.1 ± 2, 44.5 ± 1.5%** |
| Tier 1 mean / median | 15.9% / 11.4% | **15.2% / 11.4%** |
| Tier 1 within 15 / within 25 | 16 / 22 | **16 / 22**, unchanged |
| `biden_corporate_28` **derived** | −1,452.14, 7.81% | **−1,292.6 ± 10, 4.0 ± 1.0%** |
| `trump_corporate_15` **derived** | +1,698.57, 11.53% | **+1,545.2 ± 15, 19.5 ± 1.5%** |
| Decision 1 derived mean | 9.67% | **11.8 ± 1.0%** |
| CI gate `--max-mean-error 20 --min-within-25pct 21` | passes | **passes** (15.2 ≤ 20; 22 ≥ 21) |

The year-by-year build for `cbo_opt64`, which is what the outturn will be checked
against:

| FY | receipts | base | static | phase | revenue | deficit |
|---|--:|--:|--:|--:|--:|--:|
| 2025 | 494.1 | 2,372.3 | 23.723 | 0.75000 | 17.793 | −14.661 |
| 2026 | 491.4 | 2,359.4 | 23.594 | 1.00137 | 23.626 | −19.468 |
| 2027 | 484.1 | 2,324.3 | 23.243 | 1.00377 | 23.331 | −19.225 |
| 2028 | 490.7 | 2,356.0 | 23.560 | 0.99664 | 23.481 | −19.348 |
| 2029 | 500.9 | 2,405.0 | 24.050 | 0.99491 | 23.927 | −19.716 |
| 2030 | 510.6 | 2,451.6 | 24.516 | 0.99525 | 24.399 | −20.105 |
| 2031 | 518.7 | 2,490.4 | 24.904 | 0.99610 | 24.807 | −20.441 |
| 2032 | 519.2 | 2,492.9 | 24.929 | 0.99976 | 24.922 | −20.536 |
| 2033 | 533.4 | 2,561.0 | 25.610 | 0.99334 | 25.440 | −20.962 |
| 2034 | 550.8 | 2,644.6 | 26.446 | 0.99210 | 26.237 | −21.619 |
| | | | | | | **−196.08** |

Two notes on that table. The phase **exceeds 1.0** in FY2026 and FY2027, which
looks wrong and is not: CBO's projected receipts *fall* in those years, so a
fiscal year that collects a quarter of the previous, larger tax year's liability
collects more than its own. And the memo's §5 counterfactual prints −193.29 for
the same policy, 1.4% below: it keeps the closed-form 0.99038 phase, which
assumes the constant growth this lane removes, and it prices the base at exactly
`receipts/τ` rather than at SOI's anchored 1.0083 of it.

### Rows I expect NOT to move, to the decimal

| Row | Now | Predicted |
|---|--:|---|
| `biden_corporate_28` **reported** | −1,397.21, 3.73% | unchanged |
| `trump_corporate_15` **reported** | +1,491.76, 22.30% | unchanged |
| Fitted calibrated tier | 21 @ 1.7% | unchanged, 0 of 21 rows |
| Unfitted reconstructions | 33 @ 54.4% | unchanged, 0 of 33 rows |
| Leave-one-out | 18 @ 29.6% / 19.1% / 8 | **byte-identical output** |
| Every other Tier 1 row | 25 rows | unchanged, to the decimal |
| Every shipped preset | 51 scoring entries | unchanged |
| Tailor corporate rows | 6 measured steps | unchanged |
| `CORPORATE_APP_MODE` | `reported` | unchanged — not this lane's to flip |
| Decision 6 caption | none owed | **none owed** — no shipped number moves |

### The marginal share, which is the point of the lane

The memo's §4 table 4, recomputed. Today the derived path's implied marginal
base runs from 60.3% of the vintage's own average base in FY2025 to **101.6%** in
FY2034. After:

| FY | 2025 | 2026 | 2027 | 2028 | 2029 | 2030 | 2031 | 2032 | 2033 | 2034 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| today | 0.603 | 0.832 | 0.878 | 0.901 | 0.919 | 0.937 | 0.959 | 0.997 | **1.009** | **1.016** |
| predicted | 0.623 | 0.832 | 0.834 | 0.828 | 0.827 | 0.827 | 0.828 | 0.831 | 0.825 | 0.824 |

Flat at `(1 − 0.8 × 0.22) × 1.0083 = 0.831` after the first year, by
construction: the drift is gone because the numerator and the denominator are
now the same series. Window average **80.8%** against today's 90.8%, against
Treasury's 79.5%, PWBM's 64.4%, JCT's 55.9% and Tax Foundation's 55.1%. **The
model stops being higher than every published estimate and lands on the highest
one.** That is the level the memo attributes to scope and estimator, and this
lane does not close it.

### Where I expect to be wrong

- **`trump_corporate_15` derived gets worse**, 11.53% → about 19.5%, and I am
  registering that rather than discovering it. Its target is provenance
  `model_estimate` — the model's own output written down as an expectation — so
  moving away from it is not evidence of anything, in either direction. About a
  fifth of that row is `extend_bonus_depreciation`'s unsourced −$28B/yr, which
  this lane does not open. It is the reason Decision 1's derived mean gets
  *worse* (9.67% → 11.8%) while the one corporate benchmark with a document
  behind it gets *better* (7.81% → 4.0%), and it is why the mean is the wrong
  statistic here.
- **The anchor mixes a tax year and a fiscal year.** SOI's TY2022 base is a tax
  year; Treasury's FY2022 receipts are a fiscal year, and under §6655 a fiscal
  year collects three quarters of its own tax year and one quarter of the
  previous one. Applying that blend to the anchor instead gives 410.6 against
  424.9 — **3.4% apart, worse than the naive 0.83%** — which says the two series
  disagree by more than the timing convention explains and that reading either
  agreement as precision would be over-reading. The lane takes the simple
  construction, states the tolerance it needs (under 2%), and does not tune the
  anchor to improve it.
- **The path is one vintage's, and the app runs on another.** FY2035 is an
  extrapolation at the FY2033→FY2034 growth rate (3.26%). Nothing shipped reads
  it, because the app runs `reported`, but a future flip of
  `CORPORATE_APP_MODE` would.
- **CBO's own path may be the wrong denominator for a *marginal* question.**
  `receipts/τ` is an average base. Nothing in this lane claims the marginal
  base equals it; the model prices 80% of it, and the remaining 20% is the
  behavioural term. Whether the true marginal share is 0.55 (JCT), 0.64 (PWBM)
  or 0.80 (Treasury) is the memo's §5(c) residual and needs credit carryforward
  stocks, CAMT and an individual-side feedback, none of which is published in a
  source this module reads.
- **The magnitude.** 44.5% is arithmetic on a spreadsheet. A landing outside
  40–49% means something else changed and gets written into §5.

## 4. Falsification tests

Each of these is a specific thing that, if it fires, is a finding and goes in
§5 rather than being quietly absorbed.

1. **Any non-corporate Tier 1 row moves.** 25 rows must be identical to the
   decimal.
2. **`biden_corporate_28` reported moves off −1,397.21.** The fitted row scores
   through a mode this lane does not touch.
3. **Any calibrated-tier row moves.** Fitted 21 @ 1.7% and reconstructions
   33 @ 54.4%, both counts and both means.
4. **`run_loo.py --donor-matrix` is not byte-identical.**
5. **Any of the 51 preset totals or 6 Tailor corporate rows moves.**
6. **`cbo_opt64` lands outside 40–49%.**
7. **The derived score becomes vintage-dependent** — i.e.
   `test_derived_reads_no_baseline_level` fails, which would mean the path is
   being read off the scorer rather than off disk.
8. **The anchor wedge exceeds 2%** in either direction, which would mean SOI and
   Treasury do not measure the same quantity and the splice is not legitimate.

## 5. Outturn

*Appended 2026-09-05, after the code. Numbers from
`python scripts/cold_holdout.py --json`, `python scripts/run_loo.py
--donor-matrix`, `python scripts/run_validation_dashboard.py` and
`validate_all_corporate(mode=...)` on the finished branch.*

### Against the pre-registration

| Row | Predicted | Actual | |
|---|---|---|---|
| `cbo_opt64_corporate_rate_1pp` | −196.1 ± 2, 44.5 ± 1.5% | **−196.08, 44.50%** | as registered |
| Tier 1 mean / median | 15.2% / 11.4% | **15.2% / 11.4%** | as registered |
| Tier 1 within 15 / 25 | 16 / 22 | **16 / 22** | as registered |
| `biden_corporate_28` **derived** | −1,292.6 ± 10, 4.0 ± 1.0% | **−1,292.62, +4.04%** | as registered |
| `trump_corporate_15` **derived** | +1,545.2 ± 15, 19.5 ± 1.5% | **+1,545.24, −19.52%** | as registered |
| Decision 1 derived mean | 11.8 ± 1.0% | **11.78%** | as registered |
| `biden_corporate_28` **reported** | unchanged | **−1,397.21, −3.73%** | as registered |
| `trump_corporate_15` **reported** | unchanged | **+1,491.76, −22.30%** | as registered |
| Fitted calibrated tier | 21 @ 1.7%, no row moves | **21 @ 1.7%**, 0 of 21 moved | as registered |
| Unfitted reconstructions | 33 @ 54.4%, no row moves | **33 @ 54.4%**, 0 of 33 moved | as registered |
| Leave-one-out | byte-identical | **byte-identical** | as registered |
| Every other Tier 1 row | 25 unchanged | **25 unchanged**, to the decimal | as registered |
| Shipped presets / Tailor rows | unchanged | **51 + 6 unchanged**, byte-identical sweep | as registered |
| `CORPORATE_APP_MODE` | `reported` | **`reported`** | as registered |
| Decision 6 caption | none owed | **none owed** | as registered |
| CI gate `--max-mean-error 20 --min-within-25pct 21` | passes | **exit 0** | as registered |

**Every registered figure landed, including the ten-row year-by-year build**,
which the engine reproduced to the third decimal on every line — receipts, base,
phase, revenue and deficit — from a spreadsheet computed before the module was
opened. `3,515 tests pass` (7 skipped), 9 of them new. The whole
`run_validation_dashboard.py` output differs from the branch point by **one
line**, the Tier 1 mean; it exits 1 before and after, identically, on `runtime`
(Python 3.14.0 against a supported `>=3.10,<3.14`) and `microdata` (SOI 2023
coverage 119% returns / 81% AGI), neither of which this module touches, verified
against a stashed tree at the branch point.

The CI thresholds needed no change and the workflow's own rule says why:
`ceil(15.2 × 1.25)` rounded up to the nearest 5 is still **20**, and `22 − 1`
is still **21**. A modelling lane may not edit them either way; this is only the
note that the rule re-derives to what is already there.

### Reported vs derived, per benchmark — the Decision 1 table

| Benchmark | Target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `biden_corporate_28` | −$1,347.0B | −$1,397.21B | −3.73% | **−$1,292.62B** | **+4.04%** |
| `trump_corporate_15` | +$1,920.0B | +$1,491.76B | −22.30% | **+$1,545.24B** | **−19.52%** |
| **Mean abs** | | | **13.02%** | | **11.78%** |

Derived still ranks ahead of reported, as it has since PR #119, and by less than
it did. `CORPORATE_APP_MODE` **stays `reported`**: flipping it is the owner's
call after the concurrent provenance lane lands, and the numbers to decide it on
are below rather than in a mean.

### What the lane bought, and what it did not

**1. The marginal share stopped drifting.** The share of the vintage's own
average base the derived path prices, year by year:

| FY | 2025 | 2026 | 2027 | 2028 | 2029 | 2030 | 2031 | 2032 | 2033 | 2034 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| before | 0.603 | 0.832 | 0.878 | 0.901 | 0.919 | 0.937 | 0.959 | 0.997 | **1.009** | **1.016** |
| after | 0.623 | 0.832 | 0.834 | 0.828 | 0.827 | 0.827 | 0.828 | 0.831 | 0.825 | 0.824 |

Window average **90.8% → 80.8%**. The impossibility is gone: numerator and
denominator are now the same series, so what is left is the behavioural factor
times the anchor wedge, `(1 − 0.8 × 0.22) × 1.0083 = 0.831`, flat by
construction.

**2. The level did not move much, and that was the point.** The model was above
every published estimate on this window and is now above every one but Treasury:
Tax Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury 79.5%, **model 80.8%**.
Twenty of the row's sixty-two points were a vintage problem. The remaining
forty-four are the memo's §5(c) residual — credit carryforwards under §38(c) and
§904(c), CAMT, and the individual-side dividend interaction — and none of them
is in this module's power to close from a published source.

**3. The derived path crossed its own target.** `biden_corporate_28` derived went
from **−7.81% (over)** to **+4.04% (under)**, and the sign matters: that target
is a rate **plus GILTI** row (memo §2, correction 2) scored against a factory
that sets `gilti_rate_change=0.0`, so under-predicting it is the direction scope
alone would produce. It over-predicted before, which needed the base error to be
larger than the scope error.

### Falsification results

All eight were checked and **none fired**.

| # | Test | Result |
|---|---|---|
| 1 | Any non-corporate Tier 1 row moves | 25 rows identical to the decimal |
| 2 | `biden_corporate_28` reported moves | −1,397.21, unchanged |
| 3 | Any calibrated-tier row moves | 0 of 21 fitted, 0 of 33 reconstructions |
| 4 | `run_loo.py --donor-matrix` not byte-identical | byte-identical |
| 5 | Any preset or Tailor row moves | 51 + 6, byte-identical sweep |
| 6 | `cbo_opt64` outside 40–49% | 44.50% |
| 7 | Derived score becomes vintage-dependent | `test_derived_reads_no_baseline_level` passes |
| 8 | Anchor wedge exceeds 2% | 0.83%, pinned by a test |

### Findings

1. **The repository's own baseline object is not the vintage's path, and reading
   it would have made this worse.** `CBOBaseline.generate().corporate_income_tax`
   on `CBO_FEB_2024` grows at **4.88%/yr** — *faster* than the 4% constant this
   lane removed and 3.4× CBO's own 1.44% — because the corporate line is a base
   level times `real GDP growth + inflation + a corporate profit premium`. Worse,
   under `use_real_data=True` (the app's default) it returns the **identical**
   path for all three vintages, 402.1 → 614.3, because `base_corporate_tax` is
   set from an IRS-to-individual-income-tax ratio that has no vintage in it. So a
   score reported as "on the February 2024 baseline" has a corporate receipts
   line that is neither February 2024's nor distinguishable from February 2026's.
   This is a green-tier defect that no corporate lane can fix and that nothing
   currently reads for a scored quantity; it is finding 1 because it is the
   reason this lane reads a transcribed CBO table instead, and it is carry-over 2
   below.
2. **A phase factor above 1.0 is right here, and it is the first one.** CBO's
   projected corporate receipts *fall* in FY2026 and FY2027, so a fiscal year
   collecting a quarter of the previous, larger tax year collects more than its
   own: 1.00137 and 1.00377. Every other phase factor in the repository is a
   fraction, and a reviewer's instinct will be that this is a bug. It is the
   §6655 convolution behaving correctly on a non-monotone path, and it is pinned
   by a test that asserts both signs.
3. **The anchor's 0.83% agreement is not evidence about timing.** SOI's TY2022
   base is a tax year and Treasury's FY2022 receipts a fiscal year. Applying the
   module's own §6655 blend to reconcile them — `0.75 L(TY2022) + 0.25 L(TY2021)`
   — returns **410.60 against the actual 424.87, 3.4% apart**, *worse* than the
   naive 0.83%. So the two series disagree by more than the timing convention
   explains, the naive agreement is partly coincidence, and the honest claim is
   only the one the lane makes: they agree to within the 2% the splice needs. The
   lane did not tune the anchor to improve either number.
4. **Decision 1's mean moved the wrong way while its only published row moved the
   right way.** Derived 9.67% → 11.78%; `biden_corporate_28` 7.81% → 4.04%. The
   whole of the rise is `trump_corporate_15`, whose target is provenance
   `model_estimate` — the model's own output written down — so the statistic that
   decides the app default is decided by a row that measures nothing about the
   world. The module's `CORPORATE_APP_MODE` docstring now carries the per-row
   table and says so; the mean is carried beside it rather than instead of it.
5. **CBO's own rounding is visible in the transcription.** The ten annual values
   sum to **5,093.9** against the **5,094.0** CBO prints as the total — the same
   artefact the alternatives CSV shows on Option 64 itself, where Table 1-1 gives
   136.0 and the alternatives file 135.7. The test asserts the total to a tenth
   rather than to the cent, and says why.
6. **The row's `known_limitations` text is now partly stale, and this lane did
   not touch it** because a concurrent provenance lane owns it. Two sentences to
   revisit: "the base is IRS SOI Table 11's published income subject to tax …
   realized at SOI's own after-credits/before-credits ratio (0.7085)" — both
   quantities are still read, but as the *anchor* rather than as two multipliers,
   and the ratio no longer multiplies the path; and "that base is 34% larger than
   the fitted one" — the FY2025 base is now **24.9%** larger ($2,372.3B against
   $1,900B), because the projection starts three years of 4%/yr lower than the
   aging did.

### What the lane did not do

- Did not touch any target, `preregistered.py`, `holdout.py`, `loo.py`,
  `target_revisions.py`, `benchmark_sources.py`, `scenarios.py`,
  `cbo_scores.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`, the corporate rows'
  `known_limitations` text, any yardstick script or any CI threshold.
- Did not retune `corporate_elasticity`, `PROFIT_SHIFTING_SEMI_ELASTICITY`,
  `BASELINE_TAXABLE_PROFITS_BILLIONS`, `ESTIMATED_PAYMENT_SAME_FY_SHARE` or any
  fitted annual. No constant in the module changed value.
- **Did not assert a marginal-realization ratio.** The factor shipped is
  `1.0083/τ`, a wedge between two published measurements of one year's base. The
  number that would land the row — a total factor of 0.5785, against JCT's own
  steady-state 0.590 — is printed by the reconciliation script and was not
  approached: the model still prices 80.8% of the average base.
- Did not flip `CORPORATE_APP_MODE`, so no shipped number moved and no
  Decision 6 caption is owed. The Tailor corporate rows and both corporate
  presets are byte-identical.
- Did not open `reported` mode at all. Its base, its offset and its growth are
  where PR #119 left them.
- Did not re-derive the four non-rate channels. `GILTI_REVENUE_BILLIONS`,
  `FDII_COST_BILLIONS`, the −$12B R&D annual, the −$28B depreciation annual and
  the $100B book-minimum base are all still unsourced. What changed for them is
  only bookkeeping: in derived mode the engine's growth is off for the whole
  policy, so the module grows those four itself at the same
  `CORPORATE_BASE_GROWTH` it always did, and their contribution is unchanged to
  the cent.
- Did not build credit carryforwards, CAMT or the individual-side interaction,
  which are where the 44 remaining points of `cbo_opt64` live. Each needs a
  quantity that is not published in a source this module reads, and each would
  arrive as a constant that landed on CBO by construction.
- Did not adjust SOI's TY2022 anchor for §174 R&D capitalisation or the
  bonus-depreciation phase-down. The memo sizes that at 11.1% as an upper bound
  and shows it takes the row to 46.1% rather than to CBO.

## 6. Carry-overs this lane opens

Sequencing is the owner's; each names the artefact it lives in.

1. **Transcribe the January 2025 and February 2026 corporate receipts paths.**
   `fiscal_model/data_files/corporate/cbo_corporate_receipts.csv` has a `vintage`
   column and one block in it, and `cbo_receipts_by_fiscal_year` raises rather
   than borrowing another vintage's numbers, so adding them is a data edit.
   Blocked here: cbo.gov returns HTTP 403 to this environment and the Wayback
   Machine holds no snapshot of `51118-2025-01-budgetprojections.xlsx` or
   `51118-2026-02-budgetprojections.xlsx`. The memo's §3 has the 10-year totals
   (4,766.7 and 4,976.7) but no annual shape. Same blocker as
   `MODELING_IMPROVEMENT.md` §6.2 item 16.
2. **`CBOBaseline`'s corporate receipts projection** (finding 1). Not a corporate
   lane's to fix and not read by any scored quantity today, but a vintage whose
   corporate line is identical across all three vintages under the app's own
   default is a live defect in the green tier, and it is the reason the
   distinction between "the vintage" and "the repository's reconstruction of the
   vintage" had to be made explicit in this module's docstrings.
3. **The corporate module still has no leave-one-out row** —
   `MODELING_IMPROVEMENT.md` §6.2 item 23, unchanged. It now has *three*
   published series in its derived path and one fitted constant in its reported
   path, and still nothing cross-validating either.
4. **Decision 1 for corporate is due a re-measure**, on a population that is
   moving: a second corporate benchmark is being re-sourced and a third
   registered by the concurrent provenance lane, and the statistic currently
   turns on a `model_estimate` row (finding 4).
5. **The four non-rate constants.** Unsourced, untouched, and `trump_corporate_15`
   derived is about a fifth bonus depreciation — which is a fifth of the row that
   decides Decision 1.
6. **The row's `known_limitations` text** (finding 6), which is the provenance
   lane's to write.
