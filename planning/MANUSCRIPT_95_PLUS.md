# Manuscript 9.5+ Plan

> Practical path from "strong teaching/prototyping tool" to "credible citation-grade research artifact"

---

## Target

Raise the project from roughly `7.8/10` to `9.5+/10` for manuscript readiness by closing the gap between:

- a well-engineered fiscal policy application
- a research artifact that can be cited, reproduced, and defended in a paper

That means improving both the **model** and the **evidence package** around the model.

Before starting the full build, use [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md) to determine whether the existing `microsim/` and `models/` codepaths are strong enough to harden into the manuscript-grade versions described below.

---

## Current strengths

- Strong software foundation: controller-based Streamlit UI, FastAPI separation, large automated test suite, health/status endpoints
- Real policy breadth: dozens of preset proposals across major tax and spending areas
- Solid reduced-form validation: many scenarios already benchmarked within 15% of official scores
- Good teaching value: classroom mode, methodology docs, comparison tabs, OLG module

These are not the limiting factors anymore. The constraint is methodological scope and publication-grade documentation.

---

## What still blocks a 9.5+

### 1. CPS ASEC microsimulation is missing

This is the highest-leverage gap. The current system still relies on bracket aggregates and synthetic tax units for many distributional and interaction-heavy questions.

Why it matters:

- AMT x SALT x CTC x filing-status interactions need return-level heterogeneity
- distribution tables are much harder to defend without microdata
- manuscript reviewers will treat "microsimulation" claims cautiously until the data source is explicit

### 2. No real multi-model comparison yet

The current app compares conventional versus dynamic scoring, but not independent model families.

Why it matters:

- papers need robustness, not just a single preferred model
- side-by-side CBO-style vs TPC-style vs PWBM-inspired outputs make model disagreement legible
- divergences can become part of the manuscript's contribution rather than a weakness

### 3. Distributional validation is too narrow

Current validation leans mainly on published TPC tables rather than a broader CBO-style distributional benchmark set.

Why it matters:

- distribution claims are often the first thing policy readers challenge
- validation needs to extend beyond aggregate revenue accuracy

### 4. Some higher-error cases are not yet fully explained

The payroll donut-hole and Biden CTC cases are still prominent weak spots.

Why it matters:

- a paper can tolerate imperfect fit
- it cannot tolerate unexplained fit

### 5. Documentation is not yet a manuscript package

The repo has methodology and validation docs, but not yet the materials a reviewer expects to see bundled clearly.

Missing pieces:

- methods note or working paper appendix
- explicit limitations appendix
- reproducibility instructions tied to exact data vintages
- validation uncertainty bands and not just point errors

---

## 9.5+ acceptance criteria

The project should claim "citation-grade" only after all of the following are true:

1. **CPS ASEC-backed microsimulation exists** for income tax, CTC, EITC, AMT, SALT, and filing-status interactions.
2. **At least two independent scoring engines** can run the same policy side by side from a common interface.
3. **Distributional validation includes broader benchmarks** than TPC alone, ideally including CBO-style tables where available.
4. **High-error scenarios have written explanations** and, where feasible, improved calibration.
5. **Data freshness is explicit and reproducible** in the UI, API, docs, and manuscript appendix.
6. **The repo ships a manuscript evidence package**: methods, limitations, validation appendix, and reproduction instructions.

---

## The epistemic spine: calibrated vs predicted

The project's signature methodological contribution — and the argumentative spine of the manuscript — is the rigid separation of two epistemically different validation tiers. This is not a nicety; it is what distinguishes an honest model from a calibrated spreadsheet, and referees will read it as such.

### The two tiers

- **Tier 2 — Calibrated reference models** (~5% mean abs error across 29 benchmarks; live 4.4%): specialized modules (TCJA, corporate, estate, credits, AMT, payroll, PTC, capital gains, expenditures) whose parameters are tuned so their components reproduce the published CBO/JCT/Treasury decomposition. The low error is **expected by construction**. These are auditable, source-linked *reconstructions* of official scores. They demonstrate the model's *structure* is consistent with the official scoring methodology. They are **not** evidence the model would have predicted those scores cold.

- **Tier 1 — Out-of-sample predictions** (~8% mean, 4/4 within 15%; live `scripts/cold_holdout.py`): the "Generic" path. Policies scored purely bottom-up from IRS SOI filer counts and incomes via raw rate/threshold auto-population, with **no fitting to the official target**. This is the only tier that measures genuine predictive accuracy.

