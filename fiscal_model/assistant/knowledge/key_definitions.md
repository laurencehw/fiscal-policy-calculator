---
source: https://www.cbo.gov/about/products/budget-economic-data
title: Key public-finance definitions used in this app
org: app authors (synthesized from CBO and Treasury usage)
year: 2026
keywords: [definitions, glossary, eti, elasticity, dynamic scoring, static scoring, conventional, baseline, primary deficit, primary balance, fiscal gap, debt held by public, gross debt, olg, frb us, multipliers, marginal rate, effective rate, deficit, deficit financing, tax expenditure, salt, gilti, fdii, niit, amt, ctc, eitc, tcja]
---

# Key definitions

This file is the model's quick reference for terms it should define on
first use. Numbers and conventions match the app's scoring engine and
docs/METHODOLOGY.md.

## Scoring conventions

- **Static (conventional) scoring**: applies only mechanical effects of
  a policy change — for a tax cut, `ΔRevenue = ΔRate × Base × Filers`.
  No behavioral or macro feedback.
- **Behavioral offset (ETI)**: adjusts the static effect for taxpayers'
  reported-income response to a rate change. The app uses an elasticity
  of taxable income (ETI) of **0.25** (Saez, Slemrod, Giertz 2012),
  applied as `Final = Static × (1 − ETI × 0.5)`.
- **Dynamic scoring**: adds macro feedback — GDP and employment respond
  to fiscal stance, generating revenue feedback. The app's
  `FRBUSAdapterLite` uses FRB/US-calibrated multipliers: spending **1.4**
  (year 1, 0.75 decay), tax **-0.7**, with **15%** crowding-out on
  cumulative deficit.
- **Marginal revenue rate (for dynamic feedback)**: **0.25** — used to
  translate a GDP change into a revenue change.

## Elasticities

- **ETI** (elasticity of taxable income, all individuals): **0.25**.
- **Capital gains elasticity** (time-varying): short-run **0.8** (years
  1–3, timing effects), long-run **0.4** (permanent response), transition
  over **3** years (CBO/JCT methodology).
- **Corporate behavioral elasticity**: default **0.25** in the
  `CorporateTaxPolicy` class.
- **Labor supply elasticity**: **0.1** (default in `TaxPolicy`).

## Budget definitions

- **Deficit**: outlays minus revenues in a given year (positive = deficit).
- **Primary deficit**: deficit excluding net interest. Useful because
  net interest reflects past debt and current rates rather than current
  policy.
- **Debt held by the public**: federal debt held outside government
  accounts (intragovernmental holdings excluded). The standard solvency
  measure.
- **Debt-to-GDP**: debt held by public divided by nominal GDP. Conventional
  ratio for cross-country comparisons.
- **Fiscal gap**: present-value imbalance between projected primary
  surpluses and the change in debt over a horizon (typically 75 years).

## Tax-system terms

- **Tax expenditure**: revenue lost from a deduction, exclusion, credit,
  or preferential rate relative to a "normal" baseline. JCT publishes
  annual estimates.
- **SALT cap**: State and Local Tax deduction cap of \$10K enacted in
  TCJA; repeal scored at roughly +\$1.9T over 10 years (in addition to
  TCJA extension).
- **GILTI**: Global Intangible Low-Taxed Income — tax on foreign-source
  earnings of US multinationals.
- **FDII**: Foreign-Derived Intangible Income — preferential rate on
  US export-related intangible income.
- **NIIT**: Net Investment Income Tax — 3.8% on investment income for
  high earners (enacted as part of the ACA).
- **AMT**: Alternative Minimum Tax. Individual AMT was largely
  neutralized by TCJA; Corporate AMT (CAMT) was introduced by the IRA.
- **CTC / EITC**: Child Tax Credit / Earned Income Tax Credit.

## TCJA reference points

- TCJA Full Extension scored by CBO (May 2024) at **\$4,600 billion**
  over 10 years. The app's TCJA module reproduces this within **0.4%**.
- Repeal of the SALT cap adds **\$1.9 trillion** beyond TCJA extension
  (JCT 2024).
- Individual TCJA provisions sunset at end of 2025; corporate provisions
  (e.g., 21% rate) are permanent.

## OLG and long-run

- **OLG**: Overlapping Generations model — captures how a policy affects
  different birth cohorts' lifetime tax burdens and consumption.
- The app's OLG model (in `fiscal_model/models/olg/`) is a 30-period
  Auerbach–Kotlikoff model used primarily for Social Security and
  Medicare reform.

> Cite this file as the definitions source only when the user explicitly
> asks for terminology; for substantive numerical claims, prefer the
> primary source.
