# Redesign — follow-ups queued for later phases

Items surfaced by completed phases that belong to a later lane. Tick when done.

## For Phase 5 (routing / preset IDs / legacy shim)
- [ ] `/ask` is not a real route: Streamlit forces the default page's `url_path` to `""`, so `/ask` flashes "page not found" then renders Ask. Canonicalize in `_apply_legacy_url_shim` (app.py) — e.g. redirect `/ask` → `/` preserving `?q=`.
- [ ] `?analysis=preset&preset=<label>&dynamic=&run=1` legacy links currently land on `/` (Ask). Shim must translate to `/explore?preset=<id>&dynamic=&run=1` via `preset_ids.resolve_preset` and preserve auto-run.
- [ ] Share-link round trip fragility (NOTES §3.3): `share_links.py:107` writes a full label into `sidebar_preset_choice`, which the selectbox evicts; restoration survives only via `default_preset`. Fix with ids. Pinned by `tests/test_policy_input_widget_state.py::test_share_links_session_state_write_is_evicted_by_the_selectbox`.
- [ ] Promote the two Build-local ids minted in `deficit_target._SCORE_ONLY_ENTRIES` (mortgage / SALT deduction repeal) into `preset_ids.PRESET_ID_BY_LABEL`; ids already chosen and stable.
- [ ] Add `salt-deduction-eliminate` ↔ `salt-cap-repeal` to an exclusive group in `preset_ids.py`.
- [ ] Share URLs also carry `baseline=feb2026`; print into Copy Summary + CSV headers (Build already carries vintage).
- [ ] `tests/test_streamlit_boot_script.py` / `scripts/check_streamlit_boot.py`: add `/explore?preset=tcja-full-extension&run=1` and the legacy-label URL.

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
