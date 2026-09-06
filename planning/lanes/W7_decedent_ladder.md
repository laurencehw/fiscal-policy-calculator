# W7 — The decedent ladder: a size distribution instead of five point masses

*Wave 7 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §6.2,
item 15 — the one carry-over Wave 4's own falsification test left open.
Pre-registered 2026-09-06 against `main` @ `a251b32`, **before** any code in this
lane changed. The outturn is appended at the bottom as the lane's last commit.*

Wave 4 (`W4_gains_at_death.md`) gave the death channel the six reliefs a
realization-at-death proposal states, and its §6 falsification test fired: the
two Green Book rows landed on opposite sides of their targets. §8.4 diagnosed
that as the **five-class decedent ladder** — a schedule with no within-group
dispersion, on which a per-donor exclusion is a step function. Moving the
exclusion from $1M to $5M knocks 3,677 decedents × $0.89M out in one step, so it
costs the model **$82.2B** of death channel where Treasury's own two rows differ
by **$33.4B**. §6.2 item 15 carries that as "the first place a later
capital-gains lane should look". This lane looks.

Nothing below is a promise of attainment (§1.5 forbids that), and this lane
expects to move all three of its rows **the wrong way**. Every number in §5 was
computed by hand from the shipped data files *before* a line of module code
changed, in a scratch script that fits the distribution and replays the death
channel on it — and the same script reproduces the shipped five-atom answer to
the cent (432.75 / 20.19 / 102.45 against the module's 432.7511 / 20.1883 /
102.4472), which is what makes the continuous figures beside them worth reading.

## 1. Starting point (measured on `a251b32`)

`python scripts/cold_holdout.py --json`:

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| out-of-sample (Tier 1) | 26 | **15.2%** | 11.4% | 16 | 22 |
| calibrated reference (fitted) | 21 | 1.7% | 0.0% | 21 | 21 |
| uncalibrated reconstruction | 34 | 57.6% | 34.2% | 9 | 13 |

`python scripts/run_loo.py --donor-matrix`: 18 derivable, **29.6%** mean, 19.1%
median, 8/18 within 15%, 4 not cross-validatable. The `CapitalGains` module is
**39.6%** (n=3) and **none of its three cases runs the death channel** —
`cbo_2pp_all_brackets` and `pwbm_39_with_stepup` set `eliminate_step_up=False`
and `pwbm_39_no_stepup` sets `score_gains_at_death=False`
(`validation/scenarios.py:81, :103, :134`). So this lane predicts the module and
the donor matrix are **untouched**, and any movement is a falsification (§6).

The four capital-gains Tier-1 rows, and the three the lane touches decomposed by
the additive split W4 §8.2 used — total minus the death addend, because the
death channel is a separate term in `scoring_engine._score_tax_policy_year`:

