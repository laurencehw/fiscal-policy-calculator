---
source: https://www.ssa.gov/oact/TRSUM/
title: 2025 OASDI Trustees Report — Summary
org: SSA
year: 2025
keywords: [social security, ssa, trustees, trust fund, depletion, insolvency, oasi, di, oasdi, medicare, hi, fica, payroll, solvency, 75 year, actuarial balance]
---

# 2025 Social Security Trustees Report — key findings

This snapshot summarizes the 2025 OASDI Trustees Report (the most recent
at the time of writing). Confirm the latest year via `fetch_url` to
`https://www.ssa.gov/oact/TRSUM/` before citing as current.

## Trust fund depletion dates (intermediate assumptions)

- **OASI (Old-Age and Survivors Insurance)**: trust fund reserves are
  projected to be depleted in **2033**. After depletion, continuing
  payroll-tax receipts would cover roughly **77%** of scheduled benefits.
- **DI (Disability Insurance)**: solvent throughout the 75-year horizon
  under intermediate assumptions.
- **Combined OASDI**: depletion projected in **2034** (theoretical;
  the trust funds are legally separate).
- **HI (Medicare Hospital Insurance)**: depletion projected in **2036**,
  three years later than the prior year's report — improvement driven
  by stronger payroll-tax receipts and slower spending growth.

## Long-run actuarial balance

- **75-year OASDI actuarial deficit**: roughly **3.5% of taxable payroll**
  (equivalent to about **1.2% of GDP**).
- Closing the gap immediately would require either a permanent payroll-
  tax rate increase of about **3.5 percentage points**, a benefit cut of
  about **22%**, or some combination.

## What changed vs. the prior report

- Slight improvement on the OASDI side, primarily from a stronger near-
  term economy and higher covered earnings.
- HI improvement is the larger story: cost growth slower than projected,
  primarily in inpatient hospital spending.

## Policy levers commonly modeled

The app's preset library includes several Social Security solvency
options that close part of the actuarial gap:

- **Lift the payroll tax cap to 90% coverage** (`ss_cap_90_percent`):
  closes roughly half the gap.
- **Donut hole at \$250K** (`ss_donut_hole`): apply the 12.4% payroll
  tax to earnings above \$250K, scored by CBO at **−\$2.7T** (model:
  **−\$2.4T**, error 12%).
- **Eliminate the cap entirely** (`ss_eliminate_cap`): closes most of
  the gap; raises top marginal rates substantially.

## Caveats

- The intermediate projections embed assumptions about fertility,
  mortality, immigration, and productivity. The Trustees' "high cost"
  scenario brings depletion forward by 2–3 years.
- Depletion is **not bankruptcy**: payroll taxes continue. The legal
  default after depletion is automatic benefit cuts to match incoming
  revenue, which is what the "77%" figure refers to.
