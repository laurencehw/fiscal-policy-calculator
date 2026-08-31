# Redesign plan — Ask-first navigation for the Fiscal Policy Calculator

**Handoff document for a coding agent.** Self-contained: everything needed is stated here or discoverable in the repo by the steps in Phase 0.

- **Repo:** github.com/laurencehw/fiscal-policy-calculator (Streamlit, Python 3.13, deployed on Streamlit Community Cloud)
- **Live app:** https://fiscal-policy-calculator.streamlit.app/
- **Wireframes:** claude.ai/code/artifact/f3f637ba-893c-4007-a338-91b1332c09c8 — six artboards: *Ask home (desktop)*, *Build*, *Tailor*, *Ask mobile*, *IA map & URL contract*, *Build — start from your values*. Numbered chips ①–⑮ on the artboards map to the requirements below (look for “**[chip N]**”).
- **Owner:** Laurence Wilse-Samson. When a decision below says “ask,” ask him rather than guessing.

## 1. Goal and shape of the change

Re-architect navigation from the current 5-tab layout (Calculator · Ask · Budget Builder · Bill Tracker · Methodology, plus a global config sidebar) to a **verb-first multipage app**:

| New page | URL | What it is today |
|---|---|---|
| **Ask** (default/home) | `/` and `/ask` | the Ask tab, promoted to landing page |
| **Build** | `/build` | Budget Builder tab |
| **Tailor** | `/tailor` | the sidebar’s “Custom tax policy” + “Spending program” forms, moved into a page |
| **Explore** | `/explore` | the Calculator tab (presets, example cards, results) |
| **More ▾** (nav group) | `/tracker`, `/methodology`, `/classroom` | Bill Tracker, Methodology, Classroom Mode |

Mechanism: **`st.Page` + `st.navigation(position="top")`** (supported in current Streamlit; docs: docs.streamlit.io/develop/api-reference/navigation/st.navigation). Every existing surface keeps a home; nothing is deleted. This is a re-arrangement of working code plus a small number of behavioral requirements listed in Phase 3–5.

**Non-goals (do NOT do in this pass):** no scoring-engine changes beyond the single-result-object refactor in Phase 4; no Bill Tracker data refresh; no visual re-theme (keep the existing Source Sans theme and component styling); no new features beyond what’s specified.

## 2. Phase 0 — recon (read-only, ~30 min)

1. Map the entry point: find the current `st.set_page_config` call, the top-level `st.tabs([...])` for the 5 tabs, and the inner `st.tabs` for the 7 result sub-tabs.
2. Find the sidebar builder: the code that renders “Policy Configuration” (radio: preset/custom/spending), the preset picker (Policy area → proposal), “Model settings” (dark mode, dynamic scoring), and “Data Status”.
3. Find the query-param share-link handling: the code that reads `?analysis=preset&preset=…&dynamic=…&run=1` and the code that generates share URLs.
4. Find where results are rendered (the “Results Summary” block, validation card, key metrics, charts, exports) and where the computed result is stored in `st.session_state`.
5. Find the Ask tab implementation: the LLM call, the citation post-processing (“markers with no source are stripped”), and the suggestion chips.
6. Note every `st.session_state` key written by widgets (they must keep their keys across the move, or be migrated deliberately).
7. Confirm Streamlit version in requirements; upgrade to the latest 1.x if `st.navigation(position="top")` needs it. Known upstream quirk: nav can render in both top and sidebar in some configs (github.com/streamlit/streamlit/issues/13224) — verify after upgrade.

Deliverable: a short `NOTES.md` mapping file → responsibility, before writing code.

## 3. Phase 1 — multipage scaffold (no behavior change yet)

1. Create `app.py` as router:
   - `st.set_page_config(layout="wide", page_title=…)` once, here.
   - Define pages with `st.Page(fn_or_path, title=…, url_path=…, default=(Ask))`; group Tracker/Methodology/Classroom under a `"More"` section dict; `st.navigation(..., position="top")`.
   - Run the legacy-URL shim (Phase 5) BEFORE `nav.run()`.
