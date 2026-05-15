---
source: https://www.jct.gov/publications/2023/jcx-12r-23/
title: JCT distributional methodology — what makes it different from TPC and CBO
org: Joint Committee on Taxation
year: 2023
keywords: [jct, distributional, methodology, income measure, jct income, expanded income, agi, eci, expanded cash income, decile, quintile, agi class, tax incidence, corporate incidence, capital owners, labor share, employer payroll, employer health, family economic income, fei, microsimulation, joint committee, taxation]
---

# JCT distributional methodology

Three institutions publish the canonical distributional tables for US
tax policy: **JCT**, **TPC**, and **CBO**. They produce comparable but
**not identical** numbers — because they use different income measures
and incidence assumptions. Reconciling them is one of the most common
questions a policy analyst asks.

## Income measure

| Institution | Measure | Notable inclusions |
|---|---|---|
| **JCT** | "Expanded Income" (also "JCT income") | AGI + non-AGI items (employer-side payroll tax, employer health insurance value, tax-exempt interest, unrealized gains via accrual for some analyses) |
| **TPC** | "Expanded Cash Income" (ECI) | AGI + similar adjustments to JCT, with somewhat different treatment of imputed rent |
| **CBO** | "Comprehensive Income" | All cash income + government transfers + employer-side benefits + capital gains on a realization basis |

The biggest practical consequence: **CBO's measure includes transfers**
(SNAP, Medicaid value, etc.), which lifts the bottom-quintile average
income substantially. JCT and TPC exclude most transfers.

## Decile/quintile vs. AGI-class

- **JCT** typically reports by **AGI class** (e.g., \$50K–\$75K), not
  decile. This makes year-over-year comparisons hard because nominal
  AGI brackets aren't comparable across years.
- **TPC** and **CBO** report by **decile/quintile** of their respective
  income measure. Comparable over time but requires knowing the
  threshold each year.

When comparing a JCT table to a TPC table for the same policy, look
for which institution reports the **top 1%** consistently — that's the
most stable cross-walk.

## Tax-incidence assumptions

The hardest reconciling question. Where does each tax burden land?

| Tax | JCT default | TPC default | CBO default |
|---|---|---|---|
| Individual income | 100% on payer | 100% on payer | 100% on payer |
| Employer payroll | 100% on **worker** | 100% on **worker** | 100% on **worker** |
| Corporate income | 25% labor / 75% capital (since 2013) | 20% labor / 80% capital | 25% labor / 75% capital |
| Estate | 100% on **decedent's heirs** | Same | Same |
| Excise | 100% on **consumer** | Same | Same |

The **corporate incidence split is the most consequential** for
distributional differences across these institutions. A change in the
labor share (from 25% → 50%) would flatten the apparent distributional
impact of corporate tax changes by spreading more of the burden to
mid-decile wage earners.

## Time horizon

- JCT reports **calendar-year snapshots** (typically year 1 + a "fully
  phased-in" year). Not a 10-year cumulative table.
- TPC reports calendar-year, often with multiple horizon scenarios.
- CBO reports **calendar-year averages over the budget window**.

A "TCJA distributional impact" reported by JCT in 2019 is **not
directly comparable** to a CBO 2019–2028 average — JCT's number is for
that specific year; CBO's averages across phase-in.

## How this maps to the app

- The app's `DistributionalEngine` uses **CBO-style decile/quintile**
  output by default, with TPC-style AGI-bracket as a secondary option.
- Corporate incidence in the app: configurable; default matches CBO's
  25/75 split.
- Validation: the app's distributional benchmarks are calibrated
  against both JCT and CBO tables (see `get_validation_scorecard` with
  filter "distribution").

> When a user asks "why doesn't this match JCT's table?", check
> (1) income measure, (2) decile vs AGI class, (3) corporate
> incidence assumption, (4) time horizon. One of these explains
> almost every observed discrepancy.
