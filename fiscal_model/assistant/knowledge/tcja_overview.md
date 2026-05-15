---
source: https://www.cbo.gov/publication/59710
title: Budgetary Effects of Extending Provisions of the 2017 Tax Act (CBO May 2024)
org: CBO
year: 2024
keywords: [tcja, tax cuts and jobs act, 2017, extension, sunset, brackets, salt, qbi, child tax credit, ctc, individual amt, estate, pass through, 199a, jct, distributional]
---

# Tax Cuts and Jobs Act (TCJA) — extension overview

## What TCJA did

Enacted December 2017. Major individual-side changes (almost all
sunsetting end of 2025) and a permanent corporate cut:

- Permanent: **corporate rate 35% → 21%**; expensing of short-life
  capital; international regime (GILTI, FDII, BEAT).
- Sunsetting end of 2025: lower individual marginal rates and wider
  brackets; **\$10K SALT cap**; near-doubled standard deduction; elimination
  of personal exemptions; doubled CTC (\$1,000 → \$2,000); doubled estate
  exemption; the **20% Section 199A QBI deduction** for pass-through income;
  individual AMT exemption increase.

## Cost of full extension

- **CBO May 2024**: 10-year cost of extending the expiring individual
  provisions in current form is **\$4.6 trillion** (2025–2034 window).
- **JCT, slightly later**: similar range.
- This app's TCJA module reproduces \$4.6T within **0.4%**.

Adding SALT cap repeal on top of extension adds roughly **\$1.9 trillion**
(JCT 2024).

## Distributional impact (CBO and JCT)

- CBO (TCJA 2018 deciles): tax change as a share of after-tax income is
  larger in higher deciles. The top 1% gain roughly **3%**; the bottom
  quintile gains under **0.5%**.
- JCT (TCJA 2019 by AGI class): same shape; broad-based but skewed up the
  scale.
- Extension preserves this shape; SALT cap repeal further raises the top
  decile gain.

## Dynamic effects

- Wharton, CBO, and JCT have published dynamic scores. They find positive
  but modest GDP effects: roughly **+0.3% to +1.0%** by year 10. Revenue
  feedback offsets **5–15%** of the static cost.
- The app's `FRBUSAdapterLite` applied to TCJA extension produces effects
  in this range.

## Why this matters for the baseline

The CBO current-law baseline assumes the individual provisions expire on
schedule. Comparing two paths:

- Current law (sunset): debt rises to roughly **122% of GDP** by 2035.
- Full extension + SALT cap repeal: roughly **132% of GDP** by 2035.

> Use the app's TCJA presets ("TCJA Full Extension", "TCJA Extension (No
> SALT Cap)", "TCJA Rates Only") to score each variant on this app's
> calibrated baseline; cross-reference the score against CBO/JCT via
> `get_validation_scorecard`.
