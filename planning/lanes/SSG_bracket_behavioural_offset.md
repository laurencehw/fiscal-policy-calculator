# Lane SSG: bracket-specific behavioural offset (pre-registration)

Pre-registered 2026-11-25, before `policies_core.py` is opened on this branch.
The predictions below are not edited after the first code commit; the outturn
is appended under the line at the end.

Owner decision (2026-11-25, project thread): "split", then "please try to fix
and implement". This is proposal 4 of
`planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md`, rebuilt within the
rules after Antigravity's PR #280 built it outside them.

## 1. Why #280's version could not merge

#280 replaced `offset = ETI x 0.5 x static` with `ETI x tau/(1-tau) x a`, which
is the right formula (Saez, Slemrod and Giertz 2012, *JEL* 50(1), eq. 3: the
share of a rate change's mechanical revenue lost to the taxable-income
response above a floor z* is `e x tau/(1-tau) x a`, with `a = z_m/(z_m - z*)`).
But:

- **tau and a were typed in**: a five-step lookup by threshold, with no source
  file.
- **It was tuned on the held-out rows.** The agent scored the 44 out-of-sample
  rows with a patched weight, then added a bracket-number-to-threshold map, and
  only then adopted the weight. That map read an attribute
  (`statutory_bracket_number`) that does not exist on `TaxPolicy`, and so did
  its filing-status branch (`filing_status_thresholds`; the field is
  `threshold_by_filing_status`). Both branches were dead code.
- It lowered three CI ceilings to fit the tuned result.

## 2. What this lane does

`TaxPolicy.estimate_behavioral_offset` keeps the ETI and the sign convention,
and replaces the 0.5 with a weight computed from data the repository already
ships. **No constant is introduced, and nothing reads a scorecard target.**

For a plain `TaxPolicy` of type `INCOME_TAX` with a non-zero `rate_change`:

- **a(z\*)**: for each filing status, every SOI Table 1.1 AGI class above that
  status's floor (`resolved_filing_status_thresholds()`), apportioned the way
  the static base already is (`get_bracket_distribution_by_status`,
  `_shares_above_threshold`). `z_m` is the mean income per return above the
  floors, in the policy's own `income_measure`. `z*` is the return-weighted
  mean floor. `a = z_m / (z_m - z*)`, and `a = 1` at a $0 floor.
- **tau(z\*)**: CBO's statutory ordinary schedule (`cbo_tax_parameters`, the
  SOI tax year, the earliest vintage covering it). Each status-class's mean
  taxable income per return is placed in its own status's bracket. The rates
  are weighted by that class's income above the floor, which is the base the
  rate change applies to.
- **weight = tau/(1-tau) x a**, evaluated once per policy at its SOI base tax
  year.
- Every other policy keeps 0.5. That covers capital gains, corporate, payroll,
  credits, any `TaxPolicy` subclass, and zero-rate-change income tax policies.

**What this is, said plainly.** It is SSG's formula with tau and a measured
from SOI and the statute. It still assumes a constant tau above the floor (SSG
do too), and it uses federal statutory rates only, not state or payroll. The
ETI stays the repository's 0.25.

**What it costs, said in advance.**
- **The 44 rows are not clean for this lane.** #280 already showed that a
  bracket-specific weight improves the top-bracket rows. This lane has no
  tunable parameter and computed its weights before projecting any row error.
  Even so, the tier is printed with and without the lane, and the pooled
  figure is not described as an independent test of it.
- **Broad rate changes get a smaller offset than now** (0.345 against 0.5), so
  the all-brackets rows overshoot more. This is a registered regression.

## 3. Predictions

The weights come from the derivation above, run read-only against `main` on
2026-11-25. Each prediction is the current `main` value times
`(1 - 0.25w) / (1 - 0.25 x 0.5)`, because the behavioural offset is linear in
the weight. Bands are ±1.5pp of error, or ±2% of the figure.

### 3.1 Out-of-sample rows that move (15 of 44)

