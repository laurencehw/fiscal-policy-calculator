# HSD / H12 — Sectoral presets: demote to an illustrative group

*Lane of `planning/HIGH_STAKES_ACCURACY.md` §3 H12, Wave D, owner decision ⑨
taken: **demote all five**. Branch `ui/hs-d-h12-illustrative-group`, cut from
`main` @ `994f528`. Sections 1–5 are the **pre-registration** and are committed
before any surface code is opened; §6 is appended after.*

This lane is **presentational**. It is the one Wave D lane that opens no model
module, and its whole claim is that **no number moves**. If a number moves, the
lane has failed — see §4.

---

## 1. The mechanism

### 1.1 What is wrong with the surfaces today

Five presets print a dollar figure on Explore and on Build's checklist beside
forty-seven others, in the same typeface, under the same "Official estimate:"
caption, with nothing on the surface separating them from `tcja-full-extension`
(0.4%) or `ss-donut-250k` (0.0%). Measured on this commit (`scripts/cold_holdout.py`,
`scripts/run_validation_dashboard.py`, and `get_validation_badge` per preset):

| preset id | Explore label | scorecard row | tier | abs error |
|---|---|---|---|--:|
| `drug-negotiation-expand` | 💊 Expand Drug Negotiation (-$500B) | `expand_drug_negotiation` | reconstruction | **93.3%** |
| `drug-reference-pricing` | 💊 International Reference Pricing (-$100B) | `international_reference_pricing` | reconstruction | **701.0%** |
| `insulin-cap-universal` | 💊 Universal Insulin Cap ($11B) | `universal_insulin_cap` | reconstruction | **39.0%** |
| `drug-reform-comprehensive` | 💊 Comprehensive Drug Reform | **none** | no row | — |
| `irs-enforcement-double` | 🔍 Double IRS Enforcement (-$340B) | `double_enforcement` | reconstruction | **82.3%** |

The dashboard's own sub-populations put `Pharma` at **n=3, 277.8% mean, 93.3%
median, 0/3 within 15%** and `Enforcement` at **n=2, 43.5%, 1/2** — the
enforcement pair being `ira_enforcement` at 4.7% and `double_enforcement` at
82.3%, which is why the *pair* mean is not the thing to read and the row is.

