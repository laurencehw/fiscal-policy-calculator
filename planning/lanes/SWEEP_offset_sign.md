# Sweep — the behavioural-offset sign contract

*Pre-registered 2026-09-05 against `main` @ `790caff`, in this lane's first
commit, before any module was touched. Inventory (§6) and outturn (§7) appended
later, each in its own commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2 **item 22** — *"Sweep every module
for an inverted or absolute-valued behavioural offset"* — which subsumes item 8
(the expenditure module's reverse convention). Four modules have been found not
following the engine's documented sign contract, **each by a lane that was
looking at something else**: `trade.py` (Wave 3 L8), `payroll.py` (Wave 5 A),
`corporate.py` (Wave 5 B, fixed in `derived` only), and
`tax_expenditures_core.py` (Wave 4 3a, left as an unchosen convention). None of
the four was found by a test, and item 22 says why: *"this is invisible to every
gate the repository has"*, because each module's calibrated factories zero the
elasticity, so the fitted tier and the leave-one-out column are structurally
blind to the sign. The remaining nine classes have never been swept.

This lane touches the modules that fail the contract, one test file per module,
one new contract test, one audit script, and — if a shipped headline moves — one
caption in `fiscal_model/ui/tabs/results_summary.py` under Decision 6. It edits
no target, no threshold, no manifest, `preregistered.py`, `holdout.py`,
`loo.py`'s guards, `target_revisions.py`, `KNOWN_SCORES`/`CBO_SCORE_MAP`, or
`.github/workflows/`. **It changes no elasticity value** — only the sign and
shape of how an offset is applied.

## 1. The contract, in one paragraph

`fiscal_model/scoring_engine.py` books a score as
`static_deficit = static_spending − static_revenue`, then
`deficit_after_behavioral = static_deficit + behavioral`. The quantity handed to
`estimate_behavioral_offset` is the **static revenue** effect for that year, not
the deficit effect. So an offset carrying the **same sign as the static revenue
effect erodes** it — a tax increase raises less than its static figure because
the base shrinks, a tax cut loses less than its static figure because the base
grows — and an offset carrying the **opposite sign magnifies** it, which is
backwards in both directions at once.
`TaxPolicy.estimate_behavioral_offset` in `fiscal_model/policies_core.py` states
this in its docstring and implements it as `static_effect × ETI × 0.5`; the
final effect is `static × (1 − ETI·0.5)`, which shrinks the magnitude whichever
way the static points. Two ways to break it are already in the tree: return the
negation (magnifies both directions), or return `abs(...)` (erodes a revenue
gain, magnifies a revenue loss, and is right only for whichever sign the
module's own factories happen to produce). A third, latent, is an offset whose
magnitude exceeds `|static|` — same-signed but large enough to flip the score's
sign, which is not erosion either.

The contract has one honest exception. An offset may legitimately carry the
*opposite* sign when a **source says the behavioural response raises revenue in
both directions** — a second channel, not a haircut on the first. That is the
`convention` classification in §3, and it is not a bug. It is also not this
lane's to choose module-wide (item 8 says so explicitly): a convention case gets
its source documented and is listed for the owner, unchanged.

## 2. Every class that implements or inherits the offset

From `grep -rn "def estimate_behavioral_offset" fiscal_model/` plus
`grep -rn "^class .*Policy" fiscal_model/*.py fiscal_model/models/*.py
fiscal_model/long_run/*.py fiscal_model/microsim/*.py`. Thirteen classes define
it; two more `Policy` subclasses reach the engine's cost-estimate branch, which
books a hard zero and never calls it.

| # | Class | File:line | In scope |
|---|---|---|---|
| 1 | `TaxPolicy` | `policies_core.py:344` | the contract itself |
| 2 | `CapitalGainsPolicy` | `policies_core.py:822` | yes (own signature: `+years_since_start, use_real_data, phase`) |
| 3 | `AMTPolicy` | `amt.py:1225` | yes |
| 4 | `CorporateTaxPolicy` | `corporate.py:467` | yes (two modes) |
| 5 | `TaxCreditPolicy` | `credits_core.py:528` | yes (three branches) |
| 6 | `IRSEnforcementPolicy` | `enforcement.py:125` | yes |
| 7 | `EstateTaxPolicy` | `estate.py:684` | yes |
| 8 | `InternationalTaxPolicy` | `international.py:595` | yes |
| 9 | `PayrollTaxPolicy` | `payroll.py:536` | yes (fixed W5-A) |
| 10 | `PremiumTaxCreditPolicy` | `ptc.py:380` | yes |
| 11 | `TaxExpenditurePolicy` | `tax_expenditures_core.py:691` | yes (item 8's convention) |
| 12 | `TCJAExtensionPolicy` | `tcja.py:315` | yes (returns 0.0 by design) |
| 13 | `TariffPolicy` | `trade.py:228` | yes (fixed Wave 3 L8) |
| — | `DrugPricingPolicy` | `pharma.py:436` | no offset — `_score_cost_estimate_policy_branch` books `np.zeros` |
| — | `ClimateEnergyPolicy` | `climate.py:107` | no offset — same branch |
| — | `SpendingPolicy`, `TransferPolicy` | `policies_core.py:1033, 1161` | no offset — engine books `np.zeros` |

`fiscal_model/models/`, `fiscal_model/long_run/` and `fiscal_model/microsim/`
define no `Policy` subclass and no offset; the macro adapters take a
`MacroScenario`, not a policy.

## 3. The test applied to each

For every class in the table, build a **synthetic tax increase** and a
**synthetic tax cut of the same size** through the same construction, score both
on the engine, and record for each: static revenue, the behavioural offset, the
final deficit effect, and the sign of the offset *relative to* static. Two
probes, because they answer different questions:

- **Probe A — the function.** Call `estimate_behavioral_offset(+100)` and
  `(−100)` on a representative instance. This is the sign rule the class
  implements, independent of whether the class's own factories ever produce a
  negative static. (Meaningless for `CapitalGainsPolicy`, which does not read
  `static_effect` at all and rebuilds the response bracket by bracket; recorded
  as `n/a` and classified on Probe B.)
- **Probe B — the score.** Build an increase policy and a cut policy of equal
  size, run `FiscalPolicyScorer.score_policy(..., dynamic=False)`, and compare
  `|final_deficit_effect|` against `|static_deficit_effect|` over the window.

Classification vocabulary, assigned from what the probes return and not from
what the docstring says:

| tag | meaning |
|---|---|
| `correct` | erodes in both directions — same sign as static, magnitude below it |
| `inverted` | magnifies in both directions — opposite sign to static |
| `abs` | always one sign — erodes whichever direction happens to match, magnifies the other |
| `asymmetric` | erodes one direction, magnifies the other, by some rule other than `abs` |
| `zero` | returns 0.0 (by design, or because every factory zeroes the elasticity) |
| `convention` | opposite-signed **on purpose**, with a source that says the behavioural response raises revenue in both directions |

`abs`, `inverted` and `asymmetric` are bugs against the documented contract and
get fixed in the path the app actually uses. `convention` is documented and left.

## 4. Starting numbers on `790caff`

`python scripts/cold_holdout.py --json` and `python scripts/run_loo.py
--donor-matrix`, both run on the branch point before any edit:

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| **Tier 1 — out-of-sample** | 26 | **15.9%** | 11.4% | 16 | 22 |
| **Tier 2 — fitted calibrated** | 23 | **1.6%** | 0.1% | 23 | 23 |
| **Tier 2 — unfitted reconstructions** | 31 | **56.6%** | 29.9% | 9 | 12 |
| **Tier 2 — leave-one-out** | 18 derivable (4 not x-val) | **29.6%** | 19.1% | 8 | — |

Per-module LOO on the same commit: Payroll 3.8% (n=3), Estate 10.4% (n=2), AMT
73.9% (n=2), Credits 18.5% (n=3), Expenditures 35.7% (n=5), CapitalGains 39.6%
(n=3). CI gate in force: `cold_holdout.py --max-mean-error 20
--min-within-25pct 21`, which the branch point passes at 15.9% and 22.

The one row and the one preset the sweep is expected to reach, both on the
corporate module: `trump_corporate_15` scores **+$1,918.0B against a +$1,920.0B
target, 0.10%**, and the shipped preset **🏢 Trump Corporate 15%** prints the
same figure. `create_republican_corporate_cut` carries
`corporate_elasticity=0.25` and `mode=CORPORATE_APP_MODE` (= `reported`), so its
first year books a **+$159.75B deficit effect on a static −$142B**: a rate cut
amplified by 12.5% rather than eroded by it.

## 5. Predictions

Written from reading the thirteen implementations, before running either probe.
The inventory in §6 is built by running them, and a disagreement between §5 and
§6 is a finding to write down, not a number to quietly correct.

### 5.1 Predicted classification

| class | predicted | why |
|---|---|---|
| `TaxPolicy` | `correct` | `static × ETI × 0.5`, signed, docstring states the contract |
| `CapitalGainsPolicy` | `correct` | `delta_static − delta_total`; for a rate rise realizations fall so `delta_total < delta_static` and the offset is positive, and the algebra reverses with the rate — same sign either way |
| `AMTPolicy` | `inverted` | `return -total_offset` for `static > 0`, `+total_offset` otherwise |
| `CorporateTaxPolicy` (`reported`, the app default) | `abs` | `abs(static) × elasticity × 0.5` |
| `CorporateTaxPolicy` (`derived`) | `correct` | signed, fixed by W5-B |
| `TaxCreditPolicy` | `asymmetric` | EITC and CTC branches are signed and correct; the **fallback** branch is `abs(static) × labor_supply_elasticity × 0.3` |
| `IRSEnforcementPolicy` | `abs` | `abs(static) × avoidance_response_rate` |
| `EstateTaxPolicy` | `inverted` | same `return -total_offset` idiom as AMT |
| `InternationalTaxPolicy` | `abs` | `abs(static) × profit_shifting_elasticity × factor` |
| `PayrollTaxPolicy` | `correct` | `math.copysign`, fixed by W5-A |
| `PremiumTaxCreditPolicy` | `inverted` | same `return -total_offset` idiom |
| `TaxExpenditurePolicy` | `convention` | opposite-signed; CBO's Option 56 text says both channels raise revenue, so it is directionally right *there* and unsourced everywhere else — item 8 |
| `TCJAExtensionPolicy` | `zero` | returns 0.0; CBO's $4.6T already embeds behaviour |

Three of those — AMT, estate, PTC — carry the **identical comment pair**
`# Reduces revenue gain` / `# Reduces revenue loss` above a `return
-total_offset`. The comment states erosion and the code delivers magnification,
which is the tell that all three are one copy-paste and that the author read
`behavioral` as a quantity the engine *subtracts*. That is a prediction about
provenance as well as sign, and §6 can refute it.

### 5.2 Predicted movement — rows

**Exactly one scorecard row should move: `trump_corporate_15`**, in the fitted
calibrated tier, from 0.10% to somewhere near 20-25%. Its static is negative (a
rate cut), it scores through `CORPORATE_APP_MODE = reported`, and 12.5% of a
negative static currently lands on the wrong side. Signing it turns a first year
of `+142 + 17.75 = +159.75` into `+142 − 17.75 = +124.25`, so the ten-year
figure should fall by about the same 22%, to roughly **+$1,490B against a
+$1,920B target**. That is a **finding, not a regression**: no constant will be
retuned to put it back, because the constant was compensating for the sign.

Nothing else should move, and the reason is the same reason item 22 gives for
the defect being invisible:

- **AMT** — all five factories set `timing_elasticity=0.0` and
  `avoidance_elasticity=0.0`, so the correction multiplies a zero on
  `extend_tcja_amt`, `repeal_individual_amt`, `repeal_corporate_amt`,
  `pl119_21_amt_exemption` and the AMT LOO column.
- **Estate** — `create_tcja_estate_extension`, `create_biden_estate_proposal`,
  `create_warren_estate_proposal` and `create_eliminate_estate_tax` all zero both
  elasticities. Only `create_estate_rate_change` and
  `create_estate_exemption_change` carry the live Kopczuk–Slemrod 0.16, and
  neither is reached by a benchmark or a preset — they are public-API and test
  surfaces.
- **PTC** — `create_extend_enhanced_ptc` and `create_repeal_ptc` zero the
  elasticities; only `create_let_enhanced_expire` carries 0.3 and it is not a
  preset.
- **International and enforcement** are `abs`, and every one of their benchmarks
  (`fdii_repeal`, `biden_gilti_reform`, `pillar_two_adoption`,
  `biden_full_international`, `ira_enforcement`, `double_enforcement`) is a
  revenue **raiser** — positive static, where `abs` and the signed rule agree to
  the cent. The bug there is real and entirely latent.
- **Credits** — every calibrated credit factory either pins
  `annual_revenue_change_billions` (offset returns 0.0) or runs the derived path
  through the EITC/CTC branches, which are already signed.
- **Expenditures** are a `convention` case and are not touched, so
  `cap_employer_health`, `eliminate_mortgage`, `repeal_salt_cap`,
  `eliminate_salt`, `cap_charitable`, `eliminate_step_up`, `cbo_opt56...` and
  the whole Expenditures LOO column stay to the cent.
- **Capital gains, payroll, tariffs, TCJA** are predicted `correct` or `zero`
  already.

So: **Tier 1 unchanged at 26 @ 15.9%** (the CI gate is not approached);
**unfitted reconstructions unchanged at 31 @ 56.6%**; **LOO unchanged at 18 @
29.6%** with every module row identical; **fitted calibrated 23 @ 1.6% → 23 @
about 2.6%**, the whole of the change being `trump_corporate_15`.

### 5.3 Predicted movement — presets

One of the 53 `PRESET_POLICIES` entries: **🏢 Trump Corporate 15%**, by about
−22% (a smaller cost). Every other preset routes through a factory that zeroes
the elasticity, produces a positive static, or belongs to a class predicted
`correct`. A −22% move in a shipped headline is material, so **Decision 6
applies**: a caption in `results_summary.py`, after the existing ones, in its own
commit.

Two user-visible surfaces that are *not* presets should also change, both for
the better and neither gated: `bill_tracker/auto_scorer.py` builds a raw
`EstateTaxPolicy` with module-default elasticities (inverted today) and calls
`create_corporate_rate_change(include_behavioral=True)` (`abs` today); and
Tailor/Build can reach any class through the composer without a factory's zeroed
elasticity in the way.

### 5.4 Falsification

The lane is falsified — and says so in §7 rather than adjusting — if:

1. **a row moves whose class §5.1 called `correct`** (`TaxPolicy`,
   `CapitalGainsPolicy`, `PayrollTaxPolicy`, `TariffPolicy`, corporate
   `derived`). That would mean the contract as documented is not the contract
   the engine implements, and the sweep would be wrong at the root rather than
   at a leaf;
2. **a row moves that §5.2 named as not moving**, which would mean a calibrated
   factory does not zero what its comment says it zeroes;
3. **`trump_corporate_15` does not move**, which would mean the `abs()` is
   already neutralised somewhere downstream and W5-B's finding 4 is wrong;
4. **a class classifies differently from §5.1**, which is cheap to be wrong
   about and is recorded either way.

## 6. Inventory

*Built by running `python scripts/audit_offset_signs.py` on `790caff` + this
lane's script commit, not by reading. The script is committed with this section
and is re-runnable; `--json` gives the same rows machine-readable.*

Two probes, as §3 pre-registered. `f(+100)` and `f(-100)` are
`estimate_behavioral_offset` called on that instance with a synthetic static
revenue effect of plus or minus $100B - the class's **sign rule**, deliberately
independent of whether its own factories ever hand it a negative static,
because Tailor, the composer and `bill_tracker/auto_scorer.py` are not bound by
the factories. The window columns are
`FiscalPolicyScorer.score_policy(dynamic=False)` summed over FY2026-FY2035, in
deficit space. `erodes` is `|final| <= |static|`.

| class | module | dir | static/yr | f(+100) | f(-100) | window static | window behav | window final | erodes | tag |
|---|---|---|--:|--:|--:|--:|--:|--:|:-:|---|
| TaxPolicy | policies_core.py | increase | 36.0 | 12.5 | -12.5 | -359.6 | 44.9 | -314.6 | yes |  |
|  |  | cut | -36.0 | 12.5 | -12.5 | 359.6 | -44.9 | 314.6 | yes | correct |
| CapitalGainsPolicy | policies_core.py | increase | 20.0 | 35.7 | 35.7 | -247.5 | 201.0 | -46.4 | yes |  |
|  |  | cut | -20.0 | -35.3 | -35.3 | 247.5 | -181.6 | 65.8 | yes | correct |
| AMTPolicy | amt.py | increase | 100.0 | -25.0 | 25.0 | -1,146.4 | -286.6 | -1,433.0 | **NO** |  |
|  |  | cut | -100.0 | -25.0 | 25.0 | 1,146.4 | 286.6 | 1,433.0 | **NO** | inverted |
| CorporateTaxPolicy [reported] | corporate.py | increase | 114.0 | 12.5 | 12.5 | -1,368.7 | 171.1 | -1,197.6 | yes |  |
|  |  | cut | -114.0 | 12.5 | 12.5 | 1,368.7 | 171.1 | 1,539.8 | **NO** | abs |
| CorporateTaxPolicy [derived] | corporate.py | increase | 137.7 | 21.6 | -21.6 | -1,604.0 | 346.5 | -1,257.5 | yes |  |
|  |  | cut | -137.7 | 12.0 | -12.0 | 1,604.0 | -192.5 | 1,411.5 | yes | correct |
| TaxCreditPolicy [EITC/CTC] | credits_core.py | increase | 17.0 | 12.0 | -12.0 | -194.9 | 23.4 | -171.5 | yes |  |
|  |  | cut | -17.0 | 12.0 | -12.0 | 194.9 | -23.4 | 171.5 | yes | correct |
| TaxCreditPolicy [other credits] | credits_core.py | increase | 17.0 | 3.0 | 3.0 | -194.9 | 5.8 | -189.0 | yes |  |
|  |  | cut | -17.0 | 3.0 | 3.0 | 194.9 | 5.8 | 200.7 | **NO** | abs |
| IRSEnforcementPolicy | enforcement.py | increase | 19.5 | 5.0 | 5.0 | -194.9 | 9.7 | -185.1 | yes |  |
|  |  | cut | - | - | - | - | - | - | - | abs |
| EstateTaxPolicy | estate.py | increase | 3.1 | -11.4 | 11.4 | -35.9 | -4.1 | -40.0 | **NO** |  |
|  |  | cut | -3.1 | -11.3 | 11.3 | 35.9 | 4.1 | 39.9 | **NO** | inverted |
| InternationalTaxPolicy | international.py | increase | 22.1 | 15.0 | 15.0 | -220.5 | 33.1 | -187.4 | yes |  |
|  |  | cut | -11.2 | 15.0 | 15.0 | 112.5 | 16.9 | 129.4 | **NO** | abs |
| PayrollTaxPolicy | payroll.py | increase | 90.0 | 17.5 | -17.5 | -1,080.5 | 189.1 | -891.5 | yes |  |
|  |  | cut | -90.0 | 17.5 | -17.5 | 1,080.5 | -189.1 | 891.5 | yes | correct |
| PremiumTaxCreditPolicy | ptc.py | increase | 95.0 | -13.0 | 3.0 | -1,140.6 | -148.3 | -1,288.9 | **NO** |  |
|  |  | cut | -35.0 | -13.0 | 3.0 | 420.2 | 12.6 | 432.8 | **NO** | inverted |
| TaxExpenditurePolicy | tax_expenditures_core.py | increase | 83.1 | -5.0 | 5.0 | -952.6 | -47.6 | -1,000.2 | **NO** |  |
|  |  | cut | -64.5 | -5.0 | 5.0 | 740.0 | 37.0 | 777.0 | **NO** | convention |
| TCJAExtensionPolicy | tcja.py | increase | -460.2 | 0.0 | 0.0 | 4,058.5 | 0.0 | 4,058.5 | yes |  |
|  |  | cut | - | - | - | - | - | - | - | zero |
| TariffPolicy | trade.py | increase | 81.8 | 34.5 | -34.5 | -818.5 | 282.7 | -535.7 | yes |  |
|  |  | cut | -122.2 | 28.8 | -28.8 | 1,221.9 | -351.3 | 870.6 | yes | correct |

**Seven classes are against the contract, and one is a convention.**

| tag | classes |
|---|---|
| `correct` (6) | `TaxPolicy`, `CapitalGainsPolicy`, `CorporateTaxPolicy` [derived], `TaxCreditPolicy` [EITC/CTC branches], `PayrollTaxPolicy`, `TariffPolicy` |
| `inverted` (3) | `AMTPolicy`, `EstateTaxPolicy`, `PremiumTaxCreditPolicy` |
| `abs` (4) | `CorporateTaxPolicy` [reported - the app default], `TaxCreditPolicy` [fallback branch], `IRSEnforcementPolicy`, `InternationalTaxPolicy` |
| `convention` (1) | `TaxExpenditurePolicy` |
| `zero` (1) | `TCJAExtensionPolicy` |

### 6.1 What the table says that the prediction did not

**§5.1 held on all thirteen classes, with one refinement.** The prediction
called `TaxCreditPolicy` `asymmetric`, on the strength of two signed branches
and one `abs` fallback. That is right about the module and wrong about the
grain: the branch a policy takes is a property of its `credit_type` and not of
the call, so the audit gives the two branches a row each and they classify
`correct` and `abs` separately rather than blending into one tag. Nothing else
in §5.1 moved.

The prediction about *provenance* held too. `amt.py`, `estate.py` and `ptc.py`
carry the identical comment pair -

```python
# Offset reduces revenue gain or loss
if static_effect > 0:
    return -total_offset  # Reduces revenue gain
else:
    return total_offset  # Reduces revenue loss
```

- above a return that does the opposite of what the comment says, in three
files by three different mechanisms. One copy-paste, three modules, and an
author who read `behavioral` as a quantity the engine *subtracts*. It does not:
`scoring_engine.py` line 166 adds it.

Four things the table shows that reading did not:

1. **The magnification is not small.** AMT books **25 percent** more than its
   own static in *both* directions ($1,146.4B of static deficit becomes
   $1,433.0B). Corporate `reported` books **12.5 percent** more on a cut,
   international **15 percent** more, PTC **13 percent** more on a repeal and 3
   percent more on an extension, the credits fallback 3 percent. None of these
   is a rounding artefact.
2. **`PremiumTaxCreditPolicy` is inverted *and* asymmetric in magnitude.**
   `f(+100) = -13.0` against `f(-100) = +3.0`, because `adverse_selection` fires
   only when `static_effect > 0`. Signing it does not make the two directions
   symmetric and is not supposed to - the asymmetry is a modelling claim about
   who drops coverage; the sign is not.
3. **`IRSEnforcementPolicy` cannot express a revenue loss at all.**
   `annual_enforcement_spending_billions = -16.0` returns a static of exactly
   `0.0`, so the module clamps rather than scoring a funding cut. Its `abs()` is
   therefore unreachable *today* through its own constructor - which is
   precisely why the sign rule has to be probed at the function and not only at
   the score, and why the row is still a defect: a clamp is not a contract.
4. **`CapitalGainsPolicy` has no function-level sign rule to probe.** It ignores
   `static_effect` entirely and rebuilds the response bracket by bracket, so
   `f(+100)` and `f(-100)` return the same number and a function-level
   classifier would call it `abs`. It is classified from the window instead
   (`classify_from="score"`), where it erodes in both directions. The script
   records that exception rather than hiding it.

### 6.2 Which of these is reachable, and by what

The defects divide by whether anything shipped can currently reach them:

| class | reachable today by | live in a benchmark? |
|---|---|---|
| `CorporateTaxPolicy` [reported] | the **Trump Corporate 15%** preset, `bill_tracker/auto_scorer.py`'s `corporate` branch, Tailor | **yes** - `trump_corporate_15` |
| `EstateTaxPolicy` | `bill_tracker/auto_scorer.py`'s `estate` branch (raw construction, module-default elasticities), `create_estate_rate_change`, `create_estate_exemption_change` | no - every calibrated estate factory zeroes both elasticities |
| `AMTPolicy` | Tailor/composer and any raw construction | no - all five AMT factories zero both elasticities |
| `PremiumTaxCreditPolicy` | `create_let_enhanced_expire` (0.3), raw construction | no - the two preset factories zero them |
| `InternationalTaxPolicy` | every international preset and benchmark - but all four are revenue **raisers**, where `abs` and the signed rule agree to the cent | latent |
| `TaxCreditPolicy` [fallback] | any credit that is neither CTC nor EITC and has no pinned annual | latent |
| `IRSEnforcementPolicy` | nothing - the static clamps at 0 for a funding cut | latent |

That table is item 22's own claim, measured: **the defect is invisible to every
gate the repository has**, and exactly one of the seven reaches a scorecard row.

## 7. Outturn

*Appended in the lane's last commit. Every figure below is from a command named
beside it, run on this branch.*

### 7.1 Six modules signed, one convention left

`python scripts/audit_offset_signs.py`, same script and same cases as section 6:

| class | module | dir | static/yr | f(+100) | f(-100) | window static | window behav | window final | erodes | tag |
|---|---|---|--:|--:|--:|--:|--:|--:|:-:|---|
| TaxPolicy | policies_core.py | increase | 36.0 | 12.5 | -12.5 | -359.6 | 44.9 | -314.6 | yes |  |
|  |  | cut | -36.0 | 12.5 | -12.5 | 359.6 | -44.9 | 314.6 | yes | correct |
| CapitalGainsPolicy | policies_core.py | increase | 20.0 | 35.7 | 35.7 | -247.5 | 201.0 | -46.4 | yes |  |
|  |  | cut | -20.0 | -35.3 | -35.3 | 247.5 | -181.6 | 65.8 | yes | correct |
| AMTPolicy | amt.py | increase | 100.0 | 25.0 | -25.0 | -1,146.4 | 286.6 | -859.8 | yes |  |
|  |  | cut | -100.0 | 25.0 | -25.0 | 1,146.4 | -286.6 | 859.8 | yes | correct |
| CorporateTaxPolicy [reported] | corporate.py | increase | 114.0 | 12.5 | -12.5 | -1,368.7 | 171.1 | -1,197.6 | yes |  |
|  |  | cut | -114.0 | 12.5 | -12.5 | 1,368.7 | -171.1 | 1,197.6 | yes | correct |
| CorporateTaxPolicy [derived] | corporate.py | increase | 137.7 | 21.6 | -21.6 | -1,604.0 | 346.5 | -1,257.5 | yes |  |
|  |  | cut | -137.7 | 12.0 | -12.0 | 1,604.0 | -192.5 | 1,411.5 | yes | correct |
| TaxCreditPolicy [EITC/CTC] | credits_core.py | increase | 17.0 | 12.0 | -12.0 | -194.9 | 23.4 | -171.5 | yes |  |
|  |  | cut | -17.0 | 12.0 | -12.0 | 194.9 | -23.4 | 171.5 | yes | correct |
| TaxCreditPolicy [other credits] | credits_core.py | increase | 17.0 | 3.0 | -3.0 | -194.9 | 5.8 | -189.0 | yes |  |
|  |  | cut | -17.0 | 3.0 | -3.0 | 194.9 | -5.8 | 189.0 | yes | correct |
| IRSEnforcementPolicy | enforcement.py | increase | 19.5 | 5.0 | -5.0 | -194.9 | 9.7 | -185.1 | yes |  |
|  |  | cut | - | - | - | - | - | - | - | correct |
| EstateTaxPolicy | estate.py | increase | 3.1 | 11.4 | -11.4 | -35.9 | 4.1 | -31.8 | yes |  |
|  |  | cut | -3.1 | 11.3 | -11.3 | 35.9 | -4.1 | 31.8 | yes | correct |
| InternationalTaxPolicy | international.py | increase | 22.1 | 15.0 | -15.0 | -220.5 | 33.1 | -187.4 | yes |  |
|  |  | cut | -11.2 | 15.0 | -15.0 | 112.5 | -16.9 | 95.6 | yes | correct |
| PayrollTaxPolicy | payroll.py | increase | 90.0 | 17.5 | -17.5 | -1,080.5 | 189.1 | -891.5 | yes |  |
|  |  | cut | -90.0 | 17.5 | -17.5 | 1,080.5 | -189.1 | 891.5 | yes | correct |
| PremiumTaxCreditPolicy | ptc.py | increase | 95.0 | 13.0 | -3.0 | -1,140.6 | 148.3 | -992.3 | yes |  |
|  |  | cut | -35.0 | 13.0 | -3.0 | 420.2 | -12.6 | 407.6 | yes | correct |
| TaxExpenditurePolicy | tax_expenditures_core.py | increase | 83.1 | -5.0 | 5.0 | -952.6 | -47.6 | -1,000.2 | **NO** |  |
|  |  | cut | -64.5 | -5.0 | 5.0 | 740.0 | 37.0 | 777.0 | **NO** | convention |
| TCJAExtensionPolicy | tcja.py | increase | -460.2 | 0.0 | 0.0 | 4,058.5 | 0.0 | 4,058.5 | yes |  |
|  |  | cut | - | - | - | - | - | - | - | zero |
| TariffPolicy | trade.py | increase | 81.8 | 34.5 | -34.5 | -818.5 | 282.7 | -535.7 | yes |  |
|  |  | cut | -122.2 | 28.8 | -28.8 | 1,221.9 | -351.3 | 870.6 | yes | correct |

**Thirteen classes `correct`, one `convention`, one `zero`**, where the branch
point had seven against the contract. Nothing else in any module changed: no
elasticity value, no base, no growth rate, no target. The whole diff is
`math.copysign` (and, in `credits_core.py`, dropping an `abs`), plus the
docstring that says why.

`tax_expenditures_core.py` is deliberately unchanged and is now documented in
its own docstring rather than only in a lane doc. Its source is CBO,
*Options for Reducing the Deficit: 2025 to 2034* (pub. 60557), Option 56: a cap
on the employer-health exclusion makes employers offer less generous coverage
**and** shifts compensation back into taxable wages, and CBO's text has both
channels raising revenue, so an offset that adds to the static effect is right
*there*. It is unsourced in magnitude on the other five expenditure benchmarks,
and choosing it module-wide moves every fitted expenditure row and the whole
leave-one-out column together. **That is section 6.2 item 8's owner decision and
this lane did not make it** - see 7.6.

### 7.2 What moved

| | before | after |
|---|--:|--:|
| **Tier 1 - out-of-sample** | 26 @ 15.9% / 11.4% / 16 / 22 | **unchanged, to the cent on all 26 rows** |
| **Tier 2 - fitted calibrated** | 23 @ 1.6%, 23/23 within 15% | **21 @ 1.7%, 21/21 within 15%** |
| **Tier 2 - unfitted reconstructions** | 31 @ 56.6% / 29.9%, 9 / 12 | **33 @ 54.4% / 28.4%, 9 / 14** |
| **Tier 2 - leave-one-out** | 18 @ 29.6% / 19.1%, 8 within 15% | **unchanged; `--donor-matrix` byte-identical** |
| Shipped presets (53) | - | **2 moved** |

**Both Tier 2 counts changed population, and neither move is an improvement -
quote the constant-population readings beside them.** Held in place, the fitted
tier reads **23 @ 3.4%, 21/23 within 15%**; on the 31 rows the reconstruction
tier already held, it reads **56.6% / 29.9%**, exactly what it read on
`790caff`. The fitted mean *falling* 3.4% -> 1.7% and the reconstruction mean
*falling* 56.6% -> 54.4% are both **composition, not accuracy**: the two rows
that left the fitted tier are the two the sweep moved, and they are better than
the reconstruction tier's average and worse than the fitted tier's. Read the two
together or neither.

**Two scorecard rows moved, both in the fitted calibrated tier, and neither was
retuned.**

| row | target | provenance | model before | model after | error |
|---|--:|---|--:|--:|---|
| `trump_corporate_15` | +$1,920.0B | `model_estimate` | +1,918.0 | **+1,491.8** | 0.1% -> **22.3%** |
| `repeal_ptc` | -$1,100.0B | `secondhand` | -1,096.2 | **-896.9** | 0.3% -> **18.5%** |

Both are the case the lane brief describes: **a fitted constant that was
compensating for a sign bug**. `create_republican_corporate_cut` books a static
of -$142B/yr and was adding 12.5% of it to the deficit rather than taking it
off; `create_repeal_ptc` books +$99.65B/yr of saving and was adding 10% of it to
the saving. In both, the annual level had been chosen so that
*static x (1 + offset share)* landed on the target, so signing the offset takes
the score to *static x (1 - offset share)* - a movement of twice the offset,
which is exactly what the table shows. **No constant was moved to put either
back**: section 1.1 of the plan forbids it, and putting them back would re-fit
the level to the defect.

Read both misses with their provenance attached. `trump_corporate_15`'s +$1,920B
carries provenance **`model_estimate`** - it is this repository's own output,
recorded as an expectation - and `repeal_ptc`'s -$1,100B is one of the twelve
`secondhand` rows section 6.2 item 5 lists as untraceable to any document ("CBO
estimate", no publication). So neither 22.3% nor 18.5% is a distance from a
published score. What they measure is that the calibrated tier had two rows
whose agreement was buying part of its 0.1% from a bug, which is the honest
reading and the reason the fitted mean rose.

The fitted mean moving **1.6% -> 3.4%** was the whole of the tier's change; the
other 21 rows are identical to the cent.

### 7.2.1 And then both rows left the fitted tier

*Added after CI. `python scripts/check_readiness.py --strict` fails on CI
(exit 2) where it passes on `main`, and this branch is why: a **fitted**
benchmark rated Poor is strict-blocking, because its parameters exist to
reproduce that target, and signing the corporate offset made
`trump_corporate_15` exactly that. It could not be seen locally because Python
3.14 already fails the runtime check and masks everything after it; CI runs 3.12.*

The owner's decision was **reclassify, do not retune, do not exempt**, on the
precedent `readiness.py` cites in its own comment and that Wave 2 L1 set for
`pwbm_39_with_stepup` and Wave 3 L8 for `trump_universal_10` and
`trump_china_60`: **a constant that reproduced its target only through a defect
is not a calibration to that target.** Both rows now carry
`calibrated_to_target: False` in `fiscal_model/validation/scenarios.py`, with the
finding written into the comment above them and into `known_limitations`, so they
report in the unfitted-reconstruction tier where a documented miss is a finding
rather than a calibration regression.

| row | rating | why it was reclassified |
|---|---|---|
| `trump_corporate_15` | **Poor (22.3%)** - what trips the gate | the `abs()` offset added 12.5% of a negative static to the deficit; the annual was fitted so that *static x 1.125* hit +$1,920B |
| `repeal_ptc` | **Acceptable (18.5%)** - does not trip it | the inverted offset added 10% of the saving; the annual was fitted so that *static x 1.10* hit -$1,100B |

`repeal_ptc` is reclassified anyway, and the reason is worth stating: it sits
**1.5pp from Poor**, and a Poor row in the fitted tier with no
`known_limitations` is a *hard* readiness failure rather than a warning. The
classification follows the finding, not the rating - and the finding is
identical on both rows. Both also now carry a note, which readiness requires
before a Poor row is a warning at all.

`calibrated_to_target` is threaded through the corporate and PTC runners with a
default of `True`, so **no other scenario moved**; a test pins the two-row scope
so the default cannot quietly invert and empty the tier.

Neither target is published, which is the other half of why this is the right
move: +$1,920B is `model_estimate` (its own note says "No official score") and
-$1,100B is untraceable `secondhand` ("CBO estimate", no publication, on section
6.2 item 5's list of twelve). Both are queued for the next provenance pass, to
be retired or re-sourced - see 7.6 item 3.

Nothing else moved with them. Tier 1 is unchanged at 26 @ 15.9%,
`run_loo.py --donor-matrix` is still byte-identical to `790caff`, and no shipped
number changed - the two presets had already moved with the sign fix, and this
commit changes only which tier reports them. **No test pinned the fitted count
of 23 or the reconstruction count of 31**, so none had to be restated;
`tests/test_cold_holdout.py`'s anti-leakage invariant is untouched. Three new
tests pin what did change: the classification and its notes, the two-row scope,
and that strict readiness reports no `documented_calibrated_policy_ids`.

### 7.3 The two presets, and the caption

`PRESET_POLICIES` swept end to end on both trees (all 53 scored through
`create_policy_from_preset` on the app's FY2026-FY2035 window):

| preset | before | after | |
|---|--:|--:|--:|
| **Trump Corporate 15%** | +$1,690.6B | **+$1,314.9B** | **-22.2%** |
| **Repeal ACA Premium Credits (-$1.1T)** | -$966.2B | **-$790.5B** | **+18.2%** |

The other **51 score to the cent** what they scored on `790caff`. Under
Decision 6 the two that moved ship with their explanation:
`behavioural_sign_caption` in `fiscal_model/ui/tabs/results_summary.py`, after
the existing captions, computed from the scored result so it cannot drift from
the headline above it. It names the static effect, the offset, the current
figure **and the figure the user would have seen before the sweep**. It fires
only where the number actually moved - the three inverted modules moved in both
directions, the four `abs()` ones only for a revenue-losing policy - so
`biden_corporate_28` and the other 50 stay silent, and a test pins that.

**Their validation badges drop with them**, which is the other user-visible
consequence and is not a caption's job to soften. `fiscal_model/ui/preset_validation.py`
rates a preset off its scorecard row, so Trump Corporate 15% goes
**Excellent (0.1%) -> Poor (22.3%)** and Repeal ACA Premium Credits
**Excellent (0.3%) -> Acceptable (18.5%)**. That is the correct reading: the
green badges were partly bought by the defect, and the app now says how far
those two rows are from targets that are themselves a `model_estimate` and an
untraceable `secondhand` figure.

Two user-visible surfaces that are not presets also change, both quietly for the
better: `bill_tracker/auto_scorer.py` builds a raw `EstateTaxPolicy` with
module-default elasticities (inverted until now) and calls
`create_corporate_rate_change(include_behavioral=True)` (`abs` until now), and
Tailor/Build can reach any of the six classes through the composer without a
factory's zeroed elasticity in the way. Both are exploratory-tier surfaces held
to a UX bar, not an accuracy one, and neither is gated.

### 7.4 Falsification: one of the four fired

1. **A row moving whose class 5.1 called `correct`** - did **not** fire. No
   `TaxPolicy`, `CapitalGainsPolicy`, `PayrollTaxPolicy`, `TariffPolicy` or
   corporate-`derived` row moved anywhere in the three tiers or the LOO suite.
2. **A row moving that 5.2 named as not moving** - **fired**, on `repeal_ptc`.
   Section 5.2 said "PTC - `create_extend_enhanced_ptc` and `create_repeal_ptc`
   zero the elasticities". That is true of the first factory and **false of the
   second**: `create_repeal_ptc` sets `coverage_elasticity=0.0` under the
   comment *"Not modeling coverage offset"* and never touches
   `adverse_selection_factor`, which keeps its dataclass default of `0.1`. So
   the module's *other* channel was live on a shipped preset and a fitted
   benchmark the whole time, and the pre-registration was written from the
   factory's comment rather than from its argument list. The lesson generalises
   past this row: **"the factory zeroes the elasticity" is a claim about every
   elasticity the module has, and a module with two of them can zero one.**
3. **`trump_corporate_15` not moving** - did not fire; it moved, by 22.2%,
   within a point of the 22% section 5.2 predicted and to a figure (+$1,491.8B)
   about 0.1% off the +$1,490B it named.
4. **A class classifying differently from 5.1** - fired once and harmlessly:
   `TaxCreditPolicy` was predicted `asymmetric` and the audit gives its two
   branches a row each, `correct` and `abs`. Recorded in 6.1.

### 7.5 Gates and tests

| command | result |
|---|---|
| `python -m pytest tests/ -q` | **3,506 passed, 7 skipped** (`790caff` documents 3,415 passed, 1 skipped; the lane adds 97 tests, 6 of them the convention's and capital gains' skips) |
| `python scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | **exit 0** (15.9%, 22/26 - the gate is not approached) |
| `python scripts/run_loo.py --donor-matrix --max-mean-error 75` | **exit 0** (29.6%) |
| `python scripts/run_loo.py --donor-matrix` | **byte-identical** to `790caff` |
| `python scripts/run_validation_dashboard.py` | **exit 1, byte-identical output to `790caff`** |
| `python scripts/check_readiness.py --strict` | **exit 2**, the one remaining strict issue being the Python 3.14 runtime check (see 7.2.1) |
| `python -m ruff check fiscal_model/ tests/ scripts/` | clean |

The dashboard and the readiness check both fail on `790caff` too, for the two
reasons they name themselves - `runtime [degraded] Python 3.14.0 (supported
>=3.10,<3.14)` and `microdata [warn] SOI 2023: returns 119% / AGI 81%` - and
neither is touched by this lane. Both were re-run against a clean export of
`790caff` rather than taken on trust, and both produced **identical bytes**; the
dashboard does not print the by-construction calibrated tier, which is why the
two moved rows do not appear in it.

**That equality is exactly what hid the CI failure**, and it is worth writing
down as a lesson rather than a footnote. The local runtime check fails first on
Python 3.14, so `check_readiness.py --strict` exits 2 on both trees and a byte
diff of its output shows nothing - while on CI's 3.12 `main` passes and this
branch did not, because `trump_corporate_15` had become a Poor row still
declared fitted. **"Identical to main" is only evidence when the check being
compared can distinguish them**, and a check that is already failing for another
reason cannot. The direct query is what settles it:

```
python -c "from fiscal_model.readiness import build_readiness_report, \
    strict_readiness_issues; r=build_readiness_report(); \
    print([(i.name, i.details.get('documented_calibrated_policy_ids')) \
           for i in strict_readiness_issues(r)])"
```

which returned `[('runtime', None), ('revenue_scorecard', ['trump_corporate_15'])]`
before the reclassification and returns **`[('runtime', None)]`** after it -
`documented_calibrated_policy_ids` empty, and the only remaining strict issue the
Python 3.14 one that fails on `main` too. A test now asserts that, so the next
lane does not have to know to run it.

`tests/test_offset_sign_contract.py` is the lane's own gate: parametrised over
every class in both directions, plus three caption tests and two structural
ones. **The one that matters is
`test_every_offset_implementation_is_covered`**, which greps the package for
`def estimate_behavioral_offset` and fails if a class is missing from
`build_cases` - because "a module nobody swept" is how all four of the
previously found defects got in.

It was verified to *fail* rather than assumed to work: putting `enforcement.py`'s
`abs()` back makes it fail, and the **first draft of the test did not catch
it**, because probing only the direction a module's own constructor can reach
lets a clamped module through. That is now the reason the test probes plus and
minus $100B on every instance, and the reason is written into the test.

### 7.6 For the owner

Four things this lane found and did not decide.

1. **Decision 1's corporate comparison reverses with the sign, and the module
   is now due to flip.** `CORPORATE_APP_MODE`'s own docstring table records
   reported at -0.1% / +3.7% against derived's -11.5% / +7.8% and concludes that
   Decision 1's rule keeps the module on `reported`. Signing the reported offset
   takes reported's mean to **13.02%** against derived's **unmoved 9.67%**, so
   by the decision's own words - *"reported stays the app default per module
   until that module's derived error is below its fitted error"* - corporate is
   now due to flip. **This lane did not flip it**, for two reasons worth
   separating: flipping moves both corporate benchmark rows and the two
   shipped corporate presets with them (on the benchmarks' own window,
   `biden_corporate_28` -$1,397.2B -> -$1,452.1B and `trump_corporate_15`
   +$1,491.8B -> +$1,698.6B), so it needs its own caption and its own
   pre-registration; and the row that produces the reversal,
   `trump_corporate_15`, has provenance
   `model_estimate`, so *neither* ranking is evidence about the world. The
   comparison is pinned as a test
   (`test_decision_1_now_ranks_derived_ahead_of_reported`) so the reversal
   cannot be lost.
2. **The expenditure convention is still unchosen, and it is now the only one.**
   Item 8 stands exactly as written, but its context has changed: it used to be
   one of four modules whose offset pointed the wrong way and is now the only
   one, which makes it a deliberate exception rather than a member of a family.
   It is the single entry in `CONVENTION_EXCEPTIONS`, cited to CBO Option 56,
   and the decision is still whether the same convention is right for
   `eliminate_salt`, `repeal_salt_cap`, `eliminate_mortgage`, `cap_charitable`
   and `eliminate_step_up`, where nothing sources it. Worth noting the size: the
   convention is worth **+5.0% of the static effect** on a SALT elimination and
   **+20%** on Option 56, and it moves the fitted rows and the LOO column
   together.
3. **Two rows are now visibly carrying a target nobody can check.**
   `trump_corporate_15` (`model_estimate`, "CBO/Treasury") and `repeal_ptc`
   (`secondhand`, "CBO estimate") both sat at about 0% while a sign bug was
   inflating them. `repeal_ptc` is on section 6.2 item 5's list of twelve
   untraceable `secondhand` rows; `trump_corporate_15` is not on it because it
   is not `secondhand` at all - it is one of the seven `model_estimate` rows,
   i.e. this model's own output recorded as an expectation, which is a
   different and weaker thing again. A provenance pass on the two would say
   whether 22.3% and 18.5% are model error or target error; today nobody can
   tell. Since 7.2.1 the tier no longer reports them as *calibration* error -
   both are reconstructions now - but it still reports them against targets no
   document backs.

   > **Addendum, 2026-09-05 (docs sync).** Closed by PR #122,
   > `planning/lanes/PROVENANCE_corporate_ptc.md` §3 and §4:
   > `trump_corporate_15` was superseded to the published range
   > [+$595.0B, +$673.1B] and now reads **121.6%** rather than 22.3%, so the
   > 3.4% held-in-place fitted reading in §7.2 is **7.7%** on merged main;
   > `repeal_ptc` was **examined and left**, its −$1,100B traced to CBO/JCT
   > pub. 51298 Table 2's $1,142B — a baseline projection, not a repeal
   > score, and adopting it would take the row to 21.5%.
4. **`biden_corporate_28`'s target is a bundled rate-plus-GILTI row.** Not this
   lane's finding and not changed here: the corporate memo merged to `main` as
   `planning/memos/CORPORATE_PER_POINT_YIELD.md` (PR #120) recommends the
   benchmark become **`line_item_differs`**, because the module scores a rate
   change alone against a published figure that is not one. It matters to this
   lane only because `biden_corporate_28` is the *other* half of Decision 1's
   corporate comparison in item 1 above - so the row that keeps reported ahead
   on one benchmark and the row that puts derived ahead on the other are both
   now under provenance question, and the comparison should probably not be
   re-decided until they are settled. **Noted, not changed.**

   > **Addendum, 2026-09-05 (docs sync).** Closed by PR #122 §1:
   > `biden_corporate_28` is now `line_item_differs` carrying the new
   > `scope_differs` kind — the figures agree to 0.2% and the *reforms* do
   > not. The target did not move, because the GILTI leg's size is never
   > printed. Item 1's Decision 1 reversal has since reversed twice more; on
   > merged main it is **reported 62.75% vs derived 61.43%**, and a flip PR is
   > open pending the owner. See `MODELING_IMPROVEMENT.md` §5.6 finding 4.

### 7.7 What this lane did not touch

`preregistered.py`, `holdout.py`, `loo.py`, `target_revisions.py`,
`KNOWN_SCORES`, `CBO_SCORE_MAP`, `tests/test_cold_holdout.py`'s anti-leakage
invariant, `.github/workflows/`, any CI threshold, any elasticity value, any
base, any growth rate, and `planning/MODELING_IMPROVEMENT.md` - whose section
6.2 items 22 and 8 are both stale after this lane, and which a docs pass owns.
