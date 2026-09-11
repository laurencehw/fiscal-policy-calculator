# R3 — the Tier 1 battery: measure the path users type on

*Pre-registered 2026-09-11 on `validation/r3-tier1-battery`, branched from `main` @ `19aa904`
(PR #165, lane R4). Lane R3 of `planning/ROUTE_TO_8_5.md` §1, criterion ①;
`planning/HIGH_STAKES_ACCURACY.md` §3 H10. Every BEFORE figure below is from one of three runs on
**this** tree — `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json`,
`scripts/run_validation_dashboard.py`, `scripts/run_loo.py --donor-matrix` — or from a document
this lane opened and cites by page. Nothing is recalled.*

---

## §1 — What this lane is, what it may not do, and the rule it binds itself to

### 1.1 The measurement, before anything moved

`cold_holdout.py --json` on `main` @ `19aa904`:

| | |
|---|--:|
| n | **22** |
| mean abs error | **11.8%** |
| median | **8.9%** |
| within 15% | 17 |
| within 25% | 19 (86.4%) |
| error mass | 259.4 |

Eight classes at n = 1, 1, 2, 2, 3, 4, 4, 5. `corporate` and `tax_expenditure` are **single
observations**; `agi_inclusive_surtax` and `payroll` are **two**. ROUTE §0 criterion ① asks for
**n ≥ 40, mean ≤ 12%, ≥ 30/40 within 25%, every class n ≥ 3, no class mean above 25%**. A band read
off one row is not a band, and H4 ships per-class bands to users off exactly these counts.

### 1.2 What this lane may not do

1. **No module may be opened.** `policies_core.py`, `payroll.py`, `corporate.py`,
   `tax_expenditures_core.py`, `capital_gains.py` are all closed. Every new row is expressed with
   the shapes `create_policy_from_score` already builds.
2. **No existing row's `model_10yr_billions` may move.** Twenty-two rows go in byte-identical or
   the lane has failed. In particular `illustrative_1pp_all` keeps its FY2025 window: R2 published
   the `.v3` window decision and left it to the owner, and this lane does not take it by
   implication.
3. **No target may be selected after seeing the model's answer.** The manifest's two-commit rule
   applies per batch: the `PreregisteredCase` rows and the `KNOWN_SCORES` records enter in one
   commit with `runnable=False`, and the commit that flips them to `runnable=True` is the one that
   first scores them. This is Phase B's protocol exactly.
4. **No gate value is edited here.** The workflow's own rule re-derives the pooled ceiling and floor
   and the eight per-class ceilings *after* these rows land; §5 reports what the rule derives and
   whether the current values pass. Moving them is the docs-sync/gate lane's, by ROUTE owner ⑪.

### 1.3 The selection rule, fixed before any figure was read into a record

> **From each of the three CBO *Options for Reducing the Deficit* volumes the battery does not
> already contain — 2018 (publication 54667, FY2019–2028), 2020 (publication 56783, FY2021–2030)
> and 2022 (publications 58164 and 58163, FY2023–2032) — take every REVENUE option whose reform is
> one of the six shapes `create_policy_from_score` already builds, and every alternative reported
> inside it. The six shapes are: an ordinary-income rate change at a stated boundary; an
> AGI-inclusive surtax at a stated boundary; a long-term-capital-gains/qualified-dividend rate
> change; a statutory corporate rate change; a flat rate on uncapped covered earnings; and a limit
> on the income-tax exclusion for employment-based health insurance. An option or alternative is
> excluded only where the shape does not exist or where a module constant fitted to that same
> reform sits in the path (leakage) — never for its answer.**

Three consequences of the rule, stated here rather than discovered later:

- **The rule is applied per volume and per alternative, and the verdict for every one of the 100
  revenue options in the three volumes is recorded in
  `fiscal_model/data_files/validation/cbo_options_multi_volume.csv`**, one line of reason each, the
  same discipline `cbo_options.py` applies to the 2024 volume's 76. The battery's composition is
  auditable rather than a curated set of flattering shapes.
- **Spending options are out of scope in all three volumes, and the reason is not fit.** The
  spending arm needs each option's own budget-authority path transcribed and passed through
  `is_level_budget_authority_path`, and `discretionary_spending` is already at n = 5 and is the
  battery's **most accurate class (4.6%)**. Extending it would add rows where the criterion is
  already met and where the measurement is least informative — and, because those rows score well,
  excluding them can only *raise* the reported mean. Carry-over, §6.
- **One reform, one row.** The 2022 volume's Option 13 alternative 1 is already in the battery as
  `illustrative_1pp_all.v2` (lane R2 superseded it onto that very line). It is recorded in the
  alternatives CSV as `registered=false` with that reason, not re-registered.

### 1.4 The window, and why it is the whole point

`CBOScore.scoring_window_first_year` (PR #126, `FY2022_TARGET_WINDOW_RULE`) scores a record on the
ten fiscal years **its own source published**. Every row below carries it: 2019, 2021 or 2023.
Without it these rows would measure nominal growth between decades rather than the model — R2's
finding 3 is exactly that, and it is the reason it told this lane to read the other volumes "the
same way before registering them".

A **window is not a vintage**, and the vintage is a stated mismatch. The repository carries
`CBO_FEB_2024`, `CBO_JAN_2025` and `CBO_FEB_2026`; the three source volumes sit on CBO's April 2018,
September 2020 and May 2022 baselines, none of which exists here. Every new row therefore names
`scoring_vintage="cbo_feb_2024"` — **the oldest vintage this repository carries, hence the nearest
to all three** — and records the mismatch in `source_baseline_vintage`, exactly as
`biden_corporate_28_fy2022` and the Options-2024 spending rows do.

### 1.5 Two guards this lane has to touch, and what it does to each

- **`MIN_GENERIC_BASELINE_YEAR = 2020`** blocks the 2018 volume, and its stated purpose is that the
  target sit "on a baseline close enough to the model's own that baseline drift does not dominate
  the error". `scoring_window_first_year` is the field that removes that drift: a record scored on
  its target's own decade is not measuring drift between decades. The constant is therefore kept at
  2020 **for records that do not state their own window**, and a record that does state one is
  admitted. That is a narrowing of the guard's scope to the case it was written for, not a
  loosening of its value, and the test moves with it.
- **The statutory parameter schedule** (`cbo_tax_parameters.csv`, R4) covers **CY2021–CY2034** on
  the `cbo_feb_2024` vintage. A 2018-volume row whose boundary is a bracket index therefore has
  **CY2019 and CY2020 clamped to CY2021** — the loader says so out loud. Both affected rows carry
  that as a `known_limitations` entry, and their written fallback amounts are CBO's own **CY2021**
  figures, so the amount written is the amount actually applied in every year of the window.

### 1.6 What this lane does **not** claim

**These are not 22 independent observations.** Four editions of the same option are four
observations of **one mechanism on four decades**, and R2 already showed the pair
`illustrative_1pp_all` / `cbo_opt45_all_rates_1pp` measures *insensitivity to the decade* rather
than two independent predictions. §5 therefore reports, beside n, a **distinct-reform count** — the
number of different reforms the battery contains, counting the same option in four volumes once —
and the per-class means are to be read with it.

---

## §2 — The candidate table

Targets are CBO's own ten-year totals in this app's convention (negative = reduces the deficit),
read from `cbo_options_multi_volume_alternatives.csv`. Every 2020 and 2022 figure is read from CBO's
own workbook by sheet and row, with the label cell asserted; every 2018 figure is transcribed from
the PDF and re-verified against its stated report page by
`scripts/extract_cbo_options_multi_volume.py --pdf`. Base classification is read off the option's
own words, never fitted.

### 2.1 Registered — 22 rows

| # | `policy_id` | vol · option · alt | report p. | target ($B) | shape | boundary, from the source's own words | class |
|--:|---|---|--:|--:|---|---|---|
| 1 | `cbo2019_opt1_all_rates_1pp` | 2018 · 1 · 1 | 204 | −905.4 | ordinary rate +1pp | "all tax rates on ordinary income" → bracket 1 ($0) | ordinary |
| 2 | `cbo2019_opt1_top4_brackets_1pp` | 2018 · 1 · 2 | 204 | −222.9 | ordinary rate +1pp | "the four highest brackets" → bracket 4 | ordinary |
| 3 | `cbo2019_opt1_top2_brackets_1pp` | 2018 · 1 · 3 | 204 | −123.4 | ordinary rate +1pp | "the two highest brackets (35 percent and over)" → bracket 6 | ordinary |
| 4 | `cbo2019_opt2_ltcg_qdiv_2pp` | 2018 · 2 · 1 | 207 | −69.6 | LTCG/QDIV +2pp | every bracket → threshold 0 | capital gains |
| 5 | `cbo2019_opt18_hi_payroll_1pp` | 2018 · 18 · 1 | 251 | −898.3 | flat rate on covered earnings | "the 2.9 percent HI tax is levied on total earnings" | payroll |
| 6 | `cbo2019_opt18_hi_payroll_2pp` | 2018 · 18 · 2 | 251 | −1,786.5 | as above, 2pp | as above | payroll |
| 7 | `cbo2019_opt24_corporate_rate_1pp` | 2018 · 24 · 1 | 266 | −96.3 | corporate rate +1pp | 21% → 22% | corporate |
| 8 | `cbo2021_opt1_all_rates_1pp` | 2020 · 1 · 1 | 204 | −884.0 | ordinary rate +1pp | bracket 1 | ordinary |
| 9 | `cbo2021_opt1_top4_brackets_1pp` | 2020 · 1 · 2 | 204 | −203.3 | ordinary rate +1pp | "the top four brackets" → bracket 4 | ordinary |
| 10 | `cbo2021_opt1_top2_brackets_1pp` | 2020 · 1 · 3 | 204 | −113.8 | ordinary rate +1pp | "the top two brackets" → bracket 6 | ordinary |
| 11 | `cbo2021_opt2_ltcg_qdiv_2pp` | 2020 · 2 · 1 | 207 | −75.2 | LTCG/QDIV +2pp | threshold 0 | capital gains |
| 12 | `cbo2021_opt15_hi_payroll_1pp` | 2020 · 15 · 1 | 285 | −877.5 | flat rate on covered earnings | HI base, no taxable maximum | payroll |
| 13 | `cbo2021_opt15_hi_payroll_2pp` | 2020 · 15 · 2 | 285 | −1,736.3 | as above, 2pp | as above | payroll |
| 14 | `cbo2021_opt19_corporate_rate_1pp` | 2020 · 19 · 1 | 293 | −99.3 | corporate rate +1pp | 21% → 22% | corporate |
| 15 | `cbo2023_opt13_top4_brackets_2pp` | 2022 · 13 · 2 | 72 | −501.9 | ordinary rate +2pp | "the four highest brackets" → bracket 4 | ordinary |
| 16 | `cbo2023_opt13_agi_surtax_1pp_stdded` | 2022 · 13 · 3 | 72 | −1,329.1 | AGI surtax +1pp | "AGI above the standard deduction and exemption" | AGI surtax |
| 17 | `cbo2023_opt13_agi_surtax_2pp_bracket4` | 2022 · 13 · 4 | 72 | −773.8 | AGI surtax +2pp | "the sum of the standard deduction, exemptions, and the threshold of the fourth ordinary income tax bracket" | AGI surtax |
| 18 | `cbo2023_opt15_new_payroll_1pct` | 2022 · 15 · 1 | 76 | −1,135.7 | flat rate on covered earnings | "a payroll tax of 1 percent on earnings" | payroll |
| 19 | `cbo2023_opt15_new_payroll_2pct` | 2022 · 15 · 2 | 76 | −2,252.7 | as above, 2pp | as above | payroll |
| 20 | `cbo2023_opt6_employer_health_income_only` | 2022 · 6 · 3 | 30 | −651.4 | income-only exclusion cap | "$8,900 a year for individual coverage and $21,600 a year for family coverage", effective Jan 2026 | tax expenditure |
| 21 | `cbo2023_opt37_ltcg_qdiv_2pp` | 2022 · 37 · 1 | 89 | −102.1 | LTCG/QDIV +2pp | threshold 0 | capital gains |
| 22 | `cbo2023_opt50_corporate_rate_1pp` | 2022 · 50 · 1 | 115 | −129.3 | corporate rate +1pp | 21% → 22% | corporate |

**Filing-status thresholds.** Rows 2, 3, 9, 10, 15, 16 and 17 state all four statuses, read from
CBO's own transcribed parameter schedule (`cbo_tax_parameters.csv`, `cbo_feb_2024` vintage) at the
option's own first calendar year — CY2021 for the 2020 volume (and, under the clamp of §1.5, for the
2018 volume too), CY2023 for the 2022 volume. Rows 2, 3, 9, 10 and 15 also declare
`statutory_bracket_index`, so the floors actually applied are CBO's own, per year and per status,
under `STATUTORY_BRACKET_SCHEDULE_RULE`. Rows 16 and 17 do **not**: CBO states their boundary as a
*formula* (standard deduction + personal exemptions, plus the bracket-4 floor for row 17), which is
not a bracket index, so they carry the CY2023 sums of CBO's own printed parameters and are not
indexed — the same treatment `cbo_opt46_agi_surtax_1pp_20k` gives CBO's own fixed dollar amounts,
and a stated limitation rather than a choice of boundary. A test asserts every one of those amounts
against the schedule file, so none of them is a hand-typed number.

### 2.2 Examined and excluded, with the reason

All 100 revenue options carry a verdict in the CSV. The exclusions that are *not* simply "a base
change the generic path cannot express" are:

| what | where | why |
|---|---|---|
| "Increase the Payroll Tax Rate for Social Security" | 2018 · 19, 2020 · 16 | A rate change on the **capped** base. The runnable payroll shape is a flat rate on *uncapped* covered earnings; the module's capped branch reads a window-average constant (`CBO_PAYROLL_ESTIMATES['rate_1pp_annual']`), which fails the no-fitted-parameter bar. Its two alternatives are transcribed anyway, so the exclusion is visible at the alternative level. |
| "Increase the Maximum Taxable Earnings…", "Expand Social Security Coverage…" | 2018 · 20, 21; 2020 · 17, 18; 2022 · 49 | **Leakage**: the payroll module's cap constants are fitted to `ss_donut_250k` and `ss_cap_elimination`. |
| "Change the Tax Treatment of Capital Gains From Sales of Inherited Assets" | 2018 · 6, 2020 · 6, 2022 · 40 | **Carryover basis**, a deferred-realization rule — not the constructive-realization-at-death channel `CapitalGainsPolicy` has. CBO's 2024 Option 51 prints both alternatives and the battery already scores the constructive one. |
| "Reduce Tax Subsidies for Employment-Based Health Insurance" | 2018 · 12 | Its only income-tax-only alternative **replaces the ACA excise tax on high-cost plans**, so CBO's target is net of repealing a levy the expenditure module's baseline does not contain. The 2022 and 2024 editions limit the exclusion against a baseline with no excise tax; this is the reason `tax_expenditure` stops at n = 2 (§3). |
| "Raise the Tax Rates on LTCG…**and Adjust Tax Brackets**" alternatives 2 and 3 | 2018 · 2 | Realigns the preferential-rate bracket boundaries with the ordinary brackets. `CapitalGainsPolicy` prices a rate change, not a bracket realignment. Alternative 1 is the rate change alone and is registered. |
| "Limit the Income **and Payroll** Tax Exclusion…" | 2022 · 6 · 1, 6 · 2 | Out of scope per alternative — the expenditure module has no payroll base. Identical to the 2024 volume's exclusion of Option 56's first two alternatives. |
| "Increase Appropriations for the IRS's Enforcement Initiatives" | 2018 · 40, 2020 · 31 | Scored by the calibrated `IRSEnforcementPolicy`; the generic path would double-count it across tiers. |

---

## §3 — The expected outcome, stated as a rule rather than a number

1. **Every existing row scores to the cent what it scores today.** All 22, plus all 55 calibrated
   rows, plus `run_loo.py --donor-matrix`.
2. **n goes 22 → 44.** Criterion ①'s size condition wants 40; this clears it, and the
   **distinct-reform count** is reported beside it because four editions of one option are not four
   reforms.
3. **The tier mean may rise, and a rise is not a failure.** The rule selects for expressibility,
   not for fit; the two new classes of hard case it introduces are a 2018-vintage decade and a
   corporate rate priced on three more baselines. `ROUTE_TO_8_5.md` §1 R3 registered this in
   advance ("a battery selected for expressibility rather than for fit is the *only* honest way to
   grow it"), and so does this lane. What is *not* acceptable is a rise nobody can attribute: §5
   reports per-row errors and per-class means for all 44.
4. **Seven of the eight classes reach n ≥ 3. `tax_expenditure` cannot, and the reason is in the
   documents**: CBO's four volumes contain exactly three employment-based-health-insurance options
   with an income-tax-only alternative, one of which (2018) is net of an excise-tax repeal. It ends
   at **n = 2**, and criterion ① is therefore met on 7 of 8 classes rather than 8 of 8. Corporate
   goes **1 → 4** and `agi_inclusive_surtax` **2 → 4**, which are the two counts ROUTE §0 named.
5. **The gate is reported, never edited.** §5 prints what
   `tests/test_ci_workflow.py::test_no_gate_is_looser_than_the_workflow_rule_derives` derives for
   the pooled ceiling (`ceil(mean × 1.25)` rounded up to a multiple of 5), the pooled floor
   (`within_25 − 1`) and each per-class ceiling (`ceil(class mean × 1.25)`), and says plainly
   whether the live values pass on the grown battery.

### What would falsify this lane

- Any existing row's `model_10yr_billions` moving.
- Any candidate in §2.1 dropped after it was scored, or any target edited after a run.
- Any module file appearing in the diff.
- Any gate value changed in `.github/workflows/`.
- A row registered with a shape its source does not state — in particular, an
  `income_threshold_by_filing_status` amount that is not CBO's own published parameter for that
  calendar year (a test asserts every one of them against `cbo_tax_parameters.csv`).

---

## §4 — Pre-registered arithmetic

Computed before any record was made runnable, by replaying each candidate through
`create_policy_from_score` on its own window — the same call the runner makes. If the outturn
differs from any figure in §5's table by more than \$0.1B, something moved that should not have.

*(Filled in at §5 with the outturn. The predictions themselves are in the commit that entered these
rows: the model figures cannot be produced without running the scorer, so the falsification test
this lane offers is the **byte-identity of the 22 existing rows**, not a prediction of the 22 new
ones — a battery whose new rows could be predicted in advance would not be out of sample.)*

---

## §5 — Outturn

### 5.1 The tier, before and after

| | before | after |
|---|--:|--:|
| n | 22 | **44** |
| distinct reforms | 21 | **25** |
| mean abs error | 11.8% | **18.0%** |
| median | 8.9% | **12.3%** |
| within 15% | 17 | **26** |
| within 25% | 19 (86.4%) | **35 (79.5%)** |
| error mass | 258.9 | **793.8** |
| `secondhand` / `model_estimate` targets | 0 / 0 | **0 / 0** |

**Every one of the 22 existing rows scores to the cent what it scored before**,
checked row by row on the two `cold_holdout.py --json` runs; all four calibrated
blocks (`calibrated_reference`, `uncalibrated_reconstruction`,
`retired_targets`, `uncalibrated_reconstruction_retired_held_in_place`) compare
`SAME`; and `run_loo.py --donor-matrix` is byte-identical.

**The mean rose 11.8% → 18.0% and §3(3) registered that in advance.** Read it
with two things beside it: the count within 15% went 17 → **26**, and the
distinct-reform count went 21 → **25**. The battery is bigger, harder and more
honest; it is not more accurate, and nothing here made it so.

### 5.2 The 44 rows

| # | row | new? | target ($B) | model ($B) | error |
|--:|---|:-:|--:|--:|--:|
| 1 | `cbo2019_opt24_corporate_rate_1pp` | **new** | -96.3 | -192.3 | 99.7% |
| 2 | `cbo2021_opt19_corporate_rate_1pp` | **new** | -99.3 | -191.8 | 93.1% |
| 3 | `cbo2023_opt50_corporate_rate_1pp` | **new** | -129.3 | -192.9 | 49.2% |
| 4 | `cbo_opt64_corporate_rate_1pp` | | -135.7 | -196.1 | 44.5% |
| 5 | `cbo2021_opt1_top4_brackets_1pp` | **new** | -203.3 | -285.9 | 40.6% |
| 6 | `cbo_opt51_gains_at_death` | | -536.1 | -345.9 | 35.5% |
| 7 | `cbo2021_opt15_hi_payroll_2pp` | **new** | -1,736.3 | -2,336.9 | 34.6% |
| 8 | `cbo2021_opt15_hi_payroll_1pp` | **new** | -877.5 | -1,173.3 | 33.7% |
| 9 | `biden_capital_gains_39` | | -288.6 | -366.4 | 27.0% |
| 10 | `cbo2023_opt13_top4_brackets_2pp` | **new** | -501.9 | -621.4 | 23.8% |
| 11 | `biden_high_income_tax` | | -245.9 | -299.8 | 21.9% |
| 12 | `cbo2019_opt18_hi_payroll_2pp` | **new** | -1,786.5 | -2,149.2 | 20.3% |
| 13 | `cbo2019_opt18_hi_payroll_1pp` | **new** | -898.3 | -1,079.0 | 20.1% |
| 14 | `cbo2021_opt1_top2_brackets_1pp` | **new** | -113.8 | -136.5 | 19.9% |
| 15 | `cbo2023_opt37_ltcg_qdiv_2pp` | **new** | -102.1 | -82.6 | 19.1% |
| 16 | `cbo2023_opt13_agi_surtax_2pp_bracket4` | **new** | -773.8 | -914.3 | 18.2% |
| 17 | `cbo_opt45_top4_brackets_2pp` | | -569.5 | -671.2 | 17.9% |
| 18 | `cbo2021_opt1_all_rates_1pp` | **new** | -884.0 | -1,016.7 | 15.0% |
| 19 | `illustrative_1pp_all` | | -1,081.3 | -1,235.7 | 14.3% |
| 20 | `cbo_opt56_employer_health_income_only` | | -697.0 | -608.1 | 12.8% |
| 21 | `cbo2023_opt15_new_payroll_2pct` | **new** | -2,252.7 | -2,536.0 | 12.6% |
| 22 | `cbo2019_opt1_top4_brackets_1pp` | **new** | -222.9 | -250.7 | 12.5% |
| 23 | `fra_2023_discretionary_caps` | | -1,331.8 | -1,169.5 | 12.2% |
| 24 | `cbo2023_opt15_new_payroll_1pct` | **new** | -1,135.7 | -1,273.2 | 12.1% |
| 25 | `cbo_opt43_state_local_grants` | | -66.7 | -73.9 | 10.8% |
| 26 | `cbo_opt47_ltcg_qdiv_2pp` | | -103.3 | -92.5 | 10.5% |
| 27 | `ssfa_wep_gpo_repeal_outlays` | | 195.7 | 214.8 | 9.8% |
| 28 | `cbo_opt39_pell_eligibility` | | -22.1 | -20.3 | 8.1% |
| 29 | `cbo_opt61_new_payroll_tax_2pct` | | -2,540.0 | -2,745.0 | 8.1% |
| 30 | `cbo_opt46_agi_surtax_1pp_20k` | | -1,440.1 | -1,326.3 | 7.9% |
| 31 | `cbo_opt61_new_payroll_tax_1pct` | | -1,281.5 | -1,378.2 | 7.5% |
| 32 | `cbo2019_opt2_ltcg_qdiv_2pp` | **new** | -69.6 | -65.9 | 5.3% |
| 33 | `cbo_opt38_national_service` | | -10.3 | -10.6 | 2.6% |
| 34 | `cbo_opt46_agi_surtax_2pp_100k` | | -1,051.0 | -1,075.8 | 2.4% |
| 35 | `cbo2021_opt2_ltcg_qdiv_2pp` | **new** | -75.2 | -73.8 | 1.9% |
| 36 | `treasury_capgains_39_plus_stepup_elim` | | -322.0 | -316.1 | 1.8% |
| 37 | `cbo_opt42_nondefense_discretionary` | | -339.0 | -333.3 | 1.7% |
| 38 | `cbo2023_opt6_employer_health_income_only` | **new** | -651.4 | -659.9 | 1.3% |
| 39 | `cbo_opt45_all_rates_1pp` | | -1,185.3 | -1,201.2 | 1.3% |
| 40 | `cbo2019_opt1_top2_brackets_1pp` | **new** | -123.4 | -124.4 | 0.8% |
| 41 | `cbo2019_opt1_all_rates_1pp` | **new** | -905.4 | -912.7 | 0.8% |
| 42 | `cbo2023_opt13_agi_surtax_1pp_stdded` | **new** | -1,329.1 | -1,325.7 | 0.3% |
| 43 | `iija_2021_discretionary` | | 415.4 | 414.3 | 0.3% |
| 44 | `cbo_opt37_international_affairs` | | -187.0 | -186.9 | 0.0% |

### 5.3 By class

| class | n (was) | mean (was) | mass | share | w15 | w25 |
|---|--:|--:|--:|--:|--:|--:|
| corporate | **4** (1) | **71.6%** (44.5) | 286.5 | 36.1% | 0 | 0 |
| ordinary rate change | **11** (4) | **15.3%** (13.8) | 168.8 | 21.3% | 6 | 10 |
| payroll | **8** (2) | **18.6%** (7.8) | 149.0 | 18.8% | 4 | 6 |
| capital gains | **7** (4) | **14.4%** (18.7) | 101.1 | 12.7% | 4 | 5 |
| AGI-inclusive surtax | **4** (2) | **7.2%** (5.2) | 28.8 | 3.6% | 3 | 4 |
| discretionary spending | 5 (5) | 4.6% (4.6) | 23.2 | 2.9% | 5 | 5 |
| enacted-law spending | 3 (3) | 7.4% (7.4) | 22.3 | 2.8% | 3 | 3 |
| tax expenditure | **2** (1) | **7.1%** (12.8) | 14.1 | 1.8% | 2 | 2 |

**Criterion ① is met on three of its five conditions.** n ≥ 40 ✓ (44).
≥ 30/40 within 25% ✓ (35). Mean ≤ 12% ✗ (18.0%). Every class n ≥ 3 — **7 of 8**;
`tax_expenditure` stops at **2** and §2.2 says why in the documents: CBO's four
volumes contain exactly three employment-based-health-insurance options with an
income-tax-only alternative, and the 2018 one *replaces the ACA excise tax*, so
its target is net of repealing a levy the module's baseline does not contain. No
class mean above 25% ✗ (**corporate 71.6%**).

### 5.4 The finding: CBO prices one corporate reform four times and gets four numbers; the model gets one

This is the reason the corporate class was worth quadrupling, and it is the
sharpest measurement in the lane.

| volume | window | CBO's target | model | error |
|---|---|--:|--:|--:|
| 2018 (pub. 54667) | FY2019-2028 | −$96.3B | −$192.3B | 99.7% |
| 2020 (pub. 56783) | FY2021-2030 | −$99.3B | −$191.8B | 93.1% |
| 2022 (pub. 58163) | FY2023-2032 | −$129.3B | −$192.9B | 49.2% |
| 2024 (pub. 60557) | FY2025-2034 | −$135.7B | −$196.1B | 44.5% |

**CBO's own per-point yield for an identical 21%→22% increase rises 41.0% across
the four editions. The model's four answers span 2.2%.** PR #122 inferred that
flatness from one second target on one second decade and called it "exactly what
a vintage-anchored base could reproduce and a fixed base cannot"; four editions
of one option measure it directly, and the residual on any one row is therefore
mostly a **level** — the implied marginal share of the statutory base, 80.8%
against a published 55.1–79.5% — rather than a decade. Two caveats travel with
it and are on each row's `known_limitations`: CBO's transcribed receipts path
begins in FY2024, so the 2018 and 2020 rows are priced on
`cbo_corporate_receipts()`'s backward extrapolation (an extrapolation, not a
clamp, and the module says so); and all four rows score `derived` mode, which is
not the app default.

### 5.5 The second finding: the 2020 volume prices five repeated reforms *below* the 2018 volume

CBO's September 2020 baseline is pandemic-depressed, so for five of the six
options this battery repeats across those two editions the ten-year figure is
**smaller two years later**: all rates +1pp $905.4B → $884.0B, top four +1pp
$222.9B → $203.3B, top two +1pp $123.4B → $113.8B, HI +1pp $898.3B → $877.5B,
HI +2pp $1,786.5B → $1,736.5B. Only capital gains and corporate rise.

No model whose base grows monotonically with CBO's own nominal path can
reproduce a baseline that went backwards, and the four rows this hits are four
of the battery's six new Poor ratings (`cbo2021_opt1_top4_brackets_1pp` 40.6%,
`cbo2021_opt15_hi_payroll_2pp` 34.6%, `cbo2021_opt15_hi_payroll_1pp` 33.7%,
against the 2018 edition's 12.5%, 20.3% and 20.1% for the same three reforms).
`tests/test_cbo_options_multi_volume.py` asserts the *documents*, not the model,
so a transcription that ever flattened this would fail.

**A third finding sits underneath the payroll rows and is not about baselines.**
CBO's 2018 and 2020 HI options raise the *basic HI rate* and say the increase
"would be evenly split between employers and employees"; the runnable payroll
shape sets `employer_share=0.0`, which is CBO Option 61's own words for a
*different* design ("the new tax would be paid entirely by employees"). Base and
rate are identical, statutory incidence is not, and the compensation-shifting
offset is booked on the employee side only. That is why the four HI rows
(20.1%, 20.3%, 33.7%, 34.6%) sit above the four flat-tax rows (7.5%, 8.1%,
12.1%, 12.6%) even before the baseline is considered.

### 5.6 What the workflow's own rule now derives — reported, not edited

This lane does not touch `.github/workflows/`. On the grown battery the rule
derives the following, and **five of the eight live values are now wrong in the
tightening direction and one in the loosening direction**:

| gate | live | rule derives | verdict |
|---|--:|--:|---|
| pooled ceiling `--max-mean-error` | 15 | **25** (`ceil(18.0 × 1.25) = 23` → next 5) | **fails live** |
| pooled floor `--min-within-25pct` | 19 | **34** (`35 − 1`) | live value is **looser** than the rule; the rule forces a *tightening* |
| `corporate` | 56 | **90** | **fails live** |
| `ordinary_rate_change` | 15 | **20** | **fails live** |
| `payroll` | 10 | **24** | **fails live** |
| `agi_inclusive_surtax` | 7 | **9** | **fails live** |
| `capital_gains` | 24 | **18** | passes; rule tightens |
| `tax_expenditure` | 16 | **9** | passes; rule tightens |
| `discretionary_spending` | 6 | 6 | passes |
| `enacted_law_spending` | 10 | 10 | passes |

**Three tests in `tests/test_ci_workflow.py` fail on this branch and are meant
to**: `test_cold_holdout_gate_thresholds_match_the_live_battery` (18.0 > 15),
`test_the_per_class_floor_gates_every_class_the_battery_contains`
(`ordinary_rate_change` 15.3 > 15) and
`test_no_gate_is_looser_than_the_workflow_rule_derives` (floor 19 is looser than
34). Those three assertions *are* the re-derivation rule, and editing the
workflow is the gate lane's move under ROUTE owner ⑪ — H10's own process rule is
that the gate is re-derived **after** the rows land. Every other gate is green:
ruff, the mypy allowlist, `check_readiness.py --strict` (0 fail),
`build_validation_headline.py --check` after regeneration
(`out_of_sample_entries` 22 → **44**, `published_entries` 73 → **95**,
`total_entries` 77 → **99**), and the rest of the suite.

### 5.7 What did not move

`run_loo.py --donor-matrix` byte-identical. All 55 calibrated rows
byte-identical. All 22 pre-existing Tier 1 `model_10yr_billions` byte-identical.
No preset, no Tailor combination and no app surface moved, because no module was
opened and no shipped policy object changed — **no Decision 6 caption is owed**.

## §6 — Carry-overs

1. **The gate re-derivation**, §5.6, owner ⑪. Ten values, six of which move.
2. **Corporate is now a class of four and the largest thing in the tier at 36.1%
   of its mass.** R5/H3b's pre-registered bands were written against a class of
   one; the four-edition reading in §5.4 is new evidence for it and the bands
   should be restated on four rows before that lane opens.
3. **Spending options in the three earlier volumes are untranscribed**, by the
   selection rule's own §1.3 decision. Each needs its budget-authority path read
   and `is_level_budget_authority_path` applied. It would grow the battery's
   most accurate class, which is why it was not done here.
4. **`tax_expenditure` cannot reach n = 3 from CBO's *Options* volumes**, §5.3.
   A third row needs a different publisher or a different expenditure, and the
   module's cap-unit machinery has to be able to express it.
5. **The 2022 volume's Option 13 alternatives 3 and 4 carry a threshold this
   repository holds fixed.** CBO indexes the standard deduction and the
   bracket-4 floor annually; `TaxPolicy` carries one scalar threshold plus one
   statutory *bracket index*, and a second indexation source is a module change
   this lane may not make. Worth **0.3% and 18.2%** on the two rows as they
   stand, so it is not urgent — but it is the honest reason those two are the
   only rows in the battery whose boundary is stated as a formula and applied as
   an amount.
6. **The 2018 and 2020 corporate rows read a receipts path projected back past
   its own vintage.** CBO publishes corporate receipts in every *Budget and
   Economic Outlook*; transcribing the April 2018 and September 2020 editions
   would separate the module's marginal-share problem from the back-projection
   on those two rows.
7. **The HI rows' statutory incidence**, §5.5. CBO splits the rate increase
   evenly between employers and employees on four of the eight payroll rows and
   the shape books it entirely on employees. Expressing it is a `payroll.py`
   change.
8. **`cbo_options.py` now holds two idioms for the same judgement** — a
   hand-written `OUT_OF_SCOPE_REASONS` dict for the 2024 volume and a generated
   CSV for the other three. The CSV is the better one at this size; folding the
   2024 volume into it is a tidy-up nobody needs today.
