# The workbench: review of the November design brief, and the web plan

*Written 2026-11-04 against `main` @ `b01edc3`. Source: an outside product and design review of the
live site ("Fiscal Policy Calculator: a path to 9.5/10", 4 November 2026), which Laurence forwarded.
This document sits beside [PRIORITY5_AND_CHARTS.md](PRIORITY5_AND_CHARTS.md). That plan owns the
modelling lanes (B1 to B8) and the proposal charts (C1 to C6); this one owns the user journey. Where
the two touch the same file the order is fixed in the last section, so the lanes do not collide.*

## Part A: what the brief gets right, and what it gets wrong for this site

The brief's central claim is that the site has more analytical substance than its first screen shows,
and that its three tools (Explore, Build, Tailor) read as separate destinations when they are steps of
one task. I agree with both. It recommends keeping the visual identity (warm paper, Newsreader serif,
Libre Franklin for data, restrained teal and rust, fine rules), and so does this plan. The site already
uses a sans face with tabular numerals for figures, which is the brief's typography recommendation, so
the work there is hierarchy and density on working pages, not a new type system.

### A1. The five trust issues: all five were real

| Brief's finding | What the code did | Fix (PR #230) |
|---|---|---|
| Corporate 28%: intro says CBO, calibration text says Treasury | The preset label and description in `fiscal_model/app_data.py` said "CBO"; the score record and the scorecard row say U.S. Treasury (FY2025 Green Book, −$1,347B). The CTC-2021 label said CBO for a JCT figure. | Labels and descriptions renamed (ids are frozen, so no link breaks). New test `tests/test_preset_source_labels.py` fails if a label or description names a producer other than the one in `CBO_SCORE_MAP`. |
| Stated gap 4.0%, implied 2.7% | The 4.0% is the scorecard row: the model run on Treasury's FY2025-2034 window (−$1,292.6B). The page shows the FY2026-2035 score (−$1,310.9B), and the sentence called the scorecard's error "this estimate". | `own_row_model_billions` added to the credibility record (Python, API, export). `web/lib/scoreparts.ts` `checkedSentence` says which figure the error belongs to whenever the two gaps differ by more than half a point. Tested on the corporate file. |
| Macro feedback sign | `YearTable` printed `dynamic_feedback` in the revenue convention between two deficit-convention columns, so a recession that costs revenue showed as a negative (deficit-reducing) number. | Column negated and relabelled "Macro feedback, deficit". Test: conventional + macro + debt service = dynamic for every year. |
| H.Con.Res. 14 links to `house-bill/14` | `bill_tracker/ingestor.py` built every URL as `{chamber}-bill/{number}`: 1,740 of 11,384 rows (every resolution) linked to a different measure. | `congress_gov_url()` maps the measure type to congress.gov's path; the export rebuilds every row's URL from type and number, so the stored rows are corrected without a database migration. |
| "High confidence" beside a demonstration figure | The confidence is the language model's confidence in its mapping of the text, not the reliability of the dollar figure. | Column and labels now read "mapping confidence", with a sentence saying a high-confidence reading can still be far off. |

### A2. Recommendations worth doing

1. **One estimate identity on every number** (brief §3). This is the brief's best point, and it is
   the site's own rule (never collapse the tiers) carried into the interface. Every figure should
   say who produced it, the window, the baseline, and which tier it sits in.
2. **Connect the tools** (brief §2): Add to package, Compare and Adjust on a proposal page, carrying
   the policy id. Build ids are already the preset ids, so this is mostly links.
3. **A compare view** with small multiples on a common scale (brief §2, §4). Nothing on the site
   does this today.
4. **Build as the flagship** (brief §2): a persistent summary with the selected policies, their
   contributions, the target and what remains, the basis of the total and its main exclusion, and
   Undo when a choice replaces another.
5. **A working first screen** (brief §1), built from the compare component and an out-of-sample row,
   so it obeys C1's rule that no fitted row appears without the word "fitted".
