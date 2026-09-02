# L1 — Capital gains: realizations base, decomposed elasticity, lock-in, gains at death

*Wave 2 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §3 L1.
Pre-registered 2026-09-02 against `main` @ `9a1e8bc`, **before** any code in this
lane changed. The outturn is appended at the bottom as the lane's last commit.*

The plan scoped L1 as three lanes; they share the same two files, so this is one
lane landing the four defects in sequence — base, elasticity, lock-in, gains at
death — one commit each. Nothing below is a promise of attainment (§1.5 forbids
that). Every number in §4 was computed by hand from published figures *before* a
line of module code changed, so a reader can check whether the mechanism behaved
the way the lane said it would.

## 1. Starting point (measured on `9a1e8bc`)

`python scripts/cold_holdout.py --json`:

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| out-of-sample (Tier 1) | 25 | **34.4%** | 16.1% | 12 | 16 |
| calibrated reference (fitted) | 33 | 2.8% | 0.3% | 32 | 33 |
| uncalibrated reconstruction | 21 | 76.7% | 41.0% | 4 | 7 |

Tier 1 error mass is **859.5**. The four capital-gains rows carry **479.4 of it
— 55.8%**, the largest single mass in the tier after Wave 1 (§5.1):

| policy_id | official ($B) | model ($B) | abs err |
|---|--:|--:|--:|
| `treasury_capgains_39_plus_stepup_elim` | −322.0 | −816.6 | **153.6%** |
| `biden_capital_gains_39` | −288.6 | −699.4 | **142.3%** |
| `cbo_opt47_ltcg_qdiv_2pp` | −103.3 | −205.7 | **99.1%** |
| `cbo_opt51_gains_at_death` | −536.1 | −83.7 | **84.4%** |

`python scripts/run_loo.py --donor-matrix`: 18 derivable, **58.7%** mean, 32.5%
median, 6/18 within 15%, 4 not cross-validatable. The `CapitalGains` module is
**171.2%** (n=3):

| case_id | official ($B) | by-construction ($B) | LOO ($B) | signed err |
|---|--:|--:|--:|--:|
| `cbo_2pp_all_brackets` | −70.0 | −83.4 | −154.3 | **−120.5%** |
| `pwbm_39_with_stepup` | +33.0 | +30.1 | −89.3 | **−370.5%** (sign flip) |
| `pwbm_39_no_stepup` | −113.0 | −113.0 | −138.6 | −22.6% |

Donor matrix, mean |error| on the *other two* cases when each scenario donates
its behavioural tuple: `cbo_2pp_all_brackets` 104.8, `pwbm_39_with_stepup`
**29.7**, `pwbm_39_no_stepup` 333.2. `pwbm_39_with_stepup` — the one carrying
`step_up_lock_in_multiplier: 5.3` — is the module's de facto answer key, exactly
as §3 L1 said.

## 2. The four defects, and the one bug underneath them

### 2.1 The bug the plan did not name

`CapitalGainsPolicy.estimate_behavioral_offset` applies
`R1 = R0 · ((1−τ1)/(1−τ0))^ε` — an elasticity with respect to the **net-of-tax
rate** — using ε values (0.8 / 0.4, and the literature values Decision 3 froze)
that the capital-gains realization literature reports with respect to the **tax
rate**. CRS R48562 (*Boundaries on the Long-Run Realization Response to Changes
in Capital Gains Taxes*, 2025) states the definition twice: the elasticity is
"the percentage change in realizations divided by the percentage change in the
capital gains tax rate", and the functional form behind it is semi-log,
`R = B·exp(−b·t)`, so that `ε(t) = b·t`.

Applying a tax-rate elasticity as a net-of-tax elasticity understates the
response by roughly `(1−τ)/τ`. At τ = 23.8% the module's nominal ε = 0.8 is an
effective **tax-rate** elasticity of 0.8 × 0.238/0.762 = **0.25** — a third of
what any study in CRS's Table 4 reports. That single unit error is most of why
every rate-change row over-predicts.

Two consequences follow from the correct form, and both are structure the module
does not currently have:

- **ε rises with the rate.** `ε(τ) = b·τ`, so the top bracket responds more than
  the 15% bracket to the same percentage-point change — "differing by whether
  the taxpayer faces the top bracket", with no second parameter.
- **There is a revenue-maximizing rate.** `τ* = 1/b`. Decision 3's frozen
  Dowd–McClelland–Muthitacharoen (2015) persistent elasticity of −0.72,
  evaluated at CRS's 22% reference rate, gives `b = 0.72/0.22 = 3.273` and
  `τ* = 30.6%`. JCT's own coefficient is **3.1** (CRS R48562 p. 8, supplied by
  the committee), i.e. τ* = 32.3%; Treasury's is 0.72 at 22%, the same as DMM's.
  The frozen literature value and the official estimators' working coefficient
  agree to within 6%, which is the cross-check that this is a unit fix and not a
  tuning knob.

### 2.2 Base

