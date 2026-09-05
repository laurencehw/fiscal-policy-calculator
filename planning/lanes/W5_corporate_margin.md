# Wave 5 lane B — the corporate rate identity at the margin

*Pre-registered 2026-09-05 against `main` @ `1d35f1b`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §2.1's row "**Corporate rate at the
margin**" — `cbo_opt64` 47.1, mass 47, 3.6% of the pre-Wave-1 tier — carried
forward through §5.1's "Module revenue identities at the margin (payroll ×2,
corporate)". §6.2's numbered carry-over list does **not** name it; it is the
one row of the §2.1 budget that no wave has opened, which is why it is a lane
now. Under §4's rules and owner Decisions 1 and 6.

The question the row asks is not "why is a 1pp change 47% out" but "why is a
1pp change 47% out when a 7pp change is 3.7% in". A linear identity cannot do
both. Either the 7pp row is carrying an offsetting error or the two targets
disagree. **It is both, and the halves point in opposite directions** — which
is why this lane's pre-registered outcome is a *regression* on the only row it
is allowed to move.

## 1. Starting numbers

All from the branch point, on `1d35f1b`.

### The battery — `python scripts/cold_holdout.py --json`

| tier | n | mean | median | within 15 | within 25 |
|---|--:|--:|--:|--:|--:|
| Out-of-sample (Tier 1) | 26 | **18.0%** | 12.6% | 14 | 21 |
| Calibrated reference (fitted) | 23 | **1.6%** | 0.1% | 23 | 23 |
| Unfitted reconstructions | 31 | **56.6%** | 29.9% | 9 | 12 |

Tier 1 error mass is **468.2** units over 26 cases. `cbo_opt64` carries **47.1**
of it, 10.1% — third largest single row after the two payroll rows (54.1, 55.5).

### The three rows this module owns

| Row | Tier | Official | Model | Err | Provenance |
|---|---|--:|--:|--:|---|
| `cbo_opt64_corporate_rate_1pp` | out-of-sample | −135.7 | −199.6 | **47.1%** | `line_item` (CBO 60557, option 64, report p. 75) |
| `biden_corporate_28` | calibrated, fitted | −1,347.0 | −1,397.2 | **3.70%** | `line_item` (Treasury Green Book FY2025, report p. 239) |
| `trump_corporate_15` | calibrated, fitted | +1,920.0 | +1,918.0 | **0.10%** | **`model_estimate`** — the target is the model's own output |

Nothing else in either tier runs through `fiscal_model/corporate.py`.
`fdii_repeal` and `biden_gilti_reform` are scored by `international.py`;
`repeal_corporate_amt` by `amt.py`. Both files are out of this lane's scope.

### Leave-one-out — `python scripts/run_loo.py --donor-matrix`

Aggregate **29.6% mean / 19.1% median over 18 derivable cases**, 8/18 within
15%, 4 not cross-validatable. The modules in the suite are Payroll, Estate,
AMT, Credits, Expenditures and CapitalGains.

**There is no Corporate module in the leave-one-out suite, before or after this
lane.** That is finding 5 below, and it is not something a modelling lane may
fix: adding a module to `loo.py` is a yardstick edit.

## 2. What the module does today

`fiscal_model/corporate.py`, 483 lines. The whole rate identity is four lines
(`:142-150`):

```python
profits = self.baseline_profits_billions          # 1900.0
rate_change = self._get_reform_rate() - self.baseline_rate
static_effect = rate_change * profits
```

and the offset is one (`:212`):

```python
base_offset = abs(static_effect) * self.corporate_elasticity * 0.5   # 0.25 * 0.5
```

`scoring_engine.py:73` then grows the static effect at **4%/yr** and books
`deficit = −revenue + behavioral`. So the module's window score is

```
score = Δτ × 1900 × (1 − 0.125) × Σ_{t=0}^{9} 1.04^t
      = Δτ × 1900 × 0.875 × 12.006
      = Δτ × 19,958
```

— **exactly linear in Δτ, with no year, no timing and no curvature.** Its yield
per percentage point is $199.6B over the window whatever the step. That single
number is the whole of both errors:

