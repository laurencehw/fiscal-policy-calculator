---
source: https://www.cbo.gov/topics/budget/long-term-budget-projections
title: CBO — The Long-Term Budget Outlook
org: CBO
year: 2025
keywords: [cbo, long term, outlook, 30 year, 75 year, debt sustainability, primary deficit, fiscal gap, aging, demographics, medicare, social security, interest, debt held by public, sustainability gap]
---

# CBO Long-Term Budget Outlook

The CBO Long-Term Budget Outlook extends the 10-year baseline out
30 years (and in some scenarios 75 years). It is the canonical source
for debt-sustainability questions.

## Headline pattern under current law

- **Debt held by the public** rises to roughly **165–180% of GDP**
  by 2054 — an unprecedented level.
- **Net interest** grows to roughly **6% of GDP** by 2054 — comparable
  to total non-interest discretionary spending today.
- **Primary deficit** (deficit excluding interest) stays in the
  **2–3% of GDP** range — meaning rising debt is driven mostly by
  growing interest payments on existing debt, not new structural
  spending.
- **Revenues** grow modestly under current law (TCJA expiry plus
  bracket creep), to about **18.5% of GDP** by 2054.
- **Mandatory spending** (Social Security, Medicare, Medicaid) grows
  from about 14% of GDP to about 16% of GDP, driven primarily by
  aging and per-capita health-cost growth.

## The "fiscal gap" framing

CBO and academic analysts (Auerbach, Gale, et al.) often summarize the
imbalance as a **fiscal gap** — the immediate and permanent change in
primary balance needed to stabilize debt-to-GDP at its current level
over 75 years.

- 75-year fiscal gap: roughly **3–5% of GDP**, depending on which
  Social Security and Medicare scenarios are bundled in.
- That is approximately **\$1 trillion per year** at current GDP.
- Closing it requires some combination of tax increases, benefit
  changes, or growth — none of which alone are politically painless.

## Key uncertainty bands

CBO publishes high/low scenarios around three key variables:

- **Productivity growth**: ±0.5 pp can move 2054 debt-to-GDP by 20+ pp.
- **Interest rates**: ±100 bp can move 2054 debt-to-GDP by 30+ pp.
- **Mortality**: lower mortality raises SS/Medicare cost; higher raises
  revenue but reduces benefit outlays differentially.

## What the app can and can't say about long-run

- The app's `BaselineProjection` is **10 years**. The `OLG` model
  (`fiscal_model/models/olg/`) and `SolowGrowthModel`
  (`fiscal_model/long_run/`) extend reasoning past the 10-year window
  for specific policies, but they are not a substitute for the CBO
  long-term framework.
- The app does report `revenue_feedback_10yr` from dynamic scoring
  but does not produce a 30-year fiscal gap number.

> Cite the CBO Long-Term Outlook when the question is about debt
> sustainability, the fiscal gap, or scenarios beyond 10 years.
