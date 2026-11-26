# Lane REVIEW-5: AMT and PTC levels grow on CBO's path, not a flat 3% or 4% (pre-registration)

Pre-registered 2026-11-26, before `fiscal_model/scoring_engine.py` or
`fiscal_model/amt.py` is edited on this branch. The predictions below are not
edited after the first code commit; the outturn is appended under the line at
the end.

Owner decision (2026-11-26, project thread): "i agree with your
recommendations -- please move forward". The recommendation was to switch to
the baseline's path and refit the two fitted AMT constants. This is proposal 5
of `planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md`.

## 1. What is wrong

`ScoringEngine._growth_tax_policy_handlers` grows a module's annual level by a
typed flat rate. Since earlier lanes switched the credit, estate, payroll,
corporate and PTC-repeal paths to their own year-indexed bases, a probe of the
scorecard and every preset (2026-11-26) finds exactly two module classes still
compounding a typed rate:

- `AMTPolicy` at **3%** (`AMT_ENGINE_GROWTH_RATE`): `extend_tcja_amt`,
  `repeal_individual_amt`, `repeal_corporate_amt` and the three AMT presets;
- `PremiumTaxCreditPolicy` at **4%** for `extend_enhanced_ptc`.

The tax-expenditure rows also reached the branch, but they grow at each
expenditure's own `growth_rate` from its data record, which is not this lane's
question.

The scored vintage's nominal GDP grows 5.2%, 4.4%, 4.1% and then about 3.8% a
year (February 2026), so 3% is below it in every year.

## 2. What this lane does

1. For `AMTPolicy` in **reported** mode and for `PremiumTaxCreditPolicy`, the
   engine grows the annual level by the scored baseline's own nominal GDP,
   `GDP_t / GDP_start`. Years before the window are bridged at the window's
   first-year growth rate. No constant is introduced.
2. **AMT derived mode is untouched.** It divides the engine's growth back out
   year by year (`AMTPolicy.get_phase_in_factor`), so its scored path is the
   module's own whatever the engine's rate. It keeps the flat 3% that it
   divides out.
3. **The two fitted constants are refit** so their rows stay fitted. The ratio
   is the flat path's ten-year sum over the GDP path's, on each row's own
   validation window:
   - individual (`-39.3`, FY2026-2035): × 11.4639 / 11.9915 → **-37.6**;
   - corporate (`-19.2`, FY2025-2034): × 11.4639 / 12.1289 → **-18.1**.

   `create_extend_tcja_amt_relief` reads the same -39.3 and moves with it.

## 3. Predictions

1. **Fitted rows stay fitted:** `repeal_individual_amt` goes from $450.5B to
   **$450.9B ± 0.2**, and `repeal_corporate_amt` from $220.1B to
   **$219.5B ± 0.2**. Both stay under 0.3% error.
2. `extend_tcja_amt`, a reconstruction against $1,357.1B, moves from $450.5B to
   **$450.9B ± 0.2**. Its error is unchanged to one decimal (66.8%).
3. **The year paths change shape and the totals do not:** each AMT row's first
   year falls by about 4% and its last year rises by about 5%.
4. `extend_enhanced_ptc` moves by **under 0.1%**: the 4% and the GDP path
   average out (ratio 0.9998).
5. **Byte-identical:**
   - `cold_holdout.py --json`, since no out-of-sample row is an AMT or PTC row;
   - `run_loo.py --donor-matrix`, since its AMT cases run in derived mode;
   - every non-AMT, non-PTC preset.
6. The three AMT presets' ten-year totals move by **under 1%**.

## 4. What would falsify it

- Any fitted AMT row leaves its band, or any row outside AMT and PTC moves.
- The leave-one-out suite moves.
- A derived-mode AMT path changes.

---

## Outturn

(appended after the code commit)
