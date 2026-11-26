# Lane REVIEW-10: EconomicModel's capital path reaches GDP, and transfers read their own multiplier (pre-registration)

Pre-registered 2026-11-26, before `fiscal_model/economics.py` is edited on this
branch. The predictions below are not edited after the first code commit; the
outturn is appended under the line at the end.

Owner decision (2026-11-25, project thread): "please make these fixes", on the
open list of `planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md`. This is
proposal 10, and R9's recorded finding 1
(`planning/lanes/R9_economic_model_supply_weighting.md`).

## 1. What is wrong

`EconomicModel` is the library's `score_policy(dynamic=True)` model. No site
page, API route or Ask answer reports it: they all use `dynamic_view.py`. Two
defects remain in it.

1. **`_tax_policy_effects` computes a capital-stock path for corporate and
   capital-gains rate changes and never lets it reach output.** `capital` is
   returned as `capital_stock_change` and turned into `investment_change`, but
   `gdp_level` is built from the demand and labour terms only. So a corporate
   rate change has no supply effect in this model, which R9 recorded and left.
2. **`_transfer_policy_effects` hard-codes `transfer_multiplier = 0.8`.** The
   model computes a condition-adjusted `params['transfer_multiplier']` (0.736 on
   the default conditions: the 0.8 base times the debt adjustment) and reports
   it in `get_parameters`, but the transfer path ignores it.

## 2. What this lane does

1. Adds the capital path to output with the repository's own capital share:
   `supply_gdp += CAPITAL_SHARE × capital[i] × nominal_gdp[i]`, where `capital[i]`
   is the fractional change in the capital stock the module already computes.
   This is the Cobb-Douglas first-order term, `Δln Y = α × Δln K`, with
   `α = 0.35` (`constants.CAPITAL_SHARE`). The capital term enters the supply
   side, so it is weighted by `weight_supply` like the labour term.
2. Reads `self.params['transfer_multiplier']` in the transfer path.

No new constant is introduced. `capital_elasticity`, the `-rate_change × 0.5`
after-tax-return mapping and the five-year ramp are unchanged (their form is
R9's finding 2, out of scope here).

## 3. Predictions

Only `score_policy(dynamic=True)` can move. Nothing a user sees moves.

1. **Corporate and capital-gains rate changes:** a rate rise lowers
   `gdp_level_change` and `revenue_feedback` in every year after the first; a
   cut raises them. The sign of the capital term is the opposite of the rate
   change.
2. **Size:** for a +1 point corporate rate change in year 10 of the window,
   `capital = -0.005 × 0.25 × 2 = -0.25%` of the stock, so the added output
   effect is `0.35 × 0.25% = 0.0875%` of GDP before the supply weight, about
   `0.07%` after it. Feedback at the module's marginal revenue rate is a few
   billion dollars a year by the end of the window. The ten-year dynamic total
   for a +1 point corporate change moves by **between $5B and $40B**.
3. **Transfers:** every `TransferPolicy` dynamic GDP path scales by
   `0.736 / 0.8 = 0.92` on default conditions, exactly.
4. **Everything else is byte-identical:**
   - `cold_holdout.py --json` and the conventional score of every preset;
   - `dynamic_view.py` output for every preset (it never calls `EconomicModel`);
   - every income-tax, payroll, spending and generic dynamic path.

## 4. What would falsify it

- Any conventional figure, any `dynamic_view` figure or any scorecard row moves.
- The corporate move has the wrong sign or falls outside $5-40B.
- The transfer ratio is not 0.92.

---

## Outturn

Run 2026-11-26, before and after the edit on the same tree, with
`score_policy(dynamic=True)` on five probe policies, `cold_holdout.py --json`,
and `POST /score/preset` with `dynamic: true` for all 53 presets.

| Prediction | Outturn |
|---|---|
| A corporate rate rise lowers feedback; a cut raises it | +1pt: feedback -$19.7B -> -$47.9B; +7pt: -$130.0B -> -$327.4B; -6pt: +$126.4B -> +$295.5B |
| +1pt corporate dynamic total moves by $5-40B | -$125.2B -> -$97.0B, a move of $28.2B |
| Transfer GDP path scales by exactly 0.92 | 0.920 in all ten years |
| Income-tax dynamic path identical | identical (-$139.4B, feedback -$82.8B) |
| `cold_holdout.py --json` byte-identical | identical |
| Every preset's API dynamic figures identical | identical, 53 of 53 |

None of the falsification conditions fired.

The +7pt and -6pt corporate moves are large ($197B and $169B on the dynamic
total). That is this model's capital elasticity (0.25) and its
`-rate_change × 0.5` mapping from statutory rate to after-tax return, neither
of which is sourced (R9's finding 2). No surface reports `EconomicModel`, so
nothing a user sees moves. The site's dynamic view carries its own sourced
corporate channel since lane SUPPLY.

