---
source: https://www.cbo.gov/publication/56522
title: Fiscal multipliers — what we know and how to use them
org: CBO / FRB / academic literature (synthesized)
year: 2024
keywords: [multiplier, fiscal multiplier, spending multiplier, tax multiplier, frb us, romer romer, auerbach gorodnichenko, blanchard perotti, recession multiplier, zero lower bound, zlb, narrative identification, military spending, valerie ramey, transfer multiplier, infrastructure multiplier, output multiplier, cumulative multiplier, peak multiplier]
---

# Fiscal multipliers

A **fiscal multiplier** is the change in GDP produced per dollar of
fiscal stimulus. "The multiplier is 1.5" means \$1 of stimulus raises
GDP by \$1.50 over some horizon. Three things make multiplier
estimates hard:

1. The number depends on the **horizon** (year-1, year-2, cumulative).
2. The number depends on the **policy instrument** (spending vs tax
   cut vs transfer).
3. The number depends on the **macro state** (recession vs expansion,
   ZLB vs not).

## Headline ranges

CBO's working ranges for dynamic-scoring purposes, by instrument:

| Instrument | Year-1 multiplier | Cumulative (3y) |
|---|---|---|
| **Federal purchases** (goods, services) | 0.5 – 2.5 | 0.6 – 2.5 |
| **Transfers to lower-income households** (UI, SNAP, EITC) | 0.4 – 2.1 | 0.5 – 2.1 |
| **Transfers to states** (general aid) | 0.4 – 1.8 | 0.4 – 1.8 |
| **Two-year tax cut for lower-income households** | 0.3 – 1.5 | 0.4 – 1.6 |
| **Two-year tax cut for higher-income households** | 0.1 – 0.6 | 0.1 – 0.6 |
| **Corporate tax rate cut** | 0.0 – 0.4 | 0.0 – 0.4 |
| **Capital-incentive provisions** (expensing) | 0.0 – 0.4 | 0.1 – 0.6 |

Two takeaways:

- **Spending multipliers > tax-cut multipliers** for short-run output.
- Multipliers on **upper-income tax cuts and corporate tax cuts are
  small in the short run** because the recipients have low marginal
  propensities to consume.

## Why the ranges are so wide

Three live debates in the literature:

### 1. Recession vs expansion

**Auerbach & Gorodnichenko (2012, 2013)** find spending multipliers
are roughly **double in recessions** (~2.0) versus expansions (~0.5).

**Ramey & Zubairy (2018)** challenge this — using a longer historical
sample and narrative-identified shocks, they find multipliers near
**1.0 regardless of state**.

The most defensible synthesis: multipliers are state-dependent **at
the zero lower bound** (ZLB), where conventional monetary policy can't
offset fiscal contraction. Above ZLB, multipliers depend on the Fed's
reaction function.

### 2. Identification

The fundamental problem: governments don't randomly assign fiscal
shocks. Three approaches:

- **Blanchard-Perotti (2002)**: VAR identification using
  institutional timing lags in tax collection.
- **Romer-Romer (2010)**: narrative identification of tax shocks
  motivated by long-run goals (not countercyclical).
- **Ramey (2011) military spending**: identifies large defense build-
  ups as exogenous (war, geopolitical shocks).

Narrative methods (Romer-Romer, Ramey) tend to find **smaller**
multipliers (~0.8-1.2) than VAR methods (~1.5-2.0). The methodological
gap remains unresolved.

### 3. Peak vs cumulative

"Multiplier" can mean:

- **Peak multiplier**: max(GDP impact / shock size) over the
  forecast horizon.
- **Cumulative multiplier**: ∫GDP impact / shock size — a
  present-value notion.

Peak is bigger than cumulative for transitory shocks. CBO uses
**cumulative**.

## What the app uses

The app's `FRBUSAdapterLite` uses single fixed multipliers calibrated
to roughly match CBO's central estimates:

- **Spending multiplier**: **1.4** in year 1, decaying by **0.75** per
  year — so 1.05 in year 2, 0.79 in year 3, etc.
- **Tax multiplier**: **-0.7** in year 1, same decay.
- **Crowding out**: **15%** of cumulative deficit reduces the
  multiplier effect through interest-rate / private-investment
  channels.
- **Marginal revenue rate**: **0.25** — translates a GDP change to
  a federal revenue change.

These choices are NOT state-dependent — the app does not currently
distinguish recession from expansion or ZLB from not-ZLB. For policies
where state-dependence matters (a stimulus package targeting a
specific cycle phase), the assistant should flag this and point the
user toward CBO's range-based reporting or PWBM's macro module.

## How to think about a specific number

When you read "the multiplier on this policy is X.X", check:

1. **Horizon**: peak or cumulative? At what year?
2. **Macro state assumed**: recession, expansion, ZLB?
3. **Source of identification**: VAR, narrative, model-based?
4. **What's NOT included**: monetary offset? Open-economy leakage?

A "multiplier of 1.5" without context is closer to a slogan than an
estimate.

> Cite CBO for the published ranges; Auerbach-Gorodnichenko for state-
> dependent estimates; Ramey for the methodological critique; Romer-
> Romer for narrative identification.
