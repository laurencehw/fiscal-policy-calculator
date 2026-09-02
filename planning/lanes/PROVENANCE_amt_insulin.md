# Provenance lane — the AMT and insulin targets

*Opened 2026-09-02 on `provenance/amt-insulin-targets`, branched from `main`
@ `dff096d`. Work under `planning/MODELING_IMPROVEMENT.md` §1.6 ("target
problems go to the other lane") and Phase E's supersede rule. **No modelling
change**: no constant was retuned, no mechanism altered, no CI threshold
touched.*

Three targets were referred here by two modelling lanes. Lane L5 (`amt.py`)
found that its best result — the structural path landing twice as close to the
document as the fitted constant — could only be *stated*, not scored, because
the target the repository carried disagreed with the document. Lane L7
(`pharma.py`) fixed an incidence bug and was rewarded with a *worse* percentage,
because the benchmark it was scored against pointed the opposite way. Both are
target problems, and this lane is where they get resolved.

## 1. What each target was, and what it is now

| Benchmark | Was | Is | Document row it was read from |
|---|---:|---:|---|
| `extend_tcja_amt` | **$450.0B** | **$1,357.1B** | CRS **R48286**, Table 1, *"Revenue Costs of Extending the TCJA: Major Provisions (Billions of Dollars)"*, transcribing CBO pub. 60114/60271 — row **"Increased Alternative Minimum Tax Exemption"**, FY2025–FY2034 column. The adjacent FY2025–FY2029 column prints **$466.2B**. |
| `universal_insulin_cap` | **−$15.0B** (a saving) | **+$11.4B** (a cost) | CBO pub. **57957**, *Estimated Budgetary Effects of H.R. 6833, the Affordable Insulin Now Act*, table p. 1 — **"Secs. 2 and 3, Cost-Sharing for Certain Insulin Products"**: estimated outlays **6,566**, revenues **−4,793**, FY2022–2031. $6.566B + $4.793B = **$11.359B** of added deficit. |
| `repeal_individual_amt` | **$450.0B** | **$450.0B — not moved** | *Nothing to move it to.* See §3. |

Both moves went through a new ledger, `fiscal_model/validation/target_revisions.py`,
which mirrors `preregistered.py`'s rule for Tier 1: the old figure stays in the
file as a row marked `superseded_by`, the new row carries document/table/row/
page/date and a reason, and `target_revision_problems()` fails if the ledger and
the registries the app actually reads ever disagree. Entered in `2a341d8`,
first scored in `d628892` — the two-commit protocol, so "the target moved before
the model was allowed to see it" is checkable from `git log` rather than
asserted here.

### Why $450B was wrong, and what kind of wrong

Not a rounding difference. **$450B is 3.5% from the published *five*-year cost
and 66.8% from the ten-year one** — a five-year figure sitting in a ten-year
column. The ten-year figure is corroborated twice, independently of CRS:

- **JCT, JCX-35-25** scores P.L. 119-21's AMT-exemption provision at
  **$1,362.810B** over FY2025-2034 — 0.4% away, and already carried in this
  repository as the `pl119_21_amt_exemption` benchmark, which means the two
  numbers were sitting 200% apart inside the same scorecard.
- The **Bipartisan Policy Center**'s 2025 tax-debate explainer, citing JCT:
  *"Extending the TCJA's individual AMT changes would reduce revenues by nearly
  $1.4 trillion from FY2025 through FY2034."*

Definitional caveat, stated rather than split: CRS/CBO score the AMT provision
*inside* a full TCJA-extension package, where extended rate cuts push more
filers into AMT. TPC's T25-0049 reconstructs the **standalone** post-sunset
counterfactual and implies about $855B. Both are published and they answer
different questions; the package figure is the one this benchmark's own
description asks for, and it is the only one of the two that is a *scored
provision* rather than a baseline projection.

### Why −$15B was wrong

A $35 monthly insulin cap is a **cost-sharing** cap. It moves a patient's
liability onto the plan and onto the federal subsidy for that plan, so it adds
to the deficit. CBO's own table says so. −$15B is traceable to no CBO document,
and it made `universal_insulin_cap` the repository's only benchmark that
disagreed with its own model about what a policy *does*.
(cbo.gov returns HTTP 403 to non-browser clients; the table is corroborated by
InsideHealthPolicy, *"CBO: Insulin Cost Cap Hikes Spending $6.6B, Lowers
Revenues $4.8B"*, 31 March 2022.)

`KNOWN_TARGET_SIGN_INVERSIONS` in `tests/test_validation_runners.py` is now an
**empty set**, and the emptiness is the assertion.

## 2. Decision 1 — reported vs derived, against the corrected targets

`python -c` over `validate_amt_policy(case, mode=...)`, live targets:

| Benchmark | Target | Reported (fitted) | Err | Derived (structural) | Err | Winner |
|---|---:|---:|---:|---:|---:|---|
| `extend_tcja_amt` | $1,357.1B | $450.5B | **−66.80%** | **$855.3B** | **−36.97%** | derived |
| `repeal_individual_amt` | $450.0B | $450.5B | +0.12% | $948.9B | +110.87% | reported |
| `repeal_corporate_amt` | $220.0B | $220.1B | +0.05% | $252.2B | +14.64% | reported |
| **Mean abs** | | | **22.32%** | | **54.16%** | reported |

**Outcome: `AMT_APP_MODE` stays `reported`.** Decision 1's own rule is that a
module stays on `reported` until its derived error beats its fitted error, and
it does not. **No shipped number changes**, so no user-visible note is needed —
the Decision 6 obligation (a number change ships with its explanation) is not
triggered here.

Read the two losing rows before treating that mean as evidence for the fitted
path. Both are targets a constant was fitted to, so their ~0% is bookkeeping;
`repeal_corporate_amt`'s derived path is the flat $22B/yr base that `loo.py`'s
leakage guard already flags. **The one AMT benchmark whose target no constant
was fitted to is the one derived wins**, by a factor of 1.8. That is L5's claim,
now measured rather than asserted.

`AMT_SCORECARD_MODE` also stays `reported`, and its blocker has changed
character: it used to be "the target has not been checked", and is now
"`repeal_individual_amt`'s target does not exist" (§3).

## 3. `repeal_individual_amt` — the target that could not be corrected

Searched again, on top of Phase E's recorded search: TPC publishes no
"repeal the individual AMT" model estimate at any date; JCT and CBO publish no
post-2025 repeal score; the BPC explainer that quotes JCT's $1.4T for
*extending* the exemption and $637B for TCJA's original AMT change carries no
repeal figure. The nearest primary figure remains **JCX-46-17** (2 Nov 2017)
p. 3, *"G. Repeal of Alternative Minimum Tax on Individuals … −695.5"* over
FY2018-2027 — a *pre-TCJA* baseline and a different decade.

The one published quantity that fits the policy is **TPC T25-0049's AMT-revenue
column, $948.9B over 2026-2035**, on exactly this baseline. It is deliberately
**not adopted**, for two independent reasons:

1. **It is a baseline projection, not a scored repeal.** That is the same rule
   `benchmark_sources.py` already applies to `repeal_ptc`, where JCX-48-24's
   exchange-subsidy projection was rejected as a stand-in.
2. **It is `amt.py`'s own input.** The derived path reads that CSV and
   reproduces the column year for year (L5 finding 4), so adopting it as the
   target would manufacture a 0% row out of precisely the leakage pattern
   `loo.py` guards against.

Two things the owner should still weigh, recorded in the provenance record
rather than acted on: $450B is traceable to nothing, and it is **internally
incoherent** with the transcribed $1,357.1B — a *full repeal* cannot cost less
than merely extending the exemption on the same baseline.

## 4. The readiness gate

`repeal_individual_amt` is a locked id in `holdout.py`'s
`revenue-scorecard-post-lock-2026-05-02` protocol, and `readiness.py`
hard-**fails** strict readiness on any holdout entry rated Poor. Moving its
target to $948.9B would rate it Poor under `reported` (52.5%) and would rate it
Excellent under `derived` — but only because model and target would then be the
same file.

The task's option (a) — re-register the protocol lock for the superseded target
— is not available: `holdout.py` has **no re-registration path**. `HoldoutProtocol`
is a single frozen manifest with one `protocol_id` and one `locked_at`, and
adding a path would be editing the gate, which §4 forbids. So **option (b)
applies**: the entry stays scored on `reported` against its locked target, with
the derived number ($948.9B, +110.9%) recorded beside it here, in
`benchmark_sources.py` and in `AMT_SCORECARD_MODE`'s docstring. Nothing was
deleted and no threshold moved.

`scripts/check_readiness.py --strict` exits **2** (`ready_with_warnings`),
**unchanged from the base commit**. `holdout_protocol` still passes.

One thing that needed care to keep it that way, and it is a semantic correction
rather than a gate relaxation. `readiness.py` treats a documented `Poor` on a
**fitted** calibrated benchmark as strict-blocking, because "those parameters
exist to reproduce that target, so drifting to Poor is a genuine regression".
After a revision that sentence is false: the AMT constant reproduces the
*superseded* $450B and was never fitted to $1,357.1B. `scorecard.py` therefore
derives `calibrated_to_target` from the ledger, so a revised row reports in the
unfitted-reconstruction tier where a miss is a finding. Measured both ways on
this branch:

| | strict issues |
|---|---|
| As shipped (`calibrated_to_target` derived) | `runtime` only — the Python 3.14 version warning |
| Counterfactual (row held in the fitted tier) | `runtime` **and** `revenue_scorecard` |

On Python 3.14 the exit code is 2 either way, because the runtime warning
already trips it; on CI's supported Python the derivation is what keeps the
scorecard check out of the strict set. Retuning the constant to close the 66.8%
would also have turned it green, and that is the move this lane is forbidden to
make.

## 5. Fitted-tier honesty (for the coordinator's headline)

Correcting a target the constants were fitted to converts a 0% row into a real
miss. Both readings, from `cached_default_scorecard()` on this branch:

| Reading | n | Mean | Median | Within 15% | Off by >15% |
|---|--:|--:|--:|--:|---|
| Base commit `dff096d` | 34 | **2.73%** | 0.21% | 33/34 | `cbo_2pp_all_brackets` (19.2%) |
| **As reported** — revised row moved to the reconstruction tier | **33** | **2.81%** | 0.31% | **32/33** | `cbo_2pp_all_brackets` (19.2%) |
| **Held in place** — revised row kept in the fitted tier | 34 | **4.69%** | 0.33% | 32/34 | `cbo_2pp_all_brackets` (19.2%), **`extend_tcja_amt` (66.8%)** |

Quote whichever fits the sentence, but **never one without the other**: the
"33 at 2.8%" is only honest next to the statement that a 34th row was moved out
because its target changed, and `ScorecardSummary.revised_target_entries` (= 2)
is on the scorecard so the move can never be silent.

Only `extend_tcja_amt` changes tier. `universal_insulin_cap` was already
`calibrated_to_target=False`, so its improvement lands entirely inside the
reconstruction tier.

## 6. Everything else that moved, and everything that did not

| Tier | Base `dff096d` | This branch |
|---|---|---|
| **Tier 1 — out-of-sample** | 25 cases, **34.4%** mean, 12/25 within 15%, 16/25 within 25% | **identical** |
| Tier 2 — fitted calibrated | 34 @ 2.73% | 33 @ 2.81% (see §5) |
| Tier 2 — unfitted reconstructions | 20 @ 82.60% | **21 @ 76.73%** |
| Tier 2 — leave-one-out | 18 @ 61.7% mean / 35.6% median / 6-of-18 | **18 @ 58.7% / 32.5% / 6-of-18** |
| Calibrated provenance | 17 `line_item` / 15 `line_item_differs` / 15 `secondhand` / 7 `model_estimate` | **19 / 13 / 15 / 7** |
| Sectoral rows disagreeing with their target on **sign** | 1 | **0** |

Tier 1 is untouched by construction — no pre-registered case runs `AMTPolicy`
or `PharmaPolicy` — and `tests/test_target_revisions.py` asserts both that no
Generic entry carries a revision and that no revised id appears in
`PREREGISTERED_CASES`.

The **LOO** movement is a target movement, not a model movement:
`extend_tcja_amt`'s held-out derivation is unchanged at $855.3B and its error
against the corrected target is −37.0% instead of +90.1%. AMT module LOO mean
100.5% → **73.9%**; suite 61.7% → 58.7%, still under the 75% ceiling. No donor
matrix entry moved.

Per-benchmark, on the two rows this lane touched:

| Benchmark | Model (unchanged) | Err vs old target | Err vs new target |
|---|---:|---:|---:|
| `extend_tcja_amt` (reported) | $450.5B | +0.1% | **−66.8%** |
| `extend_tcja_amt` (derived) | $855.3B | +90.1% | **−37.0%** |
| `universal_insulin_cap` | +$7.0B | 146.4%, **directions disagree** | **−39.0%, directions agree** |

## 7. Blast radius outside validation

Preset labels embed the official figure, so both moved with their `preset_ids`
twin (the slugs — `amt-extend-tcja-relief`, `insulin-cap-universal` — are
unchanged, so no share link breaks):

- `⚖️ AMT: Extend TCJA Relief ($450B)` → `⚖️ AMT: Extend TCJA Relief ($1.36T)`
- `💊 Universal Insulin Cap (-$15B)` → `💊 Universal Insulin Cap ($11B)`

Touched together: `app_data.py` (`CBO_SCORE_MAP` × 2, `PRESET_POLICIES` × 2,
including the two user-facing descriptions that quoted the old figures),
`preset_ids.py`, `policy_status.py`, `ui/preset_validation.py`,
`validation/scenarios.py`. `tests/test_target_revisions.py` pins that the new
spellings resolve and the old ones are gone everywhere.

`/validation/scorecard` and the Validation tab now say **which** figure is the
target: `target_revision_id`, `superseded_10yr_billions`,
`target_revision_reason` per entry, `revised_target_entries` on the summary, a
"Target moved from" column in the tab and a clause in its caption.

## 8. Left undone, deliberately

- **`repeal_individual_amt` keeps an unsourced, internally incoherent target.**
  §3 says why moving it is worse than leaving it. Closing it needs either a
  published score that does not currently exist, or an owner decision to
  re-register the locked holdout protocol — a change to `holdout.py` that this
  lane is not permitted to make.
- **`repeal_corporate_amt` was checked and not revised.** Its transcription
  (JCX-18-22, $222,248M) is 1.0% from the carried $220B, inside
  `CONFIRMATION_TOLERANCE_PCT`. Already `line_item`; nothing to do.
- **The other 13 `line_item_differs` rows are untouched.** Each needs the same
  per-target judgement this lane applied to three of them, and several (both
  Social Security payroll targets, `repeal_ira_credits`) have no published
  figure to move to at all.
- **`docs/`, `README.md`, `CLAUDE.md`, `planning/MODELING_IMPROVEMENT.md`,
  `planning/NEXT_STEPS.md` and `docs/CHANGELOG.md` are owned by the concurrent
  `docs/wave1-sync` lane** and were not touched. Two figures there will need
  that lane's attention: the fitted-tier headline (§5), and a pre-existing
  drift — `CLAUDE.md` states Tier 1 at "52.6% mean, 8/25 within 15%, 14/25
  within 25%", while `main` @ `dff096d` already produces **34.4%, 12/25, 16/25**.
  That drift is not from this branch; it was there at the branch point.
