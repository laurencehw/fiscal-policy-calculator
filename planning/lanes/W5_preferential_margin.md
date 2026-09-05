# W5 — The preferential-rate channel at a small step

*Wave 5, lane C. Pre-registered 2026-09-05 against `main` @ `1d35f1b`, **before**
any code in this lane changed. The outturn is appended at the bottom as the
lane's last commit. Nothing below is a promise of attainment
([`MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §1.5 forbids that).
Every number in §§1-5 was produced by a scratch script that reads the **shipped**
module and rescales its own per-year output, so a reader can check whether the
mechanism behaved the way the lane said it would.*

Wave 2's L1 rebuilt the capital-gains base and elasticity; Wave 4's W4 rebuilt
the **death** channel. This lane opens the **rate** channel, and it opens it at
the one row that isolates it: CBO Option 47, a plain +2 percentage points on
long-term gains and qualified dividends with no step-up component at all. The
death channel is not touched — `estimate_step_up_elimination_revenue` and
`decedent_carveout_shares.csv` are not opened.

## 1. Starting point (measured on `1d35f1b`)

`python scripts/cold_holdout.py --json`:

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| out-of-sample (Tier 1) | 26 | **18.0%** | 12.6% | 14 | 21 |
| calibrated reference (fitted) | 23 | 1.6% | 0.1% | 23 | 23 |
| uncalibrated reconstruction | 31 | 56.6% | 29.9% | 9 | 12 |

The four capital-gains rows, and the channel each one tests:

| policy_id | official ($B) | model ($B) | abs err | rate channel | death channel |
|---|--:|--:|--:|--:|--:|
| `cbo_opt47_ltcg_qdiv_2pp` | −103.3 | −57.1 | **44.8%** | **57.1** | 0.0 |
| `cbo_opt51_gains_at_death` | −536.1 | −432.8 | 19.3% | 0.0 | 432.8 |
| `biden_capital_gains_39` | −288.6 | −240.5 | 16.7% | 220.3 | 20.2 |
| `treasury_capgains_39_plus_stepup_elim` | −322.0 | −322.7 | 0.2% | 220.3 | 102.4 |

The two channels are separate addends in `scoring_engine._score_tax_policy`, so
the split above is exact (total minus the death addend, W4 §8.4's rule, not
`score_gains_at_death=False`).

`python scripts/run_loo.py --donor-matrix`: 18 derivable, **29.6%** mean, 19.1%
median, 8/18 within 15%, 4 not cross-validatable. The `CapitalGains` module is
**39.6%** (n=3), and it is the same three rows the reconstruction tier carries:

| case_id | official ($B) | LOO ($B) | signed err | supplies its own base? |
|---|--:|--:|--:|---|
| `cbo_2pp_all_brackets` | −70.0 | −79.8 | −14.0% | yes, $955B dated **2018** |
| `pwbm_39_with_stepup` | +33.0 | +23.6 | −28.4% | yes, $100B dated **2021** |
| `pwbm_39_no_stepup` | −113.0 | −26.6 | +76.5% | yes, $100B dated **2021** |

`scripts/run_validation_dashboard.py` already exits 1 on `1d35f1b` for two
environment reasons that have nothing to do with this lane — Python 3.14 is
outside the supported range and the SOI microdata check warns at 119%/81% — so
the lane's test is that it fails **identically**, not that it passes.

## 2. What the rate channel does today

`CapitalGainsPolicy.estimate_static_revenue_effect` sums `(τ₁ − τ₀)·R₀` over
the SOI Table 3.5 brackets and `estimate_behavioral_offset` rebuilds the same
sum with `R₁ = R₀·exp(−b·Δτ)·(stock ratio)`. `b = ε/τ_ref`, frozen at Dowd,
McClelland & Muthitacharoen's persistent 0.72 (and transitory 1.20 in the
enactment year, on the timing-margin share) at CRS R48562's 22% reference rate.

`R₀` is IRS SOI Table 3.5 for **tax year 2023**, and it is the same number in
every year of a FY2025-2034 window. Option 47's static effect is
`0.02 × $1,107.7B = $22.15B` in 2025 and `$22.15B` in 2034.

CBO's own annual path for the option
(`fiscal_model/data_files/validation/cbo_options_2025_2034_alternatives.csv`,
row 47.1, report p. 57) is **not** flat:

| FY | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 | 33 | 34 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| CBO ($B) | 2.4 | 8.3 | 8.4 | 10.8 | 11.2 | 11.5 | 12.0 | 12.5 | 12.9 | 13.4 |
| model ($B) | **−14.6** | 6.8 | 7.2 | 7.4 | 7.7 | 8.0 | 8.3 | 8.5 | 8.7 | 9.0 |
| model / CBO | −6.07 | 0.82 | 0.85 | 0.69 | 0.69 | 0.70 | 0.69 | 0.68 | 0.68 | 0.67 |

Two facts fall straight out of that last row. The ratio **drifts**, 0.82 → 0.67,
which is a growth-rate difference and nothing else: CBO's path compounds at
6.17%/yr from 2026 while the model's compounds at 3.4%/yr (all of it the
accrued-gains stock ratio), and `(1.0617/1.034)⁸ = 1.234` against an observed
0.824/0.669 = 1.232. And the model's **first** year is the wrong sign, because
the enactment-year transitory coefficient (8.06 against the persistent 3.27)
takes realizations down 14.9% in one year.

The $46.2B gap therefore splits **17.0 in FY2025** (37%) and **29.3 across
FY2026-34** (63%).

### 2.1 The stale note this lane rewrites

`fiscal_model/validation/core.py`'s `known_limitations` for the row still reads,
in full:

> A uniform +2pp applies to the 0%, 15% and 20% brackets alike, but the model
> scores it against the SOI statutory-rate baseline for the *whole* realizations
> base, so gains that face the 0% rate … are taxed at the margin in the model and
> not in JCT's estimate.
>
> The frozen 0.8/0.4 realization elasticities are calibrated for large rate
> changes; at 2pp the timing response JCT assumes is proportionally larger.

Both clauses are stale, and one of them was never right. The 0.8/0.4 net-of-tax
pair was deleted in Wave 2. And the first clause explains an **over**-prediction
on a row that now under-predicts by 45%. Rewriting it is part of this lane.

## 3. The four hypotheses, settled in order

### H1 — the base omits qualified dividends. **Refuted.**

Option 47 taxes long-term gains *and* qualified dividends, so a gains-only base
would miss roughly $336B/yr. SOI Table 3.5 is not a gains table: its
preferential-rate columns are the income taxed by the capital-gains schedule,
which is **adjusted net capital gain plus qualified dividends** by construction.
The arithmetic settles it without an assumption, because in both vendored years
the base is **larger than the whole year's realized gains**:

| | preferential base (Table 3.5) | net capital gain | qualified dividends | base ÷ gains | base ÷ (gains + QD) |
|---|--:|--:|--:|--:|--:|
| TY2022 | $1,342.2B | $1,283.6B | $313.2B | **1.046** | 0.840 |
| TY2023 | $1,121.4B | $943.4B | $336.1B | **1.189** | 0.876 |

A gains-only base cannot exceed the year's gains, so the ratio in column 4
refutes the hypothesis on its own; and the ratio in column 5 is stable across a
year in which realizations fell 27%, which is what a base containing both
components looks like (the 12-16% shortfall is gains and dividends on returns
with no modified taxable income). **Adding a qualified-dividends column would
double-count $313-336B of base.** Sources: net capital gain from the vendored
Tax Foundation aggregate; qualified dividends from IRS SOI Table 1.4, column 26
("Qualified dividends [2]"), `22in14ar.xls` / `23in14ar.xls`.

This lane vendors that check rather than asserting it: a new
`soi_preferential_base_coverage.csv`, emitted by
`scripts/build_capital_gains_data.py`, **carried and never read** — the same
convention `decedent_carveout_shares.csv` uses for the marital-bequest share,
and for the same reason.

### H2 — the base is not projected across the window. **Confirmed, and it is this lane's mechanism.**

`R₀` is a TY2023 flow used unchanged for FY2025-2034. It is not a free-standing
flow: this module already carries a **stock** of accrued gains, already grows it,
and already reads a realization **hazard** off the two —
`realization_hazard = R/A` — which it then uses in `lock_in_wedge`, in
`stock_ratio` and in the family-business recapture. Holding `R` flat while `A`
grows asserts that the hazard falls **5.80% a year, 45% across the window**, and
nothing supports that; it is not a conservative choice but a different and
unstated behavioural assumption.

So: **`R(t) = h · A(t)`**, with `h` at its observed value and `A` the stock the
module already indexes, which is `(1 + g)^(t − tax_year)` with
`g = household_net_worth_growth_rate = 5.8015%` (Federal Reserve DFA, 1998:Q4
to 2024:Q4). **No new constant enters the module**: both `g` and `h` are already
shipped and already load-bearing.

This **supersedes L1 §2.6 for the realizations flow only**, and it is worth
being explicit about why, because §2.6 was pre-registered and is not being waved
away. §2.6's rule is "stocks are indexed, flows are not", and its reason was that
inventing a growth rate for a flow had cost the estate and payroll modules their
accuracy. The rule is right and the reason is right; the classification was
wrong. This flow is not free-standing — it is `h · A` off a stock this module
already indexes — so indexing it invents nothing, and *not* indexing it invents a
falling hazard instead. §2.6 also predicted that growing the base at 5.79% would
take `cbo_opt47` "from a predicted ~30% to ~150%". That arithmetic does not hold:
the row is at 55% of its target and the largest factor the projection can apply
in the last year is 1.86, so the projection cannot get the row past its target at
all, let alone to 150%. It lands at 90% of it.

**The independent check, and it is the strongest evidence in this lane.** Invert
CBO's own published annual path for the option: given the module's bracket base
and the reform rates, what semi-log coefficient `b` reproduces CBO's figure in
each year?

| | FY2025 | FY2026 | FY2030 | FY2034 |
|---|--:|--:|--:|--:|
| implied `b`, **flat** base | 4.171 | 2.889 | 2.206 | **1.806** |
| implied `b`, **projected** base | 4.228 | 3.167 | 3.007 | **3.124** |

On a flat base CBO's own path implies a coefficient that *falls* year after year
from 4.17 to 1.81 — an artefact, because a scorekeeper does not change its
elasticity every year. On a projected base it is **flat from 2026 at 3.0-3.2**,
against DMM's frozen 3.2727 and **JCT's own published working coefficient of 3.1**
(CRS R48562 p. 8). That is a coefficient this repository did not choose,
recovered from a document it did not write, agreeing with the frozen literature
value to 5% and with JCT's to 1%.

It is a **check and not a fit**, and the distinction is checkable: `g` is the
module's own shipped constant, and the `g` that would make CBO's 2034 imply DMM's
3.2727 *exactly* is **6.77%**, not 5.80%. The lane is using the slower rate and
therefore still under-predicts, which is the direction to be wrong in.

### H3 — the 0%/15%/20% bracket treatment. **Settled: the model is right and the stale note is wrong.**

Option 47 raises **all three** preferential rates by 2 percentage points — the
record's own note reads "Applies to every rate bracket, so the threshold is
zero", and the option has a single alternative. The model applies +2pp to the
0% bracket's $80.7B (7.29% of the base), worth **$1.61B/yr** of static effect and
rather more of the net effect, because a bracket at τ₀ = 0 has no baseline
revenue to lose to the realizations response. Dropping it would move the row
from 57.3% to 71.5% under on a like-for-like replay: **further away, not closer.**
The stale note's diagnosis is wrong in direction as well as in vintage.

### H4 — the realization response at a 2pp step. **Measured; no defect found; one candidate fix tested and rejected.**

At 2pp the persistent response is `exp(−3.2727 × 0.02) = 0.9366`, a 6.3%
realizations drop, and §3's H2 table says that is what CBO's own out-years imply.
The **enactment-year** coefficient is 8.0557 (persistent 3.2727 plus
transitory 5.4545 on the 87.7% timing-margin share), a 14.9% one-year drop, and
CBO's FY2025 implies 4.23. The two are **not comparable**: CBO's FY2025 is a
partial fiscal year for a calendar-year tax — its 2.4 is 29% of its own 2026 —
and this model has no receipts lag, so it books a whole enactment year against a
quarter of one. Building a fiscal-year receipts lag is a scoring-engine change
that would move every row in the battery, and it is out of this lane's scope.

The candidate structural fix — *the transitory coefficient prices a deviation of
the current rate from its permanent level, so a permanent change effective at the
window's first year has no transitory deviation at all, and the anticipatory
surge belongs to the year before* — was tested before this lane opened a file and
is **rejected by its own arithmetic**: suppressing the enactment-year transitory
term on top of H2 takes `cbo_opt47` to **+12.4% over**, `biden_capital_gains_39`
to **+68% over** and `treasury_...` to **+76% over**. It moves every row the
wrong way. Decision 3 freezes the elasticities and this lane does not touch them.

## 4. The mechanism this lane adds

One change, in the capital-gains rate channel only.

- `CapitalGainsBaseline` gains `realizations_growth_rate()` and
  `realizations_projection_factor(from_tax_year, to_year)`, both reading the
  parameter file's existing `household_net_worth_growth_rate`.
  `get_brackets_above_threshold` is **not** changed — it stays a tax-year
  lookup, so `realization_hazard`, `lock_in_wedge` and `stock_ratio` return
  exactly what they return today.
- `CapitalGainsPolicy` gains `realizations_projection_factor(year)`, and its
  static and behavioural legs both multiply by it. Both legs scale by the same
  factor, so the reported static effect and behavioural offset stay a decomposition
  of the score rather than one absorbing the other.
- **It applies only where the base's tax year is known**, i.e. the SOI
  auto-populated path. A caller that supplies `baseline_realizations_billions`
  supplies an aggregate with no vintage attached, and the module has no field to
  record one, so that base is left exactly as it is. A flag captured in
  `__post_init__` decides it, because `get_brackets` overwrites the field.
- `scoring_engine._score_tax_policy` passes `year=` to the static call for a
  `CapitalGainsPolicy` and for nothing else — the same pattern
  `TaxExpenditurePolicy` already uses in `_score_growth_tax_policy_year`.

### 4.1 Why the three reconstruction scenarios must not move, and what it would cost if they did

All three supply their own `baseline_realizations_billions`, so under §4's rule
they do not move — and that is the rule doing its job rather than an exemption.
`cbo_2pp_all_brackets` is the case that shows why: it is a **2018-vintage JCT
score** (`budget_window` FY2019-2028) of a **2018-vintage $955B base**. Growing
that base to the model's 2025-2034 window would multiply its rate channel by
**1.94 on average**, taking the row from −$79.8B to roughly −$155B against a
−$70.0B target — from 14.0% to about 121%. A projection is a property of the
base's vintage, and a base carrying its own vintage is already where it belongs.

The task's framing was that a rate-channel change improving Option 47 should move
`cbo_2pp_all_brackets` in the same direction, and if it does not, say so. It does
not, and the reason is that the two rows do not share a base: Option 47 reads the
SOI table and is scored on a window seven years after it, while
`cbo_2pp_all_brackets` carries a base and a target from the same year. Making them
share the projection would improve neither.

## 5. Pre-registered expectation

Computed by replaying the shipped model's own per-year rate channel and scaling
it by `(1 + g)^(t − 2023)`, before any module code changed. Because both legs are
linear in `R₀` and the stock ratio is a ratio, the rescaling is exact rather than
approximate, so these are predictions the outturn can be held to tightly.

| Row | before | expected after | why |
|---|--:|---|---|
| `cbo_opt47_ltcg_qdiv_2pp` | 44.8% | **8-14%, still under-predicting** | rate channel 57.1 → 92.5 against −103.3 |
| `cbo_opt51_gains_at_death` | 19.3% | **unchanged, to the dollar** | no rate change, so no rate channel to project |
| `biden_capital_gains_39` | 16.7% **under** | **28-35%, now over** | rate channel 220.3 → 359.0; death channel 20.2 untouched. **A registered regression** |
| `treasury_capgains_39_plus_stepup_elim` | 0.2% | **40-47%, now over**| same rate channel; death channel 102.4 untouched. **A registered regression** |
| **Tier 1 mean** | 18.0% | **18.5-19.3%** — a net *regression* of about 0.9pp | mass 468.0 → about 492 |
| **Tier 1 median** | 12.6% | **12.5-13.0%** | the moving rows are all outside the middle |
| **Tier 1 within 15%** | 14 | **14** | Option 47 enters, the FY2022 row leaves |
| **Tier 1 within 25%** | 21 | **20** | Option 47 enters, both Green Book rows leave |
| `CapitalGains` LOO (n=3) | 39.6% | **unchanged** | all three supply their own base |
| LOO suite (n=18) | 29.6% | **unchanged** | same |
| calibrated fitted (n=23) | 1.6% | **unchanged** | no fitted annual is touched |
| unfitted reconstruction (n=31) | 56.6% | **unchanged** | its three capital-gains rows are the LOO three |

**The lane expects to raise the Tier 1 mean and it is registering that in
advance.** [`MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §1.4 says
regressions count against the lane, so here is the count: Option 47 improves by
34.3 points of error mass and the two Green Book rows give back 57.8, for a net
**+23.5** and a tier mean of about 18.9%. The lane ships it anyway, for the
reason W4 shipped Option 51's regression and L2's follow-up shipped FRA's: the
FY2022 row's 0.2% was **already** documented as two errors cancelling (W4 §8.4:
"not a measurement of accuracy and must not be quoted as one"), and one of the two
was a base two years stale and never grown. Removing it is right and it costs the
row its number.

The CI gate is `cold_holdout.py --max-mean-error 25 --min-within-25pct 20`. At
18.9% and 20 the branch passes with the within-25 count sitting **exactly on the
floor**, and that is registered here rather than discovered later.

### 5.1 Shipped output that will move

Tailor's capital-gains form at its own defaults (data year 2024), reproducing
W4 §5.1's table so the two are comparable line for line:

| Tailor input | before | predicted after |
|---|--:|--:|
| +2pp, all brackets | −$56.4B | **−$91.4B** |
| +5pp, all brackets | −$110.9B | **−$183.7B** |
| +5pp above $1M, step-up retained | −$22.3B | **−$46.9B** |
| 39.6% above $1M + eliminate step-up, $1M exemption | −$490.7B | **−$626.9B** |
| constructive realization at death only, no exclusion | −$432.8B | **−$432.8B** |

Four of the five move, by 26% to 110%, so **Decision 6 binds** and a note ships
in the same PR, in its own commit, directly after `gains_at_death_caption` in
`fiscal_model/ui/tabs/results_summary.py`.

No preset moves: the only capital-gains-shaped preset,
`📋 Eliminate Step-Up Basis (-$500B)`, runs through `TaxExpenditurePolicy` and
never reaches this channel.

## 6. What would falsify the lane

- Any Tier-1 row other than `cbo_opt47_ltcg_qdiv_2pp`, `biden_capital_gains_39`
  and `treasury_capgains_39_plus_stepup_elim` moving at all. The diff is gated on
  `isinstance(policy, CapitalGainsPolicy)` and on an SOI-populated base; nothing
  else can reach it.
- `cbo_opt51_gains_at_death` moving by any amount. It changes no rate, so it has
  no rate channel, and a death channel that moves means the projection leaked into
  `estimate_step_up_elimination_revenue`.
- The death addend on either Green Book row moving. §1's table is the before; the
  outturn must print the same two numbers.
- The `CapitalGains` LOO module, the LOO suite, the fitted tier or the
  reconstruction tier moving by any amount.
- `run_loo.py --donor-matrix`'s three identical rows ceasing to be identical.
- `cbo_opt47` landing outside 8-14%, or either Green Book row landing outside its
  registered band.
- Tier 1's within-25 count falling below 20, which would take the CI gate with it.

## 7. Where the lane expects to be wrong

- **5.80% is a 1998-2024 net-worth CAGR carried forward for eleven years.**
  Realizations as a share of GDP are famously mean-reverting and CBO's own
  baseline projects them back toward a historical share, so this very likely grows
  the flow too fast late in the window. It is the module's own constant and no new
  one enters, which is the whole argument for it; it is not an argument that the
  rate is right.
- **TY2023 is a realizations trough.** The Tax Foundation aggregate this
  repository already vendors reads $1,283.6B (2022), **$943.4B (2023)** and
  $1,368.1B (2024) — down 27% and then up 45%. The module anchors on 2023 and
  grows it at 5.80%, which reaches $1,186B of preferential base in 2024 where the
  aggregate series says the year rebounded by nearly half. So the *level* is
  probably low as well as the *growth* possibly high — two errors in opposite
  directions, neither of which this lane corrects. Averaging the two vendored SOI
  years would raise the level about 9% and there is no published rule for doing
  it, so the lane anchors on the latest year and says this instead.
- **The FY2022 Green Book row is scored on the wrong window, and the projection
  makes that bite.** Its target is FY2022-2031 on a 2021 baseline; the model
  scores FY2025-2034 because the record states no `effective_start_year`.
  Projecting the base to a window three years after the target's costs it about
  1.058³ = 18%, which is roughly **17 of its predicted 43 points**. Fixing it means
  changing a shape input under the manifest's `superseded_by` rule, which is a
  decision no modelling lane may make.
- **The enactment-year transitory dip is left alone and is probably too big.**
  §3's H4 has the numbers and the rejected fix.
- **The $1M threshold is not indexed.** As the base grows nominally, more gains
  cross a fixed $1M in real terms; the model applies the projection to the
  above-$1M slice measured in 2023 AGI, so both Green Book rows understate their
  own base growth. That is the conservative direction on rows this lane already
  expects to over-predict.
- **The 0% bracket's share is a 2023 share.** Projecting the whole base uniformly
  holds the bracket composition at TY2023, so the $80.7B in the 0% bracket grows
  at the same rate as the $682.6B in the 20% bracket. Bracket thresholds are
  indexed and the composition drifts; nothing here tracks that.
