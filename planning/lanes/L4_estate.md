# Lane L4 — Estate: a taxable-estate size distribution instead of a two-point blend

*Pre-registered 2026-09-02 against `main` @ `9a1e8bc`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §3 L4, under §4's rules and owner
Decision 1 (reported vs derived mode, accepted 2026-09-01). The closest
precedent is `planning/lanes/L5_amt.md`: a calibrated module gaining a derived
path, with the app default left on `reported` unless derived beats fitted.

## 1. Starting numbers

All from the branch point, `python scripts/run_loo.py --donor-matrix` and
`python scripts/cold_holdout.py` on `9a1e8bc`.

### Leave-one-out (the lane's yardstick)

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Estate | `extend_tcja_exemption` | 167.0 | 167.0 | 176.9 | **+6.0%** |
| Estate | `biden_estate_reform` | −450.0 | −450.0 | −244.9 | **+45.6%** |
| Estate | `eliminate_estate_tax` | 350.0 | 350.0 | — | not cross-validatable |

Estate module mean 25.8% (n=2 derivable, 1 excluded: the target is not a
published score and the machinery reproduces differences but not levels).
**Suite aggregate: 58.7% mean / 32.5% median over 18 derivable cases, 6/18
within 15%, 4 not cross-validatable.**

### Fitted (by-construction) errors for the same three benchmarks

| Benchmark | Target | Fitted model | Fitted err |
|---|--:|--:|--:|
| `extend_tcja_exemption` | $167B | $167.0B | **0.0%** |
| `biden_estate_reform` | −$450B | −$450.0B | **0.0%** |
| `eliminate_estate_tax` | $350B | $350.0B | **0.0%** |

### Battery aggregates

- Tier 1 (out-of-sample): **25 cases, 34.4% mean, 16.1% median, 12/25 within 15%, 16/25 within 25%.**
- Calibrated fitted tier: **33 policies, 2.8% mean, 32/33 within 15%.**
- Unfitted module reconstructions: **21 policies, 76.7% mean, 4/21 within 15%.**

## 2. What the lane changes

### 2.1 The defect

`estimate_taxable_estates` (`estate.py:209-269`) is **exactly invariant in the
exemption** below $6.4M. For any `E <= 6.4M` it sets

```
estates  = 19_000 * (6.4M / E)
mid_avg  =    4M  * (E / 6.4M)
```

so `estates * mid_avg == 76e9` for every `E`, and the two-regime top-tail blend
multiplies `mid_avg` by a constant in that branch, so `estates * blended_avg` is
invariant too. **Lowering the exemption therefore derives exactly zero
revenue**, and the whole `biden_estate_reform` LOO effect comes from the
40% → 45% rate change (195.9 × 1.125 = 220.4, difference 24.5/yr, ×10 = 245).
The same invariance is visible to users: `create_estate_exemption_change(3.5e6)`
scores **$0.0B** today.

The machinery is also wrong in level. Its implied baseline is **$195.9B/yr** at
the 2026 exemption against CBO's ~$50B — `loo.py:659-663` already records this
as the reason `eliminate_estate_tax` is not cross-validatable.

### 2.2 The replacement

A taxable-estate **size distribution**, fitted to IRS SOI *Estate Tax
Statistics*, Table 1, Parts I and II, transcribed into
`fiscal_model/data_files/estate/` with a provenance header.

The distributed quantity is the **estate tax base** `B = taxable estate +
adjusted taxable gifts` — the amount the exemption is actually subtracted from.
Its survival function is modelled as Pareto, `N(B > E) ∝ E^-α`, with mean excess
`E[B - E | B > E] = E/(α-1)`, so

```
Revenue(E, τ, y) = R_2026 · (τ/0.40) · (E/E_2026)^(1-α) · (1+g)^(y-2026)
```

`α` is estimated from SOI's own class structure, entirely within each filing
year and therefore scale-free (no wealth deflator is needed for the shape).
For each pair of adjacent size-class boundaries at or above that year's filing
threshold, with `N_j` taxable returns above boundary `j` and mean base
`m_j = M_j/N_j`, a Pareto implies `α = ln(N_j/N_{j+1}) / ln(m_{j+1}/m_j)`.
Across three filing years:

| filing year | threshold | boundaries | local α |
|---|--:|---|--:|
| 2010 (2009 deaths) | $3.5M | 3.5→5, 5→10, 10→20 | 1.667, 1.718, 1.842 |
| 2013 (2012 deaths) | $5.12M | 5→10, 10→20, 20→50 | 1.656, 1.740, 1.867 |
| 2024 (2023 deaths) | $12.92M | 20→50 | 1.680 |

