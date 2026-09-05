# W4 — Capital gains at death: carve-outs and a behavioural response

*Wave 4 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §6.2,
items 7 and 14 — the two halves of the one carry-over that names this lane.
Pre-registered 2026-09-02 against `origin/main` @ `5deef17`, **before** any code
in this lane changed. The outturn is appended at the bottom as the lane's last
commit.*

Wave 2's L1 closed four defects in the capital-gains module and named the fifth
in its own §5.7: *"the death channel has no behavioural response."* That is the
whole residual on the two Treasury rows, and `MODELING_IMPROVEMENT.md` §6.2
carries it twice — once as a target-scope note (item 7) and once as a model
gap (item 14). This lane builds the missing structure. Nothing below is a
promise of attainment (§1.5 forbids that). Every number in §5 was computed by
hand from published figures *before* a line of module code changed, in a
scratch script that reads the shipped decedent ladder and applies the
transcribed shares to it, so a reader can check whether the mechanism behaved
the way the lane said it would.

## 1. Starting point (measured on `5deef17`)

`python scripts/cold_holdout.py --json`:

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| out-of-sample (Tier 1) | 26 | **31.0%** | 15.1% | 13 | 19 |
| calibrated reference (fitted) | 28 | 2.0% | 0.1% | 28 | 28 |
| uncalibrated reconstruction | 26 | 61.8% | 38.0% | 5 | 9 |

Tier 1 error mass is **805.8**. The four capital-gains rows carry **405.6 of it
— 50.3%**, still the largest single mass in the tier:

| policy_id | official ($B) | model ($B) | abs err |
|---|--:|--:|--:|
| `treasury_capgains_39_plus_stepup_elim` | −322.0 | −1,022.3 | **217.5%** |
| `biden_capital_gains_39` | −288.6 | −678.1 | **134.9%** |
| `cbo_opt47_ltcg_qdiv_2pp` | −103.3 | −57.1 | 44.8% |
| `cbo_opt51_gains_at_death` | −536.1 | −581.2 | 8.4% |

`python scripts/run_loo.py --donor-matrix`: 18 derivable, **28.4%** mean, 16.5%
median, 9/18 within 15%, 4 not cross-validatable. The `CapitalGains` module is
**39.6%** (n=3):

| case_id | official ($B) | LOO ($B) | signed err |
|---|--:|--:|--:|
| `cbo_2pp_all_brackets` | −70.0 | −79.8 | −14.0% |
| `pwbm_39_with_stepup` | +33.0 | +23.6 | −28.4% |
| `pwbm_39_no_stepup` | −113.0 | −26.6 | +76.5% |

**None of the three LOO cases runs the death channel** — two keep step-up
(`eliminate_step_up=False`) and the third sets `score_gains_at_death=False`
because PWBM's $113B is the rate change only. So this lane predicts the
`CapitalGains` LOO module is **untouched**, and any movement in it is a
falsification (§6).

The three Tier-1 rows the lane touches decompose exactly, because the death
channel is a separate addend in `scoring_engine._score_tax_policy_year`:

| row | rate channel | death channel | total |
|---|--:|--:|--:|
| `cbo_opt51_gains_at_death` | 0.0 | **581.2** | 581.2 |
| `biden_capital_gains_39` | 220.3 | **457.8** | 678.1 |
| `treasury_capgains_39_plus_stepup_elim` | 220.3 | **802.0** | 1,022.3 |

The rate channel is identical on the two Treasury rows — same +19.6pp above the
same $1,000,000 — so **everything that separates those two predictions, and
almost everything that separates each of them from its target, is the death
channel.** That is what this lane changes; the rate channel is not touched.

## 2. What the death channel does today, and what it omits

`CapitalGainsPolicy.estimate_step_up_elimination_revenue` takes the decedent
ladder Wave 2 built — Poterba & Weisbenner (2001) Table 8's flow of unrealized
gains at death, carried as a share of household net worth and grown with the
Financial Accounts stock, distributed across five estate-size classes by Avery,
Grodzicki & Moore's unrealized-gain share — subtracts the per-decedent
exclusion, and prices the rest at the rate the gain would face on a final
return. Five decedent classes, one exclusion, one rate. That is the whole
model.

Both Green Books state six reliefs alongside that exclusion, and price all of
them (FY2022 report pp. 62-63, PDF pp. 68-69; FY2025 report pp. 80-81, PDF
pp. 88-89 — the two texts are near-identical and differ only in the exclusion
amount and the threshold definition):