| policy_id | rate channel | death channel | model | official | abs err |
|---|--:|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` | 0.00 | **432.75** | −432.75 | −536.1 | 19.3% |
| `biden_capital_gains_39` (FY2025 GB, $5M) | 359.02 | **20.19** | −379.21 | −288.6 | 31.4% |
| `treasury_capgains_39_plus_stepup_elim` (FY2022 GB, $1M) | 359.02 | **102.45** | −461.47 | −322.0 | 43.3% |
| `cbo_opt47_ltcg_qdiv_2pp` | 92.5 | — | −92.5 | −103.3 | 10.5% |

Two facts about that table govern everything this lane can do.

**The rate channel alone over-shoots both Green Book targets.** Wave 5 (PR #116)
projected the realizations base across the window and took the shared rate
channel from 220.3 to **359.02**. Against −288.6 and −322.0 that is 24.4% and
11.5% over *with the death channel set to zero*. So **no change to the death
channel can bring either Green Book row to its target**, and the best either can
do is lose less. Wave 5 registered that as its own cost; this lane inherits it
and does not open the rate channel (`W5_preferential_margin.md`).

**About 17 of the FY2022 row's 43 points are a window offset** the manifest
states rather than the model produces (§6.2 item 24): its target is Treasury's
FY2022–2031 row on a 2021 baseline and the record states no
`effective_start_year`, so the model scores FY2025–2034. A separate memo lane
owns that question. This lane touches no target and no `preregistered.py` row.

The three capital-gains reconstruction rows, which must not move:
`cbo_2pp_all_brackets` −70.0 vs −79.8 (14.0%), `pwbm_39_with_stepup` +33.0 vs
+23.6 (28.4%), `pwbm_39_no_stepup` −113.0 vs −26.6 (76.5%). The fitted row
`eliminate_step_up` (−500.0 vs −523.5, 4.7%) runs through
`TaxExpenditurePolicy` and never reaches this channel.

## 2. What the ladder is today

`CapitalGainsBaseline.decedent_classes` (`fiscal_model/data/capital_gains.py`)
returns **five** point masses. Decedents are households × the DFA percentile
group's population share × `estate_flow_rate`; gains are Poterba & Weisbenner's
flow of unrealized gain at death, split across the five groups in proportion to
`group net worth × unrealized_gain_share(group mean)`; and each group carries the
three carve-out shares a realization-at-death proposal reaches, read off
`decedent_carveout_shares.csv` at that group's **mean** estate.

| group | decedents/yr | mean estate | gain per decedent | $B of gain |
|---|--:|--:|--:|--:|
| TopPt1 | 409 | $176.92M | $119,586,480 | 48.85 |
| RemainingTop1 | 3,677 | $23.83M | $12,470,188 | 45.85 |
| Next9 | 36,768 | $5.10M | $2,042,061 | 75.08 |
| Next40 | 163,413 | $0.948M | $149,409 | 24.42 |
| Bottom50 | 204,266 | $0.062M | $9,825 | 2.01 |

Its sources, all already vendored with provenance headers and all regenerable by
`python scripts/build_capital_gains_data.py`:

- **`decedent_estate_ladder.csv`** — Federal Reserve *Distributional Financial
  Accounts* (the Z.1 companion), household net worth by percentile group at
  2024:Q4, with household counts from the DFA aggregate over SCF 2022 mean
  family net worth. Its own header already says the thing this lane is about:
  *"mean_net_worth_millions_usd is a group mean and carries no within-group
  dispersion."*
- **`agm_unrealized_gain_share_by_estate_size.csv`** — Avery, Grodzicki & Moore
  (Federal Reserve FEDS 2013-28) Figure 1, "Current Law": unrealized capital gain
  as a share of the gross estate, in **eight** bands from $0 to $100M+.
- **`decedent_carveout_shares.csv`** — Poterba & Weisbenner (2001) Table 8's
  lower panel (residence and active-business shares of unrealized gain, in
  **six** net-worth classes) and IRS SOI *Estate Tax Statistics* Table 1, filing
  year 2024 (charitable deduction over the gross estate net of spousal bequests,
  in **four** size classes), each matched to a ladder class by that class's mean
  estate. Plus the marital share, carried and never applied, and the
  tangible-personal-property share, zero — both because Poterba & Weisbenner's
  own table note puts them outside the base (W4 finding 1).
- **`accrued_gains_parameters.csv`** — the level: PW's $42.8B of gains at death
  over 1998 household net worth, grown with the DFA stock.

**The ladder is coarser than every source it reads, and the arithmetic of that is
checkable rather than rhetorical.** With five class means at $176.92M / $23.83M /
$5.10M / $0.948M / $0.062M:

| step function | published rows | rows the five means ever evaluate | dead rows |
|---|--:|--:|--:|
| AGM Figure 1 (gain share of estate) | 8 | 4 (0.128, 0.325, 0.425, 0.549) | **4** |
| PW Table 8 (residence, active business) | 6 | 4 (0, 0.50, 5.0, 10.0) | **2** |
| SOI Estate Table 1 (charitable) | 4 | 3 (<$10M, $20–50M, $50M+) | **1** |

Seven published rows out of eighteen are never evaluated by any scored case,
including the whole $1M–$5M band of PW's table — which is exactly the range the
two Green Books' per-donor exclusions sit in.

## 3. The mechanism this lane adds

**A piecewise-Pareto size distribution of net worth at death, fitted to the DFA's
own percentile-group aggregates, with the three published step functions
evaluated at each estate's own size and the per-donor exclusion applied
pointwise.** The level is untouched: total gains at death stays Poterba &
Weisbenner's flow, exactly as today. Only the *shape* changes.

### 3.1 The fit

The DFA gives, for each cumulative population share `p ∈ {0.001, 0.01, 0.10}`,
the aggregate net worth above it. For a Pareto segment anchored at a threshold
`x_lo` at survival probability `s_lo` with `β = 1 − 1/α`, wealth in the segment
down to `s_hi` is

```
W_seg = N · x_lo · s_lo · (r^β − 1) / β        r = s_hi / s_lo
x_hi  = x_lo · r^(β−1)
```

so one equation in one unknown per segment, solved so that **each DFA group's own
aggregate is reproduced exactly**. The open-ended top class takes the index of
the class below it — which is not a new convention but the one
`CapitalGainsBaseline.pareto_tail_index` already applies to SOI's open-ended top
AGI class two hundred lines above. With that closure the top region collapses to
one Pareto over `s ≤ 0.01` and `β = ln(1 + W₂/W₁)/ln(10)`, and the fitted
thresholds are:

| region | β | α | threshold |
|---|--:|--:|--:|
| `s ≤ 0.01` (top 1%) | 0.344848 | 1.5264 | x(99.9th) = **$61.01M**, x(99th) = **$13.50M** |
| `0.01 < s ≤ 0.10` | 0.319727 | 1.4700 | x(90th) = **$2.818M** |
| `0.10 < s ≤ 0.50` | **−0.229560** | **0.8133** | x(50th) = $0.3895M |

**The fit refuses to extend below the 90th percentile, and says so twice.** The
third region's index comes back **below 1** — a Pareto with no finite mean, which
is what "these aggregates are not a tail" looks like in arithmetic — and the
threshold it implies for the 50th percentile is **$389,500** against the Survey
of Consumer Finances' published 2022 median family net worth of **$192,700**,
which is 2.0× out. So the two groups below the top decile **keep their group
means**, exactly as today, and the lane records the refusal rather than shipping
a shape that fails its own check. They hold 12.4% and 1.0% of gains at death;
leaving them as atoms holds the death channel *down*, which is the conservative
direction for Option 51, the one row of the three that under-predicts.

### 3.2 What the distribution is evaluated on

Within the top decile the distribution is integrated by quantile bins, geometric
in survival probability, each represented by its **analytic conditional mean**
under the fitted Pareto, with the published wealth breakpoints of all three step
functions forced in as bin edges so no bin straddles a boundary. The open top bin
is closed analytically (`x·α/(α−1)`), so the population and the aggregate wealth
are exact for any bin count. Bin boundaries are a **numerical resolution**, not a
modelling choice: a convergence test pins that doubling the count moves the
ten-year death channel by less than half a percent, and the shipped count is 200
per region.

Each bin then reads, at its own estate size rather than at a group mean:

- **AGM Figure 1** for the unrealized-gain share of that estate, which is what
  distributes PW's flow across the bins (weights `w · agm(w)`, renormalised to
  PW's total so the level is unchanged);
- **PW Table 8** for the residence and active-business shares §121 and the
  family-business deferral reach;
- **SOI Estate Table 1** for the charitable share, under the same $1,000,000
  floor rule the module already applies, because SOI's table is estate-tax filers
  only.

The carve-out order is **unchanged** — charity, then the family-business
deferral, then §121, then the rate response, and the per-donor exclusion after
all of them, which `test_the_per_donor_exclusion_applies_after_the_carveouts`
already pins. The decedent **headcount** is unchanged, and so is the uniform
death rate across wealth groups: both are §6.2 item 15's "related and smaller"
notes, not this lane's mechanism, and §7 measures them instead.

### 3.3 One published row has to be transcribed

SOI Estate Table 1's **$10M–$20M** class carries a charitable share of **6.20%**
and appears nowhere in the tree, because no ladder class mean falls in that band.
It is `2,487,098 / (55,252,297 − 15,128,678)` from the filing-year-2024 workbook,
the same three columns the build script already reads for the other three
classes. Transcribing it is the only new *published quantity* this lane adds;
everything else is a re-reading of rows already vendored.

## 4. Data transcribed

Two files change and one is retired, all emitted by
`python scripts/build_capital_gains_data.py`.

| File | What | Source |
|---|---|---|
| **new** `decedent_size_distribution.csv` | the fitted piecewise-Pareto: per region, the DFA percentile bounds, aggregate net worth, β, α, and the fitted wealth threshold; plus the region the fit refuses and why | Federal Reserve *Distributional Financial Accounts* (Z.1 companion), net-worth levels by percentile group, 2024:Q4; SCF 2022 historical tables for the median cross-check |
| **new** `decedent_carveout_ladders.csv` | the three step functions on **their own published boundaries** instead of matched to five group means — 6 PW rows, 4 SOI rows, and the marital column carried and never applied | Poterba & Weisbenner (2001) Table 8 lower panel; IRS SOI *Estate Tax Statistics* Table 1, filing year 2024 (`24es01fy.xlsx`), columns 2 / 68 / 70, rows 9–12 |
| **retired** `decedent_carveout_shares.csv` | the five-class collapse this lane removes. Its content survives, un-collapsed, in the ladder file | — |

External checks, computed and reported, never inputs:

- **SOI's own decedent count.** The fitted distribution puts **4,352** decedents a
  year above $12.92M of net worth; SOI's filing-year-2024 Table 1 reports
  **7,195** returns above the $12.92M threshold for 2023 decedents. The
  distribution is short by 1.65× at the top, against a total decedent count that
  is short by 7.6× (408,532 against roughly 3.09 million NCHS deaths) — so the
  two coarsenesses partly offset, and the top of the ladder is much closer to the
  published record than the headcount is.
- **SOI's own Pareto index.** Fitting the same shape to SOI's *decedent* estates
  (2,979 returns above $20M, 825 above $50M, filing year 2024) gives **α =
  1.401** against the DFA's 1.526 over the same range: the estates of the dead
  have a fatter tail than the wealth of the living, which is what mortality
  selection should do. The lane uses the DFA — the source the accrued-gains stock
  already reads, so the level and the shape come from one document — and reports
  SOI's index as the alternative it did not take.
- **SCF 2022 median family net worth, $192,700**, which is what makes the
  third region's fit a refusal rather than a judgement call.

## 5. Pre-registered expectation

Hand-computed before any module code changed. The scratch path reproduces the
shipped five-atom answer exactly, so the continuous column is a like-for-like
substitution of the schedule and nothing else.

| Row | before | expected after | why |
|---|--:|---|---|
| `cbo_opt51_gains_at_death` | 19.3% | **19–22%, still under-predicting** | death channel 432.8 → about 427.5. Dispersion pushes gains up the distribution, where the charitable share is 36% rather than 4%, and that very nearly cancels the Jensen gain a convex §121 deduction produces. **A registered regression** |
| `biden_capital_gains_39` | 31.4% | **31–35%, still over-predicting** | death channel 20.2 → about 24.2. With dispersion the top of `RemainingTop1` clears a $5M exclusion that its class mean ($1.89M after reliefs) never did. **A registered regression** |
| `treasury_capgains_39_plus_stepup_elim` | 43.3% | **43–48%, still over-predicting** | death channel 102.4 → about 109.3. Same mechanism at $1M: `Next9`'s post-relief $0.92M sits just under the exclusion and contributes nothing today; part of it now clears. **A registered regression** |
| `cbo_opt47_ltcg_qdiv_2pp` | 10.5% | **unchanged** | keeps step-up; the death channel never runs |
| **Tier 1 mean** | 15.2% | **15.0–16.0%** | mass 395.1 → about 400 |
| **Tier 1 within 25%** | 22 | **22** | the two rows that leave 25% already left it |
| **Tier 1 within 15%** | 16 | **16** | Option 51 was already outside |
| `CapitalGains` LOO (n=3) | 39.6% | **unchanged** | none of the three runs the death channel |
| LOO suite (n=18) | 29.6% | **unchanged** | same; `--donor-matrix` byte-identical |
| calibrated fitted (n=21) | 1.7% | **unchanged** | no fitted annual is touched |
| unfitted reconstruction (n=34) | 57.6% | **unchanged** | its three capital-gains rows are the LOO three |

**The lane expects to make its three rows worse and is registering that in
advance.** It is worth it for three reasons, none of which is an error
percentage: seven published rows out of eighteen stop being dead; the exclusion
stops being a cliff, which is the defect item 15 names; and the arithmetic in
§5.2 is only available once the schedule can be varied.

### 5.1 The number item 15 is actually about

| quantity | before | expected after | Treasury's printed step |
|---|--:|--:|--:|
| death channel at a $1M exclusion minus at $5M | **82.26** | about **85.0** | **33.40** |

**The lane predicts the step gets slightly *bigger*, not smaller** — which, if it
holds, means the five-class ladder is not what makes the model's exclusion
expensive, and §6.2 item 15's headline arithmetic does not survive contact with
the mechanism it blames. §7 says where the lane thinks the step really comes
from, and the outturn will report the measurement either way.

### 5.2 Shipped output that will move

Tailor's capital-gains form at its own defaults (data year 2024). The first three
rows have no death channel and are printed so §6 has something to fail against.

| Tailor input | before |
|---|--:|
| +2pp, all brackets | −$91.4B |
| +5pp, all brackets | −$183.7B |
| +5pp above $1M, step-up retained | −$46.9B |
| 39.6% above $1M + eliminate step-up, $1M exemption | −$626.9B |
| constructive realization at death only, no exclusion | −$432.8B |

Both step-up rows are expected to move by under 10%, so the lane does **not**
expect Decision 6 to bind the way it did in Wave 4 (52% and 26%) or Wave 5. The
existing `gains_at_death_caption` in `fiscal_model/ui/tabs/results_summary.py`
already names the three reliefs and the ordering, and none of that changes; if
the shipped figure moves enough to need a word about the schedule, the caption
gets it in its own commit.

No preset is expected to move. All 53 are scored before and after through the
API's own `_build_preset_policy`; the only capital-gains-shaped one,
`📋 Eliminate Step-Up Basis (-$500B)`, runs through `TaxExpenditurePolicy`.

## 6. What would falsify the lane

- Any Tier-1 row other than the three named moving at all.
- The `CapitalGains` LOO module, the LOO suite, the fitted tier or the
  reconstruction tier moving by any amount, or `run_loo.py --donor-matrix`
  differing by a byte.
- The first three Tailor rows in §5.2 moving, or any of the 53 presets moving.
- Any of the three rows landing outside its §5 band, or any of them changing
  **sign** or moving by more than 25% of its death channel.
- The fitted distribution failing to reproduce a DFA group aggregate, or the
  total gains at death differing from `gains_at_death_billions` — the level is
  not this lane's to change, and
  `test_decedent_classes_apply_an_exemption_per_decedent` already pins it.
- The ten-year death channel moving by more than 0.5% when the bin count is
  doubled: the bins are quadrature, and a result that depends on them is a
  parameter this lane did not declare.
- **Restated from W4 §6, and now weaker than it was**: the two Green Book rows
  landing on *opposite* sides of their targets. They currently sit on the *same*
  side because Wave 5's rate channel over-shoots both, so this test can no longer
  fail for the reason it was written; §5.1's step is the sharp version of it and
  is the one to read.

## 7. Where the lane expects to be wrong

- **The headcount, not the size classes, is what makes the exclusion expensive.**
  The scratch path can multiply the decedent count while holding the gains total
  fixed, and the $1M→$5M step falls **85.0 → 35.5 → 17.2** as the count doubles
  and doubles again. Treasury's printed step is 33.4. So a decedent count roughly
  twice the shipped one reproduces the published step, and no amount of
  within-group dispersion does. The count is `households × household_share ×
  estate_flow_rate`, where `estate_flow_rate` is Poterba & Weisbenner's **dollar**
  flow of estates over net worth used as a **headcount** rate — 0.32% a year
  against roughly 2.4% of households. The module even carries a second,
  independently derived quantity of the same kind,
  `mortality_weighted_net_worth_share` at 2.65%, computed from NCHS mortality
  against DFA net worth by age, and does not use it here. **This lane does not
  touch any of that**: it is a level change, it moves Option 51 as well as the two
  Green Book rows, and §6.2 files it separately. The measurement is the hand-off.
- **The window makes the $33.4B comparison unsound in the first place.** The two
  Treasury rows are scored on different windows on different baselines, and the
  model's own death channel is **0.71×** as large on FY2022–2031 as on
  FY2025–2034. Any restatement of the FY2022 row onto a common window makes it
  *larger*, and therefore makes Treasury's own exclusion step larger than $33.4B.
  Item 24's memo lane owns the target question and this lane will not pre-empt
  it, but the outturn will report the ratio, because comparing a $1M design on
  one window with a $5M design on another and attributing the difference to the
  exclusion is what produced item 15's number.
- **The DFA is the wealth of the living, and the base is the estates of the
  dead.** SOI's own decedent distribution is the right universe and has a fatter
  tail (α 1.401 against 1.526), but it observes only estates above the filing
  threshold and its level would have to be spliced onto the DFA's anyway. The
  lane takes the DFA whole rather than mixing two universes, and names this as
  the first place to look if the top of the distribution is wrong.
- **Mortality is uniform in wealth here and is not in life.** The wealthy are
  older and die at a higher rate, so the true decedent distribution is shifted up
  relative to the living one this lane fits. The DFA publishes net worth by age
  and by percentile group but not jointly, so the correction is not available
  from the source the level comes from.
- **The rate on the final return is still read off the pre-carve-out gain**, the
  realizations base is still a flow off a stock rather than CBO's own published
  projection, and the 72.3% active-business share is still an upper bound on
  "family-owned and -operated" — all three carried unchanged from W4 §7.

## 8. Outturn

*Appended 2026-09-06, after the code. Every number from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix`,
`python scripts/run_validation_dashboard.py` and the §5.2 reproduction scripts,
run on the finished branch and on `a251b32` in the same session, so the before
column is measured rather than quoted.*