Two of the three pharma targets are `provenance="model_estimate"` — the badge
already says so in words ("The target itself is this model's own estimate, not a
published score"), and a **concurrent ledger lane is retiring both**. That lane
and this one are independent and both land: it owns the *target*, this owns the
*surface*. Nothing here may read a hard-coded error figure, precisely so that a
retirement underneath it changes what the surface prints instead of making it
stale. **Every figure this lane renders is read from `get_validation_badge` at
render time.**

`drug-reform-comprehensive` is the awkward one and it is the reason the flag is
declared data rather than derived from the badge: it has no `CBO_SCORE_MAP`
entry, so it has no scorecard row, no badge, and no row in Build's catalog at
all. Deriving "illustrative" from a bad badge would have silently exempted the
one preset in the group with *nothing at all* behind its number.

### 1.2 What the lane does

**One flag, declared once.** `fiscal_model/app_data.py` gains
`HEADLINE_SURFACE_ILLUSTRATIVE = "illustrative"` and a `"headline_surface"` key
carrying it on exactly those five `PRESET_POLICIES` entries, plus a frozen
`ILLUSTRATIVE_PRESET_IDS` and an `is_illustrative(preset)` predicate. **No label
changes** — labels are keys (`preset_ids.PRESET_ID_BY_LABEL`,
`CBO_SCORE_MAP`, `PRESET_POLICY_PACKAGES` members, `_short_display_name` in
`components/cards.py`), and a rename breaks all of them. **No figure changes.**
Each of the five gains one sentence in its `description`.

**Explore.** `_preset_category` returns a fourteenth-plus-one policy area for a
flagged preset, and `_CATEGORY_ORDER` gains it **last**, so the group is a
separate, explicitly labelled, final entry in the "Policy area" selectbox. The
area name itself names the tier. When it is selected, `policy_input_tax` prints
the group note above the proposal picker, and the existing badge caption —
unchanged — prints that preset's distance from its published figure underneath.
For `drug-reform-comprehensive`, which has no badge, a fallback line says so.

**Build.** `build_catalog` assigns flagged presets the same illustrative area,
and `_AREA_ORDER` gains it last, so `_area_sort_key` sorts the section to the
bottom of whichever directional section a row falls in. The expander's label
names the tier; the note renders inside it; each row carries its own error
caption under the checkbox, read from the badge. The section is **collapsed by
default** — it stays expanded only when a search matches it or something in it
is selected, which is the rule every other area follows and is what keeps a
selected illustrative policy from becoming invisible (§4).

**Still selectable, still linkable.** Nothing is removed from `PRESET_POLICIES`,
from `CBO_SCORE_MAP`, from `preset_ids`, or from Build's catalog.
`?preset=<id>` resolves, `/build?policies=<id>` resolves, and a frozen
assignment link naming one still scores.

**Packages.** `PRESET_POLICY_PACKAGES["Drug Pricing + Enforcement"]` is the one
package containing a demoted preset (`💊 Expand Drug Negotiation (-$500B)`); its
`description` gains one sentence saying so. Build has **no default or "quick"
package** — the checklist starts empty — so "excluded from any default package"
is vacuous there and nothing is excluded.

### 1.3 What the lane deliberately does not do

The **values composer** is a different surface and is left alone. Measured
before any edit (`scratchpad/h12/composer_probe.py`): all **five** archetypes —
`deficit-hawk`, `egalitarian`, `generational-steward`, `growth-first`,
`small-government` — select `irs-enforcement-double` into their twelve-policy
package, and none selects any of the four pharma presets. Excluding it would
change five package totals, which is exactly the thing §3 forbids this lane from
doing. It is recorded as a **carry-over** with the measurement attached, not
taken by implication.

Ask's `list_presets` tool (`fiscal_model/assistant/tools.py`) is likewise a
carry-over: whether the assistant should mark these five is a decision about the
blue tier's citation discipline, and it is out of this lane's file list.

No scorecard row is touched, no badge map entry is touched, no API response
shape changes. **"No removing a case to go green"** (CLAUDE.md): all five keep
every row they have, at every error they have.

---

## 2. Files

Owned and edited:

- `fiscal_model/app_data.py` — the flag, the constants, the predicate, one
  sentence per description on the five.
- `app_pages/explore.py` — read; no change expected (it delegates the picker).
- `fiscal_model/ui/tabs/deficit_target.py` — illustrative area, order, expander
  label, per-row error caption.
- `fiscal_model/ui/preset_validation.py` — an illustrative caption variant only.
- `fiscal_model/ui/policy_packages.py` — one sentence on one description.
- `tests/` — the new assertions in §4.

Edited and **outside the lane's stated list**, declared here rather than
discovered later:

- `fiscal_model/ui/policy_input_presets.py` and
  `fiscal_model/ui/policy_input_tax.py` — Explore's preset picker is not in
  `app_pages/explore.py`; that module is a router that delegates to
  `render_score_surface` → `render_policy_inputs` → `render_tax_policy_inputs`.
  The category map and the picker live in these two. No sibling lane owns them
  (R1 owns `baseline.py`/`constants.py`, the ledger lane owns `validation/*`,
  H7 owns the tax-expenditure module).

`components/cards.py` is **not** edited: the Ask home's four doorway/worked
example cards are `tcja`, `biden400k`, `corp28`, `tariff10`, none of the five.

---

## 3. Expected outturn — every one of these is zero

Pre-registered before the first edit. Each is a `cmp` against a file captured on
`994f528` in `scratchpad/h12/`.

1. `scripts/cold_holdout.py --json` — **byte-identical**. 26 rows, 15.0% mean.
2. `scripts/run_validation_dashboard.py` — **byte-identical**, including the
   `Pharma 3 277.8%` and `Enforcement 2 43.5%` lines.
3. Preset sweep, all 52 catalog ids × {static, dynamic}, `static_revenue_effect`
   / `behavioral_offset` / `final_deficit_effect` to 6 dp — **byte-identical**.
4. Every badge (`tier`, `abs_pct`, `rating_label`, `caption`) for all 44 badge
   rows — **byte-identical**.
5. `scripts/build_validation_headline.py --check` — passes, no regeneration.
6. `scripts/check_readiness.py --strict` — same exit status as `main`.

What *does* change, and is the whole deliverable:

7. Explore's "Policy area" list goes 14 → 15 entries, the new one last, and the
   `Drug Pricing` and `IRS Enforcement` areas each lose their demoted members
   (`IRS Enforcement` keeps `irs-enforcement-ira` and
   `irs-enforcement-high-income`; `Drug Pricing` empties and therefore
   disappears from the list). **Every other area's membership and order is
   unchanged.**
8. Build's sections gain a final illustrative area in each direction and lose
   `Drug pricing` (both members demoted) and one of `IRS enforcement`'s two.
   **Every other area's membership and order is unchanged**, and
   `build_catalog`'s own insertion order is unchanged.

---

## 4. Falsification

The lane is refuted, and the branch is abandoned rather than patched, if any of:

- **Any scored number moves.** Items 1–4 of §3 are the test; a single differing
  byte in the holdout JSON, the dashboard, the sweep or the badge dump refutes
  it.
- **Any scorecard row changes** — membership, target, tier flag, or provenance.
  This lane does not open `fiscal_model/validation/`.
- **Any preset becomes unreachable.** `resolve_preset(<id>)` must return the
  same label for all 52 ids; `?preset=<id>` must still select each of the five
  on Explore; `/build?policies=<id>` must still check each of the four with a
  catalog row; a frozen assignment link naming one must still **score**, not
  refuse.
- **Any non-demoted preset moves** in Explore's category list or Build's
  section order.
- **The group label fails to name the tier**, or a demoted preset renders
  without its error beside it (or, for the one with no row, without a line
  saying there is no row).
- **A demoted preset appears in a second place** — flagged *and* still in its
  old area.

---

## 5. Carry-overs this lane records and does not take

1. **The values composer picks `irs-enforcement-double` into all five
   archetype packages** (§1.3), an 82.3%-off reconstruction carrying about
   $61B of a twelve-policy package. Excluding it moves five package totals.
2. **Ask's `list_presets`** does not mark tier at all. Whether the assistant
   should say "illustrative" when it lists these five is the blue tier's call.
3. `composer._tier_for` and `ui/tabs/results_summary._resolve_tier` still read
   `PRESET_TO_SCORECARD_ID` membership as a *calibrated* claim — H6 recorded
   this and left it; the illustrative flag does not reach either.
4. `PRESET_POLICY_PACKAGES`'s `official_total` sums are stale for seven of
   twelve packages (the module says so in its own header). Untouched.

---

## 6. Outturn (appended after the branch landed)

### 6.1 Every zero in §3 is a zero

| artifact | result |
|---|---|
| `scripts/cold_holdout.py --json` | **byte-identical** (`cmp`) |
| `scripts/run_validation_dashboard.py` | **byte-identical**, `Pharma 3 277.8%` and `Enforcement 2 43.5%` unmoved |
| 52 catalog presets × {static, dynamic}, three figures each to 6 dp | **byte-identical** |
| 44 badges — `tier`, `abs_pct`, `rating_label`, `caption` | **byte-identical** |
| `resolve_preset(<id>)` for all 52 catalog ids | **byte-identical** |
| `build_catalog` insertion order | **byte-identical** |
| `scripts/build_validation_headline.py --check` | identical output on both trees, exit 0 |
| `scripts/check_readiness.py --strict` | **identical output** on both trees, exit 2 on both |
| `scripts/check_streamlit_boot.py` | passes, all 9 routes |

The readiness comparison is run the way PR #119's §7.5 lesson says to run it —
by restoring `main`'s six files into this tree, capturing the output, restoring
the branch's, and `cmp`-ing the two — because **exit 2 alone proves nothing
here**: Python 3.14 fails the runtime check first and masks everything after
it, so both trees exit 2 whatever else is true. The *output* is identical line
for line, which is the claim worth making.

### 6.2 What the surfaces now show

**Explore.** The "Policy area" selectbox stays at 14 entries, and the change is
two areas leaving and one arriving last: **`Drug Pricing` disappears entirely**
(all four of its members were demoted) and **`IRS Enforcement` goes 3 → 2**
(`irs-enforcement-ira` and `irs-enforcement-high-income` stay). The new last
entry is **`Illustrative - unfitted reconstructions`**, holding exactly the five
in `PRESET_POLICIES` order: Double IRS Enforcement, Expand Drug Negotiation,
Universal Insulin Cap, International Reference Pricing, Comprehensive Drug
Reform. Selecting it prints `st.warning(ILLUSTRATIVE_GROUP_NOTE)` above the
proposal picker; under the picker the existing badge caption prints that
preset's own distance ("Unfitted reconstruction, 701.0% from -$100B …"), and
`drug-reform-comprehensive`, which has no row, gets an explicit
"No published benchmark scores this policy …" line instead of nothing. **No
other area's membership or order moved**, asserted by a test.

**Build.** `Drug pricing` is gone from both directional sections and
`IRS enforcement` keeps `irs-enforcement-ira` alone. The illustrative section
sorts **last** in each: `irs-enforcement-double`, `drug-negotiation-expand`,
`drug-reference-pricing` under *Revenue raisers*, and `insulin-cap-universal`
under *Tax cuts & new spending*. It is collapsed by default like every other
area, opens on a search hit or a checked member, carries the group note inside,
and each row carries a line under its checkbox. `drug-reform-comprehensive` is
not in Build's catalog and never was — it has no `CBO_SCORE_MAP` entry.

**Build's line is figure-free, and that is a finding rather than a shortcut.**
The first `get_validation_badge` call in a process costs **6.187 s** (measured;
`_scorecard_index` runs every specialized validator over all 81 rows) and
Build's checklist materialises no scorecard at all today — `preset_validation`
has exactly two live callers and neither is on this page. Printing a live figure
on every illustrative checkbox would have put ~6.2 s on Build's first paint,
which is the defect `planning/memos/COLD_START.md` found in the page footer and
PR #135 removed. The alternative considered and rejected was a generated
artifact in `build_validation_headline.py`'s shape: it would go **stale the
moment the concurrent ledger lane retires the two pharma targets**, failing
*their* gate for a reason in this lane's file. So the figure lives where it is
already paid for — Explore's badge caption — and `illustrative_note` names the
tier without one.

**A `with_figure=True` variant was written, shipped in the first commit, and
then deleted, because self-review found it had no caller.** Explore never
needed it (the badge caption beside it already prints the figure) and Build may
not pay for it, so the branch existed only in a test — which is exactly the
defect H6 recorded on `get_confidence_context`, *"the plan describes a live
defect on a dead function"*, reproduced here inside a week. The helper now has
one behaviour per live caller, and the "has this preset a row at all" test asks
`PRESET_ID_TO_SCORECARD_ID` membership rather than the badge, so **neither
path materialises the scorecard** — not just Build's. Explore's no-badge branch
calls it rather than formatting the constant inline, so both branches are
reachable from the app.

### 6.3 Falsification results

Every condition in §4 was tested and none fired.

- **No scored number moved** — §6.1.
- **No scorecard row changed.** `fiscal_model/validation/` was never opened;
  all five keep their rows, and a test asserts each of the four with a row
  still reports `tier == "reconstruction"`.
- **Nothing became unreachable.** `resolve_preset` is byte-identical for all 52
  ids. Through the real router (`AppTest` on `app.py` → `/explore`), a
  `?preset=<id>` link **scores** for `drug-negotiation-expand`,
  `drug-reform-comprehensive` and `irs-enforcement-double`, and lands on the
  illustrative area; a **frozen assignment link** (`frozen=1` plus the four
  provenance stamps) naming `drug-reference-pricing` scores rather than refuses.
- **No non-demoted preset moved**, on either surface.
- **The label names the tier.** `Illustrative - unfitted reconstructions`, and
  a test asserts all three words are in it.
- **No preset is in two places.** `_preset_category` tests the flag *before*
  `ui_category` and before the `is_*` ladder, and `build_catalog` before
  `preset_scoring_category`; a test walks the whole catalog both ways.

23 tests in `tests/test_illustrative_group.py`.

### 6.4 Unpredicted findings

1. **Demoting a group can delete an area, and both surfaces had one.** `Drug
   Pricing` held exactly the four demoted pharma presets, so Explore's policy
   area vanishes rather than empties — the selectbox is built from
   `[c for c in _CATEGORY_ORDER if c in categorized]`, and an area with no
   members is simply not offered. The count therefore stays at 14 rather than
   rising to 15 as §3 item 7 predicted. Build's `Drug pricing` goes the same
   way. §3's prediction was wrong in its arithmetic and right in its substance;
   the membership assertions are what the tests pin.
2. **`drug-reform-comprehensive` never had a Build row**, because Build's
   catalog is driven by `CBO_SCORE_MAP` and it has no entry there. So the group
   is five presets on Explore and four on Build, and the preset with the
   weakest number is the one Build never quoted. Worth knowing before anyone
   reads "the five" as a single population.
3. **Build has no default or "quick" package to exclude anything from** — the
   checklist starts empty and `apply_preselection` only ever runs from a link.
   The §1.2 requirement was vacuous, which is the right outcome to record
   rather than to satisfy by inventing an exclusion.
4. **The values composer is the real "default package", and it picks a demoted
   preset every time.** All five archetypes select `irs-enforcement-double`
   into their twelve-policy package, and **none** selects any of the four
   pharma presets — so the one demoted preset that reaches a values-built
   package is the 82.3% enforcement row, not the 701% pharma one. Measured
   before any edit, and left alone: `composer.py` is outside this lane's files
   and excluding the row would move five package totals. Carry-over 1.
5. **A new preset area has a second home, and only the full suite found it.**
   `fiscal_model/validation/credibility.py`'s `PRESET_AREA_TO_SCORECARD_CATEGORY`
   routes an area to the scorecard category whose *limitations list* and
   *holdout label* a result surface prints, and
   `test_confidence_band.py::test_mapping_dicts_cover_every_preset_area` fails
   when `_preset_category` returns an area that map does not carry. **Nothing a
   user reads had moved**: `_category_for_preset_area` defaults an unmapped
   area to `"Generic"`, and `"Generic"` is exactly what all five already
   resolved to through `Drug Pricing` and `IRS Enforcement` — verified by
   running `category_for_result` over all five before and after. So the
   demotion worked *silently* and the invariant fired anyway, which is the
   right requirement and the reason to keep it: a new area should be a decision
   rather than a fallback. **None of this lane's own instruments could have
   caught it** — the surface dumps, the preset sweep, the holdout, the
   dashboard and the badge dump were all byte-identical, because the defect was
   in a *declaration* rather than in an output. Worth carrying: when a lane
   adds a member to an enumerated domain, the question is not only "what does
   this change" but "who else enumerates this domain".
6. **This lane reproduced H6's own finding inside a week.** The first commit
   shipped `illustrative_note(preset, *, with_figure=True)` whose figure-
   composing branch had **no caller in the tree** — Explore did not need it and
   Build could not afford it, so it existed only in a test. H6 recorded exactly
   this shape (`get_confidence_context` has no caller; the plan described a
   live defect on a dead function) and it was written again anyway. The
   general lesson is narrow and worth carrying: **a helper with a mode
   parameter should be checked against its callers before it is committed, not
   after** — if one mode has none, the parameter is describing the author's
   hesitation rather than the surfaces' needs. §6.2 has the fix.

### 6.5 Files touched outside the lane's stated list

`fiscal_model/ui/policy_input_presets.py` and `fiscal_model/ui/policy_input_tax.py`
— declared in advance in §2 and for the reason given there: Explore's preset
picker does not live in `app_pages/explore.py`, which is a router. No sibling
lane owns either file. `components/cards.py` was read and **not** edited (the
Ask home's cards are `tcja`, `biden400k`, `corp28`, `tariff10`).

`fiscal_model/validation/credibility.py` — **a seventh file, and the one this
lane did not foresee**, in the directory the concurrent ledger lane owns. One
entry added to `PRESET_AREA_TO_SCORECARD_CATEGORY` (§6.4 item 5); no target, no
registry, no scorecard row touched, and the merge surface is a single dict line
in a file that lane has no reason to open.
