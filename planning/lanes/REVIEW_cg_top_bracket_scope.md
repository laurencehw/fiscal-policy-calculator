# Lane `REVIEW_cg_top_bracket_scope` — Scope thresholded capital-gains rate changes to statutory brackets at or above the threshold

**Status:** Pre-registered; outturn appended below.
**Opened:** 2026-11-26
**Found on:** Sealed battery row `tf3_opt7_cg_top_rate_15` (`planning/lanes/REVIEW_sealed_battery.md`), which is retired to `RETIRED` in `fiscal_model/validation/sealed.py` under rule 3.
**Files touched by the fix:** `fiscal_model/policies_core.py`, `fiscal_model/validation/sealed.py`, `tests/test_capital_gains_bracket_scope.py`.

---

## 1. What is wrong

`CapitalGainsPolicy` reads its baseline from IRS SOI Table 3.5 (`fiscal_model/data_files/capital_gains/soi_capital_gains_by_rate_bracket.csv`), which classifies returns by **Adjusted Gross Income (AGI)** and disaggregates each AGI class's preferential income (long-term capital gains plus qualified dividends) into the statutory preferential rate brackets (`0%`, `15%`, `20%`) plus the 3.8% Net Investment Income Tax (`niit_rate`).

Under 26 U.S.C. §1(h), preferential capital gains and qualified dividends stack on top of ordinary taxable income through the `0%`, `15%`, and `20%` statutory brackets. Consequently, high-AGI returns in SOI Table 3.5 still carry preferential income taxed in the `0%` and `15%` brackets (where ordinary taxable income did not exhaust those lower slices). In tax year 2023:

- Above `$613,700` AGI (`get_brackets_above_threshold(2023, 613_700.0)`):
  - `(0%, +3.8% NIIT)`: `$3.76B` (0.49%)
  - `(15%, +3.8% NIIT)`: `$86.91B` (11.39%)
  - `(20%, +3.8% NIIT)`: `$672.08B` (88.11%)
- Above `$1,000,000` AGI (`get_brackets_above_threshold(2023, 1_000_000.0)`):
  - `(0%, +3.8% NIIT)`: `$2.02B` (0.30%)
  - `(15%, +3.8% NIIT)`: `$30.10B` (4.49%)
  - `(20%, +3.8% NIIT)`: `$638.64B` (95.21%)

Previously, `CapitalGainsPolicy.get_brackets()` returned **all three** statutory brackets for any `affected_income_threshold`, and `_reform_rate()` shifted every returned bracket's rate by `self.rate_change`. That has two structural defects:

1. **Cuts in the top rate crash.** A `-5pp` cut to the top preferential rate above `$613,700` (`tf3_opt7_cg_top_rate_15`) shifts the `(0%, 3.8%)` bracket to `0.00 - 0.05 + 0.038 = -0.012`, triggering `ValueError("Capital gains rates must be in [0, 1)...")`.
2. **High-threshold rate changes misprice the lower brackets.** A rate change stated above the top-bracket threshold (`$613,700` or `$1,000,000`) reaches only gains in the `20%` statutory bracket, not the `0%` and `15%` slices of those filers' returns. Applying `rate_change` to all three brackets overstates the base priced by `11.9%` at `$613,700` (`$762.75B` vs `$672.08B`) and `4.8%` at `$1,000,000` (`$670.76B` vs `$638.64B`) — and overstates net revenue even more on large rate hikes because the out-of-scope `0%` and `15%` brackets sit well below DMM's `30.6%` revenue-maximizing rate.

---

## 2. What the change does

Zero new constants, zero new parameters, and zero changes to any elasticity or data file.

`fiscal_model/data/capital_gains.py` already ships `LTCG_RATE_BRACKETS` — the statutory preferential rate ladder from Rev. Proc. 2024-40 (26 U.S.C. §1(h), single filer, 2025):

```python
LTCG_RATE_BRACKETS = (
    (0.0, 0.00),
    (48_350.0, 0.15),
    (533_400.0, 0.20),
)
```

In `CapitalGainsPolicy` (`fiscal_model/policies_core.py`):

1. Add `_threshold_statutory_rate(self) -> float`, which reads `LTCG_RATE_BRACKETS` and returns the highest statutory rate whose bracket floor is `<= self.affected_income_threshold`:
   - `threshold < $48,350` (including `$0`): `0.00` (all three brackets `0%`, `15%`, `20%` are in scope).
   - `$48,350 <= threshold < $533,400` (e.g. `$200K`, `$400K`): `0.15` (`15%` and `20%` brackets are in scope; `0%` is excluded).
   - `threshold >= $533,400` (e.g. `$613,700`, `$1,000,000`): `0.20` (only the `20%` top bracket is in scope; `0%` and `15%` are excluded).
