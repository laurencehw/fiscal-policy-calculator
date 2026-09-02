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
- **Biden Green Book proposal** (FY2025): raise GILTI to **21%** and
  apply it on a country-by-country basis. **Treasury publishes no row for
  a GILTI change alone.** The nearest line in the FY2025 Green Book's
  Table of Revenue Estimates is *"Revise the global minimum tax regime,
  limit inversions, and make related reforms"* at **\$373,919 million**
  over FY2025–2034 (report p. 239), which also covers inversions and
  related base-protection provisions. This repository carries
  **−\$280B** as the benchmark for the GILTI change; the 34% gap to
  Treasury's row is part rounding and part scope, in unknown proportions.
- For scale, Treasury OTA's *Tax Expenditures FY2026* prices the whole
  reduced rate on CFC active income at **\$383,830 million** over
  FY2025–2034 (Table 1 line 4).

## FDII — Foreign-Derived Intangible Income

- **What it does**: preferential rate on US-resident corporate income
  from selling goods/services *to foreigners* from US operations.
  Designed to counteract GILTI's incentive to shift IP offshore.
- **Effective rate**: **13.125%** through 2025, **16.4%** thereafter.
- **Biden proposal**: repeal FDII entirely. The FY2025 Green Book's
  Table of Revenue Estimates prints *"Repeal the deduction for
  foreign-derived intangible income"* at a **gross \$157,993 million**,
  paired one-for-one with **−\$157,993 million** of expanded R&D support,
  for an explicit **subtotal of \$0** (report p. 239). Treasury OTA's
  *Tax Expenditures FY2026* separately prices the §250(a) deduction
  itself at **\$130,230 million** over FY2025–2034 (Table 1 line 5), and
  the §250(a)(3) deduction rate falls from 37.5% to **21.875%** from
  TY2026. This repository carries **−\$200B** as the benchmark, which
  matches neither the gross row (21% away) nor Treasury's net score
  (zero) — the sourcing note in
  `fiscal_model/validation/benchmark_sources.py` says so.

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
- **JCT's own five scenarios** (JCX-22-23, *Possible Effects of
  Adopting the OECD's Pillar Two*, June 2023, Table 2, report p. 10)
  bracket the answer **across both signs**, and the conditioning matters
  more than the level:

  | Scenario | Description | US receipts, FY2023–2033 |
  |---|---|---:|
  | 1 | Rest of world enacts; **US does not** | **−\$122.0B** |
  | 2 | Rest of world enacts; US enacts, no US UTPR | **−\$56.5B** |
  | 4 | Rest of world does *not* enact; US enacts, no US UTPR | **+\$102.6B** |
  | 5 | US enacts **including** a UTPR | **+\$236.5B** |

  Every scenario in which US adoption *raises* revenue assumes the rest
  of the world does not enact. Scenario 5 minus Scenario 4 prices a US
  UTPR at **\$133.9B**, within 2% of Treasury's own Green Book row for
  the same instrument (**\$136,313 million**, report p. 239).

## Biden Green Book international package — total impact

The FY2025 Green Book's **"Subtotal, Reform International Taxation"** is
**\$632,200 million** over FY2025–2034 (report p. 240). This repository
carries **−\$700B** as the package benchmark; the package is a superset
of what the module implements, covering base-protection provisions
`international.py` does not model.

## What the app reproduces

`fiscal_model/international.py` implements GILTI rate changes, FDII
repeal, BEAT changes, and Pillar Two alignment scenarios. **None of these
four benchmarks is fitted to its target**, so these are unfitted
reconstructions and the errors are findings, not regressions. Live
figures: `python scripts/cold_holdout.py`.

| Preset | Carried benchmark | Model | Error |
|---|---:|---:|---:|
| Biden GILTI reform (10.5% → 21%, country-by-country) | −\$280B | **−\$230.3B** | **17.8%** |
| Repeal FDII | −\$200B | **−\$110.7B** | **44.7%** |
| Pillar Two adoption (QDMTT + IIR, no US UTPR) | −\$80B | **−\$61.2B** | 23.5% against the midpoint — **inside** JCT's published range [−\$102.6B, +\$56.5B] |
| Full Biden international package | −\$700B | **−\$353.7B** | **49.5%** |

Two things to say alongside those numbers rather than after them:

- **FDII repeal got *worse* on purpose.** It scored 15.0% while the
  module returned a flat \$20B/yr constant that contradicted its own
  \$160B base; giving repeal the same base × rate identity the rate-change
  branch already used, on Treasury's published \$130,230M cost, moves the
  model **toward the document and away from the carried target**, which
  is 54% above Treasury's own figure for the provision.
- **The package's residual is a level, not an interaction.** The module's
  UTPR returns about \$15B over ten years against Treasury's \$136,313M
  row and JCT's implied \$133.9B — two published sources agreeing within
  2% while the module is 9× under both. Re-basing it needs OECD
  country-by-country aggregates by ultimate-parent jurisdiction.

## What's not modeled

- The app does NOT model the **dynamic** response of foreign
  jurisdictions to US rate changes (Pillar Two race-to-the-top
  dynamics). For that question, PWBM and the Tax Foundation publish
  open-economy GE analyses.
- The app does NOT distinguish the **incidence** between US workers
  and US capital — JCT and CBO use a 25/75 split (see
  jct_distributional_methodology.md); the app's distributional engine
  applies the same default.

> Cite JCT (JCX-22-23 for Pillar Two scenarios) for revenue numbers;
> OECD for Pillar Two structure; the Treasury FY2025 Green Book's Table
> of Revenue Estimates and Treasury OTA's *Tax Expenditures FY2026* for
> proposal-level and provision-level costs; the app itself
> (`score_hypothetical_policy` or `get_validation_scorecard`) for this
> model's own figures. Do **not** describe the four rows above as
> calibration: no module constant is fitted to any of them.
