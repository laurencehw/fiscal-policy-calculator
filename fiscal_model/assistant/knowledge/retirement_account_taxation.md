---
source: https://www.jct.gov/publications/2024/jcx-48-24/
title: Retirement account tax treatment — 401(k), IRA, Roth, SEP
org: JCT / Treasury / CBO (synthesized)
year: 2024
keywords: [retirement, 401k, ira, roth, sep, simple ira, secure act, secure 2.0, traditional, deductible, contribution limit, rmd, required minimum distribution, employer match, vesting, pension, defined benefit, defined contribution, dc plan, db plan, taxes deferred, exclusion, deferred, joulfaian, retirement tax expenditure, eet, ttt, ete, mega backdoor roth, backdoor roth, megabackdoor]
---

# Retirement account taxation

Retirement-account tax preferences are the **third-largest tax
expenditure** in the federal code (after the employer-health exclusion
and the capital-gains preferential rate). They cost the Treasury more
than the mortgage interest deduction and the charitable deduction
combined.

## The four major account types

| Account | Contribution treatment | Earnings | Withdrawal | Limit (2024) |
|---|---|---|---|---|
| Traditional 401(k) | **Deductible** | Tax-deferred | **Taxable** | \$23,000 (\$30,500 if 50+) |
| Roth 401(k) | After-tax | Tax-free | **Tax-free** | \$23,000 (\$30,500 if 50+) |
| Traditional IRA | Deductible (with income phase-out) | Tax-deferred | **Taxable** | \$7,000 (\$8,000 if 50+) |
| Roth IRA | After-tax (with income phase-out) | Tax-free | **Tax-free** | \$7,000 (\$8,000 if 50+) |

Plus: **SEP-IRA** and **Solo 401(k)** for self-employed (limits up to
~\$70K total); **SIMPLE IRA** for small employers (lower limits); and
**Defined Benefit plans** (pensions, largely employer-funded).

## The tax-expenditure framing

JCT classifies retirement preferences as a tax expenditure under the
"normal" income-tax baseline (which would tax earnings annually).
The deferral structure is "EET":

- **E**xempt contributions (deductible going in)
- **E**xempt earnings (no annual tax on returns)
- **T**axable withdrawals (ordinary income at retirement)

The **present-value** revenue loss to Treasury is roughly **40–60%**
of the contribution amount, depending on the gap between current
marginal rate and retirement marginal rate.

**JCT 5-year estimates (2024–2028)**:

- Employer DC plans (401(k), etc.): roughly **\$1.3 trillion**.
- Employer DB pensions: roughly **\$0.4 trillion**.
- Self-employed IRA/SEP: roughly **\$0.2 trillion**.
- **Combined**: roughly **\$1.9 trillion** over 5 years.

That makes retirement-account preferences the largest *deferral*-based
tax expenditure (the employer-health exclusion is larger but is an
exclusion, not a deferral).

## Who benefits — distribution

The retirement tax preference is **strongly tilted to high earners**:

- Top quintile gets roughly **65–70%** of the dollar benefit.
- Top 1% gets roughly **15–20%** of the dollar benefit.
- Bottom two quintiles get under **3%** combined.

Two mechanisms drive the skew:
1. **Higher contribution amounts**: limits are flat in dollars but
   high earners can fill them; lower earners cannot.
2. **Higher marginal rate**: a \$1 deduction is worth 37 cents to a
   top-bracket filer, ~12 cents to a low earner.

Roth treatment is somewhat less skewed (no immediate deduction value),
but most contributions are still traditional.

## SECURE / SECURE 2.0 expansions

- **SECURE Act (2019)**: raised RMD age from 70.5 to 72, mandated
  multi-employer 401(k) options.
- **SECURE 2.0 (2022)**:
  - RMD age to **73** (2023), eventually **75** (2033).
  - Catch-up contributions for ages 60-63 raised to **\$11,250**.
  - Mandatory auto-enrollment for new 401(k) plans.
  - SIMPLE IRA limit increases.
  - **Cost**: scored at roughly **\$50 billion** over 10 years.

## Reform options commonly modeled

- **Cap total tax preference** (lifetime cap, "mega-Roth ceiling"):
  Wyden 2021 proposal capped at \$10M aggregate; scored at
  **\$0.05–0.10 trillion** over 10 years depending on cap.
- **Eliminate "backdoor Roth"** loophole: closes a high-income
  conversion strategy; modest revenue.
- **Lower contribution limits**: each \$1,000 reduction in 401(k) limit
  scores at roughly **\$5–8 billion** over 10 years per JCT.
- **Universal Savings Account proposal** (R-side, 2017–2019):
  consolidates and simplifies but with similar EET structure;
  revenue-neutral by design.

## What the app reproduces

- The app's `tax_expenditures.py` module includes a calibrated entry
  for the retirement-account exclusion, but it is **not currently a
  primary scoring category** — most retirement-related reforms are
  scored via the static-revenue path with no behavioral elasticity.
- The OLG model (`fiscal_model/models/olg/`) is the more rigorous tool
  for retirement-related questions because it captures cohort-specific
  savings response.
- For specific JCT-style scoring of contribution-limit changes, the
  assistant should `web_search` JCT directly.

> Cite JCT tax-expenditure tables for the aggregate dollar values;
> Treasury OTA for distributional analysis; the SECURE 2.0
> conference report for the most recent policy parameters.
