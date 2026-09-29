# Fiscal Policy Calculator — Roadmap

> An open-source platform for transparent fiscal policy scoring using CBO methodology, real IRS data, and FRB/US-calibrated dynamic analysis.

*Last reviewed 2026-09-29 (written against `main` @ `0fd8537`). The previous version of this file described
the April 2026 tree; it is in git history. Live accuracy figures come from the commands named below,
never from this page — a figure typed here is a figure that goes stale.*

---

## Which document to read

The planning directory grew one document per round of work. They are not competing plans: each
answers a different question, and exactly one of them is the active plan.

| Document | What it is | Status |
|---|---|---|
| [ROUTE_TO_9.md](ROUTE_TO_9.md) | The 2026-09-22 assessment (7.5/10) and six ranked priorities | **Active plan** |
| [ROUTE_TO_8_5.md](ROUTE_TO_8_5.md) | Sixteen measurable lanes toward "quotable" | Lane sequencing; nine lanes closed, Wave G under way |
| [HIGH_STAKES_ACCURACY.md](HIGH_STAKES_ACCURACY.md) | The numbers a journalist or Hill staffer would quote | Complete — no open lane |
| [MODELING_IMPROVEMENT.md](MODELING_IMPROVEMENT.md) | Waves 1–7: modelling the mechanism, never tuning to held-out targets | Record; §6 is the carry-over list |
| [NEXT_STEPS.md](NEXT_STEPS.md) | The four-tier scorecard and its history | Record; scorecard table is live as of 2026-09-13 |
| [VALIDATION_EXPANSION.md](VALIDATION_EXPANSION.md) | How the out-of-sample tier was built | Record |
| [FEASIBILITY_CHECKLISTS.md](FEASIBILITY_CHECKLISTS.md), [MANUSCRIPT_95_PLUS.md](MANUSCRIPT_95_PLUS.md), [LAUNCH_READINESS.md](LAUNCH_READINESS.md) | Go/no-go gates, the citation-grade path, the April QA pass | Reference |
| [`lanes/`](lanes/), [`memos/`](memos/) | One pre-registration and outturn per lane; one memo per question | Evidence — never edited after the fact |

The rules every one of them binds itself to still apply: pre-register before opening a file, never
retune a constant to a held-out target, report a regression as a regression, and never collapse the
accuracy tiers into one number.

---

## Current state (September 2026)

### What's built

- **52 pre-built proposals** across 13 policy areas, plus a separately named group of 5
  *illustrative, unfitted reconstructions*, and custom tax, spending and tariff scoring paths.
- **CBO-style three-stage scoring**: static + behavioural (ETI) + optional dynamic feedback
  (FRB/US-calibrated), with 14 specialized policy modules.
- **Distributional analysis** on a return-level CPS ASEC microsimulation by default, with CBO's
  household universe where the source ranks households.
- **Baseline** transcribed from CBO's own tables (`US-CBO/cbo-data`, pinned by commit and SHA-256);
  the app's default vintage is February 2026 (publication 61882).
- **IRS SOI** Tables 1.1 and 3.3 for tax years 2021–2023 and Table 1.2 by filing status for 2023.
- **A verb-first multipage app** (Ask · Build · Tailor · Explore · More), frozen classroom
  assignment links, OLG, state modelling (top 10), a bill tracker, and a citation-grounded Ask
  assistant with a hard daily cost cap.
- **A FastAPI service**: `/health`, `/readiness`, `/summary`, `/benchmarks`,
  `/validation/scorecard`, `/presets`, `/score`, `/score/preset`, `/score/tariff`, `/ask`,
  `/ask/stream`.
- **CI**: tests on Python 3.10–3.13 with an 85% coverage gate, ruff, a blocking mypy gate, a strict
  readiness gate, and two blocking accuracy gates on the out-of-sample tier (pooled and per class).

### How accurate it is — and how to read that

Four tiers, reported separately and never collapsed into one "validated within X%" claim:

| Tier | What it measures | Where the live figure comes from |
|---|---|---|
| Out-of-sample, pre-registered (44 rows) | Prediction — the only skill claim | `python scripts/cold_holdout.py` |
| Calibrated, fitted | Bookkeeping; low by construction | `python scripts/run_validation_dashboard.py` |
| Unfitted module reconstructions | Modules against targets nothing was fitted to | the same dashboard, with the retired rows held in place on the line beneath |
| Leave-one-out | How much of the calibration is structure | `python scripts/run_loo.py` |

On 2026-09-28 the out-of-sample tier read **15.2% mean / 12.3% median over 44 rows, 36 within 25%**,
and it is eight policy classes running **4.6% (discretionary spending) to 40.3% (corporate)**.
Accuracy varies by policy family, and a pooled number must always travel with the class results.

### Known gaps, measured

- **Microdata coverage.** Against IRS SOI 2023 the default microdata carries 119% of returns but 81%
  of AGI, and none of the AGI above $10M; the top-tail augmentation that closes most of it is
  opt-in and diagnostic.
- **Distributional universe.** Three of the seven published distributional tables rank households
  but are scored on tax units, because those policies have no microsim mapping.
- **Packages are additive.** Build sums published list prices and says so; the engine sums
  individual scores with one interaction factor. Neither is a joint liability calculation.
- **Corporate** is the worst out-of-sample class: the module reaches about 80.8% of the statutory
  base its receipts path implies, where JCT reaches 53–57%.
- **Two dynamic engines disagree.** The app's dynamic view runs FRB/US-Lite; the API's and Ask's
  dynamic answers run `EconomicModel`, whose supply channel applies a rate change to all of GDP.
  For +2.6 points above $400,000 the two read -$338.9B and -$86.1B. Which to fix is an owner
  decision recorded in ROUTE_TO_9 "Status".

---

## Next priorities

The ranked list is [ROUTE_TO_9.md](ROUTE_TO_9.md) §"Prioritized implementation plan":

1. **Repair correctness and security** — package uncertainty that depended on policy order; API
   keys that became log labels. *Done 2026-09-29, with the API's "unknown" baseline vintage.*
2. **Make current evidence authoritative** — headline metrics generated from one versioned report,
   so the README, the pages, the API and the validation reports cannot disagree. *The report and
   its doc pins landed 2026-09-29 (`scripts/build_current_evidence.py`); see ROUTE_TO_9 "Status".*
3. **Improve the shared modelling core** — calibrate filing populations and upper incomes; one
   tax-unit engine for revenue and distribution.
4. **Score policy interactions explicitly** — ordinary rates, SALT, AMT and credits first.
5. **Demonstrate stronger predictive performance** — fresh locked benchmarks across families, rate
   cuts, vintages and packages; independent methodological review.
6. **Verify the real user experience** — browser journeys against accessibility and latency budgets.

The open modelling lanes from [ROUTE_TO_8_5.md](ROUTE_TO_8_5.md) (R7, R9, R12–R16) sit under
priorities 3–5 and keep their own pre-registration rules.

---

## Architecture vision

```
                    ┌─────────────────┐
                    │   Streamlit UI  │
                    │   + FastAPI     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Policy Engine  │
                    │  (scoring.py)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
     │ Static Score  │ │Behavioral│ │  Dynamic    │
     │ (IRS data)    │ │ (ETI)    │ │ (FRB/US)   │
     └───────────────┘ └──────────┘ └─────────────┘
              │              │              │
     ┌────────▼──────────────▼──────────────▼──────┐
     │              Data Layer                      │
     │  IRS SOI  │  FRED  │  CBO  │  CPS ASEC     │
     └─────────────────────────────────────────────┘
```

The multi-model platform (`models/cbo`, `models/jct`, `models/tpc`, `models/pwbm`, `models/yale`)
is the next major architectural milestone; the CBO-style, TPC-microsim and PWBM-OLG pilots are wired
into the app today and are held to a UX bar, not an accuracy bar. See
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

---

## Contributing

See the [README](../README.md) for setup and [CONTRIBUTING.md](../CONTRIBUTING.md) for the gates a
change must pass (the full test suite with `ANTHROPIC_API_KEY` unset, ruff, the blocking mypy gate
and both accuracy gates). The most useful contributions follow the priorities above, in order.