`CapitalGainsBaseline` prices realizations off a 3-row Tax Foundation aggregate
(`taxfoundation_capital_gains_2022_2024.csv`) times a hand-written 10-rung share
ladder, and a hand-written statutory rate proxy. At threshold 0 it returns 100%
of *total realized gains* at a flat 15.5%. Replaced by **IRS SOI Table 3.5**
(*Returns with Modified Taxable Income: Tax Generated, by Size of AGI and Tax
Rate*), which publishes, for every AGI class, the income actually taxed at each
preferential rate — 0%, 15%, 20%, 25% and 28% — and the tax it generated. A
+2pp change then applies to each bracket's own price.

### 2.3 Elasticity

`short_run 0.8 / long_run 0.4 / transition 3` is deleted. In its place:
`R1 = R0 · exp(−b·(τ1−τ0))`, with `b_persistent = 0.72/0.22` and
`b_transitory = 1.20/0.22` (DMM 2015, frozen by Decision 3; Agersnap–Zidar
(2021) is named in the docstring as the alternative and never used). The
transitory coefficient is a *retiming* response, so it applies in the enactment
year only, and only to the share of each AGI class's preferential base that has
a timing margin — realized **long-term** gains, from SOI Table 1.4A — not to
qualified dividends or capital-gain distributions, which cannot be retimed.

### 2.4 Lock-in

`step_up_lock_in_multiplier` (5.3× and its 2.0 default) and
`no_step_up_avoidance_multiplier` are deleted, as are the three per-case
behavioural tuples in `validation/scenarios.py`. Lock-in instead falls out of an
accrued-gains stock with a realization hazard: the stock `A` is realized at rate
`h = R/A` and exits at death at rate `m`, so a share `ω = m/(h+m)` of accrued
gains escapes tax entirely while step-up is available. The tax price of
realizing now is therefore `τ(1 − (1−ω)d)` with step-up and `τ(1 − d)` without,
where `d` discounts the deferral over the expected holding horizon `1/(h+m)`.
DMM estimated their elasticity under current law, so `b` is the with-step-up
value and the without-step-up value is the smaller one that ratio implies. No
constant is keyed to any benchmark.

### 2.5 Gains at death

`gains_at_death_billions = 54.0` and the ad-hoc exemption share
`min(0.9, 0.4 × $M)` are deleted. Replaced by decedent wealth × unrealized-gain
share × an exemption schedule, indexed to the asset stock:
`estates(t) = W(t) · 0.3196%` and `gains(t) = estates(t) · 36%`, both from
Poterba & Weisbenner (2001) Table 8 over 1998 household net worth, with `W(t)`
the Financial Accounts / DFA household net worth grown at its own 1998–2024
rate. The exemption is applied per decedent across estate-size classes using
Avery, Grodzicki & Moore (FEDS 2013-28) Figure 1 — the unrealized-gain share of
the gross estate, 12.8% under $2M rising to 54.9% over $100M.

### 2.6 The stocks-are-indexed, flows-are-not rule

Pre-registered because it decides two rows: the **death** channel is anchored on
a published *stock* (household net worth) and is grown year by year, because
§3 L1 asks for it to be "indexed to grow with the asset stock". The
**realization** channel is anchored on an observed *annual flow* (SOI) and is
held at its observed level, because the module has no realizations projection
and inventing a growth rate for a flow is what Phase D found had cost the estate
(~10%) and payroll (12.2%) modules their accuracy (`scoring_engine.py:341-349`).
Growing the realizations base at the same 5.79% would move `cbo_opt47` from a
predicted ~30% to ~150%; the rule is stated here, before the run, so that choice
cannot be read as having been made after seeing which way it scored.

## 3. Data transcribed

All land in `fiscal_model/data_files/capital_gains/` with provenance headers,
regenerable by `python scripts/build_capital_gains_data.py`.

| Quantity | Value | Source |
|---|---|---|
| Income taxed at each preferential rate, by AGI class, TY2022 and TY2023 | 2023 total $1,107.7B across 0/15/20%; $80.7B of it in the 0% bracket | IRS SOI Table 3.5, `22in35tr.xls` / `23in35tr.xls` |
| Net short-term and long-term gain by AGI class | TY2022, TY2023 | IRS SOI Table 1.4A, `22in14acg.xls` / `23in14acg.xls` |
| Household net worth, 2024:Q4 / 2022:Q4 / 1998:Q4 | $161.24T / $135.46T / $37.21T | Federal Reserve Distributional Financial Accounts (Z.1) |
| Net worth by percentile group, 2024:Q4 | top 0.1% $22.62T; 99–99.9 $27.42T; 90–99 $58.72T; 50–90 $48.49T; bottom 50 $3.99T | same |
| Net worth by age of head, 2024:Q4 | 70+ $50.95T; 55–69 $67.31T; 40–54 $32.28T; <40 $10.70T | same |
| Mortality by age band | <40 0.109%; 40–54 0.394%; 55–69 1.195%; 70+ 6.526% per year | NCHS, *United States Life Tables, 2022*, NVSR 74-02 Table 1 |
| Expected estates and unrealized gains at death | $118.9B and $42.8B per year, 1998; gains are **36%** of estate value | Poterba & Weisbenner (2001), Table 8 |
| Unrealized-gain share of the gross estate, by estate size | 12.8% (<$2M) → 54.9% (>$100M) | Avery, Grodzicki & Moore, FEDS 2013-28, Figure 1 |
| Realization elasticity, persistent / transitory, at a 22% rate | −0.72 / −1.2 | Dowd, McClelland & Muthitacharoen (2015), NTJ 68(3) |
| Elasticity definition and semi-log form; JCT's coefficient | ε = %Δrealizations / %Δ**tax rate**; `R = B·exp(−bt)`; JCT b = 3.1 | CRS R48562 (2025), pp. 1, 8, and Appendix A |
| Mean family net worth, 2022 | $1,059.47k — used only to derive the household count from the DFA aggregate | Federal Reserve, SCF 2022, Table 4 |

