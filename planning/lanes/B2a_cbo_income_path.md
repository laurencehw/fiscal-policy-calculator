# Lane B2a — project the SOI income base on CBO's own income path

*Pre-registered 2026-11-06 against `main` @ `529efc1`, in this lane's third
commit, before `fiscal_model/baseline.py` or `fiscal_model/scoring_engine.py`
was edited. The first two commits add data and a report and change no score.
Outturn appended at the end, in the last commit.*

Plan: `planning/PRIORITY5_AND_CHARTS.md` §B2 (B2a only; B2b, the payroll
vintage, follows this lane's outturn). Under `planning/MODELING_IMPROVEMENT.md`
§1 (pre-register before code, no promise of attainment) and §4 (no constant
retuned to a held-out target).

Disclosure: to compute the predictions below I read both modules (read-only)
and ran a scratch script that wraps `_income_base_projection_factor` and
`_threshold_deflator` to record, per battery row, the vintage, SOI year,
window and the GDP ratio the row uses today. No module was changed and the
mechanism below was **not** run on the battery before this commit: every
predicted figure is the scalar arithmetic in §3, not a scoring run.

## 1. Starting numbers (`python scripts/cold_holdout.py --json` at `529efc1`)

| tier | n | mean | median | within 15 | within 25 |
|---|--:|--:|--:|--:|--:|
| Out-of-sample (44-row cohort) | 44 | **15.2%** | 12.3% | 26 | 36 |
| Calibrated reference (fitted) | 15 | 1.6% | 0.0% | 15 | 15 |
| Unfitted reconstructions | 38 | 42.3% | 30.1% | 11 | 15 |

Classes this lane can touch: `ordinary_rate_change` n=11, mean **15.3%**,
mass 168.8, 6 within 15, 10 within 25; `agi_inclusive_surtax` n=4, mean
**7.2%**, mass 28.8.

## 2. The mechanism, fixed here

Today `_nominal_income_ratio(from, to)` is `nominal_income_index(to) /
nominal_income_index(from)`: the vintage's nominal GDP. Both the base
projection (`_income_base_projection_factor`) and the threshold deflator
(`_threshold_deflator`) go through it and stay one unit conversion.

After this lane the ratio is formed from **CBO's own projection of the base**,
`BaselineProjection.income_base_index(year, series)`, on the edition the
scored vintage maps to (`cbo_feb_2024` → 2024-06, graded `nearest_vintage`;
`cbo_jan_2025` → 2025-01; `cbo_feb_2026` → 2026-02). The swap is made inside
`_nominal_income_ratio` and nowhere else.

**Series, chosen on concept, not on the battery.** The policy's own
`income_measure` decides:

* `taxable_income` (the default, and every ordinary-rate row) reads
  **`rev_iit_taxable_income`**. A rate change on taxable income is a tax on
  taxable income; the SOI base the generic path reads is taxable income by AGI
  class. AGI would carry the deductions and exemptions the reform does not tax,
  whose path diverges exactly when the law changes them (CY2026 in the pre-OBBBA
  editions).
* `agi` (the four AGI-surtax rows, whose sources state the surtax on AGI)
  reads **`rev_iit_agi`**, for the same reason in reverse.

Taxable *ordinary* income (`rev_iit_taxable_ordinary`) would be closer still for
a bracket-rate change, but it is absent from the 2024-06 edition that the whole
CBO Options battery reads, so using it would make the battery and the app read
different concepts. Not used. Bracket income (`rev_iit_bracket_k`) is never a
growth index (its numbering changes meaning in CY2026 in two editions); it is
used only as a level in the decomposition report.

**Rules that are part of the mechanism, not knobs:**

1. **Years outside the edition.** The 2018-volume window (FY2019-2028) reaches
   two years before the 2024-06 edition's first year (CY2021). Those years are
   chain-linked: `index(y) = index(first) × gdp(y) / gdp(first)`, the vintage's
   own GDP growth carried from the nearest published year, as
   `nominal_income_index` already does at its own edges. Same rule past the last
   year.
2. **No series → fall back and log.** `income_base_index` returns `0.0` for a
   baseline with no vintage edition (a hand-built `BaselineProjection`, or a
   vintage with no transcription). `_nominal_income_ratio` then uses the GDP
   index exactly as today and logs that it did.
3. **Calendar vs fiscal year.** CBO's series is by calendar year; the GDP index
   is read by fiscal year, and today's code already uses the tax year as the
   index year. The year label convention is unchanged: year `y` reads CY`y`.
4. Only ratios are used, so the level of either series cancels.

## 3. Predictions

Method (scratch, not a scoring run): for each row, the predicted scalar factor
is Σ_window [TI(y)/TI(2023)] / Σ_window [GDP(y)/GDP(2023)], with the GDP ratios
recorded from today's run (SOI anchor tax year 2023 for every row). The predicted
model total is today's total × factor. For rows with a re-indexed bracket
threshold (the top-two and top-four bracket rows) the deflator moves with the
base and amplifies the movement: the band runs from 1× to 3× the scalar's
deviation from 1, same sign. Rows without a re-indexed threshold get ±0.005 on
the factor.

### 3.1 The 11 ordinary rows

| row | edition | series | model now | published | err now | factor | factor band | predicted model | **predicted err** | err band |
|---|---|---|--:|--:|--:|--:|---|--:|--:|---|
| `biden_high_income_tax` | 2026-02 | taxable_income | −299.8 | −245.9 | 21.9 | 1.0233 | 1.0183–1.0283 | −306.8 | **24.8** | 24.2–25.4 |
| `cbo2019_opt1_all_rates_1pp` | 2024-06 | taxable_income | −912.7 | −905.4 | 0.8 | 1.0195 | 1.0145–1.0245 | −930.5 | **2.8** | 2.3–3.3 |
| `cbo2019_opt1_top2_brackets_1pp` | 2024-06 | taxable_income | −124.4 | −123.4 | 0.8 | 1.0195 | 1.0195–1.0585 | −126.8 | **2.8** | 2.8–6.7 |
| `cbo2019_opt1_top4_brackets_1pp` | 2024-06 | taxable_income | −250.7 | −222.9 | 12.5 | 1.0195 | 1.0195–1.0585 | −255.6 | **14.7** | 14.7–19.0 |
| `cbo2021_opt1_all_rates_1pp` | 2024-06 | taxable_income | −1,016.7 | −884.0 | 15.0 | 0.9841 | 0.9791–0.9891 | −1,000.6 | **13.2** | 12.6–13.8 |
| `cbo2021_opt1_top2_brackets_1pp` | 2024-06 | taxable_income | −136.5 | −113.8 | 19.9 | 0.9841 | 0.9524–0.9841 | −134.3 | **18.0** | 14.2–18.0 |
| `cbo2021_opt1_top4_brackets_1pp` | 2024-06 | taxable_income | −285.9 | −203.3 | 40.6 | 0.9841 | 0.9524–0.9841 | −281.4 | **38.4** | 33.9–38.4 |
| `cbo2023_opt13_top4_brackets_2pp` | 2024-06 | taxable_income | −621.4 | −501.9 | 23.8 | 0.9587 | 0.8762–0.9587 | −595.8 | **18.7** | 8.5–18.7 |
| `cbo_opt45_all_rates_1pp` | 2024-06 | taxable_income | −1,201.2 | −1,185.3 | 1.3 | 0.9424 | 0.9374–0.9474 | −1,132.0 | **4.5** | 4.0–5.0 |
| `cbo_opt45_top4_brackets_2pp` | 2024-06 | taxable_income | −671.2 | −569.5 | 17.9 | 0.9424 | 0.8271–0.9424 | −632.5 | **11.1** | 2.5–11.1 |
| `illustrative_1pp_all` | 2026-02 | taxable_income | −1,235.7 | −1,081.3 | 14.3 | 1.0233 | 1.0183–1.0283 | −1,264.5 | **16.9** | 16.4–17.5 |

Class prediction at the point estimates: mass 168.8 → **165.9**, mean
**15.3% → 15.1%** (band 12.4%–16.1%, the sum of the row bands), within 15 stays **6** (band 5-8), within 25 stays
**10**. Five rows get worse (`biden_high_income_tax`, both 2018 all-rates and
top-two, `opt45_all_rates`, `illustrative_1pp_all`) and they are kept.

**This is much smaller than the plan's illustration** (class 15.3% → ~11%), and
the difference is stated rather than tuned away. The plan applied the 2024-06
Option-45 ratio (0.938) to every row. Measured per window, only the FY2023+
windows on the 2024-06 edition sit below 1 (the CY2026 reversion lowers taxable
income relative to GDP). The 2018 and 2020 windows straddle the anchor year, and
CBO's taxable income fell less than GDP going backward from 2023 (the CY2022
capital-gains drop is in taxable income, not in GDP), so their factors are
near or above 1. The two Feb 2026 rows sit above 1: P.L. 119-21 raises taxable
income relative to GDP.

