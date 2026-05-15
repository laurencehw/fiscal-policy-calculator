---
source: https://www.cbo.gov/publication/60039
title: Tariff scoring — methodology and concrete estimates
org: CBO + USITC + Yale Budget Lab (synthesized)
year: 2025
keywords: [tariff, tariffs, import duties, trade, customs, customs duties, revenue, deadweight loss, consumer cost, retaliation, harmonized tariff schedule, hts, gross revenue, net revenue, pass through, trump tariffs, china tariffs, universal tariff, section 301, section 232, gdp effect]
---

# How tariffs are scored — methodology and numbers

Tariff scoring has three distinct components. Cite all three when the
question is about a specific tariff proposal — quoting only the gross
revenue number is misleading.

## 1. Gross customs revenue

Mechanical: tariff rate × dutiable import base.

- **All US goods imports** (2024 baseline): roughly **\$3.2 trillion** per
  year.
- **Imports from China specifically**: roughly **\$420 billion**.
- A **10% universal tariff** with no behavioral response would mechanically
  raise about **\$320 billion** in year-1 gross revenue.
- A **60% tariff on China** with no behavioral response would mechanically
  raise about **\$250 billion** in year-1 gross revenue.

These are headline numbers — they overstate the *actual* revenue
realized because they assume zero import-demand response.

## 2. Behavioral and macro offsets

Once you net out elasticities, the picture changes:

- **Import demand elasticity**: CBO uses roughly **-1.0** for broad
  tariffs (a 10% price rise reduces import quantity by ~10%). The
  static-revenue formula then collapses by 30-50% versus the gross
  number, depending on which sub-categories carry the highest rate.
- **GDP feedback**: pre-2025 economic literature (Amiti-Redding-
  Weinstein 2019, Cavallo et al. 2021) finds **near-full pass-through**
  of US tariffs to consumer prices. Higher CPI reduces real disposable
  income → consumption falls → GDP falls. Yale Budget Lab estimates
  a **10% universal tariff cuts GDP by roughly 1.0%** in the long run.
- **Revenue feedback**: a 1% GDP drop reduces federal income/payroll
  receipts by roughly **\$280 billion** over 10 years (using the app's
  marginal revenue rate of 0.25 × baseline revenues).
- **Retaliation**: symmetric retaliation by US trading partners cuts
  US exports by an amount comparable to the tariff increase. Yale's
  scoring with retaliation roughly **doubles the GDP drag** versus
  no-retaliation.

## 3. Distributional / consumer cost

The deadweight loss plus the price-effect transfer falls predominantly
on **consumers**, not foreign producers. Yale Budget Lab's central
estimates for recent tariff proposals:

- 10% universal: roughly **\$1,500–\$2,000** per household per year.
- 10% universal + 60% on China: roughly **\$2,500–\$3,500** per household
  per year.
- Effect is **regressive** — bottom-quintile households spend a larger
  share of income on tariff-affected goods.

## Putting it together — a sample net score

For a **10% universal tariff** over 10 years:

- Gross customs revenue: roughly **\$3.0 trillion**.
- After import-demand response: roughly **\$2.2 trillion** net customs.
- After GDP-feedback revenue drag: roughly **\$1.7 trillion** net.
- With symmetric retaliation: roughly **\$1.2–\$1.5 trillion** net.

The headline "revenue" reported in political coverage is usually the
gross number; the true budget-deficit reduction is closer to the
final figure — about **40-50% of gross**.

## How this maps to the app

- The app's `trade.py` module implements all three components for the
  5 calibrated tariff presets (Trump 10% universal, Trump 60% China,
  Biden Section 301, etc.).
- `score/tariff` endpoint exposes this via the REST API with
  `include_consumer_cost` and `include_retaliation` toggles.

> Cite Yale Budget Lab for distributional/household-cost numbers; cite
> CBO/USITC for revenue and macro feedback; cite this app's `trade.py`
> for the integrated net score.
