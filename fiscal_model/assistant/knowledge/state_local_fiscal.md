---
source: https://www.cbo.gov/topics/state-and-local-finance
title: State and local fiscal interaction with federal policy
org: CBO / NCSL / Tax Foundation (synthesized)
year: 2025
keywords: [state, local, fiscal, salt, salt cap, federal aid, intergovernmental transfers, medicaid match, fmap, fiscal federalism, conformity, state income tax, state sales tax, state corporate, property tax, balanced budget requirement, rainy day fund, arpa, american rescue plan, infrastructure, ira pass through, state and local government, sub federal, ncsl]
---

# State-and-local fiscal interaction with federal policy

State and local governments **collect roughly the same revenue as the
federal government does** ($3.5T vs ~$5T federal in FY2024) and account
for the majority of public-sector employment (~20 million state/local
workers vs ~3 million federal). Federal policy shapes their finances
through five channels.

## 1. Federal aid

- **Total federal grants** to states + localities: roughly **\$1.0
  trillion** in FY2024 (~3.5% of GDP), about a third of state revenue.
- **Medicaid** is by far the largest line — federal share averages
  ~**64%** (the FMAP formula, ranging from 50% in wealthy states to
  78% in poor states).
- Education (Title I, IDEA), highway (HTF), housing (HUD), and SNAP
  administration round out the major streams.
- Pandemic-era windfalls: **ARPA (2021)** dispensed **\$350 billion**
  to state/local governments — a one-time injection that artificially
  improved 2021–2023 state budget pictures.

## 2. SALT cap interaction

The **\$10,000 SALT cap** (TCJA) caps the federal deduction for state-
and-local taxes paid. Two effects:

- **Federal revenue gain**: ~**\$1.9 trillion** over a decade (JCT).
- **Distributional**: bites hardest in high-tax states (CA, NY, NJ, CT,
  MA, MD, IL) — concentrated among top decile filers.
- **State response**: many high-tax states enacted **pass-through entity
  (PTE) taxes** that effectively let business owners deduct SALT at the
  entity level, partially circumventing the cap. JCT now scores SALT
  cap repeal at the lower end (~\$1.5–1.9T range) because of this leak.

## 3. State conformity to federal tax law

Most states use **federal AGI** or **federal taxable income** as a
starting point for state income tax. So federal changes propagate:

- TCJA's higher standard deduction **broadened state tax bases**
  (since fewer itemized deductions reduce state taxable income),
  giving conforming states a windfall **without raising rates**.
- TCJA's pass-through 199A deduction is **not** automatically picked
  up by states; about half the states explicitly decouple.
- The **IRA's clean-energy credits** have mostly NOT been picked up by
  states — federal credits don't automatically reduce state tax.

## 4. Federal preemption and mandates

- The **Medicaid match formula** structurally constrains state choices:
  states can't easily exit Medicaid without massive cost shifts.
- The **ACA Medicaid expansion** was made optional by NFIB v. Sebelius
  (2012); 40 states + DC have expanded as of 2024.
- **Unfunded mandates** are politically constrained by the Unfunded
  Mandates Reform Act, but de-facto mandates (e.g., complying with new
  EPA emissions rules) still impose state costs.

## 5. Balanced-budget requirements and rainy-day funds

- **49 of 50 states** have a balanced-budget requirement (Vermont is
  the exception). These typically apply to the **operating budget**,
  not capital — so states issue bonds for infrastructure.
- The constraint is procyclical: in recessions, states must cut
  spending or raise taxes when federal aid is most needed. This is
  why federal stimulus typically targets state-and-local: **dollar
  for dollar, state-and-local stimulus has the highest multiplier**
  (~1.7-2.0 per CBO and FRB/US).
- **Rainy-day funds** average ~**14% of general-fund spending** at the
  state level — historically high, post-pandemic.

## How this maps to the app

- The app's `state_analysis.py` tab handles the top 10 states' tax
  systems with explicit SALT-cap interaction.
- The federal `SALT` policy in `tax_expenditures.py` is calibrated
  against JCT's cap-repeal scoring.
- The app does NOT directly model the PTE workaround leakage; this
  is part of why SALT repeal scores are slightly above JCT's most
  recent updates.

> Cite NCSL or Tax Foundation for state-by-state details; CBO for
> aggregate federal-aid numbers; JCT for SALT-cap revenue effects;
> Pew or Urban Institute for distributional state-level analyses.
