---
source: https://www.jct.gov/publications/2024/jcx-48-24/
title: JCT — Estimates of Federal Tax Expenditures (annual)
org: Joint Committee on Taxation
year: 2024
keywords: [jct, tax expenditures, tax breaks, deductions, exclusions, credits, preferential rates, employer health, mortgage interest, charitable, salt, capital gains preference, qbi, 199a, step up basis, retirement, eitc, ctc]
---

# JCT Tax Expenditure Estimates

The Joint Committee on Taxation (JCT) publishes annual estimates of
**tax expenditures** — revenue losses attributable to provisions that
allow a special exclusion, exemption, deduction, credit, preferential
rate, or deferral relative to "normal" tax baseline. These are the
canonical numbers used in Congress and Treasury for tax-reform debates.

## The 10 largest tax expenditures (FY2024–FY2028 cumulative)

Ranked by 5-year revenue cost, in roughly the order JCT typically
reports:

1. **Employer-provided health insurance exclusion** — about **\$2.0 trillion**.
   The single largest tax expenditure; treats employer health coverage
   as untaxed compensation.
2. **Reduced rates on long-term capital gains and qualified dividends**
   — about **\$1.5 trillion**.
3. **Defined-contribution employer retirement plans (401(k) etc.)**
   — about **\$1.3 trillion**.
4. **Defined-benefit employer pensions** — about **\$0.4 trillion**.
5. **Section 199A QBI deduction for pass-through income** — about
   **\$0.7 trillion** (TCJA provision, scheduled to sunset).
6. **Mortgage interest deduction** — about **\$0.4 trillion** (reduced
   sharply by TCJA's higher standard deduction).
7. **Step-up basis at death** — about **\$0.3 trillion**.
8. **Earned Income Tax Credit (EITC)** — about **\$0.4 trillion** (also
   an outlay program; the refundable portion appears in outlays).
9. **Child Tax Credit (CTC)** — about **\$0.7 trillion**.
10. **Charitable contributions deduction** — about **\$0.3 trillion**.

> The exact figures shift with each annual JCT publication (and with
> changes in tax law). The list of top-ten items is more stable than
> the dollar amounts. For current numbers, the assistant should
> `web_search` `jct.gov` or `fetch_url` the latest JCX publication.

## How tax expenditures differ from outlays

- A tax expenditure is **not** identical to direct spending of the same
  size — incidence is different (concentrated on people who claim it),
  and the behavioral response is different.
- JCT cautions that expenditures are **not additive** — repealing two
  preferences yields more revenue than the sum of each repealed alone
  (because of interactions in marginal rates and itemization choices).

## How this maps to the app

- The app's `tax_expenditures.py` module scores selected expenditure
  changes (SALT cap, employer health exclusion, step-up basis) and
  validates against JCT estimates.
- For tax-expenditure questions the assistant should:
  (a) check `get_validation_scorecard` for the app's own calibrated
  estimate, and (b) cite JCT for the official figure.

> Cite JCT tax expenditures when the question is "what are the biggest
> tax breaks?", "how much would repealing X raise?", or "who benefits
> from preference Y?"
