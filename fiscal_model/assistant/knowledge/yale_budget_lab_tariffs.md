---
source: https://budgetlab.yale.edu/research
title: Yale Budget Lab — Tariff impact analyses
org: Yale Budget Lab
year: 2025
keywords: [yale budget lab, tariffs, tariff, trade, import duties, consumer prices, regressive, deadweight loss, gdp effect, household cost, effective tariff rate, china tariffs, broad based tariff, retaliation]
---

# Yale Budget Lab on tariffs

The Yale Budget Lab publishes some of the most cited microsimulation-
based tariff impact analyses, including for the 2024–2025 tariff
proposals. Their distinctive methodological choice is to combine
**microsimulation of consumer-price pass-through** with **macro
feedback** (GDP, jobs) in a single integrated estimate.

## Headline patterns from Yale's tariff analyses

- **Average household cost** (broad-based tariffs): typically reported
  in **\$1,500–\$3,500 per household per year** range depending on the
  tariff scenario, with bigger numbers for higher rates and more
  comprehensive coverage.
- **Regressivity**: tariffs are sharply regressive — bottom-quintile
  households lose a larger share of after-tax income than top-quintile
  households, because lower-income households spend a larger share of
  income on tariffed goods.
- **GDP effect**: tariffs reduce GDP through three channels:
  (1) higher consumer prices reduce real income;
  (2) input tariffs raise production costs for downstream industries;
  (3) retaliation shrinks exports.
- **Revenue**: tariff revenue is real but partially offset by reduced
  income/payroll tax receipts as GDP falls — net revenue typically
  comes in **below** the gross customs-duty number.

## Methodological notes worth flagging

- **Pass-through**: Yale assumes roughly full pass-through to consumer
  prices in the long run; pre-2025 academic literature supports this
  (Amiti, Redding, Weinstein 2019; Cavallo et al. 2021). Short-run
  pass-through is lower.
- **Retaliation**: Yale models a "symmetric retaliation" baseline (other
  countries match U.S. tariffs on U.S. exports). Without retaliation,
  GDP effects are about a third smaller.
- **Substitution**: Consumers shift toward non-tariffed goods over
  time, which dampens long-run cost — but raises effective domestic
  prices through demand reallocation.

## How this maps to the app

- The app has a `trade.py` tariff scoring module with 5 calibrated
  presets and the same conceptual channels (revenue, consumer price
  impact, GDP effect).
- For a specific Yale Budget Lab tariff number on a specific scenario
  ("Trump 10% universal + 60% on China"), the assistant should
  `web_search` `budgetlab.yale.edu` or `fetch_url` the specific
  publication.

> Cite Yale Budget Lab when the question is about tariffs and the
> reader wants household-level distributional detail. For revenue-only
> tariff scores, the app's own engine is fine; for macro feedback, Yale
> is the strongest non-government source.
