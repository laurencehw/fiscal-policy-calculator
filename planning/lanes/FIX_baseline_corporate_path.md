# Fix lane — `CBOBaseline`'s corporate receipts line, and the dashboard's blind spot

*Pre-registered 2026-09-06 against `main` @ `a251b32`, in this lane's first
commit, before any module was touched. Outturn appended at the end, in the last
commit.*

Two green-tier correctness items from `planning/MODELING_IMPROVEMENT.md` §6.2:
**item 30** (`CBOBaseline`'s corporate receipts path is neither a vintage nor
distinguishable between vintages — `W6_corporate_base_projection.md` finding 1
and its carry-over 2) and the dashboard blind spot recorded in
`SWEEP_offset_sign.md` §7.5 (the validation dashboard's output was byte-identical
across a change that moved both calibrated tiers, because it prints Tier 1 and
not the calibrated tiers).

Under §1's principles — §1.3 pre-register before any code, §1.5 report movement
and never promise attainment — and §4's prohibitions. This lane touches no
target, no threshold, no `preregistered.py` / `holdout.py` / `loo.py` /
`target_revisions.py`, no `KNOWN_SCORES` / `CBO_SCORE_MAP`, no workflow, and not
`fiscal_model/corporate.py`, which a concurrent lane owns.

---

## 1. The defect, with the three vintages' printed paths

### 1.1 What is on the record, and the one place it overstates

`W6_corporate_base_projection.md` finding 1 says the series "grows at 4.88%/yr"
and "returns the **identical** path for all three vintages (402.1 → 614.3)".
The first half is exact. **The second half is very slightly stronger than the
tree supports, and this lane corrects it rather than repeating it**: the three
paths share a base level and a first year and then diverge in the third
significant figure, because the growth rule reads the vintage's own GDP and
inflation assumptions even though the *level* it grows has no vintage in it.

`CBOBaseline(start_year=2026, duration=10).generate().corporate_income_tax`,
`use_real_data=True` — the app's own default:

| vintage | FY2026 | FY2035 | CAGR | 10-yr sum | base level |
|---|--:|--:|--:|--:|--:|
| `cbo_feb_2024` | 402.09 | 617.26 | 4.88% | 5,040.5 | 386.62 |
| `cbo_jan_2025` | 402.09 | 612.98 | 4.80% | 5,012.3 | 386.62 |
| `cbo_feb_2026` | 402.09 | 614.33 | 4.82% | 5,019.3 | 386.62 |

One base level to the cent, one first year to the cent, and 0.70% of spread at
FY2035 across three vintages whose *published* corporate receipts differ by far
more than that. The finding's "402.1 → 614.3" is the February 2026 row with the
February 2024 endpoint dropped; the substance of the finding — that a score
reported as "on the February 2024 baseline" carries a corporate line that is
neither February 2024's nor meaningfully distinguishable from February 2026's —
survives the correction intact.

`use_real_data=False`, for contrast, *is* vintage-specific in the level and
identical in the shape:

| vintage | FY2026 | FY2035 | CAGR | 10-yr sum | base level |
|---|--:|--:|--:|--:|--:|
| `cbo_feb_2024` | 468.00 | 718.44 | 4.88% | 5,866.7 | 450.0 |
| `cbo_jan_2025` | 544.96 | 830.79 | 4.80% | 6,793.3 | 524.0 |
| `cbo_feb_2026` | 436.80 | 667.36 | 4.82% | 5,452.6 | 420.0 |

So the real-data path and the fallback path disagree about February 2026's
corporate receipts by **8.6%** and about January 2025's by **35.5%**, and the
one with "real data" in its name is the one with no vintage in it.

Against CBO's own February 2024 projection (publication 59710, Table 1-1,
"Corporate income taxes"; transcribed by PR #121 into
`fiscal_model/data_files/corporate/cbo_corporate_receipts.csv`):

| FY | 2025 | 2026 | 2027 | 2028 | 2029 | 2030 | 2031 | 2032 | 2033 | 2034 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| $B | 494.1 | 491.4 | 484.1 | 490.7 | 500.9 | 510.6 | 518.7 | 519.2 | 533.4 | 550.8 |

