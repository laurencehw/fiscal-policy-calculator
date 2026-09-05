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

*Appended in the lane's last commit.*