2. In `CapitalGainsPolicy.get_brackets()`, after loading the SOI brackets above `self.affected_income_threshold` (the auto-populated SOI path only), retain only brackets with `bracket.statutory_rate >= self._threshold_statutory_rate()`.

**Algebraic equivalence and channel consistency:**

- **Static revenue:** Pricing `rate_change` only on `statutory_rate == 0.20` sums `rate_change * R_{c,20}` across AGI classes `c` above the threshold, which is algebraically identical to moving each AGI class's effective rate by `rate_change * (R_{c,20} / R_c)` (the statutory change times that class's top-bracket share).
- **Behavioral offset and stock drift:** Filtering out unreached brackets in `get_brackets()` keeps `baseline_realizations_billions`, `baseline_capital_gains_rate`, `_reform_capital_gains_rate()`, and `realizations_projection_caption` describing the exact base being priced, prevents `estimate_behavioral_offset()` from multiplying untouched `15%`-bracket gains by `stock_ratio`, and leaves `stock_ratio()`'s national hazard algebra (`1 - R_aff/N + R_aff*ratio/N`) exact.
- **Guardrails preserved:** Caller-supplied single-bracket bases (`baseline_realizations_billions > 0`), `threshold = 0` policies, and the `ValueError` guard for any cut that pushes a *reached* bracket below `0%` (e.g. `-5pp` at `threshold = 0`, or `-25pp` at `$613,700`) remain unchanged.
- **Known limitation (recorded, not tuned):** SOI Table 3.5 pools filing statuses, so `_threshold_statutory_rate()` reads the single-filer statutory boundaries in `LTCG_RATE_BRACKETS` (`$48,350` / `$533,400`). A threshold between the single and joint floors (`$48,350–$96,700` or `$533,400–$600,050`) is therefore classified using the single-filer floor. Every scored validation and sealed threshold (`$0`, `$613,700`, `$1,000,000`) lies strictly outside those gaps.

**Sealed-battery retirement (rule 3):** Add `tf3_opt7_cg_top_rate_15` to `RETIRED` in `fiscal_model/validation/sealed.py` naming this lane file. No sealed target is edited.

---

## 3. Pre-registered predictions

Every prediction below is derived from the SOI TY2023 bracket table (`soi_capital_gains_by_rate_bracket.csv`), the `5.8%/yr` stock growth factor, and frozen DMM (2015) elasticities (`-0.72` persistent, `-1.20` transitory at `22%`) before running the modified code:

1. **`tf3_opt7_cg_top_rate_15` (retired sealed row; `-5pp` above `$613,700`, FY2027–2036, Tax Foundation `+$170.7B`):**
   - Previously raised `ValueError`.
   - Predicted to score cleanly with a positive 10-year deficit (revenue loss) of roughly **`+$150B` to `+$165B`** (static `+$550B`, year-0 transitory realization surge `~-$40B`, years 1–9 net `~+$190B–$205B`).
