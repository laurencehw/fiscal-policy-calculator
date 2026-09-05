# Redesign — follow-ups queued for later phases

Items surfaced by completed phases that belong to a later lane. Tick when done.

## For Phase 5 (routing / preset IDs / legacy shim) — done
- [x] `/ask` is not a real route. Fixed in `app._apply_legacy_url_shim`, which now runs **before** `st.navigation` (that is where the "page not found" decision is made) and rewrites the page intent to the default page. Verified live over the websocket: `/ask`, `/ask?q=x` and `/studio` emit no `page_not_found`.
- [x] `?analysis=preset&preset=<label>&dynamic=&run=1` → `/explore?preset=<id>&…`. Pure translation in `share_links.rewrite_legacy_query`; the router applies it and repoints the page in the same script run (no `st.switch_page` round trip). Auto-run preserved via `run=1` → `qs_calculate`.
- [x] Share-link round trip (NOTES §3.3). `apply_share_query_params` resolves the token to its canonical label and writes the two keys the pickers read — `sidebar_policy_area` and the **short** name in `sidebar_preset_choice` — through `seed_widget_default`, so the mirror survives a page switch too. The pinned test now asserts the corrected behaviour (`test_share_links_session_state_write_survives_the_selectbox`).
- [x] Build-local ids promoted: `preset_ids.SCORE_ONLY_ID_BY_LABEL` (mortgage / SALT deduction repeal) + `SCORE_ONLY_ALIAS_ID_BY_LABEL` (the two tariff re-estimates). They join `all_preset_ids()` / `LABEL_BY_PRESET_ID` but **not** `CATALOG_PRESET_IDS`, which stays the 52 engine-scorable presets the values tagger must cover.
- [x] `salt-deduction-eliminate` added to the existing `salt-cap` exclusive group (the same instrument at its opposite setting). `tests/test_policy_catalog.py` snapshot updated deliberately.
- [x] Share URLs carry `baseline=feb2026&spec=<policy_spec_hash>&mode=conventional|dynamic`; the token and the export header both derive from `components.results.resolve_baseline_vintage()` via `share_links.baseline_vintage_token`.
- [x] Boot script: added `/ask`, `/ask?q=x`, `/explore?preset=tcja-full-extension&run=1`, `/tailor?type=income&rate=2&who=top400k&phase=1&run=1` and the legacy-label URL; `tests/test_streamlit_boot_script.py` kept in sync.

Left for a later lane:
- [x] A generic Tailor run now emits a share link. `build_share_url` falls through to
  `share_links.generic_tailor_share_url`, which reads the scored `Policy` object (not the widget
  state) and calls `encode_tailor_share` with the same `baseline` / `spec` / `mode` provenance a
  preset link carries. Verified live: a −2pp/$400K+ run emits
  `/tailor?type=income&rate=-2&who=top400k&phase=…&duration=…&dynamic=…&run=1&baseline=…&spec=…&mode=…`,
  and the text export carries it too. `POLICY_TYPE_TO_TAILOR_KIND` limits it to the three types
  Tailor has a form for; payroll/estate/etc. still return `None`. Round-trip test added.

