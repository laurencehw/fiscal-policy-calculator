# HSA-H1 — One base rule, four surfaces

*Lane of `planning/HIGH_STAKES_ACCURACY.md` §3 H1, Wave A. Branch
`model/hs-a-h1-base-rule`, cut from `main` @ `8964cb1` (which is `f3dc042` plus three
nightly bill-tracker data commits).*

*Pre-registration written 2026-09-09, **before** any model file was opened. Every "before"
figure in §3 was measured on the branch point by the four runs named in §0 and is
reproduced from a saved artifact, not recalled.*

Sibling lanes in this wave, running in parallel on disjoint files: **H6** owns
`fiscal_model/ui/preset_validation.py`, `fiscal_model/ui/controller_utils.py` and their
tests; **H13** owns `docs/VALIDATION.md`, `docs/METHODOLOGY.md` and one additive caption
block in `fiscal_model/ui/tabs/results_summary.py`. H6's four **label** strikes and the
`repeal_corporate_amt` sign are folded into this PR, because both lanes would otherwise
edit `fiscal_model/app_data.py`.

---

## 0. The yardstick, frozen before anything moved

Four runs on the branch point, saved to the lane's scratch directory and byte-compared
after:

| Run | Command | Artifact |
|---|---|---|
| Tier 1 | `python scripts/cold_holdout.py --json` | `before_holdout.json` |
| Dashboard | `python scripts/run_validation_dashboard.py` | `before_dashboard.txt` |
| Leave-one-out | `python scripts/run_loo.py --donor-matrix` | `before_loo.txt` |
| Preset + generic sweep | `sweep.py` (52 presets × static/dynamic through `composer._build_preset_policy` → `_scorer_for`; three generic shapes through four constructors) | `before_sweep.json` |

`run_validation_dashboard.py` exits **1 on the branch point already** — the health gate
trips on `runtime [degraded] Python 3.14.0 (supported >=3.10,<3.14)` and
`microdata [warn] SOI 2023: returns 119% / AGI 81%`. Both are pre-existing and neither is
this lane's. The exit code is therefore not a signal here; the printed blocks are.

**The plan's §1.3(a) table reproduces to the cent**, which is the condition the lane was
told to satisfy before proceeding:

| Shape | Tailor / preset | Ask (raw engine) | plan §1.3(a) |
|---|--:|--:|---|
| 1pp, all brackets | **−920.291193** | **−1,017.211911** | −920.3 / −1,017.2 ✓ |
| 2pp above \$400K | **−166.503232** | **−314.632045** | −166.5 / −314.6 ✓ |
| 3pp above \$2M | **−134.612557** | **−283.469479** | −134.6 / −283.5 ✓ |

---

## 1. Mechanism

### 1.1 What is actually wrong

`ordinary_income_base` decides whether an ordinary-bracket rate change is priced on the
non-preferential share of marginal income or on the whole of it. It is a **fact about the
policy** — read off the source document, never inferred from the shape — and the battery
proves the inference cannot be done: `biden_high_income_tax` is a rate change *above a
threshold* and is ordinary-based; CBO Option 46's surtax *above a threshold* is
AGI-inclusive. `cold_holdout.py --ordinary-base` is the tell — forcing one treatment on
every row worsens the other treatment's cases in both directions.

That attribute today has **three different defaults**, and no surface says which one it
used:

| Constructor | Site | Default | Value |
|---|---|---|:-:|
| dataclass | `policies_core.py:146` | literal `False` | AGI-inclusive |
| Tailor | `ui/policy_input_tax.py:221`, `:514` | literal `True` | ordinary |
| composer | `composer/composer.py:148` | `not preset_data.get("agi_inclusive_base", False)` | ordinary |
| Ask | `assistant/tools.py:536-544` | passes nothing | AGI-inclusive |

So the same specification returns two answers 1.89× apart depending on which box the user
typed it into, and the surface that disagrees with the validated row is not always the same
one: at 1pp/all-brackets the *validated* shape is Tailor's, at 2pp/\$400K it is Ask's.

A second, independent defect sits beside it: **no preset carries `agi_inclusive_base`**
(`grep agi_inclusive_base fiscal_model/app_data.py` returns nothing). The flag exists only
on `CBOScore` records, so three shipped surtax presets are scored on the ordinary base
while their own validation rows are scored AGI-inclusive — the app prints −\$134.6B beside
a label quoting TPC's −\$350B while the scorecard reports 19.0%.

### 1.2 The fix

**(a) One constant, one default, read by every constructor.**
`fiscal_model/policies_core.py` gains

```python
DEFAULT_ORDINARY_INCOME_BASE = True
```

and the dataclass field defaults to it. `True` — the **ordinary** base — because that is
the validation manifest's own default for a bracket change: `validation/core.py:937-938`
reads `ordinary_income_base = not score.agi_inclusive_base`, and `agi_inclusive_base`
defaults to `False` on `CBOScore`. The manifest's default is therefore ordinary, and the
app now agrees with it instead of contradicting it in two places out of four.

`validation/core.py` **is not touched**. It reads the record's own `agi_inclusive_base`
and passes an explicit value, so it is insulated from the dataclass default by
construction. That insulation is the falsification test in §4.