1. **Transfers to a U.S. spouse** carry over basis; gain is not realized until
   the surviving spouse disposes of the asset or dies.
2. **Transfers to charity** — *"appreciated property transferred to charity
   would not generate a taxable capital gain"* (FY2022) / *"would be exempt
   from capital gains tax"* (FY2025).
3. **Tangible personal property** — *"any gain on all tangible personal
   property such as household furnishings and personal effects (excluding
   collectibles)"* is excluded from recognition.
4. **The §121 principal-residence exclusion** — *"the $250,000 per-person
   exclusion under current law ... would apply to all residences and would be
   portable to the decedent's surviving spouse, making the exclusion
   effectively $500,000 per couple."*
5. **Family-owned-and-operated businesses** — payment *"would not be due until
   the interest in the business is sold or the business ceases to be
   family-owned and -operated."*
6. **A 15-year fixed-rate payment plan** for the tax on non-liquid assets other
   than businesses electing the deferral.

Plus a per-donor exclusion of **$1,000,000 (FY2022)** or **$5,000,000
(FY2025)**, which is the only one the module prices, and it applies to *"other*
unrealized capital gains" — i.e. after the reliefs above, not before.

CBO's Option 51 alternative 2 (pub. 60557, report p. 61) states **none** of
these. Its whole text is *"capital gains would be taxed as if the decedent had
sold the asset at death"*, with a note that the tax would be deductible against
the estate tax. It carries no exclusion, no deferral and no rate change — which
is why it is the row that tests the *level* of the channel and the Green Book
rows are the ones that test its *design*.

## 3. The mechanism this lane adds

Three channels, in the order the statute applies them, all inside
`estimate_step_up_elimination_revenue`.

### 3.1 Carve-outs — and two of the five are already in the base

The base this module prices is *unrealized capital gains at death*, from
Poterba & Weisbenner Table 8. That table's own note settles two of the six
reliefs before any code is written:

> *"Bonds, vehicles, and collectibles are assumed to have no accrued capital
> gains. ... It is assumed a decedent transfers his/her full estate to a
> surviving spouse. Such inter-spousal transfers are not included in the estate
> totals reported above."*

So the **spousal** carve-out and the **tangible-personal-property** carve-out
remove nothing this base contains: inter-spousal transfers were never in the
$42.8B, and household furnishings and personal effects carry no accrued gain in
it. Both are therefore carried as **0.0** with the quotation attached, and the
marital-bequest share is carried beside them purely as a magnitude
cross-check — SOI Estate Tax Table 1 puts bequests to a surviving spouse at
32.9% of the gross estate of estate-tax filers, which is what the model would
be double-counting if it deducted them again. **Deducting either would be the
error, not the fix**, and that is the first finding of this lane.

What is left removes real revenue:

- **Charitable bequests.** IRS SOI *Estate Tax Statistics*, Table 1, filing
  year 2024 (`24es01fy.xlsx`): the charitable deduction over the gross estate
  net of bequests to a surviving spouse — the right denominator, because PW's
  base is the estate that passes to someone other than a spouse. By size of
  gross estate: **$50M+ 36.20%**, $20-50M 12.03%, $10-20M 6.20%, under $10M
  4.30%. **Zero below SOI's smallest printed class**, which understates the
  carve-out for the two bottom ladder classes and therefore over-states the
  model's revenue there — the conservative direction, chosen deliberately.
- **§121, the principal residence.** `min(residence gain per decedent,
  $250,000)`, the statutory per-person figure (IRC §121(b)(1)), applied per
  decedent. The residence share of *unrealized gains* is PW Table 8's own
  "Share of Total Unrealized Capital Gain" panel: **100.1% below $250K of net
  worth, 83.1%, 46.0%, 35.2%, 10.2%, and 3.6% at $10M+**. The $250,000 cap
  therefore erases essentially the whole gain of a small decedent and about a
  fifth of a percent of a large one, which is what the statute does.
- **The family-owned-business deferral.** PW Table 8's "Business (active) &
  Farm" share of unrealized gains: **72.3% at $10M+**, 17.2% at $5-10M, falling
  to 0.6% at the bottom. Deferred until the interest is sold, so within a
  ten-year window the tax is collected only on what is sold: the deferred stock
  is recaptured at the module's **own observed realization hazard** (SOI
  realizations over the Financial Accounts accrued-gains stock, 2.10%/yr), so
  `recapture(t) = 1 − (1 − h)^(t+1)` and no new constant enters.

