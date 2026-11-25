# Lane SUPPLY: a corporate capital channel in the dynamic view (pre-registration)

Pre-registered 2026-11-25, before `dynamic_view.py` or the macro adapter is
edited on this branch. The predictions below are not edited after the first
code commit; the outturn is appended under the line at the end.

Owner decision (2026-11-25, project thread): "split", then "please try to fix
and implement". This is proposal 1 of
`planning/memos/GEMINI_REVIEW_2026-11-23_FOLLOWUPS.md` (a supply channel in the
dynamic view), rebuilt within the rules after Antigravity's PR #280 built it
outside them.

## 1. Why #280's version could not merge

#280 added a potential-GDP path for `CorporateTaxPolicy` (−0.075% of GDP per
+1pp, a five-year ramp) and for `TariffPolicy` (−0.95 × tariff revenue as a
share of GDP, a three-year ramp).

- **Neither constant has a source.** The docstring said −0.12% per point while
  the code used −0.075.
- **GDP was typed in** at $28T instead of the scored vintage's own path.
- **The sizes look too large.** Revenue feedback on the 28% corporate preset
  went from −$86.6B to −$380.6B, and on the universal tariff from −$140.8B to
  −$592.8B.
- **The tariff half reverses a recorded finding.** `HSC_h8_tariff_feedback.md`
  showed that a tariff GDP drag moves every trade row further from its
  conventional target, and the repository reports that drag *beside* the
  score, as Tax Foundation FF861 does.

## 2. What this lane does

For a `CorporateTaxPolicy` with a non-zero statutory `rate_change`, the
FRB/US-Lite dynamic view gains a supply path: the change in output that comes
from the change in the corporate capital stock. **Every input is sourced from a
file the repository already ships. No constant is introduced, and nothing
reads a scorecard target.**

For each year `t` of the scored window:

1. **The C-corporation EMTR and its change.** CBO's own effective marginal tax
   rate on C-corporation capital, `tp_emtr_capital_business_c_corp`, from
   publication 53724 (`cbo_tax_parameters`, the scored vintage). The statutory
   change scales it proportionally:
   `ΔEMTR_c = EMTR_c × Δτ / τ₀`, with `τ₀ = 21%`
   (`corporate.CURRENT_CORPORATE_RATE`). **This is an approximation**, and it
   is stated rather than hidden: with full expensing of equipment, the EMTR
   does not scale exactly with the statutory rate. CBO publishes the level, not
   the derivative.
2. **The C-corporation share of the capital stock.** CBO's aggregate EMTRs are
   capital-weighted means of their parts, so the weights can be read back from
   CBO's own figures:
   `s_cb = (E_business − E_passthrough) / (E_c_corp − E_passthrough)` and
   `s_bo = (E_overall − E_housing) / (E_business − E_housing)`, so
   `s = s_cb × s_bo`. On the February 2026 vintage `s` is about 0.44. A test
   fails if any year's `s` leaves (0, 1).
3. **The user cost.** With the repository's own α = 0.35, δ = 0.05 and
   K/Y = 3.0 (`constants.CAPITAL_SHARE` and the OLG calibration's BEA targets),
   the user cost is `c = α / (K/Y)` and the required return `ρ = c − δ`. A
   change in the EMTR changes the user cost by
   `dln c = (ρ / c) × ΔEMTR / (1 − EMTR)`.
4. **The long-run output effect.** With Cobb-Douglas output,
   `x*_t = −α / (1 − α) × s × dln c`.
5. **The path.** Capital closes the gap at the Solow convergence rate
   `λ = (1 − α)(g + δ)`, where `g` is the vintage's own mean real GDP growth
   over the window: `x_t = x_{t−1} + λ (x*_t − x_{t−1})`. After a sunset
   `Δτ = 0`, so the path decays back. On February 2026, `λ ≈ 0.044`.
6. **Into the view.** The GDP change is `x_t × nominal GDP_t` on the vintage's
   own path, and revenue feedback is that times the adapter's existing 0.25
   marginal revenue rate. The FRB/US-Lite adapter adds both to its demand
   results; nothing else in the adapter changes.

**What this is, said plainly.** It is the textbook user-cost channel with every
level taken from CBO's own tables and the repository's existing calibration.
It is not CBO's business-investment model. It covers the statutory-rate leg
only, so the Trump 15% preset's bonus-depreciation extension adds no supply
effect here. Labour supply is not in it.

**What does not change.**
- The conventional score, on every surface. All 44 out-of-sample rows, both
  calibrated tiers and the leave-one-out suite stay byte-identical.
- Every non-corporate policy's dynamic view. Tariffs stay demand-only in the
  view, with the drag reported beside the score as `HSC_h8` decided.
- The Simple Keynesian adapter stays demand-only, as its name says.
- Outlay routing (#280 also sent every refundable credit through outlays). It
  is a separate question and is not in this lane.

## 3. Predictions

Computed read-only against `main` (07be8b8) on 2026-11-25 with the formula
above, FY2026-2035, February 2026 vintage, FRB/US-Lite. Figures are ten-year
sums in $B. Bands: ±$1B.

| Preset | Conventional | Feedback now | Supply feedback | Feedback after | Dynamic total now | Dynamic total after |
|---|--:|--:|--:|--:|--:|--:|
| Biden Corporate 28% | −968.8 | −86.6 | **−162.2** | **−248.8** | −1,085.9 | **−923.7** |
| Trump Corporate 15% | +1,230.2 | +96.5 | **+139.0** | **+235.5** | +1,390.3 | **+1,251.3** |

Long-run output effect of the 28% preset in FY2035 (`x*`): **−0.84%** of GDP.
Effect reached by FY2035 (`x`): **−0.29%**.

Debt service does not move: the adapter prices it on the conventional deficit,
and this lane does not change that.

## 4. Falsification tests

- Any non-corporate preset's dynamic view moves, under either adapter: stop.
- Any validation artifact moves (`cold_holdout.py --json`,
  `run_validation_dashboard.py`, `run_loo.py --donor-matrix`): stop.
- A test fails if the supply function contains a typed GDP level, a typed
  EMTR, or reads any scorecard target.
- A test pins that a rate rise lowers output, a cut raises it, and a zero
  change gives exactly zero.
- A test fails if `s` leaves (0, 1) in any year of any vintage.
- If either preset lands outside its ±$1B band, the lane stops and finds out
  why before anything is adjusted.

**Not done in this lane, and said so.** The long-run figure is not checked
against a published dynamic score. Tax Foundation and PWBM both publish
long-run GDP effects for a 28% corporate rate, but their sites are not
reachable from this environment, and a figure from memory is not a check. That
comparison is the first follow-up, through Laurence's browser.

## 5. Surfaces

- The Methodology page and `CLAUDE.md` say FRB/US-Lite has "no supply-side
  channel". Both change to say it has one for corporate rate changes, and
  only for those.
- The two corporate presets carry a Decision 6 caption on the dynamic view,
  with the old feedback computed from the run rather than stored.

## 6. Not in this lane

- Supply effects for individual income tax rates (labour supply), payroll,
  capital gains or tariffs.
- Bonus depreciation and expensing.
- Outlay routing for refundable credits and the PTC.

---

## Outturn

*(appended after implementation)*