**1.21%/yr over FY2025–2034, against the model's 4.88%.** CBO's own line falls
in FY2026 and FY2027; the model's rises monotonically at four times the rate.

### 1.2 Cause — two independent mechanisms, in two methods

**(a) The level.** `_load_from_data_sources()` (`fiscal_model/baseline.py:454`)
sets

```python
self.base_corporate_tax = self.base_individual_income_tax * GDP_RATIOS["corporate_tax_to_income_tax"]
```

`base_individual_income_tax` is `IRSSOIData.get_total_revenue(max(available_years))`
— the latest IRS SOI *tax year* on file — and `corporate_tax_to_income_tax` is a
flat historical 0.18 (`constants.py:121`). Neither takes a vintage. The method
overrides **every** base level the vintage carries, so the corporate line under
`use_real_data=True` is 18% of a historical individual-income-tax aggregate, and
the vintage the user selected never reaches it. This is the whole of clause (ii)
of item 30.

**(b) The shape.** `_project_corporate_tax()` (`baseline.py:578`) grows that
level at `real_gdp_growth + inflation + BASELINE_GROWTH["corporate_profit_premium"]`,
the last being a flat **1pp** "corporate profits grow slightly faster than GDP"
(`constants.py:52`). On February 2024's assumptions that compounds to 4.88%/yr.
The premium is not sourced to anything about corporate profits, and CBO's own
narrative for this vintage says the opposite of what it asserts — receipts fall
relative to GDP on scheduled changes in tax rules, rising credit claims and
profits growing *more slowly* than the economy. This is clause (i).

### 1.3 The other receipt series have mechanism (a) too — and that is not this lane's to fix

The override is not corporate-specific. `_load_from_data_sources` sets
`base_individual_income_tax` from IRS SOI, `base_gdp` from FRED, and **every
other base level** — payroll, other revenue, all six spending categories and debt
— as a flat `GDP_RATIOS` share of that FRED GDP. So under `use_real_data=True`:

| series | FY2026, all three vintages | spread at FY2035 |
|---|--:|--:|
| individual income tax | 2,255.31 / 2,246.93 / 2,248.86 | 1.1% |
| corporate income tax | 402.09 / 402.09 / 402.09 | 0.70% |
| payroll taxes | 2,027.13 / 2,027.13 / 2,027.13 | 0.70% |
| other revenues | 468.45 / 468.45 / 468.45 | **0.00%** — byte-identical, a flat 2%/yr constant |

(Individual income tax differs in the first year only because its growth premium
is applied from year 0.) **`other_revenues` is byte-identical across all three
vintages for all ten years**, which is the same defect in its purest form.

This lane fixes **corporate only**, for one reason and it is not tidiness: the
repository carries a transcribed CBO receipts path for corporate and for nothing
else. Moving payroll, individual or other onto their vintages' own tables needs
those tables, and cbo.gov returns HTTP 403 to this environment (re-checked
2026-09-06 on `/data/budget-economic-data`, and the Wayback Machine still holds
no snapshot of `51118-2025-01-budgetprojections.xlsx` —
`archived_snapshots: {}`). Replacing one unsourced rule with another unsourced
rule on three more series is exactly what §1.1 forbids. **Recorded here as the
carry-over §6 item 1**, with the measurement above so nobody has to re-derive it.

---

## 2. Who reads the series

Traced by `grep -rn corporate_income_tax` plus following each call site to the
quantity it produces.