**PW's "active business" is an upper bound on "family-owned and -operated",**
and it is the single largest carve-out in the lane. No published split of
active-participant businesses into family-operated and not exists, so the lane
takes the share whole and says so here rather than inventing a haircut.

### 3.2 A behavioural response at death

Two channels, one frozen value each, neither fitted.

- **The rate response, persistent only.** Gains at death respond to a change in
  the rate facing them exactly as other gains do — `exp(−b·Δτ)` with
  `b = persistent_elasticity / elasticity_reference_rate`, Decision 3's frozen
  Dowd–McClelland–Muthitacharoen (2015) 0.72 at CRS R48562's 22% reference
  rate, divided by the same lock-in wedge the realization channel uses when
  step-up is eliminated. **The transitory coefficient is suppressed**, because
  it is a retiming coefficient and death cannot be retimed to the rate. `Δτ` is
  the policy's own rate change, so **CBO Option 51 — which changes no rate — is
  untouched by this channel**, and the two Green Book rows get
  `exp(−(3.2727/1.4443)·0.196) = 0.641` on the decedents the rate change
  reaches.
- **Charitable substitution.** Taxing gains at death makes a charitable bequest
  cheaper relative to a bequest to heirs: per dollar of asset given, the estate
  saves `τ·g` where `g` is the unrealized-gain share of that wealth — the
  ladder's own AGM share, so again no new quantity. With a constant-elasticity
  demand, the charitable share rises by `(1 − τ·g)^(−ε_c)`. `ε_c` is frozen at
  **1.617** — Bakija, Gale & Slemrod (2003), *Charitable Bequests and Taxes on
  Inheritances and Estates*, NBER WP 9661 / AEA P&P, Table 1, **specification
  (a)**. That is the *smallest* magnitude in their table; their most robust
  specification (d) is **−2.142**, and Joulfaian (2000) reports −0.74 on a
  1992 cross-section. Specification (a) is taken deliberately because a larger
  elasticity would move the two over-predicting Treasury rows further in this
  lane's own direction, and the smallest available number is the one that
  concedes least. The channel also ignores that a charitable bequest already
  avoids estate tax for a taxable estate, which understates the price drop and
  so the response — again the conservative direction.

### 3.3 Each row scores its own document's design

The exclusion and threshold already come from each record: `$5,000,000` for the
FY2025 row, the `CapitalGainsPolicy` default `$1,000,000` for the FY2022 row,
`0.0` for CBO Option 51. The family-business deferral does not, and it is the
one design switch this lane adds. It is set by a rule about the *documents*,
registered here before it is written:

> **`GREEN_BOOK_DEATH_DESIGN_RULE`.** A realization-at-death proposal published
> by the Treasury in a Green Book carries the reliefs the Green Book states
> alongside its per-donor exclusion, including the family-owned-business
> deferral. A budget option that states none carries only what its own text
> describes. Keyed on `CBOScore.source is ScoreSource.TREASURY` for a
> capital-gains shape that eliminates step-up; a test pins that this selects
> the same two rows as the alternative key (`step_up_exemption > 0`), so the
> rule cannot quietly become a per-row switch.

The carve-outs in §3.1 and the behavioural channels in §3.2 are **not** design
switches: a tax-exempt donee, a statutory §121 exclusion and a price response
are properties of any constructive-realization regime, so CBO Option 51 gets
them too. That is why this lane expects Option 51 to get **worse**.

### 3.4 What the lane does not build

The **15-year installment election** (relief 6) is a within-window timing
effect on the non-liquid, non-deferred share, and no share of it is separately
measurable in PW Table 8. It is not modelled, and it would move both Green Book
rows further down.

The **estate-tax deduction** for the capital gains tax paid at death — stated
by both Green Books *and* by CBO Option 51's own text — is not modelled either.
It is an estate-tax interaction, not a capital-gains one, and on SOI's 2,663
taxable returns it is worth roughly a tenth of the channel.

The **decedent headcount** is unchanged and remains the coarsest thing in the
ladder: `decedents = households × household_share × estate_flow_rate`, where
`estate_flow_rate` is Poterba & Weisbenner's *dollar* flow of estates over
household net worth (0.3195%/yr) used as a *headcount* rate, giving 408,533
decedents a year against roughly 3 million actual deaths. Because the
per-decedent exclusion bites on gains *per decedent*, too few decedents means
too much gain each and too little exclusion. This lane does not touch it; it is
named here as the reason the two Green Book rows may still over-predict after
the carve-outs land.