**The mechanism landed where §5 said it would, to two decimal places, and it did
not fix what item 15 said it would fix.** Every one of the twelve bands in §5 was
hit. Tier 1 goes **15.2% → 15.4%**, all three of the lane's rows get worse by
1–2 points, and the exclusion step the lane was aimed at went **82.3 → 85.0**,
the wrong way — which is the finding, and it is a finding about the carry-over
item rather than about the model.

### 8.1 Predicted vs actual

| Row | before | §5 said | after | inside? |
|---|--:|---|--:|---|
| `cbo_opt51_gains_at_death` | 19.3% | 19–22%, still under | **20.3%**, still under | yes |
| `biden_capital_gains_39` | 31.4% | 31–35%, still over | **32.8%**, still over | yes |
| `treasury_capgains_39_plus_stepup_elim` | 43.3% | 43–48%, still over | **45.4%**, still over | yes |
| `cbo_opt47_ltcg_qdiv_2pp` | 10.5% | unchanged | 10.5% | yes |
| Tier 1 mean | 15.2% | 15.0–16.0% | **15.4%** | yes |
| Tier 1 within 25% | 22 | 22 | **22** | yes |
| Tier 1 within 15% | 16 | 16 | **16** | yes |
| `CapitalGains` LOO (n=3) | 39.6% | unchanged | 39.6% | yes |
| LOO suite (n=18) | 29.6% | unchanged | 29.6% | yes |
| calibrated fitted (n=21) | 1.7% | unchanged | 1.7% | yes |
| unfitted reconstruction (n=34) | 57.6% | unchanged | 57.6% | yes |
| **exclusion step, $1M less $5M** | 82.26 | **about 85.0** | **85.02** | yes |