6. **Density on working pages** (brief §4): smaller h1 and shorter preamble on Explore, Build,
   Tailor and proposal pages; the editorial scale stays on Home, Methods and About.
7. **Exports that carry their caveats** (brief §6): the PNG and CSV carry the estimate identity, and
   Build's carry "sum of standalone published scores; interactions not measured".
8. **A "what changed" page** (brief §7), but only from data the nightly export can already diff.

### A3. Where the brief conflicts with the scorer's design, or is premature

- **An "estimate basis" switch on Build's total.** Build prices a package at published list prices on
  purpose: those are the figures a reader can cite, and the calculator's own scores sit in mixed tiers
  (fitted, out of sample, reconstruction). A switch that sums model scores would produce one number
  out of several tiers, which the project's rules forbid. The honest second number is a jointly
  modelled package, and that is B7 with C6's two bars. Until B7 ships, show the calculator's score as
  a column beside each row (Build already flags gaps over 25%) and do not total it.
- **Calling a scorecard gap a confidence interval**, or showing a band where a class has fewer than
  five rows. The brief warns against the first; C4 already rules on the second. No new lane may add
  a band.
- **Renaming "FRB/US-Lite (Federal Reserve calibrated)".** Worth doing, since it reads as an agency
  product, but the string is pinned in tests and B6 rewrites the dynamic tier anyway. It goes into B6
  with the one-line disclosure the brief asks for (demand channel only, no long-run supply channel).
- **Accounts, server-side saved scenarios, alerts, email digests, drag-and-drop dashboards.** The site
  is a static export with a scoring API and no user store. Saved work lives in the URL (and
  optionally `localStorage` for a "recent" list). Alerts wait until "what changed" exists and has run
  for a few weeks.
- **A usability study with 8 to 12 people and a five-second test.** Useful, and Laurence's students
  are the obvious panel, but it is his call and not a code lane. The acceptance criteria below are
  written so a study could check them.
- **An analytics funnel.** Optional. If added, use Vercel Web Analytics custom events with no query
  text and no scenario parameters, and say so on `/privacy`.

## Part B: web lanes, in order

Each lane is one PR against `web/` (plus `scripts/export_static.py` where noted). No lane moves a
score, so none needs a pre-registration; each passes
`cd web && npm run typecheck && npm test && npm run layout`, adds a test in `web/lib/*.test.ts` for
every new pure function, and adds layout-check cases for any new page at phone and desktop widths.
Copy follows Laurence's voice (first person for his choices, full sentences, no slogans).

### U1. Estimate identity (first; everything else uses it)

- New `web/lib/identity.ts`: `estimateIdentity(result, kind)` returns
  `{ producer, kind, window, baseline, tier, tierLabel, limitation }`, where `kind` is one of
  `model` (this calculator, conventional), `model-dynamic`, `published` (with the producer from
  `cbo_source`), or `package-sum`. `tier` comes from `credibility.own_row_tier` or, where there is no
  own row, from the class band (`out_of_sample` with n, or `none`).
- New `web/components/EstimateTag.tsx`: one line in the `.tag` style, e.g. "This calculator ·
  conventional · FY2026-2035 · CBO Feb 2026 baseline · calibrated reference". A short form for table
  cells (e.g. "calc." / "Treasury") with the long form in `title` and a visually hidden span.
- Use it on: the proposal headline (`explore/[id]/page.tsx`, both stages), Tailor's result, each Build
  row's published figure and calculator figure, and the Explore list's two columns (as a header note).
- Acceptance: every money figure on those four pages sits under or beside an `EstimateTag` (layout
  check asserts one per `.stage .v`); a test asserts that a fitted row's tag contains "calibrated"
  and never "out of sample"; the corporate 28% page names Treasury, not CBO.

### U2. Working-page density and navigation

