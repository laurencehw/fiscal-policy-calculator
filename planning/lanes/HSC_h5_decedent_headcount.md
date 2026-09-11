# H5 — The decedent headcount: a death rate instead of a dollar flow

*Wave C of [`planning/HIGH_STAKES_ACCURACY.md`](../HIGH_STAKES_ACCURACY.md) §3 H5,
closing the headcount half of `MODELING_IMPROVEMENT.md` §6.2 item 15 — the
hand-off `W7_decedent_ladder.md` §8.4 left. Pre-registered 2026-09-11 against
`main` @ `2d13e60`, **before** any code in this lane changed. The outturn is
appended at the bottom as the lane's last commit.*

Owner decision ⑥ is taken: the swap of the headcount rate to
`mortality_weighted_net_worth_share` is authorised, and `cbo_opt51_gains_at_death`
moving the **wrong way** is accepted in advance.

Every number in §3 and §5 below was computed before a line of module code
changed, in scratch scripts that patch exactly the one parameter the
implementation will change (`estate_flow_rate` as read by
`CapitalGainsBaseline._decedent_template`) and leave everything else shipped.
The same scripts reproduce W7's own figures to the cent first — 408,532.19
decedents, $196.20970B of gains at death in 2025, 4,377.5 decedents above
$12.92M, and the ×2 sensitivity row's 406.83 / 15.58 — which is what makes the
predicted figures beside them worth reading.

## 1. The mechanism

### 1.1 The defect: one module, two death rates, 8.3× apart

`fiscal_model/data/capital_gains.py:750` builds the decedent count as

```python
households = self._parameters["households_millions"] * 1e6   # 127,858,303
flow_rate  = self._parameters["estate_flow_rate"]            # 0.3195194857 %
...
households * share * flow_rate                               # 408,532 a year
```

`estate_flow_rate` is **dollars over dollars**: Poterba & Weisbenner (2001)
Table 8's $118.9B of expected estates over Federal Reserve DFA household net
worth at 1998:Q4, as its own `source` column in
`accrued_gains_parameters.csv` says. Used as a **headcount** rate it produces
408,532 decedents a year against roughly **3.09 million** NCHS deaths.

The sharpest statement of the defect is not the comparison with NCHS, though.
It is that **the module already carries a second death rate and uses it
elsewhere in the same file**. `CapitalGainsBaseline.death_exit_rate()`
(`capital_gains.py:571-580`) returns `mortality_weighted_net_worth_share`,
**2.646832 %/yr**, derived by `scripts/build_capital_gains_data.py:684-688`
from the NCHS 2022 life table (NVSR 74-02 Table 1) against DFA net worth by age
of head at 2024:Q4 — and `policies_core.py:1121` and `:1186` price the lock-in
wedge and the accrued-gains stock's drift with it. So on `main` the module says
the stock loses 2.65% of itself to death every year **and** that 0.32% of
households die every year. Both cannot be right, and the one with a life table
behind it is the one that is.

### 1.2 Why the same figure is the right *headcount* rate here

`death_exit_rate` is a rate on **wealth**, so swapping it into a **head** count
is not free and this lane does not treat it as free. The argument is the
module's own gains distribution. `_decedent_template` distributes gains at
death across slices in proportion to `households × wealth × unrealized-gain
share` — i.e. it already asserts that **dollars die at a uniform rate across
the wealth distribution**. Given that assertion, and given that the wealth of a
decedent in a slice is the slice's own mean wealth (which is what the fitted
size distribution supplies), the headcount rate in a slice *is* the dollar
rate:

```
decedents(s) = dollars dying in s / wealth per decedent in s
             = (n_s · w_s · d) / w_s
             = n_s · d,        d = death_exit_rate
```

So `mortality_weighted_net_worth_share` is the unique headcount rate consistent
with the gains distribution the module already ships. Any count that varies by
size class would have to move the gains distribution with it — which §1.3 is
about.

### 1.3 "Applied by size class": measured, and refuted in direction

§3 H5 of the plan asks for the share **applied by size class**, so that the
implied count above $12.92M lands near SOI's 7,194 rather than overshooting it,
and names the two tables to read it off: the DFA net-worth-by-age table and the
NCHS life table already cited in `accrued_gains_parameters.csv`. This lane read
both, before changing anything, and the arithmetic says the grading runs the
**wrong way**.

NCHS Table 1 supplies, for the same four DFA age bands the parameter file
already carries, both the band mortality `Σdx/ΣLx` and — from the `Lx` column
restricted to ages 18 and over, which is the age range a household reference
person can be in — the stationary population share of each band. DFA
`dfa-age-levels.csv` at 2024:Q4 supplies each band's net worth. Nothing is
fitted; the two marginals are published.