**Pooled α = 1.7384** (n=7, range 1.656–1.867). That the same shape parameter
comes back from three regimes 14 years apart, with filing thresholds a factor of
3.7 apart, is the evidence that this is structure and not a fit.

Two further changes, both structural, neither fitted:

1. **A one-year receipts lag.** The estate tax on a year-*t* decedent is paid
   with a return due nine months after death (IRC §6075(a)), extendable six
   months (§6081); SOI's own Table 1 footnote states it as "generally, an estate
   files a federal estate tax return (Form 706) in the year after a decedent's
   death". So fiscal-year *y* receipts come from year *y−1* deaths, and the
   effect is computed on a **year-indexed exemption path** rather than one
   window-flat annual. This makes FY2025 and FY2026 zero for the TCJA extension
   (2024 and 2025 decedents face the TCJA exemption either way) and FY2025 zero
   for the Biden reform.
2. **Kopczuk & Slemrod (2003), "Dying to Save Taxes"** replaces
   `planning_elasticity = 0.15` with one frozen, cited reported-estate
   elasticity with respect to the net-of-tax share. Both LOO factories set the
   behavioural elasticities to 0.0, so this moves no benchmark; it is the app's
   generic estate paths that change.

Plus owner Decision 1, implemented module-locally exactly as L5 did in
`amt.py`: `EstateTaxPolicy.mode` of `reported` (fitted annual) or `derived`
(structural path); `derived` is the default in the held-out path, the app and
the by-construction scorecard stay on `reported` unless derived beats fitted.

### 2.3 The level anchor

One number, and it is not a benchmark target: `BASELINE_ESTATE_DATA
["revenue_baseline_2026"] = 50.0`, already in the module, documented as CBO's
projection of estate-tax revenue once the exemption drops. It replaces **four**
fitted anchors (7,000 / 19,000 estates and $8M / $4M averages) plus three
top-tail blend constants. Neither $167B nor $450B enters anywhere.

It is cross-checkable bottom-up from SOI and I am registering the check as part
of the prediction: FY2010's $13.22B of net estate tax at a $3.5M exemption,
scaled by deaths (2.44M in 2009 → ~3.3M) and by household net worth per
decedent (~2.2× over 2009–2024), extrapolated down the fitted Pareto from
$3.5M-of-2009 to $6.4M-of-2026, gives **≈ $47B** — 6% from CBO's $50B.

## 3. The prediction

Point predictions from the arithmetic in `l4_proto.py`, before the module code
exists. The LOO engine books an estate annual with growth 0, so a LOO
ten-year total is ten times the window-average annual.

| Row | Now | Predicted | Band |
|---|--:|--:|---|
| LOO `extend_tcja_exemption` | +6.0% | **+9.9%** | +5% to +15% |
| LOO `biden_estate_reform` | +45.6% | **+5.0%** | −5% to +15% |
| Estate module mean | 25.8% | **~7.5%** | 5% to 12% |
| LOO suite mean (n=18) | 58.7% | **~56.7%** | 55% to 58% |
| LOO suite within 15% | 6/18 | **7/18** | 7/18 |
| `eliminate_estate_tax` | not x-val | **not x-val** | unchanged |

Derived ten-year totals: extend **$183.6B** (window-average annual −$18.36B,
eight non-zero years), Biden **−$427.5B** (window-average annual +$42.75B, nine
non-zero years).

### Rows I expect NOT to move

- **No Tier 1 row.** No pre-registered out-of-sample case runs `EstateTaxPolicy`.
  Tier 1 stays at 34.4% / 16.1% / 12 / 16 exactly.
- **No calibrated (fitted) row.** The scorecard and the app stay on `reported`,
  so the fitted tier stays at 2.8% over 33 with 32/33 within 15%.
- **No unfitted-reconstruction row.** 21 policies, 76.7%, unchanged.
- **No other LOO module.** Payroll, AMT, Credits, Expenditures and Capital Gains
  share no code with `estate.py`.
- **App preset output.** `create_tcja_estate_extension`,
  `create_biden_estate_proposal`, `create_warren_estate_proposal` and
  `create_eliminate_estate_tax` all carry a fitted annual and stay in `reported`
  mode, so every shipped estate preset scores exactly what it scores today.

### What I expect to move that the plan did not name

`create_estate_exemption_change` — the app's generic "set the estate exemption
to $X" path — has no fitted annual, so it reads the machinery directly and
today returns **exactly $0** for any exemption at or below $6.4M. It will start
returning a real number. That is a user-facing change and it is a bug fix, not
a recalibration.

