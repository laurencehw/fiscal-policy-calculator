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

Both halves are corrected: label → `"⚖️ Repeal Corporate AMT (+$220B)"`, `official_score`
→ `+220.0`.

**Reported to H6, not fixed here:** `preset_validation.PRESET_TO_SCORECARD_ID` is keyed on
the old string `"⚖️ Repeal Corporate AMT (-$220B)"`. H6's own test passes a string literal
and so keeps passing, but the *sidebar* passes the canonical label and will therefore stop
finding the badge until H6 re-keys its map by stable id (`amt-repeal-corporate`). That is
the one key any rename in this lane breaks; the other four presets have no entry in that
map.

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