| band | DFA net worth $M | adult pop share | mean wealth ÷ average | NCHS mortality | Pareto-tail share |
|---|--:|--:|--:|--:|--:|
| under 40 | 10,697,224 | 0.3607 | 0.184 | 0.001088 | 0.0223 |
| 40–54 | 32,282,098 | 0.2350 | 0.852 | 0.003939 | 0.1510 |
| 55–69 | 67,311,498 | 0.2109 | 1.979 | 0.011946 | 0.4908 |
| 70+ | 50,947,955 | 0.1933 | 1.634 | 0.065259 | 0.3359 |

The "Pareto-tail share" column is the age composition **at the top of the wealth
distribution** under the only assumption available without a joint age × wealth
table — that the wealth distribution has the same shape in every age band and
differs only in scale. Two Pareto tails with a common index `α` keep a constant
relative share above any threshold, `∝ N_a · μ_a^α`, so with the fitted
`α = 1.5264` already in `decedent_size_distribution.csv` the tail composition is
the last column and the tail's own mortality rate is

- **head-weighted (whole population): 1.645580 %**
- **net-worth-weighted (the shipped parameter): 2.646832 %**
- **Pareto-tail, size-graded: 2.839978 %** — **1.073×** the shipped parameter and
  **1.726×** the population-average head rate.

Two consequences, both against the plan's expectation:

1. **Grading the count by size makes the top-count comparison worse, not
   better.** The implied count above $12.92M goes 4,378 → **36,262** under the
   uniform swap and → **38,908** under the size-graded rate. SOI's 7,194 is
   further away, not nearer. The reason is not subtle once stated: **the wealthy
   are older, so they die at a *higher* rate, not a lower one.** A size-graded
   mortality raises the top and lowers the bottom.
2. **The uniform swap is already within 7% of the graded rate where the money
   is.** The three dispersed groups hold 85.8% of gains at death, and their
   gains-weighted graded rate is **2.834%** against the shipped **2.647%** — a
   7.0% gap. Grading would move the death channel by well under a tenth of what
   the swap itself moves, while adding a within-band shape assumption the DFA
   does not publish and requiring the gains distribution to be reweighted in the
   same commit.

So this lane **implements the level swap and does not grade the count**, and
ships the refutation as two regenerable CHECK-ONLY rows in
`accrued_gains_parameters.csv` so the arithmetic above lives in the tree rather
than only in this document. That is a declared deviation from §3 H5's wording
and it is recorded here rather than in a commit message.

### 1.4 What the lane does not touch

The **level** of gains at death stays at Poterba & Weisbenner's flow
(`gains_at_death_share_of_net_worth`, 0.1150162657% of net worth, $196.2097B in
2025). §3 H5 says "holding gains at death at PW's flow and varying only the
count", and §7 records what the level question looks like once the count is
right. `estate_flow_rate` stays in the parameter file, because
`gains_at_death_share_of_net_worth` is exactly `estate_flow_rate ×
gain_share_of_estates` and the row is still the level's provenance; only its
**second** use, as a headcount rate, goes.

## 2. Files

- `fiscal_model/data/capital_gains.py` — `_decedent_template` reads
  `death_exit_rate()` instead of `estate_flow_rate`; docstrings on
  `decedent_classes`, `death_exit_rate` and the module header.
- `fiscal_model/data_files/capital_gains/accrued_gains_parameters.csv` — two new
  CHECK-ONLY rows (`crude_adult_mortality_rate`,
  `size_graded_tail_mortality_rate`) and a corrected `source` note on
  `estate_flow_rate` saying what it is and is not used for.
- `scripts/build_capital_gains_data.py` — emits those two rows.
- `fiscal_model/policies_core.py` — docstring only on the `CapitalGainsPolicy`
  death-channel methods.
- `fiscal_model/ui/tabs/results_summary.py` — **one clause** inside the existing
  `gains_at_death_caption`, the Decision 6 caption. H4 is rewriting the band
  code in this file in the same wave; this hunk is additive, inside a different
  function, and touches no band code.
- `fiscal_model/validation/core.py` — the `known_limitations` prose for
  `cbo_opt51_gains_at_death`, `biden_capital_gains_39` and
  `treasury_capgains_39_plus_stepup_elim`, which on `main` describe the
  headcount as unfixed. Prose only; no record, target or shape input moves.
- `tests/test_capital_gains_death_channel.py` — the one test that pins the count
  to `estate_flow_rate` is restated, not weakened, and new tests pin the
  consistency the swap creates.

Out of my hands and untouched: `credibility.py`, `results_summary.py`'s band
code (H4), `trade.py` (H8), `app_data.py`, `preset_ids.py`, `policy_status.py`,
`ui/policy_packages.py` and `validation/scenarios.py` preset strings (the label
lane).

