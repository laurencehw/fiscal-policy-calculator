# Wireframe text extraction (from Fiscal Calculator Redesign.pdf)

## Page 1: 01-ask-home-desktop

Fiscal Policy Calculator
Ask
Build
Tailor
Explore
More
CBO Feb 2026 · SOI 2023
1
Ask a public-finance question
Answers grounded in this calculator’s validated scoring engine plus CBO, JCT, PWBM, TPC, SSA
and FRED — every claim cited.
e.g. What did extending the TCJA cost, and who benefits?
2
What does CBO project for the 10-year deficit?
Compare PWBM and CBO on a corporate-rate increase
When is the Social Security trust fund depleted?
Score a 25% corporate rate
Explain dynamic scoring
ANSWER · STREAMS AS IT ARRIVES
SOURCES (3)
CBO Outlook, Feb 2026
Treasury GB, Mar 2024
PWBM, Apr 2021
3
Build a package
Pick from 45+ scored policies and close the gap to a deficit target.
Live totals as you check options.
Open Build
Tailor a policy
Set the rate, threshold and timing yourself. Scored with tier-
labeled confidence and a sensitivity band.
Open Tailor
4
WORKED EXAMPLES — PREFILL THE QUESTION BOX
ENACTED · P.L. 119-21
What did extending the TCJA cost?
+$4.6T (CBO, May 2024)
PROPOSAL
Restore the 39.6% top rate?
 $252B (Treasury)
PROPOSAL
How much would a 28% corporate rate
raise?
 $1.35T (Treasury)
PROPOSAL
Could a 10% tariff replace income taxes?
 $2.0T (TPC)
5


## Page 2: 02-build

Fiscal Policy Calculator
Ask
Build
Tailor
Explore
More
CBO Feb 2026 · SOI 2023
Build a package
Check policies to include; totals update as you go. List prices — interactions are not modeled.
Target
% of GDP
$ billions
3.0%
6
Search 45+ scored policies
REVENUE RAISERS — REDUCE THE DEFICIT
Payroll / Social Security
PICK ONE CAP OPTION
Raise cap to cover 90% of wages
 $800B
CBO
Donut hole: tax wages above $250K
 $2.7T
SSA
Eliminate the wage cap entirely
 $3.2T
SSA
7
Corporate (1)
Tax expenditures (5)
Trade / tariffs (5)
TAX CUTS & NEW SPENDING — INCREASE THE DEFICIT
Tax credits (3)
Healthcare (2)
YOUR PACKAGE — STICKY WHILE YOU SCROLL
Baseline deficit
$3,002B/yr
7.4% of GDP
Your package (1 policy)
 $80B/yr
 $800B over 10 years
Adjusted deficit
$2,922B/yr
7.2% of GDP
Remaining gap to 3.0%
$1,710B/yr
more cuts needed
Progress toward target
5%
Waterfall — baseline   policies   adjusted(per-year, 10-yr totals ÷ 10)
TARGET 3.0%
Share link
Download CSV
Copy summary
8
Scored against CBO Feb 2026 baseline · list prices, no interaction effects · overlapping options are mutually exclusive


## Page 3: 03-tailor

Fiscal Policy Calculator
Ask
Build
Tailor
Explore
More
CBO Feb 2026 · SOI 2023
Tailor a policy
Set the parameters yourself; the score carries its confidence tier and sensitivity band.
Start from
Blank
A preset
Policy type
Income
Corporate
Capital gains
Spending
Rate change
+2.0pp
 10
0
+10
Who is affected
Top earners ($400K+)
Duration
10 years
Phase-in
1 year (min 1)
9
Advanced — taxpayers, average income, ETI (0.25). Auto-populated from IRS SOI
2023 when left at zero.
Score this policy
RESULT — SHARED PANEL, SAME COMPONENT AS BUILD & EXPLORE
GENERIC · UNCALIBRATED · ±8%
 $196B
Deficit reduction, 10-year
Roughly $20B per year, about 0.06% of GDP annually. Sensitivity:  $185B to  $207B across ETI 0.15–0.35.
Decomposition — static   behavioral   dynamic   final
No official score exists for this exact policy — nearest validated benchmark: Treasury 39.6% top rate,  $252B (Mar 2024).
Scored against the CBO Feb 2026 baseline · policy status: hypothetical.
Share link
Download CSV
Copy summary
Distribution  
Shown only when inputs change after a run: “Configuration changed — score again to refresh.” Stale results are never displayed as current.
10
Tier language and benchmarks identical to Explore presets · deep sub-tabs (Distribution, Economic Effects, Models, State) open from the result panel