## 4. Data transcribed

New file `fiscal_model/data_files/capital_gains/decedent_carveout_shares.csv`,
with a provenance header and regenerable by
`python scripts/build_capital_gains_data.py`.

| Quantity | Value | Source |
|---|---|---|
| Share of unrealized capital gain in the primary residence, by estate size | 100.1% (<$250K) / 83.1% / 46.0% / 35.2% / 10.2% / 3.6% ($10M+) | Poterba & Weisbenner (2001) Table 8, lower panel |
| Share of unrealized capital gain in active business & farm, by estate size | 0.6% / 1.4% / 1.7% / 11.4% / 17.2% / **72.3%** | same |
| Bonds, vehicles and collectibles carry no accrued gain; inter-spousal transfers are not in the totals | — | same, table note |
| Charitable deduction over gross estate net of bequests to a surviving spouse, by size of gross estate, FY2024 | 4.30% (<$10M) / 6.20% / 12.03% / **36.20%** ($50M+) | IRS SOI *Estate Tax Statistics* Table 1, `24es01fy.xlsx` |
| Bequests to a surviving spouse over gross estate (carried, **not applied**) | 32.9% all returns | same |
| §121 principal-residence exclusion | $250,000 per person | IRC §121(b)(1); FY2022 GB report p. 63, FY2025 GB report p. 81 |
| Per-donor exclusion | $1,000,000 (FY2022) / $5,000,000 (FY2025) | FY2022 GB report p. 63; FY2025 GB report p. 81 |
| Price elasticity of charitable bequests | **−1.617** (spec. (a); (d) is −2.142) | Bakija, Gale & Slemrod (2003), NBER WP 9661, Table 1 |
| Realization elasticity, persistent | 0.72 at a 22% reference rate | Dowd, McClelland & Muthitacharoen (2015); Decision 3 |
| Option 51's text: no exclusion, no deferral, no rate change | — | CBO pub. 60557, report p. 61 |

External cross-check, not an input: PW's own Table 10 scores constructive
realization at death for 1998 at **$4.53B** with no per-decedent exemption but
*with* the §121 residence exclusion — 10.6% of the $42.8B of gains, against the
~20% top statutory rate of the day. Roughly half the naive gains-times-rate
product survives their carve-outs, which is the order of magnitude this lane's
carve-outs should remove.

## 5. Pre-registered expectation

Hand-computed on the shipped ladder before any module code changed, by applying
§3's shares and multipliers to `CapitalGainsBaseline.decedent_classes(2025)` and
scaling the result by each row's measured death channel from §1. The scratch
arithmetic gives a ten-year death channel of **427.0** for Option 51 (from
575.5 on the same hand path), **16.1** for the FY2025 design (from 421.0) and
**52.8** for the FY2022 design (from 730.7); rescaled onto the model's own
457.8 / 802.0 / 581.2 that is roughly −431, −238 and −278 against targets of
−536.1, −288.6 and −322.0.

| Row | before | expected after | why |
|---|--:|---|---|
| `cbo_opt51_gains_at_death` | 8.4% | **12–28%, now under-predicting** | No exclusion, no deferral, no rate response — only the charitable and §121 carve-outs and the substitution channel apply, and they take about a quarter out of the base. **This is a registered regression**: the 8.4% was two errors cancelling, an unreached base counted in full |
| `biden_capital_gains_39` | 134.9% | **5–30%** | Death channel 457.8 → roughly 18, because the $5M exclusion applies *after* a 72.3% deferral and a 56% charitable share at the top; rate channel 220.3 unchanged |
| `treasury_capgains_39_plus_stepup_elim` | 217.5% | **0–28%** | Same shape with a $1M exclusion, so three classes stay in tax; death channel 802.0 → roughly 58 |
| `cbo_opt47_ltcg_qdiv_2pp` | 44.8% | **unchanged** | Keeps step-up; the death channel never runs |
| **Tier 1 mean** | 31.0% | **16–23%** | mass 805.8 → roughly 470–520 |
| **Tier 1 within 25%** | 19 | **20–22** | both Treasury rows enter, Option 51 stays |
| **Tier 1 within 15%** | 13 | **12–14** | Option 51 leaves, at most one Treasury row enters |
| `CapitalGains` LOO (n=3) | 39.6% | **unchanged** | none of the three runs the death channel |
| LOO suite (n=18) | 28.4% | **unchanged** | same |
| calibrated fitted (n=28) | 2.0% | **unchanged** | no fitted annual is touched |
| unfitted reconstruction (n=26) | 61.8% | **unchanged** | its three capital-gains rows are the LOO three |

