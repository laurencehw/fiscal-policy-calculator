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

Since November 2026 the app applies Saez, Slemrod and Giertz's (2012,
eq. 3) erosion share to an ordinary income-tax rate change:

```
behavioral_offset = ETI × w × static_effect
w = τ / (1 − τ) × a,   a = z_m / (z_m − z*)
final = static × (1 − ETI × w)
```

- **τ** is the federal statutory marginal rate the affected income
  already faces, read from CBO's tax-parameter schedule (publication
  53724) for each filing status.
- **a** is the Pareto-style ratio of mean income above the floor `z*`
  to the income above it, from IRS SOI Table 1.1. A $0 floor gives
  `a = 1`.

So the weight is small for a rate change on every bracket (w ≈ 0.35)
and large at the top (w ≈ 1.2-1.4 above $400K). Before this, every
rate change used a flat w = 0.5. Capital gains, corporate, payroll,
credits and the specialized modules keep their own responses.

For a +2.6pp marginal-rate increase above \$400K (one floor for every
filing status, FY2026-2035):
- Static effect: about **-\$354B** over 10 years.
- Weight w = 1.385, so the offset is about 35% of the static effect.
- Final: about **-\$231B**.

With the Green Book's own per-status floors (\$400K single, \$450K
joint) the weight is 1.232 and the model scores **-\$242.7B** against
Treasury's **-\$245.9B** (FY2025-2034).

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
