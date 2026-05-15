---
source: https://www.cbo.gov/topics/health-care
title: Medicare and Medicaid — long-run drivers
org: CBO / CMS Office of the Actuary (synthesized)
year: 2025
keywords: [medicare, medicaid, healthcare, health care, mandatory spending, hi trust fund, hospital insurance, supplementary medical insurance, smi, part a, part b, part c, part d, advantage, dual eligible, aging, demographics, excess cost growth, per capita health spending, cms, actuary, gdp share, long term outlook]
---

# Medicare and Medicaid — the long-run debt drivers

Federal health spending — primarily Medicare and Medicaid — is the
**single largest source** of projected debt growth in the CBO long-term
outlook. Understanding why matters for any fiscal-reform conversation.

## Headline numbers

- **Medicare** total federal cost: roughly **\$1.0 trillion** in FY2024
  (~3.5% of GDP). Projected to rise to **5–6% of GDP** by 2055.
- **Medicaid** federal cost: roughly **\$0.6 trillion** in FY2024
  (~2.2% of GDP). Projected to rise to **3–3.5% of GDP** by 2055.
- **Combined federal health** spending (Medicare + Medicaid + CHIP +
  ACA subsidies): roughly **6.5% of GDP** in FY2024; projected to
  cross **9% of GDP** by mid-2050s.

## Why it grows faster than GDP

Two drivers, in roughly equal magnitude:

1. **Demographics (aging).** The over-65 share of the population is
   projected to rise from about 17% in 2024 to **23%** by 2055.
   Medicare per-capita cost is roughly 3× the working-age average,
   so a larger 65+ share mechanically grows the program.
2. **Excess cost growth (ECG).** Per-capita health spending has
   historically grown about **1.0–1.5 percentage points faster** than
   per-capita GDP. ECG has slowed substantially since the early 2010s
   (the "great slowdown") but CBO assumes a non-zero spread continues.

CBO's long-term projections are highly sensitive to ECG assumptions:
a +0.5 pp ECG raises 2055 federal health spending by roughly **2% of
GDP** — comparable to the entire defense budget.

## Trust fund vs general fund

- **Medicare Part A** (Hospital Insurance) is financed by the **HI
  payroll tax** and has a **trust fund**. 2025 Trustees: depletion in
  **2036**, three years later than the prior report (improvement from
  slower spending growth). Post-depletion, HI revenues cover ~89% of
  scheduled benefits absent legislation.
- **Medicare Parts B (physician), D (drugs), and Advantage** are
  funded primarily by **general revenues** + beneficiary premiums.
  No trust-fund constraint; these expand with no automatic forcing
  mechanism.
- **Medicaid** has no trust fund — it is a federal-state matched
  general-revenue program (federal share averages ~64%, higher in
  poorer states via the FMAP formula).

## Policy levers commonly modeled

- **Drug price negotiation (IRA expansion)** — CBO scored the 2022
  IRA negotiations at roughly **\$160 billion** in Medicare savings
  over 10 years. Broader negotiation could roughly double this.
- **Medicare eligibility age** raised to 67 (matching Social
  Security) — saves roughly **\$70–100 billion** over 10 years per CBO,
  but shifts costs to other payers and is regressive.
- **Premium support / vouchers** — restructures Medicare as a
  defined-contribution program; scoring varies dramatically by design.
- **Medicaid block grants / per-capita caps** — federal savings come
  from shifting risk to states; net national health spending often
  rises modestly because states compensate with provider cuts.

## How this maps to the app

- The app's `MedicareReformPolicy` (in fiscal_model/) handles
  eligibility-age and premium changes.
- For Medicare price-negotiation scoring, see the app's `pharma.py`
  module — calibrated to CBO IRA estimates.
- Generational distribution of Medicare reforms is computable via
  the OLG model (`fiscal_model/models/olg/`).

> Cite this file for the qualitative drivers and rough magnitudes;
> for exact CBO scores on a specific Medicare proposal, prefer
> `web_search` against `cbo.gov` or `get_validation_scorecard` for
> the app's calibrated estimate.
