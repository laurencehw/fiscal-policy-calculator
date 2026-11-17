# Bet 2: corporate marginal credit factor, calibrated to houses outside the scorecard (pre-registration)

Pre-registered 2026-11-17, before `corporate.py` is opened on this branch. The
predictions below are not edited after the first code commit; the outturn is
appended under the line at the end.

Owner decision (2026-11-17, decision card): "Rebuild it within the rules"
rather than merge Cursor's PR #254 as it stood or close it.

## 1. Why #254 could not merge as it stood

PR #254 scales the derived corporate rate channel by a factor
γ = 0.7679, the ratio of a mean published "implied marginal share" to the
module's mechanical 80.84%. Two of its three calibration figures are fine. The
third, Treasury's FY2022 Green Book rate-only row (−$857.817B), is the target of
the scorecard row `biden_corporate_28_fy2022`, which CLAUDE.md says is "not
fitted to this target and never to be fitted to it": it is the module's one
unfitted corporate check. #254 fitted to it and then reported it at 15.7% as an
unfitted reconstruction. #254 was also one commit, so nothing was registered
before code.

## 2. What this lane does

Port #254's mechanism and keep its guards, with one change: the calibration set
is **Tax Foundation and PWBM only**, the two rate-only scores of 21% → 28% on
CBO's February 2024 baseline over FY2025-2034 that no scorecard row targets.

| House | Source | Share of the vintage's average `receipts / τ` |
|---|---|--:|
| Tax Foundation | *Biden Budget Tax Proposals*, 21 June 2024, Table 4, −$935.8B | 55.11% |
| PWBM | *President Biden's FY2025 Budget Proposal*, 22 May 2024, Table 1, −$1,093B | 64.37% |
| **Mean** | | **59.74%** |

γ = 0.5974 / 0.8084 = **0.7390**, applied only to `_derived_rate_effect`.
`reported` mode, `BASELINE_TAXABLE_PROFITS_BILLIONS` (1900), β = 0.8 and the
4.80133 receipts-to-base ratio are untouched. CBO's 0.85/0.80 loss-firm haircut
stays refused, and γ must sit more than 2pp from both.

**What γ is, said plainly.** It is a fitted scalar. #254 named it "§38(c)
marginal credit absorption", and that channel is real and points this way, but
nobody publishes the constrained-taxpayer share that would measure it (SOI's
excess-position tables stop at TY2010). So the code, the tests and every surface
call it "calibrated to Tax Foundation and PWBM", not "sourced".

**What it costs, said in advance.**
- **The corporate out-of-sample class stops being independent of other
  estimators.** The four JCT *Options* rows are still never used, so the class
  is a cross-house transfer test: fit on two houses, test on a third. The
  scorecard, `cold_holdout.py` and the Methods page say so, and the pooled
  out-of-sample figure is printed both with and without this lane.
- **The Biden 28% house strip becomes partly circular.** Tax Foundation and
  PWBM are two of its four houses. The strip on corporate presets will say the
  model is calibrated to those two.
- **`biden_corporate_28` (Treasury FY2025, rate + GILTI) gets worse.** This was
  pre-registered as a regression rather than avoided.

## 3. Predictions

