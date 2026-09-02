# Provenance lane — Wave 3 targets

*Opened 2026-09-02 on `provenance/wave3-targets`, branched from `main` @
`7f25bed` (the merge of PR #96). Work under `planning/MODELING_IMPROVEMENT.md`
§1.6 and the repository's two supersede mechanisms — the Tier-1 manifest
(`fiscal_model/validation/preregistered.py`) and the Tier-2 revision ledger
(`fiscal_model/validation/target_revisions.py`, built by PR #90).*

**One modelling change, and it is a provenance fix**: `annual_cost_no_cap` stops
being the `eliminate_salt` target divided by ten and becomes a computation over
IRS SOI. Nothing else was retuned, no mechanism altered, no CI threshold
touched, no case deleted.

The lane follows the precedent set in `PROVENANCE_amt_insulin.md`: every target
gets a per-target judgement, the judgement cites the document row, and the
outcome is recorded as machine-readable state rather than prose — including
when the outcome is "leave it alone".

## 1. What each target was, and what it is now

| Target | Was | Is | Document row |
|---|---|---|---|
| **CBO Option 56** (employer-health exclusion) | out of scope for **leakage** — the only path that could score it was `cap_employer_health`'s fitted annual | **Tier 1 case, −$697.0B**, scored at −$529.9B (**24.0%**) | CBO pub. **60557**, *Options for Reducing the Deficit: 2025 to 2034*, Option 56, third alternative, report **p. 66** (PDF p. 72), row *"Decrease (−) in the deficit"* |
| **`pillar_two_adoption`** | −$80.0B, a **point** | **a published range, [−$102.6B, +$56.5B]**; the point stays as a display anchor and is labelled a midpoint | JCT **JCX-22-23**, Table 2, *"Fiscal Year Federal Tax Receipt Revenue Effects for Various Scenarios"*, report **p. 10** — Scenario 4 (+$102.6B of receipts) and Scenario 2 (−$56.5B) |
| **`biden_estate_reform`** | $450.0B, `line_item_differs` against JCT's $429.6B | **$450.0B — not moved**, recorded as examined | JCT letter to Sen. Sanders on the *For the 99.5 Percent Act* (draft GAI21423 NYM), letter **p. 5**, *"Total, For the 99.5 Percent Act"*, −$429.6B |
| **`treasury_capgains_39_plus_stepup_elim`** | −$322.0B, described as the *combined* rate-plus-step-up figure | **−$322.0B — confirmed combined**, not superseded | Treasury, *General Explanations of the FY2022 Revenue Proposals*, Table of Revenue Estimates, report **p. 105** (PDF p. 111), row *"Reform the taxation of capital income"*, $322,485M over FY2022-2031 |
| **`annual_cost_no_cap`** (the leaked SALT constant) | **120.0**, exactly the $1,200B target ÷ 10 | **89.55**, computed from SOI Table 2.1 × the statutory schedule | IRS SOI Table 2.1 TY2023, total (unlimited) state-and-local-tax deduction, priced at the IRC §1 married-joint schedule as adjusted for 2025 (Rev. Proc. 2024-40) |

Two moves went through a supersede mechanism (Option 56 through the Tier-1
manifest, Pillar Two through the Tier-2 ledger), two were examined and left with
the check recorded, and one was a constant with no target status at all.

## 2. Option 56 — a leakage exclusion that expired

Phase B excluded Options 53, **56** and 62 as leakage, on one rule: *a module
whose constant was fitted to reform X cannot predict reform X under another
name.* For Option 56 that was true because the only expressible path ran through
`cap_employer_health`'s fitted annual.

Lane L6 (PR #94) removed the dependency. A percentile cap is now scored as the
**published expenditure level** (`JCT_TAX_EXPENDITURES["employer_health"]`,
$250B/yr) times a **share** read off a premium distribution, so nothing
calibrated to a target sits in the path. L6 measured the first year at **+2.5%**
against CBO and explicitly declined to promote the option itself, handing the
question here.

**Promoted, and the mechanism the option needs is stated rather than assumed:**

- **One alternative, not three.** CBO's first two alternatives limit the income
  *and payroll* tax exclusion; the expenditure module carries the income-tax
  expenditure only and has no payroll base. Scoring them would be a known base
  mismatch, not a prediction, so 56.3 and 56.6 join `OUT_OF_SCOPE_ALTERNATIVES`
  per alternative. CBO's third alternative — *"Limit only the income tax
  exclusion … to the 50th percentile of premiums"* — is the same cap on the
  income-tax exclusion alone, and it is the one that is scored.
- **The target is the deficit row, not the revenue row.** −$697B is CBO's
  bottom line ($709B of added revenue net of $12B of added mandatory outlays).
  Worth flagging for whoever next touches the extractor: in
  `cbo_options_2025_2034_alternatives.csv` the *revenue sub-rows* of options
  that print three lines carry a mechanically negated `savings_*` figure, so
  56.2/56.5/56.8 read as **negative savings** for a revenue increase. The
  `Decrease (−) in the deficit` rows (56.3/56.6/56.9) are right, and this
  battery reads only those.
- **Shape inputs are fixed by a written rule** (`OPTION_56_SHAPE_RULE`), entered
  before the option ran: the caps are CBO's own stated 2028 limits ($10,000
  individual, $24,400 family — the 50th percentile of 2026 premiums indexed with
  the chained CPI-U), and `effective_start_year` is the first fiscal year CBO's
  own table shows a non-zero effect (2028).
- **The provenance caveat, stated rather than buried.** The premium
  distribution's *shape* parameter (σ) is identified from the two percentile
  values this same option prints. That is a **design** input, exactly like the
  budget-authority level a spending option donates to its own prediction; the
  target — the revenue CBO scores — is a different series and is read nowhere.
  The level is KFF's, not CBO's, and the two disagree: the model's implied 2028
  family median is $27,946 against CBO's $24,400 (14.5% high), which is why the
  σ is information rather than a mirror.

**Result: −$529.9B against −$697.0B, 24.0%.** The residual is one named
omission, recorded in `_KNOWN_LIMITATIONS_BY_POLICY_ID` and not tuned: CBO's
revenue grows ~14%/yr because the limit is indexed to the chained CPI-U while
premiums grow faster, so a widening slice of every premium rises above it. The
module evaluates its excess share **once, at `start_year`**, and the engine then
grows the result at the expenditure's own 4%/yr. A year-indexed excess share is
the next real structure this module is missing — L6 finding 3 predicted exactly
this, and it is now measured inside the battery rather than as hand arithmetic
beside it.

The new `tax_expenditure` validation shape pins `mode="derived"` and sets
`annual_revenue_change_billions=None` in `create_policy_from_score`. That is not
a stylistic choice: routing the shape through the module's app default
(`reported`) would reproduce the leakage the option was excluded for.

`cbo_options.py`'s docstring now says a leakage exclusion is not permanent, and
names what changed. Options 53 and 62 remain excluded.

## 3. Pillar Two — a point where the document publishes a range

`-$80B` is the midpoint of the "$50-120B" range `international.py` documents in
its own module header. **It is not a figure JCT publishes.** JCT scored the
policy under five scenarios and printed five numbers, and the two that describe
this benchmark's design — *the United States enacts Pillar Two, no U.S. UTPR* —
bracket the answer **across both signs**:

| JCT scenario (JCX-22-23, Table 2, report p. 10) | US receipts | Deficit effect |
|---|---:|---:|
| **Scenario 4** — rest of the world does *not* enact; US enacts, no US UTPR | +$102.6B | **−$102.6B** |
| **Scenario 2** — rest of the world enacts; US enacts, no US UTPR | −$56.5B | **+$56.5B** |
| *(Scenario 1 — RoW enacts, US does not)* | −$122.0B | +$122.0B |
| *(Scenario 5 — US enacts **with** a UTPR)* | +$236.5B | −$236.5B |

Scenarios 1 and 5 are different policies (the US does not act; the US adds a
different instrument, which the module carries behind its own `adopt_utpr` flag
and this benchmark does not set), so they bound nothing here and are recorded
only so the chosen bounds cannot be mistaken for a selection.

**Superseded by a range, not by another point.** Choosing one scenario would
mean choosing the *rest of the world's* behaviour, which is not part of the US
policy being scored — and the scenario whose conditioning matches the module's
own QDMTT mechanism is also the one it scores best against, which is exactly the
selection the ledger exists to prevent.

The ledger was extended minimally to say so: `CalibratedTarget` gains
`published_low_10yr_billions` / `published_high_10yr_billions`, `is_range`,
`contains()` and `distance_to_range()`. For a range row the consistency check
asks whether the figure the scorecard carries lies **inside** the bounds instead
of equalling a point, and `ScorecardEntry` / `/validation/scorecard` expose
`published_range_low_billions`, `published_range_high_billions`,
`within_published_range` and `distance_to_published_range_billions`.

| Reading | Value |
|---|---|
| Model | **−$61.2B** |
| Against the carried point (−$80B) | 23.5%, rated Poor |
| Against the published range | **inside**, distance to the nearest bound **$0.0B** |

**Nothing moved in the registries or the app.** −$80B stays as the display
anchor because it is inside the published range, and `benchmark_sources.py`
stays `line_item_differs` because the gap to the nearest published scenario is
real. What changed is that the row now says the gap is **not closable by any
point**, and the 23.5% is a distance from an editorial midpoint rather than a
measurement of accuracy.

One handoff, not done here because `fiscal_model/international.py` belongs to
lane L9: its `CBO_INTERNATIONAL_ESTIMATES["pillar_two_adoption"]["10yr_score"]`
still carries `-80.0` as a display constant. No runner reads it — the sectoral
runner reads `CBO_SCORE_MAP` — but it should carry the range's provenance note
when L9 next touches the file.

## 4. The estate target — examined, and deliberately not moved

The brief's own test: *if the design the module scores is the bill JCT scored,
supersede; if the JCT figure covers a ten-section bill the module does not
construct, record that and leave it.*

It is the second. JCT's $429.6B totals the whole *For the 99.5 Percent Act*:
graduated **50/55/65%** brackets above $10M/$50M/$1B, denial of grantor-trust
step-up, valuation-discount limits, a 10-year minimum GRAT term and GST changes.
`estate.py` constructs an exemption change to $3.5M and a **single 45% top
rate** — not even the whole rate section, since it carries no graduated
schedule. $429.6B is an **upper bound on a superset**, and adopting it as a point
target would convert a bookkeeping 0.0% into a 4.7% that measures the eight
sections the module does not model.

Both errors, both modes, both figures (`validate_estate_policy(..., mode=...)`,
2026-09-02):

| Mode | Model | vs carried −$450.0B | vs published −$429.6B |
|---|---:|---:|---:|
| `reported` (fitted) | −$450.0B | **+0.00%** | **−4.75%** |
| `derived` (structural) | −$457.2B | **−1.60%** | **−6.43%** |

Neither reading changes the verdict, and the fitted 0.00% is bookkeeping either
way. What *would* change it is a JCT or Treasury score of an exemption-and-rate
change alone; none exists.

The verdict is now state rather than prose. `EXAMINED_NOT_REVISED` in
`target_revisions.py` records "somebody opened the document and decided
against", with the reason, because without it a benchmark nobody has examined
looks identical to one that was — and the question gets re-opened every pass. A
benchmark may not be both revised and examined-and-left, and
`target_revision_problems()` fails if one ever is.

## 5. The Treasury FY2022 flag — confirmed, not superseded

Lane L1 flagged that `treasury_capgains_39_plus_stepup_elim` describes −$322.0B
as the *combined* rate-plus-step-up figure while the FY2022 Green Book's
narrative states the two as separate proposals, and asked whether the carried
figure is the combined row or the rate-only one.

Opened (home.treasury.gov serves the volume; the table pages are rotated 90° and
need re-extraction). Under **"American Families Plan — Strengthen taxation of
high-income taxpayers"** the Table of Revenue Estimates prints **exactly two
rows**:

| Row | FY2022-26 | FY2022-31 |
|---|---:|---:|
| Increase the top marginal income tax rate for high earners | $131,920M | **$131,920M** |
| Reform the taxation of capital income | $136,263M | **$322,485M** |

The top-rate row is zero from 2027 on, because the 39.6% rate returns by itself
when TCJA sunsets — which is also the internal check that these are the two
rows they claim to be. **No row anywhere in the table names transfers, gifts,
death, realization or appreciated property**, so Treasury published no split of
the two sub-proposals its narrative section describes under the one heading
("Tax capital income for high-income earners at ordinary rates" and "Treat
transfers of appreciated property by gift or on death as realization events",
report pp. 62-63).

**The combined reading stands.** Footnote 1 — *"A separate proposal would first
increase the top ordinary individual income tax rate to 39.6 percent (43.4
percent including the net investment income tax)"* — which Phase E cited for the
+19.6pp incremental rate, is also confirmed. No manifest row moved, no target
moved, no model moved. The re-read is recorded in `benchmark_sources.py` and in
the record's own notes so the question is not opened a third time.

What the flag *does* leave standing is L1's substantive point, which is a model
finding and not a target one: the model's death channel alone under a $1M
exclusion is larger than the whole $322.0B target, and the model applies **no
behavioural response to the death channel** while Treasury's score prices the
spousal, charitable, §121, tangible-property, family-business and 15-year
installment carve-outs. That is L1's row to close, not this lane's.

## 6. The leaked SALT constant

L6 finding 1: `annual_cost_no_cap = 120.0` is **exactly** the `eliminate_salt`
target ($1,200B) divided by ten, and `loo.py`'s leakage guard reclassified the
case as not cross-validatable the moment L6's `eliminate` rule started reading
it — *"the base constant is the answer key restated"*. The guard cannot tell "the
target restated" from "a round number that happens to equal the target over
ten", and both readings were live: the module's own *fitted* annual for that
benchmark is **104.7**, not 120.0, so whoever set 120.0 was not copying the
fitted path. What was not in doubt is that it was unsourced and, after L6,
load-bearing.

**Replaced with the computation, not with another literal.**
`uncapped_salt_expenditure_billions()` returns
`load_deduction_distribution("salt").implied_benefit_billions` — IRS SOI Table
2.1's total (unlimited) SALT deduction, priced AGI class by AGI class at the
IRC §1 married-joint schedule as adjusted for 2025 (Rev. Proc. 2024-40) —
**$89.55B**. The identical computation on SOI's *limited* column returns
**$25.0B** against the record's own `annual_cost = 25.0`: two numbers with no
common ancestor agreeing to a tenth of a percent, which is the check that the
method is not made up. Both are pinned in `tests/test_tax_expenditure_units.py`,
and the test now asserts the record **equals** the derivation rather than
differing from it in a known direction.

L6 predicted the consequences and priced them; every one landed:

| Row | L6's prediction | Outturn |
|---|---|---|
| LOO `eliminate_salt` | readmitted at **10.2%** | **+10.2%** |
| LOO `repeal_salt_cap` | +4.0% → **−29.4%** | **−29.4%** |
| Expenditure module LOO mean | 27.2% → **30.2%** over five cases | **30.2%**, n=5 |

`repeal_salt_cap`'s old **+4.0% was never evidence of anything** — it is
`−(120.0 − 25.0)`, the same leaked constant under a different benchmark, and the
guard missed it only because its target is $1,100B rather than $1,200B. Trading
a flattering leaked number for an honest −29.4% is the trade this lane exists to
make, and L6 declined it only because it declined to source the constant.

**Nothing fitted moved.** Every preset and every fitted-tier row scores in
`reported` mode and returns the same `annual_revenue_change_billions`; the
`reported` regression pins (`create_repeal_salt_cap` −96.0,
`create_eliminate_salt_deduction` 104.7) are untouched.

`loo.py` needed **no per-case edit**: the exclusion was produced by the
mechanical guard and disappears mechanically. The guard itself was not touched.

## 7. Gate outcomes

| Gate | Base `7f25bed` | This branch |
|---|---|---|
| `ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py scripts/` | 0 | **0** |
| `pytest tests/ -q` | 0 | **0** |
| `cold_holdout.py --max-mean-error 40 --min-within-25pct 17` | 0 | **0** |
| `run_loo.py --donor-matrix --max-mean-error 75` | 0 | **0** |
| `run_validation_dashboard.py` | 1 (pre-existing: a degraded health component) | **1**, unchanged |
| `check_readiness.py --strict` | 2 (`ready_with_warnings`) | **2**, unchanged — the same four warnings (Python 3.14 runtime, degraded microdata calibration, one documented `Poor` revenue benchmark, `pwbm_39_with_stepup` in the locked holdout), no new issue. Option 56 rates `Poor` at 24.0% and carries a `known_limitations` note, so it is a documented out-of-sample miss and not a new blocker |

### Tier 1, and the thresholds the workflow's rule derives

| | Base | This branch |
|---|---|---|
| cases | 25 | **26** |
| mean abs error | 31.3% | **31.0%** |
| median | 14.1% | **15.1%** |
| within 15% | 13/25 | **13/26** |
| within 25% | 18/25 | **19/26** |

By `.github/workflows/validation-dashboard.yml`'s own rule — ceiling
`ceil(mean × 1.25)` rounded up to the nearest 5; floor = current within-25%
count minus one:

- **ceiling: `ceil(31.0 × 1.25) = 39 → 40`. Unchanged at 40.**
- **floor: `19 − 1 = 18`. A tightening from 17 → 18**, which the rule allows
  without a reason.

**The workflow was not edited.** Those are the derived values for the
coordinator; the branch passes at the current 40/17 either way.

### Tier 2

| | Base | This branch |
|---|---|---|
| Fitted calibrated (`cold_holdout.py`) | 30 @ 2.2% | **unchanged** |
| Unfitted reconstructions | 24 @ 72.1% | **unchanged** |
| Leave-one-out | 17 derivable @ 32.3% / 19.2%, 8-of-17, **5** not x-val | **18 derivable @ 32.5% / 23.6%, 8-of-18, 4 not x-val** |
| — Expenditures module | 28.8% (n=4, 2 not x-val) | **30.2% (n=5, 1 not x-val)** |
| Scorecard rows | 79 (72 published) | **80 (73 published)** |
| `revised_target_entries` | 2 | **3** |

The LOO mean moved 0.2pp while a case **re-entered** the denominator. That is
the reading to quote: the suite now cross-validates 18 of 22 calibrated
benchmarks at the same error, where it cross-validated 17 and excluded one for
leakage. `pillar_two_adoption` was already outside the fitted tier
(`calibrated_to_target=False`), so its revision moves no tier and no mean.

## 8. Left undone, deliberately

- **`repeal_salt_cap`'s target is still $1,100B and still unsourced**, and the
  row now reports −29.4% against it on a bottom-up path. Whether the honest
  target is $1,100B at all is the next question in this file's queue; §6 of
  `L6_tax_expenditures.md` shows the two SALT benchmarks are scored against
  contradictory baselines (the $10,000 cap has lapsed for `eliminate` and binds
  for `expand`), and reconciling that needs a baseline-vintage concept the
  module does not have.
- **`annual_cost_no_limit = 100.0` on the mortgage record is still unsourced**
  and still dead (L6 finding 5). It names no statute; the natural candidate,
  TCJA's $750,000 acquisition-debt cap, is worth single-digit billions a year.
  Giving it a `limitation` block would make it live automatically and move
  `eliminate_mortgage` from −5.1% to about +244% on an unsourced constant. It
  stays unread until somebody sources it.
- **Option 56's other two alternatives are not scored**, and will not be until
  the expenditure module has a payroll base. They are recorded per alternative,
  so promoting them later is a one-line change plus the mechanism.
- **The year-indexed excess share is not built.** It is the whole of Option 56's
  24% residual and it belongs to whoever owns `tax_expenditures_core.py` next,
  not to a provenance lane.
- **`fiscal_model/international.py`'s display constant still says −$80B** (§3).
  Lane L9 owns the file.
- **The alternatives CSV's revenue sub-rows carry an extraction sign artifact**
  (§2). Only the deficit rows are read, so nothing is wrong today; fixing it
  means re-running `scripts/extract_cbo_options.py`, which rewrites a
  pre-registered data file and needs its own commit pair.
- **The other 12 `line_item_differs` rows are untouched.** Each needs the same
  per-target judgement; several (both Social Security payroll targets,
  `repeal_ira_credits`) have no published figure to move to at all.

## 9. Handoff to the docs lane

`README.md`, `CLAUDE.md`, `docs/VALIDATION*.md`, `docs/METHODOLOGY.md`,
`planning/MODELING_IMPROVEMENT.md`, `planning/NEXT_STEPS.md` and
`docs/CHANGELOG.md` are owned by the concurrent docs lane and were not touched.
The rows this branch invalidates:

| File | Says today | Should say |
|---|---|---|
| `CLAUDE.md` "Model maturity" and "Target Validation", Tier 1 | 25 pre-registered cases, 34.4% mean, 16/25 within 25% | **26 cases, 31.0% mean (median 15.1%), 13/26 within 15%, 19/26 within 25%** |
| `CLAUDE.md` Target Validation, CBO Options battery | "14 runnable alternatives across 11 of its 76 options; the other 65 options carry a one-line exclusion reason … Three exclusions are leakage (Options 53, 56 and 62)" | **15 runnable alternatives across 12 options; 64 options excluded; two leakage exclusions (53 and 62)** — and one sentence on why 56 stopped being one |
| `CLAUDE.md` Target Validation, CI gate | `cold_holdout.py --max-mean-error 45 --min-within-25pct 15` | the workflow is at **40 / 17**; the rule now derives **40 / 18** |
| `CLAUDE.md` Target Validation, LOO | "58.7% mean / 32.5% median over 18 leave-one-out cases, 6/18 within 15% (4 more declared not cross-validatable)" — stale since Wave 2 as well | **32.5% mean / 23.6% median over 18 cases, 8/18 within 15%, 4 not cross-validatable** |
| `CLAUDE.md` Target Validation, revisions | "`ScorecardSummary.revised_target_entries` is **2**"; the two named are AMT and insulin | **3**; the third is `pillar_two_adoption`, and it is a *range* revision, which asserts something different from a point revision — §3 |
| `CLAUDE.md` Target Validation, scorecard totals | 79 scorecard rows, 72 published | **80 rows, 73 published**; calibrated tier unchanged at 54 (47 published) |
| `docs/VALIDATION.md` `line_item_differs` table | 13 rows listed as open owner decisions, including Pillar Two and the estate reform | still 13 rows and both are still listed — but Pillar Two now carries a **range revision** and the estate row an **examined-and-left** verdict, and both should say so rather than reading as unexamined |
| `docs/VALIDATION_NOTES.md` §6, LOO aggregate | "58.7% mean / 32.5% median over 18 derivable cases, 6/18 within 15%, plus 4 cases reported as not cross-validatable" — stale since Wave 2, and L6 then took it to 17 derivable with 5 excluded | **32.5% mean / 23.6% median over 18, 8/18 within 15%, 4 not cross-validatable.** The path back to 18 is not the path it left by: `eliminate_salt` is cross-validatable again at **+10.2%** because its base constant stopped being the target, and `repeal_salt_cap` moves **+4.0% → −29.4%** because it was built from that same constant |
| `docs/VALIDATION_NOTES.md` §6, expenditures bullet | "Tax expenditures (5 of 6, mean 39.4%)" — pre-L6; L6's handoff table asked for "4 of 6, mean 28.8%" | **5 of 6, mean 30.2%** — L6's handoff row is superseded before it was applied |
| `docs/METHODOLOGY.md` / anywhere quoting the SALT no-cap level | $120B/yr | **$89.6B/yr**, derived from SOI Table 2.1 × the statutory schedule, with §6's note that the old figure was the target restated |