- `globals.css`: a `.work` page class (set by the four working pages) with h1 at
  `clamp(30px, 4.5vw, 40px)`, a one-sentence lede, and a 1,200px max width for tables and charts while
  prose stays at its current measure. Home, Methods and About keep the current scale.
- `lib/nav.ts`: rename the first group "Policies" with Explore, Compare (from U4), Build and Tailor;
  move Methods and About into a quieter utility row in `SiteChrome.tsx`. Keep the phone menu reading
  the same list.
- Explore: the category headings become sticky table section rows rather than h2 blocks, so a desktop
  viewport shows at least 12 proposals on first load.
- Acceptance: on a 1440×900 desktop the first proposal's headline figure is above the fold on a
  proposal page and at least 12 rows show on Explore (layout check measures both); no prose block is
  wider than 75 characters; `nav.test.ts` still finds every page in the sitemap.

### U3. Proposal actions

- A row of actions under the proposal headline: **Add to package** (`/build?policies=<id>`, merged
  with any package already in `localStorage`), **Compare** (`/compare?ids=<id>`), **Adjust in
  Tailor** (only where `lib/tailor.ts` can express the preset: income rate and corporate rate shapes;
  otherwise omitted, not disabled), and **Share** (scrolls to the export controls).
- Build reads `?add=<id>` and applies `choose()`, so the exclusive-group rules still hold; when the
  added policy replaces another, it says so (see U5's notice).
- Acceptance: test that `adjustable(presetId)` is true only for presets Tailor can reproduce to
  within rounding (test against the preset file's ten-year figure); following Add to package twice
  never duplicates a row.

### U4. Compare

- New `web/app/compare/page.tsx` and `web/components/Compare.tsx`: up to three proposals from
  `?ids=a,b,c`, picked from a search box. For each, a small multiple of the annual deficit effect on
  one shared y-axis (`lib/chartaxis.ts` already computes common scales), the ten-year conventional
  figure with its `EstimateTag`, the published figure with its producer, and the tier.
- A difference line only when exactly two are compared and they share a window and baseline;
  otherwise the page says why it does not draw one.
- A "Compare" checkbox on Explore rows that builds the link.
- Acceptance: shared axis (test: the computed domain covers every series); a pair on different
  windows shows the explanation and no difference line (test); the page works with no JavaScript for
  ids in the URL (server-rendered from `site_data`), and at 390px wide the multiples stack.

### U5. Build summary panel (before Wave 4 opens B7 and C6)

- `PackageBuilder.tsx` splits into the list and a `PackageSummary.tsx` that stays visible (sticky on
  desktop, a collapsible bottom sheet on phones). It shows: the selected policies with aligned
  contribution bars on one scale; the total labelled "Sum of standalone published scores"; the
  philosophy's target and the remaining gap, in dollars and as a share; and the exclusion sentence
  ("Interactions between these policies are not measured") directly under the total.
- When `choose()` drops a policy, a polite live-region notice names both ("Replaced the 15% corporate
  rate with 28%; these are alternatives") with an Undo button that restores the previous selection.
- Philosophy presets show the short result first ("12 policies, 74% of the target") and keep their
  explanation and the tag definitions behind a "Why these choices?" disclosure.
- Leave a slot for C6: the summary renders a `secondTotal` prop when present, so B7 adds the jointly
  scored bar without reworking the panel.
- Acceptance: `lib/package.ts` gains `replacedBy(rows, before, after)` and `undo` tests; the
  exclusion sentence is inside the same DOM block as the total (layout check); on a phone the total
  and remaining gap stay visible while scrolling the list.

### U6. A working first screen

- Home keeps its headline but the lede shrinks to two sentences, followed by a live compare of two
  proposals (reusing U4's component, server-rendered) with one control: a select that swaps the
  second proposal. Primary action "Compare policies", secondary "Build a package".
- Use out-of-sample rows only, labelled as such (C1's rule); not the corporate presets, whose own row
  is fitted.
- The stats strip becomes a one-line trust strip under the example ("44 held-out benchmark cases;
  accuracy varies by policy type", with a link to Methods), with the figure read from `evidence.json`
  so it cannot go stale.
- Three question-led starting points replace the directory ("Which policies reduce the deficit?",
  "What would it take to pay for a proposal?", "Which Social Security changes close the gap?"), each
  linking to a populated Explore filter, Build with a target, or the Social Security page.
- Acceptance: at 1440×900 a chart and a scored figure are above the fold; `home.test.ts` asserts no
  fitted row and that the trust-strip count equals `evidence.json`.

### U7. Exports that carry their caveats (after Cursor's PNG follow-up merges)

- Extend `ChartActions` and `lib/chartpng.ts` (Cursor's follow-up owns them until it merges) so the
  PNG footer prints the `EstimateTag` long form, and Build gets PNG and CSV of the package with the
  "sum of standalone published scores; interactions not measured" line in both.
- Every share link carries `v=<manifest export date>`. When a link's `v` differs from the current
  manifest, the page says the numbers have been recomputed since the link was made and links to
  "what changed" (U8). Classroom's frozen links keep their stricter refusal.
- A copyable citation block on proposal, compare and Build pages, generated from the same identity.
- Acceptance: PNG test asserts the footer contains window, baseline and producer; Build's CSV first
  comment line is the exclusion sentence; a link with an old `v` shows the notice (test on the pure
  function).

### U8. What changed (later)

- `scripts/export_static.py` writes `site_data/changes.json` by comparing the new export with the
  previous commit's: preset scores that moved by more than 0.5% (with the old and new figures), new
  CBO estimates in the tracker, and a baseline vintage change. It separates a data refresh from a
  score change and never records user scenarios.
- New `/changes` page lists the last 30 days, newest first, each item linking to its page.
- Acceptance: a test export with one moved preset and one new CBO estimate produces exactly two
  items; a float-jitter re-export (last-digit changes) produces none.

### U9. Accessibility and phone pass (Laurence-led, can start any time)

- Keyboard path through Explore → proposal → Add to package → Build → Share; focus lands on the
  notice after a replacement; every chart has a table or text equivalent; primary controls are at
  least 44px tall on phones. A short task study with students if Laurence wants one.

## Part C: order, and how it avoids Cursor's lanes

Cursor's open and coming web work, from `PRIORITY5_AND_CHARTS.md` and the round 3 instructions:
the PNG follow-up (`ChartActions.tsx`, `lib/chartpng.ts`) and the C3 scatter (`/methods`) in Wave 2;
B6 and its waterfall (proposal page, `EconomicEffects.tsx`, `YearTable`) in Wave 3; B7 with C6
(`PackageBuilder.tsx`) and C4 (`YearChart.tsx`) in Wave 4.

| When | Workbench lanes | Avoids |
|---|---|---|
| Now, beside Wave 2 | **U1**, **U2**, then **U3** | Does not touch `ChartActions`, `chartpng` or `/methods` |
| Still Wave 2 | **U4** (new files), **U5** | U5 must merge before Wave 4 opens B7/C6 on `PackageBuilder` |
| After the PNG follow-up merges | **U7** | Takes over `ChartActions` only once Cursor's PR is in |
| After U4 | **U6** | Home was last changed by C1; U6 keeps C1's rule |
| Before B6 opens (Wave 3) | U1 and U3 merged | B6 edits the proposal page and `YearTable` |
| Wave 3 or later | **U8** | Touches `export_static.py`; land it between modelling PRs, not during one |

Lanes U1 to U5 are the brief's "one excellent vertical slice" (proposal, comparison, package,
share). U6 to U8 broaden it. Whether that reaches the brief's 9.5 is an empirical question; the
acceptance lines above are the parts that can be checked without a study.
