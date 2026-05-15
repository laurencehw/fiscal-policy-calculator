---
source: https://www.imf.org/external/np/seminars/eng/2019/blanchard/
title: Debt sustainability — Blanchard r vs g, fiscal space, and the "is this safe" question
org: Blanchard 2019 AEA + IMF/CBO framings (synthesized)
year: 2025
keywords: [debt sustainability, fiscal sustainability, r vs g, r-g, blanchard, primary deficit, primary balance, fiscal space, debt to gdp, stabilizing primary balance, debt limit, fiscal crisis, interest rate, growth rate, snowball, debt dynamics, secular stagnation, neutral rate, r star, fiscal consolidation]
---

# Debt sustainability — the framework

When someone asks "is this debt path sustainable?", the conventional
answer is the **Blanchard 2019** framing built around the gap between
the interest rate on government debt (**r**) and the GDP growth rate
(**g**).

## The mechanical identity

Annual change in debt-to-GDP:

```
Δ(debt/GDP) = primary_deficit/GDP + (r - g) × (debt/GDP)
```

Two terms:

1. **Primary deficit** — outlays excluding interest minus revenues. A
   policy choice; closing it is what "fiscal consolidation" means.
2. **(r − g) × debt/GDP** — the "snowball." When r > g, debt-to-GDP
   rises mechanically even with a balanced primary budget.

## When r < g

Historically common in advanced economies post-WWII. With r < g:

- A **constant primary deficit** can be sustained indefinitely; debt-
  to-GDP stabilizes at `−primary_deficit/(r-g)`.
- Blanchard's 2019 AEA address argued the welfare cost of public debt
  in an r < g world is **lower than textbook treatments suggest** —
  because debt service shrinks relative to GDP automatically.

For the US, r < g was the operative regime from roughly **2000 to
2022**. CBO's pre-2022 baselines implicitly assumed this would continue.

## When r > g

The picture flips:

- **Stabilizing primary balance** required: `(r-g) × debt/GDP`. With
  US debt/GDP at 100% and (r−g) of +1 pp, the country needs a 1-of-GDP
  primary **surplus** every year just to hold debt steady.
- The current US primary deficit runs about **3–4% of GDP**, so the
  gap to stabilization is 4–5% of GDP per year — a politically vast
  consolidation.

CBO's 2024–2025 baselines move r above g for the first sustained period
in decades, primarily because the 10-year Treasury rate is projected
near **4.0%** while real GDP growth converges to **1.8%** plus 2.0%
inflation — barely 0.2 pp of slack.

## Fiscal space

"Fiscal space" is the residual borrowing capacity before markets
balk at further debt issuance. Empirically:

- No advanced economy has hit a hard ceiling at any specific debt-
  to-GDP ratio. Japan has run debt/GDP near **250%** for two decades.
- What triggers crisis is typically a **rapid loss of confidence** —
  often tied to currency, banking, or political crises — rather than
  a particular debt level.
- "Fiscal space" is therefore best read as **conditional on credibility**:
  a country with a credible long-run fiscal plan has more space than
  one without, at the same debt level.

## How this maps to the app

- The app reports `debt_held_by_public` and `nominal_gdp` per year,
  so debt/GDP paths under any scored policy are computable.
- The app's `EconomicModel` uses a **15% crowding-out coefficient**
  on cumulative deficits — implicitly assuming a modest r-response to
  debt issuance.
- The app does NOT directly model the snowball / r-g dynamic in the
  10-year baseline window (rates are taken as exogenous from CBO).
  For r-g sensitivity analysis, prefer CBO's **long-term outlook** or
  PWBM's debt-sensitivity scenarios.

## Why this matters for reading scores

A 10-year deficit number doesn't capture sustainability — it tells
you the *direct* effect of a policy. To assess sustainability impact
you need:

1. Permanent (post-window) revenue/spending shift implied by the
   policy.
2. Effect on the primary-balance/GDP ratio.
3. r-g assumption.

> Cite Blanchard (2019) for the r-g framing; cite CBO long-term
> outlook for US-specific r-g and stabilizing-balance numbers; cite
> Reinhart & Rogoff or IMF World Economic Outlook for cross-country
> evidence on debt levels and crises.
