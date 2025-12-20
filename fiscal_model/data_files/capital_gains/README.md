# Capital Gains Baseline Data

This directory contains data and metadata used to auto-populate the capital gains realizations base used by `CapitalGainsPolicy`.

## Files

- `irs_22in01pl.xls`
  - IRS Statistics of Income (SOI) **preliminary** Table 1 for **Tax Year 2022**:
    “Individual Income Tax Returns, Preliminary Data for Tax Years 2021 and 2022: Selected Income and Tax Items, by Size of Adjusted Gross Income”.
  - Download source: `https://www.irs.gov/pub/irs-soi/22in01pl.xls`
  - We use the **Tax Year 2022** “Net capital gain” **Amount** row (money amounts are in **thousands of dollars**) by AGI size.

- `taxfoundation_capital_gains_2022_2024.csv`
  - Tax Foundation aggregate series for **Total realized capital gains**, **Taxes paid on capital gains**, and **Average effective tax rate**.
  - Source page: [`https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/`](https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/)
  - Used to scale 2022-by-AGI shares to approximate 2023/2024 totals when IRS-by-AGI data are not yet published.

## Important caveats (read this)

- IRS-by-AGI capital gains data for **Tax Years 2023/2024** may not be publicly available yet.
- For 2023/2024, the model currently **assumes the AGI distribution of net capital gains matches 2022** and scales totals using the Tax Foundation aggregate realized gains series.
- This should be treated as an **estimate** until IRS-by-AGI capital gains tables for 2023/2024 are available.

## Baseline rate (τ₀) options

Because the IRS preliminary Table 1 provides **net capital gain** by AGI bracket but does **not** provide “tax on capital gains” by AGI, we support two τ₀ approaches:

1. **Statutory/NIIT proxy (by AGI bracket)** *(default)*:
   - Uses IRS net capital gains by AGI bracket and applies a transparent rate mapping (LTCG rate bands + NIIT threshold) to compute a weighted τ₀ above a threshold.
   - Intended as a *transparent proxy*; ignores filing status and short-term gains composition.

2. **Tax Foundation average effective rate (aggregate)**:
   - Uses the year-level average effective capital gains tax rate from Tax Foundation (not by AGI).
   - Source: [`https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/`](https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/)


