# Lane W4-pharma — the Part D channels and the reference-pricing base

*Wave 4 lane 3b. Opened 2026-09-02 on `model/w4-pharma-part-d`, branched from
`main` @ `5deef17`. Carries item 12 of
[`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §6.2 — "L7's
Part D channels. Carried from Wave 1: the incidence bugs are fixed, the channels
are not built."*

Pre-registration first (§1.3). This file states what the module does today, what
the lane changes, and what it expects to happen, **before** a line of
`fiscal_model/pharma.py` moves. The outturn is appended in the lane's last
commit. Nothing here is a promise of attainment — §1.5 forbids that — and two of
the three rows are expected to get *worse* against their stored targets, which
is said here in advance rather than explained away afterwards.

## 1. Starting point (measured on `5deef17`)

`python scripts/cold_holdout.py --json`, unfitted-reconstruction tier:

| Row | Target | Model | Error | Target provenance |
|---|---:|---:|---:|---|
| `universal_insulin_cap` | +$11.4B | +$7.0B | 39.0% | `line_item` (CBO 57957) |
| `international_reference_pricing` | −$100.0B | −$746.2B | **646.2%** | `model_estimate` |
| `expand_drug_negotiation` | −$500.0B | −$371.5B | 25.7% | `model_estimate` |

Aggregates on the same commit:

- **Pharma family (3 rows): 236.9% mean** (mass 710.9).
- **14-row sectoral subset: 81.0% mean** (mass 1,134.8).
- **26-row reconstruction tier: 61.8% mean / 38.0% median** (mass 1,607.1).
- Tier 1 out-of-sample: 31.0% mean / 15.1% median, 13/26 within 15, 19/26 within 25.
- Leave-one-out: 28.4% mean / 16.5% median (n=18 derivable).
- Calibrated fitted: 2.0% (n=28).

Shipped preset output on `5deef17`:

| Preset | 10-year |
|---|---:|
| 💊 Expand Drug Negotiation | −$371.5B |
| 💊 Universal Insulin Cap | +$7.0B |
| 💊 International Reference Pricing | −$746.2B |
| 💊 Comprehensive Drug Reform | −$573.5B |

## 2. What the lane changes, and why

Wave 1 (L7) fixed *incidence* — who bears a drug-price or cost-sharing change.
It left the **channels** unbuilt. Four things follow from that, and this lane
takes them in order.

### 2.1 The federal share is one 2023 number for a benefit design that no longer exists

`part_d_program_federal_share = 0.763` is the 2023 outturn: Medicare's $4.9B
direct subsidy + $63.3B reinsurance + $43.9B low-income subsidy against $128.2B
of plan payments plus $18.8B of enrollee cost sharing (MedPAC, March 2025,
ch. 12, Table 12-5 p. 432 and p. 409). It is a **single aggregate of the three
channels**, measured in the last full year of the *pre-redesign* benefit, when
Medicare's reinsurance covered **80 percent** of catastrophic-phase cost. From
2025 the IRA's redesign cuts reinsurance to **20 percent for brands and 40
percent for generics** and pushes the difference onto plan bids and therefore
onto the capitated direct subsidy (MedPAC Figure 12-1, p. 420). Every score in
this repository runs over 2025-2034. The lane replaces the aggregate with the
three channels, re-weighted on MedPAC's own published 2025 bid decomposition.

### 2.2 The negotiation row is scored off a per-drug average that is not a per-drug average

`_estimate_negotiation_savings` computes `ira_per_drug = 237 / 10 / 20 = $1.185B`
of federal saving per negotiated molecule per year, then scales it linearly in
drug count with a hand-written 60% productivity haircut and adds a hand-written
30% for removing the exclusivity delay. Three separate problems:

1. **$237B is not CBO's negotiation score.** It is CBO's estimate of the IRA's
   *entire* drug-pricing title — negotiation, inflation rebates, the Part D
   redesign and the premium-stabilisation provisions together. CBO's figure for
   the negotiation program alone is about **$100 billion over ten years**, and
   about **$3.7 billion in the first year** (HHS Secretary Becerra, quoting CBO,
   in CMS's 15 August 2024 press release). Dividing the title total by the
   negotiation program's drug count overstates the per-drug rate by roughly 2.4×.
2. **"The IRA's 20 drugs" is not the statute.** The IRA selects 10 Part D drugs
   for 2026, up to 15 more for 2027, up to 15 more (Part B or D) for 2028, and
   **up to 20 more each year after that** (CMS, same release). The negotiated set
   is cumulative and reaches 160 molecules by 2034 under current law, not 20.
3. **Savings are not linear in drug count.** CMS's own three selection cycles are
   a published concentration curve: 10 drugs at $56.2B of gross Part D spending,
   the next 15 at $41B, the next 15 at $27B — $5.62B, $2.73B and $1.80B per
   molecule. The marginal molecule at rank 200 is worth a small fraction of the
   marginal molecule at rank 10, and a linear model cannot see that.

### 2.3 The reference-pricing base is the whole brand book; RAND's index is not

L7's own closing note: "RAND's index is computed on presentations sold in both
markets, and the module applies it to all brand spending." RAND publishes the
coverage. For the combined 33-country comparison — the one that produces the
3.08 net brand ratio the module uses — the matched presentations account for
**90.2 percent of US sales and 88.3 percent of US volume** (RR-A788-3,
Table A.4, p. 36), and brand-name originators are **84 percent of the sales that
contribute** against **87 percent of all US sales** (Tables A.6 p. 38 and 2.2
p. 12). US brand-originator sales reachable by a foreign reference price are
therefore 0.902 × 0.84 / 0.87 = **87.1 percent** of the brand base, not 100.

The lane also looks for the **utilisation response** CBO assumed when it scored
H.R. 3's cap at 120% of the average international market price, and for CBO's
stated assumption about **fewer new drugs** under the IRA's negotiation
provisions. `cbo.gov` returns HTTP 403 to every non-browser client, so both have
to be found quoted verbatim in an accessible source. **If neither can be sourced,
neither is added** — the module already carries an unsourced
`innovation_offset_pct = 0.05`, and this lane's job is to remove invented
constants, not to add a second one. Whichever way that lands is recorded in §5.

### 2.4 The `part_d_oop_cap` lever

There is nothing left to delete: L7 removed the `oop_cap` field outright and
`tests/test_pharma_incidence.py::test_no_policy_field_is_declared_without_being_read`
pins it gone. L7's docstring set the condition for bringing it back — "Adding the
mechanism means adding a sourced shift, not restoring the field" — and the
sourced shift now exists: ASPE projects **$7.2 billion** of Part D out-of-pocket
savings in 2025 for the 11.3 million enrollees who reach the $2,000 cap
(*Projecting the Impact of the Inflation Reduction Act's Part D Redesign*,
HP-2025-02, January 2025, Table 2B p. 7). The lane restores the lever on that
figure, with the same incidence as the insulin cap: cost sharing that comes off
the beneficiary lands on plan bids, and Medicare's basic-benefit subsidy picks up
74.5 percent of it.

### 2.5 `PHARMA_VALIDATION_SCENARIOS`

Item 19 of §6.2. `grep` over the tree finds no reader: `validation/compare.py`,
`validation/__init__.py` and `specialized_sectoral.py` all import
`PHARMA_VALIDATION_SCENARIOS_COMPARE` from `validation/scenarios.py`, a different
object. The dict at the foot of `pharma.py` carries `-237.0 "CBO (2022)"` and
`-500.0 "Estimate"`, which look like targets and are read by nothing. **Deleted**,
on the same footing as the `CBO_TRADE_ESTIMATES` and `TRADE_VALIDATION_SCENARIOS`
that L8 removed. `CBO_PHARMA_ESTIMATES` is deleted with it, for the same reason
and with the same test.

## 3. Data transcribed for this lane

Everything below lands in
`fiscal_model/data_files/pharma/drug_pricing_incidence.csv` with page and URL,
and `tests/test_pharma_incidence.py` pins `PHARMA_BASELINE` against it.

| Quantity | Value | Source |
|---|---|---|
| Part D direct subsidy, per enrollee per month, 2025 | $142.67 | MedPAC, March 2025, ch. 12, Table 12-2 (p. 424), quoted p. 421 |
| Part D expected reinsurance, per enrollee per month, 2025 | $40.08 | same |
| Base beneficiary premium, 2025 | $36.78 | same |
| Medicare direct subsidy / reinsurance / LIS, 2023 | $4.9B / $63.3B / $43.9B | MedPAC, same chapter, Table 12-5 (p. 432) |
| Plan payments + enrollee cost sharing, 2023 | $128.2B + $18.8B | same chapter, p. 409 |
| Catastrophic-phase reinsurance, 2025 design | 20% brand / 40% generic | same chapter, Figure 12-1 (p. 420) |
| Gross Part D spending, 10 drugs selected for 2026 | $56.2B, ~20% of Part D gross, 2023 | CMS press release, 15 Aug 2024 |
| Saving from the 2026 negotiated prices, applied to 2023 | $6B, ~22% of net covered drug costs | same |
| Gross Part D spending, 15 drugs selected for 2027 | $41B, ~14%, Nov 2023–Oct 2024 | CMS press release, 17 Jan 2025 |
| Gross Medicare spending, 15 drugs selected for 2028 | $27B, ~6% of Part B+D, Nov 2024–Oct 2025 | CMS press release, third cycle |
| IRA selection schedule | 10 / +15 / +15 / +20 per year | CMS press release, 15 Aug 2024 |
| CBO's estimate for the negotiation program alone | ~$100B over 10 years; $3.7B in year 1 | CBO, quoted by HHS in the same release |
| US sales contributing to the combined RAND comparison | 90.2% (volume 88.3%) | RAND RR-A788-3, Table A.4, p. 36 |
| Brand-originator share of contributing US sales | 84% | RR-A788-3, Table A.6, p. 38 |
| Brand-originator share of all US sales | 87% | RR-A788-3, Table 2.2, p. 12 |
| Part D out-of-pocket savings from the $2,000 cap, 2025 | $7.2B, 11.3M enrollees | ASPE HP-2025-02, Table 2B, p. 7 |

## 4. Pre-registered expectations

Hand-computed from the figures above **before** any code change
(`scratchpad/calc.py`, reproduced in the module's tests).

### 4.1 The federal share, decomposed

Of the $147.0B universe MedPAC reports for 2023, the basic-benefit block
(direct subsidy + reinsurance + enrollee premiums) is 57.35%, the low-income
subsidy 29.86% and enrollee cost sharing 12.79%. Re-splitting the basic-benefit
block on MedPAC's published 2025 per-enrollee bid decomposition (64.99% direct
subsidy / 18.26% reinsurance / 16.75% premium) gives the three channels:

| Channel | Share of a $1 Part D cost reduction |
|---|---:|
| Direct subsidy | 0.3727 |
| Reinsurance | 0.1047 |
| Low-income subsidy | 0.2986 |
| **Federal total** | **0.7760** |
| *(memo: the 2023 aggregate it replaces)* | *0.7626* |

The redesign moves cost **between** the two Medicare channels — reinsurance
0.431 → 0.105 of the universe — and barely changes the federal total, because
the 6 percent cap on the base beneficiary premium raises the direct subsidy by
almost exactly what reinsurance loses. That is the finding; the +1.3pp is
incidental.

### 4.2 Expected movement, per channel

| Row | Before | Expected after | Channel |
|---|---:|---:|---|
| `universal_insulin_cap` | +$7.0B / 39.0% | **unchanged** | the cap is a cost-sharing shift onto plan liability at the statutory 74.5%; none of the three channels re-weights it |
| `international_reference_pricing` | −$746.2B / 646.2% | **≈ −$660B / ≈ 560%**, before any utilisation response | −746.2 × 0.871 (RAND coverage) × 0.776/0.763 (federal-share re-weight) |
| `expand_drug_negotiation` | −$371.5B / 25.7% | **≈ −$64B / ≈ 87%**, a row that gets **much worse** | cumulative selections on the CMS rank-size ladder, at CMS's own $6B-on-$56.2B saving rate, times the three-channel federal share |
| 💊 Comprehensive Drug Reform | −$573.5B | moves with its components | |

### 4.3 Why the negotiation row is expected to get worse, and why that is right

−$500B is provenance `model_estimate`; `benchmark_sources.py` says so in terms
("extending that to 50 drugs is the repository's extrapolation, and −$500B is not
a CBO score of anything"). The 25.7% it currently reports is the product of two
errors pointing opposite ways: a per-drug rate 2.4× too high, applied to
molecules drawn from the top of the spending ladder rather than its tail. Fixing
either alone makes the row worse. Fixing both is what a bottom-up model of this
policy says, and the check is not the −$500B: it is CBO's **~$100B over ten
years for the negotiation program itself**. Under the rebuilt path, current law's
own cumulative schedule scores about **$74B over 2026-2031** and about **$134B
over 2026-2034** — the right side of CBO's number, on a policy CBO actually
scored. A model that says adding 30 molecules a year to the tail of the ladder
is worth five times the whole existing program is not describing this policy.

### 4.4 Aggregates

| Tier | Before | Expected after |
|---|---:|---:|
| Pharma family (3) | 236.9% | ≈ 229% |
| 14-row sectoral | 81.0% | ≈ 79% |
| 26-row reconstruction | 61.8% | ≈ 61% |
| Tier 1 out-of-sample (26) | 31.0% | **unchanged** |
| Leave-one-out (18) | 28.4% | **unchanged** |
| Calibrated fitted (28) | 2.0% | **unchanged** |

**The aggregates barely move, and the lane says so in advance.** Two rows moving
in opposite directions cancel: reference pricing sheds about 85 points of error
mass and negotiation adds about 62. A lane that reported "sectoral 81.0% → 79%"
as its result would be claiming almost nothing; the result is the four
mechanisms, and the two findings in §2.2.

### 4.5 What would falsify the lane

- Any row outside the pharma family moving at all. The diff is confined to
  `fiscal_model/pharma.py`, its data file, its tests and this file.
- Tier 1, the fitted tier or leave-one-out moving by any amount. None contains a
  pharma case.
- The insulin row moving. Nothing in §2 touches its channel.
- The rebuilt negotiation path scoring current law's own schedule *below* $50B or
  *above* $200B over ten years — either would mean the ladder or the saving rate
  is wrong, not that the policy is small.

## 5. Outturn

*Appended 2026-09-05, after the code. Numbers from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix` and
`python scripts/run_validation_dashboard.py` on the finished branch. Main did
not move under the lane, so §1's baseline is the one these are measured
against.*

**The four mechanisms landed. The prediction did not, and it missed in the
direction the lane had ruled out in advance: every aggregate got *worse*, not
better.** The two rows moved as §4.2 said they would in kind — reference pricing
shedding error from the coverage restriction, negotiation gaining a great deal
of it from the ladder — but a fifth change nobody pre-registered was larger than
the three that were, and it pushed reference pricing past where it started.

### 5.1 The three rows

| Row | Target | Before | §4.2 predicted | **After** | Err before | Err §4.2 | **Err after** |
|---|--:|--:|--:|--:|--:|--:|--:|
| `universal_insulin_cap` | +$11.4B | +$7.0B | unchanged | **+$7.0B** | 39.0% | 39.0% | **39.0%** |
| `international_reference_pricing` | −$100.0B | −$746.2B | ≈ −$660B | **−$801.0B** | 646.2% | ≈560% | **701.0%** |
| `expand_drug_negotiation` | −$500.0B | −$371.5B | ≈ −$64B | **−$33.5B** | 25.7% | ≈87% | **93.3%** |

### 5.2 Aggregates

| Tier | Before | §4.4 predicted | **After** |
|---|--:|--:|--:|
| Pharma family (3) | 236.9% | ≈229% | **277.8%** |
| 14-row sectoral | 81.0% | ≈79% | **89.8%** |
| 26-row reconstruction | 61.8% / 38.0% | ≈61% | **66.5% / 41.6%** |
| Tier 1 out-of-sample (26) | 31.0% / 15.1%, 13/26, 19/26 | unchanged | **31.0% / 15.1%, 13/26, 19/26** |
| Leave-one-out (18) | 28.4% / 16.5%, 9/18 | unchanged | **28.4% / 16.5%, 9/18** |
| Calibrated fitted (28) | 2.0%, 28/28 within 15% | unchanged | **2.0%, 28/28** |

No row changed tier, so every population above is constant and the before/after
figures are directly comparable. There is no composition term in this lane.

### 5.3 The falsification tests of §4.5

| Test | Result |
|---|---|
| Any row outside the pharma family moves | **Did not fire.** Reconstruction error mass 1,607.1 → 1,729.5, **+122.4**; pharma mass 710.9 → 833.3, **+122.4**. The two deltas are equal to the last digit, so the other 23 rows are identical. The sectoral mass moves by the same 122.4. |
| Tier 1, the fitted tier or LOO moves | **Did not fire.** All three identical, including every per-module LOO mean and the whole donor matrix. |
| The insulin row moves | **Did not fire.** +$7.0B before and after, to the cent. |
| Current law's own schedule scores outside $50B–$200B over ten years | **Did not fire.** **$74.1B over 2026-2031** and **$134.4B over 2026-2034**, against §4.3's ≈$74B and ≈$134B. |

### 5.4 The federal share, as built

§4.1's hand computation and the code agree to four decimal places:

| Channel | §4.1 | Built | 2023 aggregate it replaces |
|---|--:|--:|--:|
| Direct subsidy | 0.3727 | **0.37269** | 0.033 |
| Reinsurance | 0.1047 | **0.10470** | 0.431 |
| Low-income subsidy | 0.2986 | **0.29864** | 0.299 |
| **Federal total** | **0.7760** | **0.77603** | *0.7626* |

The redesign moves 33 cents of every program dollar out of reinsurance and 34
into the direct subsidy, and changes the federal total by 1.3pp. That is the
finding §2.1 predicted, and it is a finding about *which* channel bears a drug
policy, not about how much the Treasury bears in total.

### 5.5 The spending ladder

`negotiation_spending_ladder()` returns scale 16.614, exponent 0.6316, and
reproduces all three published cycles:

| Cycle | Mean rank | CMS per molecule | Fitted | Residual |
|---|--:|--:|--:|--:|
| IPAY 2026 (10 drugs, $56.2B) | 5.5 | $5.620B | $5.660B | +0.71% |
| IPAY 2027 (15 drugs, $41B) | 18.0 | $2.733B | $2.677B | −2.08% |
| IPAY 2028 (15 drugs, $27B) | 33.0 | $1.800B | $1.825B | +1.40% |

Two parameters, three points, no free constant left, and a fit through three
points with no standard error worth quoting — which is said in the docstring
rather than dressed up.

### 5.6 Where the pre-registration was wrong

**One omission, and it is the whole of the aggregate miss.** §4.2 predicted
reference pricing at −746.2 × 0.871 × 0.776/0.763 = **−$660.9B**. Decomposed on
the finished branch, applying each change in turn:

| Step | Score | Δ |
|---|--:|--:|
| Before (L7) | −$746.2B | |
| + RAND coverage, 0.87090 | −$649.8B | **+$96.3B** |
| + three-channel federal share | −$658.1B | −$8.3B |
| *(§4.2's prediction stops here: −$660.9B by hand, −$658.1B in code)* | | |
| + Part D gross base, $220B → $281B | −$794.4B | **−$136.3B** |
| + Part B base, $55B → $54B | −$791.3B | +$3.0B |
| + CBO's H.R. 3 availability response, 5% → 3.83% | **−$801.0B** | −$9.7B |

**The two pre-registered mechanisms landed within $3B of the pre-registered
figure.** What §4.2 did not anticipate is that this lane's *own* negotiation
work would condemn a constant the reference-pricing leg also reads.
`medicare_part_d_gross_spending_billions = 220.0` was unsourced, and the ladder
built in §2.2 contradicts it outright: current law's 160 cumulative selections
carry **$256.8B** of gross Part D spending by 2034, which does not fit inside a
$220B total. CMS's own sentence — $56.2B is "about 20 percent of total Part D
gross spending in 2023" — puts the total at **$281B**, and the second cycle's
"$41 billion ... or about 14%" independently implies $293B over a later window.
The re-source is therefore forced by the lane's mechanism rather than chosen,
and `test_the_negotiated_set_never_exceeds_total_part_d_gross_spending` pins the
contradiction so it cannot come back.

**The alternative was to keep an unsourced number because it flattered the
prediction, and that is the thing the pre-registration protocol exists to stop.**
The lane took the $281B and reports the miss.

**A second, smaller slip:** §4.2 predicted the negotiation row at ≈−$64B and it
came in at −$33.5B. The hand calculation ran the expansion across the whole
window; the code cannot, because an expansion of the *annual selection cap* has
nothing to raise until 2029, the first year that cap governs — before then the
statute names the count outright: 10, then up to 15, then up to 15. So the
expansion bites in 6 of the 10 years, not 10.

### 5.7 Findings

**1 — "The federal share" was a weight for a benefit that no longer exists, and
the error is in the composition, not the level.** The 0.763 aggregate was 2023,
when Medicare's reinsurance covered 80 percent of catastrophic-phase cost and
was 43 cents of every program dollar. Under the 2025 redesign it is 10 cents,
and the direct subsidy has gone from 3 cents to 37. The federal total barely
moves (0.763 → 0.776) because the IRA's 6 percent cap on the base beneficiary
premium raises the direct subsidy by almost exactly what reinsurance loses. A
module that only ever needs the total would have been right by accident; one
that ever needs to know *which* channel — a reinsurance-only reform, a
direct-subsidy reform, an LIS reform — was carrying a 13× error on the direct
subsidy and a 4× error on reinsurance.

**2 — The $237B was never a negotiation score, and dividing it by a drug count
compounded a second error.** $237B is CBO's score of the IRA's entire
drug-pricing title: negotiation ($98.5B), inflation rebates ($63.2B), the Part D
redesign and premium stabilisation. The negotiation program alone is about
**$100B over ten years** and **$3.7B in year one** (CBO, quoted by the Secretary
of HHS in CMS's 15 August 2024 release). The old identity divided the title
total by the negotiation program's drug count — a per-molecule rate roughly
**2.4× too high** — and then applied it to molecules drawn from the *top* of the
spending ladder rather than its tail. The two errors pointed opposite ways and
their product read 25.7% against −$500B. Fixing either alone makes the row
worse; fixing both makes it much worse, and that is what a bottom-up model of
this policy says.

**3 — The check that means something is not the −$500B.** Run over current law's
own cumulative schedule, the rebuilt identity gives **$74.1B over 2026-2031**
against CBO's ~$98.5B for the same program — a quarter low — and **$134.4B over
2026-2034**. That is a policy CBO actually scored, and the residual has a named
direction: the ladder's rank-size curve is a smooth fit through three block
means, so summing it over ranks 1-10 gives $71.3B where CMS reports $56.2B
(Jensen's inequality on a convex curve), which biases the level *up*, while
holding a 2023 spending level flat across a decade biases it *down*. Neither was
adjusted. −$500B, meanwhile, is provenance `model_estimate`, and a model that
says adding 30 molecules a year to the tail of the ladder is worth five times
the whole existing program is not describing this policy.

**4 — A rank-size ladder is the only thing that can price an expansion, and CMS
has published one for three years without anyone reading it as one.** Three
selection cycles at $5.62B, $2.73B and $1.80B of gross spending per molecule are
a measured concentration curve with an exponent of 0.63. Under it the marginal
molecule at rank 200 is worth about a fifth of the marginal molecule at rank 10.
The old identity was linear in drug count and could not see that;
`test_negotiation_savings_are_concave_in_the_number_of_molecules` now pins that
each further block of twenty buys less than the last.

**5 — RAND's index does not reach the whole brand book, and RAND says so.** The
combined 33-country comparison is computed on presentations sold in both
markets, which are 90.2 percent of US sales; within them brand-name originators
are 84 percent of sales against 87 percent across all US sales. 0.902 × 0.84 /
0.87 = **87.1 percent** — RAND's own warning that "the presentations contributing
to bilateral comparisons accounted for smaller shares of brand-name originator
... sales" turned into arithmetic. Worth $96.3B on this row, and the only one of
the lane's four mechanisms that moves it *toward* its target.

**6 — CBO has published two drug-availability figures and they differ by an
order of magnitude, so one constant could never have stood for both.** The
module carried an unsourced flat `innovation_offset_pct = 0.05`. Under the
enacted IRA, CBO expects about **1** fewer drug introduced over 2023-2032 out of
about 1,300 over thirty years — **0.23 percent** for a decade. Under H.R. 3's cap
at 120 percent of the average international market price, CBO expects **8 to 15**
fewer out of about 300 — **3.83 percent** at the midpoint of CBO's own range over
CBO's own denominator. The 5 percent sat between them and was attached to
neither. Each channel now carries the figure CBO published for the policy that
channel scores. Both were found quoted verbatim in accessible sources (CRS
R47872 and KFF for the IRA figure, Knowledge Ecology International's
reproduction of the Pallone letter for H.R. 3), because `cbo.gov` returns HTTP
403 to every non-browser client.

**7 — The utilisation response was looked for and not added, which §2.3 said in
advance was a permitted outcome.** Three answers, two of them pointing away from
adding a term. CBO's own negotiation model appears to assume no price response
at all — the working paper behind the H.R. 3 estimate reportedly says "because
utilization of a drug does not vary with its price in that model, the
negotiation can be expressed by accounting only for the per-beneficiary net
benefit of the drug" — but that sentence could not be confirmed against the
document, so it is recorded as a lead and not cited as a source. The one
*published* CBO utilisation parameter runs the other way and against a base this
module does not have: a 1 percent rise in prescriptions filled cuts Medicare's
spending on **other medical services** by about 0.2 percent (publication 43741).
And no CBO price elasticity of demand for prescription drugs could be sourced at
all. So no term was invented. This is the largest known omission in the
reference-pricing leg and it is now stated in the module docstring, the
validation record and here.

**8 — The `oop_cap` lever came back, on the condition L7 set for it.** L7 deleted
the field outright rather than leave a control that changed nothing, and wrote
the condition for restoring it: "adding the mechanism means adding a sourced
shift, not restoring the field." ASPE is that source — **$7.2B** of Part D
out-of-pocket savings in 2025 for the 11.3 million enrollees who reach the
$2,000 cap, against **$14.3B** the same enrollees would otherwise have paid. Two
published points, so the lever interpolates between them and **refuses to
extrapolate above $2,000**, where it has no measurement. At the IRA's own $2,000
it gives about $54B over ten years against CBO's +$30B for the whole redesign —
above it, and it should be, because CBO's $30B is a *net* in which the cap's
cost is offset by the reinsurance cut and the manufacturer discount program,
neither of which this lever contains.

### 5.8 Shipped presets, and the caption that ships with them

Decision 6: three of the four moved, so the explanation ships in the same PR.

| Preset | Before | **After** |
|---|--:|--:|
| 💊 Expand Drug Negotiation | −$371.5B | **−$33.5B** |
| 💊 Universal Insulin Cap | +$7.0B | **+$7.0B** |
| 💊 International Reference Pricing | −$746.2B | **−$801.0B** |
| 💊 Comprehensive Drug Reform | −$573.5B | **−$150.5B** |

`pharma_channels_caption` renders one line under any drug-pricing headline,
following `tariff_net_caption`'s pattern and computed from
`part_d_federal_channels()` and `current_law_negotiated_molecules()` so it
cannot drift from the figure above it. It is assembled from clauses the policy
actually uses: a cost-sharing cap gets **no** federal-channel clause, because it
reduces no drug cost — the same line the module itself draws between the insulin
channel's statutory 74.5 percent and the three channels.

### 5.9 What the lane did not do

- **No utilisation response.** Finding 7. The single largest known omission in
  the reference-pricing leg.
- **No re-split of the 2023 blocks for the redesign's cost-sharing shift.** The
  $2,000 cap also moves cost sharing onto plans, which raises the basic-benefit
  block and shrinks the 12.8 percent cost-sharing block. MedPAC publishes no
  post-redesign split, so the 2023 blocks are held. The omission biases the
  federal share *down*, since cost sharing is the one block with no federal
  channel in it.
- **No Part B / Part D split of the ladder.** CMS's third cycle covers both
  parts while the first two are Part D alone, and no published split exists.
- **Nothing grows.** ASPE's $734M (insulin) and $7.2B (out-of-pocket cap), CMS's
  $56.2B and MedPAC's 2023 levels are all single-year figures held flat across a
  ten-year window. Every one of them biases the score toward zero.
- **The exclusivity delay's composition effect is still not priced.** Under a
  statutory cap on selections *per year* the 7/11-year eligibility bar changes
  which molecules are negotiated, not how many, and no published figure prices
  that shift. The flag now governs only whether an expansion beyond the annual
  cap is feasible at all.
- **No target moved.** −$500B and −$100B are unchanged, and neither is in
  `target_revisions.py`. The negotiation row getting worse against a
  `model_estimate` target is the pre-registered result, not a regression to be
  fixed. Whether −$500B should be retired for want of a document is an owner
  decision on the ledger's own terms, and it is a carry-over.
- **The insulin preset's own description still reads "Estimated: −$15B/10yr".**
  That is the *superseded* target, revised to CBO 57957's +$11.4B by PR #90, and
  it carries the wrong sign. It is a preset label rather than a score — L8's
  precedent is that labels quote the official figure, not the model's — but this
  label quotes an official figure the repository has already retired. Left for
  the owner, because changing preset labels is a UX change with its own blast
  radius, and it is on the carry-over list.
- **Docs were not synced.** `docs/VALIDATION.md`, `README.md` and `CLAUDE.md`
  still carry the pre-lane sectoral and reconstruction means. Other Wave 4 lanes
  are in flight against the same aggregates; the owner's docs pass takes them
  together after the merge order is fixed.
