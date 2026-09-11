# Lane H8 — Tariffs: the GDP-feedback channel

Wave C of `planning/HIGH_STAKES_ACCURACY.md` (§1.2 rows 6 and 6b, §3 H8).
Branch `model/hs-c-h8-tariff-feedback`, worktree off `2d13e60`.

Owner decision ⑦ is taken: the five tariff presets move and their Decision 6
caption ships in this PR.

---

## 0. The plan's diagnosis is backwards, and this lane says so before it starts

§1.2 row 6 gives the residual cause for `trump_universal_10`'s 42.0% as "no
GDP-feedback channel: net/gross sits at 0.60–0.66 against a published 40–50%",
and §3 pre-registers the row improving to 20 ± 10 once the channel is added.

**Adding a GDP-feedback drag to the scored number moves every trade row further
from its target, not closer.** The five targets are *conventional* estimates —
Tax Foundation FF861 Table 3's conventional column, Tax Foundation's tracker,
CRFB's conventional range — and the model already sits **below** every one of
them in magnitude. A drag lowers the model further:

| Row | Target $B | Model $B | Error | Direction a drag moves it |
|---|---:|---:|---:|---|
| `trump_universal_10` | −2,171.1 | −1,258.5 | +42.03% | **worse** |
| `trump_china_60` | −650.0 | −278.4 | +57.17% | **worse** |
| `auto_tariff_25` | −386.2 | −182.2 | +52.81% | **worse** |
| `steel_tariff_25` | −60.0 | −52.9 | +11.89% | **worse** |
| `reciprocal_tariffs` | −1,500.0 | −1,396.8 | +6.88% | **worse** |

The 0.60–0.66 comparison is also a **denominator mismatch**. The module's
`net_to_gross_ratio` divides by gross duty *after* the import-demand response;
the knowledge snapshot's 40–50% divides by gross customs revenue *before* it
(`tariff_scoring_methodology.md` §"Putting it together": gross ≈ $3.0T →
$2.2T after the demand response → $1.7T after GDP feedback → $1.2–1.5T with
retaliation, "about 40–50% of gross"). On the snapshot's own denominator the
module already reads **0.589** for the universal tariff, not 0.65.

So the channel is real and it is missing, but it does not belong in the scored
number. What this lane does instead:

1. **Build the GDP-feedback channel** through `MacroModelAdapter`
   (`FRBUSAdapterLite`), fed by the tariff's own price-and-volume impulse, and
   report it as a **dynamic** figure beside the conventional score — the
   column structure FF861 itself publishes.
2. **Take retaliation out of the conventional score**, where it is a category
   error against every target the scorecard carries, and put it beside the
   GDP channel. This is the one change that moves the scored rows, and it
   moves four of them toward their targets and one past.
3. `reciprocal_coverage_rate = 0.50` → a partner-specific schedule.
4. The steel base → the Section 232 derivative chapter.

---

## 1. Mechanism

### 1.1 The conventional score is missing nothing and carrying one thing too many

`fiscal_model/data_files/trade/tariff_scoring_inputs.csv` already carries the
three FF861 columns as `external_check` rows: conventional **$2,171.1B**,
dynamic **$1,721.0B**, dynamic-with-retaliation **$1,443.0B**, plus a
retaliation revenue loss of **$278B** (FF861 p. 2) and the Table 2 tariff base
of **$2,747.0B** after the import-demand and noncompliance adjustments.

Read those five rows together and FF861's conventional estimate is:

```
conventional = base_after_demand_and_noncompliance × τ/(1+τ)
               × (1 − income_payroll_offset)
```

and nothing else. $2,747.0B × 0.10/1.10 = $249.7B of 2025 duty; FF861 p. 4
states its own income-and-payroll offset averages **26.2%** over the decade,
and 0.738 × $249.7B × ten years of a growing base is the $2,171.1B in Table 3.
**No retaliation, no GDP feedback.** Those are the second and third columns.

The module's conventional chain is the same object plus a retaliation term:

```
gross   = base · V(p) · Δτ/(1+Δτ)
avoid   = 0.05 · gross
offset  = 0.25 · (gross − avoid)
retal   = 0.25 · [0.30 · Δτ · export_base]        ← does not belong here
net     = gross − avoid − offset − retal
```