| reader | reaches a scored number? | moves with this fix? |
|---|---|---|
| `scoring_engine.py:353` — `_score_growth_tax_policy_year`, `use_corporate_base=True` | **only `CorporateTaxPolicy`** | **no.** `derived` mode prices off CBO's own path (`corporate.py:428`) and never looks at `base_rev`; `reported` mode uses `self.baseline_profits_billions`, defaulted to `BASELINE_TAXABLE_PROFITS_BILLIONS = 1900.0`, and falls back to `baseline_revenue / baseline_rate` **only when that is ≤ 0**, which no factory, preset or validation shape sets |
| `scoring_engine.py:426` — `_get_baseline_revenue_for_tax_policy` for `PolicyType.CORPORATE_TAX` | a **bare `TaxPolicy`** typed corporate | **yes, conditionally.** It reaches `policies_core.py:239`, `baseline_revenue × affected_share × (Δrate / 0.18)`, but only when `_should_use_irs_data()` is False or IRS loading raises — i.e. `use_real_data=False`, or a policy carrying an explicit taxpayer count. With `use_real_data=True` and no taxpayer count the score comes off IRS *individual* SOI data and the corporate baseline is never read |
| `InternationalTaxPolicy` (a `TaxPolicy` typed corporate, so it lands on the same line 426) | 4 reconstruction rows | **no.** Its `estimate_static_revenue_effect` discards `baseline_revenue` on line 450 |
| `AMTPolicy` for CAMT (`amt.py:1352`, typed corporate) | 2 rows | **no.** It matches `_growth_tax_policy_handlers` with `use_corporate_base=False`, so `base_rev` is 0.0 |
| `BaselineProjection.total_revenues` → `.deficit` → `_project_debt` → `_project_interest` | **the baseline itself** | **yes.** Corporate receipts are a term in total revenues, so the deficit, the debt path and net interest all move with them |
| `assistant/tools.py:398` `tool_get_cbo_baseline` | **shipped Ask surface** | **yes**, through `total_revenues`, `deficit` and `debt_held_by_public` |
| `ui/tabs/deficit_target.py:769` — Build's target strip | **shipped Build surface** | **yes**, through `baseline.deficit.mean()` |
| `composer/composer.py:993` `gap_to_target_billions` | Build's values path | **yes**, same quantity |
| `uncertainty.py:99, 298` | nothing shipped | band scales with the level; `calculate_baseline_uncertainty` is called only by `tests/test_uncertainty.py` |
| `api.py:1035` `POST /score/custom` with `policy_type="corporate_tax"` | **shipped API surface** | **no in practice.** It builds a bare `TaxPolicy` but scores it with `use_real_data=True` and no taxpayer count, so it takes the IRS individual branch; it reaches the corporate baseline only if IRS SOI loading fails |
| `economics.py` (dynamic scoring) | every dynamic score | **no.** It reads `baseline.nominal_gdp` and nothing else |

**No validation benchmark reads it.** The battery is built by
`build_scorer_for_vintage()` on `CBO_FEB_2024`; its corporate shape is
`CorporateTaxPolicy(mode=CORPORATE_VALIDATION_MODE)` with
`baseline_profits_billions` left at its 1,900.0 default, so both branches of the
table's first row apply and neither reads the baseline.

---

## 3. The fix

**Two changes in `fiscal_model/baseline.py`, no new data file.**

1. **`_project_corporate_tax()` reads the vintage's own published path when the
   repository carries one.** For `cbo_feb_2024` that is CBO publication 59710
   Table 1-1, already transcribed by PR #121 into
   `fiscal_model/data_files/corporate/cbo_corporate_receipts.csv`. The reader is
   `fiscal_model.corporate.cbo_corporate_receipts` / `cbo_receipts_by_fiscal_year`,
   imported lazily inside the method — **reused, not duplicated, and
   `corporate.py` is not edited.** Its out-of-window rule (continue the nearest
   observed growth rate) supplies FY2035, which the app's FY2026–2035 window
   reaches and the CSV's FY2025–2034 block does not.

2. **`_load_from_data_sources()` stops overriding the vintage's corporate base
   level.** `base_corporate_tax` becomes the vintage's own base-year figure —
   the same figure `_use_hardcoded_fallback()` already carries for that vintage —
   read from one new module-level map so the two paths cannot drift. This is the
   removal of an override, not the adoption of a new number: every value it uses
   is already in the file and is already what the module publishes for that
   vintage when data loading fails.

