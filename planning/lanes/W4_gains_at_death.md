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

*Appended by the lane's last commit.*