## 3. Pre-registered predictions

Measured by patching `estate_flow_rate → mortality_weighted_net_worth_share` in
the loaded parameter dict and re-scoring, on `2d13e60`, before implementation.

### 3.1 The four Tier-1 capital-gains rows

| policy_id | window | rate channel | death before | death after | total before | total after | target | err before | **err after** | plan's band | verdict |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|
| `cbo_opt51_gains_at_death` | FY2025 | 0.00 | 427.53 | **345.93** | −427.53 | **−345.93** | −536.1 | 20.25% | **35.47%** | 30 ± 8 | **in band; registered regression** |
| `biden_capital_gains_39` | FY2025 | 359.02 | 24.23 | **7.42** | −383.25 | **−366.44** | −288.6 | 32.80% | **26.97%** | 15 ± 8 | **out of band, high** |
| `treasury_capgains_39_plus_stepup_elim.v2` | FY2022 | 303.14 | 77.96 | **13.00** | −381.10 | **−316.14** | −322.0 | 18.35% | **1.82%** | 22 ± 6 | **out of band, low** |
| `cbo_opt47_ltcg_qdiv_2pp` | FY2025 | 92.46 | — | — | −92.46 | −92.46 | −103.3 | 10.49% | **10.49%** | unmoved | **unmoved** |

**Two of the plan's three bands are unattainable and this lane says so before
it runs rather than after.** §3 H5's bands were written against the pre-PR-#126
reading of these rows and do not survive contact with two facts already on
`main`:

- **`biden_capital_gains_39` cannot reach 15 ± 8 by any decedent count.** Its
  rate channel alone is **359.02** against a target of **288.6** — 24.4% over
  with the death channel set to **zero**. The band's ceiling of 23% is below the
  floor the rate channel puts under the row. Wave 5 registered that cost
  (`W5_preferential_margin.md`) and Decision 3 freezes the elasticity that would
  move it, so it is out of scope here (§6). The **attainable** range for this row
  is [24.4%, 32.8%] and this lane predicts **26.97%**.
- **`treasury_capgains_39_plus_stepup_elim.v2` cannot regress to 22 ± 6.** Since
  PR #126 it is scored on its own FY2022–2031 decade, where its rate channel is
  303.14 against a target of 322.0 — the model is **under** on the rate channel
  and the death channel is what pushes it over. Shrinking the death channel
  therefore moves this row **toward** its target, not away. A regression here
  would require the death channel to *grow*.

So this lane registers **its own bands**, computed above: `cbo_opt51` **35.5 ±
2**, `biden_capital_gains_39` **27.0 ± 2**, `treasury…v2` **1.8 ± 2**,
`cbo_opt47` **unmoved to the cent**. The plan's bands are recorded beside them
so the deviation is visible to the owner rather than buried.

### 3.2 The class, its ceiling, and the tier

| quantity | before | **after** | gate |
|---|--:|--:|---|
| capital-gains class mean | 20.47% | **18.69%** | ceiling **26** (`--max-class-mean-error capital_gains=26`) → **passes**, 7.3 points of headroom |
| capital-gains error mass | 81.9 | **74.8** | — |
| Tier 1 mean | 14.74% | **14.46%** | `--max-mean-error 20` → passes |
| Tier 1 median | 12.65% | **11.50%** | — |
| Tier 1 within 15% | 15 | **16** | — |
| Tier 1 within 25% | 23 | **22** | `--min-within-25pct 22` → **passes with zero headroom** |

The within-25 count is the one to watch: `cbo_opt51_gains_at_death` leaves that
set (20.25% → 35.47%) and `treasury…v2` was already inside it, so the floor is
met **exactly**. That is registered here as the tightest constraint this lane
has, and §4 makes a within-25 count below 22 a falsification.