**(b) Three presets get the attribute their sources state.** This is a per-preset
transcription, not a rule:

| Preset | `agi_inclusive_base` | Source that says so |
|---|:-:|---|
| Warren Ultra-Millionaire Surtax | `True` | TPC's own table, cited by `CBO_SCORE_MAP`: "3pp surtax on **AGI** >\$2M" |
| High-Earner Medicare Surcharge 2pp | `True` | Treasury FY2025 Green Book, cited by `CBO_SCORE_MAP`: "+2pp Medicare surcharge on **investment + wage** income >\$400K" |
| Progressive Millionaire Tax | `True` | **No source document exists** — see §1.3 |

**(c) The surfaces say which base they used.** Tailor keeps its checkbox, seeded from the
shared constant rather than a literal. Ask's `score_hypothetical_policy` gains the same
optional flag with the same default and returns the base in its payload, so the assistant
can state it. A test constructs one specification through all four constructors and
asserts identical ten-year totals.

**(d) Four label figures with no record are struck, and one sign is corrected.** §6.

### 1.3 Progressive Millionaire Tax has no document, and the lane says so

The preset is a 5pp surtax above \$1,000,000 with the description "5pp surtax on
millionaires". It has **no `CBO_SCORE_MAP` entry, no `PRESET_TO_SCORECARD_ID` badge and no
scorecard row of any tier** (§1.4 of the plan lists it among the eight). There is
therefore nothing to transcribe: the base is a **design choice of the preset**, not a
reading of a source.

The plan pre-registers it AGI-inclusive and this lane implements that, for one stated
reason: a *surtax* stated on an income amount above a threshold, with no bracket schedule
named, is the same instrument as Warren's and Treasury's, both of which are AGI-inclusive
on their own documents. That is an analogy, not a transcription, and the preset's own
description is amended to say so in the app rather than only here.

---

## 2. Files owned

| File | Change |
|---|---|
| `fiscal_model/policies_core.py` | `DEFAULT_ORDINARY_INCOME_BASE`; dataclass field reads it |
| `fiscal_model/app_data.py` | three `agi_inclusive_base: True` flags + descriptions; four label strikes + descriptions; one `official_score` sign |
| `fiscal_model/assistant/tools.py` | `ordinary_income_base` parameter, tool schema, payload field |
| `fiscal_model/ui/policy_input_tax.py` | checkbox + preset seed read the constant |
| `fiscal_model/composer/composer.py` | preset base reads the constant |
| `fiscal_model/preset_ids.py` | renamed label keys (ids unchanged) + `LEGACY_LABEL_ALIASES` |
| `fiscal_model/policy_status.py` | two renamed label keys |
| `fiscal_model/ui/calculation_controller.py` | `.get(..., True)` reads the constant |
| `api.py` | Pydantic field default reads the constant |
| `fiscal_model/ui/tabs/results_summary.py` | **one** additive caption function + one call site (H13 adds a separate one; kept self-contained) |
| `tests/test_base_rule_contract.py` | new — the four-constructor agreement test and the label rule |

**Not touched, and each for a reason:** `fiscal_model/validation/core.py` (reads the
record; moving it would move Tier 1), `fiscal_model/ui/preset_validation.py` and
`fiscal_model/ui/controller_utils.py` and their tests (H6), `docs/VALIDATION.md` and
`docs/METHODOLOGY.md` (H13), `CLAUDE.md` / `README.md` / `planning/NEXT_STEPS.md` /
`planning/MODELING_IMPROVEMENT.md` / `docs/CHANGELOG.md` (docs sync follows the wave).

---

## 3. Pre-registered movements

Every figure below was computed on the branch point by scoring the *same* policy object
twice, once with each value of the flag. They are predictions of what the implementation
must reproduce, not descriptions of what it did.

### 3.1 Three shipped presets (from **(b)**)

| Preset | static, before | static, after | dynamic, before | dynamic, after |
|---|--:|--:|--:|--:|
| Warren Ultra-Millionaire Surtax | −134.612557 | **−283.469479** | +98.204033 | **−29.009870** |
| High-Earner Medicare Surcharge 2pp | −166.503232 | **−314.632045** | −0.131447 | **−126.723105** |
| Progressive Millionaire Tax | −354.634800 | **−648.092029** | +52.334960 | **−198.455122** |

Against the targets their own labels quote: **Warren 61.5% → 19.0%** (vs TPC −350.0);
**Medicare surcharge 46.3% → 1.5%** (vs Treasury −310.0). Progressive Millionaire has no
target and gets no error figure — that is the point of §1.3.

### 3.2 Ask's generic path (from **(a)**)

`raw_engine_estimate_billions`, which is the figure §1.3(a) tabulates:

| Shape | before | after |
|---|--:|--:|
| 1pp all brackets | −1,017.211911 | **−920.291193** |
| 2pp above \$400K | −314.632045 | **−166.503232** |
| 3pp above \$2M | −283.469479 | **−134.612557** |

The `headline_estimate_billions` the assistant is instructed to quote is the capability
gate's benchmark interpolation, not the engine run, so it is **predicted not to move** on
any of the three. That prediction is recorded because if it *does* move, the gate reads
the engine estimate somewhere the lane did not find.