## For Phase 6 (mobile / polish)
- [x] Anchor-scroll helper after Calculate/Score — now one utility, `components.results.scroll_to_results_anchor`, next to the `RESULTS_ANCHOR_HTML` it targets and its single call site in `render_score_surface`. Removed from `app_controller` (which no longer renders results, and no longer imports `time`). Verified in a browser on Tailor (anchor lands at viewport top) and Explore.
- [x] Freshness alarm recalibration — done in `655131d`; release-calendar based, `_CBO_CYCLE_DAYS=395` / `_CBO_OVERDUE_DAYS=425` fallback. NOTES §11.13 updated.
- [x] Tracker banner copy — done in `655131d`.
- [x] Verify 375px (browser, via a 375-wide same-origin iframe — Chrome would not honour a window resize below the OS minimum). No horizontal scroll on `/`, `/build`, `/tailor`, `/explore` (`scrollWidth == innerWidth == 375`, zero overflowing elements); every `st.columns` group stacks full-width; the Build scoreboard renders **below** the checklist and no element is `position: sticky` (the ≥1025px guard holds); Streamlit moves the top nav into a **collapsed sidebar** natively at this width, so plan §8.1's fallback needed no code.
- [x] Hit targets ≥44px — **were failing**: sidebar nav links 28px, `st.pills` 32px, chrome popover triggers 40px. The existing mobile rule only covered `.stButton`. Added a ≤640px block in `ui/styles.py` covering `stBaseButton-pills(-Active)`, `-segmented_control(Active)`, `-secondary`, `-primary`, `stPopoverButton`, `stPageLink-NavLink`, `stSidebarNavLink`. Re-measured: all 44px.
- [x] Dark mode re-verified on every new surface — **was badly broken**. The overlay painted the page dark and forced light text, but left every Streamlit surface it did not repaint on its light theme, i.e. white-on-white: the top-nav header, the data-status pill and ⚙ triggers, the Build segmented control, the search input, expander headers. Also the app's own result cards (headline card, validation-evidence card, `.info-box`) kept inline pale backgrounds, so the headline number rendered white-on-grey and lost its red/green direction. Fixed by extending `_DARK_MODE_CSS` (`data-testid`-addressed, degrades to the light surface if a selector ever detaches) and by moving the result cards' palette out of inline hex into `.fpc-result-card` / `.fpc-impact-*` / `.fpc-evidence-card` classes defined in `ui/styles.py` (light) and `chrome.py` (dark). Alerts get a hue-preserving `brightness(1.75)` lift. Re-audited in the browser: no unreadable surface left. **Known limitation:** Plotly charts still paint a white canvas in dark mode (dark-on-light, so readable, not unreadable) — a real fix needs `st.plotly_chart` template switching, out of scope here.
- [x] CI ruff scope — done in `655131d`.
- [x] Docs drift — `CLAUDE.md` (router + `app_pages/`, `components/`, `composer/`, `preset_ids.py`, Package Studio folded into Build, URL contract table), `README.md` ("Navigation and URLs" section + project tree; model-maturity wording untouched), `docs/ARCHITECTURE.md` (presentation layer, URL contract, result object, values pipeline), NOTES §4.3 and §11.13.

## Phase 6b — new / carried forward
- [x] `$`-rendering guard is now a test: `tests/test_dollar_rendering.py` renders `/`, `/build`, `/tailor` and `/explore` (after a real run) through `AppTest` and asserts no rendered string carries two unescaped currency amounts. It found a **live** bug — the Results "Sensitivity range: `$+4,581.9B to $+4,581.9B`" line rendered as a KaTeX span with the dollar signs eaten — plus the over-cap rate-limit message (NOTES §11.22). Both fixed. Two things learned and encoded in the test: Streamlit's math parser opens a span on `$+`/`$-`, not just `$<digit>`; and a **block-level** HTML string (`<p>…`) is opaque to `remark-math` while an **inline** one (`<small>…`) is not — so the interpretation card is correctly left unescaped and escaping it actually renders a visible backslash.
- [x] Streamlit 1.56 deprecations cleared: `use_container_width=` → `width="stretch"`/`"content"` across `app_pages/`, `components/`, `fiscal_model/ui/` and `ui/tabs/` (the `a11y.render_accessible_chart` kwarg is kept for callers and translated at the boundary). pyarrow mixed-type warning fixed at `ui/tabs/detailed_results.py` by casting the display-only Policy Details column to `str`.
- [ ] **Plotly charts are not dark-mode aware** (white canvas on a dark page). Needs a theme-driven Plotly template in `ui/charts.py` passed through `apply_base_layout`, plus the same for the Vega tooltip. Readable today, but it breaks the illusion.
- [ ] **Dark mode is a CSS overlay, not a theme.** Streamlit exposes no runtime theme API and no CSS custom properties to override, so `_DARK_MODE_CSS` enumerates surfaces by `data-testid`. It is now correct on every surface the app renders, but a future Streamlit that adds a widget type will re-open the same class of bug. Worth revisiting if upstream ships a runtime theme switch.
- [x] Scoring-window drift is visible to users: Explore shows **FY2026–FY2035** for a calibrated preset while Tailor shows **FY2025–FY2034** for a generic run (`FiscalPolicyScorer` defaults `start_year=2025`). Same owner call as the entry below, but note it is now a *within-session* inconsistency, not just a plan mismatch. **Closed with the entry below** — one window, `fiscal_model.baseline.APP_DEFAULT_START_YEAR`; see `tests/test_scoring_window.py`.