| | per pp, 10yr |
|---|--:|
| Model (any step) | **199.6** |
| CBO 60557 Option 64 (+1pp, FY2025-2034) | **135.7** |
| Treasury Green Book FY2025 (+7pp, FY2025-2034) | **192.8** |
| Treasury Green Book FY2024 (+7pp, FY2024-2033) | 189.4 |
| Treasury Green Book FY2022 (+7pp, FY2022-2031) | 122.5 |

The 3.7% and the 47.1% are the same identity meeting two documents that
**disagree with each other by 42% per percentage point**, in the direction no
concave-in-rate behavioural model can produce: the *larger* rate change has the
*larger* per-point yield. The module is fitted to the larger one, and says so —
`corporate.py:39-45`:

> Calibrated to match CBO estimate: Biden 21%→28% raises ~$1.35T … Calibrated:
> $1,900B gives closer match to CBO

Four further facts about the file, each of which this lane either uses or
records:

1. **The base has a dead derivation behind it.** `:143-146` falls back to
   `baseline_revenue / baseline_rate` when `baseline_profits_billions <= 0`.
   The engine passes the vintage's own `baseline.corporate_income_tax` into that
   argument every year. The branch is unreachable because a fitted constant
   shadows it.
2. **The behavioural offset contradicts its own parent's documented contract.**
   `policies_core.py:344-354` returns a **signed** offset precisely so the
   engine's `deficit = −static + behavioral` "shrinks the magnitude of the
   revenue change in both directions". `corporate.py:212` returns
   `abs(static_effect) × …`. For a rate *increase* that erodes, correctly; for a
   rate *cut* it **amplifies**. `create_republican_corporate_cut` (21%→15%)
   scores a static −$142B/yr and a first-year deficit effect of **+$159.75B** —
   the behavioural response makes a corporate rate cut *more* expensive, not
   less.
3. **The offset is a flat fraction of the static effect**, so the implied
   semi-elasticity of the reported base to the statutory rate is
   `0.125 / (τ + Δτ)` — 0.568 at a 1pp step and 0.446 at 7pp. It falls as the
   rate rises. The literature says the opposite.
4. **Nothing in the module knows what a fiscal year is.** A rate change is
   booked at full strength in its first year.

### What the sources say

**CBO 60557, Option 64** (report p. 75; the alternatives CSV row `64.1`,
transcribed by `scripts/extract_cbo_options.py`) publishes the annual path:

```
FY  2025  2026  2027  2028  2029  2030  2031  2032  2033  2034   total
     7.5  12.7  13.6  13.7  14.1  14.4  14.5  14.6  14.9  15.7   135.7
```

FY2025 is **59% of FY2026**, against an out-year trend of about +2%/yr. CBO is
pricing a partial first year. `cbo.gov` returns HTTP 403 to this environment on
every URL, so the option's *text* — which would say what else the estimate nets
out — could not be read; only the transcribed table is available. That is a
stated limit on this lane, not a fetch that was skipped.