### 3.2 The four AGI-surtax rows (same choke point, AGI series)

| row | factor | model now | predicted | err now | **predicted err** | band |
|---|--:|--:|--:|--:|--:|---|
| `cbo2023_opt13_agi_surtax_1pp_stdded` | 1.0025 | −1,325.7 | −1,329.0 | 0.3 | **0.0** | 0.0–0.5 |
| `cbo2023_opt13_agi_surtax_2pp_bracket4` | 1.0025 | −914.3 | −916.6 | 18.2 | **18.5** | 17.9–19.0 |
| `cbo_opt46_agi_surtax_1pp_20k` | 0.9970 | −1,326.3 | −1,322.3 | 7.9 | **8.2** | 7.7–8.6 |
| `cbo_opt46_agi_surtax_2pp_100k` | 0.9970 | −1,075.8 | −1,072.6 | 2.4 | **2.1** | 1.5–2.6 |

Class mass 28.8 → 28.8, mean **7.2%** unchanged.

### 3.3 Pooled 44-row cohort

Mass 668.6 → about **665.7**: mean **15.2% → 15.1%** (it may print 15.1 or
15.2), within 25 stays **36**, within 15 stays **26** (band 25-27). Every other
class byte-identical (§3.5).

### 3.4 Tailor and the live presets (Feb 2026 vintage, FY2026-2035)