Every figure is the current `main` model value × 0.7390, because γ scales the
whole derived rate channel linearly (in #254, 113.5 / 147.8 = 0.768 = its γ).
Bands are ±1.0pp of error unless stated.

### 3.1 Out-of-sample corporate class (held out: never fitted)

| Row | Target | Now | Predicted | Now err | Predicted err |
|---|--:|--:|--:|--:|--:|
| `cbo2019_opt24_corporate_rate_1pp` | −$96.3B | −$147.8B | −$109.2B | 53.4% | **13.4%** |
| `cbo2021_opt19_corporate_rate_1pp` | −$99.3B | −$120.9B | −$89.3B | 21.8% | **10.0%** (under) |
| `cbo2023_opt50_corporate_rate_1pp` | −$129.3B | −$183.1B | −$135.3B | 41.6% | **4.6%** |
| `cbo_opt64_corporate_rate_1pp` | −$135.7B | −$196.1B | −$144.9B | 44.5% | **6.8%** |
| **class mean** | | | | **40.3%** | **8.7%** |

The 2020 row still has to be quoted with its COVID-denominator clause.

### 3.2 Pooled out-of-sample, 44 rows (only the four corporate rows move)

Mean 15.1% → **12.2%** (±0.2), within 15% 26 → **30**, within 25% 36 → **39**.
The figure without the lane stays 15.1%, and both are printed.

### 3.3 Calibrated tier

| Row | Target | Now err | Predicted err | Note |
|---|--:|--:|--:|---|
| `biden_corporate_28` | −$1,347.0B | 4.0% | **29.1%** (±1.5) | registered regression; target bundles GILTI |
| `biden_corporate_28_fy2022` | −$857.8B | 50.7% | **11.4%** (±1.5) | stays `calibrated_to_target=False`; not in the fit |
| `trump_corporate_15` | +$673.1B | 129.6% | **81.1%** (±3) | bonus-depreciation leg ($294B) unchanged |

### 3.4 Shipped presets (app window FY2026-2035), each with a Decision 6 caption

- 🏢 Biden Corporate 28%: −$1,310.9B → **about −$969B** (±$15B)
- 🏢 Trump Corporate 15%: +$1,562.8B → **about +$1,232B** (±$25B)
- No other preset moves. Leave-one-out has no corporate row and is byte-identical.

## 4. Falsification tests

- Any non-corporate out-of-sample row moves → stop.
- γ is computed from the two shares in code, and a test fails if any
  calibration figure equals a `CBO_SCORE_MAP` / scorecard target or comes from
  the four holdout rows.
- A test fails if γ is within 2pp of 0.80 or 0.85, or if the +1pp share is
  within 1pp of JCT's 0.5785 or 0.590.
- `run_loo.py --donor-matrix` byte-identical.

## 5. Not in this lane

- Re-deriving the CI gates (a corporate ceiling of 51 still passes). That
  follows as its own PR, by the workflow's rule.
- Any change to `reported` mode or `CORPORATE_APP_MODE`.

---

## Outturn

*(appended after implementation)*

Appended 2026-11-17, after implementation. Nothing above the line was edited.

### Predictions: every scored figure landed

γ = 0.5974 / 0.8084 = **0.7390** (`marginal_credit_factor()` returns 0.739035).

| Item | Predicted | Outturn |
|---|--:|--:|
| `cbo2019_opt24` | −$109.2B, 13.4% | −$109.2B, **13.4%** |
| `cbo2021_opt19` | −$89.3B, 10.0% (under) | −$89.4B, **10.0%** |
| `cbo2023_opt50` | −$135.3B, 4.6% | −$135.3B, **4.7%** |
| `cbo_opt64` | −$144.9B, 6.8% | −$144.9B, **6.8%** |
| Corporate class mean | 8.7% | **8.7%** (4 of 4 within 15%, mass 34.9) |
| Pooled out-of-sample | 12.2% (±0.2), 30 within 15, 39 within 25 | **12.2%**, **30**, **39** (median 10.3%, mass 538.8) |
| Pooled without the lane | 15.1% | **15.1%**, 26, 36, printed by `cold_holdout.py` beside the live figure |
| `biden_corporate_28` | 29.1% (±1.5) | **29.1%** (−$955.3B) |
| `biden_corporate_28_fy2022` | 11.4% (±1.5) | **11.4%**, still `calibrated_to_target=False` |
| `trump_corporate_15` | 81.1% (±3) | **80.9%** (+$1,217.4B) |
| 🏢 Biden Corporate 28% | about −$969B (±$15B) | **−$968.8B** |
| 🏢 Trump Corporate 15% | about +$1,232B (±$25B) | **+$1,230.2B** |

Decision 1's comparison on the three published corporate targets: `derived`
**40.43%** against `reported` 62.75% (unmoved). At +7pp the derived path scores
−$955.3B, inside the four-house span and near its Tax Foundation end, at a 56.3%
share of the average base.

### Falsification tests

- **No non-corporate out-of-sample row moved.** Checked against `main`'s
  `cold_holdout.py --json`: the only model figures that changed are the four
  corporate rows and the three corporate calibrated-tier rows.
- **`run_loo.py --donor-matrix` is byte-identical** to `main`.
- **No calibration figure is a scorecard or preset target**, and none comes
  from the four holdout rows: `tests/test_corporate_credit_factor.py` checks
  both, and checks that the excluded Treasury figure really is a target.
- **γ is more than 2pp from 0.80 and 0.85** (0.739).
- **The +1pp share against 0.5785:** 1.9pp away, passes.
- **The +1pp share against JCT's 0.590: FIRED.** The share is 0.5974, 0.74pp
  from 0.590, inside the 1pp band §4 set. This was a drafting error in this
  pre-registration, not something the code did. §2 itself predicts 59.74%, so
  the prediction and the guard could never both hold. Nothing in the calibration
  reads JCT: the share is the mean of Tax Foundation and PWBM, fixed before any
  code. Laurence was asked (decision card, 2026-11-17) and chose to keep the lane
  and record the miss. The test now pins the closeness as a finding
  (0.70–0.80pp), so a later change cannot move the share nearer JCT without
  failing. Read the corporate holdout result with this in mind. Two non-JCT
  houses happen to average out within a point of JCT, and that is a large part
  of why the four JCT rows land at 8.7%.

### Departures from §5

- **Two CI gates moved in this PR**: the corporate class ceiling 51 → **11** (`ceil(8.72 × 1.25)`) and the pooled within-25 floor 35 → **38** (`39 − 1`).
  §5 left gates to a follow-up PR. `tests/test_ci_workflow.py` fails any class
  ceiling more than twice its live mean, so leaving 51 would have turned CI
  red, and `test_no_gate_is_looser_than_the_workflow_rule_derives` does the same for the pooled floor. The pooled mean ceiling stays 20.
- **`biden_corporate_28` left the fitted tier** (fitted 15 → 14,
  reconstructions 38 → 39), as PR #254 had it. The rule is PR #119's:
  `BASELINE_TAXABLE_PROFITS_BILLIONS` is fitted so `reported` hits that target,
  but the scorecard scores `derived`. No constant was retuned.

### Surfaces

- `cold_holdout.py` prints the pooled figure with and without the factor and
  says the corporate class is a cross-house transfer test.
- The corporate house strips mark Tax Foundation and PWBM "(calibrated to)",
  and the strip's note says the model's closeness to those two is partly by
  construction (`estimator_ranges.house_strip`, tested).
- `corporate.py`, the corporate rows' known-limitations text, the Decision 6
  caption, CLAUDE.md, README and docs call the factor "calibrated to Tax
  Foundation and PWBM", never "sourced". Every preset JSON changed because the
  corporate known-limitations text is embedded in each. Only the two corporate
  presets changed in number.