2. Move each existing tab body into `pages/ask.py`, `pages/build.py`, `pages/explore.py`, `pages/tracker.py`, `pages/methodology.py`; Classroom already is a page — keep it, register under More.
3. Shared chrome: a small `components/chrome.py` with the **data-status pill** for the top area of every page **[chip ①]**: compact `CBO Feb 2026 · SOI 2023` with an amber/green dot; clicking/expanding reveals the full Data Status panel (move the current sidebar panel content into an expander or a `/methodology#data` anchor — ask which he prefers if unclear; default: popover/expander on the pill). The global sidebar is **removed** on all pages except where a page deliberately uses one.
4. Keep dark-mode + dynamic-scoring toggles: move “Model settings” into the pages that use them (dynamic toggle → Tailor and Explore, near Calculate; dark mode → nav corner or More; ask if unclear — default: keep a slim sidebar ONLY for Model settings on Explore/Tailor, or a settings popover).
5. Acceptance for this phase: app boots to Ask at `/`; all five surfaces reachable from the top nav; no dead code paths; existing session-state keys unchanged.

## 4. Phase 2 — the Ask home page

Wireframe: *Ask — home (desktop)* and *Ask — mobile*.

1. Layout: centered hero (H1 + one-line subtitle), `st.chat_input` **[chip ②]**, then a row of suggestion chips (use `st.pills` or buttons; reuse the existing 6 suggestions). Below: two **doorway cards** to Build and Tailor using `st.page_link` **[chip ④]**; then the four worked-example cards **[chip ⑤]** which now PREFILL the chat (set the question into session state / `?q=`) instead of running a preset — each card keeps its policy-status chip (Enacted · P.L. 119-21 / Proposal) and dated source, as shipped in the current build.
2. **Streaming is required** **[chip ③]**: replace the blocking LLM call with `st.write_stream` over the provider’s streaming API. Wrap the chat in `@st.fragment` so a question doesn’t rerun the whole page.
3. **Citations** **[chip ③]**: render a real source list. Whatever the model returns, post-process to (a) a numbered “Sources (N)” row of links (title + date, URL where available) under each answer, and (b) strip any marker with no resolvable source, as the tab already promises. Never render bare `[^N]`.
4. **No truncation**: raise/handle the completion budget so answers end cleanly; if the provider truncates, append a visible “answer was cut — continue?” affordance rather than stopping mid-table.
5. **Enter-to-send** **[chip ②]**: verify by hand in a real browser that Enter submits `st.chat_input` (automation suggested it may not; if it reproduces, investigate the component wrapper/JS interference and fix).
6. Context chip: “Using current scored policy: <policy name>” — show the actual policy name from the result object, or hide the chip when none.
7. Guardrail already in prod, keep it: engine calls from Ask must go through the capability gate — uncalibrated paths answer with the nearest validated benchmark + labeled interpolation instead of a raw engine number.

## 5. Phase 3 — the Build page

Wireframe: *Build — package (desktop)*.

1. Two-column layout: policy checklist left, **sticky scoreboard right** **[chip ⑧]** (`st.columns`; sticky via a small CSS block — acceptable use of custom CSS; keep it isolated in one place).
2. Target strip at top **[chip ⑥]**: metric toggle (% of GDP / $B) + target slider, unchanged logic.
3. **Overlap guardrails** **[chip ⑦]**: define mutually-exclusive groups in the policy data (e.g. the three SS-cap options; SALT repeal vs SALT elimination; nested TCJA bundles). Within a group, selecting one disables/dims the others with a “pick one” chip. Data-driven: add a `exclusive_group` field to the policy list rather than hard-coding UI.
4. Label the per-year vs 10-year conversion explicitly on the waterfall (“per-year, 10-yr totals ÷ 10”) **[chip ⑧]**.
5. Keep CSV/share/copy-summary exports; share URL becomes `/build?policies=<ids>&target=3.0`.
6. Fix the “1 policies” pluralization while in there.