### 5.1 Shipped output that will move

Tailor's capital-gains form, at the form's own defaults (data year 2024). Only
the two step-up rows have a death channel; the other three are printed so the
falsification test in §6 has something to fail against.

| Tailor input | before |
|---|--:|
| +2pp, all brackets | −$56.4B |
| +5pp, all brackets | −$110.9B |
| +5pp above $1M, step-up retained | −$22.3B |
| 39.6% above $1M + eliminate step-up, $1M exemption | −$1,016.5B |
| constructive realization at death only, no exclusion | −$581.2B |

No preset moves: the only capital-gains-shaped preset,
`📋 Eliminate Step-Up Basis (-$500B)`, runs through `TaxExpenditurePolicy`.

## 6. What would falsify the lane

- Any Tier-1 row other than the three named moving at all. The diff touches the
  death channel, the carve-out data file, and the Green Book design rule in
  `validation/core.py`; nothing else scores through them.
- The `CapitalGains` LOO module, the LOO suite, the fitted tier or the
  reconstruction tier moving by any amount.
- The first three Tailor rows in §5.1 moving.
- `cbo_opt51_gains_at_death` moving past 30%, or either Green Book row failing
  to at least halve.
- The two Green Book rows landing on *opposite* sides of their targets: they
  share a rate channel and differ only in the exclusion, so a design that
  over-predicts one and under-predicts the other has a bug in the exclusion
  ordering rather than a finding about the proposals.

## 7. Where the lane expects to be wrong

- **Option 51 gets worse and the lane accepts it.** Its 8.4% was bought by
  taxing charitable bequests and small decedents' housing gains, neither of
  which any realization-at-death regime reaches. Removing them is right and
  costs the row accuracy, because whatever else is too small in the level is
  now no longer offset.
- **The 72.3% active-business share is an upper bound** on the Green Book's
  "family-owned and -operated", and it is the largest single carve-out. If the
  two Green Book rows now *under*-predict, this is the first place to look.
- **The decedent headcount is unchanged** (§3.4) and is the coarsest thing in
  the channel.
- **The rate on the final return is priced on the class's pre-carve-out gain**,
  not the post-carve-out one, so a decedent whose carve-outs drop them into a
  lower preferential bracket is still priced at the higher rate. Left as it is
  because changing it is a second change to the same line and no scored case
  crosses a bracket boundary because of it.
- **The realizations base is still not projected across the window** (Wave 2's
  §2.6 rule), so the rate channel is flat and this lane does not change that.

## 8. Outturn

*Appended 2026-09-05, after the code. Every number from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix` and
the §5.1 reproduction script, run on the finished branch and on `5deef17` in the
same session, so the before column is measured rather than quoted.*

**The mechanism did what the lane said it would, and the two rows it aimed at
landed inside their bands.** Tier 1 goes **31.0% → 18.5%** and the capital-gains
error mass **405.6 → 81.0**, from 50.3% of the tier to 16.8% of it. Capital
gains is no longer the tier's largest single mass; the two payroll rows are, at
109.6.

### 8.1 Predicted vs actual

| Row | before | §5 said | after | inside? |
|---|--:|---|--:|---|
| `cbo_opt51_gains_at_death` | 8.4% | 12–28%, now under-predicting | **19.3%**, under-predicting | yes |
| `biden_capital_gains_39` | 134.9% | 5–30% | **16.7%** | yes |
| `treasury_capgains_39_plus_stepup_elim` | 217.5% | 0–28% | **0.2%** | yes |
| `cbo_opt47_ltcg_qdiv_2pp` | 44.8% | unchanged | 44.8% | yes |
| Tier 1 mean | 31.0% | 16–23% | **18.5%** | yes |
| Tier 1 within 25% | 19 | 20–22 | **21** | yes |
| Tier 1 within 15% | 13 | 12–14 | **13** | yes |
| `CapitalGains` LOO (n=3) | 39.6% | unchanged | 39.6% | yes |
| LOO suite (n=18) | 28.4% | unchanged | 28.4% | yes |
| calibrated fitted (n=28) | 2.0% | unchanged | 2.0% | yes |
| unfitted reconstruction (n=26) | 61.8% | unchanged | 61.8% | yes |

§5's hand path predicted ten-year death channels of roughly **−431, −238 and
−278** against targets of −536.1, −288.6 and −322.0. The model returns
**−432.8, −240.5 and −322.7**. Two of the three land within a couple of billion
of a number computed before any module code changed; the third is $45B away and
§8.4 is about why.

### 8.2 The three rows, channel by channel

The rate channel and the death channel are separate addends and the behavioural
offset does not scale with the death term, so the split is exact: the rate
column below is unchanged to the decimal on both Green Book rows, before and
after.

| Row | rate channel | death before | death after | total before | total after | target |
|---|--:|--:|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` | 0.0 | 581.2 | **432.8** | −581.2 | **−432.8** | −536.1 |
| `biden_capital_gains_39` | 220.3 | 457.8 | **20.2** | −678.1 | **−240.5** | −288.6 |
| `treasury_capgains_39_plus_stepup_elim` | 220.3 | 802.0 | **102.4** | −1,022.3 | **−322.7** | −322.0 |

