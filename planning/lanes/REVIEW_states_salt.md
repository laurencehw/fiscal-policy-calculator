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

(appended after the code commit)