3. **`CORPORATE_RECEIPTS_SOURCING` grades each vintage, and `metadata` carries
   the grade**, in the shape `VINTAGE_SOURCING` already uses for the vintage as a
   whole. Three states, because the three vintages genuinely have three:

   | vintage | grade | what stands behind it |
   |---|---|---|
   | `cbo_feb_2024` | `published_path` | CBO pub. 59710 Table 1-1, ten annual values, transcribed |
   | `cbo_jan_2025` | `published_base_level` | CBO pub. 61172 / data file 60870, Table B-1, "Corporate income taxes", FY2025 = $524.0B — a **level**, grown by the module's own rule |
   | `cbo_feb_2026` | `vintage_estimate` | $420.0B, the module's own figure for this vintage, transcribed from no table |

   The point of the third row is that it says so. A vintage whose corporate line
   is a reconstruction must not be reportable as "CBO's February 2026 corporate
   receipts", and after this change a caller can tell the difference without
   reading the source.

**What this fix does not do.** It does not manufacture annual paths for January
2025 or February 2026 — blocked at the source, §1.3 — so clause (i) of item 30 is
closed for one vintage of three and clause (ii) for all three. It does not touch
the other receipt or spending series (§1.3, carry-over 1). It does not retune
`corporate_profit_premium`, `GDP_RATIOS`, or any constant: the premium keeps its
value and its two remaining users, and `corporate_tax_to_income_tax` stays in
`constants.py` with nothing reading it, which the outturn will say plainly rather
than quietly deleting.

---

## 4. The prediction

Computed before `baseline.py` was opened, by re-running the module's own
arithmetic with the two changes applied externally
(`scratchpad/predict.py`). Every figure below is a claim, not a hope.

### 4.1 The three corporate paths, after

`use_real_data=True`, app window FY2026–2035:

| vintage | FY2026 | FY2035 | CAGR | sum | was |
|---|--:|--:|--:|--:|--:|
| `cbo_feb_2024` | **491.40** | **568.77** | **1.64%** | **5,168.6** | 402.09 → 617.26, 5,040.5 |
| `cbo_jan_2025` | **544.96** | **830.79** | 4.80% | **6,793.3** | 402.09 → 612.98, 5,012.3 |
| `cbo_feb_2026` | **436.80** | **667.36** | 4.82% | **5,452.6** | 402.09 → 614.33, 5,019.3 |

`use_real_data=False`: `cbo_feb_2024` moves to the same 491.40 → 568.77 /
5,168.6 (it was 468.00 → 718.44 / 5,866.7); the other two are **unchanged to the
cent**, because their base levels already came from the vintage.

On the validation window FY2025–2034, February 2024 reproduces CBO's ten printed
values exactly and sums to **5,093.9**, a tenth of a billion below the 5,094.0
CBO prints as its own total — the rounding artefact PR #121 already documented.

### 4.2 Every consumer

| consumer | prediction |
|---|---|
| `cold_holdout.py --json`, all three tiers | **byte-identical**, every row. 26 / 15.2% / 16 / 22; fitted 21 / 1.7%; reconstructions 34 / 57.6% |
| `run_loo.py --donor-matrix` | **byte-identical** |
| `compute_scorecard()`, all 81 entries | **byte-identical** |
| 53 `PRESET_POLICIES`, static and dynamic | **byte-identical.** Presets are scored at `policy_execution.py:157` with `use_real_data=False` on the default February 2026 vintage, whose fallback level does not move |
| Tailor, 4 policy types × 2 data modes × 2 dynamic settings | **byte-identical.** "Corporate Tax" routes to `CorporateTaxPolicy`; the other three never touch the corporate line |
| bare `TaxPolicy` typed corporate, `use_real_data=True` | **byte-identical** (−7,120.48 at +7pp, all three vintages — it reads IRS individual data) |
| bare `TaxPolicy` typed corporate, `use_real_data=False`, February 2026 | **byte-identical** (−1,855.39 at +7pp) |
| bare `TaxPolicy` typed corporate, `use_real_data=False`, **February 2024** | **−1,996.32 → −1,758.79** (−11.9%), the corporate-sum ratio 5,168.6 / 5,866.7 |
| bare `TaxPolicy` typed corporate, `use_real_data=False`, January 2025 | **byte-identical** (−2,311.62) |
| **Ask `get_cbo_baseline`** (February 2026, `use_real_data=True`) | ten-year deficit **$30,020.7B → $29,529.1B** (−$491.6B, −1.6%); FY2026 revenues **$5,146.53B → $5,181.24B**; FY2035 revenues **$7,250.16B → $7,303.19B**; end-of-window debt/GDP **104.8% → 103.9%** |
| **Build's target strip / `composer.gap_to_target_billions`** | mean annual baseline deficit **$3,002.07B → $2,952.91B**; as a share of mean GDP **7.307% → 7.307%** (the printed figure rounds to the same tenth) |
| baseline deficit, `use_real_data=True`, other vintages | February 2024 **29,891.0 → 29,707.2**; January 2025 **29,726.1 → 27,710.6** |
| baseline deficit, `use_real_data=False` | February 2024 **15,256.0 → 16,012.5**; the other two unchanged |
| `pytest tests/` | passes, plus the new cases |