The manuscript must report these **separately and never collapse them** into a single "validated within X%" claim. Conflating them overstates predictive power: the Tier 2 number describes how well the model reproduces scores it was tuned to; the Tier 1 number describes how well it predicts scores it never saw.

### Why the distinction matters: a worked example

The forensic value of maintaining two tiers became concrete during this work. Tier 1 had long shown ~19% mean error (2/4 within 15%), with the residual "concentrated on high-threshold TPC cases (~30%)." The project's own diagnostic — `cold_holdout.py --ordinary-base`, which applies a *uniform* (not per-case) exclusion of preferential capital gains from the rate base — revealed the structure:

| Policy | Official | Full base | Ordinary base | Error full→ordinary |
|--------|---------:|----------:|-------------:|---------------------:|
| 1pp all brackets | -$960B | -$1,017B | -$935B | 6% → 3% (improves) |
| Biden $400K+ | -$252B | -$409B | -$284B | 62% → 13% (improves) |
| 5pp top ($1M+) | -$700B | -$648B | -$491B | 7% → 30% (**worsens**) |
| 2pp cut ($500K+) | +$400B | +$364B | +$278B | 9% → 30% (**worsens**) |

The cases the uniform correction **worsens** are AGI-inclusive (TPC scores top-rate changes on taxable income including the preferential LTCG/QDIV portion); the cases it **improves** are ordinary-bracket changes. The correction's own note — *"AGI-inclusive surtaxes should NOT use it (cap gains are in their base)"* — states the tell. The two TPC cases were mislabeled `agi_inclusive_base=False`, so they wrongly received the ordinary-base correction, inflating their "predicted" error from ~8% to 30%.

The fix is a **classification correction**, not calibration: setting `agi_inclusive_base=True` on the two AGI-inclusive cases lets the Generic scorer apply the correct *uniform* bottom-up computation (full SOI base, no target fitting). Result: Tier 1 mean drops 19% → 8%, 4/4 within 15%. This is an *improvement in honesty* — the prior 19% was inflated by a labeling bug — not a retroactive polish of a flattering number.

This episode is the manuscript's argument for the two-tier split: had we reported a single collapsed number, the base mislabeling would have been invisible inside the average; maintaining a *genuinely out-of-sample* tier forced the residual to be diagnosed rather than absorbed.

### Anti-overfitting machinery

- **Locked post-change holdout protocol** (`fiscal_model/validation/holdout.py`, `revenue-scorecard-post-lock-2026-05-02`): a frozen subset of specialized benchmarks reserved as regression checkpoints. It prevents future changes from quietly overfitting to every benchmark. It is *not* a claim that the current historical estimates were developed without seeing these targets — rotate that caveat into the manuscript so a referee does not mistake a regression holdout for a prospective one.
- **CI guardrail**: `python scripts/cold_holdout.py --max-mean-error <N>` fails the build if the out-of-sample mean abs error drifts past a budget, locking the honest number against regressions.
- **Integrity invariant in tests**: `tests/test_cold_holdout.py::test_out_of_sample_tier_is_genuinely_uncalibrated` asserts `oos["mean_abs_error"] > cal["mean_abs_error"]`; if the tiers ever converge, the framing is no longer honest (the "calibrated" set has leaked into the holdout, or vice versa).

### Manuscript framing for the spine

1. **State both numbers live**, with the reproduction command, in the abstract and the validation section. Do not round 4.4% *up* to 5% in the abstract and *down* to 4% in the body — pick one and be consistent.
2. **Use the base-classification episode as a worked example of the diagnostic discipline** the two-tier split enables. It is more persuasive than any aggregate accuracy claim.
3. **Distinguish "calibrated reconstruction" from "independent confirmation" in every scoring tier description.** The 3-tier maturity table (validated / calibrated / exploratory) already codifies this; the manuscript should inherit the vocabulary directly.
4. **Foreground the locked holdout as a commitment device**, with the explicit caveat that it is a post-lock regression check, not retroactive out-of-sample proof.
5. **Report residual error with a source, not just a magnitude**: "the remaining ~8% is dominated by the Biden $400K bundled estimate (a 'combined with other provisions' Treasury figure) and top-income SOI detail limits" — not a bare "8%."

---

## Feasibility gate before full buildout