Retention of the death channel — actual against the ratio §5's scratch
arithmetic implied:

| Row | §5 hand path | actual |
|---|--:|--:|
| `cbo_opt51_gains_at_death` | 74.2% | **74.5%** |
| `biden_capital_gains_39` | 3.8% | **4.4%** |
| `treasury_capgains_39_plus_stepup_elim` | 7.2% | **12.8%** |

### 8.3 What each carve-out is worth

Ten-year death channel in $B, with one relief switched off at a time. Not
additive — they compose multiplicatively and the per-donor exclusion sits after
all of them — but it says which relief does the work.

| variant | Option 51 | FY2025 ($5M) | FY2022 ($1M) |
|---|--:|--:|--:|
| **full** | **432.8** | **20.2** | **102.4** |
| no carve-outs at all | 581.2 | 457.8 | 802.0 |
| no family-business deferral | 432.8 | 127.9 | 276.3 |
| no per-donor exclusion | 432.8 | 310.8 | 310.8 |
| no §121 | 480.5 | 20.5 | 125.5 |
| no charitable substitution | 451.3 | 33.7 | 121.1 |

Read down the marginal effects: on FY2022 the **per-donor exclusion is worth
208.4 and the family-business deferral 173.9**, then §121 at 23.1 and the
substitution channel at 18.7; on FY2025 the exclusion is worth 290.6 and the
deferral 107.7, then substitution at 13.5 and §121 at 0.3 — because after a $5M
exclusion only the top class is still in tax and its residence share is 3.6%. So
the exclusion the module already had is the largest relief on both rows, and
**the family-business deferral is the largest of the ones this lane added** —
which is what §3.1 warned about, since it is also the one taken at an upper
bound. On Option 51, which states neither, the whole change is charity plus §121
plus the substitution channel — 25.5% of the base.

The rate response at death is `exp(−2.2660 × 0.196)` = **0.6414** on the
decedents the rate change reaches, against the **0.641** §3.2 registered, and
exactly 1.0000 on Option 51, which changes no rate.

### 8.4 Where the pre-registration was wrong

**One falsification test fired, and its diagnosis is not the one it was written
to catch.** §6 said the two Green Book rows landing on *opposite* sides of their
targets would mean "a bug in the exclusion ordering". They do land on opposite
sides — FY2022 over-predicts by **0.2%**, FY2025 under-predicts by **16.7%** —
so the test fires on its literal terms. The ordering is not the cause, and the
evidence is arithmetic rather than assertion:

- The ordering is pinned by
  `test_the_per_donor_exclusion_applies_after_the_carveouts`, and applying the
  exclusion *first* would raise **both** scores, moving them the same way.
- The residual is **monotone in the exclusion**: the larger exclusion
  under-predicts more. A mis-ordered exclusion produces no such ordering.
- The cause is the **five-class ladder**, which §3.4 named as the coarsest thing
  in the channel — but named for the headcount, not for this. After the
  carve-outs and the rate response, gain per decedent is $9.71M in `TopPt1`,
  $1.89M in `RemainingTop1`, $0.92M in `Next9` and $79K in `Next40`. A $1M
  exclusion leaves two classes in tax; a $5M exclusion leaves **one**, knocking
  3,677 decedents × $0.89M out in a single step. The model's exclusion is
  therefore a step function on a schedule with no within-group dispersion:
  moving from $1M to $5M costs it **$82.2B** of death channel where it costs
  Treasury **$33.4B** (−$322.0B vs −$288.6B). That is a *dispersion* defect, and
  it is the first place a later lane should look.