**The deficit moves further than the revenue does, and that is the interest
feedback, not an error**: February 2026 gains $433.3B of revenue and loses
$491.6B of deficit, the $58.3B difference being interest not paid on debt not
issued.

### 4.3 Do I owe a Decision 6 caption?

**No, and here is the judgement rather than the assertion.** Decision 6 attaches
a caption when a *headline score* moves. No score moves: every preset, every
Tailor row, every scorecard entry and every dynamic run is predicted
byte-identical, and the one policy path that does move (a bare corporate
`TaxPolicy` on the February 2024 vintage with real data off) is reachable from no
shipped surface — Tailor routes corporate to `CorporateTaxPolicy`, the assistant
does too, and `/score/custom` scores with real data on. What moves is the
**baseline**: a context figure the Build strip and the Ask baseline tool report
*about* the projection rather than a score of any policy. A caption saying "the
baseline deficit fell 1.6% because the corporate line stopped being 18% of a
historical individual-tax aggregate" would be describing a correction to a
displayed input, and the ⚙ Data & methodology popover already names the vintage
and its sourcing. **If the outturn shows a preset or Tailor number moving, the
judgement changes and a caption is owed** — that is the falsification below.

### 4.4 Where I expect to be wrong

1. **The two `test_baseline_vintage.py` assertions on `base_corporate_tax`.**
   One asserts 524.0 for January 2025 in the fallback path; that still holds. If
   either implicitly assumed the real-data path, it will fail and the fix is the
   test, not the code.
2. **A test asserting monotonically rising revenues.** February 2024's corporate
   line now *falls* in FY2027, for the reason CBO's own does. `test_baseline.py`
   asserts `corporate_income_tax > 0`, which survives, but a growth assertion
   elsewhere may not.
3. **The `duration != 10` seam.** Every projection method in this module returns
   `np.zeros(10)` regardless of `duration`, so the published path is built over
   ten fiscal years from `start_year` to match. A caller passing `duration != 10`
   is already broken and this does not fix it.
4. **`GDP_RATIOS["corporate_tax_to_income_tax"]` becomes unread.** I expect to
   leave it in place with a note rather than delete it, because deleting a
   documented constant is a bigger claim than this lane is making.

---

## 5. Task 2 — the dashboard prints Tier 1 and not the calibrated tiers

### 5.1 The defect

`SWEEP_offset_sign.md` §7.5 records that `run_validation_dashboard.py` produced
**byte-identical output** across PR #119, a change that moved the fitted tier
1.7% → 1.8% and the reconstruction tier 57.6% → 57.4% and reclassified two rows.
The dashboard prints the health check, the SOI calibration, the distributional
benchmarks, the out-of-sample tier and leave-one-out — and **nothing about the
two calibrated tiers**, which between them are 55 of the scorecard's 81 rows.
A dashboard that cannot see a change to two-thirds of the benchmark population is
not a regression gate for it.

### 5.2 What the workflow actually checks

`.github/workflows/validation-dashboard.yml` runs
`python scripts/run_validation_dashboard.py` and branches **on the exit code
alone** (0 pass, 2 warn, anything else fail). It greps nothing and parses no
line. The JSON steps redirect to files uploaded as artifacts. **So adding output
lines is safe, and the constraint that matters is that no existing line changes
and no exit code changes.** Both are held, and the workflow is not edited.