| Row | w | Target | Now | Predicted | Now err | Predicted err |
|---|--:|--:|--:|--:|--:|--:|
| `cbo2023_opt13_agi_surtax_1pp_stdded` | 0.413 | −1,329.1 | −1,329.0 | −1,362.0 | 0.0% | 2.5% |
| `cbo2023_opt13_agi_surtax_2pp_bracket4` | 0.933 | −773.8 | −916.6 | −803.2 | 18.4% | 3.8% |
| `cbo_opt46_agi_surtax_1pp_20k` | 0.456 | −1,440.1 | −1,322.3 | −1,338.9 | 8.2% | 7.0% |
| `cbo_opt46_agi_surtax_2pp_100k` | 0.863 | −1,051.0 | −1,072.6 | −961.4 | 2.1% | **8.5% (regression)** |
| `biden_high_income_tax` | 1.232 | −245.9 | −306.8 | −242.6 | 24.8% | 1.3% |
| `cbo2019_opt1_all_rates_1pp` | 0.345 | −905.4 | −930.5 | −971.7 | 2.8% | **7.3% (regression)** |
| `cbo2019_opt1_top2_brackets_1pp` | 1.260 | −123.4 | −129.8 | −101.6 | 5.2% | **17.7% (regression)** |
| `cbo2019_opt1_top4_brackets_1pp` | 1.071 | −222.9 | −258.6 | −216.4 | 16.0% | 2.9% |
| `cbo2021_opt1_all_rates_1pp` | 0.345 | −884.0 | −1,000.5 | −1,044.8 | 13.2% | **18.2% (regression)** |
| `cbo2021_opt1_top2_brackets_1pp` | 1.260 | −113.8 | −137.9 | −108.0 | 21.2% | 5.1% |
| `cbo2021_opt1_top4_brackets_1pp` | 1.071 | −203.3 | −278.0 | −232.6 | 36.7% | 14.4% |
| `cbo2023_opt13_top4_brackets_2pp` | 1.036 | −501.9 | −583.6 | −494.2 | 16.3% | 1.5% |
| `cbo_opt45_all_rates_1pp` | 0.345 | −1,185.3 | −1,132.0 | −1,182.1 | 4.5% | 0.3% |
| `cbo_opt45_top4_brackets_2pp` | 1.033 | −569.5 | −614.6 | −521.0 | 7.9% | **8.5% (regression)** |
| `illustrative_1pp_all` | 0.345 | −1,081.3 | −1,264.5 | −1,320.5 | 16.9% | **22.1% (regression)** |

### 3.2 Pooled and by class

- Pooled, 44 rows: mean 12.2% → **10.6%** (±0.3), median 10.3% → **8.3%**,
  within 15% 30 → **34**, within 25% 39 → **40**.
- Ordinary rate change (11 rows): 15.0% → **9.0%** (±0.5).
- AGI-inclusive surtax (4 rows): 7.2% → **5.5%** (±0.5).
- The other six classes do not move. Tax expenditure and discretionary
  spending may shift in the second decimal if a row's policy is a plain
  income-tax `TaxPolicy`; anything larger stops the lane.

### 3.3 Shipped presets (conventional, FY2026-2035)

| Preset | w | Now | Predicted |
|---|--:|--:|--:|
| Top Rate to 39.6% (Biden FY2025) | 1.385 | −$309.8B | **about −$231B** |
| High-Earner Medicare Surcharge 2pp | 1.385 | −$450.3B | **about −$336B** |
| Top Rate to 45% | 1.023 | −$1,036.7B | **about −$882B** |
| Progressive Millionaire Tax | 0.904 | −$927.5B | **about −$821B** |
| Warren Ultra-Millionaire Surtax | 0.847 | −$483.7B | **about −$436B** |
| Middle Class Tax Cut | 0.670 | +$1,473.2B | **about +$1,402B** |
| Across-the-board / flat (all brackets) | 0.345 | +$6,585.0B | **about +$6,877B** |

Each moved preset carries a Decision 6 caption on its page saying the
behavioural offset now follows SSG.

## 4. Falsification tests

- Any row outside the ordinary-rate and AGI-surtax classes moves by more than
  0.1pp: stop.
- A test fails if the weight function reads any scorecard target, or if it
  contains a literal tau or a value.
- A test pins that a $0 floor gives `a = 1`, and that w rises from the
  all-brackets case to the $400K case.
- `run_loo.py --donor-matrix`: recorded, not gated. LOO rows that are
  income-tax rate changes move, and that is expected.

## 5. CI gates

Gates move **only downward**, and only by the workflow's own rule
(`ceil(mean x 1.25)`, rounded to 5 for the pooled ceiling), from the outturn.
Nothing is loosened.

## 6. Also in this PR

The /tailor ETI control from #280 (0 to 0.8, default 0.25), because what the
ETI means changes with this lane.

## 7. Not in this lane

- State and payroll rates in tau.
- An ETI that differs by income.
- Capital gains and corporate behavioural responses.

---

## Outturn

*(appended after implementation)*
