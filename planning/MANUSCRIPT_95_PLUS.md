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