### 5.3 What gets added

Read from `scripts/cold_holdout.py`'s `build_report()` and from
`cached_default_scorecard()` — **the same objects `cold_holdout.py` prints from,
never recomputed from model output.** A new `Calibrated tiers (by construction)`
block after the out-of-sample block, carrying:

* **fitted tier** — n, mean, median, within-15, within-25, and the count of
  `model_estimate` targets, from `report["calibrated_reference"]["summary"]`;
* **held in place** — the same aggregation over the fitted entries *plus* the
  entries whose `target_revision_id` is set, which is the reading CLAUDE.md
  quotes beside the fitted mean and which nothing in the repository currently
  computes;
* **unfitted reconstruction tier** — n, mean, median, within-15, within-25 and
  `model_estimate` count, from `report["uncalibrated_reconstruction"]["summary"]`,
  **plus the per-category sub-populations**, because that tier's mean is four or
  more populations and the repository's own rule is that it is never quoted as
  one number. The grouping key is `ScorecardEntry.category`, a label the
  scorecard already carries; no new taxonomy is invented;
* **`revised_target_entries`** and the **provenance counts**
  (`line_item` / `line_item_differs` / `secondhand` / `model_estimate` /
  `unclassified`, plus `published_entries` and `transcribed_entries`), from
  `ScorecardSummary`.

The same structure goes into `--json` under a new `calibrated_tiers` key. The
block is **informational**: it changes no gate and no exit code, exactly as the
out-of-sample block is.

### 5.4 The numbers it will print on `a251b32`

| reading | value |
|---|--:|
| fitted | n=21, mean 1.7%, median 0.0%, 21/21 within 15% |
| fitted held in place | n=37, mean 15.5%, median 3.7%, 26/37 within 15% |
| reconstructions | n=34, mean 57.6%, median 34.2%, 9/34 within 15% |
| revised targets | 16 |
| provenance | line_item 51 / line_item_differs 7 / secondhand 17 / model_estimate 6 / unclassified 0 |
| published entries | 75 of 81 |

Sub-populations: PL119_21 8, Trade 5, International 4, CapitalGains 3, Pharma 3,
Corporate 2, PTC 2, Expenditures 2, Enforcement 2, Credits 1, AMT 1, Climate 1.

**These are read off the live tree, not carried from CLAUDE.md**, which still
quotes the pre-Wave-4 population (28 fitted at 2.0%, 26 reconstructions at
61.8%). Documentation sync is not this lane's.

---

## 6. Falsification tests

Registered before the code was written. Each is a way this lane is wrong.

| # | falsified if | expected |
|---|---|---|
| 1 | any `cold_holdout.py --json` row differs | byte-identical, all 81 |
| 2 | `run_loo.py --donor-matrix` differs | byte-identical |
| 3 | any of the 53 presets moves, static or dynamic | byte-identical |
| 4 | any Tailor row moves | byte-identical, 16 combinations |
| 5 | the three vintages do not produce three different corporate paths | three distinct paths |
| 6 | February 2024's path ≠ the transcribed CSV on FY2025–2034 | equal to the tenth, sum 5,093.9 |
| 7 | Ask's ten-year deficit lands outside $29,529.1B ± $1B | $29,529.1B |
| 8 | the dashboard's existing lines change, or its exit code does | unchanged, exit 1 (the pre-existing Python 3.14 runtime degradation, which fails on `main` too) |
| 9 | a new dashboard line disagrees with `cold_holdout.py --json` | equal, pinned by a test |

## 7. Carry-overs this lane opens

1. **The same override defect on individual, payroll, other revenue and all six
   spending series** (§1.3). `other_revenues` is byte-identical across all three
   vintages for all ten years; payroll and corporate share one base level. Closing
   it needs each vintage's own published receipts and outlay tables, and cbo.gov
   403s (`MODELING_IMPROVEMENT.md` §6.2 item 16, same blocker).