The repo is beyond pure greenfield planning: there is already a `MicroTaxCalculator`, a CPS-oriented builder, a `BaseScoringModel`, and a PWBM-style OLG adapter. But those pieces are not yet enough to claim either CPS-backed microsimulation or a true multi-model platform.

That means the immediate next move should be:

1. run the CPS feasibility checklist
2. run the multi-model feasibility checklist
3. write a short go/no-go memo

See [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md) for the concrete steps and decision criteria.

---

## Recommended workstreams

### Workstream A: CPS ASEC microsimulation

Scope:

- ingest CPS ASEC microdata
- build taxpayer unit construction and weighting pipeline
- migrate income tax, CTC, EITC, SALT, AMT, and payroll interactions
- preserve current synthetic path only as a fallback or teaching mode

Deliverables:

- `fiscal_model/microsim/` pipeline with documented data preparation
- weighted distribution tables
- regression tests against known benchmark scenarios
- clear statement of what is CPS-based versus still aggregate

Definition of done:

- manuscript can say "distributional estimates are produced from CPS ASEC microdata" without qualification for core tax modules
- first milestone before full build: pass the CPS feasibility gate in [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md)

### Workstream B: Multi-model comparison

Scope:

- define a shared model interface
- implement at least:
  - current CBO-style reduced-form engine
  - TPC-style microsim engine
  - PWBM-inspired long-run or dynamic comparison path
- expose divergences in both API and UI

Deliverables:

- common model registry / adapter layer
- side-by-side comparison tables and charts
- documentation for why model outputs differ

Definition of done:

- manuscript can show one policy scored under multiple model families in a single figure or table
- first milestone before full build: pass the multi-model feasibility gate in [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md)

### Workstream C: Validation deepening

Scope:

- broaden distributional benchmarks
- add validation notes for high-error scenarios
- report error intervals and benchmark provenance

Deliverables:

- updated `docs/VALIDATION.md`
- per-scenario notes with official source, policy year, data year, error, and explanation
- explicit "known weak cases" section

Definition of done:

- reviewers can tell which parts are strongest, which are weaker, and why

### Workstream D: Manuscript package

Scope:

- turn repo docs into a paper-ready evidence bundle

Deliverables:

- `docs/METHODS_PAPER.md` or manuscript appendix draft
- `docs/LIMITATIONS.md`
- reproducibility section with:
  - Python version
  - lockfile workflow
  - data vintages
  - exact commands for regeneration
- validation appendix with both aggregate and distributional tables

Definition of done:

- a reader can reproduce the main tables and understand the model limits without reverse-engineering the code

---

## Highest-return near-term upgrades

If time is limited, these are the best next improvements:

1. **CPS ASEC microsimulation for core tax modules**
2. **Two-engine side-by-side comparison**
3. **CBO-style distributional benchmarking**
4. **Methods + limitations appendix**
5. **Validation uncertainty reporting**

Everything else is secondary to those five for manuscript quality.

---

## Improvements that help, but do not move the manuscript enough on their own

- additional preset policies
- more UI polish
- more classroom content
- more deployment automation
- marginal increases in unit-test count

These are valuable product improvements, but they do not by themselves close the citation-grade gap.

---

## Suggested sequence

### Phase 0: feasibility gate

- audit the current `microsim/` and `models/` foundations
- run the CPS and multi-model spikes in [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md)
- write a short go/no-go memo before committing to the full build

### Phase 1: credibility cleanup

- finish data freshness automation and vintage surfacing
- harden validation notes for known weak cases
- clean repo/docs so shipped versus planned features are clearly separated

### Phase 2: methodological leap

- implement CPS ASEC microsimulation for core individual tax modules
- revalidate aggregate and distributional outputs

### Phase 3: robustness layer

- build multi-model comparison interface
- produce side-by-side tables for key policies

### Phase 4: manuscript package

- methods paper
- limitations appendix
- reproducibility appendix
- polished validation appendix

---

## Paper-facing evidence checklist

Before submitting or circulating a manuscript built on this repo, make sure the repo can answer:

- What data vintage was used?
- Which outputs come from CPS microdata versus aggregates?
- Which model family produced each table?
- How large are the known errors on benchmark policies?
- Which scenarios are least reliable?
- How can a reviewer reproduce the exact results?

If any of those answers are vague, the manuscript is not yet at 9.5+.
