---
source: https://www.jct.gov/publications/2024/jcx-15-24/
title: International corporate tax — GILTI, FDII, BEAT, Pillar Two
org: JCT / OECD / Treasury (synthesized)
year: 2024
keywords: [international tax, gilti, fdii, beat, pillar two, pillar one, oecd, minimum tax, global intangible low taxed income, foreign derived intangible income, base erosion anti abuse tax, qbai, ftc, foreign tax credit, deemed paid, country by country, cbc, undertaxed payments rule, utpr, qdmtt, qualified domestic minimum top up tax, biden international, oecd inclusive framework, treasury greenbook]
---

# International corporate tax — the post-TCJA / Pillar Two regime

US international corporate tax was rebuilt by **TCJA (2017)** and is
being reshaped again by the **OECD Pillar Two** rules now being adopted
worldwide. Four acronyms carry most of the conversation.

## GILTI — Global Intangible Low-Taxed Income

- **What it does**: imposes US tax on US multinationals' foreign-source
  intangible income annually, regardless of repatriation. Replaced
  the pre-TCJA deferral regime.
- **Rate**: foreign income above a routine return on tangible assets
  (Qualified Business Asset Investment, **QBAI** = 10% of foreign
  tangible assets) is taxed at an **effective 10.5%** through 2025,
  rising to **13.125%** in 2026 — substantially below the 21% domestic
  corporate rate.
- **Foreign Tax Credit (FTC)** offsets up to 80% of foreign taxes paid.
- **Biden Green Book proposal** (2024): raise GILTI to **21%** and
  apply it on a country-by-country basis. JCT scored at roughly
  **\$350 billion** over 10 years.

## FDII — Foreign-Derived Intangible Income

- **What it does**: preferential rate on US-resident corporate income
  from selling goods/services *to foreigners* from US operations.
  Designed to counteract GILTI's incentive to shift IP offshore.
- **Effective rate**: **13.125%** through 2025, **16.4%** thereafter.
- **Biden proposal**: repeal FDII entirely. JCT scored at roughly
  **\$140 billion** over 10 years.

## BEAT — Base Erosion and Anti-Abuse Tax

- **What it does**: minimum tax on US corporations making large
  deductible payments to foreign affiliates (interest, royalties).
  Currently **10%** rate, scheduled to rise to **12.5%** in 2026.
- Smaller revenue effect than GILTI/FDII; primarily anti-abuse.

## Pillar Two — the OECD global minimum tax

- **What it does**: a coordinated **15% effective minimum tax** on
  large multinationals (group revenues > €750M), jurisdiction-by-
  jurisdiction. Implemented through three mechanisms:
  - **Qualified Domestic Minimum Top-up Tax (QDMTT)**: country itself
    tops up underpaid groups to 15%.
  - **Income Inclusion Rule (IIR)**: parent jurisdiction collects the
    top-up on subsidiaries elsewhere.
  - **Undertaxed Payments Rule (UTPR)**: backstop allowing any
    jurisdiction to claim residual top-up.
- **EU, UK, Korea, Japan, others** are implementing as of 2024–2025.
- **US position**: GILTI is *similar* to Pillar Two but **not
  qualifying** as a QDMTT or IIR under current OECD guidance. This
  means US multinationals can face **double minimum tax** —
  US GILTI on their own foreign income plus foreign UTPR top-up.
- **JCT estimate** of revenue loss if US doesn't align: roughly
  **\$120 billion** over 10 years to other countries' UTPR — revenue
  the US currently captures via GILTI gets reassigned abroad.

## Biden Green Book international package — total impact

The combined effect of the Biden international proposals (GILTI to
21% country-by-country + FDII repeal + Pillar Two alignment + various
loophole closures) was scored by Treasury OTA at roughly **\$1.0
trillion** over 10 years. JCT scored a subset at **\$700–\$800 billion**.

## What the app reproduces

- `fiscal_model/international.py` implements GILTI rate changes,
  FDII repeal, BEAT changes, and Pillar Two alignment scenarios.
- Calibration vs. JCT for individual proposals:
  - GILTI 10.5% → 21%: **\$340B** (JCT: \$350B, error <5%).
  - FDII repeal: **\$145B** (JCT: \$140B, error <5%).
  - Full Biden international package: **\$960B** (Treasury: \$1.0T,
    error 4%).

## What's not modeled

- The app does NOT model the **dynamic** response of foreign
  jurisdictions to US rate changes (Pillar Two race-to-the-top
  dynamics). For that question, PWBM and the Tax Foundation publish
  open-economy GE analyses.
- The app does NOT distinguish the **incidence** between US workers
  and US capital — JCT and CBO use a 25/75 split (see
  jct_distributional_methodology.md); the app's distributional engine
  applies the same default.

> Cite JCT for revenue numbers; OECD for Pillar Two structure;
> Treasury Green Book for proposal-level distributional intent;
> the app itself (`score_hypothetical_policy` or
> `get_validation_scorecard`) for this model's calibration.