**IRS SOI, *Corporation Income Tax Returns Complete Report*, Table 11**
("Selected Tax Items: Dividends, Net Income (Less Deficit), Statutory Special
Deductions, Income Subject to Tax, Taxes, Credits, and Payments"), reachable
and fetched. Tax Year 2022, returns of active corporations, $B:

| Item | TY2019 | TY2020 | TY2021 | TY2022 |
|---|--:|--:|--:|--:|
| Income subject to tax | 1,733.28 | 1,780.30 | 2,422.05 | **2,879.10** |
| Total income tax before credits | 383.00 | 393.79 | 528.81 | **633.32** |
| *of which* Income tax | 364.43 | 373.90 | 508.56 | **604.23** |
| Foreign tax credit | 73.37 | 67.01 | 96.53 | **112.16** |
| General business credit | 49.86 | 49.83 | *d* | **72.17** |
| Total income tax after credits | 257.13 | 276.61 | 371.40 | **448.72** |
| **Income tax ÷ income subject to tax** | 0.2103 | 0.2100 | 0.2100 | **0.2099** |
| **after ÷ before credits** | 0.6714 | 0.7024 | 0.7023 | **0.7085** |

The bolded ratio in the penultimate row is the point: **SOI's own "Income tax"
line is the statutory 21% of "income subject to tax" to within a tenth of a
percentage point, in every post-TCJA year.** So the base a statutory rate
change reaches is published, it is $2,879.1B in TY2022, and the module's
$1,900B is **34% below it** — which is roughly the TY2018 level ($1,956.7B).
The fitted constant is not a wrong concept; it is a stale vintage.

TY2018 is excluded from the table above: it is the §15 blended-rate transition
year, and SOI's own TY2018 table prints "total income tax before credits"
($404.08B) *below* "income tax" ($414.84B), so its ratios are not comparable.

## 3. What the lane changes

Everything is in `fiscal_model/corporate.py`, one transcribed data file, its
tests, four lines of the `corporate_rate` branch of
`create_policy_from_score`, and the row's `known_limitations` string.

1. **A `mode` field, `reported` | `derived`, defaulting to `reported`**, on the
   `AMTPolicy` / `TaxExpenditurePolicy` pattern. `reported` reproduces today's
   arithmetic bit for bit. Under owner Decision 1 it stays the app default
   unless derived beats it across the carried corporate benchmarks (§4 says it
   will not).
2. **A published statutory base.** `derived` reads income subject to tax from
   SOI Table 11 TY2022 instead of `BASELINE_TAXABLE_PROFITS_BILLIONS`, aged to
   `start_year` at the engine's existing 4% corporate growth constant — no new
   growth parameter. **It deliberately does not read the level off the
   baseline**, so `cbo_options.py`'s stated property that no uncalibrated shape
   reads a level off the vintage survives (see §4's rejected alternative).
3. **A credit-realization ratio.** The marginal pre-credit dollar reaches
   receipts at SOI's own published after÷before ratio, **0.708526** (TY2022).
   Cross-checked against an explicit §904 decomposition — the FTC treated as
   fully absorbing the tax on the foreign-source share of the base, non-FTC
   credits absorbing the domestic remainder at their own average — which
   returns **0.7012**, agreeing to 1.0% relative. That check is a test, not a
   comment.
4. **A profit-shifting semi-elasticity on the rate *level*.** The offset
   becomes `static × β × (τ₀ + Δτ)` with **β = 0.8** frozen from Heckemeyer &
   Overesch's meta-analytic consensus (2013, ZEW DP 13-045; *Canadian Journal
   of Economics* 50(4), 2017): a 1pp rise in the statutory rate reduces reported
   pre-tax profits by 0.8%. One value, one mechanism, cited, applied identically
   to every case. It makes the identity concave in Δτ, which is the row's whole
   subject.
5. **The signed-offset contract.** `derived` returns the offset signed with the
   static effect, as `policies_core.py` documents, so a rate cut is eroded
   rather than amplified. **`reported` keeps the `abs()`**, because
   `trump_corporate_15`'s fitted number must not move.
6. **IRC §6655 settlement timing.** A calendar-year corporation pays four
   estimated instalments on the 15th day of the 4th, 6th, 9th and 12th months
   (§6655(c)(2)); three of them — April, June, September — fall inside the same
   federal fiscal year, the December one and the settlement fall in the next.
   `derived` therefore books **0.75** of a tax year's liability in its own
   fiscal year and 0.25 in the following one, expressed exactly as a phase
   factor: 0.75 in the first year, `0.75 + 0.25/1.04 = 0.99038` thereafter,
   which is the convolution's closed form when the liability grows at the
   engine's own rate.
7. **The Option 64 validation shape is pinned to `derived`**, four lines in
   `create_policy_from_score`, exactly as the `tax_expenditure` shape already
   is and for the same reason: the uncalibrated path must not read a base
   fitted to another benchmark. Today it does — `BASELINE_TAXABLE_PROFITS_
   BILLIONS` was fitted to reproduce `biden_corporate_28`.

## 4. The prediction

**Headline: the one row this lane may move gets worse, from 47.1% to about
62%, and I am registering that in advance as the lane's expected outcome rather
than discovering it afterwards.** The 34% the base moves up is larger than
everything the behaviour and the timing take back down, because the published
base sides with Treasury and the row is scored against CBO.

### Rows I expect to move

| Row | Now | Predicted |
|---|--:|---|
| Tier 1 `cbo_opt64_corporate_rate_1pp` | −199.6, **47.1%** | **−220.3, 62.3%** — a registered regression |
| Tier 1 mean / median | 18.0% / 12.6% | **18.6% / 12.6%** |
| Tier 1 within 15 / within 25 | 14 / 21 | **14 / 21**, unchanged |
| CI gate `--max-mean-error 25 --min-within-25pct 20` | passes | **passes** (18.6 ≤ 25; 21 ≥ 20) |

### Rows I expect NOT to move, to the decimal

| Row | Now | Predicted |
|---|--:|---|
| `biden_corporate_28` **reported** | −1,397.2, 3.70% | unchanged |
| `trump_corporate_15` **reported** | +1,918.0, 0.10% | unchanged |
| Fitted calibrated tier | 23 @ 1.6% | unchanged |
| Unfitted reconstructions | 31 @ 56.6% | unchanged |
| Leave-one-out | 18 @ 29.6% / 19.1% / 8 | unchanged (no Corporate module) |
| Every shipped corporate preset | Biden 28%, Trump 15%, Tailor, classroom, bill tracker, Ask | unchanged — all score `reported` |
| Decision 6 caption | none needed | **none needed** — no shipped number moves |

### Reported vs derived, per benchmark — the Decision 1 table

| Benchmark | Target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `biden_corporate_28` | −$1,347.0B | −$1,397.2B | +3.73% | **−$1,452.1B** | **+7.81%** |
| `trump_corporate_15` | +$1,920.0B | +$1,918.0B | −0.11% | **+$1,698.6B** | **−11.53%** |
| **Mean abs** | | | **1.92%** | | **9.67%** |

**`CORPORATE_APP_MODE` stays `reported`** under Decision 1's own rule: derived's
9.67% does not beat reported's 1.92%. Read past the mean the way
`PROVENANCE_amt_insulin.md` §2 says to — one of the two rows is a target the
model itself produced (`trump_corporate_15`, provenance `model_estimate`), so
its 0.11% is bookkeeping and derived "loses" it by definition. On the one
corporate benchmark with a published document behind it, reported still wins,
3.73% against 7.81%. That is an honest loss and it is registered as one.

### The 7pp row before and after, which is the check that this is not a re-tune

| | 1pp | 7pp | per pp |
|---|--:|--:|--:|
| Reported | −199.6 | −1,397.2 | **199.6 / 199.6** |
| Derived | −220.3 | −1,452.1 | **220.3 / 207.4** |
| Published | −135.7 | −1,347.0 (Treasury) | **135.7 / 192.8** |

Derived is 6% concave between the two steps where reported is exactly flat. The
concavity is β doing its job and it is nowhere near enough: closing a 42%
per-point gap by behaviour alone needs **β ≈ 2.37**, three times the consensus
0.8 and outside every published estimate except Dowd, Landefeld & Moore (2017)
at very low foreign rates. The sensitivity, computed in advance:

| β | derived `cbo_opt64` | err |
|---|--:|--:|
| 0.25 (Gruber–Rauh corporate ETI, converted) | −252.6 | 86.2% |
| 0.568 (what the module's flat 12.5% implies at 1pp) | −233.9 | 72.4% |
| **0.80 (shipped — Heckemeyer & Overesch consensus)** | **−220.3** | **62.3%** |
| 1.20 | −196.8 | 45.0% |
| 2.365 (the value that would reproduce CBO) | −128.2 | 5.5% |

No lane may pick the last row. §4 of the plan is explicit.

### Where I expect to be wrong

- **The magnitude of the regression.** 62.3% is arithmetic on a spreadsheet;
  the engine's phase handling, the `use_real_data` path and the
  `effective_start_year` may move it a point or two. A landing outside 58–67%
  means something else changed and gets written into §5.
- **The credit ratio is an average standing in for a marginal.** SOI publishes
  what share of *total* pre-credit tax survives credits; the lane asserts the
  same share survives on the *marginal* pre-credit dollar. For the FTC the two
  coincide to 1% (§3.3), which is why the assumption is defensible; for the
  general business credit it is almost certainly too low, because §38(c)'s
  limit rises with the rate and lets carryforwards be used. That error points
  the derived number *down*, toward CBO, and it is not quantified here because
  the carryforward stock is not in Table 11.
- **TY2022's base is inflated by two timing items.** §174 R&D capitalisation
  began in TY2022 and bonus depreciation was phasing down; both raise taxable
  income temporarily and both reverse. The lane anchors on the latest published
  complete report and does not adjust for them — adjusting would need a number
  I would be choosing. Anchoring on TY2020 instead would put the derived
  `cbo_opt64` near the target, which is precisely why the year is fixed as
  "latest published" in advance.
- **CAMT is not modelled at all.** For a corporation paying the 15% book
  minimum, a point of regular rate raises no revenue until the regular tax
  clears the minimum. CAMT began in TY2023 and so is in none of the SOI data
  the lane reads. Another channel that points down.
- **The individual-side interaction is not modelled.** A higher corporate rate
  lowers dividends and share values and so lowers individual receipts. The
  repository carries JCT's 75/25 capital/labour incidence split
  (`cbo_distributions.py:132`) but no revenue feedback from it. This is the
  largest single unmodelled channel and the most likely home for the residual.
  It is not built here because sizing it means choosing a distributed share and
  a marginal rate, and the resulting constant would land on CBO by
  construction.

Anything that moves outside these lists is a finding and goes in §5.

## 5. Outturn

*Appended 2026-09-05, after the code. Numbers from
`python scripts/cold_holdout.py --json`, `python scripts/run_loo.py
--donor-matrix`, `python scripts/run_validation_dashboard.py` and
`validate_all_corporate(mode=...)` on the finished branch.*

### Against the pre-registration

| Row | Predicted | Actual | |
|---|---|---|---|
| `cbo_opt64_corporate_rate_1pp` | −220.3, 62.3% | **−220.3, 62.3%** | as registered |
| Tier 1 mean / median | 18.6% / 12.6% | **18.6% / 12.6%** | as registered |
| Tier 1 within 15 / 25 | 14 / 21 | **14 / 21** | as registered |
| `biden_corporate_28` reported | unchanged | **−1,397.21, 3.73%** | as registered |
| `trump_corporate_15` reported | unchanged | **+1,917.98, 0.11%** | as registered |
| `biden_corporate_28` derived | −1,452.1, 7.81% | **−1,452.14, 7.81%** | as registered |
| `trump_corporate_15` derived | +1,698.6, 11.53% | **+1,698.57, 11.53%** | as registered |
| Decision 1 means | 1.92% vs 9.67% | **1.92% vs 9.67%** | as registered |
| `CORPORATE_APP_MODE` | stays `reported` | **stays `reported`** | as registered |
| Fitted calibrated tier | 23 @ 1.6% | **23 @ 1.6%**, no row moved | as registered |
| Unfitted reconstructions | 31 @ 56.6% | **31 @ 56.6%**, no row moved | as registered |
| Leave-one-out | 18 @ 29.6% | **byte-identical output** | as registered |
| Shipped presets | unchanged | **unchanged** | as registered |
| Decision 6 caption | none owed | **none owed** | as registered |
| CI gate | passes | **exit 0** | as registered |

**Every registered row landed, to the decimal, including the regression.** The
hand arithmetic in §4 was computed on a spreadsheet before the module was
opened and the engine reproduced all seven of its figures exactly. The whole
`run_validation_dashboard.py` output differs from the branch point by **one
line** — the Tier 1 mean.

The dashboard still exits 1, before and after and identically: `runtime`
degraded (Python 3.14.0 against a supported range of `>=3.10,<3.14`) and
`microdata` warn (SOI 2023 coverage 119% returns / 81% AGI). Neither component
touches this module; the failure was verified against a stashed tree on the
branch point.

The CI thresholds needed no change and the workflow's own rule says why:
`ceil(18.6 × 1.25)` rounded up to the nearest 5 is still **25**, and
`21 − 1` is still **20**. A modelling lane may not edit them either way; this
is only the note that the rule re-derives to what is already there.

### Reported vs derived, per benchmark — the Decision 1 table

`validate_all_corporate(mode=...)` against the live targets:

| Benchmark | Target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `biden_corporate_28` | −$1,347.0B | −$1,397.21B | −3.73% | −$1,452.14B | −7.81% |
| `trump_corporate_15` | +$1,920.0B | +$1,917.98B | −0.11% | +$1,698.57B | −11.53% |
| **Mean abs** | | | **1.92%** | | **9.67%** |

`CORPORATE_APP_MODE` stays `reported`. Read it the way
`PROVENANCE_amt_insulin.md` §2 says to: the second row's target is provenance
`model_estimate` — it is this model's own output written down as an expectation
— so its 0.11% is bookkeeping and derived loses it by construction. Unlike the
AMT case there is no consolation row: on the one corporate benchmark with a
document behind it, reported wins as well, 3.73% to 7.81%. That is an honest
loss for the structural path.

### What the lane actually bought

**1. A per-point yield that depends on the point.** Reported returns the same
dollars per percentage point at every step; derived does not:

| Step | Reported per pp | Derived per pp |
|---|--:|--:|
| +1pp | 199.60 | **220.28** |
| +2pp | 199.60 | 218.14 |
| +5pp | 199.60 | 211.73 |
| +7pp | 199.60 | 207.45 |
| +14pp | 199.03 | **191.91** |

Reported's one wobble at 14pp is not curvature in the rate identity: it is the
pass-through branch firing when the corporate rate clears the 29.6% effective
pass-through rate, the module's only other non-linearity and one that has
nothing to do with the base.

**2. A base with an identity behind it instead of a comment.** The channel
decomposition on `cbo_opt64`, each step applied to the one before:

| | 10yr |
|---|--:|
| SOI statutory base, aged and grown, nothing else | −388.83 |
| × credit realization (0.7085) | −275.50 |
| × profit shifting (1 − 0.8 × 0.22) | −227.01 |
| × IRC §6655 settlement | **−220.28** |
| *reported, for comparison* | *−199.60* |
| *CBO 60557 Option 64* | *−135.70* |

Credits and behaviour together take 42% off the mechanical figure. They are
not enough, and the reason is the row above them.

**3. The residual, located.** Re-running the derived identity with every input
fixed except the SOI anchor year:

| Anchor | Base | Realization | Derived | Err |
|---|--:|--:|--:|--:|
| TY2019 | 1,733.3 | 0.6714 | −141.35 | **4.2%** |
| TY2020 | 1,780.3 | 0.7024 | −146.06 | **7.6%** |
| TY2021 | 2,422.1 | 0.7023 | −191.04 | 40.8% |
| TY2022 (shipped) | 2,879.1 | 0.7085 | −220.28 | **62.3%** |

**CBO's Option 64 prices a percentage point of corporate rate at the
*pre-pandemic* base.** Its published path peaks at $15.7B in FY2034; SOI's
TY2022 base already yields $20.4B per point *before* any behavioural response.
That is not a modelling residual it is in this module's power to close, and it
is the single most useful number this lane produced. Note also what it means
for the discipline: anchoring on TY2019 would have scored the row at 4.2%, and
the only reason this branch does not is that §4 fixed the anchor as "latest
published" before the code was written.

### Findings

1. **The two targets disagree by 42% per percentage point, and the module was
   quietly split between them.** CBO 60557 Option 64 is $135.7B per point over
   FY2025-2034; Treasury's FY2025 Green Book row is $192.8B per point over the
   same window; the module returned $199.6B per point at every step. The
   direction is the part that cannot be modelled away — the *larger* rate
   change carries the *larger* per-point yield, which no concave-in-rate
   behavioural response produces. The 3.7% and the 47.1% were never two
   different accuracies; they were one number meeting two documents.
2. **The offsetting error the lane was sent to find is real, and it is two
   errors.** The fitted base is 34% below SOI's published statutory base, and
   the fitted offset (a flat 12.5%) is well below what the published
   semi-elasticity implies at a 7pp step (22.4%). A base that is too small and
   an offset that is too small pull in opposite directions and very nearly
   cancel at 7pp — reported −1,397 against derived −1,452, both within 8% of
   Treasury's −1,347 — while at 1pp they do not, because the offset term is
   almost inert there. Correcting *one* of them alone would have looked like a
   regression on both rows; correcting both leaves the 7pp row where it was and
   moves the 1pp row further out, which is what the documents say should
   happen.
3. **$1,900B is not a wrong concept, it is a stale vintage.** SOI's income
   subject to tax was **$1,956.7B in TY2018** and is **$2,879.1B in TY2022**.
   The fitted constant is within 3% of the TY2018 base. Nobody chose a wrong
   quantity; a right quantity stopped being updated, and because the module is
   linear in the base the staleness was invisible against a target that had
   been calibrated to at the same vintage.
4. **The behavioural offset had a sign bug that only a rate cut could show.**
   `policies_core.py` documents a signed offset so that the engine erodes a
   gain and recovers part of a cut. `corporate.py` overrode it with
   `abs(static_effect)`, so `create_republican_corporate_cut` — a shipped
   preset — books a first-year deficit effect of **+$159.75B** on a static
   −$142B: the behavioural response makes a corporate rate cut *more*
   expensive. Derived signs it correctly. Reported keeps the bug on purpose,
   because `trump_corporate_15`'s fitted number is scored through it and
   Decision 1 forbids moving a shipped number in a lane that does not also ship
   a caption for it — and a caption for a number nobody has decided to change
   would be worse than the bug. **Both behaviours are now pinned by a test**, so
   the next person to touch it is making a decision rather than an edit. This
   is the lane's clearest hand-off.
5. **The corporate module is not in the leave-one-out suite at all.** The suite
   holds Payroll, Estate, AMT, Credits, Expenditures and CapitalGains. The one
   module whose base constant is *self-documented as calibrated* has never been
   cross-validated, which is precisely the population `run_loo.py` exists to
   catch. Adding it is a `loo.py` edit and no modelling lane may make one, so
   this is recorded and not done.
6. **A concavity large enough to reconcile the two documents needs β ≈ 2.37**,
   three times Heckemeyer & Overesch's consensus 0.8 and outside every
   published estimate except Dowd, Landefeld & Moore (2017) at very low foreign
   rates. Written into §4 *before* the code, together with the note that no lane
   may pick it. It is recorded here so that a future lane which arrives at
   β ≈ 2.4 by some other route knows it is standing exactly where a fitted
   constant would stand.
7. **The average-equals-marginal credit assumption survived a check it could
   have failed.** SOI's after÷before ratio is 0.7085; a §904 decomposition
   built from the same rows — the FTC treated as the statutory tax on the
   foreign-source share of the base, the remaining credits absorbing the
   domestic remainder at their own average — returns **0.7012**, 1.0% away. Two
   constructions with nothing in common but the source table. It is a test, not
   a remark.

### What the lane did not do

- Did not touch any target, `preregistered.py`, `holdout.py`, `loo.py`,
  `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`,
  `benchmark_sources.py`, the yardstick scripts, or any CI threshold.
- Did not add a per-benchmark constant, and did not add a per-case elasticity.
  `profit_shifting_semi_elasticity` is one frozen literature value; a test
  asserts no factory overrides it.
- Did not re-derive the international, R&D, bonus-depreciation or
  book-minimum channels. `GILTI_REVENUE_BILLIONS`, `FDII_COST_BILLIONS`, the
  −$12B R&D annual, the −$28B depreciation annual and the $100B book-minimum
  base are all unsourced and all untouched: this lane re-derived the *rate*
  identity, which is what its title says. The R&D and depreciation constants
  are the obvious next item, and they matter to `trump_corporate_15`, whose
  derived score is 20% depreciation.
- Did not build the three channels that would move the derived score toward
  CBO — credit carryforwards under §38(c) and §904(c), CAMT, and the
  individual-side dividend/capital-gain interaction. Each needs a quantity that
  is not published in the source the module reads, and each would arrive as a
  constant that landed on CBO by construction. All three are named in the row's
  `known_limitations`.
- Did not adjust SOI's TY2022 base for §174 R&D capitalisation or the
  bonus-depreciation phase-down, both of which inflate it and both of which
  reverse. Adjusting needs a number that would be chosen rather than read.
- Did not flip `CORPORATE_APP_MODE`, and so shipped no user-visible change and
  owes no Decision 6 caption.
- Did not open `international.py`, `amt.py` or `payroll.py`, so
  `fdii_repeal`, `biden_gilti_reform` and `repeal_corporate_amt` are untouched
  even though their names contain the word corporate.
