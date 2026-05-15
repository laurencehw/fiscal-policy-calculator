---
source: https://www.cbo.gov/publication/57398
title: Capital gains taxation — realizations elasticity, lock-in, step-up at death
source_extras:
  - https://home.treasury.gov/policy-issues/tax-policy/office-of-tax-analysis
  - https://www.nber.org/papers/w19199
title_full: Capital gains taxation — realizations elasticity, lock-in, step-up at death
org: CBO / Treasury OTA / academic literature (synthesized)
year: 2024
keywords: [capital gains, cap gains, realizations, realizations elasticity, lock-in, lock in, step up basis, step-up at death, carryover basis, biden capital gains, qualified dividends, preferential rate, niit, net investment income tax, joulfaian, saez, dowd, mcclelland, holding period, deferral, unrealized, mark to market, accrual taxation, pwbm, jct, eti capital]
---

# Capital gains taxation — the empirics

Capital gains scoring is unusual because the **timing** of realizations
responds sharply to tax rates. A simple "rate × base" calculation
overstates the revenue effect by a factor of two or more for most
proposals. Three empirical facts dominate the conversation.

## 1. Realizations elasticity is time-varying

- **Short-run elasticity** (years 1–3): roughly **0.8** — taxpayers
  rush to realize gains before a rate hike (or defer to after a rate
  cut). Joulfaian–Marples (2024) and earlier work (Dowd, McClelland,
  Muthitacharoen 2015) cluster in this range.
- **Long-run elasticity** (year 4+): roughly **0.4** — permanent
  response after timing effects wash through.
- The app's `CapitalGainsPolicy` uses 0.8 short-run / 0.4 long-run
  with a 3-year transition, matching CBO/JCT methodology.

A +10 percentage-point rate hike with these elasticities reduces
**realizations** by roughly 8% in year 1 and 4% in steady state —
substantially eroding the static revenue gain.

## 2. Step-up basis at death is the biggest preference

Current law: heirs inherit assets at **market value at death**, not the
decedent's original cost. Unrealized gains escape income tax forever.

- **JCT estimate**: step-up basis loses roughly **\$200–\$300 billion**
  in revenue per decade (cited in JCT tax-expenditure tables).
- **Treasury Office of Tax Analysis estimate** (during the Biden
  proposal): elimination of step-up with a \$1M exemption per person
  could raise **\$300–\$500 billion** over 10 years depending on
  exemption design.
- **PWBM analyses** show revenue from step-up elimination is highly
  sensitive to a "lock-in" multiplier: if eliminating step-up causes
  taxpayers to realize during life to avoid the new at-death tax,
  revenue rises faster than the static estimate. PWBM uses a
  multiplier of about **5×** the static gains-at-death number.
- The app's capital gains module supports `eliminate_step_up=True`
  with configurable exemption and lock-in multiplier.

## 3. Preferential rate creates "income shifting" margin

- Top long-term cap-gains rate: **20%** (plus 3.8% NIIT for high
  earners) = **23.8%** combined.
- Top ordinary rate: **37%** (plus 3.8% NIIT for some) = up to **40.8%**.
- The roughly **17-point gap** creates strong incentive to convert
  ordinary income into capital gains — most prominently via
  carried-interest treatment for fund managers.

Equalizing rates on capital gains and ordinary income is one of the
most-studied tax-reform proposals. JCT and Treasury scoring depends
heavily on assumptions about:

- Whether the equalization applies above a threshold (\$400K, \$1M)
  or universally.
- Whether qualified dividends are also lifted.
- Whether step-up is also eliminated (these interact — preserving
  step-up while raising the rate produces very little revenue
  because high-rate gains never get realized).

## What the app reproduces

- **Biden cap-gains rate equalization at \$1M**: app scores **−\$370
  billion** over 10 years; PWBM scored similar proposal at **−\$330B**;
  CBO/JCT range was **−\$300 to −\$500B**.
- **Eliminate step-up at \$1M exemption**: app scores **−\$320 billion**;
  Treasury OTA estimate was **−\$390 billion**. The 18% gap reflects
  the app's lock-in multiplier being conservative.

## How this maps to the app

- `fiscal_model/data/capital_gains.py` — baseline realizations data
  and elasticity model.
- `CapitalGainsPolicy` accepts `short_run_elasticity`,
  `long_run_elasticity`, `transition_years`, plus step-up parameters
  (`eliminate_step_up`, `step_up_exemption`, `step_up_lock_in_multiplier`).
- For a specific cap-gains rate-equalization score, the assistant
  should call `score_hypothetical_policy(policy_type='capital_gains_tax', ...)`
  or fetch one of the calibrated presets via `get_preset`.

## Why the elasticities matter for policy debate

A policy maker who quotes "raising cap gains to ordinary rates raises
\$1 trillion" is typically using a static base × rate calculation.
Once realizations elasticity is applied, the actual number is closer
to **\$300–\$500 billion**. The difference is real revenue, not an
accounting trick — taxpayers genuinely realize less when rates rise.

> Cite Joulfaian/Marples or Dowd-McClelland-Muthitacharoen for
> elasticity ranges; CBO/JCT for official scores; Treasury OTA for
> Biden-era distributional analyses; PWBM for dynamic scoring.