### Where I expect to be wrong, stated up front

The two carried targets are **not jointly attainable by an exemption-and-rate
model at any single Pareto shape**. Holding the level fixed, the ratio
`biden / extend` that the model can produce is
`(1.125·(6.4/3.5)^(α−1) − 1) / (1 − (6.4/14.4)^(α−1))`, which is 1.56 at α=1.5,
1.67 at α=1.74 and only reaches the 450/167 = 2.70 the targets demand at
**α ≈ 2.6** — far outside anything SOI supports. The reason both rows
nonetheless land inside 15% below is the **year-indexed path**, not the shape:
the Biden reform's first scored year replaces the 2025 TCJA exemption rather
than the post-sunset one, and the baseline exemption then grows while $3.5M does
not. If the outturn misses, the year path is where to look first, and I would
rather record that now than discover it afterwards.

The second thing I expect to be wrong is the level, and by a knowable amount:
the model's implied estate tax at a $12.92M exemption is **$29.8B** in 2026
terms, about **$27.3B** deflated to 2023, against SOI's actual FY2024 net estate
tax of **$23.3B** — roughly 17% high. CBO's $50B may carry gift tax that SOI's
Table 1 does not. I am not adjusting for it.

Anything that moves outside this list is a finding, and gets written into §4.

## 4. Outturn

*Appended 2026-09-02, after the code. Numbers from `python scripts/run_loo.py
--donor-matrix` and `python scripts/cold_holdout.py` on the finished branch.*

### Leave-one-out

| Case | Official | By-constr | LOO before | LOO after | Err before | Err after |
|---|--:|--:|--:|--:|--:|--:|
| `extend_tcja_exemption` | 167.0 | 167.0 | 176.9 | **199.0** | +6.0% | **+19.2%** |
| `biden_estate_reform` | −450.0 | −450.0 | −244.9 | **−457.2** | +45.6% | **−1.6%** |
| `eliminate_estate_tax` | 350.0 | 350.0 | — | — | not x-val | not x-val |

Estate module mean 25.8% → **10.4%**. Suite aggregate 58.7% → **57.0%** mean,
median 32.5% → **25.3%**, **6/18** within 15% (unchanged), 18 derivable and 4
not cross-validatable (unchanged). Ceiling 75%: passes.

### Against the pre-registration

| Row | Predicted | Actual | |
|---|--:|--:|---|
| LOO `extend_tcja_exemption` | +5% to +15% | **+19.2%** | **missed — see finding 3** |
| LOO `biden_estate_reform` | −5% to +15% | **−1.6%** | in band |
| Estate module mean | 5% to 12% | **10.4%** | in band |
| LOO suite mean | 55% to 58% | **57.0%** | in band |
| LOO suite within 15% | 7/18 | **6/18** | **missed** (same cause) |
| `eliminate_estate_tax` | not x-val | **not x-val** | as registered |
| Tier 1 | 34.4% / 16.1% / 12 / 16, unmoved | **unmoved** | as registered |
| Calibrated fitted tier | 2.8%, 32/33, unmoved | **unmoved** | as registered |
| Unfitted reconstructions | 21 at 76.7%, unmoved | **unmoved** | as registered |
| Other LOO modules | unmoved | **unmoved** | as registered |
| App presets | unmoved | **unmoved** | as registered |
| `create_estate_exemption_change` | stops returning $0 | **$0.0B → +$35.4B/yr at $3.5M** | as registered |

### What the module now says

| Quantity | Before | After |
|---|--:|--:|
| Implied 2026 estate-tax revenue at the $6.4M exemption | ~$195.9B | **$47.6B** |
| Taxable estates, 2026 at $6.4M | 19,000 (fitted anchor) | **10,981** |
| Taxable estates, 2026 at $14.4M | 7,000 (fitted anchor) | **2,682** |
| Average taxable amount at $6.4M | $25.8M (blended) | **$11.70M** |
| `create_estate_exemption_change(3.5M)` annual | **$0.0B** | **+$35.4B** |

Fitted constants deleted, not left unused: `taxable_estates_tcja`,
`taxable_estates_post_tcja`, `avg_taxable_amount_tcja`,
`avg_taxable_amount_post_tcja`, `top_tail_threshold`, `top_tail_count_share`,
`top_tail_value_share`, `top_tail_avg_multiplier`. What replaces them is
`alpha = 1.73843` (seven local estimates pooled from the transcribed file, range
1.656–1.867), SOI's FY2024 anchor row (2,663 taxable returns, $62.894B of base
above the exemption, $23.313B of net estate tax), a mean-excess ratio of 1.828
and an effective-rate factor of 0.9267 — every one of them read out of the CSV
at run time rather than typed into the module.