Per the workflow's own rule the gate re-derives to ceiling `ceil(14.46 × 1.25) =
19 →` nearest 5 `= 20` (unchanged) and floor `22 − 1 = 21`, which **loosens**;
the per-class capital-gains ceiling re-derives to `ceil(18.69 × 1.25) = 24`,
which tightens. **Neither is changed by this lane** — three Wave C lanes move
rows in parallel and the gate is re-derived once, after the wave, by the
coordinator. Both commands must exit 0 unchanged, and they do.

### 3.3 The calibrated tiers and leave-one-out: nothing moves

Predicted **byte-identical**: the fitted tier (16 rows), the unfitted
reconstruction tier (39 rows), `run_loo.py --donor-matrix` line for line, and
all 81 scorecard entries other than the three Tier-1 rows above.

The reason is mechanical and worth stating because `eliminate_step_up` is a
**fitted** benchmark and `loo.py` already excludes it for leakage. It never
reaches this channel: `create_eliminate_step_up_basis` builds a
`TaxExpenditurePolicy`, not a `CapitalGainsPolicy`. And the three calibrated
capital-gains scenarios do not run the death channel either —
`cbo_2pp_all_brackets` and `pwbm_39_with_stepup` set `eliminate_step_up=False`
and `pwbm_39_no_stepup` sets `score_gains_at_death=False`
(`validation/scenarios.py:81, :103, :134`). The `CapitalGains` LOO module
therefore stays at **39.6%** and the suite at **35.7%** — W7 registered the same
prediction and it held.

### 3.4 Shipped output

**No preset moves.** All 53 were scored by stable id through
`composer._build_preset_policy → _scorer_for → score_policy` under the patch and
are identical to four decimals; the only capital-gains-shaped one,
`eliminate-step-up-basis`, runs through `TaxExpenditurePolicy` at −523.4663 on
both.

**Three Tailor shapes move, and by enough that Decision 6 binds:**

| Tailor input | before | **after** | move |
|---|--:|--:|--:|
| +2pp, all brackets | −$92.46B | −$92.46B | — |
| +5pp, all brackets | −$186.34B | −$186.34B | — |
| +5pp above $1M, step-up retained | −$48.03B | −$48.03B | — |
| 39.6% above $1M + eliminate step-up, $1M exclusion | −$653.38B | **−$450.68B** | **−31.0%** |
| 39.6% above $1M + eliminate step-up, $5M exclusion | −$491.72B | **−$393.57B** | **−20.0%** |
| constructive realization at death only, no exclusion | −$427.53B | **−$345.94B** | **−19.1%** |

These are an order of magnitude larger than W7's 1–3% and are the reason the
Decision 6 caption is a clause change rather than an optional note.

### 3.5 The headcount itself

| quantity | before | **after** | external check |
|---|--:|--:|---|
| decedents a year | 408,532 | **3,384,194** | roughly **3.09 million** NCHS deaths — **9.5% over**, where the shipped figure was **86.8% under** |
| implied decedents above $12.92M | 4,378 | **36,262** | SOI's 7,194 estate-tax returns — **5.04× over**, where the shipped figure was 0.61× |
| largest gain per decedent | $279.1B | **$33.7B** | — |

The top-count check is registered as **expected to get worse**, for the reason
§1.3 gives, and §7 says what is left of it.

## 4. Falsification

This lane is falsified if any of the following holds after implementation:

1. Any of the three moved rows lands outside **this lane's** §3.1 band (35.5 ± 2,
   27.0 ± 2, 1.8 ± 2), or `cbo_opt47_ltcg_qdiv_2pp` moves by a cent.
2. Any of the other 22 Tier-1 rows moves at all.
3. Tier 1 within-25% falls below **22**, or the capital-gains class mean rises
   above **26**, or either gate command exits non-zero.
4. Any of the 16 fitted or 39 unfitted calibrated scorecard rows moves, or
   `run_loo.py --donor-matrix` differs by a line.
5. Any of the 53 presets moves.
6. The total gains at death at any slice count stops equalling
   `gains_at_death_billions` — the level is not this lane's to change.
7. The decedent count stops being exactly `households × share × death_exit_rate`
   — i.e. a second constant has crept in.

## 5. Reproduction

The figures in §3 come from three scratch scripts, each of which reproduces a
shipped W7 figure before predicting anything:

- the decomposition (reproduces 408,532.19 decedents, $196.20970B of 2025 gains
  at death, 4,377.5 above $12.92M, and the four rows' channel split);
- the rate probe (reproduces W7 §8.4's ×2 row to the cent: 406.83 / 15.58);
- the gradient (reproduces `mortality_weighted_net_worth_share` to
  0.02646832 from the DFA age table and NCHS Table 1, then grades it).

The last of these becomes two CHECK-ONLY rows emitted by
`scripts/build_capital_gains_data.py`, so §1.3's refutation is regenerable.

## 6. Out of scope

- **The realizations elasticity (Decision 3).** At +19.6pp the semi-log response
  sits near its own revenue-maximising rate and it is the largest remaining
  capital-gains term; re-opening it is an owner decision, not a lane's. The rate
  channel is untouched to the cent on every row.
- **The window rule (§6.2 item 35, `iija_2021_discretionary.v3`).** No record,
  target, `budget_window` or `scoring_window_first_year` is edited.
- **The level of gains at death.** See §7.
- **`preregistered.py`, `holdout.py`, `loo.py`, `target_revisions.py`,
  `KNOWN_SCORES`, `CBO_SCORE_MAP` and the CI thresholds**, all untouched. The
  three rows are scored against the same figures they carried on `2d13e60`.

## 7. What this lane hands on

Written before implementation so it cannot be a rationalisation of the outturn.

**The level and the count come from the same ratio, and only one of them is
being fixed.** `gains_at_death_share_of_net_worth` is `estate_flow_rate ×
gain_share_of_estates` — the same dollar flow this lane is removing from the
headcount. Held against the module's own `death_exit_rate`, the level it implies
is **0.372% of the accrued-gains stock** where the stock's death exit is priced
at **2.647%**, a factor of **7.1**. Some of that gap is real and sourced —
Poterba & Weisbenner's flow already excludes inter-spousal transfers, which is
the convention every realization-at-death proposal uses and which removes most
of a first death — but nobody has measured how much. It matters because it
points the other way from this lane: `cbo_opt51_gains_at_death` **under**-predicts
and a larger level would close it. A lane that raises the count without the
level is registering exactly half of a two-sided correction, and §3.1's 35.47%
is the price of the half.

**The decedent universe is the question under the level.** The swap puts
3,384,194 decedents against 3.09 million NCHS deaths — 9.5% over — but PW's flow
measures **non-spousal** estates, whose universe is smaller than all deaths, not
larger. Measured beside the authorised constant: the crude adult life-table rate
(1.6619%) gives 2,124,898 and the crude all-age rate (1.2910%) gives 1,650,702,
and those rows read `cbo_opt51` at **32.14%** and **28.41%** and the class at
**17.71%** and **16.90%**. **They are recorded and not taken.** The owner
authorised one constant; picking the one that scores best out of three would be
fitting a parameter to a benchmark, which is what §1.1 of the plan forbids.
Deciding which universe PW's flow describes is an owner question with a
document behind it, not a lane's preference.

**The SOI check needs a unit before it can be a check.** SOI Table 1 counts
**individual** decedents whose **gross estate** clears a per-decedent threshold;
the model counts **households** whose net worth clears the same number. A
married household at $13M usually produces two estates of roughly $6.5M, neither
of which files. So a model count above SOI's is the expected sign, and the
"1.6× short at the top against 7.6× overall" asymmetry W7 recorded is at least
partly that unit gap rather than a mortality gradient. Making it a real check
needs SOI's own gross-estate distribution spliced onto the DFA's household one —
`W7_decedent_ladder.md` §8.8 records the splice as unbuilt and its tail index
(α 1.401 against the DFA's 1.526) as measured.

---

## 8. Outturn

*Appended after implementation, on `dc3914b`. Every figure below is from a run
named in §5, repeated identically.*

### 8.1 Against the pre-registration

**Every prediction in §3 landed, to the decimal.** Nothing in §3 was adjusted
between writing it and reading the result; the probe patched exactly the
parameter the implementation moved, so the two are the same arithmetic.

| quantity | §3 predicted | **outturn** |
|---|--:|--:|
| `cbo_opt51_gains_at_death` | 35.47% | **35.5%** |
| `biden_capital_gains_39` | 26.97% | **27.0%** |
| `treasury_capgains_39_plus_stepup_elim.v2` | 1.82% | **1.8%** |
| `cbo_opt47_ltcg_qdiv_2pp` | unmoved | **unmoved to the cent** |
| capital-gains class mean | 18.69% | **18.7%** |
| capital-gains error mass | 74.8 | **74.8** |
| Tier 1 mean / median | 14.46 / 11.50 | **14.5 / 11.5** |
| Tier 1 within 15% / 25% | 16 / 22 | **16 / 22** |
| presets moved | 0 of 53 | **0 of 53** |
| fitted rows moved | 0 of 16 | **0 of 16** |
| reconstruction rows moved | 0 of 39 | **0 of 39** |
| LOO donor matrix | identical | **identical line for line** |
| decedents a year | 3,384,194 | **3,384,194** |
| implied above $12.92M | 36,262 | **36,262** |

### 8.2 The three rows, channel by channel

| Row | window | rate channel | death before | death after | total before | total after | target | before | **after** |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` | FY2025 | 0.00 | 427.53 | **345.93** | −427.53 | **−345.93** | −536.1 | 20.3% | **35.5%** |
| `biden_capital_gains_39` | FY2025 | 359.02 | 24.23 | **7.42** | −383.25 | **−366.44** | −288.6 | 32.8% | **27.0%** |
| `treasury_capgains…v2` | FY2022 | 303.14 | 77.96 | **13.00** | −381.10 | **−316.14** | −322.0 | 18.4% | **1.8%** |
| `cbo_opt47_ltcg_qdiv_2pp` | FY2025 | 92.46 | — | — | −92.46 | −92.46 | −103.3 | 10.5% | **10.5%** |