`estimate_behavioral_offset` drops the retaliation term. The conventional
net/gross ratio becomes **0.95 × 0.75 = 0.7125 for every tariff**, against
FF861's implied **0.738** — the 1.3pp difference is the module's 5% avoidance
haircut, which FF861 books inside its base as an 8% noncompliance rate rather
than as a separate line.

This is not a new convention: `assistant/knowledge/tariff_scoring_methodology.md`
already tells the Ask assistant that `include_retaliation=False` "gives a
strictly conventional (no-retaliation) score", and both knowledge files already
say the module carries no GDP feedback **"in the conventional score"**. The
defect is that the five validation scenarios and the five shipped presets score
with retaliation *on* against conventional targets.

### 1.2 The GDP-feedback channel, through the adapter that already exists

`FRBUSAdapterLite` takes a `MacroScenario` and returns
`cumulative_revenue_feedback`. Everything in the channel — the −0.7 tax
multiplier, the 0.75 decay, the 0.15 crowding-out term, the 0.65 monetary
offset and the 0.25 marginal revenue rate — is the adapter's, already
calibrated, already tested. **This lane adds no macro constant.** It supplies
one number the adapter does not have: the impulse.

The impulse is *not* the tariff's net receipts, which is what the generic
`EconomicModel` path uses today (`deficit_after_behavioral × tax_multiplier`).
A tariff withdraws more real income than it collects, for two reasons both
already in the module:

* the duty-inclusive price rises by the **whole** tariff (border pass-through
  frozen at 1.00 on Amiti–Redding–Weinstein and Fajgelbaum et al.), so
  households pay `Δτ` on every dollar that still arrives while the Treasury
  collects `Δτ/(1+Δτ)`; and
* the goods that stop arriving — `1 − V(p)` of the base — cost surplus and
  raise no duty at all.

So the impulse is the tariff's **own price and volume effect**:

```
impulse = border_pass_through · Δτ · (base · V(p))
```

which is the gross duty grossed back up by `(1 + Δτ)`. For the universal
tariff that is **$211.5B/yr** against net receipts of $125.9B/yr — 68% larger,
and that gap *is* the channel.

`policy_to_scenario` in `fiscal_model/models/macro_adapter_conversion.py` gains
one additive branch so any caller converting a scored policy to a
`MacroScenario` reads the tariff impulse rather than `−final_deficit_effect`.
Every other policy family is byte-identical.

### 1.3 `reciprocal_coverage_rate = 0.50` → a partner-specific schedule

The one number in `TRADE_BASELINE` that is not a measurement. "A flat 20pp on
half of goods imports" is not a policy anyone proposed. Executive Order 14257
(2 April 2025) set each partner's rate by a stated formula — the bilateral
goods deficit over goods imports from that partner, halved, floored at 10% —
and exempted the Annex II sectors already under Section 232 or announced for
it.

`TariffPolicy` gains an optional `rate_schedule` of `(partner, base, rate)`
rows. When it is set, every step of the chain sums over partners rather than
evaluating once at an average rate, which matters because the volume response
is **convex** in the rate: the elasticity doubles above a 30pp price change,
so an average rate understates the volume loss on the partners above the
threshold and overstates it on the partners below.

The schedule is built by `scripts/build_reciprocal_schedule.py` from 2024
Census bilateral imports and exports and transcribed to
`fiscal_model/data_files/trade/reciprocal_schedule.csv` with the Census series
and the Federal Register citation on every row. Canada and Mexico are out (they
were never in Annex I); the Annex II sectors are removed **partner by partner**,
because the exemptions are sectoral and the sectors are not evenly distributed
across partners.

The reconstruction is checked against sixteen of Annex I's own published rates,
which are transcribed as `external_check` rows and are **never inputs**.

### 1.4 The steel base → the Section 232 derivative chapter

`steel_aluminum_imports_billions = 58.9` is HS-72 plus HS-76. Section 232 also
reaches derivative articles, which sit in HS-73. Census 2024 puts HS-73 at
**$49.529B** of general imports paying **5.629%** in calculated duty, so the
combined base is **$108.417B** and the duty it already pays is **4.239%**.

