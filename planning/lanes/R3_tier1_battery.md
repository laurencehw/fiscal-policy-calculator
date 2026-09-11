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

*Appended after the work.*

## §6 — Carry-overs

*Appended after the work.*
