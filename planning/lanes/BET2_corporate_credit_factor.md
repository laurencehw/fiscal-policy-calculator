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
