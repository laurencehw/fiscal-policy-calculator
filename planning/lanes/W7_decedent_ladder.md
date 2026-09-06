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
