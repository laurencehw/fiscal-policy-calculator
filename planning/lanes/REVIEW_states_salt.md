# Lane REVIEW-11: /states SALT from each state's own SOI distribution (pre-registration)

Pre-registered 2026-11-26, before `fiscal_model/models/state/salt_interaction.py`
or `fiscal_model/tax_expenditure_distributions.py` is edited on this branch.
The predictions below are not edited after the first code commit; the outturn
is appended under the line at the end.

Owner decision (2026-11-26, project thread): "i agree with your
recommendations -- please move forward". This is proposal 11 of
`planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md` (finding 2.4).

## 1. What is wrong

`compute_salt_lift` gives every state the national SOI Table 2.1 SALT
distribution, with amounts and incomes scaled by the state's average SALT. The
shape is the nation's, so a state with no income tax inherits the nation's
high-SALT tail. On the live /states page, Texas ($86,814) and Florida
($87,374) show larger average deduction gains above the cap than California
($81,891) and New York ($82,015).

## 2. What this lane does

- Adds `data_files/state_taxes/soi_state_salt_ty2022.csv`, an extract of IRS
  SOI Historic Table 2 for tax year 2022 (`22in55cmcsv.csv`; the sha256 is in
  the provenance file). It holds each state's SALT claimants, its amount
  before the limitation (income or sales, real estate and personal property
  taxes), and its limited amount under the $10,000 cap, for ten AGI classes.
  Every class's mean AGI was checked to lie inside the class bounds the file
  is read with.
- Builds each state's `CappedDeductionDistribution` from its own rows, with
  the same construction the national one uses (`load_capped_deduction_distribution`):
  - the within-class dispersion is identified by the two published columns
    at the observed $10,000 cap;
  - marginal rates come from `statutory_marginal_rate`.
- `compute_salt_lift` reads that distribution directly: SOI's state claimant
  counts replace the `filers x pct_itemizers` approximation, and the scale
  factor is gone.
- The amounts stay at tax-year-2022 levels, as the national path's stay at
  2023. No growth is added, so the comparison with the old figures isolates
  the change of distribution.

## 3. Predictions (current-law cap, 2025)

1. **The inversion goes:** California's and New York's average deduction gain
   above the cap each exceed Texas's and Florida's.
2. California and New York remain the two largest federal revenue costs of
   lifting the cap.
3. Texas's and Florida's revenue costs each fall in magnitude.
4. **Nothing outside /states moves:** `cold_holdout.py --json` and every
   preset's score are byte-identical. The national SALT presets read the
   national distribution, which this lane does not touch.

## 4. What would falsify it

- Any of predictions 1-3 fails.
- Any figure outside the states view moves.

---

## Outturn

Run 2026-11-26 with `result_views.states_view()`, before and after the edit
on the same tree. Current-law cap, 2025, per state:

| State | Avg gain above cap, before | after | Federal cost ($B/yr), before | after |
|---|--:|--:|--:|--:|
| CA | $81,891 | **$119,046** | -8.75 | **-20.31** |
| NY | $82,015 | **$182,654** | -7.86 | **-12.60** |
| TX | $86,814 | **$35,805** | -1.39 | **-1.17** |
| FL | $87,374 | **$75,075** | -0.84 | **-2.44** |
| IL | $83,754 | $85,304 | -1.52 | -2.00 |
| PA | $85,730 | $71,422 | -1.15 | -1.22 |
| GA | $86,345 | $76,594 | -0.66 | -1.30 |
| NC | $86,929 | $74,851 | -0.50 | -1.06 |
| OH | $86,610 | $76,167 | -0.71 | -0.85 |
| MI | $86,660 | $68,385 | -0.56 | -0.65 |

1. **The inversion goes: held.** California and New York now gain $119k and
   $183k per affected filer, against Texas's $36k and Florida's $75k.
2. **California and New York remain the two largest costs: held.**
3. **Texas's and Florida's costs each fall: failed for Florida.** Texas falls
   from $1.39B to $1.17B. Florida rises from $0.84B to $2.44B. Florida's own
   distribution has about 91,000 filers above the cap, against the 26,000 the
   national shape implied, because its top AGI classes carry large property
   and sales tax bills. The national shape, scaled down to Florida's low
   average, had hidden that tail. Recorded rather than adjusted.
4. **Nothing outside /states moves: held.** The national SALT distribution and
   its presets are untouched. `states.json` is the only export file that
   changes.

**Not done: NJ, CT and MA.** The SALT half would work for any state now, since
the SOI file covers all 50 states and DC. But a state on the page also needs
2025 brackets, deductions, exemptions and a combined state-and-local rate for
the income-tax curves. Those need sourcing from each state's revenue
department, and that is its own job.