## 5b. Phase 3b — “Start from your values” (the second door into Build)

Wireframe: *Build — start from your values*. Purpose (owner’s words): the bridge between public finance as practiced and everybody — journalists, political scientists, philosophers arrive thinking in commitments, not instruments. Build opens on this panel; a mode toggle (“Start from your values” / “Start from scratch”) flips straight to the checklist. Pre-selects load INTO the normal checklist — one scoreboard, one export path, everything stays editable.

**Architecture rule (non-negotiable): LLM translates, deterministic code selects.** The LLM never picks policies; it only maps free text to a values vector. Policy selection is a pure function of tags + vector, so identical values always produce an identical package, the archetype path works with no LLM call at all, and every selection is explainable.

1. **Tag schema on the policy catalog** (wherever the Budget Builder options live). Add per policy:
   ```yaml
   tags:
     direction: raise_revenue | cut_revenue | cut_spending | add_spending
     progressivity: strong_progressive | progressive | neutral | regressive | not_modeled
     govt_size: shrink | grow | neutral
     base: individual | corporate | payroll | consumption | estate | enforcement | transfer
     generational: current | future | mixed
   ```
   Derive `progressivity` from the app’s own distribution engine where the policy is representable (write a one-off script that scores each and emits the tag; keep a manual-override file for the rest, tagged `not_modeled` → treated conservatively by the selector). Tags are honest metadata — show them in the UI on request.
2. **Values vector** (the shared interlingua): `{redistribution: -1..1, deficit_concern: 0..1, govt_size: -1..1, growth_priority: 0..1, generational_weight: 0..1, protected: [middle_class_rates, ss_benefits, medicare, defense, ...] , target_pct_gdp: float}`. Define once in `values/schema.py`; validated everywhere.
3. **Archetypes** (`values/archetypes.yaml`): five to start — *Deficit hawk, protect the vulnerable* · *Small government* · *Growth-first* · *Egalitarian* · *Generational steward* **[chip ⑫]**. Each: `{id, name, one_line, vector, rationale_template}`. Naming rules: value language only, never party or politician labels; each must read as its holder’s steelman. IDs are stable slugs (they go in URLs).
4. **Selector** (`values/select.py`): deterministic `select_package(vector, catalog) -> [(policy_id, why_sentence)]` — score policies against the vector (progressivity × redistribution, direction × govt_size, exclude anything touching `protected`, respect exclusive groups from Phase 3), then greedily fill toward `target_pct_gdp`. Emit a per-policy “why this one, given your values” sentence from the rationale template (e.g. “raises the SS cap *rather than* middle rates because you protected the middle class”). Unit-test determinism.
5. **Free-text translation** **[chip ⑬]**: LLM call with a fixed JSON schema returning ONLY a values vector + a one-sentence reading; validate against the schema; on failure, fall back to “pick an archetype.” Reuse the Ask feature’s provider plumbing and its capability-gate discipline.
6. **Reflected interpretation panel** **[chip ⑭]**: render the inferred vector as editable controls (“Redistribution: Strong”, “Protected: middle-class rates, SS benefits”) with the package preview and coverage (“7 policies, 62% of target”). Any edit re-runs the selector live (no LLM). “Load into the checklist” applies the pre-selects to Build state; the notice “starting point, not a verdict” stays.
7. **URL** **[chip ⑮]**: `/build?values=<archetype_id>` and `/build?vector=<base64-json>` restore the panel state; both shareable.
8. **Acceptance criteria (add to §9):**
   - Archetype path works fully offline (no LLM configured) — cards → package → checklist.
   - Determinism: same vector twice → byte-identical package and rationale.
   - **Symmetry harness**: a test that runs all archetypes and asserts each produces ≥4 policies reaching ≥40% of its target with at least one “why” sentence each — no archetype may be a strawman by construction.
   - Free-text path never emits a policy_id outside the catalog; schema-invalid LLM output degrades gracefully to archetype cards.
   - Editing any reflected dimension changes the package without an LLM call.
   - `?values=egalitarian` link round-trips.