Two corrections to the figures the repository has been carrying:

* "roughly triple the base" — repeated in `scenarios.py`, the CSV and §1.2 row
  6b — is wrong. It is **1.84×**.
* The whole chapter is an **upper bound** on the derivative base. Section 232's
  derivative annexes list articles at HS-10, not whole chapters, and
  Proclamation 10896 taxes a derivative article on its **steel content**, not
  its customs value. Neither the annex nor a steel-content share is
  transcribed here, so the truthful statement is a bracket: HS-72 + HS-76 is
  the floor, HS-72 + HS-73 + HS-76 at full value is the ceiling, and the lane
  ships the ceiling with the floor recorded.

---

## 2. Files

| File | Change |
|---|---|
| `fiscal_model/trade.py` | retaliation out of the conventional offset; `macro_demand_impulse()` and `estimate_gdp_feedback_revenue_loss()`; `rate_schedule`; steel base; `get_trade_summary()` gains FF861's three columns |
| `fiscal_model/data_files/trade/tariff_scoring_inputs.csv` | HS-73 promoted `context` → `model_input`; combined steel base and duty; the FF861 conventional identity as an `external_check` |
| `fiscal_model/data_files/trade/reciprocal_schedule.csv` | **new** — partner table with Census sources, plus Annex I published rates as `external_check` |
| `scripts/build_reciprocal_schedule.py` | **new** — builds the CSV from the Census API, SHA-recorded, re-runnable |
| `fiscal_model/models/macro_adapter_conversion.py` | one additive branch for the tariff impulse |
| `fiscal_model/ui/tabs/results_summary.py` | `tariff_net_caption` only — the Decision 6 caption, one self-contained function already owned by lane L8 (PR #99). H4 is rewriting this file's band code; no other function is touched |
| `fiscal_model/validation/scenarios.py` | Trade `limitations` and `notes` strings only. No target, no `calibrated_to_target`, no factory |
| `tests/test_trade.py`, `tests/test_trade_net_scoring.py`, `tests/test_trade_gdp_feedback.py` | updated and new |

Not touched: `preregistered.py`, `cold_holdout.py`, `run_loo.py`, `loo.py`,
`KNOWN_SCORES`, `CBO_SCORE_MAP` figures, `benchmark_sources.py`,
`target_revisions.py`, every CI threshold, `app_data.py`, `preset_ids.py`,
`policy_status.py`, `credibility.py`, `estimator_ranges.py`,
`data/capital_gains.py`, `policies_core.py`.

---

## 3. Pre-registered expectations

Registered on the **live** targets, on merged `main` at `2d13e60`, and derived
by hand from §1 before the code was written.

### 3.1 The five rows

| Row | Target $B | Before | Registered after | Error before → after |
|---|---:|---:|---:|---|
| `trump_universal_10` | −2,171.1 | −1,258.5 | **−1,369.9** | 42.03% → **36.90%** |
| `trump_china_60` | −650.0 | −278.4 | **−331.1** | 57.17% → **49.06%** |
| `auto_tariff_25` | −386.2 | −182.2 | **−203.9** | 52.81% → **47.20%** |
| `steel_tariff_25` | −60.0 | −52.9 | **−105.3** | 11.89% → **75.5%** (over) |
| `reciprocal_tariffs` | −1,500.0 | −1,396.8 | **−1,640.8** | 6.88% → **9.39%** (over) |

Three of the five are the retaliation term alone, and the arithmetic is the
decomposition's own: the conventional score is the measured net plus the
measured retaliation revenue loss (universal 125.85 + 11.14 = 136.99/yr;
China 27.84 + 5.27 = 33.11; auto 18.22 + 2.17 = 20.39), times ten, because
every trade preset books a flat annual.

`steel_tariff_25` is a **registered regression** and the largest single move in
the lane. Base 58.9 → 108.417, collected duty 3.06% → 4.239%, incremental rate
20.761pp, volume factor 0.79302, gross $14.780B/yr, conventional
0.7125 × that = **$10.531B/yr**. The target is −$60B, is untraceable, and was
examined-and-left twice (`EXAMINED_NOT_REVISED`); the floor base would have
given −$59.0B and a 1.7% error, which is exactly why it is worth saying that
the row's old 11.9% was a base three-quarters the size of the policy meeting a
target nobody can source.

### 3.2 The GDP-feedback channel

Registered for `trump_universal_10`, computed by hand against
`FRBUSAdapterLite`'s published parameters (impulse $211.48B/yr, tax multiplier
−0.7, decay 0.75, crowding 0.15, monetary offset 0.65, marginal rate 0.25):