Same arithmetic on the app's default window: factor **1.0249** on
taxable-income presets and Tailor, **1.0302** on AGI presets (yearly 1.002 to
1.034). So the public ten-year number on every ordinary-rate preset and Tailor
**rises about 2.5%** before thresholds (more on presets with a re-indexed
threshold), and about 3% on AGI surtax presets. The plan guessed +5.5%; the
measured figure is half that. This goes in the PR body as a change to the public
number.

### 3.5 Must stay byte-identical

Anything that does not set `soi_base_tax_year` never reaches the swapped index.
From the trace, that is every row outside §3.1-3.2:

* the 7 `capital_gains` rows (they project their own base; their deflator calls
  return 1.0 because no SOI year resolves), 4 `corporate`, 8 `payroll`,
  2 `tax_expenditure`, 5 `discretionary_spending`, 3 `enacted_law_spending`;
* the whole calibrated (fitted) tier, 15 rows, and its held-in-place reading;
* the whole unfitted-reconstruction tier, 38 rows;
* the Social Security page, OLG, and every spending preset.

If any of these moves, the lane has a bug.

## 4. What the decomposition already says (`scripts/ordinary_base_decomposition.py`)

Run before this commit, on today's code. Ten-year $B, revenue-raising positive.

| row | model static | CBO static (Σ bracket income × Δrate) | published | implied offset |
|---|--:|--:|--:|--:|
| `cbo_opt45_all_rates_1pp` | 1,372.8 | 1,353.4 | 1,185.3 | 12.4% |
| `cbo_opt45_top4_brackets_2pp` | 767.1 | 792.9 | 569.5 | 28.2% |
| `cbo2023_opt13_top4_brackets_2pp` | 710.2 | 739.0 | 501.9 | 32.1% |
| `cbo2021_opt1_top4_brackets_1pp` | 326.7 | 344.7 | 203.3 | 41.0% |

The model's static base is within ±5% of CBO's own on every bracket row. The
model's offset is a flat 12.5% of static. Option 45's all-rates row implies
12.4%, so on the one row whose vintage matches, base and response are both
right. Its top-four row implies 28%: **the top-bracket error is behavioural, not
base**. That bounds what this lane can do and points the next lane at the
top-bracket response, not the base. (The 2018-2022 volumes are on older
baselines than the 2024-06 bracket series, so their implied offsets also carry
baseline drift and are not read as elasticities.)

## 5. Acceptance

Outturn as the last commit: predicted vs actual per row (§3.1, §3.2), the
44-row cohort and the class table, each miss called a miss. A row outside its
band is a miss. `build_current_evidence.py` is not rerun in the lane; it moves
in the docs-sync PR after the wave.
