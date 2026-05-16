---
source: https://www.cbo.gov/publication/58946
title: Inflation Reduction Act — clean-energy provisions and scoring
org: CBO / JCT / Treasury (synthesized)
year: 2024
keywords: [ira, inflation reduction act, clean energy, climate, tax credits, ptc, itc, 45y, 48e, 30d, ev credit, 25e, used ev, 45w, commercial ev, 45z, clean fuel, 45v, hydrogen, 45q, carbon capture, ccus, ccs, doe loan, advanced energy, energy community, prevailing wage, apprenticeship, domestic content, direct pay, transferability, monetization, irs enforcement, methane fee]
---

# Inflation Reduction Act clean-energy provisions

The **Inflation Reduction Act (IRA, 2022)** is the largest climate
investment in US history. Its scoring is contentious because nearly
every provision is an **uncapped tax credit** — the cost depends
entirely on uptake. Initial CBO scores in 2022 have already been
revised upward.

## Headline scoring

| Provision | CBO 2022 (10y) | Goldman/Penn Wharton update | Notes |
|---|---|---|---|
| **§45Y / §48E** — Clean electricity PTC / ITC | -\$320B | -\$700–\$1,200B | Replaces §45/§48 in 2025; tech-neutral |
| **§30D / §25E / §45W** — EV credits | -\$15B | -\$30–\$60B | New, used, and commercial EVs |
| **§45Z** — Clean fuels PTC | -\$3B | -\$20–\$80B | Sustainable aviation fuel uncapped |
| **§45V** — Hydrogen PTC | -\$13B | -\$40–\$130B | Disputed by Treasury 45V guidance |
| **§45Q** — Carbon capture | -\$3B | -\$30–\$120B | Boosted from \$50/ton to \$85/ton |
| **§48C / §40D** — Manufacturing, EV battery | -\$30B | -\$45–\$80B | Capped pool + uncapped 45X |
| **§25C / §25D** — Residential energy | -\$40B | -\$50B | Homeowner credits |
| **IRS enforcement** | +\$200B | +\$140B | Funding (partially clawed back) |
| **Methane fee** | +\$1B | +\$1B | Modest enforcement tool |
| **Drug pricing reforms** | +\$160B | +\$160B | Medicare negotiation; non-climate |

**Combined IRA climate cost** (10y, 2022 CBO score): roughly **\$370
billion**. **Updated estimates** (Goldman Sachs 2023, PWBM 2024): the
energy-credit portion alone has risen to **\$1.0–\$1.6 trillion** as
high-end uptake scenarios become baseline.

## Why estimates keep rising

1. **Uncapped credits with broad eligibility** — every kWh of clean
   electricity, every EV, every ton of captured CO₂ generates a credit.
   Higher deployment = higher cost.
2. **Treasury-friendly implementation** — Final regulations on §45V
   (hydrogen), §45Y (clean electricity transferability), and
   §45Q (carbon capture) tended toward broader eligibility.
3. **Stacking** — Many projects qualify for multiple credits
   simultaneously (production + ITC + energy community + domestic
   content + prevailing wage bonuses).
4. **Transferability** (§6418) — credits can be sold to third parties
   for cash. This dramatically increases uptake because non-profits and
   tax-exempt entities can monetize via **direct pay** (§6417).

## Bonus credit structure

Most §45Y/§48E credits have a **base** and **bonus** rate:

- **Base**: 0.6¢/kWh (PTC) or 6% ITC.
- **Prevailing wage + apprenticeship**: 5× multiplier → 3.0¢/kWh or 30%.
- **Energy community bonus**: +10% ITC.
- **Domestic content bonus**: +10% ITC.

Stacking can push effective ITC to **50%** of project cost — making
the credits, not the project economics, the primary investment driver.

## Distributional incidence

- **Consumer-facing credits** (EV, home efficiency): top quintile
  captures most of the dollar value (high earners buy more EVs).
- **Producer-facing credits** (PTC, ITC, manufacturing): incidence is
  ambiguous — partly to consumers (lower energy prices), partly to
  shareholders, partly to workers.
- **JCT distributional analyses** of the residential portion show a
  **modestly regressive** pattern (correlating with home ownership
  and EV affordability).

## Repeal scenarios

Multiple 2024–2025 proposals would repeal or scale back IRA credits:

- **Full repeal**: saves **\$1.0–\$1.5 trillion** over 10 years
  (depending on which update you use).
- **EV credit elimination only**: saves **\$30–\$60 billion**.
- **Hydrogen credit tightening**: saves **\$20–\$100 billion**
  depending on the alternative regs.

## How this maps to the app

- The app's `climate.py` module includes calibrated presets for IRA
  full repeal, IRA energy-credit repeal, IRA EV credit repeal, and
  carbon tax variants. Validated against CBO + Goldman + PWBM ranges.
- For the IRS enforcement portion specifically, see
  `enforcement.py` which models ROI of additional IRS funding.

> Cite CBO for the original 2022 baseline numbers; Goldman/PWBM for
> updated estimates; Treasury final regs for the implementation
> details that drive the cost trajectory.