### Reported vs derived, per benchmark

| Benchmark | Carried target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `extend_tcja_exemption` | $167B | $167.0B | +0.0% | **$199.0B** | +19.2% |
| `biden_estate_reform` | −$450B | −$450.0B | +0.0% | **−$457.2B** | −1.6% |
| `eliminate_estate_tax` | $350B | $350.0B | +0.0% | **$471.3B** | +34.7% |

**App default stays `reported`** under Decision 1's own rule: derived does not
beat fitted on the carried benchmarks. Nothing a user sees changes — the four
shipped estate presets score 167.0 / −450.0 / −2,600.0 / 350.0 exactly as
before. The scorecard stays on `reported` too, so the calibrated tier keeps
measuring bookkeeping rather than quietly becoming a second copy of the LOO
column.

### Findings

1. **The two carried targets are not jointly attainable, and the year path is
   what gets close anyway.** Holding the level fixed, a flat-window
   exemption-and-rate model can only produce
   `biden / extend = (1.125·(6.4/3.5)^(α−1) − 1) / (1 − (6.4/14.4)^(α−1))`,
   which is **1.67** at α = 1.738 and needs **α ≈ 2.6** to reach the 450/167 =
   2.695 the targets demand — far outside anything SOI supports. The shipped
   model returns **2.30**, and the difference is entirely the year-indexed
   path: the Biden reform's first live fiscal year prices 2025 decedents, whose
   baseline is still TCJA's $13.99M exemption, and the baseline exemption then
   grows at inflation while $3.5M does not. Registering the ratio argument
   before writing the code is what made it obvious that a shape fix alone could
   not do this.
