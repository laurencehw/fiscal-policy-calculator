---
source: https://www.cbo.gov/publication/61116
title: The Budget and Economic Outlook 2025 to 2035 (CBO February 2026 update)
org: CBO
year: 2026
keywords: [cbo, baseline, projections, deficit, debt, revenues, outlays, gdp, primary deficit, current law, fy2025, fy2034, ten year, 10 year, debt to gdp]
---

# CBO February 2026 baseline — highlights as loaded by this app

This is a hand-curated summary of the CBO February 2026 baseline as it
appears in the app's `BaselineProjection`. **Numbers below are the
ones the scoring engine actually uses** — when the assistant cites the
baseline it should call `get_cbo_baseline` rather than relying on this
file for the exact figures, but the narrative shape here matches.

## Headline ten-year picture (FY2025–2034 window)

- **Cumulative deficits**: roughly **\$28.7 trillion** under current law.
- **Annual deficits** rise from about **\$2.5 trillion** in FY2025 to
  about **\$3.4 trillion** by FY2034.
- **Debt held by the public** climbs from roughly **98% of GDP** in 2025
  to roughly **103% of GDP** by 2034 — and continues rising in the
  long-term outlook.
- **Revenues**: average about **15.4% of GDP** over the window.
- **Outlays**: average about **22.6% of GDP**.
- **Annual deficit-to-GDP** runs around **7%** throughout, well above
  the post-WWII average of about 3%.

## Economic assumptions (10-year average)

- Real GDP growth: about **1.8%** per year.
- Inflation (CPI): converging to about **2.0%**.
- Unemployment: holding near **4.4–4.5%**.
- 10-year Treasury rate: about **4.0%**.

## Drivers of rising deficits

The current-law baseline assumes the **TCJA individual provisions expire
at end of 2025**. CBO's "alternative" scenarios in which TCJA is
extended raise cumulative deficits by roughly **\$4.6 trillion** before
interest (closer to \$5.5T with interest service).

Three structural drivers push debt higher:
1. **Mandatory spending** (Social Security, Medicare, Medicaid) grows
   faster than GDP because of population aging and per-capita health
   cost growth.
2. **Net interest** rises mechanically with higher rates and higher
   debt.
3. **Revenues** fail to keep pace, especially if TCJA individual
   provisions are extended.

## How the app uses this baseline

- The scoring engine adds (or subtracts) a policy's `final_deficit_effect`
  to the baseline `deficits` array to produce the post-policy debt path.
- Validation: the app's TCJA Full Extension preset scores at **\$4,582
  billion**, against CBO's **\$4,600 billion** — error **0.4%**.

> **Authoritative figures**: For an exact debt-to-GDP path year by year,
> the assistant should call `get_cbo_baseline` — that tool returns the
> arrays the scoring engine actually uses. The percentages above are
> averages and end-of-window snapshots rounded for prose use.

> **Staleness**: CBO publishes major baseline updates twice a year
> (typically January and August). The app's baseline is tagged
> `cbo_feb_2026`. For the very latest CBO projection, the assistant
> should use `web_search` against `cbo.gov` or `fetch_url` for the
> current Budget and Economic Outlook publication.