**The FY2022 row's 0.2% is not a measurement of accuracy and must not be quoted
as one.** The lane predicted 0–28%, and predicted 7.2% retention where the model
delivered 12.8%; the row landed on its target because a death channel that came
in nearly twice the hand path's size closed a gap the hand path had left open in
the other direction. The honest statement is the retention ratio: the mechanism
removes **87.2%** of the FY2022 death channel where the pre-registered hand path
said 92.8%.

**§1's rate/death split was right and this lane's first attempt to reproduce it
was not.** Scoring the rate leg by setting `score_gains_at_death=False` returns
216.6, not §1's 220.3, because the lock-in wedge still reads `eliminate_step_up`.
The additive split — total minus the death addend — returns 220.3 on both rows,
before and after, and is the one §8.2 uses.

**Option 51 got worse by 10.9pp, as registered.** §7 said its 8.4% was two errors
cancelling; both halves are now visible. Removing the charitable bequests and the
small decedents' housing gains it had been taxing costs it 25.5% of its base, and
nothing else in the channel grew to replace it.

### 8.5 Falsification checks

| §6 test | result |
|---|---|
| Any Tier-1 row other than the three named moving | **clean** — all 23 others identical to the dollar |
| `CapitalGains` LOO, LOO suite, fitted tier or reconstruction tier moving | **clean** — `run_loo.py --donor-matrix` output byte-identical; both calibrated tiers identical row by row |
| The first three Tailor rows in §5.1 moving | **clean** — −$56.4B / −$110.9B / −$22.3B, unchanged |
| Option 51 past 30%, or either Green Book row failing to halve | **clean** — 19.3%; 134.9 → 16.7 and 217.5 → 0.2 |
| The two Green Book rows on opposite sides | **fired** — see §8.4. Diagnosed as ladder dispersion, not exclusion ordering |

Suite: **3,168 passed, 1 skipped, 1 failed** — the one failure is the CI-threshold meta-test in §8.8, which fires because the battery improved.
Twenty of the passing tests are new (`tests/test_capital_gains_death_channel.py`); no existing test pinned a death-channel level, so none had to be restated.

### 8.6 Shipped output, and the note that ships with it

§5.1's table, reproduced on the finished branch:

| Tailor input | before | after |
|---|--:|--:|
| +2pp, all brackets | −$56.4B | −$56.4B |
| +5pp, all brackets | −$110.9B | −$110.9B |
| +5pp above $1M, step-up retained | −$22.3B | −$22.3B |
| 39.6% above $1M + eliminate step-up, $1M exemption | −$1,016.5B | **−$490.7B** |
| constructive realization at death only, no exclusion | −$581.2B | **−$432.8B** |

No preset moves: `Eliminate Step-Up Basis (-$500B)` scores −$523.5B before and
after, because it runs through `TaxExpenditurePolicy` and never reaches the death
channel.

Two shipped numbers move by 52% and 26%, so **Decision 6 binds** and the note
ships in the same PR — `gains_at_death_caption` in
`fiscal_model/ui/tabs/results_summary.py`, alongside the spend-out and tariff
notes, computed by replaying the scorer's own death-channel loop so it cannot
drift from the figure above it:

> Gains at death: $−432.8B of the static score above is constructive realization
> at death — Poterba & Weisbenner's flow of unrealized gain transferred by
> decedents, indexed to household net worth. It is not the whole flow: bequests
> to charity and the $250,000 section 121 exclusion on a principal residence come
> out first. This design states no per-decedent exclusion. Inter-spousal
> transfers and tangible personal property are already outside that flow, so
> neither is deducted twice.

That file is outside §3's list, and it is the only one: it is there because
Decision 6 requires it, and the addition is one function plus one call site.

### 8.7 Findings

**1 — Two of the six stated reliefs remove nothing, and deducting them would have
been the error.** This is the finding §3.1 predicted, and it survived contact.
Poterba & Weisbenner's Table 8 note excludes inter-spousal transfers from the
estate totals and assigns no accrued gain to bonds, vehicles or collectibles, so
the spousal and tangible-personal-property carve-outs are already in the base.
SOI puts bequests to a surviving spouse at **34.7%** of the gross estate in the
top class; deducting it again would have removed a third of the channel for
nothing. The column is in the CSV, marked *carried and never applied*, and
`test_the_spousal_share_is_carried_and_never_read` pins that the loader does not
hand it to the model. **A relief a proposal states is not the same as a relief a
base contains**, and the only way to tell is to read the note under the table the
base comes from.

