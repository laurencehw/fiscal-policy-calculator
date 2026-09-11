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