9. **Classroom hook** (cheap, do it): a Classroom Mode assignment stub “Build a budget from your philosophy, then defend it” linking to `/build?values=…` — the normative→positive mapping is the exercise.

## 6. Phase 4 — the Tailor page and the shared result panel

Wireframe: *Tailor — custom policy (desktop)*.

1. Move the sidebar’s custom-policy and spending forms into the page as a left-column form card: policy type segmented control (Income · Corporate · Capital gains · Spending), rate slider, who-affected select, duration + phase-in, advanced expander (auto-populate note), primary “Score this policy” button. “Start from: Blank / a preset” lets Tailor seed from any preset’s parameters.
2. **Phase-in minimum = 1** in the widget (already fixed in prod — preserve it; the engine contract is `phase_in_years ≥ 1`) **[chip ⑨]**.
3. **Single result object** **[chip ⑩]** — the core refactor:
   - One dataclass/dict per run: `{policy_spec_hash, policy_name, mode (conventional|dynamic), window (FY2026–2035), headline, static, behavioral, feedback, per_year, tier, benchmark, baseline_vintage, policy_status, created_at}`.
   - Every surface (headline, key metrics, waterfall, sub-views, Copy Summary, CSV, share URL) renders from this object. One sign convention app-wide (+ = increases deficit), stated once.
   - **Invalidation**: any change to the form after a run flips the panel to “Configuration changed — score again to refresh” instead of showing the previous result **[chip ⑩]**. This must also apply on Explore (preset changes) — it generalizes the preset-leak fix already shipped.
   - **Calibrated presets + dynamic**: resolve the remaining inconsistency — decide ONE rule (recommend: headline stays the conventional calibrated score; a clearly-labeled “Dynamic view” shows feedback and dynamic total; Key Metrics’ feedback field must agree with the Economic Effects tab in all cases, and the SS-cap-style “headline absorbs feedback” path must follow the same rule). Add a regression test asserting Results/Key-Metrics/Economic-Effects/Copy-Summary agree for (a) a calibrated preset, (b) a generic run, with dynamic on and off — four cases.
4. Extract `components/results.py: render_results(result)` used by Tailor, Explore, and (package-level variant) Build **[chip ⑩]**. Deep views (Distribution, Economic Effects, Scoring Models, Generational, State) open from the result panel (tabs inside the panel are fine).
5. Keep the tier badge + sensitivity band + “nearest validated benchmark” line on generic runs, and the policy-status + baseline sentence on presets.

## 7. Phase 5 — routing, share links, back-compat

Wireframe: *IA map & URL contract* artboard.

1. URL contract: `/ask?q=…` (prefill), `/explore?preset=<stable_id>&dynamic=0&run=1`, `/tailor?type=income&rate=2&who=top400k&phase=1&run=1`, `/build?policies=<ids>&target=3.0`.
2. **Stable preset IDs**: introduce slug IDs for presets (share links must not encode emoji display labels). Keep a label→id map so existing links keep working.
3. **Legacy shim** (runs in `app.py` before `nav.run()`): detect old-style `?analysis=preset&preset=<label>&…&run=1`, translate to `/explore?preset=<id>&…`, `st.switch_page` + preserve auto-run. Old links must restore and run exactly as before.
4. Share URLs now also carry `baseline=feb2026` (vintage stamp) — print it into Copy Summary and CSV headers too.

## 8. Phase 6 — mobile + polish

