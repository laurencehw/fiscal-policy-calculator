# Gains at death: is the level too small by the death rate?

*Memo, 2026-11-04. No score moves. The measurement is `scripts/gains_at_death_level.py`,
and `tests/test_gains_at_death_level.py` fails if this page quotes a different factor
than that script prints. Written before any change to `capital_gains.py`.*

## Conclusion

**The level is not changed.** The factor of **7.12** is real as arithmetic and is
not evidence that the flow of gains at death should be multiplied by it.

In 2025 the module's flow is **$196.2B**. Applying the NCHS wealth-weighted death
rate (2.647%) to the accrued-gains stock ($52,768B) would put gains at death at
**$1,397B**. Those two numbers answer different questions.

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
- **JCT and Treasury tax-expenditure estimates for step-up at death.** A
  plausibility range only, and not used. A tax expenditure is not a target for
  this flow, and adopting one would be a fit.

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