2. **January 2025 and February 2026 still have no annual corporate path**, so
   two of three vintages keep a 4.8%/yr reconstruction growing a published or
   estimated level. This is `W6_corporate_base_projection.md` carry-over 1
   unchanged; what this lane adds is that the *level* is now the vintage's and
   the grade is machine-readable.
3. **`corporate_profit_premium = 0.01` is still unsourced** and still governs the
   two reconstruction vintages. CBO's own February 2024 narrative contradicts it.
   Sourcing or removing it is a constant change and needs its own pre-registration.
4. **`GDP_RATIOS["corporate_tax_to_income_tax"]` has no reader after this lane.**
   Left in place deliberately; deleting a documented constant is a separate call.

---

## 8. Outturn

*Appended in this lane's last commit, measured on the branch tip.*

### 8.1 Against the pre-registration

**Every figure in §4 landed, one of them a tenth of a point off.**

| # (§6) | falsification | outcome |
|---|---|---|
| 1 | any `cold_holdout.py --json` row differs | **byte-identical**, whole file |
| 2 | `run_loo.py --donor-matrix` differs | **byte-identical** |
| 3 | any of the 53 presets moves | **byte-identical**, 53 × 2 data modes × static/dynamic |
| 4 | any Tailor row moves | **byte-identical**, all 16 |
| 5 | three vintages, three corporate paths | **three distinct paths**, both data modes, pinned by a test |
| 6 | February 2024 ≠ the transcribed CSV | **equal**, all ten values; sum 5,093.9 |
| 7 | Ask's ten-year deficit outside $29,529.1B ± $1B | **$29,529.1B** |
| 8 | the dashboard's existing lines or exit code change | **byte-identical** after task 1; purely additive after task 2; exit 1 both times, as on `main` |
| 9 | a new dashboard line disagrees with `cold_holdout.py --json` | **equal**, asserted by `test_calibrated_tiers_match_cold_holdout` |

The three corporate paths, `use_real_data=True`, FY2026–2035:

| vintage | before | after | CAGR | sum before → after |
|---|---|---|--:|---|
| `cbo_feb_2024` | 402.09 → 617.26 | **491.40 → 568.77** | 4.88% → **1.64%** | 5,040.5 → **5,168.6** |
| `cbo_jan_2025` | 402.09 → 612.98 | **544.96 → 830.79** | 4.80% | 5,012.3 → **6,793.3** |
| `cbo_feb_2026` | 402.09 → 614.33 | **436.80 → 667.36** | 4.82% | 5,019.3 → **5,452.6** |

On the validation window FY2025–2034, February 2024 is CBO's ten printed values
to the tenth and sums to 5,093.9.

### 8.2 What moved, exactly

| surface | before | after |
|---|--:|--:|
| Ask `get_cbo_baseline`, ten-year deficit | $30,020.7B | **$29,529.1B** (−1.6%) |
| Ask, FY2026 revenues | $5,146.53B | **$5,181.24B** |
| Ask, FY2035 revenues | $7,250.16B | **$7,303.19B** |
| Ask, end-of-window debt/GDP | 104.8% | **103.8%** |
| Build target strip, mean annual baseline deficit | $3,002.07B | **$2,952.91B** |
| `composer.gap_to_target_billions(3.0)` | $17,896.31B | **$17,404.65B** |
| bare corporate `TaxPolicy`, Feb 2024, real data off, +7pp | −$1,996.32B | **−$1,758.75B** |

Nothing else. All 26 out-of-sample rows, all 81 scorecard rows, the leave-one-out
donor matrix, 53 presets and 16 Tailor combinations are byte-identical, and
`check_readiness.py --strict` still exits 2 with the single Python 3.14 runtime
issue it reports on `main`.

**One prediction was a tenth off**: end-of-window debt/GDP was predicted 103.9%
and came out **103.8%**, because the prediction rounded the end-of-window GDP
back out of the published ratio instead of reading it.

### 8.3 Findings

1. **W6 finding 1's "identical" was very slightly too strong, and correcting it
   made the defect *easier* to state, not harder.** The three paths shared one
   base level and one first year and diverged 0.70% by FY2035 — the growth rule
   reads the vintage's assumptions, the level does not. Once that is said
   precisely, the cause is obvious and lives in one line of the loader, where
   "identical path" had pointed vaguely at the projection.
