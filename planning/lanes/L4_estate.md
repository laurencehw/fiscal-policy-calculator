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

*Appended in the lane's last commit.*