2. **Growth is the lane's biggest lever and the data pulls two ways.** Fitting
   the level *and* the growth jointly to SOI's own three filing years returns
   **6.81%/yr** and reproduces SOI's history to within 8% in every year, because
   household net worth outgrew GDP badly over 2009–2023. Projected forward that
   gives `extend` **+66.9%** and `biden` **+40.3%**, which no published CBO or
   JCT estate estimate is consistent with. The module ships nominal GDP growth
   (**3.82%**, the app's own `CBOBaseline.nominal_gdp` compound rate), i.e.
   wealth held at a constant ratio to GDP, and therefore **over**-states what
   was actually collected from 2009 decedents by 109% and from 2012 decedents
   by 56%. That is a known, deliberate and unresolved bias; it is pinned by
   `test_growth_is_the_baseline_gdp_rate_not_the_rate_soi_history_implies` so a
   data refresh cannot turn it into an accident. The full surface:

   | growth | 2026 base | `extend` | `biden` |
   |---|--:|--:|--:|
   | 0.0% | $39.2B | 129.9 (−22.2%) | 306.2 (−31.9%) |
   | 2.0% | $43.4B | 162.3 (−2.8%) | 377.0 (−16.2%) |
   | 3.0% | $45.7B | 181.5 (+8.7%) | 419.0 (−6.9%) |
   | **3.82% (shipped)** | **$47.6B** | **199.0 (+19.2%)** | **457.2 (−1.6%)** |
   | 5.0% | $50.5B | 227.3 (+36.1%) | 519.0 (+15.3%) |
   | 6.81% (SOI-fitted) | $55.2B | 278.7 (+66.9%) | 631.1 (+40.3%) |

3. **The pre-registration's growth semantics were wrong, and correcting them
   cost the lane its best-looking row.** §3 was computed on the module's legacy
   convention that *revenue* grows at 3%/yr. The object that grows is the size
   *distribution*, so revenue at a fixed exemption grows at `α` times it — real
   bracket creep, and the reason the baseline path (whose exemption is indexed
   at ~2.8%/yr) still comes out near 3%. Fixing that and taking the rate from
   the repository's own CBO baseline instead of the module's ambiguous 3% moved
   `extend` from the registered +9.9% to +19.2%. **The pre-registered
   configuration scores better on both rows** (3.0%: +8.7% and −6.9%) and was
   not shipped. That is the strongest evidence available that the choice was
   made on structure and not on the error it produces.

   The same pass changed the **level anchor**, and §2.3 above is therefore a
   record of the plan rather than of the code. §2.3 registered CBO's carried
   `revenue_baseline_2026 = 50.0` as the one level input, with SOI as a check.
   The shipped module reverses them: the level is SOI's own FY2024 anchor row,
   so the whole model comes out of one transcribed file plus one baseline
   growth rate, and CBO's $50B becomes the external check — which it passes at
   **$47.6B, 4.8% low**. The level check §3 registered ("$27.3B against SOI's
   $23.3B, roughly 17% high") is consequently no longer a prediction: the model
   reproduces that row **exactly**, by construction, because it is now the
   anchor. The check that replaced it is the harder one, and it is finding 2's
   backcast to the two years the model does *not* anchor on.
4. **`extend_tcja_exemption`'s +6.0% was two large errors cancelling.** The old
   machinery had a level four times too high and an exemption response of
   exactly zero below $6.4M; the extension's whole effect came from the
   branch structure at the high end. Correcting both removes the cancellation,
   which is the same thing L2 recorded for `fra_2023_discretionary_caps`
   (6% → 12% after a correct spend-out). A row that gets worse when two
   compounding defects are repaired was not measuring accuracy.
5. **The invariance was user-facing, not only a validation artefact.**
   `create_estate_exemption_change` returned **exactly $0.0B** for every
   exemption at or below $6.4M — the app scored "cut the estate exemption to
   $3.5M" as free. It now returns +$35.4B/yr, and the sign flips correctly
   above the baseline (−$24.3B/yr at a $20M exemption).
6. **`eliminate_estate_tax` is now derivable and stays excluded for the other
   reason.** Its old exclusion cited two things: an unpublished target *and* a
   machinery that "reproduces differences but not revenue levels". The second
   is no longer true — the model's 2026 baseline is $47.6B against CBO's ~$50B
   — so only the first is carried. Derived it scores **$471.3B** against the
   $350B model estimate (+34.7%), reported here as a diagnostic and folded into
   nothing.
7. **The tax base is not a pure Pareto, and the module papers over it with a
   second SOI statistic.** The count slope across SOI's class boundaries is
   α = 1.738, but the mean excess at the anchor implies 1 + 1/1.828 = **1.547**
   — the tail is fatter in value than the count slope says. The module reads
   the mean-excess ratio off SOI directly rather than deriving it from α, which
   makes the count and the average both right at the anchor (2,663 returns
   reproduced exactly) instead of splitting a correct aggregate 25% wrongly.
   The honest fix is to integrate the classes piecewise rather than fit one
   shape, and that is the next real structure this module is missing.
8. **Not a benchmark, but a large gap worth writing down:**
   `create_warren_estate_proposal` carries a fitted −$2,600B from PWBM and
   derives **−$663.6B**. The module prices a 55% flat rate on a $3.5M
   exemption; PWBM's $2.6T scores a package with a separate wealth tax. The
   preset is not in `ESTATE_TAX_VALIDATION_SCENARIOS` so nothing in the battery
   sees this, but the two numbers are not estimates of the same policy.

### What the lane did not do

- Did not touch any target, `preregistered.py`, `cold_holdout.py`,
  `run_loo.py`, `loo.py`'s leakage guard or `LEAKAGE_TOLERANCE`,
  `tests/test_preregistration.py`, or any CI threshold. `benchmark_sources.py`
  and `target_revisions.py` are untouched.
- Did not add a per-benchmark constant. The module gained one data file, one
  pooled shape statistic, one anchor row, one growth rate taken from the app's
  own baseline, one receipts lag with a statutory citation, and one literature
  elasticity — and lost eight fitted constants.
- Did not model the **portability** of a deceased spouse's unused exclusion.
  `modify_portability` and `portability_cap` are still declared and never read,
  and portability is why the effective per-couple exemption is up to twice the
  per-person figure the module prices. SOI's Table 1 carries a "Deceased
  spousal unused exclusion" column this transcription does not take, which is
  where that work would start.
- Did not model **gift tax**. The base includes adjusted taxable gifts, as it
  must, but a policy that changes the estate exemption also changes lifetime
  giving, and nothing here responds to that.
- Did not touch the **graduated rate schedule**. Every rate here is a single
  top rate scaled proportionally, which is why `biden_estate_reform`'s target —
  a bill with 50/55/65% brackets above $10M/$50M/$1B — remains an upper bound
  on what this module can construct, exactly as `benchmark_sources.py` says.
- Did not raise the question of whether the `biden_estate_reform` target should
  move from $450B to JCT's published $429.6B. It is a `line_item_differs` row
  and that is the provenance lane's call, not this one's.
