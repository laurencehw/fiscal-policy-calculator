# Gains at death: is the level too small by the death rate?

*Memo, 2026-11-04. No score moves. The measurement is `scripts/gains_at_death_level.py`,
and `tests/test_gains_at_death_level.py` fails if this page quotes a different factor
than that script prints. Written before any change to `capital_gains.py`.*

## Conclusion

**The level is not changed.** The factor of **7.12** is real as arithmetic. Both
numbers estimate unrealized gains held by decedents, so a gap of that size means
one of the inputs is wrong. The published record, below, does not support
multiplying the flow by 7.12.

In 2025 the module's flow is **$196.2B**. Applying the NCHS wealth-weighted death
rate (2.647%) to the accrued-gains stock ($52,768B) would put gains at death at
**$1,397B**.

## Which estimator the record supports

A range only. Neither figure below is a target, and neither this memo nor
`capital_gains.py` takes a number from it.

**The tax-expenditure plausibility range.** Two agencies publish the revenue
cost of not taxing gains at death. Dividing that cost by a statutory rate on
long-term gains is an implied flow. The top rate on adjusted net capital gain is
20 percent (26 U.S.C. §1(h)), and the net investment income tax adds 3.8 percent
(§1411), so 23.8 percent at the top. The 15 percent bracket in §1(h) is the
other statutory rate that applies to most realizations. The expenditures do not
publish the effective rate inside the estimate, so both ends are shown.

| Source | What is pinned | FY2026 | Implied gains at 23.8% | Implied gains at 15% |
|---|---|--:|--:|--:|
| Treasury, Office of Tax Analysis, *Tax Expenditures, Fiscal Year 2026*, Table 1, item 75, "Step-up basis of capital gains at death" (millions of dollars; the columns are 2024–2034). https://home.treasury.gov/system/files/131/Tax-Expenditures-FY2026.pdf | FY2026 cell **41,130** | $41.1B | $173B | $274B |
| Joint Committee on Taxation, JCX-45-25 (3 December 2025), *Estimates of Federal Tax Expenditures for Fiscal Years 2025–2029*, Table 1, row "Exclusion of capital gains at death", individuals column. https://www.jct.gov/publications/2025/jcx-45-25/ | FY2026 cell **72.5** | $72.5B | $305B | $483B |

The band is about **$170B to $480B**. The module's **$196.2B** sits at the low
end, next to Treasury's expenditure read at the top statutory rate. **$1,397B**
is about three times the top of the band. Matching the two expenditures at that
flow would take an effective rate of about 3 percent (Treasury) or 5 percent
(JCT), below either statutory rate.

**Differential mortality.** The 2.647 percent rate applies a population life
table, weighted by wealth, to a stock the wealthy hold. Mortality falls with
income and with wealth, so that rate is high for this stock and mortality times
the stock moves **down**, not up. Chetty and coauthors (JAMA 2016; 315(16):
1750–1766) find the richest 1 percent of men live 14.6 years longer than the
poorest 1 percent, and women 10.1 years. Saez and Zucman (QJE 2016, "Wealth
Inequality in the United States since 1913") apply mortality multipliers that
decline with wealth, below one at the top, precisely because a population life
table overstates deaths among the wealthy.

## What the factor is

| Quantity | Value | Source, as pinned on the parameter row |
|---|--:|---|
| Flow of unrealized gains at death | $196.2B | `gains_at_death_share_of_net_worth` × DFA net worth. The share is Poterba & Weisbenner (2001) Table 8: $42.8B of expected unrealized gains over 1998:Q4 household net worth |
| Estate-dollar flow | 0.320% of net worth | The same table: $118.9B of expected estates over that net worth. Dollars over dollars. Read only as the provenance of the share above |
| Gain share of those estates | 36% | Poterba & Weisbenner (2001) Table 8 |
| Accrued gains as a share of living net worth | 30.9% | Avery, Grodzicki & Moore, FEDS 2013-28, Figure 1, on DFA net worth by percentile, 2024:Q4 |
| Death exit of the accrued-gains stock | 2.647%/yr | NCHS life table weighted by DFA net worth by age. `mortality_weighted_net_worth_share` |
| Implied exit if the flow is a share of the stock | 0.372%/yr | $196.2B / $52,768B |
| Factor | **7.12** | 2.647% / 0.372% |

The 7.12 is the ratio of two rates that were already separated on purpose.
`estate_flow_rate` was used as a headcount until Wave C and produced 408,532
decedents against about 3.09 million deaths. The headcount now uses the NCHS
rate. The dollar flow was left as Poterba & Weisbenner's measured flow. Multiplying
that flow by 7.12 would put the headcount correction back into the dollars.

## What was checked, and what is not in this repository

- **SCF 2022 with an NCHS life table**, which would repeat Poterba & Weisbenner's
  method on current data. The Survey of Consumer Finances microdata is not in
  this repository, so this memo does not print an SCF figure.
- **IRS SOI estate-tax returns.** The file here carries the charitable share by
  estate size and the filing threshold. It does not carry a total of unrealized
  gains at death, and an estate-tax return covers the taxable tail, not every
  decedent.
- **IRS SOI Sales of Capital Assets.** Not in this repository. The share of
  sold assets acquired by inheritance would be a check on basis, not a
  substitute for the flow.
- **JCT and Treasury tax-expenditure estimates for step-up at death.** Used
  above as a plausibility range and not as a target. Adopting either figure as
  the flow would be a fit.

## If a later lane adopts the mortality-times-stock level

That lane has to be pre-registered before `capital_gains.py` is opened, and it
has to predict both of these, because the second is a cancellation:

- `cbo_opt51_gains_at_death` is **35.5% under** (model −$345.9B, CBO −$536.1B).
  A larger death stock moves it toward the target and can pass it. The lane
  writes the predicted error before scoring. A 7.12× stock is not a 7.12× score:
  the death channel is one part of the row.
- `treasury_capgains_39_plus_stepup_elim` reads **1.8%**. That figure is two
  errors cancelling. Enlarging the death channel removes one of them and is
  predicted to make the row worse.
- `biden_capital_gains_39` over-predicts by **27.0%** with the death channel
  already in the score. The other half of the Treasury cancellation is this
  over-prediction. A larger death stock does not fix it. The lane says what
  would, and does not tune the rate elasticity to hide it. The 22% reference
  rate stays frozen.

Until that pre-registration exists, the flow stays Poterba & Weisbenner's.
