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

*Appended in the lane's last commit.*
