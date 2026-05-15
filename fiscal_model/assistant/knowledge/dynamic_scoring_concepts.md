---
source: https://www.cbo.gov/publication/56038
title: How CBO Analyzes the Economic Effects of Changes in Federal Fiscal Policies
org: CBO
year: 2020
keywords: [dynamic scoring, conventional scoring, static, behavioral, macroeconomic feedback, multiplier, crowding out, frb us, olg, microsim, marginal rate, eti, supply side, demand side, neoclassical, keynesian]
---

# Dynamic scoring — concepts

## Definitions

- **Conventional (static) score**: holds GDP, employment, prices, and
  interest rates fixed. Captures only the mechanical, behavioral, and
  timing response of taxpayers to the change.
- **Dynamic score**: lets macro variables respond to the policy. Adds
  channels of feedback that "give back" or "amplify" the conventional
  number.

## CBO's two-track approach

CBO uses three tools, picking among them by policy size and horizon:

1. **Solow-style neoclassical** for supply-side changes operating on
   capital accumulation (e.g., corporate rate cuts). Time horizons:
   10+ years.
2. **Life-cycle / OLG** when a policy affects different generations'
   incentives differently (e.g., Social Security reform). Captures
   savings response.
3. **FRB/US** for shorter-horizon demand-side effects (e.g., stimulus,
   tax rebates). Captures aggregate-demand multipliers.

## Key feedback channels

- **Demand-side** (Keynesian, short-run): an increase in disposable
  income raises consumption; spending changes multiplied by ~1.4
  (CBO/FRB-US range); tax-rebate multiplier closer to 0.4–0.9.
- **Supply-side** (neoclassical, long-run): lower marginal rates raise
  labor and capital supply; raise GDP and revenue. Effects are slow and
  modest — for TCJA, dynamic feedback typically offsets **5–15%** of
  static cost.
- **Crowding out**: higher federal borrowing raises interest rates and
  reduces private investment. The app applies **15%** crowding out to
  cumulative deficits in `FRBUSAdapterLite`.
- **Open-economy offsets**: capital inflows can blunt crowding out,
  partly mitigating the long-run interest-rate response.

## What the app does

- **`FRBUSAdapterLite`** (default): multipliers of **1.4** (spending,
  year 1, decay 0.75) and **-0.7** (tax, year 1). Marginal revenue rate
  **0.25** for translating GDP changes into revenue.
- **OLG model** (in `fiscal_model/models/olg/`): 30-period Auerbach-
  Kotlikoff used for generational analysis (Social Security, Medicare).
- **Solow growth model** (in `fiscal_model/long_run/solow_growth.py`):
  long-run capital accumulation effects.

## Limitations to flag in answers

- Dynamic scores **disagree across models**. The same TCJA extension is
  scored by Penn Wharton, JCT, CBO, and Yale Budget Lab with overlapping
  but distinct ranges. Always cite the source's model.
- Dynamic scoring is **not** a free lunch: it can also raise the cost of
  a policy (e.g., interest-rate feedback on deficit-financed tax cuts).
- The choice of marginal revenue rate, multiplier, and crowding-out
  share materially affects the answer. State the parameters when citing.
