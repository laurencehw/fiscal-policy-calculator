# Wave 4 lane 3c — AMT: the statutory phase-out

*Pre-registered 2026-09-02 against `origin/main` @ `5deef17`, before any code
change. Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2 item 13 — "**L5's phase-out
thresholds.** Carried from Wave 1" — under §4's rules and owner Decision 1.
What Wave 1's L5 left, in its own words:

> Did not model the phase-out thresholds. `phase_out_threshold_change` is still
> declared and never read; `AMT_PHASEOUT_TCJA` still stops at 2030. Under the
> post-sunset schedule the phase-out is what claws the exemption back from
> high-income filers, so it is the next real structure this module is missing —
> but it needs a published phase-out path, which T25-0049 does not carry.

**T25-0049 does not carry one and does not need to.** The phase-out path is
*statutory*, not projected: IRC §55(d) fixes the claw-back rate and the
threshold, and the IRS publishes the indexed threshold for every filing status
in every year's inflation Revenue Procedure. That is the data this lane
transcribes, and it is a stronger source than a microsimulation projection.

## 1. Starting numbers

All from the branch point, on `5deef17`.

### Leave-one-out — `python scripts/run_loo.py --donor-matrix`

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| AMT | `extend_tcja_amt` | 1,357.1 | 450.5 | 855.3 | **−37.0%** |
| AMT | `repeal_individual_amt` | 450.0 | 450.5 | 948.9 | **+110.9%** |
| AMT | `repeal_corporate_amt` | 220.0 | 220.1 | — | not cross-validatable |

AMT module mean **73.9%** (n=2 derivable, 1 excluded by the leakage guard).
**Suite aggregate: 28.4% mean / 16.5% median over 18 derivable cases, 9/18
within 15%, 4 not cross-validatable.**

### Reported vs derived, per benchmark

`validate_amt_policy(case, mode=...)` against the live targets:

| Benchmark | Target | Reported | Err | Derived | Err |
|---|--:|--:|--:|--:|--:|
| `extend_tcja_amt` | $1,357.1B | $450.5B | −66.80% | $855.3B | **−36.97%** |
| `repeal_individual_amt` | $450.0B | $450.5B | +0.12% | $948.9B | +110.87% |
| `repeal_corporate_amt` | $220.0B | $220.1B | +0.05% | $252.2B | +14.64% |
| **Mean abs** | | | **22.32%** | | **54.16%** |

`AMT_APP_MODE` is `reported` under Decision 1's own rule, and this lane expects
it to stay there (§3).

### Battery aggregates — `python scripts/cold_holdout.py`

- Tier 1 (out-of-sample): **26 cases, 31.0% mean, 13/26 within 15%, 19/26 within 25%.**
- Calibrated fitted tier: **28 policies, 2.0% mean, 28/28 within 15%.**
- Unfitted module reconstructions: **26 policies, 61.8% mean, 5/26 within 15%, 9/26 within 25%.**

## 2. What the lane changes

Everything is in `fiscal_model/amt.py` plus one new transcribed data file and
`tests/test_amt_phaseouts.py`.

1. **A statutory phase-out, from the statute.** The exemption is reduced by a
   statutory fraction of AMTI above a threshold (IRC §55(d)(2), formerly
   §55(d)(3)). Three schedules become expressible: **pre-TCJA** (what the sunset
   reverts to), **TCJA** (2018-2025), and **P.L. 119-21** (current law from
   2026, which reset the thresholds *down* to $500,000/$1,000,000 and raised the
   claw-back rate from **25% to 50%**).
2. **A published threshold path by filing status and year**, transcribed from
   the IRS inflation Revenue Procedures, replacing `AMT_PHASEOUT_TCJA` — a
   hand-estimated MFJ/single table that stopped at 2030 and that nothing read.
3. **One indexation rule instead of a stopped table.** Every schedule is carried
   past its last published row by the §1(f)(3) compound rate the *published*
   TCJA threshold series itself implies, rounded to the statute's own $100.
   Same rule for every regime and every filing status; fitted to nothing.
4. **`phase_out_threshold_change` becomes live.** It is currently a declared
   field that no code path reads, so a threshold reform scores exactly 0.0 —
   the same class of dead branch L5 found in the exemption leg.
5. **The interpolation coordinate becomes an exemption-equivalent.** The derived
   path interpolates published aggregates on a single scalar "MFJ exemption".
   That scalar becomes the flat exemption that would produce the same aggregate
   AMT base as the (exemption, threshold, claw-back rate) triple actually does,
   with the base computed on the published IRS SOI AGI distribution. It is
   `E` exactly when the phase-out is out of reach, monotone increasing in the
   exemption and in the threshold, and monotone decreasing in the claw-back
   rate.

## 3. The prediction

**Headline: no benchmark moves, in any tier, and that is a fact about where the
benchmarks sit rather than a weak mechanism. I am registering it in advance so
that a row which *does* move is read as a defect, not as a result.**