**2 — The largest carve-out this lane added has the weakest measurement.** The
family-owned-business deferral is worth $173.9B on the FY2022 row and $107.7B on
FY2025 — the same order as the per-donor exclusions the module already had
($208.4B and $290.6B) — and it is applied at Poterba &
Weisbenner's *active business and farm* share, 72.3% at $10M+, which is an upper
bound on "family-owned and -operated". No published split of active-participant
businesses into family-operated and not exists. The lane took the share whole and
said so rather than inventing a haircut, and the consequence is that the FY2025
row's 16.7% under-prediction has an obvious first suspect.

**3 — The exclusion is a step function because the ladder has five rungs.** §8.4
has the arithmetic. The pre-registration named the decedent *headcount* as the
ladder's coarsest feature; the binding one turned out to be the absence of
*within-group dispersion*, which is what makes a per-donor exclusion behave like
a cliff. Nothing here fixes it, and the two Green Book rows landing on opposite
sides of their targets is its signature.

**4 — The behavioural response is real but small, and it is not what closed the
rows.** `exp(−b·Δτ)` = 0.641 on the reached decedents and 1.000 on Option 51; the
charitable substitution channel is worth $18.5B on Option 51, $13.5B on FY2025
and $18.7B on FY2022 — single digits as a share. The carve-outs did the work.
§6.2 item 14 asked for "L1's death-channel behavioural response" and gets one,
but a reader should not conclude that a missing elasticity was the residual: a
missing *statute* was.

**5 — The frozen elasticity was the smallest available and the lane did not touch
it.** `charitable_bequest_price_elasticity` is Bakija, Gale & Slemrod
specification (a), 1.617, the smallest magnitude in their own Table 1; (d) is
2.142 and would move both over-predicting rows further in this lane's direction.
`test_a_bigger_price_elasticity_gives_a_bigger_response` pins that the larger
value collects less, so the choice is visible in a test rather than buried in a
default. Nothing in §3.1 or §3.2 was selected against a target.

**6 — The one design switch keys on the publisher and is pinned twice.**
`GREEN_BOOK_DEATH_DESIGN_RULE` selects the family-business deferral by
`ScoreSource.TREASURY`, and
`test_the_green_book_design_rule_keys_on_the_document` asserts the alternative
key picks the same rows, so the rule cannot quietly become a per-row switch. One
correction the pre-registration needed: the FY2022 record leaves
`step_up_exemption` unset and inherits the module default, so the alternative key
is "not stated as zero" rather than "positive".

### 8.8 What the lane did not do

- **The 15-year installment election** (relief 6) is still not modelled — §3.4
  said so in advance. It is a within-window timing effect on the non-liquid,
  non-deferred share and no share of it is separately measurable in Table 8. It
  would move both Green Book rows further down, i.e. FY2022 off its target and
  FY2025 further from its.
- **The estate-tax deduction** for capital gains tax paid at death, stated by both
  Green Books *and* by Option 51, is still an estate-tax interaction the
  capital-gains module does not have.
- **The decedent headcount is unchanged** — 408,533 a year from a *dollar* flow
  rate used as a headcount rate, against roughly 3 million actual deaths.
- **The rate on the final return is still read off the pre-carve-out gain**, so a
  decedent whose reliefs drop them into a lower preferential bracket is priced at
  the higher one. No scored case crosses a boundary because of it.
- **The realizations base is still not projected across the window** (Wave 2
  §2.6), so the rate channel is flat.
- **No target moved and no constant was retuned.** `preregistered.py`,
  `holdout.py`, `loo.py`, `target_revisions.py`, `KNOWN_SCORES` and
  `CBO_SCORE_MAP` are untouched; the two Green Book rows are scored against the
  same figures they carried on `5deef17`.
- **The CI gate's ceiling was not re-derived, and it now needs to be.**
  `tests/test_ci_workflow.py::test_cold_holdout_gate_thresholds_match_the_live_battery`
  asserts the workflow's `--max-mean-error` is no more than twice the live mean;
  at 18.5% the standing 40 is 2.16×, so that test **fails on this branch**. It is
  the test's designed signal, not a regression — the gate itself still passes
  (`--max-mean-error 40 --min-within-25pct 18`, exit 0). By the workflow's own
  rule the re-derivation would be `ceil(18.5 × 1.25) = 24` and `21 − 1 = 20`,
  **but it should be done once after every Wave 4 lane lands**, not per lane:
  three other lanes are moving the same battery concurrently and a ceiling
  derived from one lane's mean would be wrong the moment the next one merges.
  Left for the owner.
