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
- [ ] A generic Tailor run emits no share link (`build_share_url` returns `None` when the policy name has no catalog id). The `/tailor` **reader** and `encode_tailor_share` both exist, so wiring the result panel to emit a `/tailor?type=…&rate=…&who=…` link for custom runs is now a small change.

## For Phase 6 (mobile / polish)
- [ ] Anchor-scroll helper after Calculate/Score (one `components.html` utility).
- [ ] Freshness alarm recalibration: `fiscal_model/data/freshness.py:57-58` `_CBO_FRESH_DAYS=120/_CBO_STALE_DAYS=180` flags a Feb baseline amber ~200 days in; amber only when a newer CBO release exists.
- [ ] Tracker banner: drop "run python scripts/update_bills.py" from user copy → "data refresh pending".
- [ ] Verify 375px: top nav, doorway-card stacking, sticky scoreboard is desktop-only (≥1025px) — confirm the fallback layout reads well.
- [ ] Dark mode re-verify on all new surfaces (chrome popovers, Build badges/captions, Sources row).
- [ ] CI ruff scope: add `app.py app_pages/ components/` to the ruff step.
- [ ] Docs drift: `CLAUDE.md`, `docs/ARCHITECTURE.md`, README still describe the tabbed `app.py`; update once phases land.

## Owner decisions still open (non-blocking)
- [ ] **Scoring window**: Build renders FY2025–2034 because `FiscalPolicyScorer` defaults `start_year=2025`; plan and wireframes say FY2026–2035 (matches the CBO Feb 2026 baseline). Changing the scorer default is outside the redesign's non-goals — owner call.
- [ ] Archetype names/vectors (§5b.3) — review for steelman quality before launch.