The rate channel is unchanged to the cent on every row. Wave 5's
`W5_preferential_margin.md` and Decision 3 are untouched.

### 8.3 The schedule: the count moved and nothing else did

Gains at death by DFA group are **identical before and after**, to twelve
significant figures — the swap changes how many people the flow is divided
across and no other property of the schedule:

| group | gains $B (both) | decedents before | **decedents after** | mean estate $M (both) |
|---|--:|--:|--:|--:|
| TopPt1 | 49.5099 | 408.5 | **3,384.2** | 176.917 |
| RemainingTop1 | 45.9550 | 3,676.8 | **30,457.7** | 23.831 |
| Next9 | 72.9238 | 36,767.9 | **304,577.5** | 5.103 |
| Next40 | 25.7078 | 163,412.9 | **1,353,677.7** | 0.948 |
| Bottom50 | 2.1132 | 204,266.1 | **1,692,097.1** | 0.062 |
| **total** | **196.2097** | **408,532** | **3,384,194** | — |

The level check holds at 1, 25, 200 and 400 slices: the sum over slices is
`gains_at_death_billions` exactly, as it was.

### 8.4 What the carve-outs are worth now

Ten-year death channel on the FY2025–2034 window, one relief switched off at a
time, before and after. Not additive — the per-donor exclusion sits after the
others — but it says where the channel went.