1. Mobile **[chip ⑪]**: with the global sidebar gone, verify at 375px: top nav collapses acceptably (test `st.navigation` top-nav behavior at narrow widths; if it degrades, fall back to nav in a collapsed sidebar on mobile only), no horizontal scroll, doorway cards stack, hit targets ≥ 44px.
2. After any Calculate/Score, scroll the result heading into view (small `components.html` JS anchor-scroll helper; keep it one utility).
3. Dark mode: re-verify all new surfaces (the sidebar-token fix shipped; new components must use theme-aware colors).
4. De-duplicate the degraded-data banner text (currently the CBO-stale sentence renders twice) and re-calibrate the alarm: Feb-baseline within its normal annual cycle = green/neutral; amber only when a newer CBO release exists. Tracker banner: drop “run python scripts/update_bills.py” from user-facing copy (say “data refresh pending”).

## 9. Acceptance criteria (test these, in order)

Automated where possible — Streamlit’s `st.testing.v1.AppTest` covers most; use Playwright (or manual) for scroll/mobile/streaming.

1. Fresh session lands on **/ask**; nav shows Ask · Build · Tailor · Explore · More; no global sidebar on Ask/Build/Tracker/Methodology.
2. Ask: question streams token-by-token; answer ends cleanly; a Sources row renders with ≥1 clickable link; no `[^N]` appears; Enter submits (verified by hand).
3. Ask engine gate: “score a 25% corporate rate” style questions return benchmark-anchored numbers (sanity: within ~2x of interpolated official anchors, never 5x).
4. Build: checking an exclusive-group option dims its siblings; totals update; waterfall labeled per-year; share URL round-trips.
5. Tailor: defaults score successfully (no `phase_in_years` error); changing any input after a run shows the invalidation notice, not stale numbers.
6. Consistency: for TCJA preset AND a generic custom run, dynamic on and off — headline, Key Metrics feedback, Economic Effects, and Copy Summary agree (the four-case regression test).
7. Legacy link `?analysis=preset&preset=🏛️+TCJA+Full+Extension+(CBO:+$4.6T)&dynamic=0&run=1` restores + auto-runs on /explore.
8. Mobile 375px: no horizontal scroll; content visible without dismissing anything; nav usable.
9. `$`-rendering CI check still passes app-wide (grep rendered output for `$…$` LaTeX spans — guard already exists conceptually; make it a test).
10. Existing exports (CSV, text, Copy Summary) all carry: policy name, status, baseline vintage, window, tier.
11. Values entry: all Phase 3b acceptance criteria (offline archetypes, determinism, symmetry harness, graceful LLM degradation, editable reflection, `?values=` round-trip).

## 10. Risks / open questions for the owner

- Where should the full Data Status panel live once the pill replaces it (popover vs /methodology section)?
- Model-settings placement (slim sidebar on Explore/Tailor vs settings popover)?
- “Build” vs “Describe” naming — wireframes use **Build** with “Start from your values” as its opening panel; confirm.
- Archetype set and names (§5b.3) — owner should review the five for steelman quality and coverage before launch; consider an outside reader from each tradition.
- Progressivity tags for non-representable policies (payroll caps, estate, corporate incidence): manual tags with a `not_modeled` flag, or hold those policies out of values-scoring until the distribution engine covers them?
- `st.navigation(position="top")` styling limits: accept stock look, or add the one CSS block (brittle across Streamlit upgrades — pin the version if so).
- Streamlit Community Cloud entry point changes (`app.py` as main) — update the deployment setting.

## 11. Suggested commit sequence

1. `phase0-notes` (NOTES.md only) → 2. `multipage-scaffold` (Phase 1, behavior-neutral) → 3. `ask-home` → 4. `build-page` → 5. `values-entry` (Phase 3b: tags + archetypes + selector, then free-text) → 6. `result-object + render_results` → 7. `tailor-page` → 8. `routing-shim` → 9. `mobile-polish` → each with the relevant acceptance tests green before the next. If scope must be cut, ship `values-entry` with archetypes only (no free-text) first — it is the accessibility payload and needs no LLM.
