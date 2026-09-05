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

*Appended in the commit that adds `scripts/audit_offset_signs.py`. Built by
running the script, not by reading.*

## 7. Outturn

*Appended in the lane's last commit.*
