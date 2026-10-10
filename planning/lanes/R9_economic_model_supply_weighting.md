# R9 — weight `EconomicModel`'s labour-supply channel by the share it reaches

**Status:** pre-registered 2026-10-10, before any code on this branch.
**Scope:** `fiscal_model/economics.py` only. Library path
`FiscalPolicyScorer.score_policy(dynamic=True)`. No app, API or Ask surface
reads `EconomicModel` since the routing decision of 2026-09-29
(`planning/ROUTE_TO_9.md`, "Status"), so this lane moves no number a user sees.

## 1. Diagnosis

`EconomicModel._tax_policy_effects` sets

```
labor_effect = -rate_change x labor_supply_elasticity        (every year)
supply_gdp   = labor_effect x nominal_gdp
```

so a rate change is applied to **all** of nominal GDP, whoever it reaches.
+2.6 points on income above $400,000 moves the hours of every worker in the
country by 0.39%. On `main` (FY2026–2035, `APP_DEFAULT_START_YEAR`):

| | value |
|---|--:|
| static deficit effect | −$345.41B |
| `EconomicModel` revenue feedback | −$216.09B |
| `final_deficit_effect` | **−$86.14B** |
| cumulative GDP level change | −$864.36B |

This is the −$86.1B `ROUTE_TO_9.md` recorded against the app's −$338.9B.

Only two policy classes reach the channel among the 53 presets plus Tailor's
custom row: the generic `TaxPolicy` rows (`rate_change ≠ 0`, eight presets and
the custom row) and the two `CorporateTaxPolicy` presets. Every other module
carries `rate_change = 0` and goes through demand alone.

## 2. Change

One weight, `labor_supply_affected_share(policy)`, multiplies `labor_effect`:

- **`INCOME_TAX`, `PAYROLL_TAX`:** AGI of returns above
  `affected_income_threshold` over all AGI, IRS SOI Table 1.1, TY2023, read
  with `IRSSOIData.get_filers_by_bracket` — the reader the generic scorer
  already uses. Threshold 0 → 1.0. **No new constant.**
- **`CORPORATE_TAX`, `CAPITAL_GAINS_TAX`, `ESTATE_TAX`:** 0.0. These rates reach
  no individual's marginal rate on labour income.
- **Any other type:** 1.0, today's behaviour.

AGI rather than wages because Table 1.1 carries no wage column and Table 1.4 is
not in the repository. AGI share above a high threshold **overstates** the
labour share there (top filers' income is more capital), so the weight is an
upper bound on the share of labour income reached, and the feedback it leaves
is an upper bound too.

Shares, TY2023: $50,000 → 0.8873; $400,000 → 0.3133; $500,000 → 0.2446;
$609,350 → 0.2275; $1M → 0.1664; $2M → 0.1208.

`hours_worked_change` and `labor_force_change` are read off `labor_effect`, so
they become economy-wide figures, which is what their names say.

Not changed, and recorded as findings rather than fixed here:
- the channel uses `−Δτ × ε` rather than `ε × Δln(1−τ)`, and applies no labour
  share to the GDP it moves;
- `capital_stock_change` and `investment_change` are computed and never enter
  `gdp_level`, so with a zero labour weight a corporate rate has demand effects
  only.

## 3. Pre-registered movements (FY2026–2035, `score_policy(dynamic=True)`)

Ten rows of 54 move; the other 44 are byte-identical in static, feedback, final
and GDP.

| row | feedback | final | GDP level (cum.) |
|---|--:|--:|--:|
| reference +2.6pp > $400K | −216.1 → **−95.9** | −86.1 → **−206.4** | −864.4 → −383.5 |
| Biden 2025 Proposal | −216.1 → −95.9 | −86.1 → −206.4 | −864.4 → −383.5 |
| Custom Policy (−2pp > $500K) | 177.5 → 75.8 | 138.2 → 240.0 | 710.1 → 303.1 |
| Progressive Millionaire Tax | −459.5 → −178.8 | −445.4 → −726.1 | −1,838.0 → −715.3 |
| Middle Class Tax Cut | 329.8 → 314.6 | 1,107.6 → 1,122.8 | 1,319.0 → 1,258.2 |
| Warren Ultra-Millionaire Surtax | −265.7 → −88.1 | −203.8 → −381.4 | −1,062.9 → −352.5 |
| Top Rate to 45% | −676.0 → −259.8 | −335.5 → −751.6 | −2,703.8 → −1,039.2 |
| High-Earner Medicare Surcharge 2pp | −194.3 → −101.8 | −245.0 → −337.5 | −777.2 → −407.3 |
| Biden Corporate 28% | −648.4 → −177.0 | −662.5 → −1,133.9 | −2,593.5 → −708.1 |
| Trump Corporate 15% | 613.5 → 209.5 | 949.2 → 1,353.2 | 2,454.2 → 838.2 |

Flat Tax Reform (threshold 0) does not move: its weight is 1.0.

The reference row's feedback erases **28%** of its static effect rather than 63%
(of the static deficit effect; 72% of the conventional score). It does not land
on the app's −$338.9B and is not meant to: that figure is a different model
that also nets debt service.

## 4. Unchanged, checked rather than asserted

- `scripts/cold_holdout.py --json` byte-identical;
- `scripts/run_validation_dashboard.py` output byte-identical;
- `scripts/run_loo.py --donor-matrix` byte-identical;
- `run_dynamic_view` for every preset under both macro models byte-identical
  (it never runs `EconomicModel`);
- every static score byte-identical.

## 5. Falsification

The lane has failed if any of: a row outside §3's ten moves; any §3 figure
misses by more than $0.1B; any §4 artefact changes; a test needs an
`EconomicModel` value it did not pin before re-pinned for a reason other than
this weight.