* cumulative GDP level effect **−$893.8B**,
* **GDP-feedback revenue loss $223.5B** over ten years,
* dynamic score **−$1,146.4B**, dynamic-with-retaliation **−$1,035.0B**.

Cross-checks, none of them fitted to:

| Check | Published | This module | Source |
|---|---:|---:|---|
| Conventional net/gross (post-demand-response) | 0.738 | **0.7125** | FF861 p. 4 (26.2% offset) |
| Dynamic drag as a share of conventional | 20.7% | **16.3%** | FF861 $2,171.1B → $1,721.0B |
| Retaliation revenue loss, universal 10% | $278B | **$111.4B** | FF861 p. 2 |
| Dynamic-with-retaliation ÷ **pre-response** gross | 0.40–0.50 | **0.485** | `tariff_scoring_methodology.md` |

The last row is the plan's own cross-check, read on the denominator the
snapshot actually uses. Landing inside the band is a check, **not a target**:
no constant in this lane was chosen to put it there, and the band would have
been reported from outside just as plainly.

### 3.3 Reciprocal tariffs

Built from the Census pull before the code was written, so the expectation is
arithmetic rather than a guess. Non-USMCA goods imports **$2,349.0B** — the
same base the universal preset carries, which is the first consistency check —
less **$669.8B** of Annex II sectors removed partner by partner, leaves
**$1,679.2B** covered at a covered-weighted rate of **27.67%**. Summing the
chain over 230 partners gives gross duty **$230.293B/yr**, conventional
**$164.084B/yr**, ten-year **−$1,640.8B**.

Registered: **6.88% → 9.39%, over rather than under** — a regression on the
point anchor. Two things about it are registered in advance:

* the row's old 6.88% was **a base two-thirds the right size meeting a rate
  nobody proposed**, so the closeness was arithmetic rather than skill; and
* the model moves **into** the published range. `reciprocal_tariffs` carries
  [−$1,800B, −$1,400B] (Wave 4), and −$1,396.8B sits $3.2B *outside* the near
  bound. −$1,640.8B is inside it, so `within_published_range` should flip
  **False → True** and `distance_to_published_range_billions` 3.2 → 0.0 while
  the headline error gets worse. Both readings are correct and the lane
  reports both.

The reconstruction is checked against sixteen published Annex I rates before
any of it is used (§4). Reconstructed against published: China 0.3373/0.34,
Vietnam 0.4521/0.46, Taiwan 0.3173/0.32, Japan 0.2320/0.24, Korea 0.2498/0.25,
India 0.2618/0.26, Thailand 0.3578/0.36, Switzerland 0.3035/0.31, Malaysia
0.2347/0.24, Indonesia 0.3175/0.32, Cambodia 0.4874/0.49, Bangladesh
0.3641/0.37, Philippines 0.1734/0.17, and the 10% floor exactly for the United
Kingdom, Brazil and Australia. The EU as a bloc reads 0.1951 against a
published 0.20. Every one is within about a point, and every residual is the
same sign, because Annex I rounds up.

### 3.4 The tiers

* **Tier 1 (out-of-sample): byte-identical.** No tariff is in it.
* **Leave-one-out: byte-identical.** No tariff module is held out.
* **Distributional: byte-identical.**
* **Fitted calibrated: byte-identical at n=16, 1.5%.** No trade row is fitted.
* **Reconstruction tier**: the Trade sub-population moves **5 @ 34.2% → 5 @
  43.6%**; the tier's 39 rows move with it and nothing else does.

  That mean is registered as **worse**, and the reason is one row measured
  against a target nobody can source. On the **four rows that have a document**
  the mean improves **39.72% → 35.64%**; `steel_tariff_25` alone carries
  11.89% → 75.5%. Quoting the five-row mean without that split would hide the
  only thing the lane did to the rows.