2. **The mode with "real data" in its name was the one with no vintage in it.**
   `use_real_data=True` gave every vintage $386.62B; `use_real_data=False` gave
   three different, vintage-specific figures. A reader — or a maintainer — would
   reasonably assume the opposite, and this is the second time this repository
   has found that the honest-sounding path was the weaker one.
3. **The defect is not corporate's; corporate was just the one with a table to
   move to.** `_load_from_data_sources` overrides *every* base level, and
   `other_revenues` is byte-identical across all three vintages for all ten
   years — the same defect with no growth-rule variation to hide it. Fixing it
   needs each vintage's own published tables, which cbo.gov 403s. Carry-over 1.
4. **A published *level* and a published *path* are different grades and the
   repository had no way to say so.** January 2025 has a transcribed FY2025
   corporate figure and no annual path; February 2026 has neither.
   `CORPORATE_RECEIPTS_SOURCING`'s three states exist because the three vintages
   genuinely have three, and a two-state flag would have had to lie about one.
5. **"Held in place" could not be computed from what the scorecard exposed, and
   the natural guess is wrong by a factor of three.** `calibrated_to_target` is
   the runner's declaration *and* not superseded, so folding all 16
   `revised_target_entries` rows back into the fitted tier reads **37 at 15.5%**
   — but 10 of those are sectoral rows no runner ever declared fitted. The
   honest reading is **27 at 5.6%**, and it needed a new field
   (`declared_calibrated_to_target`) to be computable at all. A dashboard line
   that had guessed would have been worse than the blank it replaced.
6. **The CI job never parsed the dashboard's text.** `validation-dashboard.yml`
   branches on the exit code alone, so the block that was missing had also been
   safe to add for as long as it was missing. What made the omission cost
   something was a human reading "byte-identical output" as evidence.
7. **The parity gate on `ScorecardEntryModel` earned its keep.** Adding
   `declared_calibrated_to_target` to the dataclass failed
   `test_entry_model_carries_every_scorecard_entry_field` immediately — the test
   written after `transcribed` had silently vanished from the API. The field went
   into the Pydantic model in the same commit; without the gate it would have
   been printed by the dashboard and missing from `/validation/scorecard`.

### 8.4 What this lane did not do

- Did not touch any target, threshold, `preregistered.py`, `holdout.py`,
  `loo.py`, `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`,
  `scripts/cold_holdout.py`, `tests/test_cold_holdout.py`, any workflow, or
  `fiscal_model/corporate.py` — which it *reads*, through that module's own
  public loader, and does not edit.
- Did not retune a constant. `corporate_profit_premium` keeps its unsourced 1pp
  and still governs two vintages; `GDP_RATIOS["corporate_tax_to_income_tax"]` is
  left in place with no reader rather than deleted.
- Did not manufacture an annual path for January 2025 or February 2026, and did
  not fix the same override on the individual, payroll, other-revenue or
  spending series.
- Did not add a Decision 6 caption, on the judgement in §4.3 — which the outturn
  supports: no preset, Tailor row, scorecard entry or dynamic score moved.
- Did not change a gate. Both new blocks are informational, like the
  out-of-sample block beside them.

### 8.5 Gates

| command | result |
|---|---|
| `python -m pytest tests/ -q` | **3,539 passed, 7 skipped** (`a251b32`: 3,518 passed, 7 skipped — 21 added) |
| `python scripts/cold_holdout.py --json` | byte-identical to `a251b32` |
| `python scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | **exit 0** (15.2%, 22/26) |
| `python scripts/run_loo.py --donor-matrix` | byte-identical to `a251b32` |
| `python scripts/run_validation_dashboard.py` | **exit 1**, as on `a251b32`, for the reason it names (Python 3.14 runtime); every pre-existing line unchanged |
| `python scripts/run_validation_dashboard.py --augment-top-tail --json` | exit 0 |
| `python scripts/check_readiness.py --strict` | **exit 2**, sole issue `runtime`, as on `a251b32` |
| `python -m ruff check fiscal_model/ tests/ scripts/` | clean |