| variant | before | **after** | ratio |
|---|--:|--:|--:|
| no exclusion, carve-outs on | 427.53 | **345.93** | 0.809 |
| $1M exclusion | 303.00 | **121.48** | 0.401 |
| $5M exclusion | 162.35 | **47.70** | 0.294 |
| $1M, family business deferred | 133.12 | **24.87** | 0.187 |
| $5M, family business deferred | 35.17 | **10.87** | 0.309 |
| $1M, no carve-outs at all | 426.45 | **217.70** | 0.511 |

Read the ratio column: a channel with **no** fixed-dollar relief falls by 19%
(the statutory rate ladder and the §121 cap are the only size-dependent terms
left), one with a $1M exclusion by 60%, and one with a $5M exclusion by 71%.
**The whole of the difference is that a fixed dollar amount subtracted per
decedent bites 8.3× harder when there are 8.3× as many decedents**, which is
precisely why the count was worth fixing and precisely why fixing it alone is
half a correction (§8.7 finding 2).

### 8.5 Falsification checks

| §4 test | result |
|---|---|
| Any of the three rows outside this lane's band, or `cbo_opt47` moving | **clean** — all three on their predicted figure; `cbo_opt47` −92.46197 both |
| Any of the other 22 Tier-1 rows moving | **clean** — 23 of 26 identical |
| Within-25 below 22, class mean above 26, or a gate exiting non-zero | **clean** — 22 and 18.7; both gate commands exit 0 |
| Any of the 16 fitted or 39 reconstruction rows moving, or the donor matrix | **clean** — 0, 0, and byte-identical |
| Any of the 53 presets moving | **clean** — identical to four decimals |
| The level moving at any slice count | **clean** — exact at 1, 25, 200, 400 |
| A second constant creeping into the count | **clean** — pinned by `test_the_module_has_one_death_rate_and_not_two` |

`python scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 22` exits
**0**; the per-class floor exits **0**; `python
scripts/build_validation_headline.py --check` exits **0**.
`python scripts/check_readiness.py --strict` exits **2** on this branch **and on
`2d13e60`**, with byte-identical output — the Python 3.14 runtime warning and the
standing microdata warning, neither of them this lane's.
`python scripts/run_validation_dashboard.py` exits **1** on both trees for those
same two reasons and its output differs in exactly **one line**, the Tier 1
summary.

### 8.6 Shipped output

**No preset moves.** All 53 scored by stable id, identical to four decimals.

| Tailor input | before | **after** | move |
|---|--:|--:|--:|
| +2pp, all brackets | −$92.46B | −$92.46B | — |
| +5pp, all brackets | −$186.34B | −$186.34B | — |
| +5pp above $1M, step-up retained | −$48.03B | −$48.03B | — |
| 39.6% above $1M + eliminate step-up, $1M exclusion | −$653.38B | **−$450.68B** | **−31.0%** |
| 39.6% above $1M + eliminate step-up, $5M exclusion | −$491.72B | **−$393.57B** | **−20.0%** |
| constructive realization at death only, no exclusion | −$427.53B | **−$345.94B** | **−19.1%** |

The Decision 6 clause ships in the existing `gains_at_death_caption`, one
sentence, and it is keyed to the design because the sentence that makes sense of
a $1M exclusion does not make sense without one:

> … A $1,000,000 per-decedent exclusion then applies to what is left, not to
> the whole gain, and it is subtracted across a fitted distribution of estate
> sizes rather than from an average estate. **Those decedents are counted at an
> NCHS life-table death rate — about 3.4 million a year — rather than at a flow
> of estate dollars that implied 408,532, so a fixed exclusion reaches far more
> of the gain than it used to.** …

and, where the design states no exclusion, **"…so each one carries a gain of
ordinary size."**

### 8.7 Findings

**1 — The module was carrying two death rates, and that is a sharper statement
of the defect than the comparison with NCHS.** `death_exit_rate` (2.647%) has
priced the lock-in wedge and the accrued-gains stock's drift since Wave 2, in
the same file where the decedent count divided households by 0.3195%. The two
answer the same question — how fast does wealth leave at death — and differ by
**8.3×**. Nobody had put them side by side, and once they are, the swap needs no
appeal to NCHS at all: it is an internal consistency repair that the life table
then independently corroborates (3.38 million against roughly 3.09 million
deaths, where the old figure was short by 7.6×).

**2 — This is half of a two-sided correction, and the half that was authorised
is the one that makes `cbo_opt51` worse.** The count and the level come from the
*same* Poterba & Weisbenner ratio: `gains_at_death_share_of_net_worth` is
`estate_flow_rate × gain_share_of_estates` to a hundredth of a percent (the
residual is PW's printed 0.36 against 42.8/118.9 = 0.35996). Fixing the count
while holding the level spreads an unchanged $196.2B over 8.3× as many people,
so each gain shrinks, so the fixed-dollar reliefs and the statutory rate ladder
reach less of it — hence 20.3% → 35.5% on the one row that is *all* death
channel, and hence the improvement on both Green Book rows, which are dominated
by a rate channel the smaller death channel now over-shoots less. **The level is
the other half.** Held against `death_exit_rate`, PW's flow implies **0.372% of
the accrued-gains stock** where the stock's death exit is priced at **2.647%** —
a factor of **7.1** — and `cbo_opt51` under-predicts, so a larger level would
close it. How much of the 7.1 is PW's inter-spousal exclusion (which every
realization-at-death proposal shares, so it is *supposed* to be there) and how
much is the 1998 vintage is unmeasured, and it is the single most valuable thing
left in this channel.

**3 — The plan's own diagnosis was refuted before the code changed, and in the
sign.** §3 H5 sent this lane to grade the count by estate size so the implied
count at the top would fall toward SOI's 7,194. Read off the two tables it
named, the grading runs the other way: the wealthy are **older**, so they die at
a **higher** rate, and the size-graded tail rate is **2.840%** against 2.647%
net-worth-weighted and 1.646% head-weighted. Grading takes the top count to
**38,908** where the uniform swap takes it to **36,262** — both further from
7,194. The refutation is not an argument in a document; it is two CHECK-ONLY
rows in `accrued_gains_parameters.csv`, regenerable by
`scripts/build_capital_gains_data.py`, and a test that fails if their ordering
ever reverses.

**4 — Two of the plan's three pre-registered bands were unattainable, and saying
so before running is the whole value of pre-registering.** `biden_capital_gains_39`
could not reach 15 ± 8 because its rate channel alone is 24.4% above the target
with the death channel set to zero; `treasury…v2` could not *regress* to 22 ± 6
because since PR #126 it is scored on its own decade, where the model is **under**
on the rate channel and the death channel is what pushes it over — so shrinking
the death channel was always going to improve it. Both bands were written against
pre-#126 readings. A lane that had accepted them would have reported two
falsifications it had caused by arithmetic it could have checked in an hour.

**5 — The exclusion step went through Treasury's own figure and out the other
side, which is the clearest evidence yet that the count was the lever and that
it was not the only one.** The gap between the two Green Book rows is the
per-donor exclusion alone, $1M against $5M. On the common FY2025–2034 decade
the model paid **$82.3B** for that step on the five-class ladder (Wave 4),
**$85.0B** on the fitted distribution (Wave 7, *away* from Treasury's $33.4B,
which is how W7 knew dispersion was not the cause), and now **$9.40B**
(16.82 − 7.42). W7 predicted that roughly **doubling** the count would land on
$33.4B; the authorised constant multiplies it by **8.3** and overshoots by the
same kind of margin it started with. Since the two published rows are also on
different windows — which makes $33.4B an *understatement* of the step Treasury
paid — the overshoot is worse than $9.40B against $33.4B looks. **The step is
now a check on the level (finding 2), because a larger flow with the same count
would raise it again.**