### 3.5 Presets

All five move, all five by the same arithmetic as §3.1, and the Decision 6
caption ships in the same PR. No preset **label** and no `CBO_SCORE_MAP`
figure changes — every tariff label quotes the official score, which this lane
does not touch.

---

## 4. What would falsify the lane

* Any Tier 1, leave-one-out or distributional number moving at all.
* Any non-trade scorecard row moving at all.
* A trade row landing away from §3.1's hand arithmetic — that would mean the
  implementation is not the mechanism this file describes.
* The conventional net/gross ratio landing anywhere but **0.7125** for a
  policy with retaliation switched on *or* off — after this lane the flag must
  not touch the conventional score at all.
* `tests/test_offset_sign_contract.py` going red.
* The reciprocal reconstruction failing to reproduce Annex I's published rates
  for the large partners within a few points, which would mean the formula or
  the Census vintage is wrong rather than the policy.

---

## 5. Scope

Not this lane: the three untraceable trade targets (auto, steel, reciprocal)
— provenance work, and H9 has just been over the block; the `min_volume_factor
= 0.20` floor, still an unsourced constant; the retaliation channel's own
reduced form, which returns 2.5× less than FF861's estimate; wiring the tariff
impulse into `EconomicModel` so `score_policy(dynamic=True)` reads it (that
needs a hook in `economics.py`, outside this lane's files); and the Annex II
exemption list below HS-4.

---

## 6. Outturn

Measured on `3187d49`, against `2d13e60`. Every figure below is a re-run, not a
restatement of §3.

### 6.1 The five rows

| Row | Target $B | Before | After | Error before → after | Registered |
|---|---:|---:|---:|---:|---:|
| `trump_universal_10` | −2,171.1 | −1,258.5 | **−1,369.8** | 42.03% → **36.91%** | 36.90% |
| `trump_china_60` | −650.0 | −278.4 | **−331.1** | 57.17% → **49.06%** | 49.06% |
| `auto_tariff_25` | −386.2 | −182.2 | **−203.9** | 52.81% → **47.20%** | 47.20% |
| `steel_tariff_25` | −60.0 | −52.9 | **−105.2** | 11.89% → **75.28%** | 75.5% |
| `reciprocal_tariffs` | −1,500.0 | −1,396.8 | **−1,642.0** | 6.88% → **9.47%** | 9.39% |

**The hand arithmetic held on all five.** Three rows land to the second
decimal, because the retaliation term is the only thing that moved them and it
was already measured. `steel_tariff_25` lands 0.2 points below its registration
(the CSV carries HS 73 at $49.5B and 5.63% where Census reads $49.529B and
5.629%); `reciprocal_tariffs` 0.08 points above, because §3.3's hand sum used
all 230 partners where the shipped CSV folds 134 of them — $5.5B, 0.33% of the
covered base — into one remainder row at their own weighted rate.

### 6.2 Decomposition, per year

| Row | base | Δτ | V | gross | avoid | offset | **conventional** | n/g |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| universal | 2,349.0 | 0.1000 | 0.9003 | 192.26 | 9.61 | 45.66 | **136.98** | 0.7125 |
| china | 440.3 | 0.4907 | 0.3206 | 46.47 | 2.32 | 11.04 | **33.11** | 0.7125 |
| auto | 198.5 | 0.2301 | 0.7706 | 28.62 | 1.43 | 6.80 | **20.39** | 0.7125 |
| steel | 108.4 | 0.2077\* | 0.7930\* | 14.76 | 0.74 | 3.51 | **10.52** | 0.7125 |
| reciprocal | 1,679.2 | 0.2767\* | 0.6939\* | 230.45 | 11.52 | 54.73 | **164.20** | 0.7125 |

\* base-weighted averages across a schedule; the score sums row by row.

The identity is the point: **0.7125 for every tariff, in either direction**,
where it used to run 0.599 to 0.655 and the variation *was* the retaliation
term. Against FF861's implied 0.738 the gap is the module's 5% avoidance
haircut, which FF861 books inside its base as an 8% noncompliance rate.

### 6.3 The channels that are reported and not scored, over ten years

| Row | pre-response gross | conventional | GDP feedback | retaliation | dynamic | dyn + retal | drag as % of conventional |
|---|---:|---:|---:|---:|---:|---:|---:|
| universal | 2,135.5 | 1,369.8 | **223.5** | 111.4 | 1,146.4 | **1,035.0** | 16.3% |
| china | 1,449.4 | 331.1 | 68.2 | 52.7 | 262.9 | 210.2 | 20.6% |
| auto | 371.4 | 203.9 | 34.1 | 21.7 | 169.8 | 148.2 | 16.7% |
| steel | 186.3 | 105.2 | 17.1 | 10.7 | 88.1 | 77.4 | 16.3% |
| reciprocal | 3,546.2 | 1,642.0 | 327.4 | 220.3 | 1,314.6 | 1,094.3 | 19.9% |

**The cross-checks, none of them fitted to.**

| Check | Published | This module | Source |
|---|---:|---:|---|
| Conventional net/gross, post-demand-response | 0.738 | **0.7125** | FF861 Table 2, Table 3, p. 4 |
| GDP drag as a share of the conventional score | 20.7% | **16.3%** | FF861 $2,171.1B → $1,721.0B |
| Retaliation revenue loss, 10% universal | $278B | **$111.4B** | FF861 p. 2 |
| Dyn-with-retaliation ÷ **pre-response** gross | 0.40–0.50 | **0.485** | `tariff_scoring_methodology.md` |

The last row is the plan's own cross-check and it lands inside the band, on the
denominator the snapshot actually uses. **Only the universal row is comparable
to it** and the table says why: the band is quoted for a 10% universal tariff,
and the other four sit below it (0.145 to 0.415) because a 21-to-49pp rate
destroys far more of the pre-response base. Reporting the universal row's 0.485
as though it were the module's number would be the mistake the denominator
finding is about.

### 6.4 The tiers — §4's falsification test, passed

| Aggregate | Before | After |
|---|---|---|
| **Out-of-sample (Tier 1)** | 26 @ 14.7%, 15/26 ≤15%, 23/26 ≤25% | **byte-identical** |
| **Leave-one-out `--donor-matrix`** | 18 @ 35.7% | **byte-identical, 0 diff lines** |
| **Fitted calibrated** | 16 @ 1.5%, median 0.1% | **identical, entry for entry** |
| Reconstruction tier | 39 @ 55.5%, median 29.9%, 11/39 ≤15% | **39 @ 56.7%, median 36.9%, 10/39** |
| **Trade sub-population** | 5 @ 34.2%, median 42.0%, 2/5 | **5 @ 43.6%, median 47.2%, 1/5** |
| Distributional | 7 @ 0.00–5.86pp | unchanged |

`diff` on the whole validation dashboard is **two lines** — the reconstruction
summary and the Trade row — and `cold_holdout.py --json` differs only in the
five trade entries and the reconstruction summary they roll up into. Both CI
gates pass unchanged (`--max-mean-error 20 --min-within-25pct 22`, and the
eight-class floor), `build_validation_headline.py --check` passes, and
`check_readiness.py --strict` reports **0 fail** with the same five warnings
`main` carries, none of them a trade row: `steel_tariff_25` crossing into Poor
is not strict-blocking because it is `calibrated_to_target=False`, and it
carries the `known_limitations` note the gate requires.

**The Trade mean is registered as worse and it is worse.** On the **four rows
that have a document** it improves **39.72% → 35.66%** (registered 35.64%);
`steel_tariff_25` alone carries 11.89% → 75.28%, against a target that is
untraceable and has been examined-and-left twice. Quoting 43.6% without that
split hides the only thing the lane did to the rows.

**`reciprocal_tariffs` moved into its published range while its point error
grew**, exactly as registered. `within_published_range` **False → True** and
`distance_to_published_range_billions` **3.2 → 0.0** against
[−$1,800B, −$1,400B]; the 9.47% is a distance from Tax Foundation's $1.5T
anchor, one of three conventional estimates 29% apart. Both readings are
correct and the row now carries both.

### 6.5 The reciprocal reconstruction against Annex I

The load-bearing check, run before the schedule was used for anything. Sixteen
published rates, sixteen reconstructions, **maximum miss 0.80pp**, and every
residual the same sign because Annex I rounds up:

| Partner | Published | Reconstructed | Δ | Partner | Published | Reconstructed | Δ |
|---|---:|---:|---:|---|---:|---:|---:|
| China | 0.34 | 0.3373 | −0.0027 | Malaysia | 0.24 | 0.2347 | −0.0053 |
| Vietnam | 0.46 | 0.4521 | −0.0079 | Indonesia | 0.32 | 0.3175 | −0.0025 |
| Taiwan | 0.32 | 0.3173 | −0.0027 | Cambodia | 0.49 | 0.4874 | −0.0026 |
| Japan | 0.24 | 0.2320 | −0.0080 | Bangladesh | 0.37 | 0.3641 | −0.0059 |
| Korea | 0.25 | 0.2498 | −0.0002 | Philippines | 0.17 | 0.1734 | +0.0034 |
| India | 0.26 | 0.2618 | +0.0018 | United Kingdom | 0.10 | 0.1000 | 0 |
| Thailand | 0.36 | 0.3578 | −0.0022 | Brazil | 0.10 | 0.1000 | 0 |
| Switzerland | 0.31 | 0.3035 | −0.0065 | Australia | 0.10 | 0.1000 | 0 |

The EU as a bloc reads **0.1951** against a published 0.20. And the schedule's
own consistency check: its 230 partners' goods imports sum to **$2,349.0B**,
the non-USMCA base `create_trump_universal_10` already used — two measurements
read from the same Census series two different ways, agreeing to the decimal.

### 6.6 Presets moved — Decision 6

| Preset (stable id) | Official (unchanged) | Before | After | Move |
|---|---:|---:|---:|---:|
| `tariff-universal-10pct` | −$2,171.1B | −$1,258.5B | **−$1,369.8B** | +8.9% |
| `tariff-china-60pct` | −$650.0B | −$278.4B | **−$331.1B** | +18.9% |
| `tariff-auto-25pct` | −$386.2B | −$182.2B | **−$203.9B** | +11.9% |
| `tariff-steel-aluminum-25pct` | −$60.0B | −$52.9B | **−$105.2B** | +98.9% |
| `tariff-reciprocal` | −$1,500.0B | −$1,396.8B | **−$1,642.0B** | +17.6% |

**The other 44 presets score to the cent what they scored before**, in both
static and dynamic modes — 10 of 98 preset × mode rows moved and all 10 are
these five. No preset label and no `CBO_SCORE_MAP` figure changed.

The caption is `tariff_net_caption` in `results_summary.py`, L8's own function
from PR #99, edited in place rather than added beside — one function, no new
call line, and H4's band code untouched. It now reads, computed from the scored
result so it cannot drift from it:

> Net of offsets: \$1,922.6B of gross customs duty becomes \$1,369.8B of
> conventional receipts — a 0.71 net/gross ratio — after duty avoidance and the
> 25% income-and-payroll offset CBO, JCT and Treasury apply to any indirect
> tax. Import demand responds to the whole tariff (near-complete border
> pass-through). A dynamic estimate would take it further: \$223.5B of receipts
> lost as output falls and \$111.4B lost to retaliation, leaving \$1,035.0B.
> Published estimators report those as separate columns and so does this app —
> neither is in the headline.

**The caption says which of its figures is the headline**, because on a
dynamic run it is not. PR #144's review caught a caption reading
`final_deficit_effect` — which on a dynamic run also carries revenue feedback —
disagreeing with the headline above it by 69% on one preset. This caption never
restates the headline, but its conventional figure is not the headline on a
dynamic run either, so it labels itself "the figure before the dynamic feedback
the headline above applies" and says plainly that its own two channels are the
tariff module's, not the engine's. Two of the four caption tests run the same
preset through both engine modes and compare against `final_deficit_effect`.

### 6.7 Findings

1. **The plan's residual cause for rows 6 and 6b was backwards, and §0 said so
   before a file was opened.** A GDP-feedback drag moves every trade row
   further from a conventional target. The mechanism that moved them toward
   their targets is a *convention* correction the plan did not name.
2. **The 0.60–0.66 against 40–50% comparison was a denominator mismatch.** The
   module divides by gross after the demand response; the knowledge snapshot
   divides by gross before it. On the snapshot's denominator the module already
   read 0.589 rather than 0.65, and the missing channel was worth about a tenth
   of what the gap implied.
3. **The repository already knew retaliation was not a conventional channel and
   scored with it on anyway.** `tariff_scoring_methodology.md` tells the Ask
   assistant that `include_retaliation=False` "gives a strictly conventional
   (no-retaliation) score", and the five validation scenarios and five presets
   all ran with it `True` against conventional targets.
4. **"Including HS 73 would roughly triple the base" is wrong in three places.**
   $58.9B → $108.4B is **1.84×**. The claim sits in `scenarios.py`, the
   transcription CSV and §1.2 row 6b of the plan; the first two are corrected
   here.
5. **`steel_tariff_25`'s 11.9% was a base missing most of what the statute
   reaches, meeting a target nobody can source.** The floor base returns
   −$59.0B and 1.7%; the ceiling returns −$105.2B and 75.3%. Neither end is the
   policy, and the row cannot be read as accuracy in either direction.
6. **The reciprocal row got worse against its anchor and better against its
   range**, and only the second of those is a statement about the model:
   −$1,396.8B was $3.2B outside [−$1,800B, −$1,400B] and −$1,642.0B is inside
   it.
7. **A crowding-out sign infelicity in `FRBUSAdapterLite`, found by feeding it a
   revenue-raiser.** `gdp_change[t] *= (1 - crowding_effect)` with a
   deficit-*reducing* policy gives a factor above 1 applied to a negative GDP
   change, so lower debt makes the drag **larger** rather than smaller. It
   magnifies this lane's universal-tariff GDP channel by about 12% over the
   window. Pre-existing, affects every revenue-raiser run through the adapter,
   and outside this lane's files — carried over rather than fixed, because a
   fix would move the dynamic tab for policies this lane never looked at.
8. **The generic dynamic path feeds the adapter the wrong shock for a tariff**
   and still does on `score_policy(dynamic=True)`. `policy_to_scenario` now
   reads `macro_demand_impulse()`, but `EconomicModel` — which is what
   `dynamic=True` actually calls — reads `deficit_after_behavioral`, 68%
   smaller. Wiring it needs a hook in `economics.py`, outside this lane's files.

### 6.8 Deviations from §2

Two files outside the declared list were touched, both for prose that had
become false in the commit before, neither carrying a target, a range, a
provenance kind or a ledger entry:

- `fiscal_model/assistant/knowledge/tariff_scoring_methodology.md` and
  `yale_budget_lab_tariffs.md` — the "How this maps to the app" sections said
  the module nets retaliation into the score and lands at "60-65% of gross".
- `fiscal_model/validation/benchmark_sources.py` — **one sentence** of the
  reciprocal row's `sourcing_note`, which asserted that the module applies a
  flat ~20pp to half of goods imports where the publishers apply
  partner-specific rates. §2 promised this file would not be touched; leaving a
  shipped provenance note asserting something the previous commit made false
  was the worse of the two.

### 6.9 Carry-overs

- The crowding-out sign in `FRBUSAdapterLite` (finding 7).
- `EconomicModel` reading the tariff impulse (finding 8).
- The Section 232 derivative annex at HS-10, and a steel-content share, which
  would replace the bracket in §1.4 with a number.
- The Annex II exemption list below HS-4 — semiconductors and bullion are
  resolved at HS-4 here, critical minerals are not resolved at all.
- The retaliation channel is still a reduced form returning 2.5× less than
  FF861's own estimate for the same policy.
- `min_volume_factor = 0.20` is still an unsourced constant, and the reciprocal
  schedule's top rates (48.7%) come closer to it than any shipped case did.
- The auto, steel and reciprocal targets remain untraceable or a range;
  provenance work, and H9 has just been over this block.
