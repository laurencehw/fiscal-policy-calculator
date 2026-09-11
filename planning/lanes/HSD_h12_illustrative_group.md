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