### 3.3 Tailor does not move

`2pp above $400K` with the box unticked stays at **−166.503232**, to the cent. The defect
§1.3(a) records is that Ask silently disagreed with Tailor, not that −\$166.5B is the
wrong answer to the question Tailor was asked: a custom entry has no source document to
read a base off, so the shared default is the only honest answer and the caption is what
makes it legible.

### 3.4 Collateral of flipping the dataclass default, measured per caller

Every `TaxPolicy(` construction in the tree was enumerated (130 sites, 39 files). A site
changes behaviour only if it builds a `PolicyType.INCOME_TAX` policy **and** passes no
explicit flag — `_ordinary_income_share` returns 1.0 for every other policy type. Eight
non-test sites qualify or were checked and cleared:

| Site | Verdict | Measured |
|---|---|---|
| `assistant/tools.py:536` | **moves — this is the lane's object** | §3.2 |
| `fiscal_model/health.py:224` | **moves** | `test_score` **−15.7 → −8.3** |
| `classroom/engine.py:463` | **moves** | 2.6pp>\$400K **−409.021659 → −216.454201**; 1pp>\$400K −157.316023 → −83.251616 |
| `bill_tracker/auto_scorer.py:158` | **moves** | 2pp>\$400K **−314.632045 → −166.503232** |
| `policies_factory.create_income_tax_cut` | flips to ordinary; **no production caller** | — |
| `policies_factory.create_new_tax_credit` | `TAX_CREDIT` type — `_ordinary_income_share` returns 1.0 | no change |
| `api.py:1049` (`/score` custom) | already `request.ordinary_income_base`, Pydantic default **already `True`** | **no change**; the field is repointed at the constant |
| `api.py:580` (`/score/preset`) | already `not agi_inclusive_base` | unchanged mechanism; moves for the three presets of §3.1, by design |
| `validation/core.py:938` | reads the record | **must not move** — §4 |

Three of those are decided explicitly rather than inherited:

- **`health.py`'s tripwire is allowed to move.** Its own comment says "moving the app's
  window is not a reason for that tripwire to move" — a base-rule change *is* a reason,
  and the probe's job is to run the shipped default. Nothing asserts −15.7: it is printed
  by `run_validation_dashboard.py:221` and by the readiness gate and compared to no
  constant anywhere in the tree.
- **`classroom/engine.py` is allowed to move.** The classroom is a fifth surface with the
  same defect, and it grades against the model's *own* live answer, so grading stays
  self-consistent. It is not pinned to AGI-inclusive, because pinning it would recreate
  exactly the divergence this lane exists to remove.
- **`bill_tracker` is allowed to move.** Blue tier, demo-grade extraction; it now agrees
  with Tailor.

### 3.5 Zero validation rows move

- `cold_holdout.py --json` **byte-identical** (`cmp` against `before_holdout.json`).
- `run_validation_dashboard.py` — the calibrated block (fitted / held-in-place /
  reconstruction) and the twelve sub-populations identical.
- `run_loo.py --donor-matrix` **byte-identical**.
- Every preset other than the three in §3.1 identical to the cent, both static and dynamic.

---

## 4. Falsification

The lane is **falsified** if any of these fails:

1. `cold_holdout.py --json` differs from `before_holdout.json` by a single byte.
2. `run_loo.py --donor-matrix` differs from `before_loo.txt` by a single byte.
3. Any of the six figures in §3.1 or the three in §3.2 misses its pre-registered value.
4. Tailor's `2pp above $400K` moves off −166.503232 with the box unticked.
5. Any preset outside §3.1 changes its static or dynamic ten-year total.
6. The four-constructor agreement test fails for any specification.
7. Any label rename leaves a legacy `?preset=<old emoji label>` URL unresolvable, or
   changes a stable preset id.

---

## 5. Explicitly out of scope

- **The generic base's flat ten-year path** (§1.3(c) of the plan). Every generic run
  returns the same annual ten times; CBO's own nominal path grows 3.878%/yr. That is **H2**,
  Wave B, and it must be serial with this lane because H2's predicted endpoints are
  computed *with* this base rule in place.
- **`get_confidence_context`'s tier-blind "High confidence" badge** (§1.3(d)) and the
  28 missing `PRESET_TO_SCORECARD_ID` entries — **H6**, this wave, different files.
- **Registering a scorecard target** for any of the four struck labels. §6 records the
  documents the search found; the ledger is **H9**, Wave B. This lane strikes, it does not
  register.
- **Retuning any constant.** No module constant is opened. The three preset flags are
  transcriptions and the shared default is a choice between two values that already exist
  in the tree.
- **`classroom/assignments/laffer_curve.yaml`'s stale hint** (§6.3). Reported, not edited:
  moving hint prose onto a model number is fitting the lesson to the output.

---

## 6. The four label strikes and one sign (H6's edits, carried here)

### 6.1 The rule

A preset with **no scorecard row of any tier** may not display a dollar figure in its
label. Four do. `"Top Rate to 45%"` is the model for how to do it right: its −\$420B was
withdrawn in the Phase E provenance pass, the label carries no figure, and the description
says why.

