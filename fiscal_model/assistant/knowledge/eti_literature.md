---
source: https://www.nber.org/papers/w19075
title: Elasticity of Taxable Income (ETI) — what the literature says
org: NBER / academic literature (synthesized)
year: 2024
keywords: [eti, elasticity of taxable income, saez slemrod giertz, gruber saez, kleven schultz, behavioral response, behavioral offset, tax rate, marginal rate, income shifting, real response, top income, top marginal rate, income shifting margin, deduction margin, intensive margin, extensive margin, labor supply, lindsey, feldstein]
---

# Elasticity of Taxable Income (ETI)

The **Elasticity of Taxable Income** is the most-used summary
statistic for behavioral response to income tax rates. Definition:

```
ETI = (% change in taxable income) / (% change in net-of-tax rate)
```

A net-of-tax rate of (1 − τ): if τ rises from 30% to 40%, (1 − τ)
falls from 70% to 60%, a **14% reduction**. An ETI of 0.25 implies a
**3.5% reduction in taxable income** in response.

## Headline estimates

| Source | Estimate | Sample |
|---|---|---|
| **Saez, Slemrod, Giertz (2012)** | **0.12–0.40** | Comprehensive review |
| Gruber & Saez (2002) | 0.40 | 1979-1990 NBER panel |
| Kleven & Schultz (2014) | 0.10 | Danish 1980-2005 |
| Feldstein (1995) | 1.04+ | TRA86 episodes (high-end outlier) |
| Lindsey (1987) | 1.05–2.75 | ERTA episodes (high-end outlier) |
| CBO working assumption (current) | **0.25** | App default |
| JCT working assumption | 0.25–0.30 | Various |
| Treasury OTA | 0.25 | Distributional tables |

**Consensus midpoint**: roughly **0.25**, with substantial uncertainty.
The 1980s episodes (Feldstein, Lindsey) yielded much higher
estimates that aren't replicated in better-identified later work —
they conflated real labor-supply responses with one-time accounting
choices around major tax-reform transitions.

## What ETI captures and what it doesn't

ETI is a **reduced-form summary** of all margins of response:

1. **Labor supply** — work fewer hours, retire earlier (intensive +
   extensive margins).
2. **Compensation form** — shift from wages to deferred comp, fringe
   benefits, capital-gains-eligible income.
3. **Deductions and shelters** — claim more deductions, use tax
   shelters more aggressively.
4. **Tax avoidance and evasion** — offshore accounts, misreporting.
5. **Spousal income shifting** — change which spouse earns more.

The **biggest margin is typically income shifting** (#2-#5), not
labor supply (#1). That matters because:

- A purely **labor-supply** elasticity is welfare-relevant for
  efficiency analysis (Harberger triangle).
- A pure **income-shifting** elasticity is partially a transfer to
  Treasury via the alternative form's tax base — not a welfare loss.

## ETI varies by income

- **Top 1%**: estimates cluster around **0.4–0.6**. More margins
  available (carried interest, capital gains realization timing,
  pass-through structure choices).
- **Middle income**: estimates cluster around **0.1–0.2**. Fewer
  margins; mostly labor supply and minor deductions.
- **Bottom quintile**: hard to estimate cleanly because of large
  transfer-program EITC margins. The "ETI" framing breaks down because
  changes in net-of-tax rate include the EITC clawback.

## How the app applies ETI

The app uses ETI in `TaxPolicy` via a single behavioral-offset formula:

```
behavioral_offset = ETI × 0.5 × static_effect
final = static × (1 − ETI × 0.5)
```

The **0.5** factor reflects two things:
1. **Asymmetry**: ETI estimates are dominated by tax *increases* in
   the literature. Tax *cuts* tend to have smaller behavioral
   responses (the marginal-rate change is in the "good" direction).
2. **Caution**: CBO and JCT also apply roughly this fraction in their
   behavioral adjustments.

For a +2.6pp marginal-rate increase on \$400K+ income:
- Static effect: roughly **-\$250B** over 10 years.
- ETI offset: **+\$31B** (saves about 12% of revenue).
- Final: **-\$219B**.

This roughly matches CBO's published scoring.

## Why ETI uncertainty matters for policy

A doubling of the assumed ETI (from 0.25 → 0.50) roughly **doubles
the revenue reduction** from a high-rate tax increase. So:

- "Tax the rich at 70%" proposals score very differently depending
  on whether you use ETI = 0.25 (CBO-style) or ETI = 0.6+
  (Diamond-Saez-style optimal-tax literature).
- The **Laffer-curve peak** on income tax depends on ETI:
  - ETI = 0.25 → peak around 73%.
  - ETI = 0.40 → peak around 63%.
  - ETI = 0.60 → peak around 53%.

The app's `Laffer curve` classroom assignment lets students vary ETI
and observe this.

> Cite Saez-Slemrod-Giertz (2012) for the canonical literature review;
> Gruber-Saez (2002) for the foundational US estimate; Kleven-Schultz
> (2014) for the most rigorous identification (Danish administrative
> data); CBO methodology docs for working assumptions.