**6 — The window offset shrank with the channel it discounts, and the
`treasury…v2` row's 1.8% is a bigger cancellation than its 18.4% was.** The
FY2022-window offset was 28.7 of 43.3 points (PR #126), 27.0 of 45.4 after PR
#132, and is now **14.9 of 16.7** — because the offset is mostly the death
channel's growth across three years, and the death channel is a fifth of what it
was. What is left is not accuracy: on its own decade the model books **$0.0B**
of revenue across FY2022–24 where Treasury books $66.0B (the model's enactment
year is a $61.4B transitory *loss* against Treasury's $7.7B gain, because the
module has no receipts lag) against **$316.2B** across FY2025–2031 where
Treasury books $256.5B. A 23% over-prediction on the later seven years and a
$66B hole in the first three net to 1.8%. **Read the annual path, not the
total**, and `scripts/window_offset_capgains.py` prints it.

**7 — A test calibrated on a wrong number can look like a correct test for
years.** `test_the_exclusion_is_no_longer_a_cliff` asserted that no $250,000
step of the per-donor exclusion removed more than a fifth of what was left. That
bound was not derived from anything; it passed because 408,532 decedents carried
the whole flow, so each one's gain was large enough that $250,000 barely reached
it. On the corrected count the first $250,000 removes a third. The test was
restated to the property it was *trying* to express and never did: the marginal
cost of an exclusion is the number of decedents still above it, which is itself
decreasing, so successive steps must remove **strictly less** each time —
**flats** are the signature of point masses and are what the test now forbids.
That is a stronger test than the bound it replaces and it holds at both counts.

**8 — `policies_core.py` needed no change at all, for the second wave running.**
`estimate_step_up_elimination_revenue` and `reachable_gains_per_decedent`
iterate whatever schedule `decedent_classes` hands them, so replacing the count
touched neither — as replacing five point masses with 609 quantile slices did
not in Wave 7. The seam between "how many estates, and how big" and "what a
proposal does to one" is in the right place, and this lane is a second piece of
evidence for it. §2 listed the file as taking a docstring; nothing in its
docstrings had gone stale, so it takes nothing.

### 8.8 What the lane did not do

- **The level of gains at death is unchanged** (finding 2). It is the other half
  of this correction and it is an owner decision with a document behind it.
- **The decedent universe was not chosen.** The authorised constant gives 3.38
  million, 9.5% above NCHS deaths — but PW's flow measures *non-spousal*
  estates, a universe smaller than all deaths, not larger. The alternatives were
  measured and recorded rather than taken: the crude adult life-table rate
  (1.6619%) gives 2,124,898 decedents, `cbo_opt51` at **32.1%** and the class at
  **17.7%**; the crude all-age rate (1.2910%) gives 1,650,702, **28.4%** and
  **16.9%**. Both score better than the authorised constant. **Picking the best
  of three is fitting a parameter to a benchmark**, which §1.1 of the plan
  forbids, so neither was taken and both are here.
- **The count is still uniform in wealth** — now as a measured choice (§1.3,
  finding 3) rather than an unexamined one.
- **Mortality is still uniform within a wealth class**, and the DFA still
  publishes net worth by age and by percentile group but not jointly. The
  size-graded CHECK row rests on a common-shape assumption that is stated on the
  row itself.
- **The SOI top-count check is not a check yet**, for a unit reason: SOI counts
  individual decedents' gross estates above a per-decedent threshold and the
  model counts households above a household threshold, so the model's count
  *should* exceed SOI's. Making it a real check needs SOI's own gross-estate
  distribution spliced onto the DFA's household one; `W7_decedent_ladder.md`
  §8.8 records the splice as unbuilt and SOI's own tail index (α 1.401 against
  the DFA's 1.526) as measured.
- **No target, record, shape input or CI threshold moved.** `preregistered.py`,
  `holdout.py`, `loo.py`, `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`
  and `validation-dashboard.yml` are untouched; the only `core.py` edit is the
  `known_limitations` prose for the three moved rows, which on `2d13e60`
  described the headcount as unfixed.
- **The CI gate is not re-derived, and both directions are recorded for the
  coordinator.** By the workflow's own rule the pooled ceiling stays at 20
  (`ceil(14.5 × 1.25) = 19 →` nearest 5 `= 20`) and the floor would *loosen* to
  21 (`22 − 1`); the per-class capital-gains ceiling would *tighten* to 24
  (`ceil(18.7 × 1.25)`). Three Wave C lanes move rows in parallel, so the
  re-derivation is one job after the wave, not three during it. Both commands
  exit 0 unchanged.
- **`fiscal_model/data/` is still invisible to the lint gate.** `.gitignore`
  carries a bare `data/` line, so `ruff check fiscal_model/ …` silently skips
  `capital_gains.py`. Checked by explicit path this lane's changes are clean and
  the four remaining findings are the `Optional[X]` style the file already used.
  W7 found this and left it; so does this lane, for the same reason — widening
  the gate is a repo-wide change with an unknown blast radius.