2. **`tf3_opt8_cg_top_rate_30` (live sealed row; `+10pp` above `$613,700`, FY2027–2036, Tax Foundation `-$362.5B`):**
   - Previously `-$59.0B` (83.7% error).
   - Predicted to move **smaller in magnitude (further from Tax Foundation)** to roughly **`-$20B` to `-$35B`** (~90–94% error), because roughly `-$30B` to `-$35B` of the prior `-$59.0B` came from wrongly raising the out-of-scope `0%` and `15%` brackets (which sit below DMM's `30.6%` peak). Reported here per sealed-battery rule 3.
3. **`biden_capital_gains_39` (Tier 1 out-of-sample; `+19.6pp` above `$1M` + step-up elimination, FY2025–2034, Treasury `-$288.6B`):**
   - Previously `-$366.4B` (27.0% error).
   - Predicted to fall in magnitude by roughly `$25B–$30B` (removing the `$32.1B` of `0%` and `15%` bracket base) to roughly **`-$335B` to `-$342B`** (~16–19% error), bringing this row inside the 25% band.
4. **`treasury_capgains_39_plus_stepup_elim` (Tier 1 out-of-sample; `+19.6pp` above `$1M` + step-up elimination, FY2022–2031, Treasury `-$322.0B`):**
   - Previously `-$316.1B` (1.8% error).
   - **Pre-registered regression:** Predicted to fall in magnitude by roughly `$20B–$26B` to roughly **`-$290B` to `-$297B`** (~8–10% error), remaining inside 15%.
5. **All four `threshold = 0` capital-gains rows (`cbo_opt47_capgains_2pp` and the three R3 `+2pp` editions):**
   - Predicted **unchanged to the cent** (`_threshold_statutory_rate() == 0.0`, so all three brackets remain in scope).
6. **`cbo_opt51_gains_at_death` (`rate_change = 0`, `threshold = 0`):**
   - Predicted **unchanged to the cent**.
7. **All three specialized/LOO capital-gains scenarios (`pwbm_39_with_stepup`, `pwbm_39_no_stepup`, `jct_cg_2012_20pct`):**
   - Predicted **unchanged to the cent** (all supply `baseline_realizations_billions > 0`, bypassing SOI auto-population).
8. **All other 37 Tier 1 out-of-sample rows, all 14 fitted rows, all remaining reconstruction rows, and all 53 shipped presets:**
   - Predicted **unchanged to the cent** (no shipped preset uses `CapitalGainsPolicy`'s SOI rate-change path above `$48,350`).
9. **Tier 1 scorecard headline impact (requiring `scripts/build_current_evidence.py` regeneration after test execution):**
   - `capital_gains` class mean moves slightly down from `14.4%` to roughly **`13.8%–14.3%`** (well under the `18%` CI gate ceiling; `biden_capital_gains_39` drops ~9pp while `treasury_capgains_39_plus_stepup_elim` rises ~7pp).
   - Pooled 44-row mean moves from `10.6%` to roughly **`10.5%`**; within-25% count rises from `40/44` to **`41/44`**.

---

## 4. What would falsify this lane

- `tf3_opt7_cg_top_rate_15` still raises an error, gets the wrong sign, or lands outside **`+$135B` to `+$180B`**.
- `tf3_opt8_cg_top_rate_30` moves *closer* to Tax Foundation instead of smaller in magnitude (`-$20B` to `-$35B`).
- `biden_capital_gains_39` lands outside **`-$325B` to `-$350B`**, or `treasury_capgains_39_plus_stepup_elim` lands outside **`-$280B` to `-$305B`**.
- Any `threshold = 0` capital-gains row, `cbo_opt51_gains_at_death`, any caller-supplied capital-gains scenario, any non-capital-gains validation row, or any shipped preset moves by more than `$0.0B`.
- `scripts/audit_offset_signs.py` / `tests/test_offset_sign_contract.py` fails on `CapitalGainsPolicy` (in either direction).

---

## Outturn

Run 2026-11-26 by Claude, before and after the code commit on the same tree,
with `cold_holdout.py --json`, `run_loo.py --donor-matrix --json`,
`sealed_battery.py --json` and a probe of all 53 presets.

| Prediction | Outturn |
|---|---|
| 1. `tf3_opt7_cg_top_rate_15` scores +$150B to +$165B | **+$153.6B** (10.0% from Tax Foundation's +$170.7B) **held** |
| 2. `tf3_opt8_cg_top_rate_30` -$20B to -$35B | **-$24.8B** (93.2%) **held** |
| 3. `biden_capital_gains_39` -$335B to -$342B | **-$336.7B** (27.0% → 16.7%) **held** |
| 4. `treasury_capgains_39_plus_stepup_elim` -$290B to -$297B | **-$291.0B** (1.8% → 9.6%) **held**, a registered regression |
| 5-7. $0-threshold rows, gains at death, caller-supplied scenarios unchanged | unchanged; `run_loo.py --donor-matrix --json` byte-identical **held** |
| 8. Every other scorecard row and all 53 presets unchanged | only the two rows above moved; 53 of 53 presets identical **held** |
| 9. Class mean 13.8-14.3%; pooled ~10.5%; within-25 41/44 | class **14.4% → 14.1%**, pooled **10.6% → 10.5%** (median 8.3% → 8.5%), within-25 **40 → 41** **held** |

None of the falsification conditions fired.

**Not predicted, and recorded.** `tests/test_preregistration.py::test_a_named_window_is_the_decade_the_case_is_actually_scored_on`
asserted that the Treasury row scores nearer its target on its own FY2022
decade than on the default later one. With this fix the FY2022 decade reads
-$291.0B (31.0 off) and the later decade -$346.1B (24.1 off), so that half of
the test was an accuracy claim this lane ended. The half that tests the window
itself (the source's decade scores a smaller magnitude) still holds and stays.

Surfaces: `current_evidence.json` is regenerated. The live headline sentences in
README, CLAUDE.md, docs/VALIDATION.md and docs/METHODOLOGY.md, CLAUDE.md's
class table and error-mass line are updated. The CI floor is re-derived by the
workflow's own rule, 41 - 1 = 40.