## 4. Pre-registered expectation

Hand-computed from the figures above, before any module code changed. The
`cbo_opt47` and `biden` arithmetic is written out in §2.1's terms so the reader
can redo it: bracket base × `exp(−b·Δτ)` × the reform rate, minus the baseline.

| Row | before | expected after | why |
|---|--:|---|---|
| `cbo_opt47_ltcg_qdiv_2pp` | 99.1% | **20–45%, now under-predicting** | Correct base ($1,107.7B in three priced brackets, not $1,368B at a flat 15.5%) and the semi-log form give ≈$7.2B/yr against JCT's ≈$10.3B/yr |
| `cbo_opt51_gains_at_death` | 84.4% | **0–25%** | The death channel becomes $185B/yr of gains at the 2024 anchor, grown at 5.79%, in place of a flat $54B; ≈$510–540B over the window against −$536.1B |
| `biden_capital_gains_39` | 142.3% | **5–45%** | At 43.4% the semi-log form puts the rate channel *past* τ*=30.6%, so it turns slightly negative (≈−$5.5B/yr); what is left is the death channel under a $5M exclusion, ≈$30B/yr |
| `treasury_capgains_39_plus_stepup_elim` | 153.6% | **30–80%** | Same shape with a $1M exclusion, so the death channel roughly doubles to ≈$52B/yr; this row is expected to improve least |
| **Tier 1 mean** | 34.4% | **18–26%** | mass 479.4 → roughly 100–200 |
| `cbo_2pp_all_brackets` (LOO) | −120.5% | **15–40%** | one frozen `b` |
| `pwbm_39_with_stepup` (LOO) | −370.5% | **40–90%, sign restored** | 43.4% is past τ*, so the model now loses revenue where PWBM loses revenue |
| `pwbm_39_no_stepup` (LOO) | −22.6% | **40–90%, worse** | the with/without-step-up wedge this lane derives is smaller than the 1.5× residual-avoidance multiplier being deleted |
| **LOO CapitalGains** | 171.2% | **40–70%** | §3 L1's registered target is <60% with one frozen tuple |
| LOO suite | 58.7% | **~40–46%** | only the three capital-gains rows move |
| calibrated fitted (n=33) | 2.8% | **unchanged** | no fitted annual is touched |
| unfitted reconstruction (n=21) | 76.7% | **unchanged** | contains no capital-gains case |

### 4.1 What would falsify the lane

- Any Tier-1 row outside the four moving at all. The diff touches
  `data/capital_gains.py`, `CapitalGainsPolicy`, the capital-gains branch of
  `scoring_engine.py`, and the capital-gains scenario tuples; nothing else
  scores through them.
- The fitted tier or the reconstruction tier moving by any amount.
- `cbo_opt51` still under-predicting by more than half. The whole point of the
  stock construction is that a $54B flow was an order of magnitude too small.
- `run_loo.py --donor-matrix` still showing one donor with a materially lower
  mean|others| than the others. After the tuples are deleted every donor is the
  same frozen set, so the three rows of the matrix must be identical.

### 4.2 Where the lane expects to be wrong

- **`cbo_opt47` will under-predict.** JCT's own path implies a realization
  elasticity near 1.5–2.0 at a 2pp change; DMM's frozen persistent 0.72 is well
  below that, and Decision 3 forbids reaching for a bigger number. Under-
  predicting by ~30% is the price of using the frozen value, and it is the
  opposite error from today's.
- **`treasury_capgains_39_plus_stepup_elim` improves least**, because its $1M
  exclusion puts three of the five decedent classes into tax and the model's
  decedent ladder is coarse — five DFA wealth groups, mapped to Avery-Grodzicki-
  Moore's eight estate-size rungs by group mean, with no within-group dispersion.
- **`pwbm_39_no_stepup` gets worse.** Its −22.6% today is bought with a 1.5×
  "residual avoidance" multiplier chosen after seeing the target. Deleting it
  and deriving the with/without-step-up wedge from the escape share costs that
  row accuracy, and the lane accepts that rather than keep a fitted constant.
- **The realizations base is not projected.** §2.6's rule keeps the flow at its
  observed SOI level; a realizations projection is the obvious next lane and
  would move every rate-change row.
