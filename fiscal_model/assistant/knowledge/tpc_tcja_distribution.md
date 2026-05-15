---
source: https://www.taxpolicycenter.org/publications/distributional-analysis-conference-agreement-tax-cuts-and-jobs-act
title: Tax Policy Center — Distributional analyses of TCJA
org: Tax Policy Center (Urban-Brookings)
year: 2024
keywords: [tpc, tax policy center, distribution, distributional, tcja, deciles, quintile, expanded cash income, after tax income, average tax change, share of total benefit, top 1 percent, bottom quintile, urban brookings]
---

# TPC distributional analysis of TCJA (and its extension)

The Tax Policy Center (TPC) maintains the canonical microsimulation-based
distributional tables for major federal tax proposals. For TCJA and its
proposed extensions, TPC's headline tables show the change in
**after-tax income** by **expanded cash income** (ECI) percentile,
typically reported as **quintiles** plus a **top 1%** breakout.

## Headline pattern (consistent across TPC's TCJA tables)

- **Bottom quintile**: very small absolute and percentage gain (often
  well under 0.5% of after-tax income); negligible share of the total
  benefit.
- **Middle quintile**: a modest percentage-of-income gain (typically
  about 1–2% of after-tax income at the height of TCJA's effect).
- **Top 1%**: the largest percentage-of-income gain, typically in the
  **2.5–3.5%** range, capturing a disproportionate share (often
  **20–30%**) of the total dollar value.

The exact numbers depend on:

- **Year analyzed** (2018 is the first full-year, peak benefit; later
  years are smaller because of inflation indexing and bracket creep).
- **Whether SALT cap repeal is bundled in** — repeal sharply increases
  the top decile's gain.
- **ECI vs AGI** — TPC's ECI measure adds tax-exempt income, employer-
  provided benefits, etc.; using AGI shifts the picture slightly.

## How this maps to the app

- The app's `DistributionalEngine` is calibrated against TPC and CBO
  distributional tables for 6 benchmark policies; see
  `get_validation_scorecard` for the error rates by quintile/decile.
- For an exact TPC distributional table on a specific policy, the
  assistant should `web_search` `taxpolicycenter.org` or `fetch_url`
  the specific TPC publication URL.

## Methodological notes worth flagging

- TPC's microsimulation uses a stratified sample of IRS Statistics of
  Income (SOI) records with imputations from CPS for non-filers — a
  different base than the app's CPS-ASEC microsim pilot.
- TPC scores **conventional** by default; their separate macro analyses
  (with Penn Wharton or others) report dynamic effects.

> Cite TPC when the question is about distributional shape, who-benefits,
> or who-bears-the-cost. For revenue magnitude, prefer CBO/JCT.
