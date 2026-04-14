# Feasibility Checklists — CPS Microsim and Multi-Model Comparison

> Repo-grounded go/no-go gates before committing to the two biggest 9.5+ manuscript workstreams

---

## Why this file exists

The repo already contains meaningful starting points for both of the major manuscript upgrades:

- `fiscal_model/microsim/engine.py` already provides a real `MicroTaxCalculator`
- `fiscal_model/microsim/data_builder.py` already contains a CPS-oriented ingestion path
- `fiscal_model/models/base.py` already defines `BaseScoringModel` and `ModelResult`
- `fiscal_model/models/olg/pwbm_model.py` already exposes a PWBM-style OLG adapter

But the same repo also makes clear that neither path is fully production-ready yet:

- `fiscal_model/microsim/data_builder.py` still labels the tax-unit construction logic as a simplified prototype
- `fiscal_model/ui/policy_execution.py` still uses a prototype microsim reform path
- `fiscal_model/ui/tabs/policy_comparison.py` still compares conventional versus dynamic scoring, not independent model families

That means the right next move is not "promise the full feature," but "run the feasibility gate and decide from evidence."

---

## Recommended order

1. Run the CPS ASEC microsimulation feasibility sprint.
2. Run the multi-model comparison feasibility sprint.
3. Write a short go/no-go memo covering both.
4. Only then commit to the full manuscript-grade buildout.

These can overlap, but CPS microsimulation is still the higher-leverage track.

---

## Track A — CPS ASEC Microsimulation Feasibility

### Goal

Decide whether the existing microsim stack can be hardened into a defensible CPS ASEC-backed pipeline for core household tax modules.

### Existing repo anchors

- `fiscal_model/microsim/engine.py`
- `fiscal_model/microsim/data_builder.py`
- `fiscal_model/distribution_engine.py`
- `fiscal_model/ui/policy_execution.py`
- `tests/test_microsim.py`
- `tests/test_microsim_data_builder.py`

### Phase A1 — Audit Sprint (2-3 days)

- [ ] Confirm which CPS ASEC raw files and vintages are actually available locally or in documented acquisition paths.
- [ ] Verify whether `tax_microdata_2024.csv` is reproducible from source data and a committed command.
- [ ] Inventory the exact columns consumed by `MicroTaxCalculator` and identify what is observed, imputed, or missing.
- [ ] Review `data_builder.py` tax-unit construction rules and list where household-level shortcuts break tax-law logic.
- [ ] Validate weight scaling assumptions against CPS ASEC documentation.
- [ ] Compare weighted totals from the current builder to known aggregates: population, wages, AGI-like income, children, filing status.

### Phase A2 — Hardening Spike (1 week)

- [ ] Replace the simplified household grouping with explicit tax-unit construction rules and documented assumptions.
- [ ] Separate ingestion, tax-unit construction, and validation into distinct steps rather than one monolithic script path.
- [ ] Add reproducible validation checks for weighted population, wages, income, and child counts.
- [ ] Wire one interaction-heavy path end to end through the microsim pipeline: `CTC/EITC` or `AMT + SALT`.
- [ ] Compare the microsim output with the current aggregate path on at least one known weak benchmark.
- [ ] Record runtime, memory, and reproducibility constraints for local and CI use.

### Greenlight criteria

- [ ] Raw-to-processed CPS pipeline is reproducible from documented inputs.
- [ ] Tax-unit construction rules are explicit enough to describe in a methods appendix.
- [ ] Weighted aggregates pass basic sanity checks against published totals.
- [ ] Microsim improves or materially clarifies at least one weak benchmark case.
- [ ] Runtime is acceptable for a targeted research workflow, even if not yet ideal for the default UI path.

### Stop or pivot triggers

- [ ] CPS raw-data acquisition is not reproducible enough for reviewers.
- [ ] Tax-unit construction requires a much larger external framework than this repo can realistically absorb.
- [ ] Weighted outputs do not match basic aggregates closely enough to defend the pipeline.
- [ ] Microsim adds complexity but does not improve the weak benchmark cases.

---

## Track B — Multi-Model Comparison Feasibility

### Goal

Decide whether the repo can support a real side-by-side CBO-style, microsim-style, and PWBM-style comparison from a shared policy contract.

### Existing repo anchors

- `fiscal_model/models/base.py`
- `fiscal_model/models/__init__.py`
- `fiscal_model/models/olg/pwbm_model.py`
- `fiscal_model/ui/tabs/policy_comparison.py`
- `fiscal_model/scoring_engine.py`
- `fiscal_model/microsim/engine.py`

### Phase B1 — Audit Sprint (2-3 days)

- [ ] Inventory current model abstractions and confirm which ones already emit standardized results.
- [ ] Check whether `PWBMModel` can be wrapped into the same output contract as `CBOStyleModel`.
- [ ] Identify a minimal shared policy schema that can drive at least one preset policy across all candidate engines.
- [ ] List where the current policy comparison tab assumes one scorer with a `dynamic=True/False` toggle rather than multiple engines.
- [ ] Decide whether the first comparison artifact should be CLI-first, API-first, or dev-only UI-first.

### Phase B2 — Integration Spike (1 week)

- [ ] Keep `CBOStyleModel` as the baseline engine.
- [ ] Build a `TPCMicrosimModel` or equivalent wrapper around `MicroTaxCalculator` and distribution outputs.
- [ ] Build a `PWBMScoringModel` wrapper or adapter so the OLG path emits `ModelResult`-style outputs.
- [ ] Add a simple model registry or comparison service that can execute 2-3 models for one policy.
- [ ] Run at least one preset policy through all candidate models and capture divergences.
- [ ] Write down which outputs are truly comparable and which are model-specific extras.

### Greenlight criteria

- [ ] One policy definition can run across at least two independent engines without hand-editing each model input separately.
- [ ] Outputs can be normalized into a common comparison table.
- [ ] Divergences are explainable in methodology terms rather than appearing as random noise.
- [ ] The comparison service can be demonstrated outside the current static-vs-dynamic tab.

### Stop or pivot triggers

- [ ] Every model requires a different policy schema or one-off translation layer.
- [ ] OLG outputs cannot be normalized into a useful short-run comparison artifact.
- [ ] The microsim and reduced-form models are not comparable enough to support a clear table or figure.
- [ ] UI integration pressure starts driving the architecture before the backend contract is stable.

---

## Cross-Cutting Deliverable — Go/No-Go Memo

### Goal

End the feasibility phase with a short internal memo that says what to build, what not to build, and why.

### Checklist

- [ ] Summarize the current state of CPS microsimulation hardening.
- [ ] Summarize the current state of multi-model comparison hardening.
- [ ] List data, reproducibility, licensing, and performance risks.
- [ ] Estimate effort for a full implementation if greenlit.
- [ ] Narrow manuscript claims to what the repo can honestly support today.
- [ ] Recommend one of: proceed, proceed narrowly, or defer.

---

## Suggested timeline

| Step | Time | Output |
|------|------|--------|
| CPS audit sprint | 2-3 days | Data + architecture assessment |
| CPS hardening spike | ~1 week | Reproducible pilot path + benchmark check |
| Multi-model audit sprint | 2-3 days | Adapter + contract assessment |
| Multi-model integration spike | ~1 week | Two-to-three engine pilot comparison |
| Go/no-go memo | 1-2 days | Build or defer recommendation |

---

## Definition of success

This file is successful if it prevents the repo from making one of two mistakes:

- overcommitting to a large methodological project without verifying the foundations
- underestimating how much existing code can already be reused

If both tracks pass these gates, the project has a credible path toward the core 9.5+ manuscript requirements.