All four were verified to have no row: no `CBO_SCORE_MAP` entry, no
`PRESET_TO_SCORECARD_ID` entry, and no `policy_id` in `validation/` matching
`comprehensive`, `high_income_enforcement`, `carbon_tax_25` or `extend_ira`.

### 6.2 The search, recorded either way

| Label figure | Searched | Verdict |
|---|---|---|
| 💊 Comprehensive Drug Reform **−\$600B** | CBO Options 60557, CBO 58793 / 60812 / 58850, CMS, CRFB | **No published score.** Nearest published figures are components an order of magnitude smaller — CBO put IRA negotiation at \$98.5B (2022–2031), the H.R.3-style 50-drug framework at ~\$76B/decade. **Strike.** |
| 🔍 High-Income Enforcement **−\$250B** | CBO 59972, CBO 54826, Treasury Green Books, JCT | **No published score at this dose or scope.** CBO publishes *untargeted* appropriation increases: +\$20B → −\$41B deficit, +\$40B → −\$63B deficit (pub. 59972, 2024–2034). No published estimate isolates >\$400K returns or large partnerships, and CBO's *larger* dose yields \$63B against this label's \$250B. **Strike.** |
| 🌱 Extend IRA Credits Beyond 2032 **\$400B** | JCT, CBO, Treasury, PWBM, Tax Foundation | **No published score.** Every figure found scores the credits *as enacted* or their *repeal* (JCT \$663B; Tax Foundation \$851B; CBO/JCT ~\$786B), none a five-year extension past the sunset. **Strike.** |
| 🌱 Carbon Tax \$25/ton **−\$1.0T** | CBO budget option 58638, CBO 60557 Option 73, CRFB Feb 2025, JCT, Treasury, RFF | **A document exists, at a different figure and window.** CBO/JCT, *Options for Reducing the Deficit: 2023 to 2032*, "Impose a Tax on Emissions of Greenhouse Gases" (58638): \$25/tonne rising 5% plus inflation, **−\$865B, 2023–2032**. CRFB's February 2025 re-scoring puts \$25/ton + 5% at **\$960B on FY2026–2035**. Neither is −\$1.0T and neither is on this repository's window. **Strike, and record as registrable** — that is H9's ledger, not this lane's. |

The registrable candidate is therefore **one** of four, and it is registrable at a figure
the label does not currently quote.

### 6.3 The sign

