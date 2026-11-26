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

Run 2026-11-26 with a before-and-after probe of every scorecard row and every
preset on the same tree, plus `cold_holdout.py --json` and
`run_loo.py --donor-matrix --json`.

| Prediction | Outturn |
|---|---|
| `repeal_individual_amt` $450.9B ± 0.2 | $450.9B (0.2% error) **held** |
| `repeal_corporate_amt` $219.5B ± 0.2 | $219.5B (0.2% error) **held** |
| `extend_tcja_amt` $450.9B, error 66.8% | $450.9B, 66.8% **held** |
| AMT first year about -4%, last year about +5% | individual: $39.3B → $37.6B in year 1 (-4.3%), $51.3B → $53.1B in year 10 (+3.5%) **held in direction**; the last-year rise is smaller than predicted |
| `extend_enhanced_ptc` under 0.1% | 366.2 → 365.7, **-0.12%: failed narrowly**. The 4% and the GDP path do not average out over the PTC row's 2026 start as closely as the ratio computed from 2025 suggested |
| `cold_holdout.py --json` byte-identical | **failed**: the out-of-sample tier and the reconstructions are identical, but the fitted tier's mean moved from 1.4% to 1.5% (median 0.0% → 0.1%), because the refit rows land 0.2% off rather than 0.0-0.1%. The prediction forgot that the fitted tier is in that file |
| `run_loo.py` byte-identical | **failed in the same way**: every held-out (derived) figure is identical, and only the `calibrated_*` reference columns for the three AMT cases moved |
| Non-AMT, non-PTC presets identical | **held**, 49 of 53 identical |
| AMT presets under 1% | individual relief and repeal +0.08% **held**; `amt-repeal-corporate` 220.1 → 217.0, **-1.39%: failed**. That preset starts in 2026 while its row starts in 2025, and a growth path, unlike a flat rate, sums differently from different starts. It is declared in `HEADLINE_ROW_DIVERGENCE` |

The failures are of two kinds.
- **Start years.** The PTC and corporate-AMT-preset misses come from start
  years: a flat rate gives the same sum from any start year, the GDP path does
  not, and the predictions were computed as if it did.
- **What the files contain.** The `cold_holdout` and `run_loo` misses are
  about the files, not the model. Both files report the fitted tier beside
  the held-out figures, and the prediction forgot that.

No held-out figure moved, no figure moved in a direction the lane did not
expect, and no fitted row left its band.

Surfaces: `README.md` and `CLAUDE.md` quote the fitted tier at 1.5%. The pinned
tests that fixed -39.3, 220.1 and 366.1863 are updated, with the lane named
beside each.

