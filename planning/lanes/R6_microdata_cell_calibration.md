# R6 — Microdata cell calibration (opt-in)

*Lane R6. Additive and opt-in: **nothing on the default data path changed**. Files owned:
`fiscal_model/microsim/soi_calibration.py`, `fiscal_model/microsim/top_tail.py`,
`scripts/run_validation_dashboard.py` (`collect_microdata`, argparse, JSON/text blocks only),
`tests/test_soi_cell_calibration*.py`, additions to `tests/test_validation_dashboard_script.py`.
`load_tax_microdata`, `distribution_engine.py`, `credits_microdata.py` and `reweight_to_soi` were
not opened for editing.*

*A prior investigation prototyped this exactly (a scratch script, never in the tree). This lane
turns it into library code, reproduces its figures through the library functions rather than by
quoting them, and says where a reproduced figure differs.*

---

## 0. Pre-registered claim

The shipped microdata (`fiscal_model/microsim/tax_microdata_2024.csv`, 78,727 CPS tax units)
carries **191.11M returns (119.0% of SOI's 160.60M)** and **$12.377T AGI (81.0% of $15.286T)**
against IRS SOI Table 1.1, TY2023. `reweight_to_soi` is called nowhere outside tests and clips
ratios to [0.1, 10], so it cannot repair the "no AGI" class (33.8M CPS units against SOI's 2.18M).

Registered before the figures below were produced:

1. A within-cell **exponential-tilt entropy calibration**, `w = w0 * exp(a + b*z)`, over SOI's
   19 AGI classes x {married (joint + separate), head of household, single} cells of **Table 1.2
   only**, hits both the cell's return count and its AGI wherever the target mean lies inside the
   cell's observed AGI range, and falls back to a count-only rescale (flagged) where it does not.
2. Aggregate returns reach 100.0% of SOI; AGI reaches about 101%, the remainder being SOI's
   negative-AGI class, which no non-negative record can represent.
3. A status-aware top-tail augmentation with a **data-derived floor** removes the synthetic-row
   defect (every synthetic record `married=1`, `household_id = household_weight = 0`, so none
   survives the household layer).
4. Downstream movement is **reported, not defended**: the distributional benchmarks are expected
   to be mostly unmoved, and one (`jct_salt_repeal_2024`) is expected to get **worse**, which is
   recorded as a regression and is not a reason to retune anything.
5. Nothing is fitted to a held-out benchmark, no benchmark target is touched, and the default
   path is byte-identical.

## 1. What shipped

| Piece | Where |
|---|---|
| `calibrate_cells_to_soi(df, year=2023, ...)` -> `(calibrated_df, CellCalibrationDiagnostics)` | `fiscal_model/microsim/soi_calibration.py` |
| `CellResult`, `CellCalibrationDiagnostics` (per-cell before/after returns and AGI, cells hit / count-only / empty, max and min weight ratio, effective sample size, remaining aggregate gaps) | same |
| `augment_top_tail(..., by_status=True)`, `derive_top_tail_floor`, `records_per_cell`, `min_cps_rows` | `fiscal_model/microsim/top_tail.py` |
| `--calibrate-cells` | `scripts/run_validation_dashboard.py` |
| 22 + 4 + 6 tests | `tests/test_soi_cell_calibration.py`, `..._benchmarks.py`, `tests/test_validation_dashboard_script.py` |

**Design points worth reading before using it.**

- *Targets.* `IRSSOIData.get_bracket_distribution_by_status(2023)` (Table 1.2 apportioned on Table
  1.1's class totals) and nothing else. Married is joint + separate. Status is `married > 0`, else
  `dependent_count > 0` -> HOH, else single.
- *Data-derived floor.* The lowest SOI class from which **every** higher class holds fewer than 20
  unweighted CPS rows. On the shipped file that is class 15, **$1.5M** (10 rows at $1.5M-2M, 7 at
  $2M-5M, none above), where the default path uses a hard-coded $2M. CPS rows inside the
  augmented classes (17 rows) are dropped; the synthetic cells replace them.
- *Collapse.* Synthetic records carry only married / unmarried, so at and above the floor
  HOH + single is one cell. The default is derived from the `source` column; it is not a flag.
- *Fallbacks are flagged, never hidden.* A cell with SOI returns and no rows is `empty` (and its
  returns are reported as `unrepresented_returns`); a cell with fewer than 5 rows, no AGI spread,
  or a target mean outside the observed range is `count-only`.
- *Synthetic rows (new path only).* Unique `household_id` (>= 10,000,000), `household_weight` =
  the record's weight, `household_persons` / `member_count` 2 or 1, and `investment_income` =
  interest + dividends + gains, which is how the CPS builder defines the column. `weight` is the
  only column calibration changes; `household_weight` is left alone on every row.
- *Not the default.* The default `augment_top_tail` call returns the same frame, row for row, as
  before (tested against the explicit-default call and against a pinned shape: 600 synthetic rows,
  `married=1`, household id and weight 0).

## 2. What moved, reproduced through the library

Command: `augment_top_tail(raw, 2023, by_status=True)` then `calibrate_cells_to_soi(...)`, no
non-filer filter (the prototype's "P3", which it recommended).

| Quantity | Default (raw CPS) | Calibrated | Prototype said |
|---|---:|---:|---|
| Returns, % of SOI | 119.0% | **100.0%** | 100.0% |
| AGI, % of SOI | 81.0% | **100.9%** | 100.9% |
| Cells (hit / count-only / empty) | n/a | **49 / 4 / 0** of 53 | n/a |
| Effective sample size | 57.5k | **36.1k** | 57k -> 36k |
| Max weight ratio, per row | n/a | **5.46** (min 0.014) | "4.45" |
| Weights vs prototype's `variants.pkl` P3 | n/a | **identical, max abs difference 0.0** | n/a |

The four count-only cells are the three class-0 ("no AGI") cells, whose AGI target is negative, and
the $1M-1.5M HOH cell (13 rows). **The 0.9% AGI surplus is SOI's no-AGI class**: its Table 1.1 total
is -$144.2B and the model has no negative-AGI record. A test asserts the gap is within 1% of that
class's size.

*On the one figure that differs.* The prototype's "4.45" is the ratio at each cell's
largest-weight row; this lane reports the largest `w_after / w_before` over **all** rows, 5.46.
Same weights, different statistic.

### Held-out aggregates (not calibrated to)

Income tax is **not** a target: the engine's `final_tax` on the calibrated population against SOI
Table 1.1 `total_tax` ($2,148B) and `taxable_income` ($11,625B).

| | Default | Calibrated |
|---|---:|---:|
| Income tax, % of SOI | 69.8% | **102.7%** |
| Taxable income, % of SOI | 83.2% | **106.2%** |

**This does not match the prototype's 100.3%, and the reason is a deliberate difference.** The
prototype left `investment_income = 0` on synthetic rows, so the engine's NIIT never applied to
them; this lane fills it as the CPS builder does. Zeroing it again reproduces **100.27%**, which is
the prototype's number to the digit. Neither figure is clean evidence: SOI's "income tax after
credits" excludes NIIT and the engine's `final_tax` includes it for every CPS row, so the cleaner
reading is "within about 3 points of SOI after being 30 points under". By AGI group, model / SOI
income tax: 30-100K 0.79 -> 0.90, 100-200K 0.97 -> 1.02, 200-500K 1.05 -> 1.05, 500K-1M 0.77 ->
1.08, $1M+ 0.26 -> 1.10. Below $30K the model books a net negative (credits) where SOI books +$10B,
and calibration does not change that.

### Distributional benchmarks (7 published tables)

Run through `run_full_cbo_jct_validation` with the calibrated frame substituted for the engine's
microdata:

| Benchmark | Default | Calibrated |
|---|---:|---:|
| `cbo_tcja_2018` | 0.00 | 0.00 |
| `jct_tcja_2019` | 2.10 | 2.10 |
| `cbo_arp_2021` (household universe) | 3.72 | **3.72** |
| `jct_salt_repeal_2024` | **5.86** | **11.01** |
| `jct_corporate_28_2022` | 2.51 | 2.51 |
| `cbo_tcja_extension_2026` | 0.74 | 0.74 |
| `cbo_pl119_21_2026` | 3.96 | 3.96 |
| mean of 7 | 2.70 | 3.44 |

**Six of seven did not move; the prototype's brief said five of seven.** Under this lane's run
every row but the SALT one is unchanged to two decimals; the extra row is not a finding about the
calibration, only a difference in what the earlier count included. ARP 2021 stays at 3.72pp (the
prototype's 4.10pp is the variant that keeps the non-filer filter, which this lane does not use).

### The SALT regression, and its cause

`jct_salt_repeal_2024` goes **5.86 -> 11.01pp** and its rating **acceptable -> needs_improvement**:

| Group | Default model share | Calibrated | JCT |
|---|---:|---:|---:|
| $500K-1M | 39.8% | 50.1% | -27.9% |
| $1M+ | 30.6% | 20.3% | -38.2% |

**This is a registered regression and the 5.86pp was a cancellation.** Giving the top tail its
true weight exposes three modelling facts the old, light tail had hidden, none of which this lane
may touch: (i) SALT is **imputed as a flat state rate on AGI** (`salt_imputation.py`), so a cap
repeal's benefit scales with AGI rather than with the itemised SALT actually paid; (ii) the **AMT
binds on every synthetic $2M+ row**, so removing the SALT cap there recovers nothing; (iii) JCT ranks
by **expanded income**, the model by AGI. All synthetic rows also carry California's state code
(as the prototype did), whose SALT rate is the highest in the table; **that bias was not measured
here** and is the first thing to test. No constant was retuned and no benchmark target touched.
`tests/test_soi_cell_calibration_benchmarks.py` records the numbers as a documented regression
and asserts nothing about improvement.

## 3. Why it is not the default

1. It makes one benchmark worse and moves three credits rows (below), one of them away from its
   published target and one past it: the aggregates it fixes (returns, AGI, taxes) are not what those rows are
   scored against.
2. The calibration targets AGI by class and status. It does not touch the things the SALT row
   actually depends on (the SALT imputation, the AMT interaction, the ranking concept), so it can
   expose them but not fix them.
3. It shrinks the effective sample from 57.5k to 36.1k, a real variance cost for a cell-level
   gain, and it leans on 800 synthetic top-tail records for the SOI classes above $1.5M.
4. Default numbers on every surface (presets, Tailor, Ask, validation gates) are pinned by
   `cold_holdout.py`, the dashboard and the leave-one-out suite; this lane leaves all three
   byte-identical (section 5).

## 4. What an owner decision to make it the default would move

Three derived (not fitted) credits rows, scored on the calibrated population instead of the
shipped one ($B, ten-year; reproduced through the library functions):

| Row | Default | Calibrated | Published target |
|---|---:|---:|---:|
| `biden_ctc_2021` | -1,528.5 | **-1,440.5** | -1,597.0 |
| `ctc_extension` | -714.2 | **-799.6** | (no single target; JCT/CRS ranges) |
| `biden_eitc_childless` | -110.4 | **-176.8** | -162.6 |

Against the published targets the two rows that have one move in **opposite** directions: CTC
2021 gets *worse* (4.3% under -> 9.8% under) and EITC childless gets *better* in magnitude but
flips sign (32.1% under -> 8.7% over). Neither is a measurement of the credits mechanism; both are
the population change, and a decision to adopt the calibrated frame would adopt that movement for
every derived-mode consumer of `credits_microdata._base_population`.

Plus the SALT distributional row above (5.86 -> 11.01pp, rating change), and the dashboard's
SOI-calibration block, whose headline coverage would read 100.0% / 100.9% rather than 119.0% /
81.0%. **Not** moved: Tier 1, the fitted tier, the reconstruction tier, leave-one-out, and 6 of 7
distributional rows. The adoption itself would touch `load_tax_microdata` and
`credits_microdata.py`, which this lane did not open.

## 5. Confirmations

- `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json | sha256sum` equals the baseline
  capture (`69f52cf3...a37a9dd`).
- `python scripts/run_validation_dashboard.py` (no flags) and
  `python scripts/run_loo.py --donor-matrix`: `diff` against the baseline captures is empty.
- `--calibrate-cells` is rejected together with `--augment-top-tail` / `--filter-to-filers`
  (it does its own augmentation and runs without the filter). With the flag, the JSON gains
  `calibration.cell_calibration`; without it the key is absent.
- Tests: `tests/test_soi_cell_calibration.py` (cell targets hit to 1e-6, idempotence, empty-cell
  and fallback flagging, default path byte-identical, input not mutated, status-aware cells
  reproduce Table 1.2 returns), `tests/test_soi_cell_calibration_benchmarks.py` (recorded movement
  and the SALT regression, not an expectation of improvement), and six dashboard tests.

## 6. Carry-overs

- **Test the California assumption**: draw synthetic `state_fips` from the weighted CPS
  distribution at $500K+ and re-run the SALT row. Not done here.
- **`household_weight`** is untouched by calibration, so on the household universe a calibrated
  synthetic row's household weight is its pre-calibration weight. ARP 2021 does not move, but a
  future household-universe benchmark at the top should be checked before relying on it.
- **A negative-AGI record class** would close the last 0.9% of AGI honestly; the CPS file has none.
- `scripts/run_validation_dashboard.py:135` carries one pre-existing mypy error
  (`asdict` on a possibly-type dataclass) that this lane did not introduce and left alone.
