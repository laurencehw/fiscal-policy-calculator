---
source: https://budgetmodel.wharton.upenn.edu/issues/2024/5/13/budgetary-economic-effects-extending-tcja
title: Penn Wharton Budget Model — Dynamic effects of TCJA extension
org: Penn Wharton Budget Model
year: 2024
keywords: [pwbm, penn wharton, budget model, tcja, extension, dynamic scoring, olg, overlapping generations, gdp effect, capital stock, labor supply, revenue feedback, debt feedback, crowding out, dynamic cost, conventional cost]
---

# Penn Wharton on TCJA extension — dynamic scoring

PWBM publishes dynamic scores of major fiscal proposals using a multi-
agent overlapping-generations (OLG) general-equilibrium model. For
TCJA extension, PWBM's analyses share three features that should be
flagged when citing them:

## Headline pattern

- **Conventional cost** roughly aligns with CBO: extending TCJA's
  expiring individual provisions adds **\$4–5 trillion** to deficits
  over 10 years.
- **Dynamic GDP effects are modest and decay**: PWBM typically finds a
  small short-run GDP boost (under **+1%** by year 10), but the
  long-run effect can be **negative** because higher debt crowds out
  private capital.
- **Dynamic cost can be higher than conventional**: when debt-feedback
  is included, the 10-year cost frequently *rises* by **5–15%** above
  the conventional score — the opposite direction from purely supply-
  side ("Laffer") thinking.

## Why PWBM differs from CBO

- **Open-economy vs closed-economy**: PWBM's open-economy assumption
  allows foreign capital inflows to partially offset crowding out,
  damping the negative dynamic effect.
- **Longer horizon**: PWBM reports 30+ year paths; CBO truncates at 10.
- **Behavioral richness**: PWBM models savings and labor responses by
  age cohort and skill group; CBO's macro-feedback is more aggregate.

## Headline numbers worth tracking

- Long-run GDP impact of TCJA extension: PWBM typically reports
  **−0.4% to +0.3%** in year 30 depending on financing assumption.
- Capital stock: small positive in years 1–10, frequently turns negative
  in later years.
- Hours worked: small positive throughout (the labor-supply channel
  dominates the capital-channel direction).

## How this maps to the app

- The app's `FRBUSAdapterLite` produces dynamic effects in roughly the
  same direction as PWBM's near-term numbers (small positive GDP), but
  the app doesn't yet implement PWBM's deeper OLG channels.
- The app's OLG implementation (`fiscal_model/models/olg/`) is used
  primarily for Social Security/Medicare generational analysis, not for
  general tax-policy dynamic scoring.

> Cite PWBM when the question is specifically about long-run dynamic
> effects, generational incidence, or whether a tax cut "pays for
> itself" through growth. PWBM is among the strongest sources for the
> "no, mostly not" answer.