§5's hand path — written before a line of module code changed — predicted
ten-year death channels of about **427.5, 24.2 and 109.3**. The module returns
**427.53, 24.23 and 109.24**. The hand path and the implementation are the same
arithmetic, which is what makes the pre-registration worth having: nothing was
adjusted between writing the prediction and reading the result.

### 8.2 The three rows, channel by channel

| Row | rate channel | death before | death after | total before | total after | target |
|---|--:|--:|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` | 0.00 | 432.75 | **427.53** | −432.75 | **−427.53** | −536.1 |
| `biden_capital_gains_39` | 359.02 | 20.19 | **24.23** | −379.21 | **−383.25** | −288.6 |
| `treasury_capgains_39_plus_stepup_elim` | 359.02 | 102.45 | **109.24** | −461.47 | **−468.26** | −322.0 |

The rate channel is unchanged to the cent on both Green Book rows, before and
after. Wave 5's `W5_preferential_margin.md` is untouched.

### 8.3 What the distribution is worth, and what it is not

Ten-year death channel with one relief switched off at a time. Not additive —
they compose multiplicatively and the per-donor exclusion sits after all of
them — but it says which relief does the work now that each is read at the
estate's own size.

| variant | Option 51 | FY2025 ($5M) | FY2022 ($1M) |
|---|--:|--:|--:|
| **full** | **427.53** | **24.23** | **109.24** |
| no carve-outs at all | 580.97 | 485.67 | 794.54 |
| no family-business deferral | 427.53 | 131.08 | 292.71 |
| no per-donor exclusion | 427.53 | 289.03 | 289.03 |
| no section 121 | 478.14 | 24.83 | 123.50 |
| no charitable substitution | 445.95 | 38.53 | 127.18 |

Read down the marginal effects and one of W4's orderings has flipped. On FY2025
the per-donor exclusion is still the largest relief at **264.8**, with the
family-business deferral at 106.9, §121 at 0.6 and the substitution channel at
14.3. On **FY2022 the deferral is now the largest at 183.5**, against the
exclusion's 179.8 — on the five-class ladder the exclusion led, 208.4 to 173.9 —
because a $1M exclusion applied across a distribution wastes less of itself on
decedents who fall just under it. That is the one ordering this lane changed,
and it is a consequence of the mechanism rather than a finding about the
proposals. On Option 51, which states neither relief, the whole change is charity
plus §121 plus the substitution channel — **26.4%** of the base, against 25.5% on
the old ladder.

The quadrature is stable, which is what makes the slice count a resolution
rather than a parameter:

| slices/region | slices | Option 51 | FY2025 | FY2022 |
|---|--:|--:|--:|--:|
| 25 | 84 | 427.5254 | 24.2099 | 109.2343 |
| 200 (shipped) | 609 | 427.5277 | 24.2283 | 109.2433 |
| 800 | 2,409 | 427.5277 | 24.2286 | 109.2436 |

Thirty-two-fold more slices moves the FY2022 channel by **$0.009B**, 0.009%.

Six of the seven dead published rows are alive:

| step function | published classes | evaluated before | evaluated now | still dark |
|---|--:|--:|--:|---|
| Poterba & Weisbenner Table 8 | 6 | 4 | **5** | $0.25M–$0.5M |
| Avery, Grodzicki & Moore Figure 1 | 8 | 4 | **8** | — |
| SOI Estate Table 1 (charitable) | 4 | 3 | **4** | — |

The one still dark sits inside the region the fit refuses, between the two group
means that survive there. Saying which row is unread is better than claiming all
eighteen.

One §3.1 figure moved with the schedule that produced it, and is restated here
rather than edited there: the two groups the fit refuses hold **13.1% and 1.1%**
of gains at death after the change, against the 12.4% and 1.0% measured on the
five-class ladder before it. The groups the fit declines to disperse are still
the two that matter least to the channel.

### 8.4 Where the pre-registration was wrong — and where §6.2 item 15 was

**No band was missed, so nothing in §5 was wrong.** What was wrong is the
carry-over item the lane was sent to close, and the lane says so with arithmetic
rather than assertion.

**§6.2 item 15 attributes the exclusion step to the ladder's lack of
within-group dispersion. It is not that.** Wave 4 measured the model paying
**$82.2B** of death channel to move the per-donor exclusion from $1M to $5M,
against $33.4B between Treasury's two published rows, and named the five-class
ladder. This lane replaced the ladder with a fitted, continuous size
distribution and the step went to **$85.0B** — *further* from $33.4B, not
nearer. Dispersion cannot have been the cause, and the direction is not an
accident: `max(0, gain − E)` is convex in the gain, so a mean-preserving spread
of a fixed flow of gains raises the taxable excess at every exclusion. **A
sharper schedule makes an exclusion cost more, not less.**

**What does move it is the decedent headcount, and the sensitivity is not
subtle.** Holding gains at death at Poterba & Weisbenner's flow and varying only
the number of decedents it is spread over:

| decedents | Option 51 | FY2025 | FY2022 | **step** |
|---|--:|--:|--:|--:|
| 408,532 (shipped) | 427.53 | 24.23 | 109.24 | **85.02** |
| ×1.5 | 413.88 | 18.22 | 71.34 | **53.11** |
| ×2 | 406.83 | 15.58 | 51.05 | **35.46** |
| ×4 | 383.99 | 10.88 | 28.13 | **17.25** |
| ×7.56 (≈ NCHS deaths) | 349.02 | 7.78 | 17.73 | **9.94** |

A decedent count about **twice** the shipped one reproduces Treasury's own step
to within two billion. The shipped count is `households × household_share ×
estate_flow_rate`, where `estate_flow_rate` is Poterba & Weisbenner's **dollar**
flow of estates over net worth (0.3195%/yr) used as a **headcount** rate, giving
408,532 decedents against roughly 3.09 million NCHS deaths — and the module
carries a second, independently derived quantity of exactly that kind,
`mortality_weighted_net_worth_share` at **2.65%**, computed from NCHS mortality
against DFA net worth by age, which it does not use here. **This lane did not
touch it**, because it is a level change to the whole channel (it moves Option
51 too, and in the wrong direction) and §6.2 files it separately. The
measurement is the hand-off.

**And the $33.4B was never the right comparator.** The two Treasury rows are
scored on different windows on different baselines. The model's own death
channel is **0.714×** as large on FY2022–2031 as on FY2025–2034 for the $1M
design (0.744× for the $5M one), so restating the FY2022 row onto a common
window makes it larger and makes the published step larger than $33.4B. Item
24's memo lane owns the target question and this lane does not pre-empt it, but
the number item 15 quotes is a difference between two windows as well as between
two exclusions.

**One thing the lane found that it did not predict**: the module's implied
decedent count *at the top* is much closer to the published record than its total
is. The fitted distribution puts **4,378** decedents a year above $12.92M of net
worth against SOI's **7,194** estate-tax returns above that threshold — short by
1.6×, where the headcount overall is short by 7.6×. So the two coarsenesses
partly offset, and a headcount fix that simply scaled every group would overshoot
at the top. Whoever takes item 15's headcount half should start there.

### 8.5 Falsification checks

| §6 test | result |
|---|---|
| Any Tier-1 row other than the three named moving | **clean** — 23 of 26 identical to the dollar |
| `CapitalGains` LOO, LOO suite, fitted tier or reconstruction tier moving | **clean** — 0 of 21 and 0 of 34 scorecard rows moved; `run_loo.py --donor-matrix` identical line for line |
| The first three Tailor rows moving, or any of the 53 presets moving | **clean** — −$91.4B / −$183.7B / −$46.9B unchanged; all 53 presets identical to four decimals |
| Any row outside its §5 band, or changing sign, or moving >25% of its death channel | **clean** — largest death-channel move is +20.0% (FY2025), no sign change |
| The fit failing to reproduce a DFA group aggregate, or the level moving | **clean** — every group to 1e-9, total gains at death exact at 1, 25, 200 and 400 slices |
| The channel moving >0.5% when the slice count doubles | **clean** — 0.009% over a 32× range |
| The two Green Book rows landing on opposite sides | **not fired** — both still over-predict, because Wave 5's rate channel over-shoots both targets. §6 said in advance this test could no longer fail for the reason it was written |

Suite: **3,535 tests, 3,528 passed, 7 skipped, 0 failed.** Ten are new
(`tests/test_capital_gains_death_channel.py`), and **one existing test was
restated** rather than weakened:
`test_the_spousal_share_is_carried_and_never_read` now reads the long-format
file and additionally asserts the loader does not expose the two never-applied
quantities at all. No test pinned a death-channel level, so none had to move.

`python scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 21` exits
**0**. `python scripts/run_validation_dashboard.py` exits 1 on this branch **and
on `a251b32`**, for the same two reasons on both — the runtime check (Python
3.14.0 against a supported range of `>=3.10,<3.14`) and the standing microdata
warning — and its output differs between the two trees in exactly one line, the
Tier 1 mean. The CI gate's own thresholds are untouched.

### 8.6 Shipped output, and the note that ships with it

| Tailor input | before | after |
|---|--:|--:|
| +2pp, all brackets | −$91.4B | −$91.4B |
| +5pp, all brackets | −$183.7B | −$183.7B |
| +5pp above $1M, step-up retained | −$46.9B | −$46.9B |
| 39.6% above $1M + eliminate step-up, $1M exemption | −$626.9B | **−$643.4B** |
| constructive realization at death only, no exclusion | −$432.8B | **−$427.5B** |

Two shipped figures move, by **2.6%** and **1.2%** — an order of magnitude less
than the moves that made Decision 6 bind in Waves 4 and 5. The note ships anyway,
as one clause in the existing `gains_at_death_caption`: a reader told that an
exclusion applies *per decedent* is entitled to know that the model no longer
applies it to an average decedent.

> … A $1,000,000 per-decedent exclusion then applies to what is left, not to the
> whole gain, **and it is subtracted across a fitted distribution of estate sizes
> rather than from an average estate.** …

No preset moves. All 53 were scored through the API's own `_build_preset_policy`
on `a251b32` and on this branch and are identical; the only capital-gains-shaped
one, `📋 Eliminate Step-Up Basis (-$500B)`, runs through `TaxExpenditurePolicy`
at −$523.4663B on both.

### 8.7 Findings

**1 — The ladder was not what item 15 said it was, and the sign of the movement
is what says so.** Replacing five point masses with a fitted continuous
distribution moved the $1M→$5M exclusion step from $82.3B to $85.0B. It could not
have gone the other way: the taxable excess is convex in the gain, so spreading a
fixed flow of gains over a distribution *raises* what an exclusion leaves in tax
at every exclusion level. Wave 4 read a cliff in the schedule and inferred that
the cliff was the cost; the cliff was real and the cost was somewhere else.

**2 — It is the headcount, and the module already carries a second measurement of
it.** Doubling the decedent count takes the step to $35.5B against Treasury's
$33.4B. The shipped count comes from using Poterba & Weisbenner's *dollar* flow
of estates over net worth as a *headcount* rate — 0.32% of households a year
against roughly 2.4% — and `accrued_gains_parameters.csv` already holds
`mortality_weighted_net_worth_share` at 2.65%, derived from NCHS mortality
against DFA net worth by age, unused in this channel. That is a one-line
comparison nobody had made, and it is the whole of item 15's remaining substance.

**3 — Seven of eighteen published rows were dead, and the count is the point.**
Three transcribed step functions with 6, 8 and 4 published classes were being
evaluated at five group means, so eleven of eighteen rows were read and seven
never were — including PW's entire $1M–$5M band, which is where both Green Book
exclusions sit. Six are now alive. This is worth more than the error column says:
a benchmark can be reproduced by a model that reads a third of its own data.

**4 — The fit refuses below the top decile, and the refusal is arithmetic rather
than judgement.** The same estimator that returns α = 1.53 and 1.47 for the top
1% and the next 9% returns **α = 0.813** for the 10th–50th percentiles, and the
median it implies, $389,500, is **2.02×** the SCF's published $192,700. A Pareto
that has to go below one to fit is telling you the segment is not a tail. The two
groups there keep the group means they always had, and the file carries both
reasons on the row rather than in a commit message.

**5 — An open-ended top class has to be cut somewhere, and "one household" is a
cut with an external check.** The topmost slice is the single richest household,
and the fitted conditional mean above it is **$392.2B** — the right order of
magnitude for the richest American on the shipped 2024:Q4 vintage, arrived at
from three DFA aggregates and a Pareto closure with nothing fitted to any wealth
list. It is not an input to anything; it is the check that the tail is not
absurd.

**6 — The model's decedent count is short by 7.6× overall and only 1.6× at the
top.** The fitted distribution puts 4,378 decedents above $12.92M of net worth
against SOI's own 7,194 estate-tax returns above that threshold. So the headcount
defect is not uniform, and a fix that scaled every group equally would overshoot
the top while correcting the middle. Nobody had this number before, because the
five-class ladder could not produce it.

**7 — The death-channel loop needed no change at all.**
`estimate_step_up_elimination_revenue` and `reachable_gains_per_decedent` in
`policies_core.py` iterate whatever schedule `decedent_classes` hands them and
read the shares off each entry, so replacing five point masses with 609 quantile
slices touched neither. The only edits to that file in this lane are docstrings.
That is a small piece of evidence that Wave 4 drew the seam in the right place —
the reliefs are a function of the estate, and the estate schedule is a separate
object — and it is worth recording because it is the reason a change this large
in the base moved nothing else.

### 8.8 What the lane did not do

- **The decedent headcount is unchanged**, and §8.4 is the measurement of what
  changing it would do. It is a level change to the whole channel — it moves
  Option 51 as well as the two Green Book rows, and in the opposite direction —
  so it is an owner decision about `estate_flow_rate`, not a dispersion lane's.
- **Mortality is still uniform in wealth.** The wealthy are older and die at a
  higher rate, so the true distribution of *decedents* is shifted up relative to
  the distribution of the *living* this lane fits. The DFA publishes net worth by
  age and by percentile group but not jointly.
- **The fit is the DFA's, not SOI's.** SOI Estate Table 1 observes the estates of
  the dead — the right universe — and its own tail is fatter (α **1.401** against
  the DFA's 1.526 over the same range), but it sees only estates above the filing
  threshold and its level would have to be spliced onto the DFA's. The lane took
  one universe whole and recorded the other as a check.
- **PW's $250,000–$500,000 class is still never evaluated**, for the same reason
  the fit stops at the 90th percentile.
- **The rate on the final return is still read off the pre-carve-out gain**, the
  realizations base is still a flow off a stock rather than CBO's own published
  projection, the 72.3% active-business share is still an upper bound on
  "family-owned and -operated", and the 15-year installment election and the
  estate-tax deduction are still not modelled — all carried unchanged from
  `W4_gains_at_death.md` §8.8.
- **`fiscal_model/data/` is invisible to the repository's lint gate**, and the
  lane found it rather than fixed it. `.gitignore` carries a bare `data/` line
  (line 89), which ruff's gitignore-respecting traversal applies at any depth, so
  `python -m ruff check fiscal_model/ ...` — the gate CI runs — silently skips the
  whole package, `capital_gains.py` included. Checked by explicit path it was
  flagged for a closure over loop variables and a zip-of-offsets in this lane's
  own new code; both are fixed, and the three remaining findings are the
  `Optional[X]` style the file already used. Widening the gate is a repo-wide
  change with an unknown blast radius and is not a modelling lane's to make.
- **No target moved and no constant was retuned.** `preregistered.py`,
  `holdout.py`, `loo.py`, `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`
  and the CI thresholds are untouched; the three rows are scored against the same
  figures they carried on `a251b32`.
- **The CI gate needs no re-derivation.** By the workflow's own rule a 15.4% mean
  gives a ceiling of `ceil(15.4 × 1.25) = 20` and a floor of `22 − 1 = 21`, which
  is exactly the standing `--max-mean-error 20 --min-within-25pct 21`.