## Page 4: 04-ask-mobile

Fiscal Policy Calculator
FEB 2026
Ask
Build
Tailor
Explore
More
11
Ask a public-finance question
Grounded in the validated scoring engine — every claim cited.
What did extending the TCJA cost?
10-year deficit outlook
SS trust fund depletion
Score a 25% corporate rate
PWBM vs CBO
Build a package
Hit a deficit target from 45+ policies
Tailor a policy
Rate, threshold, timing — tier-labeled score
ENACTED · P.L. 119-21
What did extending the TCJA cost?
+$4.6T (CBO, May 2024)
No drawer, no global sidebar — each page carries its own controls.


## Page 5: 05-ia-map-url-contract

Information architecture — old   new
Every existing surface keeps a home. Nothing is deleted; the entry points change.
TODAY — 5 TABS + GLOBAL SIDEBAR
Global sidebar — Policy Configuration (preset / custom / spending) +
Data Status
Calculator tab — hero, examples, 7 result sub-tabs
Ask tab
Budget Builder tab
Bill Tracker tab
Methodology tab
Classroom Mode (separate page)
NEW — st.navigation(position="top"), REAL URLS
/ask — home · chat + suggestion chips + doorway cards (default
page)
/build — package builder (was Budget Builder)
/tailor — custom policy (was sidebar “define your policy” +
spending form)
/explore — presets + examples (was Calculator tab)
More   — /tracker · /methodology · /classroom
Shared: render_results(result) · result sub-views open from the
result panel · per-page controls (no global sidebar) · Data Status  
compact pill in the top bar
URL CONTRACT
/ask?q=… — prefilled question
/explore?preset=<id>&run=1 — restore + auto-run
/tailor?type=income&rate=2&who=top400k&run=1
legacy ?analysis=…&preset=…&run=1   301-style shim to
/explore


## Page 6: 06-build-start-from-values

Fiscal Policy Calculator
Ask
Build
Tailor
Explore
More
CBO Feb 2026 · SOI 2023
Build a package
Two ways in. Values first, or straight to the policy list — both land on the same checklist and scoreboard.
Start from your values
Start from scratch
PICK A STARTING PHILOSOPHY — OR WRITE YOUR OWN BELOW
Deficit hawk, protect the vulnerable
Get to 3% of GDP, but the adjustment shouldn’t fall on the bottom of
the distribution.
progressive raisers
protects transfers
target 3.0%
Small government
Close the gap on the spending side; leave rates where they are or
lower.
spending cuts first
no new taxes
shrinks state
Growth-first
Broaden bases rather than raise marginal rates; keep investment
incentives intact.
base-broadening
low marginal rates
investment-friendly
Egalitarian
Judge the budget by what it does for the worst-off — raise at the top,
spend at the bottom.
raises at top
expands credits
mixed package
Generational steward
Weigh future cohorts equally; stabilize debt without loading costs
onto the young.
long-run balance
OLG-informed
phased reforms
Archetypes are value language, never party language — and every
one gets a steelman package.
12
OR DESCRIBE YOUR PHILOSOPHY
“I’m worried about the debt but I think the middle class has paid enough. I’d rather fix loopholes than raise rates, and I don’t want to
touch Social Security benefits…”
Translate to a package
13
HOW I READ YOUR PHILOSOPHY — CONTEST ANY OF IT
Redistribution
Strong
Deficit concern
Moderate
Size of government
Neutral
Protected
middle-class rates
SS benefits
That implies 7 pre-selected policies reaching 62% of a 3.0%-of-GDP target — e.g. it
raises the SS cap rather than middle rates because you protected the middle class.
Raise SS cap to 90% of wages
 $800B
Expand NIIT to pass-throughs
 $250B
Eliminate step-up basis
 $500B
+ 4 more — each with a “why this one” note
Load into the checklist
Share
Pre-selects are a starting point, not a verdict — everything stays editable in the checklist,
and the scoreboard shows what your values cost.
14
15
Free text is translated into the value dimensions only — policy selection is deterministic from tags on the policy list, so the same values always produce the same package.