`"⚖️ Repeal Corporate AMT (-$220B)"` carries −220.0 in its label **and** in
`CBO_SCORE_MAP["official_score"]`, where the scorecard target and the model both carry
**+220.0**. Verified against `validation/scenarios.py:582` (`expected_10yr: 220.0`) and
`validation/benchmark_sources.py:735` (JCT JCX-18-22 scores CAMT as a \$222,248M revenue
*raiser*, so repealing it *costs* that amount, "which is the direction this benchmark
scores and the repository's sign convention makes positive").

The `official_score` half is load-bearing: `deficit_target.build_catalog` drives the Build
page off `official_score`, and `BuildOption.raises_revenue` is `score < 0`. Repealing the
corporate AMT is currently checkable in Build as a **\$220B revenue raiser**. It is a
\$220B cost.

Both halves were to be corrected: label → `"⚖️ Repeal Corporate AMT (+$220B)"`,
`official_score` → `+220.0`. **Only the second was.** See §7 finding 9 for why, and §10 for
the handover.

### 6.4 Ids and links

**Stable preset ids do not change** — they ship in share URLs. `preset_ids.py` gains
`LEGACY_LABEL_ALIASES`, folded into `_ALIAS_INDEX`, so `?preset=<old emoji label>` still
resolves. `_spellings` already strips a trailing `(...)` score suffix from the *new*
label, which covers the stripped forms; it does not cover the full old string, which is
what the alias adds.

---

## 7. Decision 6

Three shipped preset numbers move by 1.8–2.1×. One additive caption block in
`fiscal_model/ui/tabs/results_summary.py`, **computed from the scored result** so it
cannot drift from the figure above it, states the old figure, the new one, and that the
base is now AGI-inclusive on the preset's own source. It fires only on a policy whose base
attribute came from a preset that declares `agi_inclusive_base`, so it is silent on every
other run and trivially separable from H13's block in the same file.

---

# Outturn

*Appended 2026-09-09, after implementation. Every "after" figure is from a re-run of the four
commands in §0 on the finished branch, compared with `cmp` where "byte-identical" is claimed.*

## 6. Pre-registered vs measured

**Every pre-registered figure landed exactly, to six decimal places. Nothing was falsified.**

**One pre-registered *action* was not completed**: the `repeal_corporate_amt` **label** rename
(§6.3 of the pre-registration) is deferred, because it cannot be made without editing a sibling
lane's map and test in the same commit. Its `CBO_SCORE_MAP` sign — the load-bearing half — was
corrected. Finding 9 measures the collision; §10 hands it over.

### 6.1 The three shipped presets

| Preset | before | pre-registered | measured | error vs its own target |
|---|--:|--:|--:|---|
| Warren Ultra-Millionaire Surtax | −134.612557 | −283.469479 | **−283.469479** | 61.5% → **19.0%** (TPC −350.0) |
| High-Earner Medicare Surcharge 2pp | −166.503232 | −314.632045 | **−314.632045** | 46.3% → **1.5%** (Treasury −310.0) |
| Progressive Millionaire Tax | −354.634800 | −648.092029 | **−648.092029** | no target — §1.3 |

Dynamic totals moved with them: Warren +98.204033 → **−29.009870**, Medicare surcharge
−0.131447 → **−126.723105**, Progressive Millionaire +52.334960 → **−198.455122**. All three
were positive or nil on the dynamic view before and are negative now, which is the arithmetic of
a static effect that roughly doubled against a debt-service term that did not.

### 6.2 Ask's generic path

| Shape | before | pre-registered | measured |
|---|--:|--:|--:|
| 1pp all brackets | −1,017.211911 | −920.291193 | **−920.291193** |
| 2pp above \$400K | −314.632045 | −166.503232 | **−166.503232** |
| 3pp above \$2M | −283.469479 | −134.612557 | **−134.612557** |

And the prediction recorded in case it was wrong: the capability gate's
`headline_estimate_billions` — the figure the assistant is instructed to quote — **did not move
on any of the three** (−960.0, −310.0, −350.0 before and after). The gate interpolates between
published benchmarks and never reads the engine estimate, so what changed is the
`raw_engine_estimate_billions` beside it, plus the new `income_base` field.

### 6.3 Tailor did not move, and neither did the composer

`2pp above $400K` through the Tailor constructor is **−166.503232 before and after**, to the
cent, with the box on its seeded default. So is the composer path, on all three shapes. The
defect was that Ask silently disagreed with them, and it is Ask that moved.

### 6.4 Zero validation rows moved

| Run | Result |
|---|---|
| `cold_holdout.py --json` | **byte-identical** (`cmp` clean, 119,989 bytes) |
| `run_loo.py --donor-matrix` | **byte-identical** (`cmp` clean) |
| `run_validation_dashboard.py` | identical **but for one line** — the health tripwire, below |
| 52 presets × static/dynamic | rename-blind value multiset differs in **exactly the three pairs of §6.1** |
| `build_validation_headline.py --check` | OK: 75 published of 81, unchanged |

The dashboard's whole diff:

```
9c9
<   model      [        ok]   test_score=-15.7
---
>   model      [        ok]   test_score=-8.3
```

Every scorecard, calibrated, leave-one-out and distributional block is character-for-character
what it was. That is the falsification test §4 named, and it passes.

### 6.5 The collateral, as measured

| Site | pre-registered | measured |
|---|---|---|
| `fiscal_model/health.py` tripwire | −15.7 → −8.3 | **−15.7 → −8.3** |
| `classroom/engine.py` 2.6pp>\$400K | −409.021659 → −216.454201 | **−409.021659 → −216.454201** |
| `bill_tracker/auto_scorer.py` 2pp>\$400K | −314.632045 → −166.503232 | **−314.632045 → −166.503232** |
| `api.py` `/score` custom | no change | **no change** — the Pydantic default was already `True` |
| `api.py` `/score/preset` | moves for §6.1's three only | as expected |
| `validation/core.py` | must not move | **did not** — `cold_holdout` byte-identical |

## 7. Findings the plan did not name

**1. The specialized modules carry the attribute and never read it — 36 of the 52 presets.**
Flipping the dataclass default changed `ordinary_income_base` on every preset policy object that
subclasses `TaxPolicy`, which is 36 of the 52, and **not one of their scores moved**, because
`AMTPolicy`, `EstateTaxPolicy`, `TariffPolicy`, `DrugPricingPolicy` and the rest override the
static-revenue path entirely. The lane's own comparison had to be made rename-blind and
value-based to see this: comparing preset dicts key by key reported 36 "moved" presets whose
figures were identical to the cent. A field 36 policies carry and none reads will make the next
default flip look dangerous and be inert — and the reverse trap is the real one: one day it will
look inert and not be.

**2. `_build_preset_policy`'s rate heuristic cannot express a 1pp preset.** The composer reads
`raw / 100.0 if abs(raw) > 1 else raw`, so a preset declaring `rate_change: 1.0` — one
percentage point, in the units every other preset uses — is scored as a **100-point** rate
change. The lane hit this building its own synthetic comparison, which returned −\$92,029B. No
shipped preset is affected (`0 < |rate_change| <= 1` matches none of the 52), so nothing is
broken today; the heuristic is a latent trap for anyone adding a sub-1pp preset, and `api.py`
carries the identical line. **Carry-over.**

**3. The classroom's Laffer hint was already outside its own tolerance, in both directions.**
`classroom/assignments/laffer_curve.yaml`'s level-3 hint reads "The model score for a 2pp
increase on \$400K+ income is roughly −\$250 to −\$280B ... Try entering ~\$260B", graded
`relative_to_model` on `total_static_cost` at **±2%**. The model's static answer was
**−359.579** before this lane and is **−190.289** after. A student following the hint failed the
check before and fails it after; this lane changed which side of the hint the answer sits on and
did not create the gap. **Not edited**: moving hint prose onto a model number is fitting the
lesson to the output, and it is a content decision with an owner. **Carry-over, owner item.**

**4. The label rule needed a narrower reading than "no dollar figure in the label".** The first
version of the test flagged `🌱 Carbon Tax \$25/ton`, whose "$25/ton" is the policy's own *rate*,
not a claimed score. The rule the plan states is about a claimed ten-year score, which by this
catalog's convention lives in the label's **trailing parenthetical** — "(CBO: \$4.6T)",
"(−\$374B)". The shipped test reads only that suffix, and says so, so `25% Auto Tariff` and both
carbon taxes are not false positives. H6 will want the same narrowing in its own enforcement
test.

**5. Only one of the four struck figures has a document, and it is not close.** §6.2 of the
pre-registration records the search. Three have no published estimate at any dose or scope — and
for High-Income Enforcement the record is sharper than "not found": CBO's *larger* published
dose (\$40B of funding) yields **−\$63B** of deficit against this label's **−\$250B**, so no
rescaling of a published row reaches it. The carbon tax's real CBO/JCT option scores −\$865B on
FY2023–2032 and CRFB's February 2025 re-scoring puts the same design at \$960B on FY2026–2035;
the label said −\$1.0T on neither window. **Registrable by H9, at a figure the label never quoted.**

**6. `preset_ids` had no mechanism for a retired *catalog* label, and its own docstring had
noticed.** `SCORE_ONLY_ALIAS_ID_BY_LABEL` was kept as an empty dict against exactly this need,
but it covers only Build-local score-only ids. `_spellings` folds the score-suffix-**stripped**
form of the current label into the index, which resolves `?preset=Comprehensive Drug Reform` but
not `?preset=💊 Comprehensive Drug Reform (-$600B)` — the form an actual old link carries.
`LEGACY_LABEL_ALIASES` closes it, and `_build_index` now resolves a retired label's id through
its successor rather than generating id-shaped aliases out of a display string. Ten spellings of
the five retired labels are asserted to resolve.

**7. `scripts/smoke_ask_assistant.py` crashes on Windows before printing its summary.** Its
per-scenario token line contains `≈`, which the default `cp1252` console encoding cannot encode,
so the script dies with `UnicodeEncodeError` after the *first* scenario — exit 1 on a run whose
scenarios all passed. `PYTHONIOENCODING=utf-8` is the workaround and produced §9's output. Not
fixed here: `scripts/` belongs to no Wave A lane and the defect is orthogonal. **Carry-over.**

**8. `ruff format --check` fails repo-wide on `main` and is not a CI gate.** 317 files would be
reformatted at the pinned `ruff==0.15.8`, five of them files this lane touched — and all five
would have been reformatted **before** this lane touched them (checked with
`git show HEAD:<path> | ruff format --check`). CI runs `ruff check` only, over
`fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py`, which **passes**. No
formatting was applied, because a 317-file diff is not this lane's to ship. **Carry-over.**

**9. The plan asked for the `repeal_corporate_amt` label rename in this PR, and Wave A's
file-disjointness makes that impossible. The rename is deferred; the sign fix is not.**
The plan's §3 H6 says "*Also fix, in H1's PR*: the `repeal_corporate_amt` label and its
`CBO_SCORE_MAP` sign", and §4 says Wave A lanes must be file-disjoint. For this one preset the
two requirements contradict, because the label **is** a key of H6's
`ui/preset_validation.PRESET_TO_SCORECARD_ID`:

- `tests/test_preset_validation.py::test_every_mapped_preset_exists_in_preset_policies` asserts
  every key of that map is a key of `PRESET_POLICIES`. Renaming the label **fails it**.
- `tests/test_preset_validation.py::test_badge_lookup_is_cached` passes the *old* string
  literal and counts cache hits. Re-keying the map to the new label **fails that one instead**.

So the map and its test have to move in the same commit as the rename, and both are H6's. The
lane's pre-registration had predicted only the second test and predicted it would survive; the
first was missed, and the full suite is what found it — which is the argument for running the
suite before believing a file-ownership boundary holds.

**What shipped instead**: `CBO_SCORE_MAP`'s `official_score` −220.0 → **+220.0**, which is the
load-bearing half (`build_catalog` totals Build packages off it), plus a description saying in
the app that the label's "−$220B" is this app's convention for a *deficit reduction* and is the
opposite of what a repeal does. The label still reads `(-$220B)`. That is a visible
inconsistency for one PR, and it is the better of the two available states: the number people
add up is now right, where before both the label and the number were wrong.
`tests/test_base_rule_contract.py::test_the_repeal_corporate_amt_label_still_disagrees_with_its_own_score`
**asserts the inconsistency**, with a failure message naming the three edits the rename needs —
a to-do with a failing build attached rather than a comment. §10 owner item 1.

**10. Five tests encoded the old default, and two of them were not about the default at all.**
`test_cold_holdout.py::test_ordinary_income_base_flag` and two `test_policies.py` arithmetic
tests asserted the whole-base identity through the *implicit* default, so they now say
`ordinary_income_base=False` explicitly — which is what they always meant, since an arithmetic
test should not depend on a live capital-gains data file. A new companion,
`test_ordinary_income_base_reduces_the_bracket_base`, covers the share they were silently
folding in. The other two are separate findings, 11 and 12.

**11. `DistributionalEngine` does not read `ordinary_income_base` — the same policy object gives
a revenue score and a who-pays table on two different bases, about 2.6x apart.**
`test_distribution.py::test_synthetic_path_tracks_soi_static_for_top_rate` builds one policy and
feeds it to both the distribution engine and the scorer, asserting they track within 2x. The
scorer honours the base and the engine ignores it, so at a \$400,000 threshold the synthetic
table totals \$50.0B/yr against the scorer's \$19.4B/yr — **2.57x**, and the test failed.

Nothing shipped is wrong today: the seven published distributional benchmarks are scored on
their own registered universes, and the dashboard's distributional block is character-identical
before and after this lane, which is itself the proof the engine never read the flag. But a user
reading a revenue score and a who-pays table off one run is reading two bases.

**The band was not widened.** The comparison is now pinned to the base *both* engines
implement, and a new test — `test_the_distribution_engine_does_not_read_the_income_base` —
asserts the divergence **exists**, and fails with instructions when someone closes it. Closing
it moves who-pays tables and so is a lane of its own. **Carry-over.**

**13. The Decision 6 caption was silent on all three presets it exists for, and only rendering
it found that.** `TaxPolicy._ordinary_income_share` short-circuits to `1.0` when
`ordinary_income_base` is `False` — which is exactly the state of every policy this caption
fires for — so the counterfactual came back as "the same number", the `share >= 1.0` guard
tripped and the caption returned `""`. The tests written first did not catch it: they asserted
the *presets* moved, which they had. Calling the module-level `preferential_income_share`
directly fixes it, and the caption now reproduces the pre-registered before-figures from the
scored result alone: **−\$134.6B** at a 52.5% preferential share, **−\$166.5B** at 47.1%,
**−\$354.6B** at 45.3%. Three tests now pin the caption to both figures of each move, one
asserts it stays silent on three presets that did not move, and one asserts it does **not**
claim "its own source uses" for the millionaire surtax, which has no source. **The lesson is
narrow and general: a caption that is computed rather than stored still needs to be rendered
once, because "the number moved" and "the sentence about the number appears" are different
claims.**

**12. The classroom's tolerance boundary was decided by floating point, and this lane's number
move exposed it.** `RelativeValidator` documents `|student − model| / |model| <= tolerance` and
`test_classroom.py::test_relative_validation_tolerance_boundary` asserts that a student exactly
at the tolerance passes. At the new model answer of −166.503231617789, `model × 1.05` round-trips
to a `pct_error` of **0.050000000000000086**, and the student was failed by the sixteenth decimal
place. The old answer happened to round the other way. `classroom/engine.py` now compares against
`tolerance * (1 + 1e-9)`, so the documented boundary is deterministic instead of lucky; the
margin is relative, so it cannot meaningfully widen a large tolerance. **This is a grading
behaviour change in the 🔵 tier, small and deliberate, and it was not pre-registered** — it was
found by the suite and is recorded here rather than folded into the base-rule story.

## 8. Gates

| Gate | Result |
|---|---|
| `ANTHROPIC_API_KEY= python -m pytest tests/ -q -p no:cacheprovider` | §8.1 |
| `python -m ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py` (CI's scope) | **All checks passed** |
| `python -m ruff check .` (repo-wide) | 9 errors, **all pre-existing in `api.py`** (one `F401`, eight `RUF100`), none from this lane, none in CI's scope |
| `python -m ruff format --check .` | fails repo-wide on `main` too — finding 8 |
| `python scripts/check_readiness.py --strict` | exit 2; verdict **`ready_with_warnings`, 6 pass / 4 warn / 0 fail** — §8.2 |
| `python scripts/build_validation_headline.py --check` | **OK**, 75 published of 81 |

### 8.2 What readiness says past the runtime line

Python 3.14 trips `runtime` first and exits 2 locally, which is the trap PR #119 §7.5 recorded.
Read past it: **zero failures**, and all four warnings are pre-existing —
`runtime` (3.14.0 outside `>=3.10,<3.14`), `microdata` (SOI 2023 calibration degraded),
`revenue_scorecard` (a documented Poor outlier) and `holdout_protocol` (`repeal_ptc` and
`pwbm_39_with_stepup`, documented Poor outliers carried since Wave 7). Because
`cold_holdout.py --json` is byte-identical, no scorecard state moved, so none of the three
scorecard-derived warnings can be this lane's.

## 9. The Ask smoke test

A scored number moved and the tool's signature changed, so §3's rule 6 requires re-running
`scripts/smoke_ask_assistant.py` against the live API. **3 of 3 pass, \$0.0317.** The output,
never the key:

```
Model: claude-sonnet-4-6
Knowledge dir: .../fiscal_model/assistant/knowledge
Web search: off

==============================================================================
1. CBO baseline (forces get_cbo_baseline)
==============================================================================
A: Under the loaded baseline[^1]:

- **Cumulative 10-year deficit (2025–2034):** \$29.5 trillion
- **Debt-to-GDP at end of window (2034):** **103.8%**

Both figures reflect the app's CBO baseline before any policy changes are applied.
Tool calls: ['get_cbo_baseline']
Stripped citation markers: []
Tokens: in=1,569 out=157 cache_w=0 cache_r=6,866 | cost ≈ $0.00912 | elapsed 8.6s

==============================================================================
2. Hypothetical scoring (forces score_hypothetical_policy)
==============================================================================
A: Raising the corporate rate from 21% to 25% is estimated to **reduce the deficit by
\$798.4 billion** over FY2025–2034[^1], per this app's calibrated corporate-tax module.
The result is benchmarked against JCT/CBO's scored +1 pp option (\$135.7 billion/pp)[^2]
and interpolated alongside Treasury's 21%→28% score (\$1,347 billion)[^3], with the
module agreeing within ~8%.
Tool calls: ['score_hypothetical_policy']
Stripped citation markers: []
Tokens: in=1,756 out=323 cache_w=0 cache_r=6,866 | cost ≈ $0.01217 | elapsed 8.2s

==============================================================================
3. Knowledge corpus (forces search_knowledge)
==============================================================================
A: The 2025 SSA Trustees Report projects the **OASI trust fund will be depleted in
2033**.[^1] At that point, incoming payroll-tax revenues would cover approximately
**77% of scheduled benefits**.[^1]
Tool calls: ['search_knowledge']
Stripped citation markers: []
Tokens: in=1,871 out=180 cache_w=0 cache_r=6,866 | cost ≈ $0.01037 | elapsed 6.0s

==============================================================================
SUMMARY
==============================================================================
  PASS 1. CBO baseline (forces get_cbo_baseline)  (8.6s, tools: ['get_cbo_baseline'])
  PASS 2. Hypothetical scoring (forces score_hypothetical_policy)  (8.2s, tools: ['score_hypothetical_policy'])
  PASS 3. Knowledge corpus (forces search_knowledge)  (6.0s, tools: ['search_knowledge'])

Total cost across 3 call(s): $0.0317
Session summary: 6 turn(s) · $0.0317 · 26,454 tokens · cache-hit 80%
```

Scenario 2 is a **corporate** hypothetical, which routes to `CorporateTaxPolicy` and therefore
carries no income base — the new `income_base` / `income_base_note` fields are added only for
`policy_type == "income_tax"`, because the corporate module prices profits and a spending path
has no income base at all. The individual-rate case is covered by
`tests/test_base_rule_contract.py::test_ask_states_which_base_produced_the_number`, which
asserts both values of the field and that the two bases do not return one number.

The run also surfaced finding 7: the script needs `PYTHONIOENCODING=utf-8` on Windows or it
exits 1 partway through a passing run.

## 10. Carry-overs and owner items

**Carry-overs**, none blocking and none this lane's to take:

1. `_build_preset_policy`'s `abs(raw) > 1` rate heuristic cannot express a sub-1pp preset; the
   identical line is in `api.py`. Finding 2.
2. `classroom/assignments/laffer_curve.yaml`'s level-3 hint sits outside its own ±2% tolerance,
   and did before this lane. Finding 3 — **owner item**, it is a content decision.
3. `scripts/smoke_ask_assistant.py` crashes on Windows on `≈` before its summary. Finding 7.
4. `ruff format --check` fails on 317 files repo-wide; not a CI gate. Finding 8.
5. The carbon tax's real CBO/JCT option (−\$865B, FY2023–2032) and CRFB's \$960B re-scoring are
   **registrable** — H9's ledger, Wave B.

**Owner items:**

1. **The `repeal_corporate_amt` label rename is owed and is a three-file commit no Wave A lane
   can make alone.** Finding 9. Whoever takes it must, in **one** commit:
   - `fiscal_model/app_data.py` — rename the key in `CBO_SCORE_MAP` and `PRESET_POLICIES` to
     `"⚖️ Repeal Corporate AMT (+$220B)"` and drop the "queued for the same fix" clause from the
     description;
   - `fiscal_model/preset_ids.py` — rename the `PRESET_ID_BY_LABEL` key (the slug
     `amt-repeal-corporate` **does not change**) and add the old spelling to
     `LEGACY_LABEL_ALIASES`;
   - `fiscal_model/ui/preset_validation.py` **and** `tests/test_preset_validation.py` — re-key
     `PRESET_TO_SCORECARD_ID` and update the string literal in `test_badge_lookup_is_cached`;
   - `tests/test_base_rule_contract.py` — delete
     `test_the_repeal_corporate_amt_label_still_disagrees_with_its_own_score`, which fails on
     purpose once the rename lands and whose message says all of the above.

   The natural owner is **H6**, since two of the four files are already its own. A deviation
   from the plan's "in H1's PR" instruction, with the reason measured rather than asserted.
2. **The Build catalog's Repeal Corporate AMT row flips sign**, from a \$220B revenue raiser to a
   \$220B cost. It is a correction, not a model movement, and no Decision 6 caption is owed
   because no *scored* number moved — but it changes what a Build package totals, so the owner
   should know it rides in this PR.
3. **A grading rule moved in the 🔵 tier**, unpre-registered: `classroom/engine.py` now honours
   its own documented "exactly at tolerance passes" boundary instead of leaving it to floating
   point. Finding 12. Small, but it is a change to how student answers are marked.