Both individual-AMT benchmarks sit **exactly on a published regime anchor**:
`extend_tcja_amt`'s policy leg *is* the high anchor and `repeal_individual_amt`
zeroes the low one. A transform of the interpolation coordinate that is computed
from each anchor's own statutory parameters returns that anchor's published row
unchanged, by construction. The phase-out is a second dimension of the reform
space and the two benchmarks do not vary in it. Neither does the third: CAMT has
no exemption and no phase-out.

### Rows I expect NOT to move, to the decimal

| Row | Now | Predicted |
|---|--:|---|
| LOO `extend_tcja_amt` | −37.0% ($855.3B) | unchanged |
| LOO `repeal_individual_amt` | +110.9% ($948.9B) | unchanged |
| LOO `repeal_corporate_amt` | not cross-validatable | unchanged |
| AMT module LOO mean | 73.9% | unchanged |
| LOO suite (n=18) | 28.4% / 16.5% / 9-of-18 | unchanged |
| Tier 1 | 26 @ 31.0% / 13 / 19 | unchanged |
| Fitted calibrated tier | 28 @ 2.0% | unchanged |
| Unfitted reconstructions | 26 @ 61.8% | unchanged |
| Reported-vs-derived mean | 22.32% vs 54.16% | unchanged |
| `AMT_APP_MODE` | `reported` | **stays `reported`** — derived still loses |
| App preset output | every AMT preset | unchanged (all score `reported`) |

`pl119_21_amt_exemption` is scored by `tcja.py`'s
`create_tcja_extension(extend_amt=True)`, not by `AMTPolicy`, so it stays at
its current reconstruction value. This lane does not open `tcja.py`.

### What I expect to change, and how it will be measured

Three things no row in the battery currently measures.

1. **A threshold reform stops scoring zero.** `phase_out_threshold_change`
   returns 0.0 today for any value. Predicted after: a $100,000 cut to the MFJ
   threshold scores a revenue **gain**, and a $100,000 increase a **loss**, in
   the low-single-digit $B/yr range post-sunset. The *sign* is the test; the
   magnitude is a report.
2. **P.L. 119-21's actual AMT design becomes expressible** — permanent TCJA
   exemption, thresholds reset to $500,000/$1,000,000, claw-back rate 50%. JCT
   scores that provision at **+$1,362.810B** (JCX-35-25, FY2025-2034), already
   carried in this repository as `pl119_21_amt_exemption` and reconstructed by
   the TCJA module at **$719.3B (−47.2%)**, whose own note says *"law also cuts
   phaseout thresholds and raises the rate"*. Predicted `AMTPolicy` derived
   10-year cost: **$780B to $880B**, i.e. **−35% to −43%** against JCT's figure.
   **I am not changing that benchmark or its runner**; the AMTPolicy number is
   computed and reported beside it, because it is the only published quantity in
   the repository that prices the mechanism this lane adds.
3. **The stopped tables go.** `AMT_PHASEOUT_TCJA` ended at 2030; the two
   exemption dictionaries ended at 2034 and clamped to their last row.

### One row that is not a benchmark and will move

`create_increase_amt_exemption` in **derived** mode. Two reasons: the
coordinate transform is non-linear in the exemption, and the current-law
post-sunset exemption schedule is being replaced by the **statutory** reversion.
The module currently carries a hand-estimated $93,000 MFJ for 2026; pre-TCJA law
indexed forward from Rev. Proc. 2016-55's $84,500 is about **$112,800**, ~21%
higher. Predicted: same sign, same ordering in the size of the change, magnitude
within a factor of ~1.5 of today. No benchmark reads this factory, and every
shipped preset that does scores in `reported` mode.

### Risks I am naming before writing the code

- The exemption-equivalent averages the statutory claw-back over the **pooled**
  SOI AGI distribution (all filing statuses) while the module's coordinate is
  MFJ-denominated, and it ages SOI 2023 forward at the module's existing 3%/yr
  engine growth constant. Both are approximations. Because **both anchors are
  computed the same way and both benchmarks sit on anchors**, neither can bias a
  benchmark; they set only how steeply an off-anchor reform is priced. The
  sensitivity to each gets reported in §4, not hidden.
- AMTI is not AGI. The claw-back is applied to a published AGI distribution
  because no public AMTI distribution exists at this granularity. Same
  qualification.
- The derived path's "current law" is **TPC T25-0049's baseline** — law as of
  1 January 2025, i.e. with the TCJA sunset still in force — and *not*
  P.L. 119-21. That is what the two benchmarks describe. Scoring against
  post-OBBBA law would need a TPC vintage that does not exist, and inventing one
  is the failure mode §4 forbids.

Anything that moves outside this list is a finding, and gets written into §4.

## 4. Outturn

*Appended after the code, in the last commit.*