## Owner decisions still open (non-blocking)
- [x] **Scoring window** — *decided and shipped*: every app surface (Ask, Build, Tailor, Explore, classroom) and the public API now score **FY2026–FY2035** through one named constant, `fiscal_model.baseline.APP_DEFAULT_START_YEAR`. The scorer/dataclass defaults were **not** moved: the validation suite reaches the same policy factories the app does, and its targets are quoted on the windows their own documents used, so the window is applied app-side (`create_policy_from_preset` for presets, the calculation paths for custom runs) and `DEFAULT_VALIDATION_START_YEAR` stays 2025. `cold_holdout.py --json`, `run_loo.py --donor-matrix`, `run_validation_dashboard.py`, `distributional_validation.py` and `check_readiness.py --strict` are identical before and after. Two app totals move, both in `pharma.py`, whose schedule is anchored to statutory calendar years: Expand Drug Negotiation −$33.5B → −$41.8B and Comprehensive Drug Reform −$150.5B → −$158.9B, because a FY2026–2035 window holds one more post-2029 negotiation year than FY2025–2034 did. See `tests/test_scoring_window.py`.
- [ ] Archetype names/vectors (§5b.3) — review for steelman quality before launch.

## From the external app assessment (2026-09-01) — queued, not implemented

Raised by an outside reviewer against the live app. Product/UX items only; the
validation-documentation half of that review landed separately in
`docs/METHODOLOGY.md`, `planning/MODELING_IMPROVEMENT.md` and
`planning/NEXT_STEPS.md`.

- [x] **Classroom as a first-class path, not a mode flag.** Done: `frozen=1`
  alongside the provenance stamps locks baseline vintage, scoring engine,
  dynamic on/off **and** the policy (the owner's call), renders those controls
  disabled under "🔒 Frozen for this assignment" in the form, beside Score and
  in the ⚙ popover, and **refuses to score** when the URL's vintage is not the
  one the deployment serves. Codec and UI in `fiscal_model/ui/frozen_links.py`;
  instructors make one from a result surface opened with `?classroom=1`.
  Carry-over: Build packages are not freezable, and the frozen link does not
  pin the Data & methodology options (a spec-hash mismatch is captioned, not
  refused).
- [~] **Cold start: ~20s of blank skeleton on Streamlit Cloud.** *Partially done
  in #82* — option (a) shipped: the chrome and brand line are painted before any
  data load or heavy import, so the first script run no longer renders nothing
  recognisable. What remains is the part (a) cannot reach: Streamlit Cloud
  container sleep itself, which needs (b) a warm container (paid tier or an
  external pinger) or (c) an explanation in the copy surrounding the link. The
  measurement that decides between them has not been made, and it is the next
  step: if most of the remaining wait is import time there is more of (a) to do;
  if it is cold container scheduling, only (b) helps. Streamlit does not paint
  until the first script run completes, so no in-app placeholder can cover the
  scheduling half.
- [x] **The "older snapshots" data banner reads like an outage.** — done in #82.
  The degraded-data banner used to fire on page load, before the visitor had
  scored anything, and its wording made a routine baseline-vintage lag look like
  the site was broken — the landing page's first impression was a warning about a
  problem the visitor did not yet have. The vintage is now stated as a neutral
  fact where it matters, and alert styling is reserved for genuinely unusable
  data. `components/chrome.py` owns both the banner and the data-status pill.
- [x] **Zero-width sensitivity band on calibrated presets looks broken.** — done
  in #82. A calibrated preset used to render "Sensitivity range: $+4,581.9B to
  $+4,581.9B" — the same number twice, which read as a rendering bug rather than
  as "this preset carries a point estimate with no modelled band".
- [x] **Build-page garbled reasoning sentences and raw `\$` escapes.** — done in
  #82. The Build page's generated reasoning text used to show truncated and
  ungrammatical sentences, and backslash-dollar escapes leaked through to the
  reader where the string is block-level HTML (opaque to `remark-math`) and
  therefore should not have been escaped at all — the inverse of the bug
  `tests/test_dollar_rendering.py` was written for.
