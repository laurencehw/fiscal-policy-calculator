---
source: https://www.cbo.gov/publication/61116
title: The Budget and Economic Outlook 2026 to 2036 (CBO February 2026)
org: CBO
year: 2026
keywords: [cbo, baseline, projections, deficit, debt, revenues, outlays, gdp, primary deficit, current law, fy2026, fy2035, ten year, 10 year]
---

# CBO February 2026 baseline highlights

This is a hand-curated summary of the CBO's February 2026 Budget and
Economic Outlook, the vintage the app uses by default. Numbers below
match the `CBOBaseline` projections used by the scoring engine when
`vintage = BaselineVintage.CBO_FEB_2026`.

## Headline ten-year picture (FY2026–2035)

- **Cumulative deficits**: roughly **\$21–22 trillion** under current law.
- **Debt held by the public** rises from roughly **100% of GDP** in 2026
  to roughly **122% of GDP** by 2035 — the highest ratio in US history.
- **Revenues**: average about **17.8% of GDP**.
- **Outlays**: average about **24.0% of GDP**.
- **Net interest** approaches **3.4% of GDP** by the end of the window,
  reflecting higher rates and a larger debt stock.

## Economic assumptions (10-year average)

- Real GDP growth: about **1.8%** per year after 2026.
- Inflation (CPI): converging to about **2.0%**.
- Unemployment: holding near **4.4–4.5%**.
- 10-year Treasury rate: about **4.0%**.

## Drivers of rising deficits

The current-law baseline assumes the **TCJA individual provisions expire
at end of 2025**. CBO's "alternative" scenarios in which TCJA is
extended raise cumulative deficits by roughly **\$4.6 trillion** before
interest, or closer to **\$5.5 trillion** with interest.

Three structural drivers push debt higher:
1. **Mandatory spending** (Social Security, Medicare, Medicaid) grows
   faster than GDP because of population aging and per-capita health
   cost growth.
2. **Net interest** rises mechanically with higher rates and higher debt.
3. **Revenues** fail to keep pace, especially if TCJA individual
   provisions are extended.

## How the app uses this baseline

- The scoring engine adds (or subtracts) the policy's `final_deficit_effect`
  to the baseline `deficits` array to produce the post-policy debt path.
- Validation: the app's TCJA Full Extension preset scores at **\$4,582
  billion**, against CBO's **\$4,600 billion** — error **0.4%**.

> **Note on staleness**: CBO publishes major baseline updates twice a year
> (typically January and August). If the user asks about the very latest
> deficit projection, prefer `query_fred` for live federal-debt data and
> use `fetch_url` for the most recent CBO publication.
