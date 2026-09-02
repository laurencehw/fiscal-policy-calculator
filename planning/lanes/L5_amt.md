# Lane L5 — AMT: a live exemption path and a 2026 sunset ramp

*Pre-registered 2026-09-01 against `main` @ `cff6b88`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §3 L5, under §4's rules and owner
Decision 1 (reported vs derived mode, accepted 2026-09-01).

## 1. Starting numbers

All from the branch point, `python scripts/run_loo.py --donor-matrix` and
`python scripts/cold_holdout.py` on `cff6b88`.

### Leave-one-out (the lane's yardstick)

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| AMT | `extend_tcja_amt` | 450.0 | 450.5 | 779.5 | **+73.2%** |
| AMT | `repeal_individual_amt` | 450.0 | 450.5 | 836.9 | **+86.0%** |
| AMT | `repeal_corporate_amt` | 220.0 | 220.1 | — | not cross-validatable |

AMT module mean 79.6% (n=2 derivable, 1 excluded by the leakage guard).
**Suite aggregate: 59.3% mean / 35.6% median over 18 derivable cases, 6/18
within 15%, 4 not cross-validatable.**

### Fitted (by-construction) errors for the same three benchmarks

| Benchmark | Target | Fitted model | Fitted err |
|---|--:|--:|--:|
| `extend_tcja_amt` | $450B | $450.5B | **0.1%** |
| `repeal_individual_amt` | $450B | $450.5B | **0.1%** |
| `repeal_corporate_amt` | $220B | $220.1B | **0.0%** |

### Battery aggregates

- Tier 1 (out-of-sample): **25 cases, 52.6% mean, 8/25 within 15%, 14/25 within 25%.**
- Calibrated fitted tier: **34 policies, 2.7% mean, 33/34 within 15%.**
- Unfitted module reconstructions: **20 policies, 250.8% mean, 4/20 within 15%.**

## 2. What the lane changes

Two defects named in §3 L5, both in `fiscal_model/amt.py`.

1. **The exemption-change branch is dead.** `estimate_static_revenue_effect`
   computes `baseline_taxpayers` and `policy_taxpayers` from the *same* call
   (`amt.py:357, 360`), so the branch always returns 0.0 and the three
   expressions above it (`:349-359`) are evaluated and discarded. Fix: baseline
   count from the current-law schedule, policy count from the reform schedule.
2. **No ramp / no year index.** The identity delivers one steady-state
   post-sunset level (~$73B/yr, matching `revenue_post_tcja_2030 = 75.0`,
   `amt.py:119`) for every year of the window. Fix: a year-indexed
   affected-payer and average-liability path, sourced and transcribed under
   `fiscal_model/data_files/`.

Plus owner Decision 1: an `AMTPolicy.mode` of `reported` (fitted annual) or
`derived` (structural path). Derived becomes the default in the validation
entry point; the app's presets stay on `reported` unless derived beats fitted.

## 3. The prediction

**Headline: I expect both individual-AMT rows to move *away* from the carried
target, not toward it, and I am pre-registering that rather than tuning to
avoid it.**

§3 L5 hypothesised that the missing 2026 ramp biases the derivation high and
that phasing it in "would close most of this". The published data contradicts
the hypothesis before a line of code is written. TPC's T25-0049 (April 2025,
baseline = law in place as of 1 January 2025, i.e. with the TCJA sunset still
in law) shows the sunset as a **cliff, not a ramp** — AMT payers go 0.2M in
2025 to 7.6M in 2026 — and the post-sunset path then *grows*, from $71.6B in
2026 to $124.2B in 2035. The module's steady-state $73B/yr is therefore the
window's **early-year** level, not its average. A correctly year-indexed path
scores *higher* than the flat one, not lower.

The reason the rows cannot come down is a target problem the repository has
already documented and this lane is forbidden to fix (§1.6, §4):
`fiscal_model/validation/benchmark_sources.py` records `extend_tcja_amt`'s
published line item as **$1,357.1B** (CRS R48286 Table 1, transcribing CBO
pub. 60114) with the note that the *five*-year figure is $466.2B — "the carried
target looks like a five-year number sitting in a ten-year column" — and
records for `repeal_individual_amt` that "$450B looks low on its face".

### Rows I expect to move, and how far

| Row | Now | Predicted | Direction |
|---|--:|--:|---|
| LOO `extend_tcja_amt` | +73.2% | **+85% to +95%** | worse vs the carried target |
| LOO `repeal_individual_amt` | +86.0% | **+105% to +115%** | worse vs the carried target |
| LOO suite mean (n=18) | 59.3% | **61% to 63%** | worse by ~2pp |
| Fitted `extend_tcja_amt` | 0.1% | **~90%** | derived replaces the fitted constant in validation |
| Fitted `repeal_individual_amt` | 0.1% | **~110%** | same |
| Fitted `repeal_corporate_amt` | 0.0% | **~15%** | same; no year data exists for CAMT, so derived = the flat $22B/yr base |
| Fitted tier mean (n=34) | 2.7% | **~9%** | 33/34 to ~30/34 within 15% |

Point predictions from the arithmetic, before the code exists: the derived
10-year cost of extending TCJA AMT relief is **~$860B** (TPC's post-sunset path
2026-2035 sums to $948.9B; the TCJA-regime counterfactual, TPC's 0.2M payers at
their own $29,740 per payer grown at the table's 2024-to-2025 rate, sums to
~$87B), and derived full repeal from 2026 is **~$949B**.

### The number that should improve

Against the **published line item** rather than the carried target,
`extend_tcja_amt` goes from **-66.8%** (fitted $450.5B vs $1,357.1B) to about
**-37%** (derived ~$860B vs $1,357.1B). That is the claim this lane is actually
making: the structural path lands roughly twice as close to the document as the
fitted constant does, and the fitted constant only looks good because it
reproduces a target its own provenance record says is wrong.

Definitional caveat, stated up front: CRS/CBO's $1,357.1B is scored inside a
full TCJA-extension package, where extended rate cuts push far more filers into
AMT; TPC's path is a standalone current-law sunset. They are different
counterfactuals, both published, and the derived model reconstructs TPC's.

### Rows I expect NOT to move

- **No Tier 1 row.** No pre-registered out-of-sample case runs `AMTPolicy`.
  Tier 1 should stay at 52.6% / 8 / 14 exactly.
- **No unfitted-reconstruction row.** `pl119_21_amt_exemption` is scored by the
  TCJA module (`create_tcja_extension(extend_amt=True)`), not by `AMTPolicy`;
  the 20-case reconstruction mean should stay at 250.8% exactly.
- **No other LOO module.** Payroll, Estate, Credits, Expenditures and Capital
  Gains share no code with `amt.py`.
- **App preset output.** The app default stays `reported`, so every shipped AMT
  preset scores exactly what it scores today, including the
  `create_repeal_corporate_amt()` regression band [210, 232].

Anything that moves outside this list is a finding, and gets written into §4.

## 4. Outturn

*(appended in the lane's last commit)*
